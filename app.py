"""
GymTracker Dashboard — Visualización de entrenamiento
"""

import streamlit as st

st.set_page_config(
    page_title="GymTracker",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from dashboard.styles import inject_global_css
from dashboard.data_loader import get_connection, has_local_db, clear_excel_cache
from dashboard.queries import (Filters, get_mesociclos, get_ejercicios,
                                get_tipos, get_date_range)
from dashboard.tabs import (tab_resumen, tab_progreso, tab_records,
                             tab_volumen, tab_intensidad, tab_frecuencia,
                             tab_grupos)

inject_global_css()

# ── Sidebar ───────────────────────────────────────────────────────────

with st.sidebar:
    st.title("GymTracker")
    st.caption("Dashboard de entrenamiento")

    st.markdown("---")

    # Carga de datos
    uploaded_file = None
    if not has_local_db():
        st.warning("No se encontró base de datos local")
        uploaded_file = st.file_uploader(
            "Subí tu Excel de entrenamiento",
            type=["xlsx"],
            help="El archivo Excel con tus mesociclos de entrenamiento",
        )
    else:
        with st.expander("Actualizar datos"):
            uploaded_file = st.file_uploader(
                "Subir nuevo Excel",
                type=["xlsx"],
                help="Subí una versión actualizada del Excel",
            )
            if st.button("Reprocesar datos"):
                clear_excel_cache()
                st.rerun()

conn = get_connection(uploaded_file)

if conn is None:
    st.title("GymTracker")
    st.markdown("### Bienvenido")
    st.markdown(
        "Para comenzar, subí tu archivo Excel de entrenamiento "
        "usando el panel lateral."
    )
    st.stop()

# ── Filtros ───────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("---")
    st.subheader("Filtros")

    mesociclos = get_mesociclos(conn)
    selected_mesos = st.multiselect(
        "Mesociclo", mesociclos, default=mesociclos, key="filter_meso"
    )

    tipos = get_tipos(conn)
    selected_tipos = st.multiselect(
        "Grupo muscular", tipos, default=tipos, key="filter_tipo"
    )

    ejercicios_disponibles = get_ejercicios(conn)
    selected_ejercicios = st.multiselect(
        "Ejercicio (opcional)", ejercicios_disponibles, key="filter_ejercicio"
    )

    min_date, max_date = get_date_range(conn)
    if min_date and max_date:
        date_range = st.date_input(
            "Rango de fechas",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="filter_fechas",
        )
        fecha_inicio = date_range[0] if len(date_range) >= 1 else min_date
        fecha_fin = date_range[1] if len(date_range) >= 2 else max_date
    else:
        fecha_inicio, fecha_fin = None, None

filters = Filters(
    mesociclos=selected_mesos,
    ejercicios=selected_ejercicios,
    tipos=selected_tipos,
    fecha_inicio=fecha_inicio,
    fecha_fin=fecha_fin,
)

# ── Tabs ──────────────────────────────────────────────────────────────

tabs = st.tabs([
    "Resumen",
    "Progreso",
    "Records",
    "Volumen",
    "Intensidad",
    "Frecuencia",
    "Grupos Musculares",
])

with tabs[0]:
    tab_resumen.render(conn, filters)

with tabs[1]:
    tab_progreso.render(conn, filters)

with tabs[2]:
    tab_records.render(conn, filters)

with tabs[3]:
    tab_volumen.render(conn, filters)

with tabs[4]:
    tab_intensidad.render(conn, filters)

with tabs[5]:
    tab_frecuencia.render(conn, filters)

with tabs[6]:
    tab_grupos.render(conn, filters)
