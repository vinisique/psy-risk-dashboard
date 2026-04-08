"""
🧠 Agente de IA — HSE-IT · Vivamente 360°
Analisa os dados de riscos psicossociais e gera insights acionáveis.
Tecnologia: Groq API (llama-3.3-70b-versatile) + Streamlit

ATUALIZAÇÃO v2: plano de ação em padrão 5W2H, editável, persistente e com
acompanhamento de status por ação (Pendente / Em andamento / Concluído).
"""

import streamlit as st
import pandas as pd
import json
import os
import re
import uuid
import requests
from datetime import datetime
from pathlib import Path

# ── Módulo compartilhado com o dashboard ──────────────────────────────────────
from analytics import (
    load_all_data,
    build_context,
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

STATUS_CONFIG = {
    "Pendente":      {"cor": COR_CINZA,    "emoji": "⏳"},
    "Em andamento":  {"cor": COR_AMARELO,  "emoji": "🔄"},
    "Concluído":     {"cor": COR_VERDE,    "emoji": "✅"},
}

# ─────────────────────────────────────────────
# PERSISTÊNCIA
# ─────────────────────────────────────────────
PLANS_FILE = Path("hse_planos.json")

def load_saved_plans() -> dict:
    if PLANS_FILE.exists():
        try:
            return json.loads(PLANS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_plans(plans: dict):
    PLANS_FILE.write_text(json.dumps(plans, ensure_ascii=False, indent=2), encoding="utf-8")

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

/* Plano 5W2H */
.plan-header {{
    background: linear-gradient(135deg, #1e2a4a 0%, #1A1D27 100%);
    border: 1px solid {COR_ACCENT}44;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 12px;
}}
.w2h-badge {{
    display: inline-block;
    background: {COR_ACCENT}22;
    color: {COR_ACCENT};
    border: 1px solid {COR_ACCENT}44;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
    font-family: 'DM Mono', monospace;
    margin-right: 6px;
}}
.progress-bar-bg {{
    background: {COR_BORDA};
    border-radius: 99px;
    height: 8px;
    width: 100%;
    margin-top: 4px;
}}
.progress-bar-fill {{
    border-radius: 99px;
    height: 8px;
    transition: width 0.3s ease;
}}
.acao-card {{
    background: {COR_CARD};
    border: 1px solid {COR_BORDA};
    border-radius: 10px;
    padding: 14px 16px;
    margin: 8px 0;
}}
.status-badge {{
    display: inline-block;
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 600;
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
# SYSTEM PROMPT — 5W2H
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """Você é o Especialista em Planos de Ação HSE-IT — um agente que gera exclusivamente planos de ação estruturados para riscos psicossociais (NR-1), seguindo rigorosamente o padrão 5W2H.

REGRAS OBRIGATÓRIAS (nunca quebre):
- Você deve responder APENAS com um JSON válido, nada mais, nada menos.
- Nunca adicione texto explicativo, introdução, conclusão ou qualquer coisa fora do JSON.
- Use exatamente o schema abaixo com o padrão 5W2H completo.
- Os campos devem ser claros, específicos e realistas para o contexto brasileiro de SST/RH.
- Prioridade: "Alta", "Média" ou "Baixa".
- Prazo (when): formato legível (ex: "Próximos 15 dias", "Até 30/06/2026", "90 dias").
- Indicador de sucesso: deve ser mensurável (número, %, taxa, score, etc.).
- Custo estimado (how_much): valor estimado ou "A definir" se não aplicável.
- Aproveite ao máximo as informações do contexto fornecido.

DEFINIÇÃO DO 5W2H:
- What (O quê): descrição clara da ação a ser executada
- Why (Por quê): justificativa baseada nos dados de risco
- Who (Quem): responsável pela execução
- Where (Onde): local/setor/área de aplicação
- When (Quando): prazo e frequência
- How (Como): metodologia/forma de execução
- How Much (Quanto custa): custo estimado ou recurso necessário

SCHEMA OBRIGATÓRIO:
{
  "problema": "descrição curta e clara do problema principal identificado nos dados",
  "objetivo": "objetivo SMART do plano (o que queremos alcançar)",
  "acoes": [
    {
      "what": "descrição clara e acionável da ação (O quê)",
      "why": "justificativa baseada nos dados de risco (Por quê)",
      "who": "quem executa (ex: Gestor de RH, Liderança da área, Equipe HSE)",
      "where": "local, setor ou área de aplicação (Onde)",
      "when": "prazo específico e frequência se aplicável (Quando)",
      "how": "método ou forma de executar a ação (Como)",
      "how_much": "custo estimado ou recursos necessários (Quanto custa)",
      "prioridade": "Alta | Média | Baixa",
      "indicador_sucesso": "métrica mensurável de sucesso"
    }
  ]
}

Exemplo de saída CORRETA:
{"problema":"Demandas excessivas (score 3.41/4) em Operações","objetivo":"Reduzir score de Demandas em 1.0 ponto em 90 dias","acoes":[{"what":"Redistribuição de carga horária e tarefas","why":"Score de Demandas 3.41/4 indica sobrecarga crítica afetando 68% da equipe","who":"Gestores de Operações e RH","where":"Setor de Operações","when":"30 dias, revisão mensal","how":"Workshop de mapeamento de processos + reuniões individuais de alinhamento","how_much":"16h de consultoria interna (sem custo adicional)","prioridade":"Alta","indicador_sucesso":"Redução de 25% nos colaboradores reportando sobrecarga na próxima medição"}]}

Gere o plano mais preciso e acionável possível com base no contexto HSE-IT fornecido.
"""

# ─────────────────────────────────────────────
# FUNÇÕES AUXILIARES
# ─────────────────────────────────────────────
def validate_and_fix_plan(raw_response: str, messages: list, api_key: str, max_retries: int = 3) -> dict:
    """Valida o JSON 5W2H retornado. Se inválido, tenta corrigir via API."""
    REQUIRED_ACTION_KEYS = ["what", "why", "who", "where", "when", "how", "how_much", "prioridade", "indicador_sucesso"]
    current_raw = raw_response
    for attempt in range(max_retries):
        try:
            json_str = re.search(r'\{.*\}', current_raw, re.DOTALL).group(0)
            plan = json.loads(json_str)
            if not all(k in plan for k in ["problema", "objetivo", "acoes"]):
                raise ValueError("Campos raiz ausentes")
            for acao in plan["acoes"]:
                if not all(k in acao for k in REQUIRED_ACTION_KEYS):
                    raise ValueError(f"Ação incompleta — faltam: {[k for k in REQUIRED_ACTION_KEYS if k not in acao]}")
            # Injeta campos de controle
            for acao in plan["acoes"]:
                acao.setdefault("status", "Pendente")
                acao.setdefault("id", str(uuid.uuid4())[:8])
                acao.setdefault("notas", "")
                acao.setdefault("data_conclusao", "")
            plan["id"] = str(uuid.uuid4())[:12]
            plan["criado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
            plan["titulo"] = plan["problema"][:60]
            return plan
        except Exception as e:
            if attempt < max_retries - 1:
                retry_messages = messages + [
                    {"role": "assistant", "content": current_raw},
                    {"role": "user", "content":
                        f"O JSON retornado está inválido ({e}). "
                        "Corrija e retorne APENAS o JSON válido com o padrão 5W2H: "
                        "problema, objetivo, acoes (cada ação com what, why, who, where, when, how, how_much, prioridade, indicador_sucesso)."}
                ]
                try:
                    current_raw = call_groq(retry_messages, api_key)
                except Exception:
                    break
    return {"problema": "Erro na geração", "objetivo": "Tente novamente", "acoes": [], "id": "err", "criado_em": "", "titulo": "Erro"}


def call_groq(messages: list, api_key: str) -> str:
    groq_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": "llama-3.3-70b-versatile",
            "max_tokens": 3000,
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


def calc_progress(plan: dict) -> tuple[int, int, int]:
    """Retorna (concluídas, em_andamento, total)."""
    acoes = plan.get("acoes", [])
    total = len(acoes)
    concluidas = sum(1 for a in acoes if a.get("status") == "Concluído")
    em_andamento = sum(1 for a in acoes if a.get("status") == "Em andamento")
    return concluidas, em_andamento, total


def render_progress_bar(concluidas: int, em_andamento: int, total: int):
    if total == 0:
        return
    pct_concluido = concluidas / total * 100
    pct_andamento = em_andamento / total * 100
    st.markdown(f"""
    <div style="margin: 4px 0 12px 0;">
        <div style="display:flex; justify-content:space-between; font-size:12px; color:{COR_MUTED}; margin-bottom:4px;">
            <span>✅ {concluidas}/{total} ações concluídas</span>
            <span style="color:{COR_ACCENT};">{pct_concluido:.0f}% completo</span>
        </div>
        <div class="progress-bar-bg">
            <div class="progress-bar-fill" style="width:{pct_concluido:.1f}%; background:{COR_VERDE};"></div>
        </div>
        <div style="display:flex; gap:16px; margin-top:6px; font-size:11px;">
            <span style="color:{COR_VERDE};">⬤ Concluído: {concluidas}</span>
            <span style="color:{COR_AMARELO};">⬤ Em andamento: {em_andamento}</span>
            <span style="color:{COR_CINZA};">⬤ Pendente: {total - concluidas - em_andamento}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_plan_card(plan: dict, plan_key: str, edit_mode: bool = False):
    """Renderiza um plano de ação 5W2H completo com editor opcional."""
    concluidas, em_andamento, total = calc_progress(plan)

    # Cabeçalho do plano
    st.markdown(f"""
    <div class="plan-header">
        <div style="font-size:11px; color:{COR_MUTED}; margin-bottom:4px; font-family:'DM Mono',monospace;">
            PLANO · {plan.get('criado_em', '')} · ID {plan.get('id', '')}
        </div>
        <div style="font-size:17px; font-weight:600; color:{COR_TEXTO}; margin-bottom:6px;">
            🎯 {plan.get('problema', '')}
        </div>
        <div style="font-size:13px; color:{COR_MUTED};">
            <b style="color:{COR_ACCENT};">Objetivo:</b> {plan.get('objetivo', '')}
        </div>
    </div>
    """, unsafe_allow_html=True)

    render_progress_bar(concluidas, em_andamento, total)

    # Cabeçalho da tabela 5W2H
    labels_5w2h = [
        ("🔵 O quê", "what"),
        ("❓ Por quê", "why"),
        ("👤 Quem", "who"),
        ("📍 Onde", "where"),
        ("📅 Quando", "when"),
        ("⚙️ Como", "how"),
        ("💰 Quanto custa", "how_much"),
    ]

    saved_plans = st.session_state.get("saved_plans", {})

    for idx, acao in enumerate(plan.get("acoes", [])):
        acao_id = acao.get("id", str(idx))
        status  = acao.get("status", "Pendente")
        scfg    = STATUS_CONFIG.get(status, STATUS_CONFIG["Pendente"])
        pri     = acao.get("prioridade", "Média")
        pri_cor = COR_VERMELHO if pri == "Alta" else COR_AMARELO if pri == "Média" else COR_VERDE

        with st.expander(f"{scfg['emoji']} Ação {idx+1} — {acao.get('what', '')[:70]}  |  {pri}", expanded=edit_mode):

            # Status + prioridade
            col_s, col_p = st.columns([2, 1])
            with col_s:
                novo_status = st.selectbox(
                    "Status",
                    list(STATUS_CONFIG.keys()),
                    index=list(STATUS_CONFIG.keys()).index(status),
                    key=f"status_{plan_key}_{acao_id}",
                )
            with col_p:
                nova_pri = st.selectbox(
                    "Prioridade",
                    ["Alta", "Média", "Baixa"],
                    index=["Alta", "Média", "Baixa"].index(pri),
                    key=f"pri_{plan_key}_{acao_id}",
                )

            # Campos 5W2H editáveis
            novos_campos = {}
            for label, campo in labels_5w2h:
                novos_campos[campo] = st.text_area(
                    label,
                    value=acao.get(campo, ""),
                    height=68,
                    key=f"{campo}_{plan_key}_{acao_id}",
                )

            # Indicador e notas
            novo_indicador = st.text_input(
                "📊 Indicador de sucesso",
                value=acao.get("indicador_sucesso", ""),
                key=f"ind_{plan_key}_{acao_id}",
            )
            novas_notas = st.text_area(
                "📝 Notas / observações",
                value=acao.get("notas", ""),
                height=60,
                key=f"notas_{plan_key}_{acao_id}",
            )

            if novo_status == "Concluído" and status != "Concluído":
                data_conclusao = datetime.now().strftime("%d/%m/%Y")
            else:
                data_conclusao = acao.get("data_conclusao", "")

            # Botão salvar ação
            if st.button(f"💾 Salvar alterações — Ação {idx+1}", key=f"save_{plan_key}_{acao_id}", type="primary"):
                acao.update({
                    "status": novo_status,
                    "prioridade": nova_pri,
                    "indicador_sucesso": novo_indicador,
                    "notas": novas_notas,
                    "data_conclusao": data_conclusao,
                    **novos_campos,
                })
                saved_plans[plan_key] = plan
                save_plans(saved_plans)
                st.session_state.saved_plans = saved_plans
                st.success("✅ Alterações salvas!")
                st.rerun()

    # Exportar plano como JSON
    st.download_button(
        "⬇️ Exportar plano (JSON)",
        data=json.dumps(plan, ensure_ascii=False, indent=2),
        file_name=f"plano_{plan.get('id', 'hse')}_{datetime.now().strftime('%Y%m%d')}.json",
        mime="application/json",
        key=f"export_{plan_key}",
    )


# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "saved_plans" not in st.session_state:
    st.session_state.saved_plans = load_saved_plans()

# ─────────────────────────────────────────────
# SIDEBAR — filtros + planos salvos
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

    # Planos salvos na sidebar
    saved_plans = st.session_state.saved_plans
    if saved_plans:
        st.markdown("### 📋 Planos salvos")
        for pk, pl in saved_plans.items():
            conc, _, tot = calc_progress(pl)
            pct = int(conc / tot * 100) if tot else 0
            cor_pct = COR_VERDE if pct == 100 else COR_AMARELO if pct > 0 else COR_CINZA
            if st.button(
                f"{'✅' if pct==100 else '📄'} {pl.get('titulo','Plano')[:30]}…  {pct}%",
                key=f"sb_{pk}",
                use_container_width=True,
            ):
                st.session_state.viewing_plan = pk
                st.rerun()
        st.markdown("---")

    if st.button("🗑️ Limpar conversa", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

    st.markdown(f"""
    <div style="font-size:11px; color:{COR_MUTED}; line-height:1.8; margin-top:8px;">
        <b>Modelo:</b> Llama 3.3 70B (Groq)<br>
        <b>Dados:</b> {len(base)} respondentes<br>
        <b>Planos salvos:</b> {len(saved_plans)}<br>
        <b>Padrão:</b> 5W2H
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CONTEXTO — build_context do analytics.py
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
        Especialista em Riscos Psicossociais · NR-1 · Planos 5W2H · Vivamente 360°
        &nbsp;·&nbsp;
        <span style="color:{COR_TEXTO};">{n_f} respondentes</span>
        &nbsp;·&nbsp; NR médio: <span style="color:{COR_AMARELO if nr_f >= 5 else COR_VERDE};">{nr_f:.1f}</span>
        &nbsp;·&nbsp; <span style="color:{COR_LARANJA};">{perc_alto_f:.0f}% em risco alto</span>
    </p>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# ABAS PRINCIPAIS
# ─────────────────────────────────────────────
tab_chat, tab_planos = st.tabs(["💬 Chat com o Agente", "📋 Planos de Ação"])

# ══════════════════════════════════════════════
# ABA 1: CHAT
# ══════════════════════════════════════════════
with tab_chat:

    # Perguntas rápidas
    if not st.session_state.chat_history:
        st.markdown(f'<div class="section-title">💡 Perguntas de partida</div>', unsafe_allow_html=True)

        quick_questions = [
            ("🔴", "Quais são os principais alertas que preciso comunicar à liderança hoje?"),
            ("📊", "Analise os setores mais críticos e o que está por trás desses números."),
            ("🎯", "Gere um plano de ação 5W2H prioritário para os próximos 90 dias."),
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

    # Histórico do chat
    for msg_idx, msg in enumerate(st.session_state.chat_history):
        if msg["role"] == "user":
            st.markdown(f'<div class="msg-user">🙋 {msg["content"]}</div>', unsafe_allow_html=True)
        else:
            content = msg["content"]
            if isinstance(content, dict) and "acoes" in content:
                # É um plano 5W2H — renderiza compacto no chat
                conc, and_, tot = calc_progress(content)
                pct = int(conc / tot * 100) if tot else 0
                st.markdown(f"""
                <div class="msg-agent">
                🤖 <strong style="color:{COR_PURPLE};">Agente HSE-IT</strong> — Plano 5W2H gerado<br><br>
                <b style="color:{COR_ACCENT};">Problema:</b> {content.get('problema','')}<br>
                <b style="color:{COR_ACCENT};">Objetivo:</b> {content.get('objetivo','')}<br>
                <span style="font-size:12px; color:{COR_MUTED};">
                    {tot} ações · {pct}% concluído · ID: {content.get('id','')}
                </span>
                </div>
                """, unsafe_allow_html=True)

                # Botão para salvar/ver o plano
                plan_key = content.get("id", str(msg_idx))
                col_salvar, col_ver = st.columns([1, 1])
                with col_salvar:
                    if plan_key not in st.session_state.saved_plans:
                        if st.button("💾 Salvar este plano", key=f"savebtn_{msg_idx}"):
                            st.session_state.saved_plans[plan_key] = content
                            save_plans(st.session_state.saved_plans)
                            st.success("Plano salvo!")
                            st.rerun()
                    else:
                        st.success("✅ Plano já salvo")
                with col_ver:
                    if st.button("📋 Ver / editar plano completo", key=f"verbtn_{msg_idx}"):
                        if plan_key not in st.session_state.saved_plans:
                            st.session_state.saved_plans[plan_key] = content
                            save_plans(st.session_state.saved_plans)
                        st.session_state.viewing_plan = plan_key
                        st.rerun()
            else:
                content_html = str(content).replace("\n\n", "<br><br>").replace("\n", "<br>")
                content_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content_html)
                content_html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', content_html)
                st.markdown(f'''
                <div class="msg-agent">
                🤖 <strong style="color:{COR_PURPLE};">Agente HSE-IT</strong><br><br>
                {content_html}
                </div>
                ''', unsafe_allow_html=True)

    # Input
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
            placeholder="Ex: Gere um plano 5W2H para o setor de Operações",
            height=80,
            key="user_input_area",
            label_visibility="collapsed",
        )
    with col_btn:
        send_btn = st.button("Enviar →", use_container_width=True, type="primary")

    if typed_input and send_btn:
        user_input = typed_input

    # Processar mensagem
    if user_input and user_input.strip():
        st.session_state.chat_history.append({"role": "user", "content": user_input.strip()})

        context_message = f"""CONTEXTO COMPLETO DO DASHBOARD HSE-IT:

{contexto_atual}

---
Gere o plano de ação em padrão 5W2H conforme o schema definido."""

        api_messages = []
        last_user_idx = max(i for i, m in enumerate(st.session_state.chat_history) if m["role"] == "user")
        for i, msg in enumerate(st.session_state.chat_history):
            if msg["role"] == "user" and i == last_user_idx:
                api_messages.append({
                    "role": "user",
                    "content": f"{context_message}\n\nPergunta: {msg['content']}"
                })
            else:
                content = msg["content"]
                if isinstance(content, dict):
                    content = json.dumps(content, ensure_ascii=False)
                api_messages.append({"role": msg["role"], "content": content})

        with st.spinner("🧠 Gerando plano 5W2H com base nos dados do dashboard..."):
            try:
                raw = call_groq(api_messages, GROQ_API_KEY)
                plan = validate_and_fix_plan(raw, api_messages, GROQ_API_KEY)
                st.session_state.chat_history.append({"role": "assistant", "content": plan})
                st.rerun()
            except Exception as e:
                st.error(f"❌ Erro ao consultar o agente: {str(e)}")
                st.session_state.chat_history.pop()

    # Resumo automático (quando não há chat)
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
            st.markdown("**Scores por dimensão**")
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

# ══════════════════════════════════════════════
# ABA 2: PLANOS DE AÇÃO
# ══════════════════════════════════════════════
with tab_planos:
    saved_plans = st.session_state.saved_plans

    # Se veio de um link da sidebar ou botão do chat
    viewing_key = st.session_state.get("viewing_plan", None)

    if not saved_plans:
        st.info("💡 Nenhum plano salvo ainda. Peça ao agente para gerar um plano de ação e clique em 'Salvar este plano'.")
    else:
        # Visão geral — todos os planos
        st.markdown(f'<div class="section-title">📊 Visão geral dos planos</div>', unsafe_allow_html=True)

        total_acoes_g    = sum(len(p.get("acoes", [])) for p in saved_plans.values())
        total_concluidas = sum(calc_progress(p)[0] for p in saved_plans.values())
        total_andamento  = sum(calc_progress(p)[1] for p in saved_plans.values())
        pct_global       = int(total_concluidas / total_acoes_g * 100) if total_acoes_g else 0

        col_g1, col_g2, col_g3, col_g4 = st.columns(4)
        col_g1.metric("Planos ativos", len(saved_plans))
        col_g2.metric("Ações totais", total_acoes_g)
        col_g3.metric("Ações concluídas", total_concluidas)
        col_g4.metric("Progresso global", f"{pct_global}%")

        render_progress_bar(total_concluidas, total_andamento, total_acoes_g)

        st.markdown("---")

        # Seletor de plano
        plan_options = {pk: f"{'✅' if calc_progress(pl)[0]==len(pl.get('acoes',[])) and pl.get('acoes') else '📄'} {pl.get('titulo','Plano')[:50]} — {pl.get('criado_em','')}"
                        for pk, pl in saved_plans.items()}

        # Pré-seleciona o plano se veio de um botão
        default_idx = 0
        if viewing_key and viewing_key in list(plan_options.keys()):
            default_idx = list(plan_options.keys()).index(viewing_key)

        selected_pk = st.selectbox(
            "Selecione o plano",
            list(plan_options.keys()),
            format_func=lambda k: plan_options[k],
            index=default_idx,
            key="plan_selector",
        )

        if "viewing_plan" in st.session_state:
            del st.session_state.viewing_plan

        if selected_pk:
            plan = saved_plans[selected_pk]

            col_del, _ = st.columns([1, 4])
            with col_del:
                if st.button("🗑️ Excluir este plano", key="del_plan"):
                    del st.session_state.saved_plans[selected_pk]
                    save_plans(st.session_state.saved_plans)
                    st.rerun()

            st.markdown("---")
            render_plan_card(plan, selected_pk, edit_mode=True)

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown(f"""
<div style="margin-top:2rem; padding-top:1rem; border-top:1px solid {COR_BORDA};
     display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
  <span style="font-size:11px; color:{COR_MUTED};">
    🤖 Agente HSE-IT · Groq + Llama 3.3 · Padrão 5W2H · Vivamente 360°
  </span>
  <span style="font-size:11px; color:{COR_MUTED}; font-family:'DM Mono', monospace;">
    {datetime.now().strftime("%d/%m/%Y")} · {n_f} respondentes · {len(st.session_state.saved_plans)} planos salvos
  </span>
</div>
""", unsafe_allow_html=True)
