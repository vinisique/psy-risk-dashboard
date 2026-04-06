import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="OrgPulse · Risk Intelligence",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================
# DESIGN SYSTEM (CSS)
# =========================
st.markdown("""
<style>
    /* ── IMPORTS ─────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

    /* ── BASE ────────────────────────────────────── */
    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
        background-color: #0D0F14;
        color: #E8EAF0;
    }

    .main { background-color: #0D0F14; }
    .block-container { padding: 2rem 2.5rem 4rem; max-width: 1400px; }

    /* ── SIDEBAR ─────────────────────────────────── */
    [data-testid="stSidebar"] {
        background-color: #111318;
        border-right: 1px solid #1E2130;
    }
    [data-testid="stSidebar"] .block-container { padding: 2rem 1.5rem; }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #8B8FA8;
        font-size: 0.65rem;
        font-weight: 600;
        letter-spacing: 0.15em;
        text-transform: uppercase;
    }

    /* ── HEADER ─────────────────────────────────── */
    .orgpulse-header {
        display: flex;
        align-items: flex-end;
        gap: 1.2rem;
        padding-bottom: 2rem;
        border-bottom: 1px solid #1E2130;
        margin-bottom: 2rem;
    }
    .orgpulse-logo {
        font-family: 'DM Serif Display', serif;
        font-size: 2.2rem;
        color: #E8EAF0;
        line-height: 1;
        letter-spacing: -0.02em;
    }
    .orgpulse-logo span { color: #00C9A7; }
    .orgpulse-subtitle {
        font-size: 0.78rem;
        color: #5A5F7A;
        font-weight: 400;
        letter-spacing: 0.04em;
        padding-bottom: 0.25rem;
    }
    .orgpulse-badge {
        margin-left: auto;
        background: #161924;
        border: 1px solid #1E2130;
        border-radius: 6px;
        padding: 0.4rem 0.9rem;
        font-family: 'DM Mono', monospace;
        font-size: 0.7rem;
        color: #00C9A7;
        letter-spacing: 0.06em;
    }

    /* ── KPI CARDS ───────────────────────────────── */
    .kpi-card {
        background: #111318;
        border: 1px solid #1E2130;
        border-radius: 12px;
        padding: 1.4rem 1.6rem;
        position: relative;
        overflow: hidden;
        transition: border-color 0.2s;
    }
    .kpi-card:hover { border-color: #2A2F45; }
    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, #00C9A7, #00A3FF);
        opacity: 0;
        transition: opacity 0.2s;
    }
    .kpi-card:hover::before { opacity: 1; }
    .kpi-label {
        font-size: 0.68rem;
        font-weight: 600;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #5A5F7A;
        margin-bottom: 0.75rem;
    }
    .kpi-value {
        font-family: 'DM Serif Display', serif;
        font-size: 2.4rem;
        color: #E8EAF0;
        line-height: 1;
        letter-spacing: -0.02em;
    }
    .kpi-value.danger { color: #FF4D6A; }
    .kpi-value.warning { color: #FFB547; }
    .kpi-value.success { color: #00C9A7; }
    .kpi-sub {
        font-size: 0.72rem;
        color: #5A5F7A;
        margin-top: 0.5rem;
    }

    /* ── SECTION TITLES ──────────────────────────── */
    .section-title {
        font-family: 'DM Serif Display', serif;
        font-size: 1.15rem;
        color: #E8EAF0;
        letter-spacing: -0.01em;
        margin-bottom: 1rem;
    }
    .section-label {
        font-size: 0.65rem;
        font-weight: 600;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: #00C9A7;
        margin-bottom: 0.3rem;
    }

    /* ── PANELS ──────────────────────────────────── */
    .panel {
        background: #111318;
        border: 1px solid #1E2130;
        border-radius: 12px;
        padding: 1.5rem;
    }

    /* ── PROBLEM CARDS ───────────────────────────── */
    .problem-card {
        background: #16111A;
        border: 1px solid #2D1C2A;
        border-left: 3px solid #FF4D6A;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .problem-card.warning-card {
        background: #16140F;
        border-color: #2D2510;
        border-left-color: #FFB547;
    }
    .problem-name {
        font-size: 0.82rem;
        font-weight: 500;
        color: #C8CAD8;
    }
    .problem-score {
        font-family: 'DM Mono', monospace;
        font-size: 1.1rem;
        font-weight: 500;
        color: #FF4D6A;
    }
    .problem-score.warning { color: #FFB547; }

    /* ── DIVIDER ─────────────────────────────────── */
    .custom-divider {
        border: none;
        border-top: 1px solid #1E2130;
        margin: 2rem 0;
    }

    /* ── DATAFRAME ───────────────────────────────── */
    [data-testid="stDataFrame"] {
        border: 1px solid #1E2130;
        border-radius: 10px;
        overflow: hidden;
    }
    .dvn-scroller { background: #111318 !important; }

    /* ── HIDE STREAMLIT CHROME ───────────────────── */
    #MainMenu, footer, header { visibility: hidden; }
    [data-testid="stDecoration"] { display: none; }
</style>
""", unsafe_allow_html=True)

# =========================
# PLOT THEME
# =========================
PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans", color="#8B8FA8", size=11),
    margin=dict(l=0, r=0, t=10, b=0),
    showlegend=False,
    xaxis=dict(
        gridcolor="#1E2130",
        zerolinecolor="#1E2130",
        tickfont=dict(color="#5A5F7A", size=10),
    ),
    yaxis=dict(
        gridcolor="#1E2130",
        zerolinecolor="#1E2130",
        tickfont=dict(color="#5A5F7A", size=10),
    ),
)

RISK_COLORS = {
    "Normal":  "#00C9A7",
    "Alto":    "#FFB547",
    "Crítico": "#FF4D6A",
}

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    return pd.read_parquet("base.parquet")

df_base = load_data()

# Column aliases (clean labels for display)
COL_UNIDADE = "Informe sua unidade"
COL_SETOR   = "Informe seu setor / departamento."
COL_CARGO   = "Informe seu cargo"

DIMENSAO_LABELS = {
    "score_Demandas":        "Demandas",
    "score_Controle":        "Controle",
    "score_Apoio_Chefia":    "Apoio da Chefia",
    "score_Apoio_Colegas":   "Apoio dos Colegas",
    "score_Relacionamentos": "Relacionamentos",
    "score_Cargo":           "Cargo",
    "score_Comunicacao":     "Comunicação",
}

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.markdown("### Filtros")
    st.markdown("---")

    empresa_opts = sorted(df_base["Empresa"].unique())
    empresa = st.multiselect("Empresa", empresa_opts, default=empresa_opts)

    unidade_opts = sorted(df_base[COL_UNIDADE].unique())
    unidade = st.multiselect("Unidade", unidade_opts, default=unidade_opts)

    setor_opts = sorted(df_base[COL_SETOR].unique())
    setor = st.multiselect("Setor", setor_opts, default=setor_opts)

    st.markdown("---")
    st.markdown(
        "<div style='font-size:0.65rem;color:#3A3F55;letter-spacing:0.05em'>"
        "OrgPulse · Modelo HSE · v2.0"
        "</div>",
        unsafe_allow_html=True,
    )

df = df_base[
    df_base["Empresa"].isin(empresa) &
    df_base[COL_UNIDADE].isin(unidade) &
    df_base[COL_SETOR].isin(setor)
]

# =========================
# HEADER
# =========================
st.markdown("""
<div class="orgpulse-header">
    <div>
        <div class="orgpulse-logo">Org<span>Pulse</span></div>
        <div class="orgpulse-subtitle">Psychosocial Risk Intelligence · Modelo HSE</div>
    </div>
    <div class="orgpulse-badge">LIVE ANALYSIS</div>
</div>
""", unsafe_allow_html=True)

# =========================
# KPIs
# =========================
total       = len(df)
igrp_medio  = round(df["IGRP"].mean(), 2) if total else 0
pct_alto    = round((df["risco_geral"].isin(["Alto","Crítico"])).mean() * 100, 1) if total else 0
pct_critico = round((df["risco_geral"] == "Crítico").mean() * 100, 1) if total else 0

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Colaboradores</div>
        <div class="kpi-value">{total:,}</div>
        <div class="kpi-sub">respondentes ativos</div>
    </div>""", unsafe_allow_html=True)

with c2:
    igrp_class = "danger" if igrp_medio > 70 else "warning" if igrp_medio > 50 else "success"
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">IGRP Médio</div>
        <div class="kpi-value {igrp_class}">{igrp_medio}</div>
        <div class="kpi-sub">índice geral de risco psicossocial</div>
    </div>""", unsafe_allow_html=True)

with c3:
    alto_class = "danger" if pct_alto > 40 else "warning" if pct_alto > 20 else "success"
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Alto / Crítico</div>
        <div class="kpi-value {alto_class}">{pct_alto}%</div>
        <div class="kpi-sub">colaboradores em risco elevado</div>
    </div>""", unsafe_allow_html=True)

with c4:
    crit_class = "danger" if pct_critico > 15 else "warning" if pct_critico > 5 else "success"
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Risco Crítico</div>
        <div class="kpi-value {crit_class}">{pct_critico}%</div>
        <div class="kpi-sub">requer intervenção imediata</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

# =========================
# ROW 2 — OVERVIEW
# =========================
col1, col2 = st.columns([1, 1.6], gap="large")

with col1:
    st.markdown("<div class='section-label'>Visão Geral</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Distribuição de Risco</div>", unsafe_allow_html=True)

    risco = df["risco_geral"].value_counts().reset_index()
    risco.columns = ["Risco", "Qtd"]
    risco["Pct"] = (risco["Qtd"] / risco["Qtd"].sum() * 100).round(1)
    risco["Cor"] = risco["Risco"].map(RISK_COLORS)

    fig = go.Figure(go.Bar(
        x=risco["Risco"],
        y=risco["Qtd"],
        marker=dict(
            color=risco["Cor"],
            line=dict(width=0),
        ),
        customdata=risco["Pct"],
        hovertemplate="<b>%{x}</b><br>%{y} colaboradores<br>%{customdata}%<extra></extra>",
        text=risco["Pct"].apply(lambda v: f"{v}%"),
        textposition="outside",
        textfont=dict(color="#8B8FA8", size=11),
    ))
    fig.update_layout(**PLOT_LAYOUT, height=280)
    fig.update_xaxes(showgrid=False)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown("<div class='section-label'>Por Setor</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>IGRP Médio por Setor</div>", unsafe_allow_html=True)

    setor_df = (
        df.groupby(COL_SETOR)["IGRP"]
        .mean()
        .reset_index()
        .rename(columns={COL_SETOR: "Setor", "IGRP": "IGRP"})
        .sort_values("IGRP", ascending=True)
        .tail(10)
    )

    def igrp_color(v):
        if v > 70: return "#FF4D6A"
        if v > 50: return "#FFB547"
        return "#00C9A7"

    setor_df["Cor"] = setor_df["IGRP"].apply(igrp_color)

    fig = go.Figure(go.Bar(
        x=setor_df["IGRP"],
        y=setor_df["Setor"],
        orientation="h",
        marker=dict(color=setor_df["Cor"], line=dict(width=0)),
        hovertemplate="<b>%{y}</b><br>IGRP: %{x:.1f}<extra></extra>",
        text=setor_df["IGRP"].round(1),
        textposition="outside",
        textfont=dict(color="#8B8FA8", size=10),
    ))
    fig.update_layout(**PLOT_LAYOUT, height=280)
    fig.update_yaxes(showgrid=False)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

# =========================
# ROW 3 — DIMENSIONS
# =========================
col1, col2 = st.columns([1.6, 1], gap="large")

with col1:
    st.markdown("<div class='section-label'>Diagnóstico HSE</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Score por Dimensão</div>", unsafe_allow_html=True)

    dim_cols = list(DIMENSAO_LABELS.keys())
    heatmap = df[dim_cols].mean().reset_index()
    heatmap.columns = ["Col", "Score"]
    heatmap["Dimensão"] = heatmap["Col"].map(DIMENSAO_LABELS)
    heatmap["Cor"] = heatmap["Score"].apply(igrp_color)
    heatmap = heatmap.sort_values("Score", ascending=True)

    fig = go.Figure(go.Bar(
        x=heatmap["Score"],
        y=heatmap["Dimensão"],
        orientation="h",
        marker=dict(
            color=heatmap["Cor"],
            opacity=0.85,
            line=dict(width=0),
        ),
        hovertemplate="<b>%{y}</b><br>Score: %{x:.2f}<extra></extra>",
        text=heatmap["Score"].round(2),
        textposition="outside",
        textfont=dict(color="#8B8FA8", size=10),
    ))
    fig.update_layout(**PLOT_LAYOUT, height=310)
    fig.update_yaxes(showgrid=False)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown("<div class='section-label'>Atenção Imediata</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Dimensões Críticas</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    problemas = heatmap.sort_values("Score").head(3)
    for i, (_, row) in enumerate(problemas.iterrows()):
        card_class = "problem-card" if i == 0 else "problem-card warning-card"
        score_class = "problem-score" if i == 0 else "problem-score warning"
        st.markdown(f"""
        <div class="{card_class}">
            <div class="problem-name">{row['Dimensão']}</div>
            <div class="{score_class}">{row['Score']:.2f}</div>
        </div>""", unsafe_allow_html=True)

    # Radar chart
    categories = heatmap["Dimensão"].tolist()
    values     = heatmap["Score"].tolist()
    # close the polygon
    categories_c = categories + [categories[0]]
    values_c     = values + [values[0]]

    fig_r = go.Figure(go.Scatterpolar(
        r=values_c,
        theta=categories_c,
        fill="toself",
        fillcolor="rgba(0,201,167,0.08)",
        line=dict(color="#00C9A7", width=1.5),
    ))
    fig_r.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans", color="#5A5F7A", size=9),
        margin=dict(l=20, r=20, t=20, b=20),
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            angularaxis=dict(tickcolor="#1E2130", linecolor="#1E2130", gridcolor="#1E2130"),
            radialaxis=dict(tickcolor="#1E2130", linecolor="#1E2130", gridcolor="#1E2130",
                            showticklabels=False),
        ),
        height=220,
        showlegend=False,
    )
    st.plotly_chart(fig_r, use_container_width=True)

st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

# =========================
# ROW 4 — TABLES
# =========================
col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown("<div class='section-label'>Detalhamento</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Top Setores de Risco</div>", unsafe_allow_html=True)

    _s_igrp = df.groupby(COL_SETOR)["IGRP"].agg(["mean", "count"]).reset_index()
    _s_igrp.columns = ["Setor", "IGRP", "N"]
    _s_risco = (
        df.assign(_em_risco=df["risco_geral"].isin(["Alto", "Crítico"]))
        .groupby(COL_SETOR)["_em_risco"]
        .mean()
        .reset_index()
        .rename(columns={COL_SETOR: "Setor", "_em_risco": "% em Risco"})
    )
    setor_risco = (
        _s_igrp.merge(_s_risco, on="Setor")
        .sort_values("IGRP", ascending=False)
        .head(10)
    )
    setor_risco["IGRP"]       = setor_risco["IGRP"].round(2)
    setor_risco["% em Risco"] = (setor_risco["% em Risco"] * 100).round(1).astype(str) + "%"

    st.dataframe(
        setor_risco,
        use_container_width=True,
        hide_index=True,
        column_config={
            "IGRP": st.column_config.ProgressColumn(
                "IGRP", min_value=0, max_value=100, format="%.2f"
            )
        }
    )

with col2:
    st.markdown("<div class='section-label'>Detalhamento</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Top Cargos de Risco</div>", unsafe_allow_html=True)

    _c_igrp = df.groupby(COL_CARGO)["IGRP"].agg(["mean", "count"]).reset_index()
    _c_igrp.columns = ["Cargo", "IGRP", "N"]
    _c_risco = (
        df.assign(_em_risco=df["risco_geral"].isin(["Alto", "Crítico"]))
        .groupby(COL_CARGO)["_em_risco"]
        .mean()
        .reset_index()
        .rename(columns={COL_CARGO: "Cargo", "_em_risco": "% em Risco"})
    )
    cargo_risco = (
        _c_igrp.merge(_c_risco, on="Cargo")
        .sort_values("IGRP", ascending=False)
        .head(10)
    )
    cargo_risco["IGRP"]       = cargo_risco["IGRP"].round(2)
    cargo_risco["% em Risco"] = (cargo_risco["% em Risco"] * 100).round(1).astype(str) + "%"

    st.dataframe(
        cargo_risco,
        use_container_width=True,
        hide_index=True,
        column_config={
            "IGRP": st.column_config.ProgressColumn(
                "IGRP", min_value=0, max_value=100, format="%.2f"
            )
        }
    )

st.markdown("<hr class='custom-divider'>", unsafe_allow_html=True)

# =========================
# DETAILED BASE (COLLAPSED)
# =========================
with st.expander("📋  Base de dados completa", expanded=False):
    display_cols = {
        "Empresa": "Empresa",
        COL_UNIDADE: "Unidade",
        COL_SETOR:   "Setor",
        COL_CARGO:   "Cargo",
        "IGRP":      "IGRP",
        "risco_geral": "Risco Geral",
    }
    st.dataframe(
        df[list(display_cols.keys())].rename(columns=display_cols),
        use_container_width=True,
        hide_index=True,
    )
