"""
ETL Bronze Layer V2 - Extracción correcta de datos
Entiende que cada HOJA tiene:
- N DÍAS (verticalmente)
- M MICROCICLOS (horizontalmente)
- Total sesiones = N × M
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
        
        print("✅ Tablas Bronze V2 creadas")
    
    def extract_sheet(self, sheet_name: str):
        """Extrae datos de una hoja específica"""
        
        print(f"\n{'='*100}")
        print(f"Extrayendo datos de: {sheet_name}")
        print(f"{'='*100}")
        
        # Leer Excel sin encabezados
        df = pd.read_excel(self.excel_path, sheet_name=sheet_name, header=None)
        
        # 1. Detectar días (bloques verticales)
        dias = self._detect_dias(df)
        print(f"\n🗓️  Días detectados: {len(dias)}")
        for dia in dias:
            print(f"  - {dia['nombre']} (fila {dia['fila_inicio']})")
        
        # 2. Detectar microciclos (columnas horizontales)
        microciclos = self._detect_microciclos(df)
        print(f"\n📊 Microciclos detectados: {len(microciclos)}")
        for micro in microciclos:
            print(f"  - {micro['nombre']} (columna {micro['col_inicio']})")
        
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
        
        print(f"\n📈 Total sesiones extraídas: {len(sesiones_data)}")
        print(f"📈 Total series extraídas: {len(series_data)}")
        
        # 4. Guardar en DuckDB
        self._save_to_bronze(sesiones_data, series_data)
        
        print(f"\n✅ Extracción completada")
    
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
        """Detecta microciclos dinámicamente de la fila 21"""
        
        microciclos = []
        fila_micros = 21
        
        for col in range(7, 100):
            if col >= len(df.columns):
                break
            
            val = df.iloc[fila_micros, col]
            
            if pd.notna(val) and 'MICROCICLO' in str(val):
                micro_str = str(val)
                try:
                    numero = int(micro_str.split()[-1])
                except:
                    numero = len(microciclos) + 1
                
                microciclos.append({
                    'nombre': micro_str,
                    'numero': numero,
                    'col_inicio': col
                })
        
        return microciclos
    
    def _extract_sesion_metadata(self, df: pd.DataFrame, dia: Dict, micro: Dict, sheet_name: str) -> Dict:
        """Extrae metadata de una sesión específica (día × microciclo)"""
        
        # Buscar metadata dentro del bloque del día
        fila_inicio = dia['fila_inicio']
        fila_fin = dia['fila_fin']
        
        # La metadata está aproximadamente 2-6 filas después del encabezado del día
        fecha = None
        hora = None
        prs = None
        rpe = None
        
        # Buscar "FECHA y HO" en este bloque, en la columna del microciclo
        for fila in range(fila_inicio, min(fila_inicio + 15, fila_fin)):
            val = df.iloc[fila, 7]  # Columna 7 suele tener "FECHA y HO"
            
            if pd.notna(val) and 'FECHA' in str(val):
                # La fecha está en la columna del microciclo + 2
                col_fecha = micro['col_inicio'] + 2
                if col_fecha < len(df.columns):
                    fecha = df.iloc[fila, col_fecha]
                    
                    # Hora puede estar en la siguiente columna
                    col_hora = micro['col_inicio'] + 4
                    if col_hora < len(df.columns):
                        hora = df.iloc[fila, col_hora]
                
                # PRS está 2 filas abajo, en la columna base del microciclo - 1
                if fila + 2 < len(df):
                    col_prs = micro['col_inicio'] - 1
                    if col_prs >= 0:
                        prs = df.iloc[fila + 2, col_prs]
                
                # RPE está 4 filas abajo
                if fila + 4 < len(df):
                    col_rpe = micro['col_inicio'] - 1
                    if col_rpe >= 0:
                        rpe = df.iloc[fila + 4, col_rpe]
                
                break
        
        # Limpiar valores de error de Excel
        if prs and isinstance(prs, str) and '#' in str(prs):
            prs = None
        if rpe and isinstance(rpe, str) and '#' in str(rpe):
            rpe = None
        
        return {
            'id': None,
            'sheet_name': sheet_name,
            'numero_dia': dia['numero'],
            'nombre_dia': dia['nombre'],
            'microciclo': micro['nombre'],
            'numero_microciclo': micro['numero'],
            'fecha': fecha if pd.notna(fecha) else None,
            'hora': hora if pd.notna(hora) else None,
            'prs_pre_sesion': prs if pd.notna(prs) else None,
            'rpe_sesion': rpe if pd.notna(rpe) else None,
            'valoracion': None,
            'notas_sesion': None
        }
    
    def _extract_series_from_dia_micro(self, df: pd.DataFrame, dia: Dict, micro: Dict, sheet_name: str) -> List[Dict]:
        """Extrae series de un día específico y microciclo específico"""
        
        series = []
        
        # Buscar ejercicios en el bloque del día
        fila_inicio = dia['fila_inicio'] + 15  # Los ejercicios empiezan ~15 filas después
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
    
    def _save_to_bronze(self, sesiones_data: List[Dict], series_data: List[Dict]):
        """Guarda datos en las tablas Bronze"""
        
        # Crear mapeo de (numero_dia, numero_microciclo) -> sesion_id
        sesion_map = {}
        
        # Guardar sesiones
        for sesion in sesiones_data:
            max_id = self.conn.execute("SELECT COALESCE(MAX(id), 0) FROM bronze_sesiones").fetchone()[0]
            sesion['id'] = max_id + 1
            
            # Guardar en el mapa
            key = (sesion['numero_dia'], sesion['numero_microciclo'])
            sesion_map[key] = sesion['id']
            
            df_sesion = pd.DataFrame([sesion])
            self.conn.execute("""
                INSERT INTO bronze_sesiones 
                (id, sheet_name, numero_dia, nombre_dia, microciclo, numero_microciclo, 
                 fecha, hora, prs_pre_sesion, rpe_sesion, valoracion, notas_sesion)
                SELECT id, sheet_name, numero_dia, nombre_dia, microciclo, numero_microciclo,
                       fecha, hora, prs_pre_sesion, rpe_sesion, valoracion, notas_sesion
                FROM df_sesion
            """)
        
        # Asignar sesion_id a las series y guardar
        serie_id = self.conn.execute("SELECT COALESCE(MAX(id), 0) FROM bronze_series").fetchone()[0]
        
        for serie in series_data:
            serie_id += 1
            serie['id'] = serie_id
            
            # Asignar sesion_id basado en numero_dia y numero_microciclo
            key = (serie['numero_dia'], serie['numero_microciclo'])
            serie['sesion_id'] = sesion_map.get(key)
        
        # Insertar todas las series
        if len(series_data) > 0:
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
        
        print(f"  💾 Guardados: {len(sesiones_data)} sesiones, {len(series_data)} series")
    
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
    print("\n" + "="*100)
    print("VERIFICACIÓN DE DATOS CARGADOS")
    print("="*100)
    
    print("\n📅 Sesiones cargadas:")
    result = etl.conn.execute("SELECT * FROM bronze_sesiones ORDER BY numero_dia, numero_microciclo").fetchdf()
    print(result)
    
    print("\n💪 Primeras 20 series cargadas:")
    result = etl.conn.execute("""
        SELECT sesion_id, numero_dia, numero_microciclo, nombre_ejercicio, numero_serie, repeticiones, carga_kg, rir_rpe
        FROM bronze_series 
        ORDER BY numero_dia, numero_microciclo, id
        LIMIT 20
    """).fetchdf()
    print(result)
    
    print("\n📊 Resumen:")
    result = etl.conn.execute("""
        SELECT 
            COUNT(DISTINCT sesion_id) as total_sesiones,
            COUNT(*) as total_series,
            COUNT(DISTINCT nombre_ejercicio) as ejercicios_unicos
        FROM bronze_series
    """).fetchdf()
    print(result)
    
    etl.close()
    print("\n✅ ETL Bronze V2 completado!")