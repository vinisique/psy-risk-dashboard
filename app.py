import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# =========================
# CONFIG & TEMA
# =========================
st.set_page_config(
    page_title="OrgPulse · Riscos Psicossociais",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado — design premium
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

/* ---- Reset & Base ---- */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ---- Sidebar ---- */
[data-testid="stSidebar"] {
    background-color: #0F1923;
    border-right: 1px solid #1E2D3D;
}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stMultiSelect label {
    color: #8B9BB4 !important;
    font-size: 11px !important;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    font-weight: 500;
}
[data-testid="stSidebar"] [data-baseweb="select"] {
    background: #1A2535 !important;
    border: 1px solid #1E2D3D !important;
    border-radius: 6px !important;
}
[data-testid="stSidebar"] [data-baseweb="tag"] {
    background: #1E3A5C !important;
    color: #60A5FA !important;
}

/* ---- Esconde elementos padrão ---- */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0 !important; max-width: 100% !important; }

/* ---- Cards KPI ---- */
.kpi-card {
    background: #111C2A;
    border: 1px solid #1E2D3D;
    border-radius: 10px;
    padding: 18px 20px;
    border-left: 3px solid;
    position: relative;
    overflow: hidden;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; right: 0;
    width: 60px; height: 60px;
    border-radius: 0 10px 0 60px;
    opacity: 0.06;
}
.kpi-card.info  { border-left-color: #3B82F6; }
.kpi-card.info::before { background: #3B82F6; }
.kpi-card.warn  { border-left-color: #F59E0B; }
.kpi-card.warn::before { background: #F59E0B; }
.kpi-card.alert { border-left-color: #EF4444; }
.kpi-card.alert::before { background: #EF4444; }
.kpi-card.ok    { border-left-color: #10B981; }
.kpi-card.ok::before { background: #10B981; }
.kpi-label {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #5A7A9A;
    margin-bottom: 8px;
}
.kpi-value {
    font-size: 28px;
    font-weight: 600;
    color: #E8F0FE;
    line-height: 1;
}
.kpi-sub {
    font-size: 11px;
    color: #4A6080;
    margin-top: 6px;
}

/* ---- Section titles ---- */
.section-title {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #3B82F6;
    margin: 28px 0 14px 0;
    display: flex;
    align-items: center;
    gap: 8px;
}
.section-title::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(to right, #1E2D3D, transparent);
}

/* ---- Panel ---- */
.panel {
    background: #111C2A;
    border: 1px solid #1E2D3D;
    border-radius: 10px;
    padding: 20px;
}
.panel-title {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #5A7A9A;
    margin-bottom: 16px;
}

/* ---- Badge de risco ---- */
.badge {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 20px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.05em;
}
.badge-critico { background: rgba(239,68,68,0.15); color: #F87171; }
.badge-alto    { background: rgba(245,158,11,0.15); color: #FCD34D; }
.badge-normal  { background: rgba(16,185,129,0.15); color: #34D399; }

/* ---- Topbar ---- */
.topbar {
    background: #0A1520;
    border-bottom: 1px solid #1E2D3D;
    padding: 14px 32px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0;
}
.topbar-brand {
    font-size: 16px;
    font-weight: 600;
    color: #E8F0FE;
    letter-spacing: -0.01em;
}
.topbar-brand span { color: #3B82F6; }
.topbar-sub {
    font-size: 11px;
    color: #3A5270;
    margin-top: 2px;
}
.topbar-tag {
    background: rgba(59,130,246,0.1);
    border: 1px solid rgba(59,130,246,0.25);
    color: #60A5FA;
    font-size: 10px;
    font-weight: 500;
    padding: 3px 10px;
    border-radius: 20px;
    letter-spacing: 0.04em;
}

/* ---- Alert card (focos críticos) ---- */
.alert-card {
    background: #111C2A;
    border: 1px solid #1E2D3D;
    border-left: 3px solid;
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 10px;
}
.alert-card.critico { border-left-color: #EF4444; }
.alert-card.alto    { border-left-color: #F59E0B; }
.alert-card.normal  { border-left-color: #10B981; }
.alert-head { font-size: 13px; font-weight: 600; color: #CBD5E1; margin-bottom: 4px; }
.alert-body { font-size: 11px; color: #4A6080; }
.alert-metric { font-size: 22px; font-weight: 700; margin-top: 8px; }

/* ---- Separador ---- */
.separator {
    height: 1px;
    background: linear-gradient(to right, transparent, #1E2D3D, transparent);
    margin: 6px 0;
}

/* ---- Main wrap ---- */
.main-wrap { padding: 0 32px 32px 32px; background: #0A1520; min-height: 100vh; }

/* Override streamlit metric ---- */
[data-testid="stMetricValue"] { font-size: 24px !important; }
[data-testid="metric-container"] {
    background: #111C2A;
    border: 1px solid #1E2D3D;
    border-radius: 10px;
    padding: 14px !important;
}
</style>
""", unsafe_allow_html=True)

# =========================
# PLOTLY THEME
# =========================
PLOT_BG     = "rgba(0,0,0,0)"
PAPER_BG    = "rgba(0,0,0,0)"
FONT_COLOR  = "#8B9BB4"
GRID_COLOR  = "#1E2D3D"
FONT_FAMILY = "Inter, sans-serif"

def base_layout(height=300):
    return dict(
        height=height,
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(family=FONT_FAMILY, color=FONT_COLOR, size=11),
        margin=dict(l=8, r=8, t=8, b=8),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor="#1E2D3D",
            font=dict(size=10)
        ),
        xaxis=dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR, tickfont=dict(size=10)),
        yaxis=dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR, tickfont=dict(size=10)),
    )

# Paleta semântica
COR_CRITICO = "#EF4444"
COR_ALTO    = "#F59E0B"
COR_NORMAL  = "#10B981"
COR_AZUL    = "#3B82F6"
COR_DIMS    = ["#3B82F6","#60A5FA","#93C5FD","#818CF8","#A78BFA","#C084FC","#E879F9"]

# Labels amigáveis das dimensões
DIM_LABELS = {
    "score_Demandas":      "Demandas",
    "score_Controle":      "Controle",
    "score_Apoio_Chefia":  "Apoio Chefia",
    "score_Apoio_Colegas": "Apoio Colegas",
    "score_Relacionamentos":"Relacionamentos",
    "score_Cargo":         "Cargo",
    "score_Comunicacao":   "Comunicação"
}

# Dimensões negativas (score alto = pior)
DIM_NEGATIVAS = ["Demandas", "Relacionamentos"]
DIM_POSITIVAS = ["Controle", "Apoio_Chefia", "Apoio_Colegas", "Cargo", "Comunicacao"]

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    df_base  = pd.read_parquet("base.parquet")
    df_setor = pd.read_parquet("setor.parquet")
    df_cargo = pd.read_parquet("cargo.parquet")
    return df_base, df_setor, df_cargo

try:
    df_base, df_setor, df_cargo = load_data()
except Exception as e:
    st.error(f"Erro ao carregar base.parquet / setor.parquet / cargo.parquet: {e}")
    st.info("Certifique-se de que os arquivos .parquet estão no mesmo diretório do dashboard.")
    st.stop()

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.markdown("""
    <div style='padding:20px 4px 24px'>
        <div style='font-size:18px;font-weight:700;color:#E8F0FE;letter-spacing:-0.01em'>Org<span style="color:#3B82F6">Pulse</span></div>
        <div style='font-size:10px;color:#3A5270;margin-top:2px'>Riscos Psicossociais · HSE-IT</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("**Filtros**")

    empresas_all = sorted(df_base['Empresa'].dropna().unique())
    empresa_sel = st.multiselect("Empresa", empresas_all, default=empresas_all, key="empresa")

    unidades_all = sorted(df_base['Informe sua unidade'].dropna().unique())
    unidade_sel = st.multiselect("Unidade", unidades_all, default=unidades_all, key="unidade")

    setores_all = sorted(df_base['Informe seu setor / departamento.'].dropna().unique())
    setor_sel = st.multiselect("Setor", setores_all, default=setores_all, key="setor")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style='background:#1A2535;border:1px solid #1E2D3D;border-radius:8px;padding:12px;margin-top:8px'>
        <div style='font-size:10px;font-weight:600;letter-spacing:0.08em;color:#3B82F6;text-transform:uppercase;margin-bottom:8px'>Legenda de Risco</div>
        <div style='font-size:11px;color:#8B9BB4;margin-bottom:4px'><span style='color:#EF4444;font-weight:700'>●</span> Crítico — ≥2 dimensões em Alto</div>
        <div style='font-size:11px;color:#8B9BB4;margin-bottom:4px'><span style='color:#F59E0B;font-weight:700'>●</span> Alto — 1 dimensão em Alto</div>
        <div style='font-size:11px;color:#8B9BB4'><span style='color:#10B981;font-weight:700'>●</span> Normal — sem dimensão em Alto</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style='font-size:10px;color:#2A3D54;margin-top:24px;line-height:1.6'>
        Modelo: HSE-IT (Lucca et al.)<br>
        Escala: Likert 0–4<br>
        Polarização: Demandas e Relacionamentos (inversa)
    </div>
    """, unsafe_allow_html=True)

# =========================
# FILTRAR BASE
# =========================
df = df_base[
    (df_base['Empresa'].isin(empresa_sel)) &
    (df_base['Informe sua unidade'].isin(unidade_sel)) &
    (df_base['Informe seu setor / departamento.'].isin(setor_sel))
]

# Recalcular df_setor e df_cargo com os filtros
cols_scores = list(DIM_LABELS.keys())

df_setor_f = (
    df.groupby('Informe seu setor / departamento.')
    .agg({
        'IGRP': 'mean',
        **{c: 'mean' for c in cols_scores},
        'risco_geral': lambda x: (x.isin(['Alto','Crítico'])).mean()
    })
    .reset_index()
    .rename(columns={'risco_geral': 'perc_risco_alto', 'Informe seu setor / departamento.': 'Setor'})
)

df_cargo_f = (
    df.groupby('Informe seu cargo')
    .agg({
        'IGRP': 'mean',
        'risco_geral': lambda x: (x.isin(['Alto','Crítico'])).mean()
    })
    .reset_index()
    .rename(columns={'risco_geral': 'perc_risco_alto', 'Informe seu cargo': 'Cargo'})
)

n_total   = len(df)
igrp_med  = df['IGRP'].mean() if n_total > 0 else 0
perc_ac   = (df['risco_geral'].isin(['Alto','Crítico'])).mean() * 100 if n_total > 0 else 0
perc_crit = (df['risco_geral'] == 'Crítico').mean() * 100 if n_total > 0 else 0

# =========================
# TOPBAR
# =========================
st.markdown(f"""
<div class="topbar">
    <div>
        <div class="topbar-brand">Org<span>Pulse</span> <span style='color:#3A5270;font-weight:300;font-size:13px'>·</span> Dashboard Psicossocial</div>
        <div class="topbar-sub">Modelo HSE-IT · Validação Lucca et al. · {n_total} respondentes no filtro atual</div>
    </div>
    <div class="topbar-tag">Plataforma Vivamente 360°</div>
</div>
""", unsafe_allow_html=True)

# =========================
# MAIN WRAP
# =========================
st.markdown('<div class="main-wrap">', unsafe_allow_html=True)

# =========================
# SEÇÃO 1: KPIs
# =========================
st.markdown('<div class="section-title">Visão Geral</div>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

def cor_igrp(v):
    if v >= 3.1: return "alert"
    elif v >= 2.1: return "warn"
    elif v >= 1.1: return "ok"
    return "ok"

def cor_perc(v):
    if v >= 30: return "alert"
    elif v >= 15: return "warn"
    return "ok"

with col1:
    st.markdown(f"""
    <div class="kpi-card info">
        <div class="kpi-label">Colaboradores</div>
        <div class="kpi-value">{n_total:,}</div>
        <div class="kpi-sub">respondentes no filtro atual</div>
    </div>""", unsafe_allow_html=True)

with col2:
    cls = cor_igrp(igrp_med)
    st.markdown(f"""
    <div class="kpi-card {cls}">
        <div class="kpi-label">IGRP Médio</div>
        <div class="kpi-value">{igrp_med:.2f}</div>
        <div class="kpi-sub">Índice Geral de Riscos Psicossociais</div>
    </div>""", unsafe_allow_html=True)

with col3:
    cls = cor_perc(perc_ac)
    st.markdown(f"""
    <div class="kpi-card {cls}">
        <div class="kpi-label">% Alto ou Crítico</div>
        <div class="kpi-value">{perc_ac:.1f}%</div>
        <div class="kpi-sub">{int(n_total * perc_ac / 100)} colaboradores em atenção</div>
    </div>""", unsafe_allow_html=True)

with col4:
    cls = "alert" if perc_crit > 10 else ("warn" if perc_crit > 5 else "ok")
    st.markdown(f"""
    <div class="kpi-card {cls}">
        <div class="kpi-label">% Crítico</div>
        <div class="kpi-value">{perc_crit:.1f}%</div>
        <div class="kpi-sub">≥ 2 dimensões em Alto Risco</div>
    </div>""", unsafe_allow_html=True)

# =========================
# SEÇÃO 2: DISTRIBUIÇÃO + IGRP
# =========================
st.markdown('<div class="section-title">Distribuição de Risco</div>', unsafe_allow_html=True)

col_a, col_b = st.columns([1, 1.6])

with col_a:
    # Distribuição de risco — donut
    dist = df['risco_geral'].value_counts()
    labels_ord = ["Normal", "Alto", "Crítico"]
    vals = [dist.get(l, 0) for l in labels_ord]
    colors = [COR_NORMAL, COR_ALTO, COR_CRITICO]

    fig_donut = go.Figure(go.Pie(
        labels=labels_ord,
        values=vals,
        hole=0.65,
        marker=dict(colors=colors, line=dict(color="#0A1520", width=3)),
        textfont=dict(size=11, family=FONT_FAMILY),
        textinfo="percent",
        hovertemplate="<b>%{label}</b><br>%{value} colaboradores (%{percent})<extra></extra>"
    ))
    fig_donut.add_annotation(
        text=f"<b>{n_total}</b><br><span style='font-size:10px'>total</span>",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=18, color="#E8F0FE", family=FONT_FAMILY),
        align="center"
    )
    lay = base_layout(height=260)
    lay.update(showlegend=True, legend=dict(orientation="h", y=-0.05, x=0.5, xanchor="center"))
    fig_donut.update_layout(**lay)
    st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})

with col_b:
    # IGRP por setor — horizontal bars
    top_set = df_setor_f.sort_values('IGRP', ascending=True).tail(10)

    def cor_igrp_bar(v):
        if v >= 3.1: return COR_CRITICO
        elif v >= 2.1: return COR_ALTO
        else: return COR_NORMAL

    bar_colors = [cor_igrp_bar(v) for v in top_set['IGRP']]

    fig_setor = go.Figure(go.Bar(
        x=top_set['IGRP'],
        y=top_set['Setor'],
        orientation='h',
        marker=dict(color=bar_colors, line=dict(width=0)),
        text=[f"{v:.2f}" for v in top_set['IGRP']],
        textposition="outside",
        textfont=dict(size=10, color="#8B9BB4", family=FONT_FAMILY),
        hovertemplate="<b>%{y}</b><br>IGRP: %{x:.2f}<extra></extra>"
    ))
    lay = base_layout(height=260)
    lay.update(
        title=dict(text="IGRP por Setor (Top 10)", font=dict(size=11, color="#5A7A9A"), x=0),
        xaxis=dict(range=[0, 4.5], title="", tickvals=[0,1,2,3,4]),
        yaxis=dict(title=""),
        bargap=0.35,
    )
    fig_setor.update_layout(**lay)
    st.plotly_chart(fig_setor, use_container_width=True, config={"displayModeBar": False})

# =========================
# SEÇÃO 3: DIMENSÕES HSE
# =========================
st.markdown('<div class="section-title">Diagnóstico por Dimensão HSE</div>', unsafe_allow_html=True)

col_c, col_d = st.columns([1.6, 1])

with col_c:
    # Score médio por dimensão — radar + barras
    dim_means = {label: df[col].mean() for col, label in DIM_LABELS.items() if col in df.columns}

    dims = list(dim_means.keys())
    vals_dim = list(dim_means.values())

    # Cor de cada dimensão conforme polaridade
    def cor_dim(nome, score):
        if nome in ["Demandas", "Relacionamentos"]:
            # negativo: alto é ruim
            if score >= 3.1: return COR_CRITICO
            elif score >= 2.1: return COR_ALTO
            else: return COR_NORMAL
        else:
            # positivo: baixo é ruim
            if score <= 1: return COR_CRITICO
            elif score <= 2: return COR_ALTO
            else: return COR_NORMAL

    bar_cols_dim = [cor_dim(d, v) for d, v in zip(dims, vals_dim)]

    fig_dim = go.Figure()

    # Barras de score
    fig_dim.add_trace(go.Bar(
        x=vals_dim,
        y=dims,
        orientation='h',
        marker=dict(color=bar_cols_dim, line=dict(width=0)),
        text=[f"{v:.2f}" for v in vals_dim],
        textposition="outside",
        textfont=dict(size=11, color="#8B9BB4", family=FONT_FAMILY),
        width=0.55,
        hovertemplate="<b>%{y}</b><br>Score: %{x:.2f}<extra></extra>"
    ))

    # Linha de referência — 0 a 4 max
    lay = base_layout(height=300)
    lay.update(
        title=dict(text="Score médio por dimensão (0–4) · Cores indicam nível de risco", font=dict(size=11, color="#5A7A9A"), x=0),
        xaxis=dict(range=[0, 4.8], title="", tickvals=[0, 1, 2, 3, 4],
                   showgrid=True, gridcolor="#1A2535"),
        yaxis=dict(title="", autorange="reversed"),
        bargap=0.3,
        shapes=[
            # faixa risco alto (negativos) >= 3.1
            dict(type="rect", xref="x", yref="paper",
                 x0=3.1, x1=4.0, y0=0, y1=1,
                 fillcolor=COR_CRITICO, opacity=0.05, line_width=0),
        ]
    )
    fig_dim.update_layout(**lay)
    st.plotly_chart(fig_dim, use_container_width=True, config={"displayModeBar": False})

with col_d:
    st.markdown('<div class="panel" style="height:100%">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">Diagnóstico de Atenção</div>', unsafe_allow_html=True)

    # Ordenar dimensões pelo nível de risco (piores primeiro)
    def severidade_dim(nome, score):
        if nome in ["Demandas", "Relacionamentos"]:
            if score >= 3.1: return (3, score)
            elif score >= 2.1: return (2, score)
            else: return (1, score)
        else:
            if score <= 1: return (3, -score)
            elif score <= 2: return (2, -score)
            else: return (1, -score)

    dims_sorted = sorted(dim_means.items(), key=lambda x: severidade_dim(x[0], x[1]), reverse=True)

    for nome, score in dims_sorted:
        c = cor_dim(nome, score)
        if c == COR_CRITICO:
            badge = '<span class="badge badge-critico">Alto Risco</span>'
            nota = "⚠ requer ação"
        elif c == COR_ALTO:
            badge = '<span class="badge badge-alto">Moderado</span>'
            nota = "monitorar"
        else:
            badge = '<span class="badge badge-normal">Adequado</span>'
            nota = ""

        pol = "↑ alto é pior" if nome in ["Demandas", "Relacionamentos"] else "↓ baixo é pior"
        st.markdown(f"""
        <div style='margin-bottom:12px;padding-bottom:12px;border-bottom:1px solid #1A2535'>
            <div style='display:flex;justify-content:space-between;align-items:center'>
                <span style='font-size:12px;font-weight:600;color:#CBD5E1'>{nome}</span>
                {badge}
            </div>
            <div style='display:flex;align-items:center;gap:8px;margin-top:6px'>
                <div style='flex:1;height:5px;background:#1A2535;border-radius:3px'>
                    <div style='width:{score/4*100:.0f}%;height:100%;background:{c};border-radius:3px'></div>
                </div>
                <span style='font-size:12px;font-weight:700;color:{c};min-width:28px'>{score:.2f}</span>
            </div>
            <div style='font-size:10px;color:#3A5270;margin-top:3px'>{pol} · {nota}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# SEÇÃO 4: HEATMAP SETOR × DIMENSÃO
# =========================
st.markdown('<div class="section-title">Heatmap — Setor × Dimensão</div>', unsafe_allow_html=True)

top_set_hm = df_setor_f.sort_values('IGRP', ascending=False).head(10)
dim_cols = list(DIM_LABELS.keys())
dim_nomes = list(DIM_LABELS.values())

z_vals = top_set_hm[dim_cols].values.tolist()
setores_hm = top_set_hm['Setor'].tolist()

# Customtext com valor formatado
custom = [[f"{v:.2f}" for v in row] for row in z_vals]

fig_heat = go.Figure(go.Heatmap(
    z=z_vals,
    x=dim_nomes,
    y=setores_hm,
    text=custom,
    texttemplate="%{text}",
    textfont=dict(size=10, family=FONT_FAMILY),
    colorscale=[
        [0.0,  "#0D3B2E"],
        [0.25, "#10B981"],
        [0.5,  "#F59E0B"],
        [0.75, "#EF4444"],
        [1.0,  "#7F1D1D"],
    ],
    zmin=0, zmax=4,
    colorbar=dict(
        title=dict(text="Score", font=dict(size=10, color="#5A7A9A")),
        tickfont=dict(size=9, color="#5A7A9A"),
        thickness=12,
        len=0.8,
        tickvals=[0,1,2,3,4],
        ticktext=["0","1","2","3","4"],
        bgcolor="rgba(0,0,0,0)",
        bordercolor="#1E2D3D"
    ),
    hovertemplate="<b>%{y}</b><br>%{x}: %{z:.2f}<extra></extra>"
))

lay = base_layout(height=max(280, len(setores_hm) * 32 + 60))
lay.update(
    xaxis=dict(side="top", tickfont=dict(size=10), showgrid=False),
    yaxis=dict(showgrid=False, tickfont=dict(size=10), autorange="reversed"),
)
fig_heat.update_layout(**lay)
st.plotly_chart(fig_heat, use_container_width=True, config={"displayModeBar": False})

st.markdown("""
<div style='font-size:10px;color:#3A5270;margin-top:-8px;margin-bottom:8px'>
⚠ Atenção à polaridade: para Demandas e Relacionamentos, valores altos = maior risco. Para demais dimensões, valores baixos = maior risco.
</div>
""", unsafe_allow_html=True)

# =========================
# SEÇÃO 5: FOCOS CRÍTICOS
# =========================
st.markdown('<div class="section-title">Focos Críticos — Top 5 Setores e Cargos</div>', unsafe_allow_html=True)

col_e, col_f = st.columns(2)

with col_e:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">Top 5 Setores por IGRP</div>', unsafe_allow_html=True)

    top5_set = df_setor_f.sort_values('IGRP', ascending=False).head(5)

    for _, row in top5_set.iterrows():
        igrp = row['IGRP']
        perc = row['perc_risco_alto'] * 100
        if igrp >= 3.1:
            cls, badge, cor_v = "critico", "Crítico", COR_CRITICO
        elif igrp >= 2.1:
            cls, badge, cor_v = "alto", "Alto", COR_ALTO
        else:
            cls, badge, cor_v = "normal", "Normal", COR_NORMAL

        st.markdown(f"""
        <div class="alert-card {cls}">
            <div style='display:flex;justify-content:space-between;align-items:flex-start'>
                <div>
                    <div class="alert-head">{row['Setor']}</div>
                    <div class="alert-body">{perc:.1f}% dos colaboradores em Alto ou Crítico</div>
                </div>
                <span class="badge badge-{cls}">{badge}</span>
            </div>
            <div class="alert-metric" style='color:{cor_v}'>IGRP {igrp:.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

with col_f:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">Top 5 Cargos por IGRP</div>', unsafe_allow_html=True)

    top5_cargo = df_cargo_f.sort_values('IGRP', ascending=False).head(5)

    for _, row in top5_cargo.iterrows():
        igrp = row['IGRP']
        perc = row['perc_risco_alto'] * 100
        if igrp >= 3.1:
            cls, badge, cor_v = "critico", "Crítico", COR_CRITICO
        elif igrp >= 2.1:
            cls, badge, cor_v = "alto", "Alto", COR_ALTO
        else:
            cls, badge, cor_v = "normal", "Normal", COR_NORMAL

        st.markdown(f"""
        <div class="alert-card {cls}">
            <div style='display:flex;justify-content:space-between;align-items:flex-start'>
                <div>
                    <div class="alert-head">{row['Cargo']}</div>
                    <div class="alert-body">{perc:.1f}% dos colaboradores em Alto ou Crítico</div>
                </div>
                <span class="badge badge-{cls}">{badge}</span>
            </div>
            <div class="alert-metric" style='color:{cor_v}'>IGRP {igrp:.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# SEÇÃO 6: BASE DETALHADA (expansível)
# =========================
st.markdown('<div class="section-title">Análise Detalhada</div>', unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📊 Por Setor", "👤 Por Cargo"])

with tab1:
    cols_exib_setor = ['Setor', 'IGRP', 'perc_risco_alto'] + [c for c in dim_cols if c in df_setor_f.columns]
    df_exib = df_setor_f[cols_exib_setor].copy()
    df_exib = df_exib.rename(columns={**DIM_LABELS, 'perc_risco_alto': '% Risco Alto/Crítico'})
    df_exib['IGRP'] = df_exib['IGRP'].round(2)
    df_exib['% Risco Alto/Crítico'] = (df_exib['% Risco Alto/Crítico'] * 100).round(1).astype(str) + '%'
    for d in DIM_LABELS.values():
        if d in df_exib.columns:
            df_exib[d] = df_exib[d].round(2)
    st.dataframe(
        df_exib.sort_values('IGRP', ascending=False),
        use_container_width=True,
        hide_index=True
    )

with tab2:
    df_exib_c = df_cargo_f.copy()
    df_exib_c['IGRP'] = df_exib_c['IGRP'].round(2)
    df_exib_c['perc_risco_alto'] = (df_exib_c['perc_risco_alto'] * 100).round(1).astype(str) + '%'
    df_exib_c = df_exib_c.rename(columns={'perc_risco_alto': '% Risco Alto/Crítico'})
    st.dataframe(
        df_exib_c.sort_values('IGRP', ascending=False),
        use_container_width=True,
        hide_index=True
    )

with st.expander("📋 Base Individual Completa"):
    cols_show = [
        'Empresa', 'Informe sua unidade',
        'Informe seu setor / departamento.',
        'Informe seu cargo', 'IGRP', 'risco_geral'
    ] + [c for c in dim_cols if c in df.columns]
    df_show = df[cols_show].copy()
    df_show = df_show.rename(columns=DIM_LABELS)
    df_show['IGRP'] = df_show['IGRP'].round(2)
    for d in DIM_LABELS.values():
        if d in df_show.columns:
            df_show[d] = df_show[d].round(2)
    st.dataframe(df_show, use_container_width=True, hide_index=True)

st.markdown('</div>', unsafe_allow_html=True)  # main-wrap
