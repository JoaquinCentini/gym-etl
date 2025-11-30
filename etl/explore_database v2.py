import duckdb

conn = duckdb.connect(r"data\gym.duckdb")

print("📊 RESUMEN GENERAL:")
print(conn.execute("""
    SELECT 
        COUNT(DISTINCT sheet_name) as hojas,
        COUNT(DISTINCT id) as total_sesiones,
        COUNT(DISTINCT numero_dia) as dias_distintos,
        COUNT(DISTINCT numero_microciclo) as micros_distintos
    FROM bronze_sesiones
""").fetchdf())

print("\n📋 POR HOJA:")
print(conn.execute("""
    SELECT 
        sheet_name,
        COUNT(DISTINCT numero_dia) as dias,
        COUNT(DISTINCT numero_microciclo) as micros,
        COUNT(*) as sesiones
    FROM bronze_sesiones
    GROUP BY sheet_name
    ORDER BY sheet_name
""").fetchdf())

print("\n💪 TOTALES:")
print(conn.execute("""
    SELECT 
        COUNT(*) as total_series,
        COUNT(DISTINCT nombre_ejercicio) as ejercicios_unicos
    FROM bronze_series
""").fetchdf())

conn.close()