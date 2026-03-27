"""
ETL Silver Layer - Limpieza y normalización de datos
Transforma datos Bronze en tablas limpias y normalizadas
"""

import logging
import os

import duckdb
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)


class GymETLSilver:
    def __init__(self, db_path: str = "data/gym.duckdb"):
        self.db_path = db_path
        if not os.path.exists(db_path):
            raise FileNotFoundError(
                f"No se encontró la base de datos: {db_path}. "
                "Ejecutá primero el ETL Bronze."
            )
        self.conn = duckdb.connect(db_path)
        self._validate_bronze_tables()
        self._create_silver_tables()

    def _validate_bronze_tables(self):
        """Verifica que existan datos en Bronze antes de transformar"""
        tables = self.conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name IN ('bronze_sesiones', 'bronze_series')"
        ).fetchall()
        table_names = {t[0] for t in tables}
        missing = {'bronze_sesiones', 'bronze_series'} - table_names
        if missing:
            raise ValueError(
                f"Faltan tablas Bronze: {missing}. "
                "Ejecutá primero el ETL Bronze."
            )
    
    def _create_silver_tables(self):
        """Crear tablas Silver si no existen"""
        
        # Dimensión de Ejercicios
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS silver_dim_ejercicios (
                ejercicio_id INTEGER PRIMARY KEY,
                nombre_ejercicio VARCHAR,
                tipo_ejercicio VARCHAR,
                url_video VARCHAR,
                fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Dimensión de Fecha
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS silver_dim_fecha (
                fecha_id INTEGER PRIMARY KEY,
                fecha DATE,
                anio INTEGER,
                mes INTEGER,
                dia INTEGER,
                dia_semana INTEGER,
                nombre_dia_semana VARCHAR,
                semana_anio INTEGER,
                fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Dimensión de Plan (Meso + Micro)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS silver_dim_plan (
                plan_id INTEGER PRIMARY KEY,
                sheet_name VARCHAR,
                mesociclo VARCHAR,
                numero_dia INTEGER,
                nombre_dia VARCHAR,
                microciclo VARCHAR,
                numero_microciclo INTEGER,
                fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla de hechos de Series (limpia)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS silver_fact_series (
                serie_id INTEGER PRIMARY KEY,
                sesion_id INTEGER,
                ejercicio_id INTEGER,
                fecha_id INTEGER,
                plan_id INTEGER,
                grupo_ejercicio VARCHAR(5),
                numero_serie INTEGER,
                repeticiones_ejecutadas INTEGER,
                repeticiones_texto VARCHAR,
                carga_kg DECIMAL(6,2),
                rir_rpe INTEGER,
                tipo_metrica VARCHAR(10),
                dosis_prescrita VARCHAR,
                notas VARCHAR,
                fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        logger.info("Tablas Silver creadas")
    
    def transform_bronze_to_silver(self):
        """Transforma datos de Bronze a Silver"""
        
        logger.info("Iniciando transformación Bronze -> Silver")

        self.conn.execute("BEGIN TRANSACTION")
        try:
            logger.info("Paso 1/4: Creando dimensión de ejercicios...")
            self._create_dim_ejercicios()

            logger.info("Paso 2/4: Creando dimensión de fecha...")
            self._create_dim_fecha()

            logger.info("Paso 3/4: Creando dimensión de plan...")
            self._create_dim_plan()

            logger.info("Paso 4/4: Creando tabla de hechos de series...")
            self._create_fact_series()

            self.conn.execute("COMMIT")
            logger.info("Transformación completada")
        except Exception:
            self.conn.execute("ROLLBACK")
            logger.exception("Error en transformación, se hizo rollback")
            raise
    
    def _create_dim_ejercicios(self):
        """Crear dimensión de ejercicios desde Bronze, deduplicando por nombre"""

        self.conn.execute("DELETE FROM silver_dim_ejercicios")

        # Deduplicar por nombre_ejercicio, tomando el primer tipo/url no nulo
        self.conn.execute("""
            INSERT INTO silver_dim_ejercicios (ejercicio_id, nombre_ejercicio, tipo_ejercicio, url_video)
            SELECT
                ROW_NUMBER() OVER (ORDER BY nombre_ejercicio) as ejercicio_id,
                nombre_ejercicio,
                tipo_ejercicio,
                url_video
            FROM (
                SELECT
                    TRIM(nombre_ejercicio) as nombre_ejercicio,
                    FIRST_VALUE(tipo_ejercicio IGNORE NULLS) OVER (
                        PARTITION BY TRIM(nombre_ejercicio)
                        ORDER BY id
                    ) as tipo_ejercicio,
                    FIRST_VALUE(url_ejercicio IGNORE NULLS) OVER (
                        PARTITION BY TRIM(nombre_ejercicio)
                        ORDER BY id
                    ) as url_video,
                    ROW_NUMBER() OVER (
                        PARTITION BY TRIM(nombre_ejercicio)
                        ORDER BY id
                    ) as rn
                FROM bronze_series
                WHERE nombre_ejercicio IS NOT NULL
                  AND TRIM(nombre_ejercicio) != ''
                  AND TRIM(nombre_ejercicio) != 'nan'
            ) dedup
            WHERE rn = 1
        """)
        
        count = self.conn.execute("SELECT COUNT(*) FROM silver_dim_ejercicios").fetchone()[0]
        logger.info("%d ejercicios únicos cargados", count)
    
    def _create_dim_fecha(self):
        """Crear dimensión de fecha desde Bronze"""
        
        # Limpiar tabla
        self.conn.execute("DELETE FROM silver_dim_fecha")
        
        # Insertar fechas únicas
        self.conn.execute("""
            INSERT INTO silver_dim_fecha (
                fecha_id, fecha, anio, mes, dia, dia_semana, 
                nombre_dia_semana, semana_anio
            )
            SELECT 
                ROW_NUMBER() OVER (ORDER BY fecha) as fecha_id,
                fecha,
                EXTRACT(YEAR FROM fecha) as anio,
                EXTRACT(MONTH FROM fecha) as mes,
                EXTRACT(DAY FROM fecha) as dia,
                EXTRACT(DOW FROM fecha) as dia_semana,
                CASE EXTRACT(DOW FROM fecha)
                    WHEN 0 THEN 'Domingo'
                    WHEN 1 THEN 'Lunes'
                    WHEN 2 THEN 'Martes'
                    WHEN 3 THEN 'Miércoles'
                    WHEN 4 THEN 'Jueves'
                    WHEN 5 THEN 'Viernes'
                    WHEN 6 THEN 'Sábado'
                END as nombre_dia_semana,
                EXTRACT(WEEK FROM fecha) as semana_anio
            FROM (
                SELECT DISTINCT fecha
                FROM bronze_sesiones
                WHERE fecha IS NOT NULL
            ) fechas_unicas
        """)
        
        count = self.conn.execute("SELECT COUNT(*) FROM silver_dim_fecha").fetchone()[0]
        logger.info("%d fechas únicas cargadas", count)
    
    def _create_dim_plan(self):
        """Crear dimensión de plan desde Bronze"""
        
        # Limpiar tabla
        self.conn.execute("DELETE FROM silver_dim_plan")
        
        # Insertar planes únicos (cada combinación de día y microciclo)
        self.conn.execute("""
            INSERT INTO silver_dim_plan (
                plan_id, sheet_name, mesociclo, numero_dia, nombre_dia, 
                microciclo, numero_microciclo
            )
            SELECT 
                ROW_NUMBER() OVER (ORDER BY sheet_name, numero_dia, numero_microciclo) as plan_id,
                sheet_name,
                sheet_name as mesociclo,
                numero_dia,
                nombre_dia,
                microciclo,
                numero_microciclo
            FROM (
                SELECT DISTINCT 
                    sheet_name,
                    numero_dia,
                    nombre_dia,
                    microciclo,
                    numero_microciclo
                FROM bronze_sesiones
            ) planes_unicos
        """)
        
        count = self.conn.execute("SELECT COUNT(*) FROM silver_dim_plan").fetchone()[0]
        logger.info("%d planes únicos cargados", count)
    
    def _create_fact_series(self):
        """Crear tabla de hechos de series desde Bronze"""
        
        # Limpiar tabla
        self.conn.execute("DELETE FROM silver_fact_series")
        
        # Insertar series con FKs a dimensiones
        self.conn.execute("""
            INSERT INTO silver_fact_series (
                serie_id, sesion_id, ejercicio_id, fecha_id, plan_id,
                grupo_ejercicio, numero_serie, repeticiones_ejecutadas, 
                repeticiones_texto, carga_kg, rir_rpe, tipo_metrica,
                dosis_prescrita, notas
            )
            SELECT 
                ROW_NUMBER() OVER (ORDER BY bs.id) as serie_id,
                bs.sesion_id,
                ej.ejercicio_id,
                f.fecha_id,
                p.plan_id,
                bs.grupo_ejercicio,
                bs.numero_serie,
                -- Intentar convertir repeticiones a entero, si falla usar NULL
                TRY_CAST(bs.repeticiones AS INTEGER) as repeticiones_ejecutadas,
                bs.repeticiones as repeticiones_texto,
                TRY_CAST(bs.carga_kg AS DECIMAL(6,2)) as carga_kg,
                TRY_CAST(bs.rir_rpe AS INTEGER) as rir_rpe,
                bs.tipo_metrica,
                bs.dosis as dosis_prescrita,
                bs.notas_ejercicio as notas
            FROM bronze_series bs
            -- Join con ejercicios
            LEFT JOIN silver_dim_ejercicios ej 
                ON TRIM(bs.nombre_ejercicio) = ej.nombre_ejercicio
            -- Join con sesiones para obtener fecha
            LEFT JOIN bronze_sesiones ses 
                ON bs.sesion_id = ses.id
            -- Join con fecha
            LEFT JOIN silver_dim_fecha f 
                ON ses.fecha = f.fecha
            -- Join con plan
            LEFT JOIN silver_dim_plan p 
                ON bs.sheet_name = p.sheet_name
                AND bs.numero_dia = p.numero_dia
                AND bs.numero_microciclo = p.numero_microciclo
            WHERE bs.nombre_ejercicio IS NOT NULL
              AND TRIM(bs.nombre_ejercicio) != ''
              AND TRIM(bs.nombre_ejercicio) != 'nan'
        """)
        
        count = self.conn.execute("SELECT COUNT(*) FROM silver_fact_series").fetchone()[0]
        logger.info("%d series cargadas en fact table", count)
    
    def verify_silver_data(self):
        """Verificar datos en Silver"""

        logger.info("Verificación de datos Silver")

        ej = self.conn.execute("SELECT COUNT(*) FROM silver_dim_ejercicios").fetchone()[0]
        logger.info("Dimensión Ejercicios: %d registros", ej)

        f = self.conn.execute("SELECT COUNT(*) FROM silver_dim_fecha").fetchone()[0]
        logger.info("Dimensión Fecha: %d registros", f)

        rango = self.conn.execute(
            "SELECT MIN(fecha) as min_fecha, MAX(fecha) as max_fecha FROM silver_dim_fecha"
        ).fetchdf()
        logger.info("Rango de fechas:\n%s", rango)

        p = self.conn.execute("SELECT COUNT(*) FROM silver_dim_plan").fetchone()[0]
        logger.info("Dimensión Plan: %d registros", p)

        s = self.conn.execute("SELECT COUNT(*) FROM silver_fact_series").fetchone()[0]
        logger.info("Tabla de Hechos: %d series", s)

        calidad = self.conn.execute("""
            SELECT
                COUNT(*) as total_series,
                SUM(CASE WHEN ejercicio_id IS NULL THEN 1 ELSE 0 END) as sin_ejercicio,
                SUM(CASE WHEN fecha_id IS NULL THEN 1 ELSE 0 END) as sin_fecha,
                SUM(CASE WHEN plan_id IS NULL THEN 1 ELSE 0 END) as sin_plan,
                SUM(CASE WHEN carga_kg IS NULL THEN 1 ELSE 0 END) as sin_carga,
                SUM(CASE WHEN rir_rpe IS NULL THEN 1 ELSE 0 END) as sin_rir
            FROM silver_fact_series
        """).fetchdf()
        logger.info("Calidad de datos:\n%s", calidad)
    
    def close(self):
        """Cerrar conexión"""
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    db_path = os.path.join(PROJECT_ROOT, "data", "gym.duckdb")

    with GymETLSilver(db_path) as etl_silver:
        etl_silver.transform_bronze_to_silver()
        etl_silver.verify_silver_data()

    logger.info("ETL Silver completado!")