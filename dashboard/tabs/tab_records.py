"""Tab Records Personales — PRs por ejercicio"""

import streamlit as st
import duckdb

from dashboard.queries import Filters, get_records
from dashboard.charts import chart_top_records


def render(conn: duckdb.DuckDBPyConnection, f: Filters):
    df = get_records(conn, f)

    if df.empty:
        st.info("Sin records para los filtros seleccionados")
        return

    # Top records chart
    st.subheader("Top 15 Records por peso")
    st.plotly_chart(chart_top_records(df, top_n=15), use_container_width=True)

    st.markdown("---")

    # Tabla completa
    st.subheader("Todos los Records Personales")
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Record (kg)": st.column_config.NumberColumn(format="%.1f kg"),
            "Fecha": st.column_config.DateColumn(format="DD/MM/YYYY"),
        },
    )
