"""Tab Volumen de Entrenamiento — Volumen total por semana/mesociclo"""

import streamlit as st
import duckdb

from dashboard.queries import (Filters, get_volumen_por_grupo_semanal,
                                get_volumen_por_mesociclo)
from dashboard.charts import chart_volumen_stacked, chart_volumen_mesociclo


def render(conn: duckdb.DuckDBPyConnection, f: Filters):
    vista = st.radio("Agrupar por", ["Semanal", "Mesociclo"],
                     key="volumen_vista", horizontal=True)

    if vista == "Semanal":
        df = get_volumen_por_grupo_semanal(conn, f)
        if df.empty:
            st.info("Sin datos de volumen")
            return

        st.subheader("Volumen semanal por grupo muscular")
        st.plotly_chart(chart_volumen_stacked(df), use_container_width=True)

        # Resumen
        with st.expander("Resumen semanal"):
            resumen = df.groupby("semana").agg(
                volumen_total=("volumen", "sum"),
                series_totales=("series", "sum"),
                reps_totales=("total_reps", "sum"),
            ).reset_index()
            st.dataframe(resumen, use_container_width=True, hide_index=True)

    else:
        df = get_volumen_por_mesociclo(conn, f)
        if df.empty:
            st.info("Sin datos de volumen")
            return

        st.subheader("Volumen por mesociclo y grupo muscular")
        st.plotly_chart(chart_volumen_mesociclo(df), use_container_width=True)

        with st.expander("Resumen por mesociclo"):
            resumen = df.groupby("mesociclo").agg(
                volumen_total=("volumen", "sum"),
                series_totales=("series", "sum"),
            ).reset_index()
            st.dataframe(resumen, use_container_width=True, hide_index=True)
