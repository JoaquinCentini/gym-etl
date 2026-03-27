"""Constructores de gráficos Plotly para el dashboard"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from dashboard.styles import PLOTLY_TEMPLATE, MUSCLE_COLORS, MUSCLE_LABELS, COLOR_SEQUENCE


def _apply_template(fig: go.Figure) -> go.Figure:
    """Aplica template y configuración base a un gráfico"""
    fig.update_layout(template=PLOTLY_TEMPLATE)
    return fig


def _muscle_label(tipo: str) -> str:
    return MUSCLE_LABELS.get(tipo, tipo)


def _muscle_color(tipo: str) -> str:
    return MUSCLE_COLORS.get(tipo, "#888")


# ── Resumen ───────────────────────────────────────────────────────────

def chart_volumen_semanal(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return go.Figure()
    fig = px.bar(df, x="semana", y="volumen",
                 labels={"semana": "Semana", "volumen": "Volumen (kg×reps)"},
                 color_discrete_sequence=["#FF4B4B"])
    fig.update_layout(showlegend=False)
    return _apply_template(fig)


def chart_distribucion_grupos(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return go.Figure()
    df = df.copy()
    df["label"] = df["tipo_ejercicio"].map(_muscle_label)
    colors = [_muscle_color(t) for t in df["tipo_ejercicio"]]
    fig = go.Figure(data=[go.Pie(
        labels=df["label"], values=df["volumen"],
        hole=0.5, marker_colors=colors,
        textinfo="label+percent", textposition="outside",
    )])
    fig.update_layout(showlegend=False, margin=dict(l=20, r=20, t=20, b=20))
    return _apply_template(fig)


# ── Progreso ──────────────────────────────────────────────────────────

def chart_progreso_series(df: pd.DataFrame) -> go.Figure:
    """Line chart con todas las series de un ejercicio"""
    if df.empty:
        return go.Figure()
    df = df.copy()
    df["serie_label"] = "Serie " + df["numero_serie"].astype(str)
    fig = px.line(df, x="fecha", y="carga_kg", color="serie_label",
                  markers=True,
                  labels={"fecha": "Fecha", "carga_kg": "Carga (kg)",
                          "serie_label": "Serie"},
                  color_discrete_sequence=COLOR_SEQUENCE)
    fig.update_traces(line_width=2)
    return _apply_template(fig)


def chart_progreso_mejor_serie(df: pd.DataFrame) -> go.Figure:
    """Line chart con la mejor serie por sesión + tendencia"""
    if df.empty:
        return go.Figure()
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["fecha"], y=df["carga_kg"],
        mode="lines+markers", name="Mejor serie",
        line=dict(color="#FF4B4B", width=3),
        marker=dict(size=8),
    ))

    # Tendencia lineal
    if len(df) >= 3:
        x_num = np.arange(len(df))
        mask = df["carga_kg"].notna()
        if mask.sum() >= 2:
            z = np.polyfit(x_num[mask], df.loc[mask, "carga_kg"], 1)
            trend = np.polyval(z, x_num)
            fig.add_trace(go.Scatter(
                x=df["fecha"], y=trend,
                mode="lines", name="Tendencia",
                line=dict(color="#636EFA", width=2, dash="dash"),
            ))

    fig.update_layout(
        xaxis_title="Fecha", yaxis_title="Carga (kg)",
        legend=dict(orientation="h", y=1.1),
    )
    return _apply_template(fig)


# ── Records ───────────────────────────────────────────────────────────

def chart_top_records(df: pd.DataFrame, top_n: int = 15) -> go.Figure:
    if df.empty:
        return go.Figure()
    top = df.head(top_n).iloc[::-1]
    colors = [_muscle_color(t) for t in top["Grupo"]]
    fig = go.Figure(data=[go.Bar(
        x=top["Record (kg)"], y=top["Ejercicio"],
        orientation="h", marker_color=colors,
        text=top["Record (kg)"].apply(lambda x: f"{x:.1f} kg"),
        textposition="outside",
    )])
    fig.update_layout(
        xaxis_title="Carga (kg)", yaxis_title="",
        height=max(400, top_n * 35),
        margin=dict(l=200),
    )
    return _apply_template(fig)


# ── Volumen ───────────────────────────────────────────────────────────

def chart_volumen_stacked(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return go.Figure()
    df = df.copy()
    df["label"] = df["tipo_ejercicio"].map(_muscle_label)
    fig = px.bar(df, x="semana", y="volumen", color="label",
                 labels={"semana": "Semana", "volumen": "Volumen (kg×reps)",
                         "label": "Grupo"},
                 color_discrete_map={_muscle_label(k): v
                                     for k, v in MUSCLE_COLORS.items()})
    fig.update_layout(barmode="stack",
                      legend=dict(orientation="h", y=-0.2))
    return _apply_template(fig)


def chart_volumen_mesociclo(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return go.Figure()
    df = df.copy()
    df["label"] = df["tipo_ejercicio"].map(_muscle_label)
    fig = px.bar(df, x="mesociclo", y="volumen", color="label",
                 labels={"mesociclo": "Mesociclo", "volumen": "Volumen (kg×reps)",
                         "label": "Grupo"},
                 color_discrete_map={_muscle_label(k): v
                                     for k, v in MUSCLE_COLORS.items()})
    fig.update_layout(barmode="stack",
                      legend=dict(orientation="h", y=-0.2))
    return _apply_template(fig)


# ── Intensidad ────────────────────────────────────────────────────────

def chart_rir_por_sesion(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return go.Figure()
    fig = px.line(df, x="fecha", y="avg_rir", color="mesociclo",
                  markers=True,
                  labels={"fecha": "Fecha", "avg_rir": "RIR promedio",
                          "mesociclo": "Mesociclo"},
                  color_discrete_sequence=COLOR_SEQUENCE)
    fig.update_traces(line_width=2)
    fig.update_layout(
        yaxis=dict(autorange="reversed", title="RIR (menor = más intenso)"),
        legend=dict(orientation="h", y=1.1),
    )
    return _apply_template(fig)


def chart_rir_boxplot(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return go.Figure()
    fig = px.box(df, x="micro_label", y="rir_rpe", color="mesociclo",
                 labels={"micro_label": "Microciclo", "rir_rpe": "RIR",
                         "mesociclo": "Mesociclo"},
                 color_discrete_sequence=COLOR_SEQUENCE)
    fig.update_layout(
        showlegend=False,
        xaxis_tickangle=-45,
    )
    return _apply_template(fig)


# ── Frecuencia ────────────────────────────────────────────────────────

def chart_heatmap_frecuencia(df: pd.DataFrame) -> go.Figure:
    """Heatmap estilo GitHub: semanas vs días de la semana"""
    if df.empty:
        return go.Figure()

    df = df.copy()
    df["week_label"] = df["anio"].astype(str) + "-S" + df["semana_anio"].astype(str).str.zfill(2)

    dias_orden = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    pivot = df.pivot_table(index="nombre_dia_semana", columns="week_label",
                           values="series", aggfunc="sum", fill_value=0)

    # Reordenar filas
    pivot = pivot.reindex([d for d in dias_orden if d in pivot.index])

    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale=[[0, "#1a1a2e"], [0.5, "#e94560"], [1, "#FF4B4B"]],
        showscale=False,
        hovertemplate="Semana: %{x}<br>Día: %{y}<br>Series: %{z}<extra></extra>",
    ))
    fig.update_layout(
        xaxis_title="Semana", yaxis_title="",
        xaxis_tickangle=-45,
        height=300,
    )
    return _apply_template(fig)


def chart_sesiones_por_mes(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return go.Figure()
    monthly = df.groupby(["anio", "mes"]).agg(
        dias=("fecha", "nunique")
    ).reset_index()
    monthly["mes_label"] = monthly["anio"].astype(str) + "-" + monthly["mes"].astype(str).str.zfill(2)
    fig = px.bar(monthly, x="mes_label", y="dias",
                 labels={"mes_label": "Mes", "dias": "Días entrenados"},
                 color_discrete_sequence=["#FF4B4B"])
    fig.update_layout(showlegend=False)
    return _apply_template(fig)


# ── Grupos Musculares ─────────────────────────────────────────────────

def chart_radar_grupos(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return go.Figure()
    df = df.copy()
    df["label"] = df["tipo_ejercicio"].map(_muscle_label)
    colors = [_muscle_color(t) for t in df["tipo_ejercicio"]]

    fig = go.Figure(data=go.Barpolar(
        r=df["total_series"],
        theta=df["label"],
        marker_color=colors,
        opacity=0.85,
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, gridcolor="#333"),
            angularaxis=dict(gridcolor="#333"),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=False,
        height=400,
    )
    return _apply_template(fig)


def chart_volumen_grupo_temporal(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return go.Figure()
    df = df.copy()
    df["label"] = df["tipo_ejercicio"].map(_muscle_label)
    fig = px.area(df, x="semana", y="series", color="label",
                  labels={"semana": "Semana", "series": "Series",
                          "label": "Grupo"},
                  color_discrete_map={_muscle_label(k): v
                                      for k, v in MUSCLE_COLORS.items()})
    fig.update_layout(legend=dict(orientation="h", y=-0.2))
    return _apply_template(fig)
