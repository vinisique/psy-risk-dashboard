import streamlit as st
import pandas as pd

# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="Dashboard Psicossocial",
    layout="wide",
    page_icon="📊"
)

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    df_base = pd.read_parquet("base.parquet")
    df_setor = pd.read_parquet("setor.parquet")
    df_cargo = pd.read_parquet("cargo.parquet")
    return df_base, df_setor, df_cargo

df_base, df_setor, df_cargo = load_data()

# =========================
# SIDEBAR (FILTROS)
# =========================
st.sidebar.header("Filtros")

empresa = st.sidebar.multiselect(
    "Empresa",
    options=df_base['Empresa'].unique(),
    default=df_base['Empresa'].unique()
)

unidade = st.sidebar.multiselect(
    "Unidade",
    options=df_base['Informe sua unidade'].unique(),
    default=df_base['Informe sua unidade'].unique()
)

setor = st.sidebar.multiselect(
    "Setor",
    options=df_base['Informe seu setor / departamento.'].unique(),
    default=df_base['Informe seu setor / departamento.'].unique()
)

# =========================
# FILTRO BASE
# =========================
df_filtered = df_base[
    (df_base['Empresa'].isin(empresa)) &
    (df_base['Informe sua unidade'].isin(unidade)) &
    (df_base['Informe seu setor / departamento.'].isin(setor))
]

# =========================
# KPIs
# =========================
st.title("📊 Dashboard Psicossocial")

col1, col2, col3 = st.columns(3)

col1.metric("Total Colaboradores", len(df_filtered))
col2.metric("IGRP Médio", round(df_filtered['IGRP'].mean(), 2))
col3.metric(
    "% Risco Alto/Crítico",
    f"{round((df_filtered['risco_geral'].isin(['Alto','Crítico']).mean())*100,1)}%"
)

# =========================
# DISTRIBUIÇÃO DE RISCO
# =========================
st.subheader("Distribuição de Risco")

risco_dist = df_filtered['risco_geral'].value_counts(normalize=True)

st.bar_chart(risco_dist)

# =========================
# TOP SETORES CRÍTICOS
# =========================
st.subheader("🔥 Setores Críticos")

df_setor_filtered = (
    df_filtered
    .groupby('Informe seu setor / departamento.')
    .agg({
        'IGRP': 'mean',
        'risco_geral': lambda x: (x.isin(['Alto','Crítico'])).mean()
    })
    .reset_index()
    .rename(columns={'risco_geral': 'perc_risco'})
)

df_setor_filtered = df_setor_filtered.sort_values('IGRP', ascending=False)

st.dataframe(df_setor_filtered.head(10), use_container_width=True)

# =========================
# TOP CARGOS CRÍTICOS
# =========================
st.subheader("🔥 Cargos Críticos")

df_cargo_filtered = (
    df_filtered
    .groupby('Informe seu cargo')
    .agg({
        'IGRP': 'mean',
        'risco_geral': lambda x: (x.isin(['Alto','Crítico'])).mean()
    })
    .reset_index()
    .rename(columns={'risco_geral': 'perc_risco'})
)

df_cargo_filtered = df_cargo_filtered.sort_values('IGRP', ascending=False)

st.dataframe(df_cargo_filtered.head(10), use_container_width=True)

# =========================
# HEATMAP (SCORES)
# =========================
st.subheader("📌 Heatmap de Dimensões")

heatmap = df_filtered[[
    'score_Demandas',
    'score_Controle',
    'score_Apoio_Chefia',
    'score_Apoio_Colegas',
    'score_Relacionamentos',
    'score_Cargo',
    'score_Comunicacao'
]].mean().to_frame(name="Score")

st.dataframe(heatmap)

# =========================
# TABELA DETALHADA
# =========================
st.subheader("📋 Base Detalhada")

st.dataframe(df_filtered, use_container_width=True)
