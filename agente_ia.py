"""
🧠 Agente de IA — HSE-IT · Vivamente 360°
Analisa os dados de riscos psicossociais e gera insights acionáveis.
Tecnologia: Anthropic API (claude-sonnet-4-20250514) + Streamlit
"""

import streamlit as st
import pandas as pd
import json
import os
import re
import requests
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIG DA PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Agente IA · HSE-IT",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# PALETA (mantida igual ao dashboard principal)
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
COR_PURPLE   = "#A78BFA"

DIMENSOES = [
    "Demandas", "Controle", "Apoio_Chefia",
    "Apoio_Colegas", "Relacionamentos", "Cargo", "Mudanca"
]
DIMENSOES_LABEL = {
    "Demandas": "Demandas",
    "Controle": "Controle",
    "Apoio_Chefia": "Apoio da Chefia",
    "Apoio_Colegas": "Apoio dos Colegas",
    "Relacionamentos": "Relacionamentos",
    "Cargo": "Cargo / Função",
    "Mudanca": "Comunicação e Mudanças",
}

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
}}
[data-testid="stSidebar"] * {{ color: {COR_TEXTO} !important; }}

.block-container {{ padding: 1.5rem 2rem 3rem; }}

/* Chat bubbles */
.msg-user {{
    background: linear-gradient(135deg, #1e3a5f, #1a2d4a);
    border: 1px solid {COR_ACCENT}33;
    border-radius: 16px 16px 4px 16px;
    padding: 14px 18px;
    margin: 8px 0 8px 15%;
    color: {COR_TEXTO};
    font-size: 14px;
    line-height: 1.6;
}}
.msg-agent {{
    background: {COR_CARD};
    border: 1px solid {COR_BORDA};
    border-radius: 4px 16px 16px 16px;
    padding: 16px 20px;
    margin: 8px 15% 8px 0;
    color: {COR_TEXTO};
    font-size: 14px;
    line-height: 1.7;
}}
.msg-agent strong {{ color: {COR_ACCENT}; }}
.msg-agent em {{ color: {COR_MUTED}; }}

/* Insight cards */
.insight-card {{
    background: {COR_CARD};
    border-left: 3px solid {COR_ACCENT};
    border-radius: 0 12px 12px 0;
    padding: 12px 16px;
    margin: 6px 0;
    font-size: 13px;
}}
.insight-critico {{ border-left-color: {COR_VERMELHO}; }}
.insight-alerta  {{ border-left-color: {COR_AMARELO}; }}
.insight-ok      {{ border-left-color: {COR_VERDE}; }}

.chip {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 100px;
    font-size: 11px;
    font-weight: 600;
    margin: 2px;
}}
.chip-critico  {{ background: rgba(214,59,59,0.2);  color: {COR_VERMELHO}; }}
.chip-moderado {{ background: rgba(245,166,35,0.2); color: {COR_AMARELO}; }}
.chip-ok       {{ background: rgba(45,158,117,0.2); color: {COR_VERDE}; }}

.section-title {{
    font-size: 12px; font-weight: 600; color: {COR_MUTED};
    text-transform: uppercase; letter-spacing: .1em;
    margin: 1.5rem 0 .8rem;
    padding-bottom: 6px;
    border-bottom: 1px solid {COR_BORDA};
}}

.thinking-badge {{
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(79,142,247,0.1);
    border: 1px solid {COR_ACCENT}44;
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 12px;
    color: {COR_ACCENT};
    margin: 8px 0;
}}

.quick-btn {{
    background: {COR_CARD};
    border: 1px solid {COR_BORDA};
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 12px;
    color: {COR_TEXTO};
    cursor: pointer;
    transition: all 0.2s;
    width: 100%;
    text-align: left;
    margin: 3px 0;
}}
.quick-btn:hover {{ border-color: {COR_ACCENT}; color: {COR_ACCENT}; }}

.agent-header {{
    background: linear-gradient(135deg, #1A1D27 0%, #0F1117 100%);
    border: 1px solid {COR_BORDA};
    border-radius: 16px;
    padding: 24px 28px;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 16px;
}}
.agent-avatar {{
    width: 52px; height: 52px;
    background: linear-gradient(135deg, {COR_ACCENT}, {COR_PURPLE});
    border-radius: 14px;
    display: flex; align-items: center; justify-content: center;
    font-size: 24px; flex-shrink: 0;
}}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CARGA DE DADOS
# ─────────────────────────────────────────────
@st.cache_data
def load_all_data():
    base     = pd.read_parquet("base.parquet")
    setor    = pd.read_parquet("setor.parquet")
    cargo    = pd.read_parquet("cargo.parquet")
    unidade  = pd.read_parquet("unidade.parquet") if os.path.exists("unidade.parquet") else None
    return base, setor, cargo, unidade

base, setor, cargo, unidade = load_all_data()

# ─────────────────────────────────────────────
# MONTAGEM DO CONTEXTO ANALÍTICO
# ─────────────────────────────────────────────
def build_context(filtro_empresa=None, filtro_setor=None, filtro_cargo=None):
    """Gera um resumo estruturado dos dados para alimentar o agente."""
    
    base_f = base.copy()
    if filtro_empresa:
        base_f = base_f[base_f["Empresa"].isin(filtro_empresa)]
    if filtro_setor:
        base_f = base_f[base_f["Informe seu setor / departamento."].isin(filtro_setor)]
    if filtro_cargo:
        base_f = base_f[base_f["Informe seu cargo"].isin(filtro_cargo)]

    n = len(base_f)
    if n == 0:
        return "Nenhum respondente encontrado com os filtros selecionados.", {}

    dist_risco = base_f["risco_geral"].value_counts().to_dict()
    nr_medio   = base_f["NR_geral"].mean()
    igrp_medio = base_f["IGRP"].mean()

    # Scores por dimensão
    scores_dim = {}
    for d in DIMENSOES:
        col = f"score_{d}"
        if col in base_f.columns:
            scores_dim[DIMENSOES_LABEL[d]] = round(float(base_f[col].mean()), 3)

    # Top setores críticos
    setor_f = base_f.groupby("Informe seu setor / departamento.").agg(
        n=("NR_geral", "count"),
        nr_medio=("NR_geral", "mean"),
        perc_critico=("risco_geral", lambda x: (x == "Crítico").mean()),
        perc_alto=("risco_geral", lambda x: x.isin(["Crítico","Importante"]).mean()),
    ).reset_index().rename(columns={"Informe seu setor / departamento.": "setor"})
    setor_f = setor_f.sort_values("nr_medio", ascending=False)
    top_setores = setor_f.head(5)[["setor","n","nr_medio","perc_alto"]].to_dict("records")

    # Top cargos
    cargo_f = base_f.groupby("Informe seu cargo").agg(
        n=("NR_geral", "count"),
        nr_medio=("NR_geral", "mean"),
        perc_alto=("risco_geral", lambda x: x.isin(["Crítico","Importante"]).mean()),
    ).reset_index().rename(columns={"Informe seu cargo": "cargo"})
    cargo_f = cargo_f.sort_values("nr_medio", ascending=False)
    top_cargos = cargo_f.head(5)[["cargo","n","nr_medio","perc_alto"]].to_dict("records")

    # Empresas
    emp_f = base_f.groupby("Empresa").agg(
        n=("NR_geral","count"),
        nr_medio=("NR_geral","mean"),
        perc_alto=("risco_geral", lambda x: x.isin(["Crítico","Importante"]).mean()),
    ).reset_index()

    # Questões mais críticas
    questoes_raw = [c for c in base_f.columns if not any([
        c in ["Empresa","Informe sua unidade","Informe seu setor / departamento.","Informe seu cargo",
              "IGRP","NR_geral","risco_geral","qtd_dimensoes_alto"],
        c.startswith("score_"), c.startswith("NR_"), c.startswith("class_"),
        c.startswith("P_"), c.startswith("S_")
    ])]
    
    questoes_criticas = []
    for q in questoes_raw[:35]:
        media = base_f[q].mean()
        questoes_criticas.append({"questao": q[:80], "score": round(float(media), 2)})
    questoes_criticas.sort(key=lambda x: x["score"], reverse=True)

    stats = {
        "n_respondentes": n,
        "nr_medio": round(float(nr_medio), 2),
        "igrp_medio": round(float(igrp_medio), 3),
        "distribuicao_risco": dist_risco,
        "scores_por_dimensao": scores_dim,
        "top_setores_criticos": top_setores,
        "top_cargos_criticos": top_cargos,
        "empresas": emp_f.to_dict("records"),
        "questoes_mais_criticas": questoes_criticas[:10],
    }

    perc_alto = (dist_risco.get("Crítico",0) + dist_risco.get("Importante",0)) / n * 100
    perc_critico = dist_risco.get("Crítico",0) / n * 100

    contexto = f"""
# CONTEXTO — DASHBOARD HSE-IT (Riscos Psicossociais / NR-1)
## Visão Geral da Amostra
- Respondentes no filtro: {n}
- NR Geral médio: {nr_medio:.2f} (escala 1–16; ≥13 = Crítico)
- IGRP médio: {igrp_medio:.3f} (escala 0–4)
- Em risco Alto/Crítico: {perc_alto:.1f}%
- Em risco Crítico: {perc_critico:.1f}%

## Distribuição por Nível de Risco
{json.dumps(dist_risco, ensure_ascii=False, indent=2)}

## Scores Médios por Dimensão (0–4)
Dimensões NEGATIVAS (maior score = pior): Demandas, Relacionamentos
Dimensões POSITIVAS (menor score = pior): Controle, Apoio Chefia, Apoio Colegas, Cargo, Comunicação
{json.dumps(scores_dim, ensure_ascii=False, indent=2)}

## Top 5 Setores com Maior NR (mais críticos)
{json.dumps(top_setores, ensure_ascii=False, indent=2)}

## Top 5 Cargos com Maior NR (mais críticos)
{json.dumps(top_cargos, ensure_ascii=False, indent=2)}

## Empresas
{json.dumps(emp_f.to_dict("records"), ensure_ascii=False, indent=2)}

## 10 Questões com Score Mais Preocupante
(Demandas: score alto = ruim | Outras: score baixo = ruim)
{json.dumps(questoes_criticas[:10], ensure_ascii=False, indent=2)}

---
Escalas de Referência:
- NR Geral: Aceitável (≤4) | Moderado (5–8) | Importante (9–12) | Crítico (≥13)
- Score Dimensão 0–4: varia se positivo ou negativo
""".strip()

    return contexto, stats


SYSTEM_PROMPT = """Você é um especialista sênior em Saúde Mental Ocupacional, Psicologia Organizacional e Gestão de Riscos Psicossociais (NR-1 brasileira). Você analisa dados do instrumento HSE-IT (Health & Safety Executive Indicator Tool adaptado).

Seu papel é interpretar dados quantitativos de riscos psicossociais e transformá-los em insights humanos, estratégicos e acionáveis — não apenas descrever números.

Você SEMPRE:
- Contextualiza o que cada número significa na prática (impacto humano e organizacional)
- Identifica padrões, correlações e situações que merecem atenção imediata
- Sugere ações concretas, priorizadas e realistas para gestores de RH e HSE
- Usa linguagem clara, direta e empática
- Cita os dados específicos ao fazer afirmações
- Estrutura bem as respostas com seções quando pertinente
- Faz perguntas reflexivas quando útil para aprofundar a análise

Você NUNCA:
- Inventa dados não presentes no contexto
- Usa jargões desnecessários sem explicação
- Dá respostas genéricas sem ancoragem nos dados reais
- Ignora o aspecto humano — por trás de cada número há pessoas

Você pode responder em português brasileiro. Quando listar ações, seja específico: quem faz, o quê, quando.
"""


def call_anthropic(messages: list, api_key: str) -> str:
    """Chama a API da Anthropic com streaming simulado."""
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": "claude-opus-4-5",
        "max_tokens": 2048,
        "system": SYSTEM_PROMPT,
        "messages": messages,
    }
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json=payload,
        timeout=60,
    )
    if resp.status_code != 200:
        error_detail = resp.json().get("error", {}).get("message", resp.text)
        raise Exception(f"Erro API ({resp.status_code}): {error_detail}")
    
    data = resp.json()
    return data["content"][0]["text"]


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
        <div style="text-align:center; padding: 25px 0 15px 0; border-bottom: 1px solid #2A2D3E;">
            <h2 style="margin:0; font-size:22px; color:#4F8EF7;">🤖 Agente HSE-IT</h2>
            <p style="margin:4px 0 0 0; font-size:12px; color:#8B8FA8;">
                IA · Vivamente 360° · NR-1
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    
    # API Key
    st.markdown("### 🔑 API Key")
    api_key = st.text_input(
        "Chave Anthropic",
        type="password",
        placeholder="sk-ant-...",
        help="Crie uma chave gratuita em console.anthropic.com — novos usuários recebem créditos grátis."
    )
    if not api_key:
        st.info("💡 [Obter chave grátis →](https://console.anthropic.com)")

    st.markdown("---")

    # Filtros de contexto
    st.markdown("### 🔍 Contexto da análise")
    
    empresas_disp = sorted(base["Empresa"].dropna().unique())
    sel_empresa = st.multiselect("Empresa", empresas_disp, default=empresas_disp, key="ai_empresa")

    setores_disp = sorted(base[base["Empresa"].isin(sel_empresa)]["Informe seu setor / departamento."].dropna().unique())
    sel_setor = st.multiselect("Setor", setores_disp, default=setores_disp, key="ai_setor")

    cargos_disp = sorted(base[base["Informe seu setor / departamento."].isin(sel_setor)]["Informe seu cargo"].dropna().unique())
    sel_cargo = st.multiselect("Cargo", cargos_disp, default=cargos_disp, key="ai_cargo")

    st.markdown("---")
    
    if st.button("🗑️ Limpar conversa", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.context_injected = False
        st.rerun()

    st.markdown("---")
    st.markdown(f"""
    <div style="font-size:11px; color:{COR_MUTED}; line-height:1.6;">
        <b>Modelo:</b> Claude Opus 4.5<br>
        <b>Dados:</b> {len(base)} respondentes<br>
        <b>Instrumento:</b> HSE-IT (NR-1)
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# INICIALIZAR SESSION STATE
# ─────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "context_injected" not in st.session_state:
    st.session_state.context_injected = False

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
contexto_atual, stats = build_context(sel_empresa, sel_setor, sel_cargo)
n_f = stats.get("n_respondentes", 0)
nr_f = stats.get("nr_medio", 0)
perc_alto_f = (stats.get("distribuicao_risco", {}).get("Crítico", 0) + 
               stats.get("distribuicao_risco", {}).get("Importante", 0)) / max(n_f, 1) * 100

st.markdown(f"""
<div class="agent-header">
  <div class="agent-avatar">🧠</div>
  <div>
    <h1 style="margin:0; font-size:22px;">Agente de Análise HSE-IT</h1>
    <p style="margin:4px 0 0 0; font-size:13px; color:{COR_MUTED};">
        Especialista em Riscos Psicossociais · NR-1 · Vivamente 360°
        &nbsp;·&nbsp; 
        <span style="color:{COR_TEXTO};">{n_f} respondentes</span>
        &nbsp;·&nbsp; NR médio: <span style="color:{COR_AMARELO if nr_f >= 5 else COR_VERDE};">{nr_f:.1f}</span>
        &nbsp;·&nbsp; <span style="color:{COR_LARANJA};">{perc_alto_f:.0f}% em risco alto</span>
    </p>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PERGUNTAS RÁPIDAS
# ─────────────────────────────────────────────
if not st.session_state.chat_history:
    st.markdown(f'<div class="section-title">💡 Perguntas de partida</div>', unsafe_allow_html=True)
    
    quick_questions = [
        ("🔴", "Quais são os principais alertas que preciso comunicar à liderança hoje?"),
        ("📊", "Analise os setores mais críticos e o que está por trás desses números."),
        ("🎯", "Gere um plano de ação prioritário para os próximos 90 dias."),
        ("🔬", "Qual dimensão está mais comprometida e por que isso importa?"),
        ("👥", "Que padrões você identifica nos cargos com maior risco?"),
        ("📋", "O que o PGR precisa contemplar com base nessa análise?"),
    ]
    
    cols = st.columns(2)
    for i, (emoji, q) in enumerate(quick_questions):
        with cols[i % 2]:
            if st.button(f"{emoji} {q}", key=f"quick_{i}", use_container_width=True):
                st.session_state.selected_quick = q
                st.rerun()

# ─────────────────────────────────────────────
# HISTÓRICO DO CHAT
# ─────────────────────────────────────────────
chat_container = st.container()

with chat_container:
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(f'<div class="msg-user">🙋 {msg["content"]}</div>', unsafe_allow_html=True)
        else:
            # Formatar resposta do agente
            content = msg["content"]
            # Converter markdown básico para HTML
            content_html = content.replace("\n\n", "<br><br>").replace("\n", "<br>")
            # Bold
            content_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content_html)
            # Italic
            content_html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', content_html)
            st.markdown(f'<div class="msg-agent">🤖 <strong style="color:{COR_PURPLE};">Agente HSE-IT</strong><br><br>{content_html}</div>', 
                       unsafe_allow_html=True)

# ─────────────────────────────────────────────
# INPUT DO USUÁRIO
# ─────────────────────────────────────────────
st.markdown("---")

# Processar quick question selecionada
if hasattr(st.session_state, "selected_quick"):
    user_input = st.session_state.selected_quick
    del st.session_state.selected_quick
else:
    user_input = None

col_input, col_btn = st.columns([5, 1])
with col_input:
    typed_input = st.text_area(
        "Sua pergunta",
        placeholder="Ex: Quais setores precisam de intervenção urgente? / Explique o score de Demandas / Que ações concretas você recomenda?",
        height=80,
        key="user_input_area",
        label_visibility="collapsed",
    )

with col_btn:
    send_btn = st.button("Enviar →", use_container_width=True, type="primary")

if typed_input and send_btn:
    user_input = typed_input

# ─────────────────────────────────────────────
# PROCESSAR MENSAGEM
# ─────────────────────────────────────────────
if user_input and user_input.strip():
    if not api_key:
        st.error("⚠️ Configure sua chave API Anthropic na barra lateral para usar o agente.")
        st.stop()

    # Adicionar mensagem do usuário
    st.session_state.chat_history.append({
        "role": "user",
        "content": user_input.strip()
    })

    # Montar messages para a API
    # Primeiro turno: injetar contexto dos dados
    api_messages = []
    
    # Injetar contexto como primeira mensagem do usuário (context window)
    context_message = f"""Você tem acesso ao seguinte contexto de dados do dashboard HSE-IT:

{contexto_atual}

---
Responda às perguntas do usuário com base nesses dados. Seja específico, cite números, e gere insights acionáveis."""

    # Reconstruir histórico para a API
    for i, msg in enumerate(st.session_state.chat_history):
        if i == 0:
            # Primeira mensagem: injetar contexto + pergunta do usuário
            api_messages.append({
                "role": "user",
                "content": f"{context_message}\n\nPrimeira pergunta do usuário: {msg['content']}"
            })
        else:
            api_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

    # Chamar API com indicador de progresso
    with st.spinner("🧠 Analisando dados..."):
        try:
            resposta = call_anthropic(api_messages, api_key)
            
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": resposta
            })
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Erro ao consultar o agente: {str(e)}")
            # Remover a mensagem do usuário que falhou
            st.session_state.chat_history.pop()

# ─────────────────────────────────────────────
# SEÇÃO DE INSIGHTS AUTOMÁTICOS (se não há chat ainda)
# ─────────────────────────────────────────────
if not st.session_state.chat_history and stats:
    st.markdown(f'<div class="section-title">📊 Resumo automático dos dados</div>', unsafe_allow_html=True)
    
    dist = stats.get("distribuicao_risco", {})
    n_total = stats.get("n_respondentes", 1)
    scores = stats.get("scores_por_dimensao", {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Distribuição de risco**")
        for nivel, cor in [("Crítico", COR_VERMELHO), ("Importante", COR_LARANJA), 
                           ("Moderado", COR_AMARELO), ("Aceitável", COR_VERDE)]:
            cnt = dist.get(nivel, 0)
            pct = cnt / n_total * 100
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid {COR_BORDA};">
                <span style="color:{COR_MUTED};">{nivel}</span>
                <span><b style="color:{cor};">{pct:.1f}%</b> <span style="color:{COR_MUTED}; font-size:12px;">({cnt})</span></span>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("**Scores por dimensão** (0–4)")
        for dim_label, score in scores.items():
            # Identificar se é dimensão negativa
            is_neg = dim_label in ["Demandas", "Relacionamentos"]
            if is_neg:
                cor = COR_VERMELHO if score >= 3 else COR_AMARELO if score >= 2 else COR_VERDE
            else:
                cor = COR_VERMELHO if score <= 1.5 else COR_AMARELO if score <= 2.5 else COR_VERDE
            
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; padding:5px 0; border-bottom:1px solid {COR_BORDA};">
                <span style="color:{COR_MUTED}; font-size:13px;">{dim_label}</span>
                <b style="color:{cor};">{score:.2f}</b>
            </div>
            """, unsafe_allow_html=True)

    # Top setores
    top_s = stats.get("top_setores_criticos", [])
    if top_s:
        st.markdown(f'<div class="section-title">🔥 Setores mais críticos (por NR)</div>', unsafe_allow_html=True)
        for s in top_s[:3]:
            nr = s.get("nr_medio", 0)
            cls = "critico" if nr >= 13 else "alerta" if nr >= 9 else "ok"
            st.markdown(f"""
            <div class="insight-card insight-{cls}">
                <b>{s.get("setor","—")}</b>
                &nbsp;&nbsp;<span style="color:{COR_MUTED}; font-size:12px;">{s.get("n",0)} pessoas</span>
                &nbsp;&nbsp;NR médio: <b>{nr:.2f}</b>
                &nbsp;&nbsp;{s.get("perc_alto",0)*100:.0f}% em risco alto
            </div>
            """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown(f"""
<div style="margin-top:2rem; padding-top:1rem; border-top:1px solid {COR_BORDA};
     display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
  <span style="font-size:11px; color:{COR_MUTED};">
    🤖 Agente HSE-IT · Powered by Claude · Vivamente 360°
  </span>
  <span style="font-size:11px; color:{COR_MUTED}; font-family:'DM Mono', monospace;">
    {datetime.now().strftime("%d/%m/%Y")} · {n_f} respondentes no contexto
  </span>
</div>
""", unsafe_allow_html=True)
