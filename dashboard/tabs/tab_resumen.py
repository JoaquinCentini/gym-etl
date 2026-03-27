"""Tab Resumen — Overview con KPIs y gráficos principales"""

import streamlit as st
import duckdb

from dashboard.queries import Filters, get_kpis, get_volumen_semanal, get_distribucion_grupos
from dashboard.charts import chart_volumen_semanal, chart_distribucion_grupos
from dashboard.styles import kpi_card


def render(conn: duckdb.DuckDBPyConnection, f: Filters):
    kpis = get_kpis(conn, f)

    # KPI cards
    cols = st.columns(4)
    with cols[0]:
        st.html(kpi_card(
            "Total Series", f"{kpis['total_series']:,}",
            color="#FF4B4B"
        ))
    with cols[1]:
        st.html(kpi_card(
            "Ejercicios", str(kpis['ejercicios']),
            color="#636EFA"
        ))
    with cols[2]:
        max_c = kpis['max_carga']
        st.html(kpi_card(
            "Carga Máxima", f"{max_c:.1f} kg" if max_c else "—",
            color="#00CC96"
        ))
    with cols[3]:
        st.html(kpi_card(
            "Días Entrenados", str(kpis['dias']),
            color="#AB63FA"
        ))

    st.markdown("---")

    # Gráficos
    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader("Volumen por semana")
        df_vol = get_volumen_semanal(conn, f)
        if not df_vol.empty:
            st.plotly_chart(chart_volumen_semanal(df_vol), use_container_width=True)
        else:
            st.info("Sin datos de volumen para los filtros seleccionados")

    with col2:
        st.subheader("Distribución por grupo")
        df_dist = get_distribucion_grupos(conn, f)
        if not df_dist.empty:
            st.plotly_chart(chart_distribucion_grupos(df_dist), use_container_width=True, key="resumen_distribucion")
        else:
            st.info("Sin datos de distribución")
