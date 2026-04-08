"""
🧠 Agente de IA — HSE-IT · Vivamente 360°
Analisa os dados de riscos psicossociais e gera insights acionáveis.
Tecnologia: Groq API (llama-3.3-70b-versatile) + Streamlit

ATUALIZAÇÃO: agora usa analytics.py como módulo compartilhado,
aproveitando TODAS as análises do dashboard (heatmap, PGR, matriz
de dimensões por setor/cargo, questões críticas, etc.).
"""

import streamlit as st
import pandas as pd
import json
import os
import re
import requests
from datetime import datetime

# ── Módulo compartilhado com o dashboard ──────────────────────────────────────
from analytics import (
    load_all_data,
    build_context,          # aplica filtros + roda analytics completo
    DIMENSOES, DIMENSOES_LABEL, DIM_NEGATIVAS,
    NIVEIS_ORDEM, NIVEIS_GERAL_ORDEM,
)

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
# CHAVE API
# ─────────────────────────────────────────────
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except KeyError:
    st.error("⚠️ Chave GROQ_API_KEY não encontrada em .streamlit/secrets.toml")
    st.stop()

# ─────────────────────────────────────────────
# PALETA
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

.section-title {{
    font-size: 12px; font-weight: 600; color: {COR_MUTED};
    text-transform: uppercase; letter-spacing: .1em;
    margin: 1.5rem 0 .8rem;
    padding-bottom: 6px;
    border-bottom: 1px solid {COR_BORDA};
}}

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
# CARGA DE DADOS (via analytics.py)
# ─────────────────────────────────────────────
@st.cache_data
def _load():
    return load_all_data()

base, setor, cargo, unidade = _load()

# ─────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """Você é o Especialista em Planos de Ação HSE-IT — um agente que gera exclusivamente planos de ação estruturados para riscos psicossociais (NR-1).

REGRAS OBRIGATÓRIAS (nunca quebre):
- Você deve responder APENAS com um JSON válido, nada mais, nada menos.
- Nunca adicione texto explicativo, introdução, conclusão ou qualquer coisa fora do JSON.
- Use exatamente o schema abaixo.
- Os campos devem ser claros, específicos e realistas para o contexto brasileiro de SST/RH.
- Prioridade: "Alta", "Média" ou "Baixa".
- Prazo: formato legível (ex: "Próximos 15 dias", "Até 30/06/2026", "90 dias").
- Indicador de sucesso: deve ser mensurável (número, %, taxa, score, etc.).
- Aproveite ao máximo as informações do contexto: matriz de risco por setor × dimensão,
  PGR por setor, questões críticas, NR por cargo e unidade.

SCHEMA OBRIGATÓRIO:
{
  "problema": "descrição curta e clara do problema principal identificado nos dados",
  "objetivo": "objetivo SMART do plano (o que queremos alcançar)",
  "acoes": [
    {
      "descricao": "descrição clara e acionável da ação",
      "responsavel": "quem executa (ex: Gestor de RH, Liderança da área, Equipe HSE, etc.)",
      "prazo": "prazo específico",
      "prioridade": "Alta | Média | Baixa",
      "indicador_sucesso": "métrica mensurável de sucesso"
    }
  ]
}

Exemplos de saída CORRETA:
{"problema":"Demandas excessivas (score 3.41/4) e NR geral elevado (12.8) em Operações","objetivo":"Reduzir score de Demandas em 1.0 ponto e NR geral abaixo de 9.0 em 90 dias","acoes":[{"descricao":"Mapear carga horária e redistribuir tarefas nas equipes sobrecarregadas","responsavel":"Gestores de Operações e RH","prazo":"30 dias","prioridade":"Alta","indicador_sucesso":"Redução de 25% nos colaboradores reportando sobrecarga"}]}
{"problema":"Baixo Controle (score 1.2/4) e alto risco crítico (28%) nos Analistas Administrativos","objetivo":"Aumentar score de Controle para ≥2.8 e reduzir risco crítico para <10%","acoes":[{"descricao":"Ampliar autonomia decisória em processos rotineiros","responsavel":"Gestores diretos + RH","prazo":"45 dias","prioridade":"Alta","indicador_sucesso":"Aumento de 1.5 ponto no score de Controle na próxima medição"}]}

Agora, com base no contexto completo do dashboard HSE-IT fornecido (que inclui a matriz de risco por setor × dimensão, PGR, questões críticas e NR por cargo), gere o plano de ação mais preciso e acionável possível.
"""

# ─────────────────────────────────────────────
# FUNÇÕES
# ─────────────────────────────────────────────
def validate_and_fix_plan(raw_response: str, max_retries: int = 3) -> dict:
    for _ in range(max_retries):
        try:
            json_str = re.search(r'\{.*\}', raw_response, re.DOTALL).group(0)
            plan = json.loads(json_str)
            required = ["problema", "objetivo", "acoes"]
            if not all(k in plan for k in required):
                raise ValueError("Campos obrigatórios ausentes")
            for acao in plan["acoes"]:
                if not all(k in acao for k in ["descricao", "responsavel", "prazo", "prioridade", "indicador_sucesso"]):
                    raise ValueError("Ação incompleta")
            return plan
        except Exception:
            continue
    return {"problema": "Erro na geração", "objetivo": "Corrigir output", "acoes": []}


def call_groq(messages: list, api_key: str) -> str:
    groq_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": "llama-3.3-70b-versatile",
            "max_tokens": 2048,
            "messages": groq_messages,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        },
        timeout=60,
    )
    if resp.status_code != 200:
        try:
            err = resp.json().get("error", {}).get("message", resp.text)
        except Exception:
            err = resp.text
        raise Exception(f"Erro API Groq ({resp.status_code}): {err}")
    return resp.json()["choices"][0]["message"]["content"]


# ─────────────────────────────────────────────
# SIDEBAR — filtros
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
        <div style="text-align:center; padding:25px 0 15px 0; border-bottom:1px solid {COR_BORDA};">
            <h2 style="margin:0; font-size:22px; color:{COR_ACCENT};">🤖 Agente HSE-IT</h2>
            <p style="margin:4px 0 0 0; font-size:12px; color:{COR_MUTED};">
                IA · Vivamente 360° · NR-1
            </p>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### 🔍 Contexto da análise")

    empresas_disp = sorted(base["Empresa"].dropna().unique())
    sel_empresa   = st.multiselect("Empresa", empresas_disp, default=empresas_disp, key="ai_empresa")

    setores_disp  = sorted(base[base["Empresa"].isin(sel_empresa)]["Informe seu setor / departamento."].dropna().unique())
    sel_setor     = st.multiselect("Setor", setores_disp, default=setores_disp, key="ai_setor")

    cargos_disp   = sorted(base[base["Informe seu setor / departamento."].isin(sel_setor)]["Informe seu cargo"].dropna().unique())
    sel_cargo     = st.multiselect("Cargo", cargos_disp, default=cargos_disp, key="ai_cargo")

    st.markdown("---")
    if st.button("🗑️ Limpar conversa", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

    st.markdown("---")
    st.markdown(f"""
    <div style="font-size:11px; color:{COR_MUTED}; line-height:1.8;">
        <b>Modelo:</b> Llama 3.3 70B (Groq)<br>
        <b>Dados:</b> {len(base)} respondentes<br>
        <b>Contexto:</b> dashboard completo (heatmap + PGR + questões)
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ─────────────────────────────────────────────
# CONTEXTO — build_context do analytics.py
# aproveita TODAS as análises do dashboard
# ─────────────────────────────────────────────
contexto_atual, stats = build_context(
    base,
    filtro_empresa=sel_empresa,
    filtro_setor=sel_setor,
    filtro_cargo=sel_cargo,
)

n_f          = stats.get("n_respondentes", 0)
nr_f         = stats.get("nr_medio", 0)
perc_alto_f  = stats.get("perc_risco_alto", 0)

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
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
for msg in st.session_state.chat_history:
    if msg["role"] == "user":
        st.markdown(f'<div class="msg-user">🙋 {msg["content"]}</div>', unsafe_allow_html=True)
    else:
        content = msg["content"]
        if isinstance(content, dict):
            st.markdown('<div class="msg-agent">🤖 <strong style="color:#A78BFA;">Agente HSE-IT</strong><br><br>', unsafe_allow_html=True)
            st.markdown("### 🎯 Plano de Ação")
            st.markdown(f"**Problema:** {content['problema']}")
            st.markdown(f"**Objetivo:** {content['objetivo']}")
            for acao in content["acoes"]:
                st.markdown(f"""
- **{acao['descricao']}**
  - Responsável: {acao['responsavel']}
  - Prazo: {acao['prazo']}
  - Prioridade: {acao['prioridade']}
  - Indicador: {acao['indicador_sucesso']}
""")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            content_html = content.replace("\n\n", "<br><br>").replace("\n", "<br>")
            content_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content_html)
            content_html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', content_html)
            st.markdown(f'''
            <div class="msg-agent">
            🤖 <strong style="color:{COR_PURPLE};">Agente HSE-IT</strong><br><br>
            {content_html}
            </div>
            ''', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# INPUT DO USUÁRIO
# ─────────────────────────────────────────────
st.markdown("---")

if hasattr(st.session_state, "selected_quick"):
    user_input = st.session_state.selected_quick
    del st.session_state.selected_quick
else:
    user_input = None

col_input, col_btn = st.columns([5, 1])
with col_input:
    typed_input = st.text_area(
        "Sua pergunta",
        placeholder="Ex: Quais setores precisam de intervenção urgente?",
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
    st.session_state.chat_history.append({"role": "user", "content": user_input.strip()})

    # Monta histórico para API (injeta contexto rico na primeira mensagem)
    context_message = f"""CONTEXTO COMPLETO DO DASHBOARD HSE-IT (use estes dados para embasar o plano):

{contexto_atual}

---
Gere o plano de ação em JSON conforme o schema definido."""

    api_messages = []
    for i, msg in enumerate(st.session_state.chat_history):
        if i == 0:
            api_messages.append({
                "role": "user",
                "content": f"{context_message}\n\nPergunta: {msg['content']}"
            })
        else:
            api_messages.append({"role": msg["role"], "content": msg["content"]})

    with st.spinner("🧠 Analisando dados do dashboard..."):
        try:
            raw = call_groq(api_messages, GROQ_API_KEY)
            plan = validate_and_fix_plan(raw)
            st.session_state.chat_history.append({"role": "assistant", "content": plan})
            st.rerun()
        except Exception as e:
            st.error(f"❌ Erro ao consultar o agente: {str(e)}")
            st.session_state.chat_history.pop()

# ─────────────────────────────────────────────
# RESUMO AUTOMÁTICO (quando não há chat ainda)
# ─────────────────────────────────────────────
if not st.session_state.chat_history and stats:
    st.markdown(f'<div class="section-title">📊 Resumo automático dos dados</div>', unsafe_allow_html=True)

    dist   = stats.get("distribuicao_risco", {})
    n_tot  = max(stats.get("n_respondentes", 1), 1)
    scores = stats.get("scores_por_dimensao", {})
    class_ = stats.get("classificacao_por_dimensao", {})

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Distribuição de risco**")
        for nivel, cor in [("Crítico", COR_VERMELHO), ("Importante", COR_LARANJA),
                           ("Moderado", COR_AMARELO), ("Aceitável", COR_VERDE)]:
            cnt = dist.get(nivel, 0)
            pct = cnt / n_tot * 100
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid {COR_BORDA};">
                <span style="color:{COR_MUTED};">{nivel}</span>
                <span><b style="color:{cor};">{pct:.1f}%</b> <span style="color:{COR_MUTED}; font-size:12px;">({cnt})</span></span>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        st.markdown("**Scores por dimensão com classificação**")
        for dim_label, score in scores.items():
            cls = class_.get(dim_label, "")
            is_neg = dim_label in ["Demandas", "Relacionamentos"]
            cor = (COR_VERMELHO if (score >= 3 if is_neg else score <= 1.5)
                   else COR_AMARELO if (score >= 2 if is_neg else score <= 2.5)
                   else COR_VERDE)
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; padding:5px 0; border-bottom:1px solid {COR_BORDA};">
                <span style="color:{COR_MUTED}; font-size:13px;">{dim_label}</span>
                <span><b style="color:{cor};">{score:.2f}</b>
                <span style="color:{COR_MUTED}; font-size:11px;"> {cls}</span></span>
            </div>
            """, unsafe_allow_html=True)

    # Top setores críticos (usando dados ricos do analytics.py)
    top_s = stats.get("top_setores", [])
    if top_s:
        st.markdown(f'<div class="section-title">🔥 Setores mais críticos</div>', unsafe_allow_html=True)
        for s in top_s[:3]:
            nr  = s.get("NR_geral", 0)
            cls = "critico" if nr >= 13 else "alerta" if nr >= 9 else "ok"
            dims_crit = s.get("dimensoes_criticas_ou_importantes", {})
            dims_txt  = "  ·  " + ", ".join(f"{k}={v}" for k, v in list(dims_crit.items())[:3]) if dims_crit else ""
            st.markdown(f"""
            <div class="insight-card insight-{cls}">
                <b>{s.get('Setor', s.get('setor', '—'))}</b>
                &nbsp;&nbsp;<span style="color:{COR_MUTED}; font-size:12px;">{s.get('n_colaboradores', 0)} pessoas</span>
                &nbsp;&nbsp;NR: <b>{nr:.2f}</b>
                &nbsp;&nbsp;{s.get('perc_risco_alto', 0)*100:.0f}% em risco alto
                <span style="color:{COR_MUTED}; font-size:11px;">{dims_txt}</span>
            </div>
            """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown(f"""
<div style="margin-top:2rem; padding-top:1rem; border-top:1px solid {COR_BORDA};
     display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
  <span style="font-size:11px; color:{COR_MUTED};">
    🤖 Agente HSE-IT · Powered by Groq + Llama 3.3 · Vivamente 360°
  </span>
  <span style="font-size:11px; color:{COR_MUTED}; font-family:'DM Mono', monospace;">
    {datetime.now().strftime("%d/%m/%Y")} · {n_f} respondentes · contexto: dashboard completo
  </span>
</div>
""", unsafe_allow_html=True)
