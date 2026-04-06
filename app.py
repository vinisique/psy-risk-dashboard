import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuração da página
st.set_page_config(page_title="Dashboard Vivamente 360 - NR 1", layout="wide")

# Estilo CSS customizado para aspecto profissional
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .metric-card { background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# -------------------------
# CARREGAMENTO DE DADOS
# -------------------------
@st.cache_data
def load_data():
    try:
        base = pd.read_parquet("base.parquet")
        setor = pd.read_parquet("setor.parquet")
        cargo = pd.read_parquet("cargo.parquet")
        # Tentativa de carregar unidade (Etapa 6b do notebook)
        try:
            unidade = pd.read_parquet("unidade.parquet")
        except:
            unidade = base.groupby("Informe sua unidade").size().reset_index(name="Total")
            
        return base, setor, cargo, unidade
    except Exception as e:
        st.error(f"Erro ao carregar arquivos parquet: {e}")
        return None, None, None, None

df_base, df_setor, df_cargo, df_unidade = load_data()

# -------------------------
# SIDEBAR - FILTROS
# -------------------------
st.sidebar.title("Filtros do Dashboard")
if df_base is not None:
    empresa_selecionada = st.sidebar.multiselect("Empresa", df_base['Empresa'].unique())
    unidade_selecionada = st.sidebar.multiselect("Unidade", df_base['Informe sua unidade'].unique())
    setor_selecionado = st.sidebar.multiselect("Setor", df_base['Informe seu setor / departamento.'].unique())

    # Aplicação dos filtros no DF Base
    mask = pd.Series([True] * len(df_base))
    if empresa_selecionada: mask &= df_base['Empresa'].isin(empresa_selecionada)
    if unidade_selecionada: mask &= df_base['Informe sua unidade'].isin(unidade_selecionada)
    if setor_selecionado: mask &= df_base['Informe seu setor / departamento.'].isin(setor_selecionado)
    
    df_filtered = df_base[mask]
else:
    st.stop()

# -------------------------
# DASHBOARD PRINCIPAL
# -------------------------
st.title("📊 Monitoramento de Riscos Psicossociais (NR 1)")

aba1, aba2, aba3, aba4, aba5 = st.tabs([
    "Visão Geral & IGRP", 
    "Engajamento", 
    "Dimensões & Questões", 
    "Top 5 & Criticidade", 
    "Matriz de Risco & PGR"
])

# --- ABA 1: VISÃO GERAL (IGRP & RISCO ALTO) --- [cite: 11, 14]
with aba1:
    col1, col2 = st.columns(2)
    
    # Índice Geral (IGRP) 
    igrp_medio = df_filtered['IGRP'].mean()
    with col1:
        st.subheader("Índice Geral de Riscos (IGRP)")
        fig_igrp = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = igrp_medio,
            domain = {'x': [0, 1], 'y': [0, 1]},
            gauge = {
                'axis': {'range': [None, 4]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 1], 'color': "green"},
                    {'range': [1, 2], 'color': "yellow"},
                    {'range': [2, 3], 'color': "orange"},
                    {'range': [3, 4], 'color': "red"}]
            }
        ))
        st.plotly_chart(fig_igrp, use_container_width=True)

    # % Trabalhadores Risco Alto/Crítico [cite: 15]
    risco_alto_count = df_filtered[df_filtered['NR_geral'] >= 9].shape[0]
    perc_risco_alto = (risco_alto_count / len(df_filtered)) * 100
    with col2:
        st.subheader("% Trabalhadores em Risco Alto/Crítico")
        st.metric("Total Criticidade (Laranja + Vermelho)", f"{perc_risco_alto:.1f}%")
        fig_pizza_risco = px.pie(df_filtered, names='risco_geral', color='risco_geral',
                                 color_discrete_map={'Baixo':'green', 'Aceitável':'blue', 'Moderado':'yellow', 'Importante':'orange', 'Crítico':'red'})
        st.plotly_chart(fig_pizza_risco, use_container_width=True)

# --- ABA 2: ENGAJAMENTO (Slide 13) --- [cite: 9]
with aba2:
    st.subheader("Engajamento e Questionários Respondidos")
    # Entrada manual de Headcount solicitada [cite: 13]
    headcount_input = st.number_input("Insira o Headcount Total da Unidade/Empresa para cálculo:", min_value=1, value=len(df_filtered)+10)
    respondidos = len(df_filtered)
    taxa_adesao = (respondidos / headcount_input) * 100
    
    # Lógica de cor do slide 13 [cite: 9]
    cor_adesao = "red"
    if taxa_adesao >= 70: cor_adesao = "green"
    elif taxa_adesao >= 50: cor_adesao = "yellow"
    
    st.markdown(f"<h2 style='text-align: center; color: {cor_adesao};'>{taxa_adesao:.1f}% de Adesão</h2>", unsafe_allow_html=True)
    st.write(f"Respondidos: {respondidos} | Total Esperado: {headcount_input}")

# --- ABA 3: DIMENSÕES & QUESTÕES --- [cite: 17, 19]
with aba3:
    st.subheader("Indicadores por Dimensão (Média de Score)")
    dimensoes = ['score_Demandas', 'score_Controle', 'score_Apoio_Chefia', 'score_Apoio_Colegas', 'score_Relacionamentos', 'score_Cargo', 'score_Mudanca']
    df_dim = df_filtered[dimensoes].mean().reset_index()
    df_dim.columns = ['Dimensão', 'Média Score']
    
    fig_dim = px.bar(df_dim, x='Dimensão', y='Média Score', color='Média Score', color_continuous_scale='RdYlGn_r')
    st.plotly_chart(fig_dim, use_container_width=True)
    
    st.divider()
    st.subheader("Visão por Questão (Heatmap de Respostas)")
    # Seleção de questões específicas para o heatmap conforme Slide 18 [cite: 19]
    questoes_cols = [c for c in df_filtered.columns if 'As exigências' in c or 'Tenho prazos' in c or 'Posso decidir' in c]
    if questoes_cols:
        df_quest = df_filtered[questoes_cols].apply(pd.Series.value_counts).fillna(0).T
        fig_heat = px.imshow(df_quest, labels=dict(x="Frequência", y="Questão"), text_auto=True, color_continuous_scale='Viridis')
        st.plotly_chart(fig_heat, use_container_width=True)

# --- ABA 4: TOP 5 & CRITICIDADE --- [cite: 21, 22]
with aba4:
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("Top 5 Setores com Maior NR Médio")
        top_setor = df_filtered.groupby("Informe seu setor / departamento.")["NR_geral"].mean().sort_values(ascending=False).head(5)
        fig_top_setor = px.bar(top_setor, orientation='h', color=top_setor.values, color_continuous_scale='Reds')
        st.plotly_chart(fig_top_setor, use_container_width=True)
        
    with col_b:
        st.subheader("Top 5 Cargos em Risco Crítico")
        top_cargo = df_filtered.groupby("Informe seu cargo")["NR_geral"].mean().sort_values(ascending=False).head(5)
        fig_top_cargo = px.bar(top_cargo, orientation='h', color=top_cargo.values, color_continuous_scale='Oranges')
        st.plotly_chart(fig_top_cargo, use_container_width=True)

# --- ABA 5: MATRIZ DE RISCO & PGR --- [cite: 23]
with aba5:
    st.subheader("Matriz de Risco (Severidade x Probabilidade)")
    # Simulação de Matriz NR = P x S conforme Slide 8 [cite: 8]
    fig_matrix = px.scatter(df_filtered, x='IGRP', y='qtd_dimensoes_alto', 
                            size='NR_geral', color='risco_geral',
                            hover_name='Informe seu cargo',
                            title="Distribuição de Risco por Funcionário")
    st.plotly_chart(fig_matrix, use_container_width=True)
    
    st.divider()
    st.subheader("Plano de Gerenciamento de Riscos (PGR)")
    st.dataframe(df_filtered[['Empresa', 'Informe sua unidade', 'Informe seu setor / departamento.', 'Informe seu cargo', 'NR_geral', 'risco_geral']].sort_values(by='NR_geral', ascending=False))
