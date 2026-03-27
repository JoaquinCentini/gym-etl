"""Tab Progreso Histórico — Curvas de carga por ejercicio"""

import streamlit as st
import duckdb

from dashboard.queries import (Filters, get_ejercicios, get_progreso_ejercicio,
                                get_mejor_serie_por_sesion)
from dashboard.charts import chart_progreso_series, chart_progreso_mejor_serie


def render(conn: duckdb.DuckDBPyConnection, f: Filters):
    ejercicios = get_ejercicios(conn)
    if not ejercicios:
        st.info("No hay ejercicios cargados")
        return

    col1, col2 = st.columns([3, 1])
    with col1:
        ejercicio = st.selectbox("Ejercicio", ejercicios, key="progreso_ejercicio")
    with col2:
        modo = st.radio("Vista", ["Mejor serie", "Todas las series"],
                        key="progreso_modo", horizontal=True)

    if not ejercicio:
        return

    if modo == "Todas las series":
        df = get_progreso_ejercicio(conn, ejercicio, f)
        if df.empty:
            st.info(f"Sin datos de carga para {ejercicio}")
            return
        st.plotly_chart(chart_progreso_series(df), use_container_width=True)
    else:
        df = get_mejor_serie_por_sesion(conn, ejercicio, f)
        if df.empty:
            st.info(f"Sin datos de carga para {ejercicio}")
            return
        st.plotly_chart(chart_progreso_mejor_serie(df), use_container_width=True)

    # Tabla de detalle
    with st.expander("Ver datos"):
        st.dataframe(df, use_container_width=True, hide_index=True)
