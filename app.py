"""
Dashboard HSE-IT — Plataforma Vivamente 360°
Baseado nos slides 14–23 do PPTX NR-1
Parquets esperados: base.parquet, setor.parquet, cargo.parquet, unidade.parquet
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
import os

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard HSE-IT · NR-1",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# PALETA & TEMA
# ─────────────────────────────────────────────
COR_VERDE   = "#2D9E75"
COR_AMARELO = "#F5A623"
COR_LARANJA = "#E8621A"
COR_VERMELHO= "#D63B3B"
COR_CINZA   = "#8B8FA8"
COR_BG      = "#0F1117"
COR_CARD    = "#1A1D27"
COR_BORDA   = "#2A2D3E"
COR_TEXTO   = "#E8EAF0"
COR_MUTED   = "#6B7280"
COR_ACCENT  = "#4F8EF7"

RISCO_CORES = {
    "Baixo Risco":    COR_VERDE,
    "Risco Médio":    COR_AMARELO,
    "Risco Moderado": COR_LARANJA,
    "Alto Risco":     COR_VERMELHO,
    "Aceitável":      COR_VERDE,
    "Moderado":       COR_AMARELO,
    "Importante":     COR_LARANJA,
    "Crítico":        COR_VERMELHO,
    "Sem dados":      COR_CINZA,
}

DIMENSOES = [
    "Demandas", "Controle", "Apoio_Chefia",
    "Apoio_Colegas", "Relacionamentos", "Cargo", "Comunicacao_Mudancas"
]
DIMENSOES_LABEL = {
    "Demandas": "Demandas",
    "Controle": "Controle",
    "Apoio_Chefia": "Apoio da Chefia",
    "Apoio_Colegas": "Apoio dos Colegas",
    "Relacionamentos": "Relacionamentos",
    "Cargo": "Cargo / Função",
    "Comunicacao_Mudancas": "Comunicação e Mudanças",
}
DIM_NEGATIVAS = {"Demandas", "Relacionamentos"}

NIVEIS_ORDEM = ["Baixo Risco", "Risco Médio", "Risco Moderado", "Alto Risco"]
NIVEIS_GERAL_ORDEM = ["Aceitável", "Moderado", "Importante", "Crítico"]

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {{
    font-family: 'DM Sans', sans-serif;
    background-color: {COR_BG};
    color: {COR_TEXTO};
}}
.block-container {{ padding: 1.5rem 2rem 3rem; }}
[data-testid="stSidebar"] {{
    background-color: {COR_CARD} !important;
    border-right: 1px solid {COR_BORDA};
}}
[data-testid="stSidebar"] * {{ color: {COR_TEXTO} !important; }}

/* Metric cards */
.kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 14px; margin-bottom: 2rem; }}
.kpi-card {{
    background: {COR_CARD};
    border: 1px solid {COR_BORDA};
    border-radius: 12px;
    padding: 18px 20px;
}}
.kpi-label {{ font-size: 11px; font-weight: 500; color: {COR_MUTED}; text-transform: uppercase; letter-spacing: .08em; margin-bottom: 6px; }}
.kpi-value {{ font-size: 28px; font-weight: 600; color: {COR_TEXTO}; line-height: 1; }}
.kpi-sub {{ font-size: 12px; color: {COR_MUTED}; margin-top: 4px; }}
.kpi-accent {{ color: {COR_ACCENT}; }}

/* Section titles */
.section-title {{
    font-size: 13px; font-weight: 600; color: {COR_MUTED};
    text-transform: uppercase; letter-spacing: .1em;
    margin: 2rem 0 1rem;
    padding-bottom: 8px;
    border-bottom: 1px solid {COR_BORDA};
}}

/* Risk badges */
.badge {{ display: inline-block; padding: 2px 10px; border-radius: 99px; font-size: 11px; font-weight: 600; }}
.badge-verde   {{ background: rgba(45,158,117,.18); color: {COR_VERDE}; }}
.badge-amarelo {{ background: rgba(245,166,35,.18); color: {COR_AMARELO}; }}
.badge-laranja {{ background: rgba(232,98,26,.18);  color: {COR_LARANJA}; }}
.badge-vermelho{{ background: rgba(214,59,59,.18);  color: {COR_VERMELHO}; }}

/* Page header */
.page-header {{
    background: linear-gradient(135deg, #1A1D27 0%, #0F1117 100%);
    border: 1px solid {COR_BORDA};
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}}
.page-header h1 {{ font-size: 22px; font-weight: 600; margin: 0; color: {COR_TEXTO}; }}
.page-header p  {{ font-size: 13px; color: {COR_MUTED}; margin: 4px 0 0; }}

/* Tabs */
[data-baseweb="tab-list"] {{ background: {COR_CARD} !important; border-radius: 10px; padding: 4px; gap: 2px; }}
[data-baseweb="tab"] {{ background: transparent !important; border-radius: 8px !important; color: {COR_MUTED} !important; font-weight: 500 !important; }}
[aria-selected="true"][data-baseweb="tab"] {{ background: {COR_BG} !important; color: {COR_TEXTO} !important; }}

/* Plotly charts bg */
.js-plotly-plot .plotly .bg {{ fill: transparent !important; }}

/* Divider */
.divider {{ border: none; border-top: 1px solid {COR_BORDA}; margin: 1.5rem 0; }}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def badge_risco(nivel: str) -> str:
    mapa = {
        "Baixo Risco": "verde", "Aceitável": "verde",
        "Risco Médio": "amarelo", "Moderado": "amarelo",
        "Risco Moderado": "laranja", "Importante": "laranja",
        "Alto Risco": "vermelho", "Crítico": "vermelho",
    }
    cls = mapa.get(nivel, "amarelo")
    return f'<span class="badge badge-{cls}">{nivel}</span>'


def cor_nivel(nivel: str) -> str:
    return RISCO_CORES.get(nivel, COR_CINZA)


def plotly_layout(fig, height=380, margin=None):
    m = margin or dict(l=20, r=20, t=30, b=20)
    fig.update_layout(
        height=height,
        margin=m,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans", color=COR_TEXTO, size=12),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=COR_BORDA,
            font=dict(size=11),
        ),
        xaxis=dict(gridcolor=COR_BORDA, zerolinecolor=COR_BORDA),
        yaxis=dict(gridcolor=COR_BORDA, zerolinecolor=COR_BORDA),
    )
    return fig


def nivel_geral_para_cor(nivel: str) -> str:
    return {
        "Aceitável": COR_VERDE,
        "Moderado": COR_AMARELO,
        "Importante": COR_LARANJA,
        "Crítico": COR_VERMELHO,
    }.get(nivel, COR_CINZA)


def classificar_NR(nr: float) -> str:
    if nr >= 13: return "Crítico"
    if nr >= 9:  return "Importante"
    if nr >= 5:  return "Moderado"
    return "Aceitável"


def score_para_classificacao(score: float, dim: str) -> str:
    neg = dim in DIM_NEGATIVAS
    if neg:
        if score >= 3.1: return "Alto Risco"
        if score >= 2.1: return "Risco Moderado"
        if score >= 1.1: return "Risco Médio"
        return "Baixo Risco"
    else:
        if score <= 1.0: return "Alto Risco"
        if score <= 2.0: return "Risco Moderado"
        if score <= 3.0: return "Risco Médio"
        return "Baixo Risco"


def _nr_row_color(val):
    """Retorna estilo CSS para células NR — sem dependência de matplotlib."""
    try:
        v = float(val)
    except (TypeError, ValueError):
        return ""
    if v >= 13:
        return f"background-color: rgba(214,59,59,0.35); color: {COR_TEXTO}"
    if v >= 9:
        return f"background-color: rgba(232,98,26,0.30); color: {COR_TEXTO}"
    if v >= 5:
        return f"background-color: rgba(245,166,35,0.25); color: {COR_TEXTO}"
    return f"background-color: rgba(45,158,117,0.20); color: {COR_TEXTO}"


def _perc_row_color(val):
    """Coloração para células de percentual (0–100) — sem matplotlib."""
    try:
        v = float(str(val).replace("%", ""))
    except (TypeError, ValueError):
        return ""
    if v >= 60:
        return f"background-color: rgba(214,59,59,0.30); color: {COR_TEXTO}"
    if v >= 35:
        return f"background-color: rgba(232,98,26,0.25); color: {COR_TEXTO}"
    if v >= 15:
        return f"background-color: rgba(245,166,35,0.20); color: {COR_TEXTO}"
    return f"background-color: rgba(45,158,117,0.15); color: {COR_TEXTO}"

# ─────────────────────────────────────────────
# CARGA DE DADOS
# ─────────────────────────────────────────────

@st.cache_data
def load_data(path_base, path_setor, path_cargo, path_unidade=None):
    base     = pd.read_parquet(path_base)
    setor    = pd.read_parquet(path_setor)
    cargo    = pd.read_parquet(path_cargo)
    unidade  = pd.read_parquet(path_unidade) if path_unidade and os.path.exists(path_unidade) else None
    return base, setor, cargo, unidade


def agg_grupo(df, col, rename):
    g = df.groupby(col).agg(
        n_colaboradores=(col, "count"),
        IGRP=("IGRP", "mean"),
        NR_geral=("NR_geral", "mean"),
        **{f"score_{d}": (f"score_{d}", "mean") for d in DIMENSOES if f"score_{d}" in df.columns},
        **{f"NR_{d}": (f"NR_{d}", "mean") for d in DIMENSOES if f"NR_{d}" in df.columns},
        perc_critico=("risco_geral", lambda x: (x == "Crítico").mean()),
        perc_importante=("risco_geral", lambda x: (x == "Importante").mean()),
        perc_risco_alto=("risco_geral", lambda x: x.isin(["Crítico", "Importante"]).mean()),
    ).reset_index().rename(columns={col: rename})

    g["classificacao"] = g["NR_geral"].apply(classificar_NR)
    g["rank_risco"] = g["NR_geral"].rank(ascending=False, method="min")
    return g.sort_values(["perc_risco_alto", "NR_geral"], ascending=False)

# ─────────────────────────────────────────────
# CAMINHOS DOS DADOS (REPOSITÓRIO)
# ─────────────────────────────────────────────

BASE_PATH = "base.parquet"
SETOR_PATH = "setor.parquet"
CARGO_PATH = "cargo.parquet"
UNIDADE_PATH = "unidade.parquet"

# ─────────────────────────────────────────────
# LOAD
# ─────────────────────────────────────────────

base, setor, cargo, unidade = load_data(
    BASE_PATH,
    SETOR_PATH,
    CARGO_PATH,
    UNIDADE_PATH
)

# ─────────────────────────────────────────────
# SIDEBAR — apenas filtros
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("---")
    st.markdown("### 🔍 Filtros globais")

    empresas_disp = sorted(base["Empresa"].dropna().unique())
    sel_empresa = st.multiselect("Empresa", empresas_disp, default=empresas_disp)

    unidades_disp = sorted(base[base["Empresa"].isin(sel_empresa)]["Informe sua unidade"].dropna().unique())
    sel_unidade = st.multiselect("Unidade", unidades_disp, default=unidades_disp)

    setores_disp = sorted(base[base["Informe sua unidade"].isin(sel_unidade)]["Informe seu setor / departamento."].dropna().unique())
    sel_setor = st.multiselect("Setor", setores_disp, default=setores_disp)

    cargos_disp = sorted(base[base["Informe seu setor / departamento."].isin(sel_setor)]["Informe seu cargo"].dropna().unique())
    sel_cargo = st.multiselect("Cargo", cargos_disp, default=cargos_disp)

    top_n = st.slider("Top N (rankings)", 3, 10, 5)

# ─────────────────────────────────────────────
# FILTRAR BASE
# ─────────────────────────────────────────────

base_f = base[
    base["Empresa"].isin(sel_empresa) &
    base["Informe sua unidade"].isin(sel_unidade) &
    base["Informe seu setor / departamento."].isin(sel_setor) &
    base["Informe seu cargo"].isin(sel_cargo)
].copy()

def reaplicar_agg(df, col, rename):
    if df.empty: return pd.DataFrame()
    g = df.groupby(col).agg(
        n_colaboradores=(col, "count"),
        IGRP=("IGRP", "mean"),
        NR_geral=("NR_geral", "mean"),
        **{f"score_{d}": (f"score_{d}", "mean") for d in DIMENSOES if f"score_{d}" in df.columns},
        **{f"NR_{d}": (f"NR_{d}", "mean") for d in DIMENSOES if f"NR_{d}" in df.columns},
        perc_critico=("risco_geral", lambda x: (x == "Crítico").mean()),
        perc_importante=("risco_geral", lambda x: (x == "Importante").mean()),
        perc_risco_alto=("risco_geral", lambda x: x.isin(["Crítico", "Importante"]).mean()),
    ).reset_index().rename(columns={col: rename})
    g["classificacao"] = g["NR_geral"].apply(classificar_NR)
    g["rank_risco"] = g["NR_geral"].rank(ascending=False, method="min")
    return g.sort_values(["perc_risco_alto", "NR_geral"], ascending=False)

setor_f   = reaplicar_agg(base_f, "Informe seu setor / departamento.", "Setor")
cargo_f   = reaplicar_agg(base_f, "Informe seu cargo", "Cargo")
unidade_f = reaplicar_agg(base_f, "Informe sua unidade", "Unidade")
empresa_f = reaplicar_agg(base_f, "Empresa", "Empresa")

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────

n_total = len(base_f)
perc_critico = (base_f["risco_geral"] == "Crítico").mean() * 100 if n_total else 0
perc_alto    = base_f["risco_geral"].isin(["Crítico", "Importante"]).mean() * 100 if n_total else 0
igrp_medio   = base_f["IGRP"].mean() if n_total else 0
nr_medio     = base_f["NR_geral"].mean() if n_total else 0

st.markdown(f"""
<div class="page-header">
  <div>
    <h1>🧠 Dashboard HSE-IT · Riscos Psicossociais</h1>
    <p>Plataforma Vivamente 360° — NR-1 · {n_total} respondentes no filtro atual</p>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-label">Respondentes</div>
    <div class="kpi-value">{n_total:,}</div>
    <div class="kpi-sub">no filtro selecionado</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">IGRP Médio</div>
    <div class="kpi-value kpi-accent">{igrp_medio:.2f}</div>
    <div class="kpi-sub">escala 0–4</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">NR Geral Médio</div>
    <div class="kpi-value">{nr_medio:.1f}</div>
    <div class="kpi-sub">escala 1–16</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Em Risco Alto/Crítico</div>
    <div class="kpi-value" style="color:{COR_LARANJA};">{perc_alto:.1f}%</div>
    <div class="kpi-sub">Importante + Crítico</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Em Risco Crítico</div>
    <div class="kpi-value" style="color:{COR_VERMELHO};">{perc_critico:.1f}%</div>
    <div class="kpi-sub">NR ≥ 13</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# TABS PRINCIPAIS
# ─────────────────────────────────────────────

tabs = st.tabs([
    "📊 Visão Geral",
    "📐 Por Dimensão",
    "❓ Por Questão",
    "🏢 Score de Clima",
    "⚕️ Risco de Saúde",
    "🔥 Impacto Org.",
    "🌡️ Heatmap",
    "👔 Por Cargo",
    "📋 PGR",
])

# ══════════════════════════════════════════════
# TAB 1 — VISÃO GERAL
# ══════════════════════════════════════════════
with tabs[0]:

    st.markdown('<div class="section-title">Slide 14 · Índice Geral de Riscos Psicossociais (IGRP) por Dimensão</div>', unsafe_allow_html=True)

    scores_dim = {}
    class_dim  = {}
    for d in DIMENSOES:
        col_s = f"score_{d}"
        col_c = f"class_{d}"
        scores_dim[d] = base_f[col_s].mean() if col_s in base_f.columns else 0
        class_dim[d]  = score_para_classificacao(scores_dim[d], d)

    labels = [DIMENSOES_LABEL[d] for d in DIMENSOES]
    vals   = [round(scores_dim[d], 3) for d in DIMENSOES]
    cores  = [cor_nivel(class_dim[d]) for d in DIMENSOES]

    fig_igrp = go.Figure()
    fig_igrp.add_trace(go.Bar(
        x=vals, y=labels,
        orientation="h",
        marker_color=cores,
        marker_line_width=0,
        text=[f"{v:.2f}" for v in vals],
        textposition="outside",
        textfont=dict(size=12, color=COR_TEXTO),
    ))
    fig_igrp.add_vline(x=2, line_dash="dot", line_color=COR_MUTED, line_width=1,
                       annotation_text="Ponto central (2.0)", annotation_font_color=COR_MUTED,
                       annotation_position="top right")
    fig_igrp.update_layout(
        xaxis=dict(range=[0, 4.5], title="Score médio (0–4)", gridcolor=COR_BORDA),
        yaxis=dict(title=""),
    )
    plotly_layout(fig_igrp, height=360)
    st.plotly_chart(fig_igrp, use_container_width=True)

    cols_leg = st.columns(4)
    for i, (nivel, cor) in enumerate([("Baixo Risco", COR_VERDE), ("Risco Médio", COR_AMARELO),
                                       ("Risco Moderado", COR_LARANJA), ("Alto Risco", COR_VERMELHO)]):
        with cols_leg[i]:
            st.markdown(f'<div style="display:flex;align-items:center;gap:8px;font-size:12px;color:{COR_MUTED};">'
                        f'<div style="width:12px;height:12px;border-radius:3px;background:{cor};"></div>{nivel}</div>',
                        unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    st.markdown('<div class="section-title">Slide 15 · % de Trabalhadores por Nível de Risco Global</div>', unsafe_allow_html=True)

    col_pizza, col_barra = st.columns([1, 1])

    with col_pizza:
        dist_risco = base_f["risco_geral"].value_counts()
        ordem = ["Aceitável", "Moderado", "Importante", "Crítico"]
        labels_p = [o for o in ordem if o in dist_risco.index]
        vals_p   = [dist_risco[o] for o in labels_p]
        cores_p  = [nivel_geral_para_cor(o) for o in labels_p]

        fig_pizza = go.Figure(go.Pie(
            labels=labels_p, values=vals_p,
            marker=dict(colors=cores_p, line=dict(color=COR_BG, width=2)),
            hole=0.55,
            textinfo="percent",
            textfont=dict(size=13, color=COR_TEXTO),
            insidetextorientation="horizontal",
        ))
        fig_pizza.update_layout(
            annotations=[dict(text=f"<b>{n_total}</b><br>pessoas", x=0.5, y=0.5,
                              font=dict(size=14, color=COR_TEXTO), showarrow=False)],
            showlegend=True,
            legend=dict(orientation="v", x=1, y=0.5, font=dict(size=12)),
        )
        plotly_layout(fig_pizza, height=320)
        st.plotly_chart(fig_pizza, use_container_width=True)

    with col_barra:
        fig_abs = go.Figure()
        for nivel in ordem:
            cnt = dist_risco.get(nivel, 0)
            pct = cnt / n_total * 100 if n_total else 0
            fig_abs.add_trace(go.Bar(
                x=[nivel], y=[cnt],
                name=nivel,
                marker_color=nivel_geral_para_cor(nivel),
                marker_line_width=0,
                text=[f"{pct:.1f}%<br>({cnt})"],
                textposition="outside",
                textfont=dict(size=11, color=COR_TEXTO),
            ))
        fig_abs.update_layout(
            showlegend=False,
            xaxis=dict(title=""),
            yaxis=dict(title="Nº de trabalhadores", gridcolor=COR_BORDA),
            bargap=0.35,
        )
        plotly_layout(fig_abs, height=320)
        st.plotly_chart(fig_abs, use_container_width=True)


# ══════════════════════════════════════════════
# TAB 2 — POR DIMENSÃO
# ══════════════════════════════════════════════
with tabs[1]:
    st.markdown('<div class="section-title">Slide 16 · Distribuição de Nível de Risco por Dimensão do HSE-IT</div>', unsafe_allow_html=True)

    rows_dim = []
    for d in DIMENSOES:
        col_c = f"class_{d}"
        if col_c not in base_f.columns: continue
        vc = base_f[col_c].value_counts()
        total = vc.sum()
        for nivel in NIVEIS_ORDEM:
            cnt = vc.get(nivel, 0)
            rows_dim.append({
                "Dimensão": DIMENSOES_LABEL[d],
                "Nível": nivel,
                "Qtd": cnt,
                "Perc": cnt / total * 100 if total else 0,
            })

    df_dim = pd.DataFrame(rows_dim)

    if not df_dim.empty:
        fig_stack = go.Figure()
        for nivel in NIVEIS_ORDEM:
            sub = df_dim[df_dim["Nível"] == nivel]
            fig_stack.add_trace(go.Bar(
                name=nivel,
                x=sub["Dimensão"],
                y=sub["Perc"],
                marker_color=cor_nivel(nivel),
                marker_line_width=0,
                text=sub["Perc"].apply(lambda v: f"{v:.0f}%" if v >= 5 else ""),
                textposition="inside",
                textfont=dict(size=11, color="#fff"),
            ))
        fig_stack.update_layout(
            barmode="stack",
            xaxis=dict(title=""),
            yaxis=dict(title="% de respondentes", gridcolor=COR_BORDA, range=[0, 105]),
            legend=dict(orientation="h", y=1.08, x=0, font=dict(size=11)),
        )
        plotly_layout(fig_stack, height=420)
        st.plotly_chart(fig_stack, use_container_width=True)

    st.markdown('<div class="section-title">Tabela detalhada por dimensão</div>', unsafe_allow_html=True)
    if not df_dim.empty:
        pivot = df_dim.pivot_table(index="Dimensão", columns="Nível", values="Perc", fill_value=0)
        pivot = pivot.reindex(columns=[c for c in NIVEIS_ORDEM if c in pivot.columns])
        pivot = pivot.round(1)

        # Coloração sem matplotlib: aplicamos _perc_row_color em cada célula
        styled = pivot.style.applymap(_perc_row_color).format("{:.1f}%")
        st.dataframe(styled, use_container_width=True, height=320)


# ══════════════════════════════════════════════
# TAB 3 — POR QUESTÃO
# ══════════════════════════════════════════════
with tabs[2]:
    st.markdown('<div class="section-title">Slide 17 · Distribuição de Respostas por Questão do HSE-IT</div>', unsafe_allow_html=True)

    col_q_detect = [c for c in base_f.columns if c.startswith("Q") and c[1:].isdigit()]
    if not col_q_detect:
        known = {"Empresa","Informe sua unidade","Informe seu setor / departamento.","Informe seu cargo",
                 "IGRP","NR_geral","risco_geral","qtd_dimensoes_alto"}
        col_q_detect = [c for c in base_f.columns
                        if c not in known
                        and not c.startswith("score_")
                        and not c.startswith("NR_")
                        and not c.startswith("class_")
                        and not c.startswith("P_")
                        and not c.startswith("S_")]

    if col_q_detect:
        dim_por_q = {}
        mapa_dim = {
            "Demandas": [1,2,3,4,5,6,7,8],
            "Controle": [9,10,11,12,13,14],
            "Apoio_Chefia": [15,16,17,18,19],
            "Apoio_Colegas": [20,21,22,23],
            "Relacionamentos": [24,25,26,27],
            "Cargo": [28,29,30,31,32],
            "Comunicacao_Mudancas": [33,34,35],
        }
        for d, qs in mapa_dim.items():
            for q in qs:
                dim_por_q[q] = d

        sel_dim_q = st.selectbox("Filtrar por dimensão", ["Todas"] + [DIMENSOES_LABEL[d] for d in DIMENSOES])

        rows_q = []
        for i, col in enumerate(col_q_detect[:35], start=1):
            vc = base_f[col].value_counts().reindex([0,1,2,3,4], fill_value=0)
            total_q = vc.sum()
            dim_q = dim_por_q.get(i, "")
            for resp_val, resp_label in zip([0,1,2,3,4], ["Nunca","Raramente","Às vezes","Frequentemente","Sempre"]):
                cnt = vc.get(resp_val, 0)
                rows_q.append({
                    "Q": f"Q{i:02d}",
                    "Dimensão": DIMENSOES_LABEL.get(dim_q, dim_q),
                    "Resposta": resp_label,
                    "Valor": resp_val,
                    "Qtd": cnt,
                    "Perc": cnt / total_q * 100 if total_q else 0,
                })

        df_q = pd.DataFrame(rows_q)

        if sel_dim_q != "Todas":
            df_q = df_q[df_q["Dimensão"] == sel_dim_q]

        COR_RESPOSTAS = ["#4F8EF7","#2D9E75","#F5A623","#E8621A","#D63B3B"]

        fig_q = go.Figure()
        for resp_label, cor_r in zip(["Nunca","Raramente","Às vezes","Frequentemente","Sempre"], COR_RESPOSTAS):
            sub_r = df_q[df_q["Resposta"] == resp_label]
            fig_q.add_trace(go.Bar(
                name=resp_label,
                x=sub_r["Q"],
                y=sub_r["Perc"],
                marker_color=cor_r,
                marker_line_width=0,
                text=sub_r["Perc"].apply(lambda v: f"{v:.0f}%" if v >= 8 else ""),
                textposition="inside",
                textfont=dict(size=10, color="#fff"),
            ))
        fig_q.update_layout(
            barmode="stack",
            xaxis=dict(title="Questão", tickangle=-45),
            yaxis=dict(title="% de respondentes", gridcolor=COR_BORDA, range=[0, 105]),
            legend=dict(orientation="h", y=1.08, x=0, font=dict(size=11)),
        )
        plotly_layout(fig_q, height=420, margin=dict(l=20, r=20, t=50, b=60))
        st.plotly_chart(fig_q, use_container_width=True)

        st.markdown('<div class="section-title">Score médio por questão (0–4)</div>', unsafe_allow_html=True)
        scores_q = []
        for i, col in enumerate(col_q_detect[:35], start=1):
            dim_q = dim_por_q.get(i, "")
            media_q = base_f[col].mean()
            classe_q = score_para_classificacao(media_q, dim_q) if dim_q else ""
            scores_q.append({"Q": f"Q{i:02d}", "Score": round(media_q, 2),
                             "Dimensão": DIMENSOES_LABEL.get(dim_q, dim_q),
                             "Classificação": classe_q})
        df_sq = pd.DataFrame(scores_q)
        if sel_dim_q != "Todas":
            df_sq = df_sq[df_sq["Dimensão"] == sel_dim_q]

        fig_sq = go.Figure(go.Bar(
            x=df_sq["Q"], y=df_sq["Score"],
            marker_color=[cor_nivel(c) for c in df_sq["Classificação"]],
            marker_line_width=0,
            text=df_sq["Score"].apply(lambda v: f"{v:.2f}"),
            textposition="outside",
            textfont=dict(size=10, color=COR_TEXTO),
        ))
        fig_sq.update_layout(
            xaxis=dict(title="Questão", tickangle=-45),
            yaxis=dict(title="Score médio", gridcolor=COR_BORDA, range=[0, 4.8]),
        )
        plotly_layout(fig_sq, height=350, margin=dict(l=20, r=20, t=20, b=60))
        st.plotly_chart(fig_sq, use_container_width=True)
    else:
        st.warning("Colunas de questões individuais não encontradas no base.parquet.")


# ══════════════════════════════════════════════
# TAB 4 — SCORE DE CLIMA
# ══════════════════════════════════════════════
with tabs[3]:
    st.markdown('<div class="section-title">Slide 18 · Score de Clima Psicossocial — Top Rankings por Criticidade</div>', unsafe_allow_html=True)

    def ranking_chart(df_g, col_grupo, titulo, cor_col="NR_geral"):
        if df_g.empty: return
        top = df_g.nlargest(top_n, "NR_geral")
        cores_r = [nivel_geral_para_cor(c) for c in top["classificacao"]]
        fig = go.Figure(go.Bar(
            x=top[cor_col], y=top[col_grupo],
            orientation="h",
            marker_color=cores_r, marker_line_width=0,
            text=top[cor_col].round(2).astype(str) + "  " + top["classificacao"],
            textposition="outside",
            textfont=dict(size=11, color=COR_TEXTO),
        ))
        fig.update_layout(
            title=dict(text=titulo, font=dict(size=13, color=COR_TEXTO), x=0),
            xaxis=dict(title="NR Geral médio", gridcolor=COR_BORDA, range=[0, 18]),
            yaxis=dict(title="", autorange="reversed"),
        )
        plotly_layout(fig, height=max(250, top_n * 52 + 60))
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        ranking_chart(setor_f, "Setor", f"Top {top_n} Setores por NR")
        ranking_chart(empresa_f, "Empresa", f"Top {top_n} Empresas por NR")
    with c2:
        ranking_chart(cargo_f, "Cargo", f"Top {top_n} Cargos por NR")
        if unidade_f is not None and not unidade_f.empty:
            ranking_chart(unidade_f, "Unidade", f"Top {top_n} Unidades por NR")

    st.markdown('<div class="section-title">Tabela consolidada de rankings</div>', unsafe_allow_html=True)

    tabs_rank = st.tabs(["Por Setor", "Por Cargo", "Por Unidade", "Por Empresa"])
    for tab_r, df_r, col_r in zip(tabs_rank,
                                    [setor_f, cargo_f, unidade_f if unidade_f is not None else pd.DataFrame(), empresa_f],
                                    ["Setor", "Cargo", "Unidade", "Empresa"]):
        with tab_r:
            if df_r is None or df_r.empty:
                st.info("Sem dados disponíveis.")
                continue
            cols_show = [col_r, "n_colaboradores", "NR_geral", "IGRP",
                         "perc_risco_alto", "perc_critico", "classificacao"]
            cols_show = [c for c in cols_show if c in df_r.columns]
            df_show = df_r[cols_show].copy().rename(columns={
                "n_colaboradores": "N", "NR_geral": "NR Geral", "IGRP": "IGRP",
                "perc_risco_alto": "% Alto/Crítico", "perc_critico": "% Crítico",
                "classificacao": "Classificação"
            })
            df_show["NR Geral"] = df_show["NR Geral"].round(2)
            df_show["IGRP"] = df_show["IGRP"].round(2)
            if "% Alto/Crítico" in df_show.columns:
                df_show["% Alto/Crítico"] = (df_show["% Alto/Crítico"] * 100).round(1).astype(str) + "%"
            if "% Crítico" in df_show.columns:
                df_show["% Crítico"] = (df_show["% Crítico"] * 100).round(1).astype(str) + "%"
            st.dataframe(df_show, use_container_width=True, hide_index=True,
                         height=min(500, (len(df_show)+1)*38))


# ══════════════════════════════════════════════
# TAB 5 — RISCO DE SAÚDE
# ══════════════════════════════════════════════
with tabs[4]:
    st.markdown('<div class="section-title">Slide 19 · Risco de Impacto na Saúde — Severidade por Setor e Cargo</div>', unsafe_allow_html=True)

    def chart_severidade(df_g, col_grupo, titulo):
        if df_g.empty: return
        top = df_g.nlargest(top_n, "NR_geral")
        cols_nr = [f"NR_{d}" for d in DIMENSOES if f"NR_{d}" in top.columns]
        if not cols_nr: return

        fig = go.Figure()
        cores_d = [COR_VERMELHO, COR_LARANJA, COR_AMARELO, COR_VERDE, COR_ACCENT, "#B97CF7", "#5DCAA5"]
        for d, cor_d in zip(DIMENSOES, cores_d):
            col_nr = f"NR_{d}"
            if col_nr not in top.columns: continue
            fig.add_trace(go.Bar(
                name=DIMENSOES_LABEL[d],
                x=top[col_nr],
                y=top[col_grupo],
                orientation="h",
                marker_color=cor_d, marker_line_width=0,
            ))
        fig.update_layout(
            barmode="group",
            title=dict(text=titulo, font=dict(size=13, color=COR_TEXTO), x=0),
            xaxis=dict(title="NR médio (1–16)", gridcolor=COR_BORDA),
            yaxis=dict(title="", autorange="reversed"),
            legend=dict(orientation="h", y=-0.25, font=dict(size=10)),
        )
        plotly_layout(fig, height=max(300, top_n * 60 + 100), margin=dict(l=20, r=20, t=40, b=120))
        st.plotly_chart(fig, use_container_width=True)

    chart_severidade(setor_f, "Setor", f"Top {top_n} Setores — NR por Dimensão")
    chart_severidade(cargo_f, "Cargo", f"Top {top_n} Cargos — NR por Dimensão")


# ══════════════════════════════════════════════
# TAB 6 — IMPACTO ORG.
# ══════════════════════════════════════════════
with tabs[5]:
    st.markdown('<div class="section-title">Slide 20 · Impacto Organizacional Relacionado ao Risco</div>', unsafe_allow_html=True)

    st.markdown("##### Top setores por NR alto — Risco de Absenteísmo (colunas empilhadas por nível)")

    if not setor_f.empty:
        top_abs = setor_f.nlargest(top_n, "NR_geral")

        fig_abs = go.Figure()
        for nivel, col_p, cor_n in [
            ("Crítico", "perc_critico", COR_VERMELHO),
            ("Importante", "perc_importante", COR_LARANJA),
        ]:
            if col_p in top_abs.columns:
                fig_abs.add_trace(go.Bar(
                    name=nivel,
                    x=top_abs["Setor"],
                    y=(top_abs[col_p] * 100).round(1),
                    marker_color=cor_n, marker_line_width=0,
                    text=(top_abs[col_p] * 100).round(1).astype(str) + "%",
                    textposition="inside",
                    textfont=dict(size=11, color="#fff"),
                ))

        fig_abs.update_layout(
            barmode="stack",
            xaxis=dict(title="Setor", tickangle=-30),
            yaxis=dict(title="% trabalhadores em risco", gridcolor=COR_BORDA),
            legend=dict(orientation="h", y=1.08),
        )
        plotly_layout(fig_abs, height=380)
        st.plotly_chart(fig_abs, use_container_width=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown("##### Top setores por maior P e S combinados — Probabilidade de Adoecimento (barra horizontal)")

    if not setor_f.empty:
        cols_nr_dim = [f"NR_{d}" for d in DIMENSOES if f"NR_{d}" in setor_f.columns]
        if cols_nr_dim:
            setor_ps = setor_f.copy()
            setor_ps["score_ps_total"] = setor_ps[cols_nr_dim].sum(axis=1)
            top_adoec = setor_ps.nlargest(top_n, "score_ps_total")

            fig_adoec = go.Figure()
            for d, cor_d in zip(DIMENSOES, [COR_VERMELHO, COR_LARANJA, COR_AMARELO,
                                             COR_VERDE, COR_ACCENT, "#B97CF7", "#5DCAA5"]):
                col_nr = f"NR_{d}"
                if col_nr not in top_adoec.columns: continue
                fig_adoec.add_trace(go.Bar(
                    name=DIMENSOES_LABEL[d],
                    y=top_adoec["Setor"],
                    x=top_adoec[col_nr],
                    orientation="h",
                    marker_color=cor_d, marker_line_width=0,
                ))
            fig_adoec.update_layout(
                barmode="stack",
                xaxis=dict(title="Soma dos NR por dimensão", gridcolor=COR_BORDA),
                yaxis=dict(title="", autorange="reversed"),
                legend=dict(orientation="h", y=-0.3, font=dict(size=10)),
            )
            plotly_layout(fig_adoec, height=max(280, top_n * 55 + 100),
                          margin=dict(l=20, r=20, t=20, b=100))
            st.plotly_chart(fig_adoec, use_container_width=True)


# ══════════════════════════════════════════════
# TAB 7 — HEATMAP
# ══════════════════════════════════════════════
with tabs[6]:
    st.markdown('<div class="section-title">Slide 21 · Heatmap — Nível de Risco (NR) por Dimensão</div>', unsafe_allow_html=True)

    visao_hm = st.radio("Agrupar por:", ["Setor", "Cargo", "Unidade"], horizontal=True, key="hm_visao")

    mapa_visao = {"Setor": setor_f, "Cargo": cargo_f, "Unidade": unidade_f}
    df_hm_src = mapa_visao.get(visao_hm, setor_f)

    if df_hm_src is not None and not df_hm_src.empty:
        col_grupo_hm = visao_hm
        cols_nr_hm = [f"NR_{d}" for d in DIMENSOES if f"NR_{d}" in df_hm_src.columns]
        labels_hm  = [DIMENSOES_LABEL[d] for d in DIMENSOES if f"NR_{d}" in df_hm_src.columns]

        df_hm = df_hm_src.nlargest(min(20, len(df_hm_src)), "NR_geral")
        z_hm  = df_hm[cols_nr_hm].values
        y_hm  = df_hm[col_grupo_hm].tolist()
        annot = [[f"{val:.1f}" for val in row] for row in z_hm]

        fig_hm = go.Figure(go.Heatmap(
            z=z_hm,
            x=labels_hm,
            y=y_hm,
            text=annot,
            texttemplate="%{text}",
            textfont=dict(size=11, color=COR_TEXTO),
            colorscale=[
                [0.0,  COR_VERDE],
                [0.33, COR_AMARELO],
                [0.66, COR_LARANJA],
                [1.0,  COR_VERMELHO],
            ],
            zmin=1, zmax=16,
            colorbar=dict(
                title="NR", tickvals=[1,4,8,12,16],
                ticktext=["1","4","8","12","16"],
                tickfont=dict(color=COR_TEXTO, size=11),
                title=dict(
                    text="NR",
                    font=dict(color=COR_TEXTO)
                ),
                bgcolor="rgba(0,0,0,0)",
                bordercolor=COR_BORDA,
            ),
        ))
        fig_hm.update_layout(
            xaxis=dict(title="", tickangle=-30, side="top"),
            yaxis=dict(title="", autorange="reversed"),
        )
        plotly_layout(fig_hm, height=max(400, len(y_hm) * 32 + 80))
        st.plotly_chart(fig_hm, use_container_width=True)
    else:
        st.info(f"Dados de {visao_hm} não disponíveis.")


# ══════════════════════════════════════════════
# TAB 8 — POR CARGO
# ══════════════════════════════════════════════
with tabs[7]:
    st.markdown('<div class="section-title">Slide 22 · Análise Detalhada por Cargo</div>', unsafe_allow_html=True)

    if not cargo_f.empty:
        cargos_lista = cargo_f["Cargo"].tolist()
        cargo_sel = st.selectbox("Selecione o cargo:", cargos_lista)

        row_cargo = cargo_f[cargo_f["Cargo"] == cargo_sel].iloc[0]

        st.markdown(f"""
        <div class="kpi-grid">
          <div class="kpi-card">
            <div class="kpi-label">Colaboradores</div>
            <div class="kpi-value">{int(row_cargo.get('n_colaboradores',0))}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">NR Geral</div>
            <div class="kpi-value kpi-accent">{row_cargo.get('NR_geral',0):.2f}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Classificação</div>
            <div class="kpi-value" style="font-size:18px;">{row_cargo.get('classificacao','—')}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Em Risco Alto/Crítico</div>
            <div class="kpi-value" style="color:{COR_LARANJA};">{row_cargo.get('perc_risco_alto',0)*100:.1f}%</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        scores_cargo = []
        labels_radar = []
        for d in DIMENSOES:
            col_s = f"score_{d}"
            if col_s in row_cargo:
                scores_cargo.append(round(float(row_cargo[col_s]), 3))
                labels_radar.append(DIMENSOES_LABEL[d])

        if scores_cargo:
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=scores_cargo + [scores_cargo[0]],
                theta=labels_radar + [labels_radar[0]],
                fill="toself",
                fillcolor=f"rgba(79,142,247,0.15)",
                line=dict(color=COR_ACCENT, width=2),
                name=cargo_sel,
            ))
            fig_radar.update_layout(
                polar=dict(
                    bgcolor="rgba(0,0,0,0)",
                    angularaxis=dict(tickfont=dict(size=11, color=COR_TEXTO), linecolor=COR_BORDA),
                    radialaxis=dict(range=[0, 4], gridcolor=COR_BORDA,
                                   tickfont=dict(size=10, color=COR_MUTED)),
                ),
                showlegend=False,
            )
            plotly_layout(fig_radar, height=380)
            st.plotly_chart(fig_radar, use_container_width=True)

        st.markdown('<div class="section-title">NR por Dimensão</div>', unsafe_allow_html=True)
        tab_dim_cargo = []
        for d in DIMENSOES:
            tab_dim_cargo.append({
                "Dimensão": DIMENSOES_LABEL[d],
                "Score": round(float(row_cargo.get(f"score_{d}", 0)), 2),
                "NR": round(float(row_cargo.get(f"NR_{d}", 0)), 2),
                "Polaridade": "Negativa" if d in DIM_NEGATIVAS else "Positiva",
            })
        df_dim_cargo = pd.DataFrame(tab_dim_cargo)
        st.dataframe(df_dim_cargo, use_container_width=True, hide_index=True)

        base_cargo = base_f[base_f["Informe seu cargo"] == cargo_sel]
        st.markdown(f'<div class="section-title">Distribuição individual ({len(base_cargo)} respondentes)</div>', unsafe_allow_html=True)

        dist_cargo = base_cargo["risco_geral"].value_counts().reindex(NIVEIS_GERAL_ORDEM, fill_value=0)
        fig_dist_c = go.Figure(go.Bar(
            x=dist_cargo.index, y=dist_cargo.values,
            marker_color=[nivel_geral_para_cor(n) for n in dist_cargo.index],
            marker_line_width=0,
            text=dist_cargo.values,
            textposition="outside",
            textfont=dict(size=12, color=COR_TEXTO),
        ))
        fig_dist_c.update_layout(
            xaxis=dict(title=""),
            yaxis=dict(title="Nº de respondentes", gridcolor=COR_BORDA),
            showlegend=False,
        )
        plotly_layout(fig_dist_c, height=280)
        st.plotly_chart(fig_dist_c, use_container_width=True)
    else:
        st.info("Dados de cargo não disponíveis.")


# ══════════════════════════════════════════════
# TAB 9 — PGR
# ══════════════════════════════════════════════
with tabs[8]:
    st.markdown('<div class="section-title">Slide 23 · PGR — Programa de Gerenciamento de Riscos</div>', unsafe_allow_html=True)
    st.caption("Análise por Unidade / Setor / Cargo × Categorias — Matriz NR (P × S)")

    visao_pgr = st.radio("Dimensão de análise:", ["Setor", "Cargo", "Unidade"], horizontal=True, key="pgr_visao")
    mapa_pgr  = {
        "Setor":   (setor_f,   "Setor"),
        "Cargo":   (cargo_f,   "Cargo"),
        "Unidade": (unidade_f if unidade_f is not None else pd.DataFrame(), "Unidade"),
    }
    df_pgr_src, col_pgr = mapa_pgr[visao_pgr]

    if df_pgr_src is not None and not df_pgr_src.empty:
        cols_nr_pgr = [f"NR_{d}" for d in DIMENSOES if f"NR_{d}" in df_pgr_src.columns]
        labels_pgr  = [DIMENSOES_LABEL[d] for d in DIMENSOES if f"NR_{d}" in df_pgr_src.columns]

        df_pgr = df_pgr_src[[col_pgr, "n_colaboradores", "NR_geral", "classificacao"] + cols_nr_pgr].copy()
        df_pgr = df_pgr.sort_values("NR_geral", ascending=False).reset_index(drop=True)

        rename_map = {f"NR_{d}": DIMENSOES_LABEL[d] for d in DIMENSOES if f"NR_{d}" in df_pgr.columns}
        df_pgr_show = df_pgr.rename(columns={**rename_map,
                                              "n_colaboradores": "N",
                                              "NR_geral": "NR Geral",
                                              "classificacao": "Classificação"})

        nr_cols = list(rename_map.values())
        all_num_cols = ["NR Geral"] + nr_cols

        # Coloração sem matplotlib
        styled = (
            df_pgr_show.style
            .applymap(_nr_row_color, subset=all_num_cols)
            .format({c: "{:.2f}" for c in all_num_cols})
        )

        st.dataframe(styled, use_container_width=True,
                     height=min(600, (len(df_pgr_show)+1) * 38))

        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        st.markdown("##### Matriz de Risco — Heatmap PGR")

        z_pgr = df_pgr[cols_nr_pgr].values
        y_pgr = df_pgr[col_pgr].tolist()
        annot_pgr = [[f"{v:.1f}" for v in row] for row in z_pgr]

        fig_pgr = go.Figure(go.Heatmap(
            z=z_pgr,
            x=labels_pgr,
            y=y_pgr,
            text=annot_pgr,
            texttemplate="%{text}",
            textfont=dict(size=11),
            colorscale=[
                [0.0,  COR_VERDE],
                [0.25, COR_AMARELO],
                [0.55, COR_LARANJA],
                [1.0,  COR_VERMELHO],
            ],
            zmin=1, zmax=16,
            colorbar=dict(
                title="NR",
                tickvals=[2, 6, 10, 14],
                ticktext=["Aceitável", "Moderado", "Importante", "Crítico"],
                tickfont=dict(color=COR_TEXTO, size=10),
                title=dict(
                    text="NR",
                    font=dict(color=COR_TEXTO)
                ),
                bgcolor="rgba(0,0,0,0)",
                bordercolor=COR_BORDA,
            ),
        ))
        fig_pgr.update_layout(
            xaxis=dict(title="", tickangle=-30, side="top"),
            yaxis=dict(title="", autorange="reversed"),
        )
        plotly_layout(fig_pgr, height=max(400, len(y_pgr) * 30 + 80))
        st.plotly_chart(fig_pgr, use_container_width=True)

        st.markdown(f"""
        <div style="display:flex;gap:16px;flex-wrap:wrap;font-size:12px;color:{COR_MUTED};margin-top:8px;">
          <span><b style="color:{COR_VERDE}">■</b> Aceitável (NR 1–4)</span>
          <span><b style="color:{COR_AMARELO}">■</b> Moderado (NR 5–8)</span>
          <span><b style="color:{COR_LARANJA}">■</b> Importante (NR 9–12)</span>
          <span><b style="color:{COR_VERMELHO}">■</b> Crítico (NR 13–16)</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info(f"Dados de {visao_pgr} não disponíveis.")

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown(f"""
<div style="margin-top:3rem;padding-top:1.5rem;border-top:1px solid {COR_BORDA};
     display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
  <span style="font-size:12px;color:{COR_MUTED};">
    🧠 Dashboard HSE-IT · Plataforma Vivamente 360° · NR-1
  </span>
  <span style="font-size:11px;color:{COR_MUTED};font-family:'DM Mono',monospace;">
    base.parquet · setor.parquet · cargo.parquet · unidade.parquet
  </span>
</div>
""", unsafe_allow_html=True)
