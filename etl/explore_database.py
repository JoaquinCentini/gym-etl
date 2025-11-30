"""
Script para explorar los datos cargados en la base de datos DuckDB V2
"""

import duckdb
import pandas as pd

# Conectar a la base de datos
conn = duckdb.connect(r"data/gym.duckdb")

print("="*100)
print("EXPLORACIÓN DE LA BASE DE DATOS GYM V2")
print("="*100)

# 1. Ver todas las tablas
print("\n📋 TABLAS DISPONIBLES:")
print("-"*100)
tables = conn.execute("SHOW TABLES").fetchdf()
print(tables)

# 2. Estructura de la tabla bronze_sesiones
print("\n\n📅 ESTRUCTURA DE bronze_sesiones:")
print("-"*100)
schema_sesiones = conn.execute("DESCRIBE bronze_sesiones").fetchdf()
print(schema_sesiones)

print("\n📊 TODAS LAS SESIONES CARGADAS:")
print("-"*100)
sesiones = conn.execute("""
    SELECT id, numero_dia, nombre_dia, numero_microciclo, microciclo, fecha, hora, prs_pre_sesion, rpe_sesion
    FROM bronze_sesiones 
    ORDER BY numero_dia, numero_microciclo
""").fetchdf()
print(sesiones.to_string())

# 3. Estructura de la tabla bronze_series
print("\n\n💪 ESTRUCTURA DE bronze_series:")
print("-"*100)
schema_series = conn.execute("DESCRIBE bronze_series").fetchdf()
print(schema_series)

# 4. Resumen general
print("\n\n📊 RESUMEN GENERAL:")
print("-"*100)

resumen = conn.execute("""
    SELECT 
        COUNT(DISTINCT numero_dia) as total_dias,
        COUNT(DISTINCT numero_microciclo) as total_microciclos,
        COUNT(DISTINCT sesion_id) as total_sesiones,
        COUNT(*) as total_series,
        COUNT(DISTINCT nombre_ejercicio) as ejercicios_unicos
    FROM bronze_series
""").fetchdf()
print(resumen)

# 5. Sesiones por día
print("\n\n📅 SESIONES POR DÍA:")
print("-"*100)
por_dia = conn.execute("""
    SELECT 
        ses.numero_dia,
        ses.nombre_dia,
        COUNT(DISTINCT ses.numero_microciclo) as microciclos,
        COUNT(DISTINCT ses.id) as total_sesiones
    FROM bronze_sesiones ses
    GROUP BY ses.numero_dia, ses.nombre_dia
    ORDER BY ses.numero_dia
""").fetchdf()
print(por_dia)

# 6. Series por microciclo
print("\n\n📊 SERIES POR MICROCICLO:")
print("-"*100)
por_micro = conn.execute("""
    SELECT 
        numero_microciclo,
        microciclo,
        COUNT(*) as total_series,
        COUNT(DISTINCT nombre_ejercicio) as ejercicios_distintos,
        COUNT(DISTINCT sesion_id) as sesiones
    FROM bronze_series
    GROUP BY numero_microciclo, microciclo
    ORDER BY numero_microciclo
""").fetchdf()
print(por_micro)

# 7. Ejercicios únicos
print("\n\n🏋️ EJERCICIOS ÚNICOS:")
print("-"*100)
ejercicios = conn.execute("""
    SELECT 
        nombre_ejercicio,
        tipo_ejercicio,
        COUNT(*) as veces_realizado,
        COUNT(DISTINCT sesion_id) as en_sesiones
    FROM bronze_series
    GROUP BY nombre_ejercicio, tipo_ejercicio
    ORDER BY veces_realizado DESC
    LIMIT 30
""").fetchdf()
print(ejercicios.to_string())

# 8. Series por grupo de ejercicio
print("\n\n📋 SERIES POR GRUPO DE EJERCICIO:")
print("-"*100)
por_grupo = conn.execute("""
    SELECT 
        grupo_ejercicio,
        COUNT(*) as total_series,
        COUNT(DISTINCT nombre_ejercicio) as ejercicios_distintos
    FROM bronze_series
    GROUP BY grupo_ejercicio
    ORDER BY grupo_ejercicio
""").fetchdf()
print(por_grupo)

# 9. Ejemplo de una sesión completa
print("\n\n📖 EJEMPLO: DÍA 1, MICROCICLO 1 (sesión completa):")
print("-"*100)
ejemplo_sesion = conn.execute("""
    SELECT 
        grupo_ejercicio,
        nombre_ejercicio,
        numero_serie,
        repeticiones,
        carga_kg,
        rir_rpe,
        dosis
    FROM bronze_series
    WHERE numero_dia = 1 AND numero_microciclo = 1
    ORDER BY id
""").fetchdf()
print(ejemplo_sesion.to_string())

# 10. Estadísticas de carga por ejercicio
print("\n\n📊 ESTADÍSTICAS DE CARGA POR EJERCICIO (Top 10):")
print("-"*100)
stats = conn.execute("""
    SELECT 
        nombre_ejercicio,
        COUNT(*) as total_series,
        ROUND(AVG(carga_kg), 1) as promedio_carga,
        ROUND(MIN(carga_kg), 1) as min_carga,
        ROUND(MAX(carga_kg), 1) as max_carga,
        ROUND(AVG(rir_rpe), 1) as promedio_rir
    FROM bronze_series
    WHERE carga_kg IS NOT NULL
    GROUP BY nombre_ejercicio
    ORDER BY promedio_carga DESC
    LIMIT 10
""").fetchdf()
print(stats.to_string())

# 11. Progresión de carga en un ejercicio específico
print("\n\n📈 PROGRESIÓN: Press banco plano (por microciclo):")
print("-"*100)
progresion = conn.execute("""
    SELECT 
        numero_microciclo,
        numero_serie,
        repeticiones,
        carga_kg,
        rir_rpe
    FROM bronze_series
    WHERE nombre_ejercicio LIKE '%Press banco%'
      AND numero_dia = 1
    ORDER BY numero_microciclo, numero_serie
""").fetchdf()
if len(progresion) > 0:
    print(progresion.to_string())
else:
    print("No se encontró este ejercicio")

# 12. Sesiones con fecha
print("\n\n📅 SESIONES CON FECHA REGISTRADA:")
print("-"*100)
con_fecha = conn.execute("""
    SELECT 
        numero_dia,
        numero_microciclo,
        fecha,
        hora,
        prs_pre_sesion,
        rpe_sesion
    FROM bronze_sesiones
    WHERE fecha IS NOT NULL
    ORDER BY fecha
""").fetchdf()
print(con_fecha.to_string())

# 13. Calidad de datos
print("\n\n⚠️ CALIDAD DE DATOS:")
print("-"*100)

# Series sin carga
sin_carga = conn.execute("""
    SELECT COUNT(*) as series_sin_carga
    FROM bronze_series
    WHERE carga_kg IS NULL
""").fetchone()[0]
print(f"Series sin carga: {sin_carga}")

# Series sin RIR
sin_rir = conn.execute("""
    SELECT COUNT(*) as series_sin_rir
    FROM bronze_series
    WHERE rir_rpe IS NULL
""").fetchone()[0]
print(f"Series sin RIR: {sin_rir}")

# Sesiones sin fecha
sesiones_sin_fecha = conn.execute("""
    SELECT COUNT(*) as sesiones_sin_fecha
    FROM bronze_sesiones
    WHERE fecha IS NULL
""").fetchone()[0]
print(f"Sesiones sin fecha: {sesiones_sin_fecha}")

# 14. Matriz día × microciclo (cuántas series hay en cada combinación)
print("\n\n🗺️ MATRIZ DÍA × MICROCICLO (cantidad de series):")
print("-"*100)
matriz = conn.execute("""
    SELECT 
        numero_dia,
        SUM(CASE WHEN numero_microciclo = 1 THEN 1 ELSE 0 END) as M1,
        SUM(CASE WHEN numero_microciclo = 2 THEN 1 ELSE 0 END) as M2,
        SUM(CASE WHEN numero_microciclo = 3 THEN 1 ELSE 0 END) as M3,
        SUM(CASE WHEN numero_microciclo = 4 THEN 1 ELSE 0 END) as M4,
        SUM(CASE WHEN numero_microciclo = 5 THEN 1 ELSE 0 END) as M5,
        SUM(CASE WHEN numero_microciclo = 6 THEN 1 ELSE 0 END) as M6,
        COUNT(*) as Total
    FROM bronze_series
    GROUP BY numero_dia
    ORDER BY numero_dia
""").fetchdf()
print(matriz)

conn.close()
print("\n\n✅ Exploración completada!")