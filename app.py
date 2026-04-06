import streamlit as st
import pandas as pd
import plotly.express as px

# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="OrgPulse Dashboard",
    layout="wide",
)

st.title("OrgPulse - Psychosocial Risk Dashboard")
st.caption("Análise de riscos psicossociais baseada no modelo HSE")

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    df_base = pd.read_parquet("base.parquet")
    return df_base

df_base = load_data()

# =========================
# SIDEBAR
# =========================
st.sidebar.header("Filtros")

empresa = st.sidebar.multiselect(
    "Empresa",
    df_base['Empresa'].unique(),
    default=df_base['Empresa'].unique()
)

unidade = st.sidebar.multiselect(
    "Unidade",
    df_base['Informe sua unidade'].unique(),
    default=df_base['Informe sua unidade'].unique()
)

setor = st.sidebar.multiselect(
    "Setor",
    df_base['Informe seu setor / departamento.'].unique(),
    default=df_base['Informe seu setor / departamento.'].unique()
)

df = df_base[
    (df_base['Empresa'].isin(empresa)) &
    (df_base['Informe sua unidade'].isin(unidade)) &
    (df_base['Informe seu setor / departamento.'].isin(setor))
]

# =========================
# KPIs (LINHA HORIZONTAL)
# =========================
col1, col2, col3, col4 = st.columns(4)

col1.metric("Colaboradores", len(df))
col2.metric("IGRP Médio", round(df['IGRP'].mean(), 2))
col3.metric(
    "% Alto/Crítico",
    f"{round((df['risco_geral'].isin(['Alto','Crítico']).mean())*100,1)}%"
)
col4.metric(
    "% Crítico",
    f"{round((df['risco_geral'] == 'Crítico').mean()*100,1)}%"
)

st.divider()

# =========================
# LINHA 2 - VISÃO GERAL
# =========================
col1, col2 = st.columns(2)

with col1:
    st.subheader("Distribuição de Risco")

    risco = df['risco_geral'].value_counts().reset_index()
    risco.columns = ['Risco', 'Qtd']

    fig = px.bar(
        risco,
        x='Risco',
        y='Qtd',
        color='Risco',
        color_discrete_map={
            'Normal': 'green',
            'Alto': 'orange',
            'Crítico': 'red'
        }
    )

    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("IGRP por Setor")

    setor_df = (
        df.groupby('Informe seu setor / departamento.')
        .agg({'IGRP': 'mean'})
        .reset_index()
        .sort_values('IGRP', ascending=False)
    )

    fig = px.bar(
        setor_df.head(10),
        x='IGRP',
        y='Informe seu setor / departamento.',
        orientation='h',
        color='IGRP',
        color_continuous_scale='RdYlGn_r'
    )

    st.plotly_chart(fig, use_container_width=True)

st.divider()

# =========================
# LINHA 3 - DIAGNÓSTICO
# =========================
col1, col2 = st.columns(2)

with col1:
    st.subheader("Heatmap de Dimensões")

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
        heatmap,
        x='Score',
        y='Dimensão',
        orientation='h',
        color='Score',
        color_continuous_scale='RdYlGn'
    )

    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Principais Problemas")

    problemas = heatmap.sort_values('Score').head(3)

    for _, row in problemas.iterrows():
        st.error(f"{row['Dimensão']} - Score: {round(row['Score'],2)}")

st.divider()

# =========================
# LINHA 4 - DETALHAMENTO
# =========================
col1, col2 = st.columns(2)

with col1:
    st.subheader("Setores Críticos")

    setor_risco = (
        df.groupby('Informe seu setor / departamento.')
        .agg({
            'IGRP': 'mean',
            'risco_geral': lambda x: (x.isin(['Alto','Crítico'])).mean()
        })
        .reset_index()
    )

    setor_risco.columns = ['Setor', 'IGRP', '% Risco']

    st.dataframe(
        setor_risco.sort_values('IGRP', ascending=False).head(10),
        use_container_width=True
    )

with col2:
    st.subheader("Cargos Críticos")

    cargo_risco = (
        df.groupby('Informe seu cargo')
        .agg({
            'IGRP': 'mean',
            'risco_geral': lambda x: (x.isin(['Alto','Crítico'])).mean()
        })
        .reset_index()
    )

    cargo_risco.columns = ['Cargo', 'IGRP', '% Risco']

    st.dataframe(
        cargo_risco.sort_values('IGRP', ascending=False).head(10),
        use_container_width=True
    )

st.divider()

# =========================
# BASE DETALHADA
# =========================
st.subheader("Base Detalhada")
st.dataframe(df, use_container_width=True)
