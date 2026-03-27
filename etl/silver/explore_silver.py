"""
Script para explorar la capa Silver completa
Analiza cada dimensión y la tabla de hechos
"""

import duckdb
import pandas as pd

# Conectar a la base de datos
conn = duckdb.connect(r"data/gym.duckdb")

print("="*100)
print("EXPLORACIÓN DE LA CAPA SILVER")
print("="*100)

# ============================================================================
# 1. RESUMEN GENERAL
# ============================================================================
print("\n📊 RESUMEN GENERAL DE SILVER:")
print("-"*100)

resumen = conn.execute("""
    SELECT 
        (SELECT COUNT(*) FROM silver_dim_ejercicios) as total_ejercicios,
        (SELECT COUNT(*) FROM silver_dim_fecha) as total_fechas,
        (SELECT COUNT(*) FROM silver_dim_plan) as total_planes,
        (SELECT COUNT(*) FROM silver_fact_series) as total_series
""").fetchdf()
print(resumen)

# ============================================================================
# 2. DIMENSIÓN DE EJERCICIOS
# ============================================================================
print("\n\n" + "="*100)
print("📋 DIMENSIÓN: EJERCICIOS")
print("="*100)

# Estructura
print("\n🔍 Estructura de la tabla:")
estructura_ej = conn.execute("DESCRIBE silver_dim_ejercicios").fetchdf()
print(estructura_ej)

# Primeros registros
print("\n📝 Primeros 10 ejercicios:")
primeros_ej = conn.execute("""
    SELECT ejercicio_id, nombre_ejercicio, tipo_ejercicio
    FROM silver_dim_ejercicios
    ORDER BY ejercicio_id
    LIMIT 10
""").fetchdf()
print(primeros_ej.to_string())

# Ejercicios por tipo
print("\n📊 Ejercicios por tipo:")
por_tipo = conn.execute("""
    SELECT 
        tipo_ejercicio,
        COUNT(*) as cantidad,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM silver_dim_ejercicios), 1) as porcentaje
    FROM silver_dim_ejercicios
    GROUP BY tipo_ejercicio
    ORDER BY cantidad DESC
""").fetchdf()
print(por_tipo.to_string())

# Ejercicios con/sin URL
print("\n🔗 Ejercicios con URL de video:")
con_url = conn.execute("""
    SELECT 
        SUM(CASE WHEN url_video IS NOT NULL THEN 1 ELSE 0 END) as con_url,
        SUM(CASE WHEN url_video IS NULL THEN 1 ELSE 0 END) as sin_url,
        COUNT(*) as total
    FROM silver_dim_ejercicios
""").fetchdf()
print(con_url)

# Ejercicios más frecuentes (según fact)
print("\n🏆 Top 10 ejercicios más realizados:")
top_ejercicios = conn.execute("""
    SELECT 
        e.nombre_ejercicio,
        e.tipo_ejercicio,
        COUNT(*) as veces_realizado
    FROM silver_fact_series f
    JOIN silver_dim_ejercicios e ON f.ejercicio_id = e.ejercicio_id
    GROUP BY e.nombre_ejercicio, e.tipo_ejercicio
    ORDER BY veces_realizado DESC
    LIMIT 10
""").fetchdf()
print(top_ejercicios.to_string())

# ============================================================================
# 3. DIMENSIÓN DE FECHA
# ============================================================================
print("\n\n" + "="*100)
print("📅 DIMENSIÓN: FECHA")
print("="*100)

# Estructura
print("\n🔍 Estructura de la tabla:")
estructura_fecha = conn.execute("DESCRIBE silver_dim_fecha").fetchdf()
print(estructura_fecha)

# Rango de fechas
print("\n📆 Rango de fechas:")
rango = conn.execute("""
    SELECT 
        MIN(fecha) as fecha_inicio,
        MAX(fecha) as fecha_fin,
        COUNT(DISTINCT fecha) as dias_unicos
    FROM silver_dim_fecha
""").fetchdf()
print(rango)

# Distribución por año
print("\n📊 Distribución por año:")
por_anio = conn.execute("""
    SELECT 
        anio,
        COUNT(*) as dias,
        MIN(fecha) as primera_fecha,
        MAX(fecha) as ultima_fecha
    FROM silver_dim_fecha
    GROUP BY anio
    ORDER BY anio
""").fetchdf()
print(por_anio.to_string())

# Distribución por mes
print("\n📊 Distribución por mes (últimos 12 meses con datos):")
por_mes = conn.execute("""
    SELECT 
        anio,
        mes,
        COUNT(*) as dias
    FROM silver_dim_fecha
    GROUP BY anio, mes
    ORDER BY anio DESC, mes DESC
    LIMIT 12
""").fetchdf()
print(por_mes.to_string())

# Distribución por día de semana
print("\n📊 Distribución por día de semana:")
por_dia_semana = conn.execute("""
    SELECT 
        nombre_dia_semana,
        COUNT(*) as cantidad,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM silver_dim_fecha), 1) as porcentaje
    FROM silver_dim_fecha
    GROUP BY dia_semana, nombre_dia_semana
    ORDER BY dia_semana
""").fetchdf()
print(por_dia_semana.to_string())

# ============================================================================
# 4. DIMENSIÓN DE PLAN
# ============================================================================
print("\n\n" + "="*100)
print("📊 DIMENSIÓN: PLAN")
print("="*100)

# Estructura
print("\n🔍 Estructura de la tabla:")
estructura_plan = conn.execute("DESCRIBE silver_dim_plan").fetchdf()
print(estructura_plan)

# Primeros registros
print("\n📝 Primeros 10 planes:")
primeros_plan = conn.execute("""
    SELECT plan_id, mesociclo, numero_dia, nombre_dia, numero_microciclo
    FROM silver_dim_plan
    ORDER BY mesociclo, numero_dia, numero_microciclo
    LIMIT 10
""").fetchdf()
print(primeros_plan.to_string())

# Planes por mesociclo
print("\n📊 Planes por mesociclo:")
por_meso = conn.execute("""
    SELECT 
        mesociclo,
        COUNT(DISTINCT numero_dia) as dias,
        COUNT(DISTINCT numero_microciclo) as microciclos,
        COUNT(*) as combinaciones
    FROM silver_dim_plan
    GROUP BY mesociclo
    ORDER BY mesociclo
""").fetchdf()
print(por_meso.to_string())

# Distribución de días
print("\n📊 Distribución de días de entrenamiento:")
dist_dias = conn.execute("""
    SELECT 
        numero_dia,
        COUNT(DISTINCT mesociclo) as en_mesociclos,
        COUNT(*) as total_combinaciones
    FROM silver_dim_plan
    GROUP BY numero_dia
    ORDER BY numero_dia
""").fetchdf()
print(dist_dias.to_string())

# ============================================================================
# 5. TABLA DE HECHOS - SERIES
# ============================================================================
print("\n\n" + "="*100)
print("💪 TABLA DE HECHOS: SERIES")
print("="*100)

# Estructura
print("\n🔍 Estructura de la tabla:")
estructura_fact = conn.execute("DESCRIBE silver_fact_series").fetchdf()
print(estructura_fact)

# Primeros registros
print("\n📝 Primeras 10 series:")
primeras_series = conn.execute("""
    SELECT 
        f.serie_id,
        e.nombre_ejercicio,
        f.numero_serie,
        f.repeticiones_ejecutadas,
        f.carga_kg,
        f.rir_rpe
    FROM silver_fact_series f
    LEFT JOIN silver_dim_ejercicios e ON f.ejercicio_id = e.ejercicio_id
    ORDER BY f.serie_id
    LIMIT 10
""").fetchdf()
print(primeras_series.to_string())

# Estadísticas generales
print("\n📊 Estadísticas generales de series:")
stats = conn.execute("""
    SELECT 
        COUNT(*) as total_series,
        COUNT(DISTINCT sesion_id) as sesiones_distintas,
        COUNT(DISTINCT ejercicio_id) as ejercicios_distintos,
        ROUND(AVG(repeticiones_ejecutadas), 1) as promedio_reps,
        ROUND(AVG(carga_kg), 1) as promedio_carga_kg,
        ROUND(AVG(rir_rpe), 1) as promedio_rir
    FROM silver_fact_series
""").fetchdf()
print(stats)

# Series por grupo de ejercicio
print("\n📊 Series por grupo de ejercicio:")
por_grupo = conn.execute("""
    SELECT 
        grupo_ejercicio,
        COUNT(*) as total_series,
        COUNT(DISTINCT ejercicio_id) as ejercicios_distintos,
        ROUND(AVG(carga_kg), 1) as promedio_carga
    FROM silver_fact_series
    WHERE grupo_ejercicio IS NOT NULL
    GROUP BY grupo_ejercicio
    ORDER BY grupo_ejercicio
""").fetchdf()
print(por_grupo.to_string())

# Distribución de repeticiones
print("\n📊 Distribución de repeticiones:")
dist_reps = conn.execute("""
    SELECT 
        repeticiones_ejecutadas,
        COUNT(*) as cantidad,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM silver_fact_series WHERE repeticiones_ejecutadas IS NOT NULL), 1) as porcentaje
    FROM silver_fact_series
    WHERE repeticiones_ejecutadas IS NOT NULL
    GROUP BY repeticiones_ejecutadas
    ORDER BY repeticiones_ejecutadas
    LIMIT 20
""").fetchdf()
print(dist_reps.to_string())

# Distribución de RIR
print("\n📊 Distribución de RIR:")
dist_rir = conn.execute("""
    SELECT 
        rir_rpe,
        COUNT(*) as cantidad,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM silver_fact_series WHERE rir_rpe IS NOT NULL), 1) as porcentaje
    FROM silver_fact_series
    WHERE rir_rpe IS NOT NULL
    GROUP BY rir_rpe
    ORDER BY rir_rpe
""").fetchdf()
print(dist_rir.to_string())

# ============================================================================
# 6. CALIDAD DE DATOS
# ============================================================================
print("\n\n" + "="*100)
print("⚠️ CALIDAD DE DATOS")
print("="*100)

calidad = conn.execute("""
    SELECT 
        COUNT(*) as total_series,
        SUM(CASE WHEN ejercicio_id IS NULL THEN 1 ELSE 0 END) as sin_ejercicio_id,
        SUM(CASE WHEN fecha_id IS NULL THEN 1 ELSE 0 END) as sin_fecha_id,
        SUM(CASE WHEN plan_id IS NULL THEN 1 ELSE 0 END) as sin_plan_id,
        SUM(CASE WHEN repeticiones_ejecutadas IS NULL THEN 1 ELSE 0 END) as sin_reps,
        SUM(CASE WHEN carga_kg IS NULL THEN 1 ELSE 0 END) as sin_carga,
        SUM(CASE WHEN rir_rpe IS NULL THEN 1 ELSE 0 END) as sin_rir,
        ROUND(SUM(CASE WHEN ejercicio_id IS NOT NULL AND fecha_id IS NOT NULL AND plan_id IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as pct_completo
    FROM silver_fact_series
""").fetchdf()
print(calidad)

print("\n📝 Interpretación:")
sin_fecha = calidad.iloc[0]['sin_fecha_id']
sin_plan = calidad.iloc[0]['sin_plan_id']
pct = calidad.iloc[0]['pct_completo']

if sin_fecha > 0:
    print(f"  ⚠️  {sin_fecha} series sin fecha_id (sesiones sin fecha registrada)")
if sin_plan > 0:
    print(f"  ⚠️  {sin_plan} series sin plan_id (problema en join)")
print(f"  ✅ {pct}% de series tienen todas las FKs principales")

# ============================================================================
# 7. ANÁLISIS AVANZADO
# ============================================================================
print("\n\n" + "="*100)
print("📈 ANÁLISIS AVANZADO")
print("="*100)

# Progresión de carga en ejercicio principal
print("\n📊 Progresión de carga - Press banco (ejemplo):")
progresion = conn.execute("""
    SELECT 
        f.fecha_id,
        fe.fecha,
        e.nombre_ejercicio,
        f.numero_serie,
        f.repeticiones_ejecutadas,
        f.carga_kg,
        f.rir_rpe
    FROM silver_fact_series f
    JOIN silver_dim_ejercicios e ON f.ejercicio_id = e.ejercicio_id
    LEFT JOIN silver_dim_fecha fe ON f.fecha_id = fe.fecha_id
    WHERE e.nombre_ejercicio LIKE '%Press banco%'
      AND f.fecha_id IS NOT NULL
    ORDER BY fe.fecha, f.numero_serie
    LIMIT 20
""").fetchdf()
if len(progresion) > 0:
    print(progresion.to_string())
else:
    print("  No se encontró este ejercicio con fechas")

# Series por día de la semana
print("\n📊 Series por día de la semana:")
por_dia = conn.execute("""
    SELECT 
        fe.nombre_dia_semana,
        COUNT(*) as total_series,
        COUNT(DISTINCT f.sesion_id) as sesiones,
        ROUND(AVG(f.carga_kg), 1) as promedio_carga
    FROM silver_fact_series f
    JOIN silver_dim_fecha fe ON f.fecha_id = fe.fecha_id
    GROUP BY fe.dia_semana, fe.nombre_dia_semana
    ORDER BY fe.dia_semana
""").fetchdf()
print(por_dia.to_string())

# ejercicio para ver
print("\n📊 Aducción 1 brazo en polea:")
ejercicio = conn.execute("""
    SELECT 
        *
    FROM silver_dim_ejercicios de
    WHERE de.nombre_ejercicio = 'Aducción 1 brazo en polea'
""").fetchdf()
print(ejercicio)

conn.close()

print("\n\n" + "="*100)
print("✅ Exploración de Silver completada!")
print("="*100)


