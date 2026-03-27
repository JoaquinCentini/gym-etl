"""Tab Grupos Musculares — Distribución de volumen por grupo"""

import streamlit as st
import duckdb

from dashboard.queries import Filters, get_volumen_por_grupo, get_volumen_grupo_temporal
from dashboard.charts import (chart_distribucion_grupos, chart_radar_grupos,
                               chart_volumen_grupo_temporal)
from dashboard.styles import MUSCLE_LABELS


def render(conn: duckdb.DuckDBPyConnection, f: Filters):
    df = get_volumen_por_grupo(conn, f)

    if df.empty:
        st.info("Sin datos de grupos musculares")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Distribución de volumen")
        st.plotly_chart(chart_distribucion_grupos(df), use_container_width=True, key="grupos_distribucion")

    with col2:
        st.subheader("Balance muscular")
        st.plotly_chart(chart_radar_grupos(df), use_container_width=True)

    st.markdown("---")

    # Tabla de detalle
    st.subheader("Detalle por grupo")
    display_df = df.copy()
    display_df["tipo_ejercicio"] = display_df["tipo_ejercicio"].map(
        lambda t: MUSCLE_LABELS.get(t, t)
    )
    display_df.columns = ["Grupo", "Series", "Volumen", "Ejercicios", "Carga prom."]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Evolución temporal
    st.subheader("Series por grupo a lo largo del tiempo")
    df_temp = get_volumen_grupo_temporal(conn, f)
    if not df_temp.empty:
        st.plotly_chart(chart_volumen_grupo_temporal(df_temp), use_container_width=True)
