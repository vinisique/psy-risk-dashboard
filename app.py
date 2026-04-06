import streamlit as st
import pandas as pd
import plotly.express as px

# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="OrgPulse Dashboard",
    layout="wide"
)

# =========================
# DESIGN (SAFE CSS)
# =========================
st.markdown("""
<style>
    html, body {
        background-color: #0E1117;
        color: #E6E6E6;
        font-family: 'Segoe UI', sans-serif;
    }

    /* KPI Cards */
    .kpi-card {
        background: #161A23;
        padding: 1.2rem;
        border-radius: 10px;
        border: 1px solid #262B36;
    }

    .kpi-title {
        font-size: 0.8rem;
        color: #8A90A2;
    }

    .kpi-value {
        font-size: 1.8rem;
        font-weight: 600;
        color: #FFFFFF;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #161A23;
    }

    /* Titles */
    h1, h2, h3 {
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

st.title("OrgPulse — Psychosocial Risk Intelligence")
st.caption("Análise de riscos psicossociais baseada no modelo HSE")

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
# KPIs
# =========================
col1, col2, col3, col4 = st.columns(4)

def kpi(title, value):
    return f"""
    <div class="kpi-card">
        <div class="kpi-title">{title}</div>
        <div class="kpi-value">{value}</div>
    </div>
    """

col1.markdown(kpi("Colaboradores", len(df)), unsafe_allow_html=True)
col2.markdown(kpi("IGRP Médio", round(df['IGRP'].mean(), 2)), unsafe_allow_html=True)
col3.markdown(kpi(
    "% Alto/Crítico",
    f"{round((df['risco_geral'].isin(['Alto','Crítico']).mean())*100,1)}%"
), unsafe_allow_html=True)
col4.markdown(kpi(
    "% Crítico",
    f"{round((df['risco_geral'] == 'Crítico').mean()*100,1)}%"
), unsafe_allow_html=True)

st.divider()

# =========================
# GRÁFICO PADRÃO (FUNÇÃO)
# =========================
def style_fig(fig):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#AAB0C0"),
        margin=dict(l=0, r=0, t=20, b=0)
    )
    return fig

# =========================
# LINHA 2
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
            'Normal': '#00C9A7',
            'Alto': '#FFB547',
            'Crítico': '#FF4D6A'
        }
    )

    st.plotly_chart(style_fig(fig), use_container_width=True)

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
        color_continuous_scale=['#00C9A7', '#FFB547', '#FF4D6A']
    )

    st.plotly_chart(style_fig(fig), use_container_width=True)

st.divider()

# =========================
# LINHA 3
# =========================
col1, col2 = st.columns(2)

with col1:
    st.subheader("Score por Dimensão")

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
        color_continuous_scale=['#00C9A7', '#FFB547', '#FF4D6A']
    )

    st.plotly_chart(style_fig(fig), use_container_width=True)

with col2:
    st.subheader("Principais Problemas")

    problemas = heatmap.sort_values('Score').head(3)

    for _, row in problemas.iterrows():
        st.markdown(
            f"<div style='padding:10px;border-left:3px solid #FF4D6A;'>"
            f"{row['Dimensão']} — {round(row['Score'],2)}</div>",
            unsafe_allow_html=True
        )

st.divider()

# =========================
# LINHA 4
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

    st.dataframe(setor_risco.sort_values('IGRP', ascending=False).head(10), use_container_width=True)

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

    st.dataframe(cargo_risco.sort_values('IGRP', ascending=False).head(10), use_container_width=True)

st.divider()

# =========================
# BASE
# =========================
st.subheader("Base Detalhada")
st.dataframe(df, use_container_width=True)
