import streamlit as st
import pandas as pd
import plotly.express as px

# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="Psychosocial Risk Analytics",
    layout="wide"
)

# =========================
# THEME (SaaS)
# =========================
st.markdown("""
    <style>
        body {
            background-color: #0e1117;
            color: #e6e6e6;
        }
        .stMetric {
            background-color: #1c1f26;
            padding: 15px;
            border-radius: 10px;
        }
    </style>
""", unsafe_allow_html=True)

st.title("Psychosocial Risk Analytics")
st.caption("Organizational risk intelligence platform")

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    return pd.read_parquet("base.parquet")

df_base = load_data()

# =========================
# SIDEBAR
# =========================
st.sidebar.header("Filters")

empresa = st.sidebar.multiselect(
    "Company",
    df_base['Empresa'].unique(),
    default=df_base['Empresa'].unique()
)

unidade = st.sidebar.multiselect(
    "Unit",
    df_base['Informe sua unidade'].unique(),
    default=df_base['Informe sua unidade'].unique()
)

setor = st.sidebar.multiselect(
    "Department",
    df_base['Informe seu setor / departamento.'].unique(),
    default=df_base['Informe seu setor / departamento.'].unique()
)

df = df_base[
    (df_base['Empresa'].isin(empresa)) &
    (df_base['Informe sua unidade'].isin(unidade)) &
    (df_base['Informe seu setor / departamento.'].isin(setor))
]

# =========================
# KPIs
# =========================
col1, col2, col3, col4 = st.columns(4)

col1.metric("Employees", len(df))
col2.metric("Average IGRP", round(df['IGRP'].mean(), 2))
col3.metric(
    "High Risk %",
    f"{round((df['risco_geral'].isin(['Alto','Crítico']).mean())*100,1)}%"
)
col4.metric(
    "Critical %",
    f"{round((df['risco_geral'] == 'Crítico').mean()*100,1)}%"
)

st.divider()

# =========================
# BENCHMARK
# =========================
st.subheader("Benchmark by Company")

benchmark = (
    df_base.groupby('Empresa')['IGRP']
    .mean()
    .reset_index()
    .sort_values('IGRP', ascending=False)
)

fig = px.bar(
    benchmark,
    x='IGRP',
    y='Empresa',
    orientation='h',
    color='IGRP',
    color_continuous_scale='RdYlGn_r'
)

st.plotly_chart(fig, use_container_width=True)

st.divider()

# =========================
# DISTRIBUTION
# =========================
col1, col2 = st.columns(2)

with col1:
    st.subheader("Risk Distribution")

    risco = df['risco_geral'].value_counts().reset_index()
    risco.columns = ['Risk', 'Count']

    fig = px.bar(
        risco,
        x='Risk',
        y='Count',
        color='Risk',
        color_discrete_map={
            'Normal': '#2ca02c',
            'Alto': '#ff7f0e',
            'Crítico': '#d62728'
        }
    )

    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("IGRP by Department")

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
# INSIGHTS AUTOMÁTICOS
# =========================
st.subheader("Automated Insights")

insights = []

# Insight 1
perc_critico = (df['risco_geral'] == 'Crítico').mean()

if perc_critico > 0.15:
    insights.append("High concentration of critical risk detected.")
elif perc_critico > 0.05:
    insights.append("Moderate presence of critical risk groups.")

# Insight 2
pior_dim = df[[
    'score_Demandas',
    'score_Controle',
    'score_Apoio_Chefia',
    'score_Apoio_Colegas',
    'score_Relacionamentos',
    'score_Cargo',
    'score_Comunicacao'
]].mean().idxmin()

insights.append(f"Primary risk driver: {pior_dim.replace('score_', '')}")

# Insight 3
top_setor = setor_df.iloc[0]['Informe seu setor / departamento.']
insights.append(f"Highest risk department: {top_setor}")

# Render insights
for i in insights:
    st.write(f"- {i}")

st.divider()

# =========================
# HEATMAP
# =========================
st.subheader("Dimension Analysis")

heatmap = df[[
    'score_Demandas',
    'score_Controle',
    'score_Apoio_Chefia',
    'score_Apoio_Colegas',
    'score_Relacionamentos',
    'score_Cargo',
    'score_Comunicacao'
]].mean().reset_index()

heatmap.columns = ['Dimension', 'Score']

fig = px.bar(
    heatmap,
    x='Score',
    y='Dimension',
    orientation='h',
    color='Score',
    color_continuous_scale='RdYlGn'
)

st.plotly_chart(fig, use_container_width=True)

st.divider()

# =========================
# DATA TABLE
# =========================
st.subheader("Detailed Data")
st.dataframe(df, use_container_width=True)
