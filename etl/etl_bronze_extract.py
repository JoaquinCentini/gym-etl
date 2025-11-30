"""
ETL Bronze Layer - Extracción de datos crudos desde Excel
Extrae datos de una hoja de entrenamiento y los guarda en DuckDB
"""

import pandas as pd
import duckdb
from datetime import datetime
from typing import List, Dict, Any

class GymETLBronze:
    def __init__(self, excel_path: str, db_path: str = "data/gym.duckdb"):
        self.excel_path = excel_path
        self.db_path = db_path
        self.conn = duckdb.connect(db_path)
        self._create_bronze_tables()
    
    def _create_bronze_tables(self):
        """Crear tablas Bronze si no existen"""
        
        # Tabla para metadata de días
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS bronze_dias (
                id INTEGER PRIMARY KEY,
                sheet_name VARCHAR,
                fecha TIMESTAMP,
                hora TIME,
                prs_pre_sesion DECIMAL(3,1),
                rpe_sesion DECIMAL(3,1),
                valoracion VARCHAR,
                notas_dia VARCHAR,
                fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla para series (datos crudos)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS bronze_series (
                id INTEGER PRIMARY KEY,
                dia_id INTEGER,
                sheet_name VARCHAR,
                grupo_ejercicio VARCHAR(5),
                tipo_ejercicio VARCHAR(100),
                nombre_ejercicio VARCHAR(500),
                url_ejercicio VARCHAR(500),
                notas_ejercicio VARCHAR(500),
                microciclo VARCHAR(50),
                numero_microciclo INTEGER,
                dosis VARCHAR(200),
                numero_serie INTEGER,
                repeticiones VARCHAR,
                carga_kg DECIMAL(6,2),
                rir_rpe INTEGER,
                tipo_metrica VARCHAR(10),
                fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dia_id) REFERENCES bronze_dias(id)
            )
        """)
        
        print("✅ Tablas Bronze creadas")
    
    def extract_sheet(self, sheet_name: str):
        """Extrae datos de una hoja específica"""
        
        print(f"\n{'='*80}")
        print(f"Extrayendo datos de: {sheet_name}")
        print(f"{'='*80}")
        
        # Leer Excel sin encabezados
        df = pd.read_excel(self.excel_path, sheet_name=sheet_name, header=None)
        
        # Extraer metadata del día
        dias_data = self._extract_dias_metadata(df, sheet_name)
        
        # Extraer series de ejercicios
        series_data = self._extract_series_data(df, sheet_name)
        
        # Guardar en DuckDB
        self._save_to_bronze(dias_data, series_data)
        
        print(f"\n✅ Extracción completada: {len(series_data)} series guardadas")
    
    def _extract_dias_metadata(self, df: pd.DataFrame, sheet_name: str) -> List[Dict]:
        """Extrae metadata de los días de entrenamiento"""
        
        dias = []
        fila_actual = 10
        dia_num = 1
        
        # Buscar todos los días en la hoja (cada ~50 filas aprox)
        while fila_actual < len(df):
            # Buscar "FECHA y HO" en la columna 7
            if pd.notna(df.iloc[fila_actual, 7]) and 'FECHA' in str(df.iloc[fila_actual, 7]):
                fecha = df.iloc[fila_actual, 9]
                hora = df.iloc[fila_actual, 11]
                
                # PRS Pre Sesión está 2 filas abajo
                prs = df.iloc[fila_actual + 2, 6] if fila_actual + 2 < len(df) else None
                
                # RPE Sesión está 4 filas abajo
                rpe = df.iloc[fila_actual + 4, 6] if fila_actual + 4 < len(df) else None
                
                dia_data = {
                    'id': None,  # Se generará automáticamente
                    'sheet_name': sheet_name,
                    'fecha': fecha,
                    'hora': hora,
                    'prs_pre_sesion': prs,
                    'rpe_sesion': rpe,
                    'valoracion': None,  # Por ahora
                    'notas_dia': None    # Por ahora
                }
                
                dias.append(dia_data)
                print(f"  📅 Día {dia_num} encontrado: {fecha}")
                dia_num += 1
            
            fila_actual += 1
            
            # Seguridad: no buscar más allá de 500 filas
            if fila_actual > 500:
                break
        
        return dias
    
    def _extract_series_data(self, df: pd.DataFrame, sheet_name: str) -> List[Dict]:
        """Extrae datos de series de ejercicios"""
        
        series = []
        
        # Buscar donde empiezan los ejercicios (después de fila 20)
        fila_inicial = 23
        
        # Definir microciclos y sus columnas
        microciclos = [
            {'nombre': 'MICROCICLO 1', 'numero': 1, 'col_inicio': 7},
            {'nombre': 'MICROCICLO 2', 'numero': 2, 'col_inicio': 13},
            {'nombre': 'MICROCICLO 3', 'numero': 3, 'col_inicio': 19},
            {'nombre': 'MICROCICLO 4', 'numero': 4, 'col_inicio': 25},
        ]
        
        fila_actual = fila_inicial
        
        while fila_actual < len(df) - 3:  # Necesitamos al menos 4 filas
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
                
                print(f"  🏋️ Ejercicio {grupo}: {nombre_ejercicio[:50]}...")
                
                # Extraer series de cada microciclo
                for micro in microciclos:
                    col_inicio = micro['col_inicio']
                    dosis = df.iloc[fila_actual, col_inicio]
                    
                    # Procesar series S1-S5
                    for num_serie in range(1, 6):
                        col_serie = col_inicio + (num_serie - 1)
                        
                        reps = df.iloc[fila_actual + 1, col_serie]
                        carga = df.iloc[fila_actual + 2, col_serie]
                        rir = df.iloc[fila_actual + 3, col_serie]
                        
                        # Solo guardar si hay datos
                        if pd.notna(reps):
                            serie_data = {
                                'id': None,
                                'dia_id': None,  # Se asignará después
                                'sheet_name': sheet_name,
                                'grupo_ejercicio': grupo,
                                'tipo_ejercicio': tipo_ejercicio,
                                'nombre_ejercicio': nombre_ejercicio,
                                'url_ejercicio': url_ejercicio,
                                'notas_ejercicio': notas_ejercicio if pd.notna(notas_ejercicio) else None,
                                'microciclo': micro['nombre'],
                                'numero_microciclo': micro['numero'],
                                'dosis': dosis if pd.notna(dosis) else None,
                                'numero_serie': num_serie,
                                'repeticiones': str(reps) if pd.notna(reps) else None,
                                'carga_kg': float(carga) if pd.notna(carga) else None,
                                'rir_rpe': int(rir) if pd.notna(rir) else None,
                                'tipo_metrica': 'RIR'  # Por ahora asumimos RIR
                            }
                            series.append(serie_data)
                
                fila_actual += 4  # Cada ejercicio ocupa 4 filas
            else:
                fila_actual += 1
            
            # Seguridad
            if fila_actual > 200:
                break
        
        return series
    
    def _save_to_bronze(self, dias_data: List[Dict], series_data: List[Dict]):
        """Guarda datos en las tablas Bronze"""
        
        # Primero guardar días
        for dia in dias_data:
            # Generar ID único
            max_id = self.conn.execute("SELECT COALESCE(MAX(id), 0) FROM bronze_dias").fetchone()[0]
            dia['id'] = max_id + 1
            
            # Limpiar valores de error de Excel
            if dia['prs_pre_sesion'] and isinstance(dia['prs_pre_sesion'], str) and '#' in str(dia['prs_pre_sesion']):
                dia['prs_pre_sesion'] = None
            if dia['rpe_sesion'] and isinstance(dia['rpe_sesion'], str) and '#' in str(dia['rpe_sesion']):
                dia['rpe_sesion'] = None
            
            # Convertir DataFrame para insertar
            df_dia = pd.DataFrame([dia])
            self.conn.execute("""
                INSERT INTO bronze_dias (id, sheet_name, fecha, hora, prs_pre_sesion, rpe_sesion, valoracion, notas_dia)
                SELECT id, sheet_name, fecha, hora, prs_pre_sesion, rpe_sesion, valoracion, notas_dia 
                FROM df_dia
            """)
            
            # Asignar dia_id a las series correspondientes
            # Por ahora, todas las series de esta sheet van al mismo día
            for serie in series_data:
                serie['dia_id'] = dia['id']
        
        # Luego guardar series
        serie_id = self.conn.execute("SELECT COALESCE(MAX(id), 0) FROM bronze_series").fetchone()[0]
        
        for serie in series_data:
            serie_id += 1
            serie['id'] = serie_id
        
        # Insertar todas las series de una vez
        df_series = pd.DataFrame(series_data)
        self.conn.execute("""
            INSERT INTO bronze_series 
            (id, dia_id, sheet_name, grupo_ejercicio, tipo_ejercicio, nombre_ejercicio, url_ejercicio, 
             notas_ejercicio, microciclo, numero_microciclo, dosis, numero_serie, repeticiones, carga_kg, rir_rpe, tipo_metrica)
            SELECT id, dia_id, sheet_name, grupo_ejercicio, tipo_ejercicio, nombre_ejercicio, url_ejercicio, 
                   notas_ejercicio, microciclo, numero_microciclo, dosis, numero_serie, repeticiones, carga_kg, rir_rpe, tipo_metrica
            FROM df_series
        """)
        
        print(f"  💾 Guardados: {len(dias_data)} días, {len(series_data)} series")
    
    def close(self):
        """Cerrar conexión a DuckDB"""
        self.conn.close()


# Ejemplo de uso
if __name__ == "__main__":
    # Configuración
    excel_path = r"data\raw\Centini Joaquín.xlsx"
    db_path = "data/gym.duckdb"
    
    # Crear ETL
    etl = GymETLBronze(excel_path, db_path)
    
    # Extraer una hoja de prueba
    etl.extract_sheet("Meso 2")
    
    # Ver resultados
    print("\n" + "="*80)
    print("VERIFICACIÓN DE DATOS CARGADOS")
    print("="*80)
    
    print("\n📅 Días cargados:")
    result = etl.conn.execute("SELECT * FROM bronze_dias").fetchdf()
    print(result)
    
    print("\n💪 Primeras 10 series cargadas:")
    result = etl.conn.execute("SELECT * FROM bronze_series LIMIT 10").fetchdf()
    print(result)
    
    print("\n📊 Resumen:")
    result = etl.conn.execute("""
        SELECT 
            COUNT(DISTINCT dia_id) as total_dias,
            COUNT(*) as total_series,
            COUNT(DISTINCT nombre_ejercicio) as ejercicios_unicos
        FROM bronze_series
    """).fetchdf()
    print(result)
    
    etl.close()
    print("\n✅ ETL Bronze completado!")