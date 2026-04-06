import streamlit as st
import pandas as pd
import plotly.express as px

# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="OrgPulse · Risk Intelligence",
    layout="wide"
)

# =========================
# CSS (CORRIGIDO E SEGURO)
# =========================
st.markdown("""
<style>
html, body {
    background-color: #0D0F14;
    color: #E8EAF0;
    font-family: sans-serif;
}

/* SIDEBAR */
[data-testid="stSidebar"] {
    background-color: #111318;
    border-right: 1px solid #1E2130;
}

/* INPUTS */
[data-testid="stSidebar"] * {
    color: #E8EAF0 !important;
}

/* KPI CARDS */
.kpi {
    background: #111318;
    border: 1px solid #1E2130;
    border-radius: 10px;
    padding: 16px;
}

.kpi-title {
    font-size: 12px;
    color: #8B8FA8;
}

.kpi-value {
    font-size: 28px;
    font-weight: bold;
}

/* TABLE FIX (CRÍTICO) */
[data-testid="stDataFrame"] {
    background-color: #111318 !important;
}

[data-testid="stDataFrame"] div {
    color: #E8EAF0 !important;
}

/* TITLES */
.section-title {
    font-size: 18px;
    margin-bottom: 10px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    return pd.read_parquet("base.parquet")

df_base = load_data()

COL_UNIDADE = "Informe sua unidade"
COL_SETOR = "Informe seu setor / departamento."
COL_CARGO = "Informe seu cargo"

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.markdown("### Filtros")

    empresa = st.multiselect(
        "Empresa",
        df_base['Empresa'].unique(),
        default=df_base['Empresa'].unique()
    )

    unidade = st.multiselect(
        "Unidade",
        df_base[COL_UNIDADE].unique(),
        default=df_base[COL_UNIDADE].unique()
    )

    setor = st.multiselect(
        "Setor",
        df_base[COL_SETOR].unique(),
        default=df_base[COL_SETOR].unique()
    )

# =========================
# FILTER
# =========================
df = df_base[
    (df_base['Empresa'].isin(empresa)) &
    (df_base[COL_UNIDADE].isin(unidade)) &
    (df_base[COL_SETOR].isin(setor))
]

# =========================
# HEADER
# =========================
st.title("OrgPulse · Psychosocial Risk Intelligence")

# =========================
# KPIs (ESCALA CORRIGIDA)
# =========================
total = len(df)
igrp = df['IGRP'].mean()

pct_alto = (df['risco_geral'].isin(['Alto','Crítico']).mean()) * 100
pct_crit = (df['risco_geral'] == 'Crítico').mean() * 100

c1, c2, c3, c4 = st.columns(4)

def cor_igrp(v):
    if v < 2: return "#00C9A7"
    elif v < 2.6: return "#FFB547"
    else: return "#FF4D6A"

with c1:
    st.markdown(f"""
    <div class="kpi">
        <div class="kpi-title">Colaboradores</div>
        <div class="kpi-value">{total}</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="kpi">
        <div class="kpi-title">IGRP Médio</div>
        <div class="kpi-value" style="color:{cor_igrp(igrp)}">{round(igrp,2)}</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="kpi">
        <div class="kpi-title">% Alto/Crítico</div>
        <div class="kpi-value">{round(pct_alto,1)}%</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="kpi">
        <div class="kpi-title">% Crítico</div>
        <div class="kpi-value">{round(pct_crit,1)}%</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# =========================
# ROW 1
# =========================
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="section-title">Distribuição de Risco</div>', unsafe_allow_html=True)

    risco = df['risco_geral'].value_counts().reset_index()
    risco.columns = ['Risco', 'Qtd']

    fig = px.bar(
        risco,
        x='Risco',
        y='Qtd',
        color='Risco',
        color_discrete_map={
            'Normal': '#00C9A7',
            'Alto': '#FFB547',
            'Crítico': '#FF4D6A'
        }
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown('<div class="section-title">IGRP por Setor</div>', unsafe_allow_html=True)

    setor_df = df.groupby(COL_SETOR)['IGRP'].mean().reset_index()

    fig = px.bar(
        setor_df.sort_values('IGRP').tail(10),
        x='IGRP',
        y=COL_SETOR,
        orientation='h',
        color='IGRP',
        color_continuous_scale='RdYlGn_r'
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# =========================
# DIMENSÕES
# =========================
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="section-title">Dimensões</div>', unsafe_allow_html=True)

    heatmap = df[[
        'score_Demandas',
        'score_Controle',
        'score_Apoio_Chefia',
        'score_Apoio_Colegas',
        'score_Relacionamentos',
        'score_Cargo',
        'score_Comunicacao'
    ]].mean().reset_index()

    heatmap.columns = ['Dimensão', 'Score']

    fig = px.bar(
        heatmap.sort_values('Score'),
        x='Score',
        y='Dimensão',
        orientation='h',
        color='Score',
        color_continuous_scale='RdYlGn'
    )

    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown('<div class="section-title">Principais Problemas</div>', unsafe_allow_html=True)

    problemas = heatmap.sort_values('Score').head(3)

    for _, row in problemas.iterrows():
        st.warning(f"{row['Dimensão']} → {round(row['Score'],2)}")

st.divider()

# =========================
# TABELAS
# =========================
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="section-title">Setores Críticos</div>', unsafe_allow_html=True)

    setor_risco = df.groupby(COL_SETOR).agg({
        'IGRP':'mean',
        'risco_geral': lambda x: (x.isin(['Alto','Crítico'])).mean()
    }).reset_index()

    setor_risco.columns = ['Setor','IGRP','% Risco']

    st.dataframe(setor_risco.sort_values('IGRP', ascending=False).head(10), use_container_width=True)

with col2:
    st.markdown('<div class="section-title">Cargos Críticos</div>', unsafe_allow_html=True)

    cargo_risco = df.groupby(COL_CARGO).agg({
        'IGRP':'mean',
        'risco_geral': lambda x: (x.isin(['Alto','Crítico'])).mean()
    }).reset_index()

    cargo_risco.columns = ['Cargo','IGRP','% Risco']

    st.dataframe(cargo_risco.sort_values('IGRP', ascending=False).head(10), use_container_width=True)

st.divider()

# =========================
# BASE
# =========================
with st.expander("Base completa"):
    st.dataframe(df, use_container_width=True)
