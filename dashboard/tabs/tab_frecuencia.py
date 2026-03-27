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

    max_gap = dias_descanso + 1  # ej: 1 día descanso → gap máximo de 2
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


def _peor_mes(df: pd.DataFrame) -> tuple[str, int]:
    """Retorna (nombre_mes, días_entrenados) del mes con menos actividad.
    Solo considera meses completos (excluye el primero y el último si son parciales)."""
    if df.empty:
        return ("—", 0)

    dias_por_mes = (
        df.groupby(["anio", "mes"])["fecha"]
        .nunique()
        .reset_index()
        .rename(columns={"fecha": "dias"})
    )
    if len(dias_por_mes) <= 2:
        # Con 1-2 meses no podemos excluir parciales, usamos todo
        peor = dias_por_mes.loc[dias_por_mes["dias"].idxmin()]
    else:
        # Excluir primer y último mes (posiblemente incompletos)
        dias_por_mes = dias_por_mes.iloc[1:-1]
        peor = dias_por_mes.loc[dias_por_mes["dias"].idxmin()]

    nombre = MESES_ES.get(int(peor["mes"]), "?")
    return (f"{nombre} {int(peor['anio'])}", int(peor["dias"]))


def render(conn: duckdb.DuckDBPyConnection, f: Filters):
    df = get_frecuencia_diaria(conn, f)

    if df.empty:
        st.info("Sin datos de frecuencia")
        return

    total_dias = df["fecha"].nunique()
    semanas = df.groupby(["anio", "semana_anio"])["fecha"].nunique().reset_index()
    dias_por_semana = semanas["fecha"].mean() if not semanas.empty else 0

    # Selector de días de descanso
    dias_descanso = st.slider(
        "Días de descanso permitidos en la racha",
        min_value=1, max_value=5, value=1,
        key="frecuencia_dias_descanso",
    )

    racha = _calcular_racha(df["fecha"], dias_descanso)
    peor_mes_nombre, peor_mes_dias = _peor_mes(df)

    # KPIs
    cols = st.columns(4)
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
            "Racha más larga", f"{racha} sesiones",
            subtitle=f"(max {dias_descanso} día{'s' if dias_descanso > 1 else ''} descanso)",
            color="#00CC96"
        ))
    with cols[3]:
        st.html(kpi_card(
            "Peor mes", peor_mes_nombre,
            subtitle=f"solo {peor_mes_dias} días entrenados",
            color="#EF553B"
        ))

    st.markdown("---")

    # Heatmap
    st.subheader("Calendario de entrenamiento")
    st.plotly_chart(chart_heatmap_frecuencia(df), use_container_width=True)

    # Sesiones por mes
    st.subheader("Días entrenados por mes")
    st.plotly_chart(chart_sesiones_por_mes(df), use_container_width=True)
