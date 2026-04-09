"""
Dashboard HSE-IT — Plataforma Vivamente 360°
Baseado nos slides 13–23 do PPTX NR-1
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
COR_VERDE    = "#2D9E75"
COR_AMARELO  = "#F5A623"
COR_LARANJA  = "#E8621A"
COR_VERMELHO = "#D63B3B"
COR_CINZA    = "#8B8FA8"
COR_BG       = "#0F1117"
COR_CARD     = "#1A1D27"
COR_BORDA    = "#2A2D3E"
COR_TEXTO    = "#E8EAF0"
COR_MUTED    = "#6B7280"
COR_ACCENT   = "#4F8EF7"

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
    "Apoio_Colegas", "Relacionamentos", "Cargo", "Mudanca"
]
DIMENSOES_LABEL = {
    "Demandas":        "Demandas",
    "Controle":        "Controle",
    "Apoio_Chefia":    "Apoio da Chefia",
    "Apoio_Colegas":   "Apoio dos Colegas",
    "Relacionamentos": "Relacionamentos",
    "Cargo":           "Cargo / Função",
    "Mudanca":         "Comunicação e Mudanças",
}
DIM_NEGATIVAS = {"Demandas", "Relacionamentos"}

# Questões negativas (polaridade: valor alto = maior risco)
# Todas as perguntas de Demandas (1-8) e Relacionamentos (24-27)
QS_NEGATIVAS = set(range(1, 9)) | set(range(24, 28))

NIVEIS_ORDEM       = ["Baixo Risco", "Risco Médio", "Risco Moderado", "Alto Risco"]
NIVEIS_GERAL_ORDEM = ["Aceitável", "Moderado", "Importante", "Crítico"]

# Cores das respostas para questões NEGATIVAS (alto = pior)
COR_RESPOSTAS_NEG = ["#2D9E75", "#8BC4A8", "#F5A623", "#E8621A", "#D63B3B"]
# Cores das respostas para questões POSITIVAS (alto = melhor)
COR_RESPOSTAS_POS = ["#D63B3B", "#E8621A", "#F5A623", "#8BC4A8", "#2D9E75"]

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
[data-testid="stSidebar"] {{
    background-color: {COR_CARD} !important;
    border-right: 1px solid {COR_BORDA};
    padding-top: 0 !important;
}}
[data-testid="stSidebar"] > div {{ padding-top: 0 !important; }}
[data-testid="stSidebar"] * {{ color: {COR_TEXTO} !important; }}
[data-baseweb="tab-list"] {{
    background: {COR_CARD} !important;
    border-radius: 12px;
    padding: 8px !important;
    gap: 8px !important;
    margin-bottom: 10px;
}}
[data-baseweb="tab"] {{
    background: transparent !important;
    border-radius: 8px !important;
    padding: 12px 24px !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    color: {COR_MUTED} !important;
    transition: all 0.2s;
}}
[aria-selected="true"][data-baseweb="tab"] {{
    background: {COR_BG} !important;
    color: {COR_TEXTO} !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}}
.block-container {{ padding: 1.5rem 2rem 3rem; }}
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
.section-title {{
    font-size: 13px; font-weight: 600; color: {COR_MUTED};
    text-transform: uppercase; letter-spacing: .1em;
    margin: 2rem 0 1rem;
    padding-bottom: 8px;
    border-bottom: 1px solid {COR_BORDA};
}}
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
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

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
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=COR_BORDA, font=dict(size=11)),
        xaxis=dict(gridcolor=COR_BORDA, zerolinecolor=COR_BORDA),
        yaxis=dict(gridcolor=COR_BORDA, zerolinecolor=COR_BORDA),
    )
    return fig


def nivel_geral_para_cor(nivel: str) -> str:
    return {"Aceitável": COR_VERDE, "Moderado": COR_AMARELO,
            "Importante": COR_LARANJA, "Crítico": COR_VERMELHO}.get(nivel, COR_CINZA)


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


def score_para_P(score: float, dim: str) -> int:
    """Converte score médio (0–4) em P discreto (1–4) conforme polaridade."""
    if pd.isna(score): return 1
    if dim in DIM_NEGATIVAS:
        if score >= 3.1: return 4
        if score >= 2.1: return 3
        if score >= 1.1: return 2
        return 1
    else:
        if score <= 1.0: return 4
        if score <= 2.0: return 3
        if score <= 3.0: return 2
        return 1


def _nr_row_color(val):
    try:
        v = float(val)
    except (TypeError, ValueError):
        return ""
    if v >= 13: return f"background-color: rgba(214,59,59,0.35); color: {COR_TEXTO}"
    if v >= 9:  return f"background-color: rgba(232,98,26,0.30); color: {COR_TEXTO}"
    if v >= 5:  return f"background-color: rgba(245,166,35,0.25); color: {COR_TEXTO}"
    return f"background-color: rgba(45,158,117,0.20); color: {COR_TEXTO}"


def _perc_row_color(val):
    try:
        v = float(str(val).replace("%", ""))
    except (TypeError, ValueError):
        return ""
    if v >= 60: return f"background-color: rgba(214,59,59,0.30); color: {COR_TEXTO}"
    if v >= 35: return f"background-color: rgba(232,98,26,0.25); color: {COR_TEXTO}"
    if v >= 15: return f"background-color: rgba(245,166,35,0.20); color: {COR_TEXTO}"
    return f"background-color: rgba(45,158,117,0.15); color: {COR_TEXTO}"


def _p_row_color(val):
    """Coloração para células de P (1–4)."""
    try:
        v = int(val)
    except (TypeError, ValueError):
        return ""
    if v == 4: return f"background-color: rgba(214,59,59,0.35); color: {COR_TEXTO}"
    if v == 3: return f"background-color: rgba(232,98,26,0.30); color: {COR_TEXTO}"
    if v == 2: return f"background-color: rgba(245,166,35,0.25); color: {COR_TEXTO}"
    return f"background-color: rgba(45,158,117,0.20); color: {COR_TEXTO}"


def _class_row_color(val):
    """Coloração para células de classificação textual."""
    mapa = {
        "Alto Risco":     f"background-color: rgba(214,59,59,0.35); color: {COR_TEXTO}",
        "Risco Moderado": f"background-color: rgba(232,98,26,0.30); color: {COR_TEXTO}",
        "Risco Médio":    f"background-color: rgba(245,166,35,0.25); color: {COR_TEXTO}",
        "Baixo Risco":    f"background-color: rgba(45,158,117,0.20); color: {COR_TEXTO}",
    }
    return mapa.get(str(val), "")

# ─────────────────────────────────────────────
# CARGA DE DADOS
# ─────────────────────────────────────────────

@st.cache_data
def load_data(path_base, path_setor, path_cargo, path_unidade=None):
    base    = pd.read_parquet(path_base)
    setor   = pd.read_parquet(path_setor)
    cargo   = pd.read_parquet(path_cargo)
    unidade = pd.read_parquet(path_unidade) if path_unidade and os.path.exists(path_unidade) else None
    return base, setor, cargo, unidade


def reaplicar_agg(df, col, rename):
    if df.empty: return pd.DataFrame()
    g = df.groupby(col).agg(
        n_colaboradores=(col, "count"),
        IGRP=("IGRP", "mean"),
        NR_geral=("NR_geral", "mean"),
        **{f"score_{d}": (f"score_{d}", "mean") for d in DIMENSOES if f"score_{d}" in df.columns},
        **{f"NR_{d}":    (f"NR_{d}",    "mean") for d in DIMENSOES if f"NR_{d}"    in df.columns},
        **{f"P_{d}":     (f"P_{d}",     "mean") for d in DIMENSOES if f"P_{d}"     in df.columns},
        **{f"S_{d}":     (f"S_{d}",     "mean") for d in DIMENSOES if f"S_{d}"     in df.columns},
        perc_critico   =("risco_geral", lambda x: (x == "Crítico").mean()),
        perc_importante=("risco_geral", lambda x: (x == "Importante").mean()),
        perc_moderado  =("risco_geral", lambda x: (x == "Moderado").mean()),
        perc_aceitavel =("risco_geral", lambda x: (x == "Aceitável").mean()),
        perc_risco_alto=("risco_geral", lambda x: x.isin(["Crítico", "Importante"]).mean()),
    ).reset_index().rename(columns={col: rename})
    g["classificacao"] = g["NR_geral"].apply(classificar_NR)
    g["rank_risco"]    = g["NR_geral"].rank(ascending=False, method="min")
    return g.sort_values(["perc_risco_alto", "NR_geral"], ascending=False)

# ─────────────────────────────────────────────
# CAMINHOS
# ─────────────────────────────────────────────
BASE_PATH    = "base.parquet"
SETOR_PATH   = "setor.parquet"
CARGO_PATH   = "cargo.parquet"
UNIDADE_PATH = "unidade.parquet"

base, setor, cargo, unidade = load_data(BASE_PATH, SETOR_PATH, CARGO_PATH, UNIDADE_PATH)

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
        <div style="text-align:center; padding:25px 0 15px 0; border-bottom:1px solid #2A2D3E;">
            <h2 style="margin:0; font-size:24px; color:#2D9E75;">🧠 HSE-IT</h2>
            <p style="margin:4px 0 0 0; font-size:13px; color:#8B8FA8;">
                Plataforma Vivamente 360° • NR-1
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Slide 13: input manual de total de colaboradores ──────────────────
    st.markdown("### 👥 Total de Colaboradores")
    st.caption("Informe o total cadastrado para calcular o índice de engajamento.")
    total_colaboradores = st.number_input(
        "Total de colaboradores da empresa",
        min_value=1,
        value=st.session_state.get("total_colab", 1),
        step=1,
        key="total_colab",
        help="Número total de funcionários cadastrados (100% base). Usado no indicador de engajamento.",
    )

    st.markdown("---")
    st.markdown("### 🔍 Filtros globais")

    empresas_disp = sorted(base["Empresa"].dropna().unique())
    sel_empresa   = st.multiselect("Empresa", empresas_disp, default=empresas_disp)

    unidades_disp = sorted(base[base["Empresa"].isin(sel_empresa)]["Informe sua unidade"].dropna().unique())
    sel_unidade   = st.multiselect("Unidade", unidades_disp, default=unidades_disp)

    setores_disp  = sorted(base[base["Informe sua unidade"].isin(sel_unidade)]["Informe seu setor / departamento."].dropna().unique())
    sel_setor     = st.multiselect("Setor", setores_disp, default=setores_disp)

    cargos_disp   = sorted(base[base["Informe seu setor / departamento."].isin(sel_setor)]["Informe seu cargo"].dropna().unique())
    sel_cargo     = st.multiselect("Cargo", cargos_disp, default=cargos_disp)

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

# Criar class_{dim} se não existir
for d in DIMENSOES:
    col_score = f"score_{d}"
    col_class = f"class_{d}"
    if col_score in base_f.columns and col_class not in base_f.columns:
        base_f[col_class] = base_f[col_score].apply(
            lambda x: score_para_classificacao(x, d) if pd.notna(x) else "Sem dados"
        )

setor_f   = reaplicar_agg(base_f, "Informe seu setor / departamento.", "Setor")
cargo_f   = reaplicar_agg(base_f, "Informe seu cargo", "Cargo")
unidade_f = reaplicar_agg(base_f, "Informe sua unidade", "Unidade")
empresa_f = reaplicar_agg(base_f, "Empresa", "Empresa")

# ─────────────────────────────────────────────
# HEADER + KPIs
# ─────────────────────────────────────────────
n_total      = len(base_f)
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
    <div class="kpi-value">{igrp_medio:.2f}</div>
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
# TABS
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
# TAB 1 — VISÃO GERAL (Slides 13, 14, 15)
# ══════════════════════════════════════════════
with tabs[0]:

    # ── Slide 13 — Engajamento ────────────────────────────────────────────
    st.markdown('<div class="section-title">Slide 13 · Índice de Engajamento — Questionários Respondidos</div>', unsafe_allow_html=True)

    perc_engaj = (n_total / total_colaboradores * 100) if total_colaboradores > 0 else 0
    perc_engaj = min(perc_engaj, 100.0)

    cor_engaj = COR_VERDE if perc_engaj >= 70 else (COR_AMARELO if perc_engaj >= 50 else COR_VERMELHO)

    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=perc_engaj,
        number=dict(suffix="%", font=dict(size=36, color=COR_TEXTO)),
        delta=dict(reference=70, valueformat=".1f", suffix="%",
                   increasing=dict(color=COR_VERDE), decreasing=dict(color=COR_VERMELHO)),
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=1, tickcolor=COR_MUTED,
                      tickfont=dict(color=COR_MUTED, size=11)),
            bar=dict(color=cor_engaj, thickness=0.25),
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
            steps=[
                dict(range=[0,  50], color="rgba(214,59,59,0.15)"),
                dict(range=[50, 70], color="rgba(245,166,35,0.15)"),
                dict(range=[70,100], color="rgba(45,158,117,0.15)"),
            ],
            threshold=dict(
                line=dict(color=COR_VERDE, width=3),
                thickness=0.8,
                value=70,
            ),
        ),
        title=dict(text="Participação na pesquisa", font=dict(size=14, color=COR_MUTED)),
    ))
    fig_gauge.update_layout(
        height=280,
        margin=dict(l=40, r=40, t=60, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans", color=COR_TEXTO),
    )

    col_g1, col_g2, col_g3 = st.columns([1.5, 1, 1])
    with col_g1:
        st.plotly_chart(fig_gauge, use_container_width=True)
    with col_g2:
        st.markdown(f"""
        <div class="kpi-card" style="margin-top:20px;">
            <div class="kpi-label">Responderam</div>
            <div class="kpi-value" style="color:{cor_engaj};">{n_total:,}</div>
            <div class="kpi-sub">de {total_colaboradores:,} colaboradores</div>
        </div>
        """, unsafe_allow_html=True)
    with col_g3:
        status_txt = "✅ Meta atingida" if perc_engaj >= 70 else ("⚠️ Atenção" if perc_engaj >= 50 else "🔴 Baixo engajamento")
        st.markdown(f"""
        <div class="kpi-card" style="margin-top:20px;">
            <div class="kpi-label">Status</div>
            <div class="kpi-value" style="font-size:16px; color:{cor_engaj};">{status_txt}</div>
            <div class="kpi-sub">Meta: 70% | Alerta: 50%</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr style="border-color:#2A2D3E; margin:2rem 0;">', unsafe_allow_html=True)

    # ── Slide 14 — IGRP por Dimensão ─────────────────────────────────────
    st.markdown('<div class="section-title">Slide 14 · Índice Geral de Riscos Psicossociais (IGRP) por Dimensão</div>', unsafe_allow_html=True)

    scores_dim = {}
    class_dim  = {}
    for d in DIMENSOES:
        col_s = f"score_{d}"
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

    st.markdown('<hr style="border-color:#2A2D3E; margin:2rem 0;">', unsafe_allow_html=True)

    # ── Slide 15 — % Trabalhadores por Nível ─────────────────────────────
    st.markdown('<div class="section-title">Slide 15 · % de Trabalhadores por Nível de Risco Global</div>', unsafe_allow_html=True)

    col_pizza, col_barra = st.columns([1, 1])

    with col_pizza:
        dist_risco = base_f["risco_geral"].value_counts()
        ordem      = ["Aceitável", "Moderado", "Importante", "Crítico"]
        labels_p   = [o for o in ordem if o in dist_risco.index]
        vals_p     = [dist_risco[o] for o in labels_p]
        cores_p    = [nivel_geral_para_cor(o) for o in labels_p]

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
# TAB 2 — POR DIMENSÃO (Slide 16)
# ══════════════════════════════════════════════
with tabs[1]:
    st.markdown('<div class="section-title">Slide 16 · Distribuição de Nível de Risco por Dimensão do HSE-IT</div>', unsafe_allow_html=True)

    rows_dim = []
    for d in DIMENSOES:
        col_c = f"class_{d}"
        if col_c not in base_f.columns: continue
        vc    = base_f[col_c].value_counts()
        total = vc.sum()
        for nivel in NIVEIS_ORDEM:
            cnt = vc.get(nivel, 0)
            rows_dim.append({
                "Dimensão": DIMENSOES_LABEL[d],
                "Nível":    nivel,
                "Qtd":      cnt,
                "Perc":     cnt / total * 100 if total else 0,
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
        pivot  = df_dim.pivot_table(index="Dimensão", columns="Nível", values="Perc", fill_value=0)
        pivot  = pivot.reindex(columns=[c for c in NIVEIS_ORDEM if c in pivot.columns])
        pivot  = pivot.round(1)
        styled = pivot.style.map(_perc_row_color).format("{:.1f}%")
        st.dataframe(styled, use_container_width=True, height=320)


# ══════════════════════════════════════════════
# TAB 3 — POR QUESTÃO (Slide 17) — com polarização
# ══════════════════════════════════════════════
with tabs[2]:
    st.markdown('<div class="section-title">Slide 17 · Distribuição de Respostas por Questão do HSE-IT</div>', unsafe_allow_html=True)
    st.caption("🔴 Questões negativas (Demandas, Relacionamentos): Frequentemente/Sempre = maior risco. "
               "🟢 Questões positivas: Nunca/Raramente = maior risco.")

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
        mapa_dim_q = {
            "Demandas":        [1,2,3,4,5,6,7,8],
            "Controle":        [9,10,11,12,13,14],
            "Apoio_Chefia":    [15,16,17,18,19],
            "Apoio_Colegas":   [20,21,22,23],
            "Relacionamentos": [24,25,26,27],
            "Cargo":           [28,29,30,31,32],
            "Mudanca":         [33,34,35],
        }
        for d, qs in mapa_dim_q.items():
            for q in qs:
                dim_por_q[q] = d

        sel_dim_q = st.selectbox(
            "Filtrar por dimensão",
            ["Todas"] + [DIMENSOES_LABEL[d] for d in DIMENSOES],
            key="sel_dim_q"
        )

        # ── Gráfico empilhado com cores por polaridade ────────────────────
        # Cada questão tem sua própria paleta dependendo de ser negativa ou positiva.
        # Estratégia: uma trace por nível de resposta; cor varia por questão.
        # Usamos barras independentes por questão (cada uma com sua própria cor).

        rows_q = []
        for i, col in enumerate(col_q_detect[:35], start=1):
            vc      = base_f[col].value_counts().reindex([0,1,2,3,4], fill_value=0)
            total_q = vc.sum()
            dim_q   = dim_por_q.get(i, "")
            is_neg  = i in QS_NEGATIVAS
            cores_q = COR_RESPOSTAS_NEG if is_neg else COR_RESPOSTAS_POS
            for resp_val, resp_label, cor_r in zip(
                [0,1,2,3,4],
                ["Nunca","Raramente","Às vezes","Frequentemente","Sempre"],
                cores_q
            ):
                cnt = vc.get(resp_val, 0)
                rows_q.append({
                    "Q":        f"Q{i:02d}",
                    "Índice":   i,
                    "Dimensão": DIMENSOES_LABEL.get(dim_q, dim_q),
                    "Resposta": resp_label,
                    "Valor":    resp_val,
                    "Qtd":      cnt,
                    "Perc":     cnt / total_q * 100 if total_q else 0,
                    "Cor":      cor_r,
                    "Negativa": is_neg,
                })

        df_q = pd.DataFrame(rows_q)

        if sel_dim_q != "Todas":
            df_q = df_q[df_q["Dimensão"] == sel_dim_q]

        # Constrói o gráfico de barras empilhadas com polarização nas cores.
        # Como cada questão tem paleta própria, iteramos por questão e por resposta.
        qs_filtradas  = df_q["Q"].unique().tolist()
        resp_labels   = ["Nunca","Raramente","Às vezes","Frequentemente","Sempre"]

        fig_q = go.Figure()
        for resp_label in resp_labels:
            sub_r = df_q[df_q["Resposta"] == resp_label]
            # Cor por questão (cada barra da mesma resposta pode ter cor diferente)
            fig_q.add_trace(go.Bar(
                name=resp_label,
                x=sub_r["Q"],
                y=sub_r["Perc"],
                marker_color=sub_r["Cor"].tolist(),
                marker_line_width=0,
                text=sub_r["Perc"].apply(lambda v: f"{v:.0f}%" if v >= 8 else ""),
                textposition="inside",
                textfont=dict(size=10, color="#fff"),
                showlegend=False,  # legenda manual abaixo
            ))

        # Legenda manual: duas colunas (negativa / positiva)
        fig_q.update_layout(
            barmode="stack",
            xaxis=dict(title="Questão", tickangle=-45),
            yaxis=dict(title="% de respondentes", gridcolor=COR_BORDA, range=[0, 105]),
        )
        plotly_layout(fig_q, height=420, margin=dict(l=20, r=20, t=50, b=60))
        st.plotly_chart(fig_q, use_container_width=True)

        # Legenda de polarização
        col_ln, col_lp = st.columns(2)
        with col_ln:
            st.markdown("**🔴 Questões negativas** (Demandas / Relacionamentos):")
            for label, cor in zip(resp_labels, COR_RESPOSTAS_NEG):
                st.markdown(f'<span style="background:{cor};padding:2px 8px;border-radius:4px;color:#fff;font-size:11px;">{label}</span>', unsafe_allow_html=True)
        with col_lp:
            st.markdown("**🟢 Questões positivas** (demais dimensões):")
            for label, cor in zip(resp_labels, COR_RESPOSTAS_POS):
                st.markdown(f'<span style="background:{cor};padding:2px 8px;border-radius:4px;color:#fff;font-size:11px;">{label}</span>', unsafe_allow_html=True)

        # ── Score médio por questão ───────────────────────────────────────
        st.markdown('<div class="section-title">Score médio por questão (0–4)</div>', unsafe_allow_html=True)
        scores_q = []
        for i, col in enumerate(col_q_detect[:35], start=1):
            dim_q   = dim_por_q.get(i, "")
            media_q = base_f[col].mean()
            classe_q = score_para_classificacao(media_q, dim_q) if dim_q else ""
            scores_q.append({
                "Q":            f"Q{i:02d}",
                "Score":        round(media_q, 2),
                "Dimensão":     DIMENSOES_LABEL.get(dim_q, dim_q),
                "Classificação":classe_q,
                "Polaridade":   "Negativa" if i in QS_NEGATIVAS else "Positiva",
            })
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
# TAB 4 — SCORE DE CLIMA (Slide 18) — Radar chart
# ══════════════════════════════════════════════
with tabs[3]:
    st.markdown('<div class="section-title">Slide 18 · Score de Clima Psicossocial — Radar por Criticidade</div>', unsafe_allow_html=True)
    st.caption("Cada linha no radar representa um grupo (setor/cargo/unidade/empresa). "
               "Os eixos são as 7 dimensões HSE-IT. Score 0–4.")

    tabs_clima = st.tabs(["Por Setor", "Por Cargo", "Por Unidade", "Por Empresa"])

    CORES_RADAR = [
        "#4F8EF7","#2D9E75","#F5A623","#E8621A","#D63B3B",
        "#B97CF7","#5DCAA5","#F77F4F","#7FC8F8","#F7D44F",
    ]

    def radar_chart(df_g, col_grupo, titulo):
        if df_g is None or df_g.empty:
            st.info("Sem dados disponíveis.")
            return

        top = df_g.nlargest(top_n, "NR_geral")
        labels_r = [DIMENSOES_LABEL[d] for d in DIMENSOES if f"score_{d}" in top.columns]
        dims_r   = [d for d in DIMENSOES if f"score_{d}" in top.columns]

        if not dims_r:
            st.info("Dados de score por dimensão não disponíveis.")
            return

        fig = go.Figure()
        for idx, (_, row) in enumerate(top.iterrows()):
            scores_r = [float(row.get(f"score_{d}", 0)) for d in dims_r]
            scores_r_closed = scores_r + [scores_r[0]]
            labels_closed   = labels_r + [labels_r[0]]
            cor = CORES_RADAR[idx % len(CORES_RADAR)]
            grupo_nome = str(row[col_grupo])
            classif    = row.get("classificacao", "")
            fig.add_trace(go.Scatterpolar(
                r=scores_r_closed,
                theta=labels_closed,
                fill="toself",
                fillcolor=f"rgba({int(cor[1:3],16)},{int(cor[3:5],16)},{int(cor[5:7],16)},0.12)",
                # Plotly não aceita rgba hex direto, usamos opacity
                opacity=0.85,
                line=dict(color=cor, width=2),
                name=f"{grupo_nome} ({classif})",
            ))

        fig.update_layout(
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                angularaxis=dict(tickfont=dict(size=11, color=COR_TEXTO), linecolor=COR_BORDA),
                radialaxis=dict(
                    range=[0, 4],
                    gridcolor=COR_BORDA,
                    tickvals=[1, 2, 3, 4],
                    ticktext=["1", "2", "3", "4"],
                    tickfont=dict(size=9, color=COR_MUTED),
                ),
            ),
            showlegend=True,
            legend=dict(orientation="h", y=-0.2, font=dict(size=10),
                        bgcolor="rgba(0,0,0,0)"),
            title=dict(text=titulo, font=dict(size=13, color=COR_TEXTO), x=0),
        )
        plotly_layout(fig, height=480, margin=dict(l=60, r=60, t=60, b=120))
        st.plotly_chart(fig, use_container_width=True)

        # Tabela consolidada abaixo do radar
        cols_show = [col_grupo, "n_colaboradores", "NR_geral", "IGRP",
                     "perc_risco_alto", "perc_critico", "classificacao"]
        cols_show = [c for c in cols_show if c in top.columns]
        df_show   = top[cols_show].copy().rename(columns={
            "n_colaboradores": "N", "NR_geral": "NR Geral",
            "perc_risco_alto": "% Alto/Crítico", "perc_critico": "% Crítico",
            "classificacao":   "Classificação",
        })
        df_show["NR Geral"] = df_show["NR Geral"].round(2)
        df_show["IGRP"]     = df_show["IGRP"].round(2)
        if "% Alto/Crítico" in df_show.columns:
            df_show["% Alto/Crítico"] = (df_show["% Alto/Crítico"]*100).round(1).astype(str) + "%"
        if "% Crítico" in df_show.columns:
            df_show["% Crítico"] = (df_show["% Crítico"]*100).round(1).astype(str) + "%"
        st.dataframe(df_show, use_container_width=True, hide_index=True,
                     height=min(400, (len(df_show)+1)*38))

    mapa_clima = [
        (setor_f,   "Setor",   f"Top {top_n} Setores — Score por Dimensão"),
        (cargo_f,   "Cargo",   f"Top {top_n} Cargos — Score por Dimensão"),
        (unidade_f, "Unidade", f"Top {top_n} Unidades — Score por Dimensão"),
        (empresa_f, "Empresa", f"Empresas — Score por Dimensão"),
    ]
    n_empresas = len(empresa_f) if empresa_f is not None and not empresa_f.empty else 0

    for tab_c, (df_c, col_c, titulo_c) in zip(tabs_clima, mapa_clima):
        with tab_c:
            # Slide 18: Empresa só aparece se houver mais de uma
            if col_c == "Empresa" and n_empresas <= 1:
                st.info("Análise por empresa disponível apenas quando há mais de uma empresa nos dados.")
            else:
                radar_chart(df_c, col_c, titulo_c)


# ══════════════════════════════════════════════
# TAB 5 — RISCO DE SAÚDE (Slide 19) — P_{dim} (1-4)
# ══════════════════════════════════════════════
with tabs[4]:
    st.markdown('<div class="section-title">Slide 19 · Risco de Impacto na Saúde — Probabilidade (P) por Dimensão</div>', unsafe_allow_html=True)
    st.caption("Eixo: P discreto (1=Baixo Risco · 2=Risco Médio · 3=Risco Moderado · 4=Alto Risco) "
               "calculado a partir do score médio de cada dimensão.")

    def chart_probabilidade(df_g, col_grupo, titulo):
        if df_g is None or df_g.empty:
            st.info("Sem dados disponíveis.")
            return

        top      = df_g.nlargest(top_n, "NR_geral")
        dims_ok  = [d for d in DIMENSOES if f"score_{d}" in top.columns]
        if not dims_ok:
            st.info("Dados de score não disponíveis.")
            return

        # Calcula P discreto para cada dimensão com base no score médio do grupo
        for d in dims_ok:
            top[f"P_calc_{d}"] = top[f"score_{d}"].apply(lambda s: score_para_P(s, d))

        fig = go.Figure()
        cores_d = [COR_VERMELHO, COR_LARANJA, COR_AMARELO, COR_VERDE, COR_ACCENT, "#B97CF7", "#5DCAA5"]
        for d, cor_d in zip(dims_ok, cores_d):
            fig.add_trace(go.Bar(
                name=DIMENSOES_LABEL[d],
                x=top[f"P_calc_{d}"],
                y=top[col_grupo],
                orientation="h",
                marker_color=cor_d,
                marker_line_width=0,
                text=top[f"P_calc_{d}"].astype(str),
                textposition="inside",
                textfont=dict(size=10, color="#fff"),
            ))

        fig.update_layout(
            barmode="group",
            title=dict(text=titulo, font=dict(size=13, color=COR_TEXTO), x=0),
            xaxis=dict(
                title="Probabilidade P (1–4)",
                gridcolor=COR_BORDA,
                range=[0, 5],
                tickvals=[1, 2, 3, 4],
                ticktext=["1 — Baixo", "2 — Médio", "3 — Moderado", "4 — Alto"],
            ),
            yaxis=dict(title="", autorange="reversed"),
            legend=dict(orientation="h", y=-0.25, font=dict(size=10)),
        )
        plotly_layout(fig, height=max(300, top_n * 60 + 100), margin=dict(l=20, r=20, t=40, b=120))
        st.plotly_chart(fig, use_container_width=True)

    chart_probabilidade(setor_f, "Setor", f"Top {top_n} Setores — P por Dimensão")
    chart_probabilidade(cargo_f, "Cargo", f"Top {top_n} Cargos — P por Dimensão")


# ══════════════════════════════════════════════
# TAB 6 — IMPACTO ORG. (Slide 20)
# Gráfico 1: barra HORIZONTAL empilhada (4 níveis) — absenteísmo
# Gráfico 2: barras horizontais SIMPLES por dimensão — adoecimento
# ══════════════════════════════════════════════
with tabs[5]:
    st.markdown('<div class="section-title">Slide 20 · Impacto Organizacional Relacionado ao Risco</div>', unsafe_allow_html=True)

    # ── Gráfico 1: Top setores por NR alto → absenteísmo ─────────────────
    # Tipo: BARRA HORIZONTAL EMPILHADA (4 níveis: Aceitável, Moderado, Importante, Crítico)
    st.markdown("##### Top setores por NR alto — Risco de Absenteísmo")
    st.caption("Barras horizontais empilhadas: distribuição dos 4 níveis de risco por setor.")

    if not setor_f.empty:
        top_abs = setor_f.nlargest(top_n, "NR_geral")

        niveis_abs = [
            ("Aceitável",  "perc_aceitavel",  COR_VERDE),
            ("Moderado",   "perc_moderado",   COR_AMARELO),
            ("Importante", "perc_importante", COR_LARANJA),
            ("Crítico",    "perc_critico",    COR_VERMELHO),
        ]

        fig_abs = go.Figure()
        for nivel_lbl, col_p, cor_n in niveis_abs:
            if col_p not in top_abs.columns:
                continue
            vals_perc = (top_abs[col_p] * 100).round(1)
            fig_abs.add_trace(go.Bar(
                name=nivel_lbl,
                y=top_abs["Setor"],
                x=vals_perc,
                orientation="h",
                marker_color=cor_n,
                marker_line_width=0,
                text=vals_perc.apply(lambda v: f"{v:.1f}%" if v >= 5 else ""),
                textposition="inside",
                textfont=dict(size=11, color="#fff"),
            ))

        fig_abs.update_layout(
            barmode="stack",
            xaxis=dict(title="% de trabalhadores", gridcolor=COR_BORDA, range=[0, 105]),
            yaxis=dict(title="", autorange="reversed"),
            legend=dict(orientation="h", y=1.08, x=0),
        )
        plotly_layout(fig_abs, height=max(300, top_n * 52 + 80))
        st.plotly_chart(fig_abs, use_container_width=True)

    st.markdown('<hr style="border-color:#2A2D3E; margin:2rem 0;">', unsafe_allow_html=True)

    # ── Gráfico 2: Top setores P+S alto → adoecimento ─────────────────────
    # Tipo: BARRAS HORIZONTAIS SIMPLES (não empilhadas) — NR por dimensão
    st.markdown("##### Top setores por maior P × S — Probabilidade de Adoecimento")
    st.caption("Barras horizontais por dimensão (não empilhadas). Ordenados pela soma dos NR.")

    if not setor_f.empty:
        cols_nr_dim = [f"NR_{d}" for d in DIMENSOES if f"NR_{d}" in setor_f.columns]
        if cols_nr_dim:
            setor_ps = setor_f.copy()
            setor_ps["score_ps_total"] = setor_ps[cols_nr_dim].sum(axis=1)
            top_adoec = setor_ps.nlargest(top_n, "score_ps_total")

            cores_d = [COR_VERMELHO, COR_LARANJA, COR_AMARELO,
                       COR_VERDE, COR_ACCENT, "#B97CF7", "#5DCAA5"]

            # Barras agrupadas horizontais (group, não stack)
            fig_adoec = go.Figure()
            for d, cor_d in zip(DIMENSOES, cores_d):
                col_nr = f"NR_{d}"
                if col_nr not in top_adoec.columns:
                    continue
                fig_adoec.add_trace(go.Bar(
                    name=DIMENSOES_LABEL[d],
                    y=top_adoec["Setor"],
                    x=top_adoec[col_nr],
                    orientation="h",
                    marker_color=cor_d,
                    marker_line_width=0,
                    text=top_adoec[col_nr].round(1).astype(str),
                    textposition="outside",
                    textfont=dict(size=10, color=COR_TEXTO),
                ))

            fig_adoec.update_layout(
                barmode="group",
                xaxis=dict(title="NR médio (1–16)", gridcolor=COR_BORDA),
                yaxis=dict(title="", autorange="reversed"),
                legend=dict(orientation="h", y=-0.3, font=dict(size=10)),
            )
            plotly_layout(fig_adoec,
                          height=max(300, top_n * 65 + 100),
                          margin=dict(l=20, r=20, t=20, b=100))
            st.plotly_chart(fig_adoec, use_container_width=True)


# ══════════════════════════════════════════════
# TAB 7 — HEATMAP (Slide 21)
# ══════════════════════════════════════════════
with tabs[6]:
    st.markdown('<div class="section-title">Slide 21 · Heatmap — Nível de Risco (NR) por Dimensão</div>', unsafe_allow_html=True)

    visao_hm   = st.radio("Agrupar por:", ["Setor", "Cargo", "Unidade"], horizontal=True, key="hm_visao")
    mapa_visao = {"Setor": setor_f, "Cargo": cargo_f, "Unidade": unidade_f}
    df_hm_src  = mapa_visao.get(visao_hm, setor_f)

    if df_hm_src is not None and not df_hm_src.empty:
        col_grupo_hm = visao_hm
        cols_nr_hm   = [f"NR_{d}" for d in DIMENSOES if f"NR_{d}" in df_hm_src.columns]
        labels_hm    = [DIMENSOES_LABEL[d] for d in DIMENSOES if f"NR_{d}" in df_hm_src.columns]

        df_hm  = df_hm_src.nlargest(min(20, len(df_hm_src)), "NR_geral")
        z_hm   = df_hm[cols_nr_hm].values
        y_hm   = df_hm[col_grupo_hm].tolist()
        annot  = [[f"{val:.1f}" for val in row] for row in z_hm]

        fig_hm = go.Figure(go.Heatmap(
            z=z_hm, x=labels_hm, y=y_hm,
            text=annot, texttemplate="%{text}",
            textfont=dict(size=11, color=COR_TEXTO),
            colorscale=[[0.0, COR_VERDE],[0.33, COR_AMARELO],[0.66, COR_LARANJA],[1.0, COR_VERMELHO]],
            zmin=1, zmax=16,
            colorbar=dict(
                tickvals=[1,4,8,12,16], ticktext=["1","4","8","12","16"],
                tickfont=dict(color=COR_TEXTO, size=11),
                title=dict(text="NR", font=dict(color=COR_TEXTO)),
                bgcolor="rgba(0,0,0,0)", bordercolor=COR_BORDA,
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
# TAB 8 — POR CARGO (Slide 22)
# Adicionado: N Respostas e Classificação de Risco Predominante na tabela
# ══════════════════════════════════════════════
with tabs[7]:
    st.markdown('<div class="section-title">Slide 22 · Análise Detalhada por Cargo</div>', unsafe_allow_html=True)

    if not cargo_f.empty:
        cargos_lista = cargo_f["Cargo"].tolist()
        cargo_sel    = st.selectbox("Selecione o cargo:", cargos_lista)
        row_cargo    = cargo_f[cargo_f["Cargo"] == cargo_sel].iloc[0]

        n_resp_cargo = int(row_cargo.get("n_colaboradores", 0))

        st.markdown(f"""
        <div class="kpi-grid">
          <div class="kpi-card">
            <div class="kpi-label">N Respostas</div>
            <div class="kpi-value">{n_resp_cargo}</div>
            <div class="kpi-sub">respondentes neste cargo</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">NR Geral</div>
            <div class="kpi-value">{row_cargo.get('NR_geral',0):.2f}</div>
            <div class="kpi-sub">escala 1–16</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Classificação</div>
            <div class="kpi-value" style="font-size:18px;">{row_cargo.get('classificacao','—')}</div>
            <div class="kpi-sub">nível de risco geral</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Em Risco Alto/Crítico</div>
            <div class="kpi-value" style="color:{COR_LARANJA};">{row_cargo.get('perc_risco_alto',0)*100:.1f}%</div>
            <div class="kpi-sub">Importante + Crítico</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Radar
        scores_cargo  = []
        labels_radar  = []
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
                fillcolor="rgba(79,142,247,0.15)",
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

        # ── Tabela NR por dimensão com colunas completas ──────────────────
        st.markdown('<div class="section-title">NR por Dimensão — Detalhamento</div>', unsafe_allow_html=True)

        # Monta tabela com: Dimensão, N Respostas, Score HSE-IT, P, S, Classificação de Risco, NR
        tab_dim_cargo = []
        base_cargo    = base_f[base_f["Informe seu cargo"] == cargo_sel]
        n_resp_dim    = len(base_cargo)

        for d in DIMENSOES:
            score_val = float(row_cargo.get(f"score_{d}", 0))
            nr_val    = float(row_cargo.get(f"NR_{d}", 0))
            p_val     = score_para_P(score_val, d)
            # S = NR / P (evita divisão por zero)
            s_val     = round(nr_val / p_val, 2) if p_val > 0 else 0.0
            class_val = score_para_classificacao(score_val, d)

            tab_dim_cargo.append({
                "Dimensão":               DIMENSOES_LABEL[d],
                "N Respostas":            n_resp_dim,
                "Score HSE-IT":           round(score_val, 2),
                "Probabilidade (P)":      p_val,
                "Severidade (S)":         s_val,
                "Classificação de Risco": class_val,
                "NR (P × S)":             round(nr_val, 2),
                "Polaridade":             "Negativa" if d in DIM_NEGATIVAS else "Positiva",
            })

        df_dim_cargo = pd.DataFrame(tab_dim_cargo)

        # Classificação predominante = a que aparece mais nas dimensões
        class_counts   = df_dim_cargo["Classificação de Risco"].value_counts()
        class_predom   = class_counts.index[0] if not class_counts.empty else "—"
        cor_predom     = cor_nivel(class_predom)

        st.markdown(f"""
        <div style="margin-bottom:12px; padding:10px 16px; background:{COR_CARD};
             border:1px solid {COR_BORDA}; border-radius:8px; display:inline-block;">
            <span style="font-size:11px; color:{COR_MUTED}; text-transform:uppercase;">
                Classificação Predominante:
            </span>
            <span style="font-size:14px; font-weight:600; color:{cor_predom}; margin-left:8px;">
                {class_predom}
            </span>
        </div>
        """, unsafe_allow_html=True)

        cols_style = ["Score HSE-IT", "Probabilidade (P)", "Severidade (S)", "NR (P × S)"]
        styled_cargo = (
            df_dim_cargo.style
            .map(_nr_row_color, subset=["NR (P × S)"])
            .map(_p_row_color,  subset=["Probabilidade (P)"])
            .map(_class_row_color, subset=["Classificação de Risco"])
            .format({"Score HSE-IT": "{:.2f}", "Severidade (S)": "{:.2f}", "NR (P × S)": "{:.2f}"})
        )
        st.dataframe(styled_cargo, use_container_width=True, hide_index=True)

        # Distribuição individual
        st.markdown(f'<div class="section-title">Distribuição individual ({n_resp_dim} respondentes)</div>',
                    unsafe_allow_html=True)

        dist_cargo  = base_cargo["risco_geral"].value_counts().reindex(NIVEIS_GERAL_ORDEM, fill_value=0)
        fig_dist_c  = go.Figure(go.Bar(
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
# TAB 9 — PGR (Slide 23)
# Adicionado: Score HSE-IT, P, S, Classificação de Risco por dimensão
# ══════════════════════════════════════════════
with tabs[8]:
    st.markdown('<div class="section-title">Slide 23 · PGR — Programa de Gerenciamento de Riscos</div>', unsafe_allow_html=True)
    st.caption("Análise por Unidade / Setor / Cargo × Categorias — Matriz NR (P × S)")

    visao_pgr = st.radio("Dimensão de análise:", ["Setor", "Cargo", "Unidade"],
                         horizontal=True, key="pgr_visao")
    mapa_pgr  = {
        "Setor":   (setor_f,   "Setor"),
        "Cargo":   (cargo_f,   "Cargo"),
        "Unidade": (unidade_f if unidade_f is not None else pd.DataFrame(), "Unidade"),
    }
    df_pgr_src, col_pgr = mapa_pgr[visao_pgr]

    if df_pgr_src is not None and not df_pgr_src.empty:

        # ── Monta tabela PGR completa ──────────────────────────────────────
        # Colunas: Grupo | N | Score HSE-IT (por dim) | P (por dim) | S (por dim) |
        #          Classificação de Risco (por dim) | NR (por dim) | NR Geral | Classificação Geral
        rows_pgr = []
        for _, row in df_pgr_src.iterrows():
            rec = {
                col_pgr:         row[col_pgr],
                "N":             int(row.get("n_colaboradores", 0)),
                "NR Geral":      round(float(row.get("NR_geral", 0)), 2),
                "Classificação": row.get("classificacao", ""),
            }
            for d in DIMENSOES:
                score_v = float(row.get(f"score_{d}", 0))
                nr_v    = float(row.get(f"NR_{d}",    0))
                p_v     = score_para_P(score_v, d)
                s_v     = round(nr_v / p_v, 2) if p_v > 0 else 0.0
                lbl     = DIMENSOES_LABEL[d]
                rec[f"Score — {lbl}"]   = round(score_v, 2)
                rec[f"P — {lbl}"]       = p_v
                rec[f"S — {lbl}"]       = s_v
                rec[f"Class. — {lbl}"]  = score_para_classificacao(score_v, d)
                rec[f"NR — {lbl}"]      = round(nr_v, 2)
            rows_pgr.append(rec)

        df_pgr_full = pd.DataFrame(rows_pgr).sort_values("NR Geral", ascending=False).reset_index(drop=True)

        # Seleção de colunas a exibir (controla complexidade visual)
        col_view = st.radio(
            "Visualizar:",
            ["Resumo (NR por dimensão)", "Score + P + S + Classificação", "Completo"],
            horizontal=True,
            key="pgr_col_view"
        )

        nr_cols    = [f"NR — {DIMENSOES_LABEL[d]}" for d in DIMENSOES]
        score_cols = [f"Score — {DIMENSOES_LABEL[d]}" for d in DIMENSOES]
        p_cols     = [f"P — {DIMENSOES_LABEL[d]}"     for d in DIMENSOES]
        s_cols     = [f"S — {DIMENSOES_LABEL[d]}"     for d in DIMENSOES]
        class_cols = [f"Class. — {DIMENSOES_LABEL[d]}" for d in DIMENSOES]

        if col_view == "Resumo (NR por dimensão)":
            cols_show_pgr = [col_pgr, "N", "NR Geral", "Classificação"] + nr_cols
        elif col_view == "Score + P + S + Classificação":
            cols_show_pgr = [col_pgr, "N"] + score_cols + p_cols + s_cols + class_cols
        else:
            cols_show_pgr = [col_pgr, "N", "NR Geral", "Classificação"] + score_cols + p_cols + s_cols + class_cols + nr_cols

        cols_show_pgr = [c for c in cols_show_pgr if c in df_pgr_full.columns]
        df_pgr_show   = df_pgr_full[cols_show_pgr]

        # Estilização
        num_cols_fmt  = {c: "{:.2f}" for c in (nr_cols + score_cols + s_cols) if c in df_pgr_show.columns}
        style_pgr = df_pgr_show.style.format(num_cols_fmt)

        if col_view in ["Resumo (NR por dimensão)", "Completo"]:
            nr_present = [c for c in nr_cols if c in df_pgr_show.columns]
            if nr_present:
                style_pgr = style_pgr.map(_nr_row_color, subset=["NR Geral"] + nr_present)

        if col_view in ["Score + P + S + Classificação", "Completo"]:
            p_present     = [c for c in p_cols    if c in df_pgr_show.columns]
            class_present = [c for c in class_cols if c in df_pgr_show.columns]
            if p_present:
                style_pgr = style_pgr.map(_p_row_color, subset=p_present)
            if class_present:
                style_pgr = style_pgr.map(_class_row_color, subset=class_present)

        st.dataframe(style_pgr, use_container_width=True,
                     height=min(600, (len(df_pgr_full)+1) * 38))

        st.markdown('<hr style="border-color:#2A2D3E; margin:2rem 0;">', unsafe_allow_html=True)
        st.markdown("##### Matriz de Risco — Heatmap PGR")

        cols_nr_pgr = [f"NR_{d}" for d in DIMENSOES if f"NR_{d}" in df_pgr_src.columns]
        labels_pgr  = [DIMENSOES_LABEL[d] for d in DIMENSOES if f"NR_{d}" in df_pgr_src.columns]
        df_pgr_hm   = df_pgr_src.sort_values("NR_geral", ascending=False)

        z_pgr      = df_pgr_hm[cols_nr_pgr].values
        y_pgr      = df_pgr_hm[col_pgr].tolist()
        annot_pgr  = [[f"{v:.1f}" for v in row] for row in z_pgr]

        fig_pgr = go.Figure(go.Heatmap(
            z=z_pgr, x=labels_pgr, y=y_pgr,
            text=annot_pgr, texttemplate="%{text}",
            textfont=dict(size=11),
            colorscale=[[0.0, COR_VERDE],[0.25, COR_AMARELO],[0.55, COR_LARANJA],[1.0, COR_VERMELHO]],
            zmin=1, zmax=16,
            colorbar=dict(
                tickvals=[2, 6, 10, 14],
                ticktext=["Aceitável","Moderado","Importante","Crítico"],
                tickfont=dict(color=COR_TEXTO, size=10),
                title=dict(text="NR", font=dict(color=COR_TEXTO)),
                bgcolor="rgba(0,0,0,0)", bordercolor=COR_BORDA,
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
