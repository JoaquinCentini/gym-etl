"""
ETL Bronze Layer V2 - Extracción correcta de datos
Entiende que cada HOJA tiene:
- N DÍAS (verticalmente)
- M MICROCICLOS (horizontalmente)
- Total sesiones = N × M
"""

import logging
import os

import pandas as pd
import duckdb
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class GymETLBronze:
    def __init__(self, excel_path: str, db_path: str = "data/gym.duckdb"):
        self.excel_path = excel_path
        self.db_path = db_path
        self._validate_inputs()
        self.conn = duckdb.connect(db_path)
        self._create_bronze_tables()

    def _validate_inputs(self):
        """Valida que el archivo Excel exista y tenga hojas de mesociclos"""
        if not os.path.exists(self.excel_path):
            raise FileNotFoundError(f"No se encontró el archivo Excel: {self.excel_path}")

        xl = pd.ExcelFile(self.excel_path)
        meso_sheets = [s for s in xl.sheet_names if "Meso" in s]
        if not meso_sheets:
            raise ValueError(
                f"El archivo Excel no contiene hojas de mesociclos. "
                f"Hojas encontradas: {xl.sheet_names}"
            )
        logger.info("Excel válido: %d hojas de mesociclo encontradas", len(meso_sheets))
    
    def _create_bronze_tables(self):
        """Crear tablas Bronze si no existen"""
        
        # Tabla para metadata de sesiones de entrenamiento
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS bronze_sesiones (
                id INTEGER PRIMARY KEY,
                sheet_name VARCHAR,
                numero_dia INTEGER,
                nombre_dia VARCHAR,
                microciclo VARCHAR(50),
                numero_microciclo INTEGER,
                fecha TIMESTAMP,
                hora TIME,
                prs_pre_sesion DECIMAL(3,1),
                rpe_sesion DECIMAL(3,1),
                valoracion VARCHAR,
                notas_sesion VARCHAR,
                fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla para series (datos crudos)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS bronze_series (
                id INTEGER PRIMARY KEY,
                sesion_id INTEGER,
                sheet_name VARCHAR,
                numero_dia INTEGER,
                microciclo VARCHAR(50),
                numero_microciclo INTEGER,
                grupo_ejercicio VARCHAR(5),
                tipo_ejercicio VARCHAR(100),
                nombre_ejercicio VARCHAR(500),
                url_ejercicio VARCHAR(500),
                notas_ejercicio VARCHAR(500),
                dosis VARCHAR(200),
                numero_serie INTEGER,
                repeticiones VARCHAR,
                carga_kg VARCHAR,
                rir_rpe VARCHAR,
                tipo_metrica VARCHAR(10),
                fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sesion_id) REFERENCES bronze_sesiones(id)
            )
        """)
        
        logger.info("Tablas Bronze V2 creadas")
    
    def extract_sheet(self, sheet_name: str):
        """Extrae datos de una hoja específica"""
        
        logger.info("Extrayendo datos de: %s", sheet_name)
        
        # Leer Excel sin encabezados
        df = pd.read_excel(self.excel_path, sheet_name=sheet_name, header=None)
        
        # 1. Detectar días (bloques verticales)
        dias = self._detect_dias(df)
        logger.info("Días detectados: %d", len(dias))
        for dia in dias:
            logger.debug("  - %s (fila %d)", dia['nombre'], dia['fila_inicio'])
        
        # 2. Detectar microciclos (columnas horizontales)
        microciclos = self._detect_microciclos(df)
        logger.info("Microciclos detectados: %d", len(microciclos))
        for micro in microciclos:
            logger.debug("  - %s (columna %d)", micro['nombre'], micro['col_inicio'])
        
        # 3. Extraer sesiones (combinación día × microciclo)
        sesiones_data = []
        series_data = []
        
        for dia in dias:
            for micro in microciclos:
                # Extraer metadata de esta sesión específica
                sesion = self._extract_sesion_metadata(df, dia, micro, sheet_name)
                
                # Extraer series de esta sesión
                series = self._extract_series_from_dia_micro(df, dia, micro, sheet_name)
                
                if sesion and len(series) > 0:
                    sesiones_data.append(sesion)
                    series_data.extend(series)
        
        logger.info("Total sesiones extraídas: %d", len(sesiones_data))
        logger.info("Total series extraídas: %d", len(series_data))

        # 4. Eliminar datos previos de esta hoja (idempotencia)
        self._delete_sheet_data(sheet_name)

        # 5. Guardar en DuckDB
        self._save_to_bronze(sesiones_data, series_data)
        
        logger.info("Extracción completada para %s", sheet_name)
    
    def _detect_dias(self, df: pd.DataFrame) -> List[Dict]:
        """Detecta los bloques de DÍAS en la columna 0"""
        
        dias = []
        
        for idx in range(len(df)):
            val = df.iloc[idx, 0]
            
            if pd.notna(val) and 'DÍA' in str(val).upper():
                # Extraer número del día
                nombre = str(val).strip()
                try:
                    numero = int(nombre.split()[-1])
                except:
                    numero = len(dias) + 1
                
                dias.append({
                    'nombre': nombre,
                    'numero': numero,
                    'fila_inicio': idx
                })
        
        # Calcular fila_fin de cada día
        for i in range(len(dias)):
            if i < len(dias) - 1:
                dias[i]['fila_fin'] = dias[i + 1]['fila_inicio'] - 1
            else:
                dias[i]['fila_fin'] = min(dias[i]['fila_inicio'] + 60, len(df) - 1)
        
        return dias
    
    def _detect_microciclos(self, df: pd.DataFrame) -> List[Dict]:
        """Detecta microciclos buscando 'MICROCICLO' en las primeras 30 filas"""

        microciclos = []
        fila_micros = None

        # Buscar en qué fila aparecen los encabezados de MICROCICLO
        for fila in range(min(30, len(df))):
            for col in range(7, min(100, len(df.columns))):
                val = df.iloc[fila, col]
                if pd.notna(val) and 'MICROCICLO' in str(val).upper():
                    fila_micros = fila
                    break
            if fila_micros is not None:
                break

        if fila_micros is None:
            logger.warning("No se encontraron encabezados de MICROCICLO")
            return microciclos

        logger.debug("Encabezados de MICROCICLO encontrados en fila %d", fila_micros)

        # Recorrer esa fila buscando todos los microciclos
        for col in range(7, min(100, len(df.columns))):
            val = df.iloc[fila_micros, col]

            if pd.notna(val) and 'MICROCICLO' in str(val).upper():
                micro_str = str(val)
                try:
                    numero = int(micro_str.split()[-1])
                except ValueError:
                    numero = len(microciclos) + 1

                microciclos.append({
                    'nombre': micro_str,
                    'numero': numero,
                    'col_inicio': col
                })

        return microciclos
    
    def _find_label_row(self, df: pd.DataFrame, fila_inicio: int, fila_fin: int, label: str) -> int | None:
        """Busca la fila que contiene una etiqueta en las columnas 1-10 del bloque"""
        for fila in range(fila_inicio, min(fila_fin, len(df))):
            for col in range(1, min(11, len(df.columns))):
                val = df.iloc[fila, col]
                if pd.notna(val) and label in str(val).upper():
                    return fila
        return None

    def _safe_cell(self, df: pd.DataFrame, fila: int, col: int):
        """Lee una celda de forma segura, retornando None si está fuera de rango o es NaN/error"""
        if fila < 0 or fila >= len(df) or col < 0 or col >= len(df.columns):
            return None
        val = df.iloc[fila, col]
        if pd.isna(val):
            return None
        # Limpiar errores de Excel (#REF!, #N/A, etc.)
        if isinstance(val, str) and '#' in val:
            return None
        return val

    def _extract_sesion_metadata(self, df: pd.DataFrame, dia: Dict, micro: Dict, sheet_name: str) -> Dict:
        """Extrae metadata de una sesión específica (día × microciclo)"""

        fila_inicio = dia['fila_inicio']
        fila_fin = dia['fila_fin']
        meta_limit = min(fila_inicio + 15, fila_fin)

        fecha = None
        hora = None
        prs = None
        rpe = None

        # Buscar fila de FECHA dinámicamente
        fila_fecha = self._find_label_row(df, fila_inicio, meta_limit, 'FECHA')
        if fila_fecha is not None:
            fecha = self._safe_cell(df, fila_fecha, micro['col_inicio'] + 2)
            hora = self._safe_cell(df, fila_fecha, micro['col_inicio'] + 4)

        # Buscar fila de PRS dinámicamente
        fila_prs = self._find_label_row(df, fila_inicio, meta_limit, 'PRS')
        if fila_prs is not None:
            prs = self._safe_cell(df, fila_prs, micro['col_inicio'] - 1)

        # Buscar fila de RPE dinámicamente
        fila_rpe = self._find_label_row(df, fila_inicio, meta_limit, 'RPE')
        if fila_rpe is not None:
            rpe = self._safe_cell(df, fila_rpe, micro['col_inicio'] - 1)

        return {
            'id': None,
            'sheet_name': sheet_name,
            'numero_dia': dia['numero'],
            'nombre_dia': dia['nombre'],
            'microciclo': micro['nombre'],
            'numero_microciclo': micro['numero'],
            'fecha': fecha,
            'hora': hora,
            'prs_pre_sesion': prs,
            'rpe_sesion': rpe,
            'valoracion': None,
            'notas_sesion': None
        }
    
    def _find_first_exercise_row(self, df: pd.DataFrame, dia: Dict) -> int:
        """Busca la fila del primer grupo de ejercicio (A-F) dentro de un bloque de día"""
        EXERCISE_GROUPS = {'A', 'B', 'C', 'D', 'E', 'F'}
        for fila in range(dia['fila_inicio'], dia['fila_fin'] + 1):
            val = df.iloc[fila, 0]
            if pd.notna(val) and str(val).strip() in EXERCISE_GROUPS:
                return fila
        # Fallback al offset original si no se encuentra
        logger.warning(
            "No se encontró grupo de ejercicio en %s, usando offset +15",
            dia['nombre'],
        )
        return dia['fila_inicio'] + 15

    def _extract_series_from_dia_micro(self, df: pd.DataFrame, dia: Dict, micro: Dict, sheet_name: str) -> List[Dict]:
        """Extrae series de un día específico y microciclo específico"""

        series = []

        fila_inicio = self._find_first_exercise_row(df, dia)
        fila_fin = dia['fila_fin']

        fila_actual = fila_inicio
        
        while fila_actual < fila_fin - 3:
            grupo = df.iloc[fila_actual, 0]
            
            # Verificar si es un ejercicio válido
            if pd.notna(grupo) and str(grupo) in ['A', 'B', 'C', 'D', 'E', 'F']:
                
                # Extraer info del ejercicio
                tipo_ejercicio = df.iloc[fila_actual, 1]
                nombre_completo = str(df.iloc[fila_actual + 1, 1])
                notas_ejercicio = df.iloc[fila_actual + 2, 1]
                
                # Separar nombre y URL
                if 'http' in nombre_completo:
                    partes = nombre_completo.split('http')
                    nombre_ejercicio = partes[0].strip()
                    url_ejercicio = 'http' + partes[1] if len(partes) > 1 else None
                else:
                    nombre_ejercicio = nombre_completo
                    url_ejercicio = None
                
                # Extraer dosis
                col_inicio = micro['col_inicio']
                dosis = df.iloc[fila_actual, col_inicio]
                
                # Procesar series S1-S5 de este microciclo
                for num_serie in range(1, 6):
                    col_serie = col_inicio + (num_serie - 1)
                    
                    if col_serie >= len(df.columns):
                        break
                    
                    reps = df.iloc[fila_actual + 1, col_serie]
                    carga = df.iloc[fila_actual + 2, col_serie]
                    rir = df.iloc[fila_actual + 3, col_serie]
                    
                    # Solo guardar si hay datos
                    if pd.notna(reps):
                        serie_data = {
                            'id': None,
                            'sesion_id': None,  # Se asignará después
                            'sheet_name': sheet_name,
                            'numero_dia': dia['numero'],
                            'microciclo': micro['nombre'],
                            'numero_microciclo': micro['numero'],
                            'grupo_ejercicio': grupo,
                            'tipo_ejercicio': tipo_ejercicio if pd.notna(tipo_ejercicio) else None,
                            'nombre_ejercicio': nombre_ejercicio,
                            'url_ejercicio': url_ejercicio,
                            'notas_ejercicio': notas_ejercicio if pd.notna(notas_ejercicio) else None,
                            'dosis': dosis if pd.notna(dosis) else None,
                            'numero_serie': num_serie,
                            'repeticiones': str(reps) if pd.notna(reps) else None,
                            'carga_kg': str(carga) if pd.notna(carga) else None,
                            'rir_rpe': str(rir) if pd.notna(rir) else None,
                            'tipo_metrica': 'RIR'
                        }
                        series.append(serie_data)
                
                fila_actual += 4  # Cada ejercicio ocupa 4 filas
            else:
                fila_actual += 1
        
        return series
    
    def _delete_sheet_data(self, sheet_name: str):
        """Elimina datos previos de una hoja para garantizar idempotencia"""
        # Eliminar series primero (FK a sesiones)
        deleted_series = self.conn.execute(
            "DELETE FROM bronze_series WHERE sheet_name = ? RETURNING id",
            [sheet_name]
        ).fetchall()
        deleted_sesiones = self.conn.execute(
            "DELETE FROM bronze_sesiones WHERE sheet_name = ? RETURNING id",
            [sheet_name]
        ).fetchall()
        if deleted_series or deleted_sesiones:
            logger.info(
                "Datos previos de '%s' eliminados: %d sesiones, %d series",
                sheet_name, len(deleted_sesiones), len(deleted_series),
            )

    def _save_to_bronze(self, sesiones_data: List[Dict], series_data: List[Dict]):
        """Guarda datos en las tablas Bronze"""

        sesion_map = {}

        # Obtener max ID una sola vez
        sesion_id = self.conn.execute(
            "SELECT COALESCE(MAX(id), 0) FROM bronze_sesiones"
        ).fetchone()[0]

        for sesion in sesiones_data:
            sesion_id += 1
            sesion['id'] = sesion_id

            key = (sesion['numero_dia'], sesion['numero_microciclo'])
            sesion_map[key] = sesion['id']

        # Insertar todas las sesiones en batch
        if sesiones_data:
            df_sesiones = pd.DataFrame(sesiones_data)
            self.conn.execute("""
                INSERT INTO bronze_sesiones
                (id, sheet_name, numero_dia, nombre_dia, microciclo, numero_microciclo,
                 fecha, hora, prs_pre_sesion, rpe_sesion, valoracion, notas_sesion)
                SELECT id, sheet_name, numero_dia, nombre_dia, microciclo, numero_microciclo,
                       fecha, hora, prs_pre_sesion, rpe_sesion, valoracion, notas_sesion
                FROM df_sesiones
            """)

        # Asignar IDs a series
        serie_id = self.conn.execute(
            "SELECT COALESCE(MAX(id), 0) FROM bronze_series"
        ).fetchone()[0]

        for serie in series_data:
            serie_id += 1
            serie['id'] = serie_id
            key = (serie['numero_dia'], serie['numero_microciclo'])
            serie['sesion_id'] = sesion_map.get(key)

        # Insertar todas las series en batch
        if series_data:
            df_series = pd.DataFrame(series_data)
            self.conn.execute("""
                INSERT INTO bronze_series
                (id, sesion_id, sheet_name, numero_dia, microciclo, numero_microciclo,
                 grupo_ejercicio, tipo_ejercicio, nombre_ejercicio, url_ejercicio,
                 notas_ejercicio, dosis, numero_serie, repeticiones, carga_kg, rir_rpe, tipo_metrica)
                SELECT id, sesion_id, sheet_name, numero_dia, microciclo, numero_microciclo,
                       grupo_ejercicio, tipo_ejercicio, nombre_ejercicio, url_ejercicio,
                       notas_ejercicio, dosis, numero_serie, repeticiones, carga_kg, rir_rpe, tipo_metrica
                FROM df_series
            """)

        logger.info("Guardados: %d sesiones, %d series", len(sesiones_data), len(series_data))
    
    def close(self):
        """Cerrar conexión a DuckDB"""
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
    excel_path = os.path.join(PROJECT_ROOT, "data", "raw", "Centini Joaquín.xlsx")
    db_path = os.path.join(PROJECT_ROOT, "data", "gym.duckdb")

    with GymETLBronze(excel_path, db_path) as etl:
        etl.extract_sheet("Meso 2")

        logger.info("Sesiones cargadas:")
        result = etl.conn.execute(
            "SELECT * FROM bronze_sesiones ORDER BY numero_dia, numero_microciclo"
        ).fetchdf()
        logger.info("\n%s", result)

        logger.info("Primeras 20 series cargadas:")
        result = etl.conn.execute("""
            SELECT sesion_id, numero_dia, numero_microciclo, nombre_ejercicio,
                   numero_serie, repeticiones, carga_kg, rir_rpe
            FROM bronze_series
            ORDER BY numero_dia, numero_microciclo, id
            LIMIT 20
        """).fetchdf()
        logger.info("\n%s", result)

        logger.info("Resumen:")
        result = etl.conn.execute("""
            SELECT
                COUNT(DISTINCT sesion_id) as total_sesiones,
                COUNT(*) as total_series,
                COUNT(DISTINCT nombre_ejercicio) as ejercicios_unicos
            FROM bronze_series
        """).fetchdf()
        logger.info("\n%s", result)

    logger.info("ETL Bronze V2 completado!")