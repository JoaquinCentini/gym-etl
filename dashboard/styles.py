"""Estilos, colores y componentes HTML del dashboard"""

import streamlit as st
import plotly.graph_objects as go

# Paleta de colores por grupo muscular
MUSCLE_COLORS = {
    "Tracción": "#636EFA",
    "Empuje": "#EF553B",
    "DomCaderaxIsquiosxGlúteos": "#00CC96",
    "DomRodillaxCuádriceps": "#AB63FA",
    "CORE": "#FFA15A",
    "Tríceps": "#19D3F3",
    "Biceps": "#FF6692",
    "DeltoideMedio": "#B6E880",
    "Abs": "#FF97FF",
    "GemelosxSóleo": "#FECB52",
}

# Nombres cortos para display
MUSCLE_LABELS = {
    "Tracción": "Tracción",
    "Empuje": "Empuje",
    "DomCaderaxIsquiosxGlúteos": "Cadera/Glúteos",
    "DomRodillaxCuádriceps": "Cuádriceps",
    "CORE": "Core",
    "Tríceps": "Tríceps",
    "Biceps": "Bíceps",
    "DeltoideMedio": "Deltoides",
    "Abs": "Abdominales",
    "GemelosxSóleo": "Gemelos",
}

# Secuencia de colores para gráficos genéricos
COLOR_SEQUENCE = list(MUSCLE_COLORS.values())

# Template base para Plotly
PLOTLY_TEMPLATE = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#FAFAFA", family="sans-serif"),
        xaxis=dict(gridcolor="#333", zerolinecolor="#555"),
        yaxis=dict(gridcolor="#333", zerolinecolor="#555"),
        colorway=COLOR_SEQUENCE,
        hoverlabel=dict(bgcolor="#262730", font_color="#FAFAFA"),
        margin=dict(l=40, r=20, t=40, b=40),
    )
)


def kpi_card(title: str, value: str, subtitle: str = "", color: str = "#FF4B4B"):
    """Genera HTML para una tarjeta KPI estilizada"""
    return f"""
    <div style="
        background: linear-gradient(135deg, {color}22, {color}11);
        border-left: 4px solid {color};
        border-radius: 8px;
        padding: 16px 20px;
        margin: 4px 0;
    ">
        <div style="font-size: 0.85rem; color: #999; text-transform: uppercase;
                    letter-spacing: 0.05em; margin-bottom: 4px;">
            {title}
        </div>
        <div style="font-size: 2rem; font-weight: 700; color: #FAFAFA;">
            {value}
        </div>
        <div style="font-size: 0.8rem; color: #888; margin-top: 2px;">
            {subtitle}
        </div>
    </div>
    """


def inject_global_css():
    """Inyecta CSS global para el dashboard"""
    st.markdown("""
    <style>
        /* Tabs styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 8px 16px;
            border-radius: 8px 8px 0 0;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] > div {
            padding-top: 1rem;
        }

        /* Hide Streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header [data-testid="stDecoration"] {display: none;}

        /* Metric cards spacing */
        [data-testid="stMetric"] {
            background: #262730;
            border-radius: 8px;
            padding: 12px 16px;
        }
    </style>
    """, unsafe_allow_html=True)
