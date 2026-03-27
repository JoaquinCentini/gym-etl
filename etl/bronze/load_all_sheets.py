"""
ETL Bronze - Cargar múltiples hojas
Procesa todas las hojas de mesociclos
"""

import sys
import os

import pandas as pd
import duckdb

# Permitir importar desde el mismo directorio del script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from etl_bronze_v2 import GymETLBronze

# Configuración — rutas relativas a la raíz del proyecto
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
excel_path = os.path.join(PROJECT_ROOT, "data", "raw", "Centini Joaquín.xlsx")
db_path = os.path.join(PROJECT_ROOT, "data", "gym.duckdb")

# Ver hojas disponibles
xl_file = pd.ExcelFile(excel_path)
print("=" * 100)
print("HOJAS DISPONIBLES EN EL EXCEL")
print("=" * 100)
for i, sheet in enumerate(xl_file.sheet_names):
    print(f"{i}: {sheet}")

# Hojas que son mesociclos (desde la 5 en adelante según tu indicación)
hojas_meso = xl_file.sheet_names[5:]  # Desde "Meso 1" en adelante

print("\n" + "=" * 100)
print(f"HOJAS A PROCESAR: {len(hojas_meso)}")
print("=" * 100)
for hoja in hojas_meso:
    print(f"  - {hoja}")

# Preguntar confirmación
print("\n" + "=" * 100)
limpiar = input("Limpiar tablas Bronze antes de cargar? (s/n): ")

if limpiar.lower() == 's':
    print("\nLimpiando tablas Bronze...")
    conn_temp = duckdb.connect(db_path)
    try:
        conn_temp.execute("DELETE FROM bronze_series")
        conn_temp.execute("DELETE FROM bronze_sesiones")
        print("Tablas Bronze limpiadas")
    except Exception as e:
        print(f"Error al limpiar: {e}")
    finally:
        conn_temp.close()

respuesta = input("\nProcesar todas estas hojas? (s/n): ")

if respuesta.lower() == 's':
    print("\n" + "=" * 100)
    print("INICIANDO PROCESAMIENTO")
    print("=" * 100)

    etl = GymETLBronze(excel_path, db_path)

    for i, hoja in enumerate(hojas_meso, 1):
        print(f"\n[{i}/{len(hojas_meso)}] Procesando: {hoja}")
        print("-" * 100)

        try:
            etl.extract_sheet(hoja)
            print(f"{hoja} completado")
        except Exception as e:
            print(f"Error en {hoja}: {e}")
            continue

    # Resumen final
    print("\n" + "=" * 100)
    print("RESUMEN FINAL")
    print("=" * 100)

    resumen = etl.conn.execute("""
        SELECT
            sheet_name,
            COUNT(DISTINCT id) as sesiones,
            COUNT(DISTINCT numero_dia) as dias,
            COUNT(DISTINCT numero_microciclo) as microciclos
        FROM bronze_sesiones
        GROUP BY sheet_name
        ORDER BY sheet_name
    """).fetchdf()
    print(resumen)

    print("\nTOTALES:")
    totales = etl.conn.execute("""
        SELECT
            COUNT(DISTINCT s.id) as total_sesiones,
            COUNT(*) as total_series,
            COUNT(DISTINCT ser.nombre_ejercicio) as ejercicios_unicos,
            COUNT(DISTINCT s.sheet_name) as hojas_procesadas
        FROM bronze_sesiones s
        LEFT JOIN bronze_series ser ON s.id = ser.sesion_id
    """).fetchdf()
    print(totales)

    etl.close()
    print("\nProcesamiento completo!")

else:
    print("\nCancelado por el usuario")
