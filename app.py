import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# Configuração da Página
st.set_page_config(page_title="Dashboard HSE-IT - Plataforma Vivamente", layout="wide")

@st.cache_data
def load_data():
    df = pd.read_parquet("base.parquet")
    # Identificar colunas de perguntas (ajuste o prefixo se necessário)
    col_perguntas = [c for c in df.columns if '?' in c or c.startswith('Questão')] 
    return df, col_perguntas

df, col_perguntas = load_data()

# --- SIDEBAR FILTERS ---
st.sidebar.header("Filtros Analíticos")
unidade = st.sidebar.multiselect("Unidade", options=df['Informe sua unidade'].unique())
setor = st.sidebar.multiselect("Setor", options=df['Informe seu setor / departamento.'].unique())
cargo = st.sidebar.multiselect("Cargo", options=df['Informe seu cargo'].unique())

# Aplicar Filtros
df_filtered = df.copy()
if unidade: df_filtered = df_filtered[df_filtered['Informe sua unidade'].isin(unidade)]
if setor: df_filtered = df_filtered[df_filtered['Informe seu setor / departamento.'].isin(setor)]
if cargo: df_filtered = df_filtered[df_filtered['Informe seu cargo'].isin(cargo)]

# --- HEADER ---
st.title("📊 Dashboard NR 1 - Plataforma Vivamente 360º")
st.markdown("---")

# --- LINHA 1: ADESÃO E RISCO GERAL ---
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    # Slide 14: Adesão (Assumindo um total hipotético de 1200 funcionários para o Gauge)
    total_colaboradores = 1200 
    adesao = (len(df_filtered) / total_colaboradores) * 100
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = adesao,
        title = {'text': "Adesão (%)"},
        gauge = {'axis': {'range': [0, 100]},
                 'bar': {'color': "darkblue"},
                 'steps': [
                     {'range': [0, 50], 'color': "red"},
                     {'range': [50, 70], 'color': "yellow"},
                     {'range': [70, 100], 'color': "green"}]}
    ))
    st.plotly_chart(fig_gauge, use_container_width=True)

with col2:
    # Slide 16: Risco Organizacional (Rosca)
    risco_counts = df_filtered['risco_geral'].value_counts().reset_index()
    fig_pie = px.pie(risco_counts, values='count', names='risco_geral', hole=0.5,
                     title="Distribuição de Risco",
                     color='risco_geral',
                     color_discrete_map={'Crítico':'#ff0000', 'Importante':'#ffa500', 'Moderado':'#ffff00', 'Aceitável':'#008000'})
    st.plotly_chart(fig_pie, use_container_width=True)

with col3:
    # Slide 15: IGRP por Setor
    igrp_setor = df_filtered.groupby('Informe seu setor / departamento.')['IGRP'].mean().sort_values().reset_index()
    fig_igrp = px.bar(igrp_setor, x='IGRP', y='Informe seu setor / departamento.', orientation='h',
                      title="IGRP Médio por Setor", color='IGRP', color_continuous_scale='RdYlGn_r')
    st.plotly_chart(fig_igrp, use_container_width=True)

st.markdown("---")

# --- LINHA 2: DIMENSÕES E QUESTÕES (O MOTIVO DO ERRO ANTERIOR) ---
col4, col5 = st.columns(2)

with col4:
    # Slide 18: Indicadores por Dimensão (Empilhado 100%)
    # Precisamos derreter (melt) as colunas de perguntas para o formato longo
    df_questions = df_filtered[col_perguntas].melt(var_name='Questão', value_name='Resposta')
    # Aqui você precisaria de um mapeamento Dimensão -> Pergunta para agrupar
    # Simplificado: Frequência geral de Likert
    fig_dim = px.histogram(df_questions, x='Resposta', color='Resposta', barmode='group',
                           title="Distribuição Likert Geral (0-4)",
                           category_orders={"Resposta": [0, 1, 2, 3, 4]})
    st.plotly_chart(fig_dim, use_container_width=True)

with col5:
    # Slide 20: Score de Clima (Radar)
    avg_scores = df_filtered[[c for c in df_filtered.columns if 'score_' in c]].mean()
    fig_radar = go.Figure(data=go.Scatterpolar(
      r=avg_scores.values,
      theta=[c.replace('score_', '') for c in avg_scores.index],
      fill='toself'
    ))
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 4])), showlegend=False, title="Radar de Clima Psicossocial")
    st.plotly_chart(fig_radar, use_container_width=True)

st.markdown("---")

# --- LINHA 3: MATRIZES E TABELAS ---
st.subheader("Análise Detalhada (Matriz PGR e Cargos)")

# Slide 23: Tabela de Análise por Cargo
df_cargo_table = df_filtered.groupby('Informe seu cargo').agg({
    'IGRP': 'mean',
    'NR_geral': 'mean',
    'ID': 'count'
}).rename(columns={'ID': 'Qtd Respondentes'}).reset_index()

st.dataframe(df_cargo_table.style.background_gradient(cmap='RdYlGn_r', subset=['IGRP']), use_container_width=True)

# Slide 22: Heatmap Dimensões vs Setor
scores_cols = [c for c in df_filtered.columns if 'score_' in c]
heatmap_data = df_filtered.groupby('Informe seu setor / departamento.')[scores_cols].mean()
fig_heat = px.imshow(heatmap_data, labels=dict(color="Score"),
                x=[c.replace('score_', '') for c in scores_cols],
                y=heatmap_data.index,
                title="Heatmap: Dimensões por Setor (Médias)",
                color_continuous_scale='RdYlGn_r')
st.plotly_chart(fig_heat, use_container_width=True)
