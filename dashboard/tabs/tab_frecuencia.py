"""Tab Frecuencia — Consistencia de entrenamiento"""

import streamlit as st
import duckdb
import pandas as pd

from dashboard.queries import Filters, get_frecuencia_diaria
from dashboard.charts import chart_heatmap_frecuencia, chart_sesiones_por_mes
from dashboard.styles import kpi_card

MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def _calcular_racha(fechas: pd.Series, dias_descanso: int = 1) -> int:
    """Calcula la racha más larga de sesiones permitiendo N días de descanso"""
    if fechas.empty:
        return 0
    fechas_sorted = pd.to_datetime(fechas).sort_values().unique()
    if len(fechas_sorted) < 2:
        return len(fechas_sorted)

    max_gap = dias_descanso + 1
    racha_max = 1
    racha_actual = 1
    for i in range(1, len(fechas_sorted)):
        diff = (fechas_sorted[i] - fechas_sorted[i - 1]).days
        if diff <= max_gap:
            racha_actual += 1
            racha_max = max(racha_max, racha_actual)
        else:
            racha_actual = 1
    return racha_max


def _dias_por_mes(df: pd.DataFrame) -> pd.DataFrame:
    """Retorna DataFrame con días entrenados por mes, excluyendo meses parciales
    cuando hay suficientes datos."""
    if df.empty:
        return pd.DataFrame(columns=["anio", "mes", "dias"])

    resultado = (
        df.groupby(["anio", "mes"])["fecha"]
        .nunique()
        .reset_index()
        .rename(columns={"fecha": "dias"})
    )
    if len(resultado) > 2:
        resultado = resultado.iloc[1:-1]
    return resultado


def _mejor_peor_mes(df: pd.DataFrame) -> tuple[str, int, str, int]:
    """Retorna (peor_nombre, peor_dias, mejor_nombre, mejor_dias)"""
    meses = _dias_por_mes(df)
    if meses.empty:
        return ("—", 0, "—", 0)

    peor = meses.loc[meses["dias"].idxmin()]
    mejor = meses.loc[meses["dias"].idxmax()]

    peor_nombre = f"{MESES_ES.get(int(peor['mes']), '?')} {int(peor['anio'])}"
    mejor_nombre = f"{MESES_ES.get(int(mejor['mes']), '?')} {int(mejor['anio'])}"

    return (peor_nombre, int(peor["dias"]), mejor_nombre, int(mejor["dias"]))


def render(conn: duckdb.DuckDBPyConnection, f: Filters):
    df = get_frecuencia_diaria(conn, f)

    if df.empty:
        st.info("Sin datos de frecuencia")
        return

    total_dias = df["fecha"].nunique()
    semanas = df.groupby(["anio", "semana_anio"])["fecha"].nunique().reset_index()
    dias_por_semana = semanas["fecha"].mean() if not semanas.empty else 0

    # Selector de días de descanso — radio buttons en vez de slider
    dias_descanso = st.radio(
        "Días de descanso permitidos en la racha",
        options=[1, 2, 3],
        horizontal=True,
        key="frecuencia_dias_descanso",
    )

    racha = _calcular_racha(df["fecha"], dias_descanso)
    peor_nombre, peor_dias, mejor_nombre, mejor_dias = _mejor_peor_mes(df)

    # KPIs — 5 columnas iguales
    cols = st.columns(5)
    with cols[0]:
        st.html(kpi_card(
            "Total días entrenados", str(total_dias),
            color="#FF4B4B",
        ))
    with cols[1]:
        st.html(kpi_card(
            "Días/semana promedio", f"{dias_por_semana:.1f}",
            color="#636EFA",
        ))
    with cols[2]:
        st.html(kpi_card(
            "Racha más larga", f"{racha} sesiones",
            subtitle=f"(max {dias_descanso} día{'s' if dias_descanso > 1 else ''} descanso)",
            color="#00CC96",
        ))
    with cols[3]:
        st.html(kpi_card(
            "Mejor mes", mejor_nombre,
            subtitle=f"{mejor_dias} días entrenados",
            color="#AB63FA",
        ))
    with cols[4]:
        st.html(kpi_card(
            "Peor mes", peor_nombre,
            subtitle=f"solo {peor_dias} días entrenados",
            color="#EF553B",
        ))

    st.markdown("---")

    # Heatmap
    st.subheader("Calendario de entrenamiento")
    st.plotly_chart(chart_heatmap_frecuencia(df), use_container_width=True)

    # Sesiones por mes
    st.subheader("Días entrenados por mes")
    st.plotly_chart(chart_sesiones_por_mes(df), use_container_width=True)
