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
# SESSION STATE — inicializado ANTES de tudo
# ─────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "action_plans" not in st.session_state:
    st.session_state.action_plans = []
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "chat"
if "editing_plan_idx" not in st.session_state:
    st.session_state.editing_plan_idx = None
if "plan_edit_state" not in st.session_state:
    st.session_state.plan_edit_state = {}

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

/* 5W2H TABLE STYLES */
.w2h-wrapper {{
    background: {COR_CARD};
    border: 1px solid {COR_BORDA};
    border-radius: 4px 16px 16px 16px;
    padding: 20px;
    margin: 8px 10% 8px 0;
}}
.w2h-header {{
    display: flex; align-items: center; gap: 12px;
    margin-bottom: 12px;
}}
.w2h-problema {{
    background: #1e1e30;
    border-left: 3px solid {COR_PURPLE};
    border-radius: 0 8px 8px 0;
    padding: 10px 14px;
    margin-bottom: 6px;
    font-size: 13px;
}}
.w2h-objetivo {{
    background: #1a2a1a;
    border-left: 3px solid {COR_VERDE};
    border-radius: 0 8px 8px 0;
    padding: 10px 14px;
    margin-bottom: 14px;
    font-size: 13px;
}}
.w2h-table {{
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 12px;
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid {COR_BORDA};
}}
.w2h-table th {{
    padding: 10px 10px;
    text-align: center;
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    border-bottom: 2px solid {COR_BORDA};
    border-right: 1px solid {COR_BORDA};
}}
.w2h-table td {{
    padding: 10px 10px;
    vertical-align: top;
    border-bottom: 1px solid {COR_BORDA};
    border-right: 1px solid {COR_BORDA};
    line-height: 1.5;
    font-size: 12px;
}}
.w2h-table tr:last-child td {{ border-bottom: none; }}
.w2h-table td:last-child, .w2h-table th:last-child {{ border-right: none; }}
.w2h-table tr:nth-child(even) td {{ background: rgba(255,255,255,0.02); }}
.th-what   {{ background: #4c1d95; color: #e9d5ff; }}
.th-why    {{ background: #7c2d8e; color: #f3e8ff; }}
.th-where  {{ background: #be185d; color: #fce7f3; }}
.th-when   {{ background: #c2410c; color: #ffedd5; }}
.th-who    {{ background: #b45309; color: #fef3c7; }}
.th-how    {{ background: #047857; color: #d1fae5; }}
.th-howmuch{{ background: #0e7490; color: #cffafe; }}
.th-status {{ background: #374151; color: #f9fafb; }}
.badge-alta    {{ background: {COR_VERMELHO}22; color: {COR_VERMELHO}; border:1px solid {COR_VERMELHO}44; border-radius:6px; padding:2px 8px; font-size:11px; font-weight:600; }}
.badge-media   {{ background: {COR_AMARELO}22; color: {COR_AMARELO}; border:1px solid {COR_AMARELO}44; border-radius:6px; padding:2px 8px; font-size:11px; font-weight:600; }}
.badge-baixa   {{ background: {COR_VERDE}22; color: {COR_VERDE}; border:1px solid {COR_VERDE}44; border-radius:6px; padding:2px 8px; font-size:11px; font-weight:600; }}
.badge-pendente    {{ background: #374151; color: #9ca3af; border:1px solid #4b5563; border-radius:6px; padding:2px 8px; font-size:11px; }}
.badge-em-andamento{{ background: {COR_ACCENT}22; color: {COR_ACCENT}; border:1px solid {COR_ACCENT}44; border-radius:6px; padding:2px 8px; font-size:11px; }}
.badge-concluido   {{ background: {COR_VERDE}22; color: {COR_VERDE}; border:1px solid {COR_VERDE}44; border-radius:6px; padding:2px 8px; font-size:11px; }}
.badge-cancelado   {{ background: #dc262622; color: #ef4444; border:1px solid #ef444444; border-radius:6px; padding:2px 8px; font-size:11px; }}

/* TAB NAV */
.tab-nav {{
    display: flex; gap: 8px; margin-bottom: 1.5rem;
    border-bottom: 1px solid {COR_BORDA}; padding-bottom: 0;
}}
.tab-btn {{
    padding: 10px 20px; background: transparent;
    border: none; border-bottom: 2px solid transparent;
    color: {COR_MUTED}; font-size: 14px; font-weight: 500;
    cursor: pointer; transition: all .2s;
}}
.tab-btn.active {{
    color: {COR_ACCENT}; border-bottom-color: {COR_ACCENT};
}}

/* PLAN CARD in plans tab */
.plan-card {{
    background: {COR_CARD};
    border: 1px solid {COR_BORDA};
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 12px;
    transition: border-color .2s;
}}
.plan-card:hover {{ border-color: {COR_ACCENT}55; }}
.plan-card-title {{
    font-size: 14px; font-weight: 600; color: {COR_TEXTO};
    margin-bottom: 4px;
}}
.plan-card-meta {{
    font-size: 12px; color: {COR_MUTED};
}}
.progress-bar-outer {{
    background: {COR_BORDA}; border-radius: 4px; height: 6px;
    margin: 10px 0 4px;
}}
.progress-bar-inner {{
    height: 100%; border-radius: 4px;
    background: linear-gradient(90deg, {COR_ACCENT}, {COR_PURPLE});
    transition: width .4s ease;
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
      "descricao": "descrição clara e acionável da ação (O quê?)",
      "porque": "justificativa específica desta ação (Por quê?)",
      "onde": "setor, área ou local de aplicação (Onde?)",
      "responsavel": "quem executa (ex: Gestor de RH, Liderança da área, Equipe HSE) (Quem?)",
      "prazo": "prazo específico (Quando?)",
      "como": "método, ferramenta ou abordagem de execução (Como?)",
      "prioridade": "Alta | Média | Baixa",
      "indicador_sucesso": "métrica mensurável de sucesso — número, %, taxa ou score (Quanto?)"
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
def validate_and_fix_plan(raw_response: str, messages: list, api_key: str, max_retries: int = 3) -> dict:
    """Valida o JSON retornado pelo agente. Se inválido, chama a API novamente
    com uma instrução de correção até max_retries tentativas."""
    current_raw = raw_response
    for attempt in range(max_retries):
        try:
            json_str = re.search(r'\{.*\}', current_raw, re.DOTALL).group(0)
            plan = json.loads(json_str)
            required = ["problema", "objetivo", "acoes"]
            if not all(k in plan for k in required):
                raise ValueError("Campos obrigatórios ausentes")
            for acao in plan["acoes"]:
                if not all(k in acao for k in ["descricao", "responsavel", "prazo", "prioridade", "indicador_sucesso"]):
                    raise ValueError("Ação incompleta")
            # Preenche campos opcionais com fallback se ausentes
            for acao in plan["acoes"]:
                acao.setdefault("porque", plan.get("objetivo",""))
                acao.setdefault("onde", "")
                acao.setdefault("como", acao.get("indicador_sucesso",""))
            return plan
        except Exception as e:
            if attempt < max_retries - 1:
                # Retry real: pede ao modelo que corrija o output anterior
                retry_messages = messages + [
                    {"role": "assistant", "content": current_raw},
                    {"role": "user", "content":
                        f"O JSON retornado está inválido ({e}). "
                        "Corrija e retorne APENAS o JSON válido com os campos: "
                        "problema, objetivo, acoes (cada ação com descricao, responsavel, prazo, prioridade, indicador_sucesso)."}
                ]
                try:
                    current_raw = call_groq(retry_messages, api_key)
                except Exception:
                    break
            continue
    return {"problema": "Erro na geração do plano", "objetivo": "Tente novamente", "acoes": []}


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
# 5W2H TABLE RENDERING
# ─────────────────────────────────────────────
STATUS_OPTIONS    = ["⏳ Pendente", "🔄 Em andamento", "✅ Concluído", "❌ Cancelado"]
PRIORIDADE_OPTIONS = ["Alta", "Média", "Baixa"]

# Cores dos cabeçalhos 5W2H (fiel à imagem de referência)
TH_COLORS = {
    "what"   : ("#6B21A8", "#E9D5FF"),   # roxo
    "why"    : ("#9D174D", "#FCE7F3"),   # rosa-magenta
    "where"  : ("#BE123C", "#FFE4E6"),   # vermelho-rosa
    "when"   : ("#C2410C", "#FFEDD5"),   # laranja
    "who"    : ("#B45309", "#FEF3C7"),   # âmbar
    "how"    : ("#065F46", "#D1FAE5"),   # verde
    "howmuch": ("#0E7490", "#CFFAFE"),   # ciano
    "status" : ("#374151", "#F9FAFB"),   # cinza
}

STATUS_COLOR = {
    "⏳ Pendente"      : ("#6B7280", "#F3F4F6"),
    "🔄 Em andamento"  : ("#2563EB", "#DBEAFE"),
    "✅ Concluído"     : ("#059669", "#D1FAE5"),
    "❌ Cancelado"     : ("#DC2626", "#FEE2E2"),
}
PRIO_COLOR = {
    "Alta" : ("#DC2626", "#FEE2E2"),
    "Média": ("#D97706", "#FEF3C7"),
    "Baixa": ("#059669", "#D1FAE5"),
}


def _badge(text: str, color_map: dict, default=("#6B7280","#F3F4F6")) -> str:
    fg, bg = color_map.get(text, default)
    return (f'<span style="background:{bg};color:{fg};border:1px solid {fg}44;'
            f'border-radius:5px;padding:2px 8px;font-size:11px;font-weight:600;'
            f'white-space:nowrap;">{text}</span>')


def _th(label: str, sub: str, key: str, width: str) -> str:
    bg, fg = TH_COLORS[key]
    return (f'<th style="background:{bg};color:{fg};width:{width};min-width:{width};'
            f'max-width:{width};padding:10px 8px;text-align:center;font-size:12px;'
            f'font-weight:700;border-right:1px solid rgba(255,255,255,0.15);'
            f'border-bottom:2px solid rgba(255,255,255,0.2);vertical-align:middle;'
            f'word-break:break-word;white-space:normal;">'
            f'{label}<br><span style="font-size:10px;opacity:.75;font-weight:400;">({sub})</span></th>')


def _td(content: str, width: str, center: bool = False) -> str:
    align = "center" if center else "left"
    return (f'<td style="width:{width};min-width:{width};max-width:{width};'
            f'padding:10px 8px;vertical-align:top;text-align:{align};'
            f'font-size:12px;line-height:1.5;word-break:break-word;'
            f'white-space:normal;border-right:1px solid #2A2D3E;'
            f'border-bottom:1px solid #2A2D3E;color:#E8EAF0;">'
            f'{content}</td>')


def render_5w2h_html_table(plan: dict) -> str:
    """Gera a string HTML completa da tabela 5W2H."""
    acoes = plan.get("acoes", [])
    objetivo = plan.get("objetivo", "—")

    # Larguras fixas por coluna (total ~1100px)
    W = {"what":"220px","why":"160px","where":"110px","when":"100px",
         "who":"130px","how":"130px","howmuch":"160px","status":"110px"}

    thead = (
        "<thead><tr>"
        + _th("O quê?",   "What?",     "what",    W["what"])
        + _th("Por quê?", "Why?",      "why",     W["why"])
        + _th("Onde?",    "Where?",    "where",   W["where"])
        + _th("Quando?",  "When?",     "when",    W["when"])
        + _th("Quem?",    "Who?",      "who",     W["who"])
        + _th("Como?",    "How?",      "how",     W["how"])
        + _th("Quanto?",  "How much?", "howmuch", W["howmuch"])
        + _th("Status",   "Status",    "status",  W["status"])
        + "</tr></thead>"
    )

    rows = ""
    for i, a in enumerate(acoes):
        bg = "#16192A" if i % 2 == 0 else "#1A1D2B"
        status = a.get("status", "⏳ Pendente")
        prio   = a.get("prioridade", "Alta")
        # "Por quê" usa o objetivo geral pois o schema não tem campo why por ação
        porque = a.get("porque", objetivo)
        onde   = a.get("onde", a.get("responsavel_area", "—"))  # fallback gracioso
        como   = a.get("como", a.get("indicador_sucesso", "—"))  # fallback

        rows += f'<tr style="background:{bg};">'
        rows += _td(a.get("descricao","—"),         W["what"])
        rows += _td(porque,                          W["why"])
        rows += _td(onde,                            W["where"])
        rows += _td(a.get("prazo","—"),              W["when"],   center=True)
        rows += _td(a.get("responsavel","—"),        W["who"])
        rows += _td(como,                            W["how"])
        rows += _td(a.get("indicador_sucesso","—"),  W["howmuch"])
        rows += _td(_badge(status, STATUS_COLOR) + "<br>" + _badge(prio, PRIO_COLOR),
                    W["status"], center=True)
        rows += "</tr>"

    table_html = f"""
    <style>
      .w2h-scroll {{ overflow-x:auto; border-radius:10px; border:1px solid #2A2D3E; }}
      .w2h-tbl {{ border-collapse:collapse; table-layout:fixed; width:100%; }}
      .w2h-tbl tr:last-child td {{ border-bottom:none; }}
      .w2h-tbl td:last-child, .w2h-tbl th:last-child {{ border-right:none !important; }}
    </style>
    <div class="w2h-scroll">
      <table class="w2h-tbl">{thead}<tbody>{rows}</tbody></table>
    </div>
    """
    return table_html


def plan_to_dataframe(plan: dict) -> pd.DataFrame:
    """Converte o plano JSON em DataFrame editável."""
    acoes  = plan.get("acoes", [])
    objetivo = plan.get("objetivo", "—")
    rows = []
    for a in acoes:
        rows.append({
            "O quê?"    : a.get("descricao", ""),
            "Por quê?"  : a.get("porque", objetivo),
            "Onde?"     : a.get("onde", ""),
            "Quando?"   : a.get("prazo", ""),
            "Quem?"     : a.get("responsavel", ""),
            "Como?"     : a.get("como", ""),
            "Quanto?"   : a.get("indicador_sucesso", ""),
            "Status"    : a.get("status", "⏳ Pendente"),
            "Prioridade": a.get("prioridade", "Alta"),
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["O quê?","Por quê?","Onde?","Quando?","Quem?","Como?","Quanto?","Status","Prioridade"]
    )


def dataframe_to_acoes(df: pd.DataFrame, original_acoes: list) -> list:
    """Converte o DataFrame editado de volta para lista de ações."""
    updated = []
    for i, row in df.iterrows():
        updated.append({
            "descricao"         : row.get("O quê?", ""),
            "porque"            : row.get("Por quê?", ""),
            "onde"              : row.get("Onde?", ""),
            "prazo"             : row.get("Quando?", ""),
            "responsavel"       : row.get("Quem?", ""),
            "como"              : row.get("Como?", ""),
            "indicador_sucesso" : row.get("Quanto?", ""),
            "status"            : row.get("Status", "⏳ Pendente"),
            "prioridade"        : row.get("Prioridade", "Alta"),
        })
    return updated


def render_5w2h_card(plan: dict, plan_key: str, editable: bool = True):
    """
    Exibe a tabela 5W2H estilizada via HTML + abre data_editor ao clicar em Editar.
    Retorna o DataFrame com os dados atuais (editados ou originais).
    """
    import streamlit.components.v1 as components

    # ── Cabeçalho problema/objetivo ──
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
        <div style="width:36px;height:36px;background:linear-gradient(135deg,{COR_ACCENT},{COR_PURPLE});
             border-radius:9px;display:flex;align-items:center;justify-content:center;
             font-size:18px;flex-shrink:0;">🎯</div>
        <div>
            <div style="font-size:15px;font-weight:600;color:{COR_TEXTO};">Plano de Ação · 5W2H</div>
            <div style="font-size:11px;color:{COR_MUTED};">HSE-IT · NR-1 · Vivamente 360°</div>
        </div>
    </div>
    <div style="background:#1e1e30;border-left:3px solid {COR_PURPLE};border-radius:0 8px 8px 0;
         padding:10px 14px;margin-bottom:6px;">
        <span style="font-size:10px;color:{COR_PURPLE};font-weight:700;
              text-transform:uppercase;letter-spacing:.08em;">⚠ Problema identificado</span><br>
        <span style="font-size:13px;color:{COR_TEXTO};">{plan.get('problema','—')}</span>
    </div>
    <div style="background:#1a2a1a;border-left:3px solid {COR_VERDE};border-radius:0 8px 8px 0;
         padding:10px 14px;margin-bottom:14px;">
        <span style="font-size:10px;color:{COR_VERDE};font-weight:700;
              text-transform:uppercase;letter-spacing:.08em;">🎯 Objetivo SMART</span><br>
        <span style="font-size:13px;color:{COR_TEXTO};">{plan.get('objetivo','—')}</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Tabela HTML estilizada ──
    table_html = render_5w2h_html_table(plan)
    n_acoes = len(plan.get("acoes", []))
    components.html(table_html, height=max(140, 55 + n_acoes * 72), scrolling=False)

    # ── Modo edição via data_editor ──
    edit_toggle_key = f"edit_toggle_{plan_key}"
    if edit_toggle_key not in st.session_state:
        st.session_state[edit_toggle_key] = False

    col_btn, col_hint = st.columns([1, 4])
    with col_btn:
        label = "✏️ Editar tabela" if not st.session_state[edit_toggle_key] else "👁 Ver tabela"
        if st.button(label, key=f"toggle_edit_{plan_key}", use_container_width=True):
            st.session_state[edit_toggle_key] = not st.session_state[edit_toggle_key]
            st.rerun()
    with col_hint:
        if st.session_state[edit_toggle_key]:
            st.markdown(f'<div style="font-size:11px;color:{COR_MUTED};padding-top:8px;">'
                        f'Clique em qualquer célula para editar · Status e Prioridade têm dropdown</div>',
                        unsafe_allow_html=True)

    df = plan_to_dataframe(plan)

    if st.session_state[edit_toggle_key] and editable:
        col_config = {
            "O quê?"    : st.column_config.TextColumn("📋 O quê?",   width=220),
            "Por quê?"  : st.column_config.TextColumn("❓ Por quê?", width=160),
            "Onde?"     : st.column_config.TextColumn("📍 Onde?",    width=110),
            "Quando?"   : st.column_config.TextColumn("📅 Quando?",  width=100),
            "Quem?"     : st.column_config.TextColumn("👤 Quem?",    width=130),
            "Como?"     : st.column_config.TextColumn("⚙️ Como?",    width=130),
            "Quanto?"   : st.column_config.TextColumn("📊 Quanto?",  width=160),
            "Status"    : st.column_config.SelectboxColumn("🚦 Status",     options=STATUS_OPTIONS,    width=120),
            "Prioridade": st.column_config.SelectboxColumn("🔺 Prioridade", options=PRIORIDADE_OPTIONS, width=100),
        }
        df = st.data_editor(
            df,
            key=f"de_{plan_key}",
            column_config=col_config,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            height=min(500, 60 + n_acoes * 55),
        )

    return df


def compute_plan_progress(plan: dict) -> float:
    """Returns fraction of concluded actions."""
    acoes = plan.get("acoes", [])
    if not acoes: return 0.0
    done = sum(1 for a in acoes if a.get("status","") == "✅ Concluído")
    return done / len(acoes)


def render_plans_tab():
    """Renders the saved action plans tab."""
    plans = st.session_state.action_plans
    if not plans:
        st.markdown(f"""
        <div style="text-align:center;padding:60px 20px;color:{COR_MUTED};">
            <div style="font-size:48px;margin-bottom:16px;">📋</div>
            <div style="font-size:16px;font-weight:600;color:{COR_TEXTO};margin-bottom:8px;">Nenhum plano salvo ainda</div>
            <div style="font-size:13px;">Gere um plano de ação no chat e clique em <b>Salvar Plano</b> para acompanhá-lo aqui.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    st.markdown(f'<div class="section-title">📋 {len(plans)} plano(s) de ação salvos</div>', unsafe_allow_html=True)

    for idx, saved in enumerate(plans):
        plan = saved["plan"]
        created_at = saved.get("created_at","—")
        progress = compute_plan_progress(plan)
        n_acoes = len(plan.get("acoes",[]))
        n_done  = int(progress * n_acoes)
        prog_pct = int(progress * 100)

        with st.expander(
            f"📌 {plan.get('problema','Plano')[:80]}  ·  {prog_pct}% concluído  ·  Salvo em {created_at}",
            expanded=(idx == 0)
        ):
            plan_key = f"saved_plan_{idx}"

            # Progress bar
            st.markdown(f"""
            <div style="margin-bottom:16px;">
                <div style="display:flex;justify-content:space-between;font-size:11px;color:{COR_MUTED};margin-bottom:4px;">
                    <span>Progresso geral</span><span>{n_done}/{n_acoes} ações concluídas</span>
                </div>
                <div class="progress-bar-outer">
                    <div class="progress-bar-inner" style="width:{prog_pct}%"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Render editable 5W2H table
            edited_df = render_5w2h_card(plan, plan_key, editable=True)

            st.markdown("<br>", unsafe_allow_html=True)
            col_upd, col_del, _ = st.columns([2, 2, 5])
            with col_upd:
                if st.button("💾 Salvar alterações", key=f"update_plan_{idx}", use_container_width=True, type="primary"):
                    acoes_atualizadas = dataframe_to_acoes(edited_df, plan.get("acoes", []))
                    st.session_state.action_plans[idx]["plan"] = {**plan, "acoes": acoes_atualizadas}
                    st.success("✅ Plano atualizado!")
                    st.rerun()
            with col_del:
                if st.button("🗑️ Remover plano", key=f"del_plan_{idx}", use_container_width=True):
                    st.session_state.action_plans.pop(idx)
                    st.rerun()


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
    n_plans = len(st.session_state.action_plans)
    plans_label = f"📋 Planos de Ação" + (f"  ({n_plans})" if n_plans else "")
    col_tab1, col_tab2 = st.columns(2)
    with col_tab1:
        if st.button("💬 Chat", use_container_width=True,
                     type="primary" if st.session_state.active_tab == "chat" else "secondary"):
            st.session_state.active_tab = "chat"
            st.rerun()
    with col_tab2:
        if st.button(plans_label, use_container_width=True,
                     type="primary" if st.session_state.active_tab == "plans" else "secondary"):
            st.session_state.active_tab = "plans"
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
# TAB ROUTING
# ─────────────────────────────────────────────
if st.session_state.active_tab == "plans":
    render_plans_tab()
    st.stop()

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
for msg_idx, msg in enumerate(st.session_state.chat_history):
    if msg["role"] == "user":
        st.markdown(f'<div class="msg-user">🙋 {msg["content"]}</div>', unsafe_allow_html=True)
    else:
        content = msg["content"]
        if isinstance(content, dict):
            plan_key = f"chat_plan_{msg_idx}"
            st.markdown(f"""
            <div style="border-left:3px solid {COR_PURPLE};padding-left:12px;margin:8px 0 4px 0;">
                <span style="font-size:13px;font-weight:600;color:{COR_PURPLE};">🤖 Agente HSE-IT</span>
                <span style="font-size:11px;color:{COR_MUTED};margin-left:8px;">· Plano de Ação · 5W2H</span>
            </div>
            """, unsafe_allow_html=True)

            edited_df = render_5w2h_card(content, plan_key, editable=True)

            col_save, col_info, _ = st.columns([2, 3, 4])
            with col_save:
                if st.button("💾 Salvar Plano de Ação", key=f"save_{plan_key}",
                             use_container_width=True, type="primary"):
                    # Rebuild plan from the edited dataframe
                    acoes_atualizadas = dataframe_to_acoes(edited_df, content.get("acoes", []))
                    updated = {**content, "acoes": acoes_atualizadas}
                    st.session_state.action_plans.append({
                        "plan": updated,
                        "created_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    })
                    st.session_state.chat_history[msg_idx]["content"] = updated
                    st.success("✅ Plano salvo! Acesse em **Planos de Ação** na barra lateral.")
            with col_info:
                st.markdown(f"""
                <div style="font-size:11px;color:{COR_MUTED};padding-top:8px;">
                    ✏️ Clique em qualquer célula para editar · depois clique em Salvar
                </div>""", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
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
    last_user_idx = max(i for i, m in enumerate(st.session_state.chat_history) if m["role"] == "user")
    for i, msg in enumerate(st.session_state.chat_history):
        if msg["role"] == "user" and i == last_user_idx:
            # Sempre injeta o contexto atualizado na última pergunta do usuário
            api_messages.append({
                "role": "user",
                "content": f"{context_message}\n\nPergunta: {msg['content']}"
            })
        else:
            content = msg["content"]
            # Groq exige string em content; se for dict (plano serializado), converte para JSON
            if isinstance(content, dict):
                content = json.dumps(content, ensure_ascii=False)
            api_messages.append({"role": msg["role"], "content": content})

    with st.spinner("🧠 Analisando dados do dashboard..."):
        try:
            raw = call_groq(api_messages, GROQ_API_KEY)
            plan = validate_and_fix_plan(raw, api_messages, GROQ_API_KEY)
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
