"""Queries SQL para el dashboard — cada función retorna un DataFrame"""

import duckdb
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date


@dataclass
class Filters:
    """Estado de filtros globales del sidebar"""
    mesociclos: List[str] = field(default_factory=list)
    ejercicios: List[str] = field(default_factory=list)
    tipos: List[str] = field(default_factory=list)
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None


def _where_clause(f: Filters, plan_alias: str = "p", ejercicio_alias: str = "e",
                  fecha_alias: str = "fe") -> str:
    """Construye cláusula WHERE dinámica a partir de los filtros"""
    conditions = []
    if f.mesociclos:
        mesos = ", ".join(f"'{m}'" for m in f.mesociclos)
        conditions.append(f"{plan_alias}.mesociclo IN ({mesos})")
    if f.ejercicios:
        ejs = ", ".join(f"'{e}'" for e in f.ejercicios)
        conditions.append(f"{ejercicio_alias}.nombre_ejercicio IN ({ejs})")
    if f.tipos:
        tipos = ", ".join(f"'{t}'" for t in f.tipos)
        conditions.append(f"{ejercicio_alias}.tipo_ejercicio IN ({tipos})")
    if f.fecha_inicio:
        conditions.append(f"{fecha_alias}.fecha >= '{f.fecha_inicio}'")
    if f.fecha_fin:
        conditions.append(f"{fecha_alias}.fecha <= '{f.fecha_fin}'")
    return " AND ".join(conditions) if conditions else "1=1"


# ── Sidebar: opciones de filtros ──────────────────────────────────────

def get_mesociclos(conn: duckdb.DuckDBPyConnection) -> List[str]:
    return [r[0] for r in conn.execute(
        "SELECT DISTINCT mesociclo FROM silver_dim_plan ORDER BY mesociclo"
    ).fetchall()]


def get_ejercicios(conn: duckdb.DuckDBPyConnection) -> List[str]:
    return [r[0] for r in conn.execute(
        "SELECT DISTINCT nombre_ejercicio FROM silver_dim_ejercicios ORDER BY nombre_ejercicio"
    ).fetchall()]


def get_tipos(conn: duckdb.DuckDBPyConnection) -> List[str]:
    return [r[0] for r in conn.execute(
        "SELECT DISTINCT tipo_ejercicio FROM silver_dim_ejercicios "
        "WHERE tipo_ejercicio IS NOT NULL ORDER BY tipo_ejercicio"
    ).fetchall()]


def get_date_range(conn: duckdb.DuckDBPyConnection):
    row = conn.execute(
        "SELECT MIN(fecha) as mn, MAX(fecha) as mx FROM silver_dim_fecha"
    ).fetchone()
    return row[0], row[1]


# ── Tab Resumen ───────────────────────────────────────────────────────

def get_kpis(conn: duckdb.DuckDBPyConnection, f: Filters) -> dict:
    w = _where_clause(f)
    row = conn.execute(f"""
        SELECT
            COUNT(*) as total_series,
            COUNT(DISTINCT e.ejercicio_id) as ejercicios,
            MAX(fs.carga_kg) as max_carga,
            COUNT(DISTINCT fe.fecha) as dias
        FROM silver_fact_series fs
        JOIN silver_dim_ejercicios e ON fs.ejercicio_id = e.ejercicio_id
        LEFT JOIN silver_dim_fecha fe ON fs.fecha_id = fe.fecha_id
        LEFT JOIN silver_dim_plan p ON fs.plan_id = p.plan_id
        WHERE {w}
    """).fetchone()
    return {
        "total_series": row[0],
        "ejercicios": row[1],
        "max_carga": row[2],
        "dias": row[3],
    }


def get_volumen_semanal(conn: duckdb.DuckDBPyConnection, f: Filters) -> pd.DataFrame:
    w = _where_clause(f)
    return conn.execute(f"""
        SELECT
            fe.anio || '-S' || LPAD(CAST(fe.semana_anio AS VARCHAR), 2, '0') as semana,
            fe.semana_anio,
            fe.anio,
            SUM(COALESCE(fs.repeticiones_ejecutadas, 0) * COALESCE(fs.carga_kg, 0)) as volumen,
            COUNT(*) as series
        FROM silver_fact_series fs
        JOIN silver_dim_ejercicios e ON fs.ejercicio_id = e.ejercicio_id
        JOIN silver_dim_fecha fe ON fs.fecha_id = fe.fecha_id
        LEFT JOIN silver_dim_plan p ON fs.plan_id = p.plan_id
        WHERE {w}
        GROUP BY fe.anio, fe.semana_anio, semana
        ORDER BY fe.anio, fe.semana_anio
    """).fetchdf()


def get_distribucion_grupos(conn: duckdb.DuckDBPyConnection, f: Filters) -> pd.DataFrame:
    w = _where_clause(f)
    return conn.execute(f"""
        SELECT
            e.tipo_ejercicio,
            COUNT(*) as total_series,
            SUM(COALESCE(fs.repeticiones_ejecutadas, 0) * COALESCE(fs.carga_kg, 0)) as volumen
        FROM silver_fact_series fs
        JOIN silver_dim_ejercicios e ON fs.ejercicio_id = e.ejercicio_id
        LEFT JOIN silver_dim_fecha fe ON fs.fecha_id = fe.fecha_id
        LEFT JOIN silver_dim_plan p ON fs.plan_id = p.plan_id
        WHERE {w} AND e.tipo_ejercicio IS NOT NULL
        GROUP BY e.tipo_ejercicio
        ORDER BY volumen DESC
    """).fetchdf()


# ── Tab Progreso ──────────────────────────────────────────────────────

def get_progreso_ejercicio(conn: duckdb.DuckDBPyConnection, ejercicio: str,
                           f: Filters) -> pd.DataFrame:
    w = _where_clause(f)
    return conn.execute(f"""
        SELECT
            fe.fecha,
            fs.numero_serie,
            fs.repeticiones_ejecutadas as reps,
            fs.carga_kg,
            fs.rir_rpe,
            p.mesociclo
        FROM silver_fact_series fs
        JOIN silver_dim_ejercicios e ON fs.ejercicio_id = e.ejercicio_id
        JOIN silver_dim_fecha fe ON fs.fecha_id = fe.fecha_id
        LEFT JOIN silver_dim_plan p ON fs.plan_id = p.plan_id
        WHERE e.nombre_ejercicio = '{ejercicio}'
          AND fs.carga_kg IS NOT NULL
          AND {w}
        ORDER BY fe.fecha, fs.numero_serie
    """).fetchdf()


def get_mejor_serie_por_sesion(conn: duckdb.DuckDBPyConnection, ejercicio: str,
                                f: Filters) -> pd.DataFrame:
    w = _where_clause(f)
    return conn.execute(f"""
        SELECT
            fe.fecha,
            MAX(fs.carga_kg) as carga_kg,
            MAX(fs.repeticiones_ejecutadas) as reps,
            p.mesociclo
        FROM silver_fact_series fs
        JOIN silver_dim_ejercicios e ON fs.ejercicio_id = e.ejercicio_id
        JOIN silver_dim_fecha fe ON fs.fecha_id = fe.fecha_id
        LEFT JOIN silver_dim_plan p ON fs.plan_id = p.plan_id
        WHERE e.nombre_ejercicio = '{ejercicio}'
          AND fs.carga_kg IS NOT NULL
          AND {w}
        GROUP BY fe.fecha, p.mesociclo
        ORDER BY fe.fecha
    """).fetchdf()


# ── Tab Records ───────────────────────────────────────────────────────

def get_records(conn: duckdb.DuckDBPyConnection, f: Filters) -> pd.DataFrame:
    w = _where_clause(f)
    return conn.execute(f"""
        WITH ranked AS (
            SELECT
                e.nombre_ejercicio,
                e.tipo_ejercicio,
                fs.carga_kg,
                fs.repeticiones_ejecutadas as reps,
                fe.fecha,
                ROW_NUMBER() OVER (
                    PARTITION BY e.ejercicio_id
                    ORDER BY fs.carga_kg DESC, fe.fecha DESC
                ) as rn
            FROM silver_fact_series fs
            JOIN silver_dim_ejercicios e ON fs.ejercicio_id = e.ejercicio_id
            LEFT JOIN silver_dim_fecha fe ON fs.fecha_id = fe.fecha_id
            LEFT JOIN silver_dim_plan p ON fs.plan_id = p.plan_id
            WHERE fs.carga_kg IS NOT NULL AND {w}
        )
        SELECT nombre_ejercicio as "Ejercicio",
               tipo_ejercicio as "Grupo",
               carga_kg as "Record (kg)",
               reps as "Reps",
               fecha as "Fecha"
        FROM ranked
        WHERE rn = 1
        ORDER BY carga_kg DESC
    """).fetchdf()


# ── Tab Volumen ───────────────────────────────────────────────────────

def get_volumen_por_grupo_semanal(conn: duckdb.DuckDBPyConnection,
                                   f: Filters) -> pd.DataFrame:
    w = _where_clause(f)
    return conn.execute(f"""
        SELECT
            fe.anio || '-S' || LPAD(CAST(fe.semana_anio AS VARCHAR), 2, '0') as semana,
            fe.semana_anio,
            fe.anio,
            e.tipo_ejercicio,
            SUM(COALESCE(fs.repeticiones_ejecutadas, 0) * COALESCE(fs.carga_kg, 0)) as volumen,
            COUNT(*) as series,
            SUM(fs.repeticiones_ejecutadas) as total_reps
        FROM silver_fact_series fs
        JOIN silver_dim_ejercicios e ON fs.ejercicio_id = e.ejercicio_id
        JOIN silver_dim_fecha fe ON fs.fecha_id = fe.fecha_id
        LEFT JOIN silver_dim_plan p ON fs.plan_id = p.plan_id
        WHERE {w} AND e.tipo_ejercicio IS NOT NULL
        GROUP BY fe.anio, fe.semana_anio, semana, e.tipo_ejercicio
        ORDER BY fe.anio, fe.semana_anio
    """).fetchdf()


def get_volumen_por_mesociclo(conn: duckdb.DuckDBPyConnection,
                               f: Filters) -> pd.DataFrame:
    w = _where_clause(f)
    return conn.execute(f"""
        SELECT
            p.mesociclo,
            e.tipo_ejercicio,
            SUM(COALESCE(fs.repeticiones_ejecutadas, 0) * COALESCE(fs.carga_kg, 0)) as volumen,
            COUNT(*) as series,
            SUM(fs.repeticiones_ejecutadas) as total_reps
        FROM silver_fact_series fs
        JOIN silver_dim_ejercicios e ON fs.ejercicio_id = e.ejercicio_id
        LEFT JOIN silver_dim_fecha fe ON fs.fecha_id = fe.fecha_id
        JOIN silver_dim_plan p ON fs.plan_id = p.plan_id
        WHERE {w} AND e.tipo_ejercicio IS NOT NULL
        GROUP BY p.mesociclo, e.tipo_ejercicio
        ORDER BY p.mesociclo
    """).fetchdf()


# ── Tab Intensidad ────────────────────────────────────────────────────

def get_intensidad_por_sesion(conn: duckdb.DuckDBPyConnection,
                               f: Filters) -> pd.DataFrame:
    w = _where_clause(f)
    return conn.execute(f"""
        SELECT
            fe.fecha,
            p.mesociclo,
            AVG(fs.rir_rpe) as avg_rir,
            MIN(fs.rir_rpe) as min_rir,
            COUNT(*) as series
        FROM silver_fact_series fs
        JOIN silver_dim_fecha fe ON fs.fecha_id = fe.fecha_id
        LEFT JOIN silver_dim_plan p ON fs.plan_id = p.plan_id
        LEFT JOIN silver_dim_ejercicios e ON fs.ejercicio_id = e.ejercicio_id
        WHERE fs.rir_rpe IS NOT NULL AND {w}
        GROUP BY fe.fecha, p.mesociclo
        ORDER BY fe.fecha
    """).fetchdf()


def get_rir_por_microciclo(conn: duckdb.DuckDBPyConnection,
                            f: Filters) -> pd.DataFrame:
    w = _where_clause(f)
    return conn.execute(f"""
        SELECT
            p.mesociclo || ' - Micro ' || p.numero_microciclo as micro_label,
            p.mesociclo,
            p.numero_microciclo,
            fs.rir_rpe
        FROM silver_fact_series fs
        JOIN silver_dim_plan p ON fs.plan_id = p.plan_id
        LEFT JOIN silver_dim_fecha fe ON fs.fecha_id = fe.fecha_id
        LEFT JOIN silver_dim_ejercicios e ON fs.ejercicio_id = e.ejercicio_id
        WHERE fs.rir_rpe IS NOT NULL AND {w}
        ORDER BY p.mesociclo, p.numero_microciclo
    """).fetchdf()


# ── Tab Frecuencia ────────────────────────────────────────────────────

def get_frecuencia_diaria(conn: duckdb.DuckDBPyConnection,
                           f: Filters) -> pd.DataFrame:
    w = _where_clause(f)
    return conn.execute(f"""
        SELECT
            fe.fecha,
            fe.dia_semana,
            fe.nombre_dia_semana,
            fe.semana_anio,
            fe.anio,
            fe.mes,
            COUNT(DISTINCT fs.sesion_id) as sesiones,
            COUNT(*) as series
        FROM silver_fact_series fs
        JOIN silver_dim_fecha fe ON fs.fecha_id = fe.fecha_id
        LEFT JOIN silver_dim_plan p ON fs.plan_id = p.plan_id
        LEFT JOIN silver_dim_ejercicios e ON fs.ejercicio_id = e.ejercicio_id
        WHERE {w}
        GROUP BY fe.fecha, fe.dia_semana, fe.nombre_dia_semana,
                 fe.semana_anio, fe.anio, fe.mes
        ORDER BY fe.fecha
    """).fetchdf()


# ── Tab Grupos ────────────────────────────────────────────────────────

def get_volumen_por_grupo(conn: duckdb.DuckDBPyConnection,
                           f: Filters) -> pd.DataFrame:
    w = _where_clause(f)
    return conn.execute(f"""
        SELECT
            e.tipo_ejercicio,
            COUNT(*) as total_series,
            SUM(COALESCE(fs.repeticiones_ejecutadas, 0) * COALESCE(fs.carga_kg, 0)) as volumen,
            COUNT(DISTINCT e.ejercicio_id) as ejercicios_distintos,
            ROUND(AVG(fs.carga_kg), 1) as carga_promedio
        FROM silver_fact_series fs
        JOIN silver_dim_ejercicios e ON fs.ejercicio_id = e.ejercicio_id
        LEFT JOIN silver_dim_fecha fe ON fs.fecha_id = fe.fecha_id
        LEFT JOIN silver_dim_plan p ON fs.plan_id = p.plan_id
        WHERE {w} AND e.tipo_ejercicio IS NOT NULL
        GROUP BY e.tipo_ejercicio
        ORDER BY volumen DESC
    """).fetchdf()


def get_volumen_grupo_temporal(conn: duckdb.DuckDBPyConnection,
                                f: Filters) -> pd.DataFrame:
    w = _where_clause(f)
    return conn.execute(f"""
        SELECT
            fe.anio || '-S' || LPAD(CAST(fe.semana_anio AS VARCHAR), 2, '0') as semana,
            fe.semana_anio,
            fe.anio,
            e.tipo_ejercicio,
            COUNT(*) as series
        FROM silver_fact_series fs
        JOIN silver_dim_ejercicios e ON fs.ejercicio_id = e.ejercicio_id
        JOIN silver_dim_fecha fe ON fs.fecha_id = fe.fecha_id
        LEFT JOIN silver_dim_plan p ON fs.plan_id = p.plan_id
        WHERE {w} AND e.tipo_ejercicio IS NOT NULL
        GROUP BY fe.anio, fe.semana_anio, semana, e.tipo_ejercicio
        ORDER BY fe.anio, fe.semana_anio
    """).fetchdf()
