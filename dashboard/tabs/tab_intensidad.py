"""Tab Intensidad — Evolución de RIR/RPE"""

import streamlit as st
import duckdb

from dashboard.queries import Filters, get_intensidad_por_sesion, get_rir_por_microciclo
from dashboard.charts import chart_rir_por_sesion, chart_rir_boxplot


def render(conn: duckdb.DuckDBPyConnection, f: Filters):
    st.subheader("RIR promedio por sesión")
    st.caption("Menor RIR = mayor intensidad (más cerca del fallo)")

    df_sesion = get_intensidad_por_sesion(conn, f)
    if not df_sesion.empty:
        st.plotly_chart(chart_rir_por_sesion(df_sesion), use_container_width=True)
    else:
        st.info("Sin datos de RIR/RPE")

    st.markdown("---")

    st.subheader("Distribución de RIR por microciclo")
    df_micro = get_rir_por_microciclo(conn, f)
    if not df_micro.empty:
        st.plotly_chart(chart_rir_boxplot(df_micro), use_container_width=True)
    else:
        st.info("Sin datos de RIR por microciclo")
