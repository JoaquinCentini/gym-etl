"""Tab Frecuencia — Consistencia de entrenamiento"""

import streamlit as st
import duckdb
import pandas as pd

from dashboard.queries import Filters, get_frecuencia_diaria
from dashboard.charts import chart_heatmap_frecuencia, chart_sesiones_por_mes
from dashboard.styles import kpi_card


def _calcular_racha(fechas: pd.Series) -> int:
    """Calcula la racha más larga de días consecutivos entrenados"""
    if fechas.empty:
        return 0
    fechas_sorted = pd.to_datetime(fechas).sort_values().unique()
    if len(fechas_sorted) < 2:
        return len(fechas_sorted)

    racha_max = 1
    racha_actual = 1
    for i in range(1, len(fechas_sorted)):
        diff = (fechas_sorted[i] - fechas_sorted[i - 1]).days
        if diff <= 2:  # Permite 1 día de descanso entre entrenamientos
            racha_actual += 1
            racha_max = max(racha_max, racha_actual)
        else:
            racha_actual = 1
    return racha_max


def render(conn: duckdb.DuckDBPyConnection, f: Filters):
    df = get_frecuencia_diaria(conn, f)

    if df.empty:
        st.info("Sin datos de frecuencia")
        return

    total_dias = df["fecha"].nunique()
    semanas = df.groupby(["anio", "semana_anio"])["fecha"].nunique().reset_index()
    dias_por_semana = semanas["fecha"].mean() if not semanas.empty else 0
    racha = _calcular_racha(df["fecha"])

    # KPIs
    cols = st.columns(3)
    with cols[0]:
        st.html(kpi_card(
            "Total días entrenados", str(total_dias),
            color="#FF4B4B"
        ))
    with cols[1]:
        st.html(kpi_card(
            "Días/semana promedio", f"{dias_por_semana:.1f}",
            color="#636EFA"
        ))
    with cols[2]:
        st.html(kpi_card(
            "Racha más larga", f"{racha} días",
            subtitle="(con max 1 día de descanso)",
            color="#00CC96"
        ))

    st.markdown("---")

    # Heatmap
    st.subheader("Calendario de entrenamiento")
    st.plotly_chart(chart_heatmap_frecuencia(df), use_container_width=True)

    # Sesiones por mes
    st.subheader("Días entrenados por mes")
    st.plotly_chart(chart_sesiones_por_mes(df), use_container_width=True)
