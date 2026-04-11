"""
dashboard_ai.py — Dashboard HSE-IT · Vivamente 360°
════════════════════════════════════════════════════
Dashboard principal com IA integrada em dois contextos:

1. ANÁLISE DE GRÁFICOS / TABELAS
   Botão "🤖 Analisar" abaixo de cada visual.
   A análise é cacheada por hash (filtros + dados) — só
   regera quando os dados ou filtros mudam. Sem desperdício
   de tokens.

2. PÁGINA DE PROBLEMAS + PLANOS DE AÇÃO
   Lista automática de riscos críticos identificados nos dados.
   Para cada problema, o usuário pode gerar um plano 5W2H
   editável e salvável (mesmo modelo do agente original).

NÃO há chat livre — o agente é usado apenas nos 2 contextos acima.
"""

import hashlib
import json
import re
import requests
import traceback
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# ── Módulo compartilhado ────────────────────────────────────────────────────
from analytics import (
    DIMENSOES,
    DIMENSOES_LABEL,
    DIM_NEGATIVAS,
    NIVEIS_GERAL_ORDEM,
    NIVEIS_ORDEM,
    build_context,
    load_all_data,
)
from rag import buscar_contexto_normativo

# ═══════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Dashboard HSE-IT · NR-1",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Chave API ───────────────────────────────────────────────────────────────
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except KeyError:
    st.error("⚠️ Chave GROQ_API_KEY não encontrada em .streamlit/secrets.toml")
    st.stop()

# ═══════════════════════════════════════════════════════════════════════════
# PALETA
# ═══════════════════════════════════════════════════════════════════════════
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

RISCO_CORES = {
    "Aceitável":  COR_VERDE,
    "Moderado":   COR_AMARELO,
    "Importante": COR_LARANJA,
    "Crítico":    COR_VERMELHO,
    "Sem dados":  COR_CINZA,
}

QS_NEGATIVAS = set(range(1, 9)) | set(range(24, 28))

PLOTLY_CONFIG = dict(scrollZoom=False, doubleClick=False, displayModeBar=False)

# ═══════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════
_ss_defaults = {
    "action_plans":      [],
    "analysis_cache":    {},   # hash → texto da análise
    "open_analysis":     {},   # visual_key → bool (expander aberto?)
    "problems_cache":    None, # lista de problemas gerada
    "problems_hash":     "",   # hash dos dados quando a lista foi gerada
    "plan_generating":   {},   # problem_key → bool
    "debug_log":         [],
}
for k, v in _ss_defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ═══════════════════════════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════════════════════════
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
[data-baseweb="tab-list"] {{
    background: {COR_CARD} !important;
    border-radius: 12px;
    padding: 8px !important;
    gap: 8px !important;
    margin-bottom: 10px;
}}
[data-baseweb="tab"] {{
    background: transparent !important;
    border-radius: 8px !important;
    padding: 12px 24px !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    color: {COR_MUTED} !important;
    transition: all 0.2s;
}}
[aria-selected="true"][data-baseweb="tab"] {{
    background: {COR_BG} !important;
    color: {COR_TEXTO} !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}}
.block-container {{ padding: 1.5rem 2rem 3rem; }}

.kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 14px; margin-bottom: 2rem;
}}
.kpi-card {{
    background: {COR_CARD};
    border: 1px solid {COR_BORDA};
    border-radius: 12px;
    padding: 18px 20px;
}}
.kpi-label  {{ font-size:11px; font-weight:500; color:{COR_MUTED}; text-transform:uppercase; letter-spacing:.08em; margin-bottom:6px; }}
.kpi-value  {{ font-size:28px; font-weight:600; color:{COR_TEXTO}; line-height:1; }}
.kpi-sub    {{ font-size:12px; color:{COR_MUTED}; margin-top:4px; }}

.section-title {{
    font-size:13px; font-weight:600; color:{COR_MUTED};
    text-transform:uppercase; letter-spacing:.1em;
    margin:2rem 0 1rem;
    padding-bottom:8px;
    border-bottom:1px solid {COR_BORDA};
}}
.page-header {{
    background: linear-gradient(135deg, #1A1D27 0%, #0F1117 100%);
    border: 1px solid {COR_BORDA};
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 2rem;
}}

/* Análise box */
.ai-analysis-box {{
    background: #111827;
    border: 1px solid {COR_PURPLE}44;
    border-left: 3px solid {COR_PURPLE};
    border-radius: 0 12px 12px 12px;
    padding: 16px 20px;
    margin-top: 8px;
    font-size: 13px;
    line-height: 1.75;
    color: {COR_TEXTO};
}}
.ai-analysis-box strong {{ color: {COR_ACCENT}; }}

/* Problema card */
.problem-card {{
    background: {COR_CARD};
    border: 1px solid {COR_BORDA};
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 14px;
    transition: border-color .2s;
}}
.problem-card:hover {{ border-color: {COR_VERMELHO}55; }}

/* 5W2H badges */
.badge-alta    {{ background:{COR_VERMELHO}22; color:{COR_VERMELHO}; border:1px solid {COR_VERMELHO}44; border-radius:6px; padding:2px 8px; font-size:11px; font-weight:600; }}
.badge-media   {{ background:{COR_AMARELO}22;  color:{COR_AMARELO};  border:1px solid {COR_AMARELO}44;  border-radius:6px; padding:2px 8px; font-size:11px; font-weight:600; }}
.badge-baixa   {{ background:{COR_VERDE}22;    color:{COR_VERDE};    border:1px solid {COR_VERDE}44;    border-radius:6px; padding:2px 8px; font-size:11px; font-weight:600; }}

/* Progress bar */
.progress-bar-outer {{ background:{COR_BORDA}; border-radius:4px; height:6px; margin:10px 0 4px; }}
.progress-bar-inner {{ height:100%; border-radius:4px; background:linear-gradient(90deg,{COR_ACCENT},{COR_PURPLE}); }}

@media (max-width: 768px) {{
    .block-container {{ padding:1rem .75rem 2rem !important; }}
    .kpi-grid {{ grid-template-columns: repeat(2,1fr) !important; gap:10px !important; }}
    .kpi-value {{ font-size:22px !important; }}
}}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# HELPERS — helpers gerais
# ═══════════════════════════════════════════════════════════════════════════

def cor_nivel(nivel: str) -> str:
    return RISCO_CORES.get(nivel, COR_CINZA)


def nivel_geral_para_cor(nivel: str) -> str:
    return {"Aceitável": COR_VERDE, "Moderado": COR_AMARELO,
            "Importante": COR_LARANJA, "Crítico": COR_VERMELHO}.get(nivel, COR_CINZA)


def classificar_NR(nr: float) -> str:
    if nr >= 13: return "Crítico"
    if nr >= 9:  return "Importante"
    if nr >= 5:  return "Moderado"
    return "Aceitável"


def score_para_classificacao(score: float, dim: str) -> str:
    neg = dim in DIM_NEGATIVAS
    if neg:
        if score >= 3.1: return "Alto Risco"
        if score >= 2.1: return "Risco Moderado"
        if score >= 1.1: return "Risco Médio"
        return "Baixo Risco"
    else:
        if score <= 1.0: return "Alto Risco"
        if score <= 2.0: return "Risco Moderado"
        if score <= 3.0: return "Risco Médio"
        return "Baixo Risco"


def score_para_P(score: float, dim: str) -> int:
    if pd.isna(score): return 1
    if dim in DIM_NEGATIVAS:
        if score >= 3.1: return 4
        if score >= 2.1: return 3
        if score >= 1.1: return 2
        return 1
    else:
        if score <= 1.0: return 4
        if score <= 2.0: return 3
        if score <= 3.0: return 2
        return 1


def plotly_layout(fig, height=380, margin=None):
    m = margin or dict(l=48, r=24, t=30, b=20)
    fig.update_layout(
        height=height, margin=m,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans", color=COR_TEXTO, size=12),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=COR_BORDA, font=dict(size=11)),
        xaxis=dict(gridcolor=COR_BORDA, zerolinecolor=COR_BORDA),
        yaxis=dict(gridcolor=COR_BORDA, zerolinecolor=COR_BORDA),
        dragmode=False,
    )
    return fig


def _nr_row_color(val):
    try: v = float(val)
    except: return ""
    if v >= 13: return f"background-color:rgba(214,59,59,.35);color:{COR_TEXTO}"
    if v >= 9:  return f"background-color:rgba(232,98,26,.30);color:{COR_TEXTO}"
    if v >= 5:  return f"background-color:rgba(245,166,35,.25);color:{COR_TEXTO}"
    return f"background-color:rgba(45,158,117,.20);color:{COR_TEXTO}"


def _perc_row_color(val):
    try: v = float(str(val).replace("%",""))
    except: return ""
    if v >= 60: return f"background-color:rgba(214,59,59,.30);color:{COR_TEXTO}"
    if v >= 35: return f"background-color:rgba(232,98,26,.25);color:{COR_TEXTO}"
    if v >= 15: return f"background-color:rgba(245,166,35,.20);color:{COR_TEXTO}"
    return f"background-color:rgba(45,158,117,.15);color:{COR_TEXTO}"


def _class_row_color(val):
    return {
        "Alto Risco":     f"background-color:rgba(214,59,59,.35);color:{COR_TEXTO}",
        "Risco Moderado": f"background-color:rgba(232,98,26,.30);color:{COR_TEXTO}",
        "Risco Médio":    f"background-color:rgba(245,166,35,.25);color:{COR_TEXTO}",
        "Baixo Risco":    f"background-color:rgba(45,158,117,.20);color:{COR_TEXTO}",
    }.get(str(val), "")


def reaplicar_agg(df, col, rename):
    if df.empty: return pd.DataFrame()
    g = df.groupby(col).agg(
        n_colaboradores=(col, "count"),
        IGRP=("IGRP", "mean"),
        NR_geral=("NR_geral", "mean"),
        **{f"score_{d}": (f"score_{d}", "mean") for d in DIMENSOES if f"score_{d}" in df.columns},
        **{f"NR_{d}":    (f"NR_{d}",    "mean") for d in DIMENSOES if f"NR_{d}"    in df.columns},
        perc_critico   =("risco_geral", lambda x: (x == "Crítico").mean()),
        perc_importante=("risco_geral", lambda x: (x == "Importante").mean()),
        perc_moderado  =("risco_geral", lambda x: (x == "Moderado").mean()),
        perc_aceitavel =("risco_geral", lambda x: (x == "Aceitável").mean()),
        perc_risco_alto=("risco_geral", lambda x: x.isin(["Crítico","Importante"]).mean()),
    ).reset_index().rename(columns={col: rename})
    g["classificacao"] = g["NR_geral"].apply(classificar_NR)
    return g.sort_values(["perc_risco_alto","NR_geral"], ascending=False)


# ═══════════════════════════════════════════════════════════════════════════
# CACHE DE ANÁLISES — hash-based, persiste no session_state
# ═══════════════════════════════════════════════════════════════════════════

def _make_hash(data: dict) -> str:
    """
    Gera hash SHA-256 de um dict serializável.
    Usado para detectar se os dados/filtros mudaram desde a última análise.
    """
    raw = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def get_cached_analysis(visual_key: str) -> str | None:
    """Retorna análise cacheada para visual_key, ou None se não existir."""
    return st.session_state.analysis_cache.get(visual_key)


def set_cached_analysis(visual_key: str, text: str):
    st.session_state.analysis_cache[visual_key] = text


def invalidate_analysis(visual_key: str):
    st.session_state.analysis_cache.pop(visual_key, None)


# ═══════════════════════════════════════════════════════════════════════════
# GROQ API
# ═══════════════════════════════════════════════════════════════════════════

SYSTEM_ANALYSIS = """Você é o Agente HSE-IT — especialista em saúde mental ocupacional, riscos psicossociais e NR-1.
Recebe dados de um gráfico ou tabela do dashboard Vivamente 360° e gera uma análise concisa, técnica e acionável.

REGRA DE FORMATO: responda SEMPRE com JSON:
{
  "tipo": "analise",
  "titulo": "título curto da análise (máx 10 palavras)",
  "resumo": "1 frase de diagnóstico direto",
  "insights": ["insight 1 com dado específico", "insight 2", "insight 3"],
  "alertas": ["alerta crítico se existir — pode ser lista vazia"],
  "recomendacoes": ["ação imediata recomendada 1", "ação 2"]
}
Seja direto. Cite números dos dados. Máximo 5 itens por lista."""

SYSTEM_PLAN = """Você é o Agente HSE-IT — especialista em saúde mental ocupacional, riscos psicossociais, NR-1 e ISO 45003.
Recebe um problema identificado nos dados e gera um plano de ação 5W2H completo.

REGRA DE FORMATO: responda SEMPRE com JSON válido:
{
  "tipo": "plano_acao",
  "problema": "descrição curta do problema",
  "objetivo": "objetivo SMART do plano",
  "acoes": [
    {
      "descricao": "O quê?",
      "porque": "Por quê?",
      "onde": "Onde?",
      "responsavel": "Quem?",
      "prazo": "Quando?",
      "como": "Como?",
      "prioridade": "Alta | Média | Baixa",
      "indicador_sucesso": "Quanto? (métrica mensurável)",
      "status": "⏳ Pendente"
    }
  ]
}
Gere entre 3 e 5 ações. Seja específico e acionável."""


def call_groq(system: str, user_content: str) -> str:
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "llama-3.3-70b-versatile",
            "max_tokens": 1500,
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user_content},
            ],
        },
        timeout=60,
    )
    if resp.status_code != 200:
        try:    err = resp.json().get("error", {}).get("message", resp.text)
        except: err = resp.text
        raise Exception(f"Groq API {resp.status_code}: {err}")
    return resp.json()["choices"][0]["message"]["content"]


def parse_json_response(raw: str) -> dict:
    try:
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        return json.loads(m.group(0)) if m else {"tipo": "analise", "resumo": raw}
    except Exception:
        return {"tipo": "analise", "resumo": raw}


# ═══════════════════════════════════════════════════════════════════════════
# COMPONENTE: BOTÃO "🤖 ANALISAR" + CAIXA DE ANÁLISE
# ═══════════════════════════════════════════════════════════════════════════

def render_ai_analysis_button(
    visual_key: str,
    data_for_hash: dict,
    prompt_context: str,
    label: str = "🤖 Analisar com IA",
):
    """
    Renderiza o botão de análise IA abaixo de qualquer gráfico/tabela.

    visual_key      : identificador único do visual (ex: "heatmap_setor")
    data_for_hash   : dict com os dados/stats usados no visual — define
                      quando a análise precisa ser regerada
    prompt_context  : texto descrevendo o visual e seus dados para o modelo
    label           : texto do botão
    """
    # Chave de cache = visual_key + hash dos dados
    current_hash = _make_hash(data_for_hash)
    cache_key    = f"{visual_key}_{current_hash}"

    # Se existir cache para o hash atual, usa; se dados mudaram, invalida
    cached = get_cached_analysis(cache_key)

    col_btn, col_status, _ = st.columns([2, 3, 4])

    with col_btn:
        btn_label = "🔄 Regerado (dados atualizados)" if cached else label
        clicked = st.button(
            label if not cached else "✅ Ver análise IA",
            key=f"ai_btn_{visual_key}",
            use_container_width=True,
        )

    with col_status:
        if cached:
            st.markdown(
                f'<div style="font-size:11px;color:{COR_VERDE};padding-top:8px;">'
                f'✅ Análise disponível · hash <code>{current_hash}</code></div>',
                unsafe_allow_html=True,
            )

    # Abre/fecha expander no click
    open_key = f"open_{visual_key}"
    if clicked:
        st.session_state.open_analysis[open_key] = not st.session_state.open_analysis.get(open_key, False)

    if st.session_state.open_analysis.get(open_key, False):
        with st.expander("🤖 Análise gerada pela IA", expanded=True):
            if cached:
                _render_analysis_box(cached)
            else:
                with st.spinner("🧠 Gerando análise..."):
                    try:
                        rag_ctx = buscar_contexto_normativo(prompt_context[:300])
                        full_prompt = f"{prompt_context}\n\n{rag_ctx}" if rag_ctx else prompt_context
                        raw    = call_groq(SYSTEM_ANALYSIS, full_prompt)
                        result = parse_json_response(raw)
                        set_cached_analysis(cache_key, result)
                        _render_analysis_box(result)
                    except Exception as e:
                        st.error(f"❌ Erro ao gerar análise: {e}")


def _render_analysis_box(result: dict):
    """Renderiza o dict de análise estruturada."""
    if isinstance(result, str):
        st.markdown(result)
        return

    titulo = result.get("titulo", "Análise IA")
    resumo = result.get("resumo", "")
    insights = result.get("insights", [])
    alertas  = result.get("alertas", [])
    recs     = result.get("recomendacoes", [])

    st.markdown(f"**{titulo}**")
    if resumo:
        st.markdown(
            f'<div style="background:#1a2030;border-left:3px solid {COR_ACCENT};'
            f'border-radius:0 8px 8px 0;padding:10px 14px;margin-bottom:12px;'
            f'font-size:13px;color:{COR_TEXTO};">{resumo}</div>',
            unsafe_allow_html=True,
        )

    if insights:
        st.markdown(f'<div style="font-size:11px;font-weight:600;color:{COR_MUTED};'
                    f'text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px;">'
                    f'📊 Insights</div>', unsafe_allow_html=True)
        for ins in insights:
            st.markdown(
                f'<div style="border-left:2px solid {COR_ACCENT};padding:5px 10px;'
                f'margin-bottom:4px;font-size:12px;color:{COR_TEXTO};">{ins}</div>',
                unsafe_allow_html=True,
            )

    if alertas:
        st.markdown(f'<div style="font-size:11px;font-weight:600;color:{COR_VERMELHO};'
                    f'text-transform:uppercase;letter-spacing:.08em;margin:10px 0 6px;">'
                    f'⚠️ Alertas</div>', unsafe_allow_html=True)
        for alerta in alertas:
            st.markdown(
                f'<div style="border-left:2px solid {COR_VERMELHO};padding:5px 10px;'
                f'margin-bottom:4px;font-size:12px;color:{COR_TEXTO};">{alerta}</div>',
                unsafe_allow_html=True,
            )

    if recs:
        st.markdown(f'<div style="font-size:11px;font-weight:600;color:{COR_VERDE};'
                    f'text-transform:uppercase;letter-spacing:.08em;margin:10px 0 6px;">'
                    f'✅ Recomendações</div>', unsafe_allow_html=True)
        for rec in recs:
            st.markdown(
                f'<div style="border-left:2px solid {COR_VERDE};padding:5px 10px;'
                f'margin-bottom:4px;font-size:12px;color:{COR_TEXTO};">{rec}</div>',
                unsafe_allow_html=True,
            )


# ═══════════════════════════════════════════════════════════════════════════
# 5W2H PLAN RENDERING (reutilizado do agente original)
# ═══════════════════════════════════════════════════════════════════════════

STATUS_OPTIONS     = ["⏳ Pendente", "🔄 Em andamento", "✅ Concluído", "❌ Cancelado"]
PRIORIDADE_OPTIONS = ["Alta", "Média", "Baixa"]

TH_COLORS = {
    "what"   : ("#6B21A8","#E9D5FF"),
    "why"    : ("#9D174D","#FCE7F3"),
    "where"  : ("#BE123C","#FFE4E6"),
    "when"   : ("#C2410C","#FFEDD5"),
    "who"    : ("#B45309","#FEF3C7"),
    "how"    : ("#065F46","#D1FAE5"),
    "howmuch": ("#0E7490","#CFFAFE"),
    "status" : ("#374151","#F9FAFB"),
}

STATUS_COLOR = {
    "⏳ Pendente"    : ("#6B7280","#F3F4F6"),
    "🔄 Em andamento": ("#2563EB","#DBEAFE"),
    "✅ Concluído"   : ("#059669","#D1FAE5"),
    "❌ Cancelado"   : ("#DC2626","#FEE2E2"),
}
PRIO_COLOR = {
    "Alta" : ("#DC2626","#FEE2E2"),
    "Média": ("#D97706","#FEF3C7"),
    "Baixa": ("#059669","#D1FAE5"),
}


def _badge(text, color_map, default=("#6B7280","#F3F4F6")):
    fg, bg = color_map.get(text, default)
    return (f'<span style="background:{bg};color:{fg};border:1px solid {fg}44;'
            f'border-radius:5px;padding:2px 8px;font-size:11px;font-weight:600;">{text}</span>')


def _th(label, sub, key, width):
    bg, fg = TH_COLORS[key]
    return (f'<th style="background:{bg};color:{fg};width:{width};padding:10px 8px;'
            f'text-align:center;font-size:12px;font-weight:700;'
            f'border-right:1px solid rgba(255,255,255,.15);'
            f'border-bottom:2px solid rgba(255,255,255,.2);vertical-align:middle;">'
            f'{label}<br><span style="font-size:10px;opacity:.75;font-weight:400;">({sub})</span></th>')


def _td(content, width, center=False):
    align = "center" if center else "left"
    return (f'<td style="width:{width};padding:10px 8px;vertical-align:top;text-align:{align};'
            f'font-size:12px;line-height:1.5;word-break:break-word;'
            f'border-right:1px solid #2A2D3E;border-bottom:1px solid #2A2D3E;color:#E8EAF0;">'
            f'{content}</td>')


def render_5w2h_html(plan: dict) -> str:
    acoes   = plan.get("acoes", [])
    objetivo = plan.get("objetivo", "—")
    W = {"what":"220px","why":"160px","where":"110px","when":"100px",
         "who":"130px","how":"130px","howmuch":"160px","status":"110px"}

    thead = ("<thead><tr>"
             + _th("O quê?","What?","what",W["what"])
             + _th("Por quê?","Why?","why",W["why"])
             + _th("Onde?","Where?","where",W["where"])
             + _th("Quando?","When?","when",W["when"])
             + _th("Quem?","Who?","who",W["who"])
             + _th("Como?","How?","how",W["how"])
             + _th("Quanto?","How much?","howmuch",W["howmuch"])
             + _th("Status","Status","status",W["status"])
             + "</tr></thead>")

    rows = ""
    for i, a in enumerate(acoes):
        bg = "#16192A" if i % 2 == 0 else "#1A1D2B"
        rows += f'<tr style="background:{bg};">'
        rows += _td(a.get("descricao","—"),       W["what"])
        rows += _td(a.get("porque", objetivo),     W["why"])
        rows += _td(a.get("onde","—"),             W["where"])
        rows += _td(a.get("prazo","—"),            W["when"],  True)
        rows += _td(a.get("responsavel","—"),      W["who"])
        rows += _td(a.get("como","—"),             W["how"])
        rows += _td(a.get("indicador_sucesso","—"),W["howmuch"])
        rows += _td(_badge(a.get("status","⏳ Pendente"), STATUS_COLOR) + "<br>"
                    + _badge(a.get("prioridade","Alta"), PRIO_COLOR),
                    W["status"], True)
        rows += "</tr>"

    return f"""
    <style>
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      body {{ background: transparent; overflow-y: auto; }}
      .w2h-s {{ overflow-x: auto; border-radius: 10px; border: 1px solid #2A2D3E; }}
      .w2h-t {{ border-collapse: collapse; table-layout: fixed; width: 100%; }}
      .w2h-t tr:last-child td {{ border-bottom: none; }}
      .w2h-t td:last-child, .w2h-t th:last-child {{ border-right: none !important; }}
    </style>
    <div class="w2h-s"><table class="w2h-t">{thead}<tbody>{rows}</tbody></table></div>
    """


def plan_to_df(plan: dict) -> pd.DataFrame:
    objetivo = plan.get("objetivo","—")
    rows = []
    for a in plan.get("acoes", []):
        rows.append({
            "O quê?"    : a.get("descricao",""),
            "Por quê?"  : a.get("porque", objetivo),
            "Onde?"     : a.get("onde",""),
            "Quando?"   : a.get("prazo",""),
            "Quem?"     : a.get("responsavel",""),
            "Como?"     : a.get("como",""),
            "Quanto?"   : a.get("indicador_sucesso",""),
            "Status"    : a.get("status","⏳ Pendente"),
            "Prioridade": a.get("prioridade","Alta"),
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["O quê?","Por quê?","Onde?","Quando?","Quem?","Como?","Quanto?","Status","Prioridade"])


def df_to_acoes(df: pd.DataFrame) -> list:
    return [{
        "descricao"        : r.get("O quê?",""),
        "porque"           : r.get("Por quê?",""),
        "onde"             : r.get("Onde?",""),
        "prazo"            : r.get("Quando?",""),
        "responsavel"      : r.get("Quem?",""),
        "como"             : r.get("Como?",""),
        "indicador_sucesso": r.get("Quanto?",""),
        "status"           : r.get("Status","⏳ Pendente"),
        "prioridade"       : r.get("Prioridade","Alta"),
    } for _, r in df.iterrows()]


def compute_progress(plan: dict) -> float:
    acoes = plan.get("acoes",[])
    if not acoes: return 0.0
    return sum(1 for a in acoes if a.get("status","") == "✅ Concluído") / len(acoes)


def render_plan_card(plan: dict, plan_key: str, editable: bool = True):
    """Renderiza cabeçalho + tabela 5W2H + data_editor opcional."""
    import streamlit.components.v1 as components

    st.markdown(f"""
    <div style="background:#1e1e30;border-left:3px solid {COR_PURPLE};border-radius:0 8px 8px 0;
         padding:10px 14px;margin-bottom:6px;">
        <span style="font-size:10px;color:{COR_PURPLE};font-weight:700;text-transform:uppercase;">⚠ Problema</span><br>
        <span style="font-size:13px;color:{COR_TEXTO};">{plan.get("problema","—")}</span>
    </div>
    <div style="background:#1a2a1a;border-left:3px solid {COR_VERDE};border-radius:0 8px 8px 0;
         padding:10px 14px;margin-bottom:14px;">
        <span style="font-size:10px;color:{COR_VERDE};font-weight:700;text-transform:uppercase;">🎯 Objetivo SMART</span><br>
        <span style="font-size:13px;color:{COR_TEXTO};">{plan.get("objetivo","—")}</span>
    </div>
    """, unsafe_allow_html=True)

    n_acoes = len(plan.get("acoes",[]))
    # 120px de cabeçalho fixo + 110px por linha (folga para texto que quebra em múltiplas linhas).
    # scrolling=True garante que, mesmo que o cálculo seja conservador, nada some.
    components.html(render_5w2h_html(plan), height=max(200, 120 + n_acoes * 110), scrolling=True)

    toggle_key = f"edit_toggle_{plan_key}"
    if toggle_key not in st.session_state:
        st.session_state[toggle_key] = False

    col_btn, col_hint = st.columns([1, 4])
    with col_btn:
        lbl = "✏️ Editar" if not st.session_state[toggle_key] else "👁 Ver tabela"
        if st.button(lbl, key=f"toggle_{plan_key}", use_container_width=True):
            st.session_state[toggle_key] = not st.session_state[toggle_key]
            st.rerun()
    with col_hint:
        if st.session_state[toggle_key]:
            st.markdown(f'<div style="font-size:11px;color:{COR_MUTED};padding-top:8px;">'
                        f'Edite células · Status/Prioridade têm dropdown</div>', unsafe_allow_html=True)

    df = plan_to_df(plan)
    if st.session_state[toggle_key] and editable:
        col_cfg = {
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
        df = st.data_editor(df, key=f"de_{plan_key}", column_config=col_cfg,
                            use_container_width=True, hide_index=True, num_rows="fixed",
                            height=min(500, 60 + n_acoes * 55))
    return df


# ═══════════════════════════════════════════════════════════════════════════
# CARGA DE DADOS
# ═══════════════════════════════════════════════════════════════════════════
@st.cache_data
def _load():
    return load_all_data()

base, setor, cargo, unidade = _load()

# ═══════════════════════════════════════════════════════════════════════════
# SIDEBAR — filtros
# ═══════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center;padding:25px 0 15px;border-bottom:1px solid {COR_BORDA};">
        <h2 style="margin:0;font-size:22px;color:{COR_VERDE};">🧠 HSE-IT</h2>
        <p style="margin:4px 0 0;font-size:12px;color:{COR_MUTED};">Vivamente 360° · NR-1</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 👥 Total de Colaboradores")
    total_colaboradores = st.number_input(
        "Total cadastrado", min_value=1,
        value=st.session_state.get("total_colab", 1),
        step=1, key="total_colab",
    )

    st.markdown("---")
    st.markdown("### 🔍 Filtros")
    empresas_disp = sorted(base["Empresa"].dropna().unique())
    sel_empresa   = st.multiselect("Empresa", empresas_disp, default=empresas_disp, key="f_empresa")

    setores_disp  = sorted(base[base["Empresa"].isin(sel_empresa)]["Informe seu setor / departamento."].dropna().unique())
    sel_setor     = st.multiselect("Setor", setores_disp, default=setores_disp, key="f_setor")

    cargos_disp   = sorted(base[base["Informe seu setor / departamento."].isin(sel_setor)]["Informe seu cargo"].dropna().unique())
    sel_cargo     = st.multiselect("Cargo", cargos_disp, default=cargos_disp, key="f_cargo")

    top_n = st.slider("Top N (rankings)", 3, 10, 5)

    st.markdown("---")
    st.markdown(f'<div style="font-size:11px;color:{COR_MUTED};">Análises cacheadas: '
                f'<b>{len(st.session_state.analysis_cache)}</b> | '
                f'Planos salvos: <b>{len(st.session_state.action_plans)}</b></div>',
                unsafe_allow_html=True)
    if st.button("🗑 Limpar cache de análises", use_container_width=True):
        st.session_state.analysis_cache = {}
        st.session_state.open_analysis  = {}
        st.rerun()

# ═══════════════════════════════════════════════════════════════════════════
# FILTRAR BASE + AGREGAR
# ═══════════════════════════════════════════════════════════════════════════
base_f = base[
    base["Empresa"].isin(sel_empresa) &
    base["Informe seu setor / departamento."].isin(sel_setor) &
    base["Informe seu cargo"].isin(sel_cargo)
].copy()

for d in DIMENSOES:
    col_score = f"score_{d}"
    col_class = f"class_{d}"
    if col_score in base_f.columns and col_class not in base_f.columns:
        base_f[col_class] = base_f[col_score].apply(
            lambda x, _d=d: score_para_classificacao(x, _d) if pd.notna(x) else "Sem dados"
        )

setor_f   = reaplicar_agg(base_f, "Informe seu setor / departamento.", "Setor")
cargo_f   = reaplicar_agg(base_f, "Informe seu cargo", "Cargo")

n_total      = len(base_f)
nr_medio     = base_f["NR_geral"].mean() if n_total else 0
perc_alto    = base_f["risco_geral"].isin(["Crítico","Importante"]).mean() * 100 if n_total else 0
perc_critico = (base_f["risco_geral"] == "Crítico").mean() * 100 if n_total else 0

# Hash do estado atual dos dados (detecta mudanças de filtro ou dados novos)
DADOS_HASH = _make_hash({
    "n": n_total,
    "nr": round(nr_medio, 3),
    "empresa": sorted(sel_empresa),
    "setor": sorted(sel_setor),
    "cargo": sorted(sel_cargo),
})

# ═══════════════════════════════════════════════════════════════════════════
# HEADER + KPIs
# ═══════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="page-header">
  <h1 style="margin:0;font-size:22px;">🧠 Dashboard HSE-IT · Riscos Psicossociais</h1>
  <p style="margin:4px 0 0;font-size:13px;color:{COR_MUTED};">
      Vivamente 360° · NR-1 · {n_total} respondentes
  </p>
</div>
""", unsafe_allow_html=True)

perc_engaj = min(n_total / total_colaboradores * 100, 100.0) if total_colaboradores else 0

st.markdown(f"""
<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-label">Respondentes</div>
    <div class="kpi-value">{n_total:,}</div>
    <div class="kpi-sub">no filtro atual</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Engajamento</div>
    <div class="kpi-value" style="color:{'#2D9E75' if perc_engaj>=70 else '#F5A623' if perc_engaj>=50 else '#D63B3B'};">{perc_engaj:.1f}%</div>
    <div class="kpi-sub">de {total_colaboradores:,} cadastrados</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">NR Geral Médio</div>
    <div class="kpi-value">{nr_medio:.1f}</div>
    <div class="kpi-sub">escala 1–16</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Em Risco Alto/Crítico</div>
    <div class="kpi-value" style="color:{COR_LARANJA};">{perc_alto:.1f}%</div>
    <div class="kpi-sub">Importante + Crítico</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Em Risco Crítico</div>
    <div class="kpi-value" style="color:{COR_VERMELHO};">{perc_critico:.1f}%</div>
    <div class="kpi-sub">NR ≥ 13</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# TABS PRINCIPAIS
# ═══════════════════════════════════════════════════════════════════════════
tabs = st.tabs([
    "📊 Visão Geral",
    "🌡️ Heatmap",
    "📐 Por Dimensão",
    "📋 PGR",
    "🚨 Problemas & Planos",
])

# ══════════════════════════════════════════════════════════════════════════
# TAB 1 — VISÃO GERAL
# ══════════════════════════════════════════════════════════════════════════
with tabs[0]:

    # ── Distribuição de risco ────────────────────────────────────────────
    st.markdown('<div class="section-title">Distribuição de risco global</div>', unsafe_allow_html=True)

    dist_risco = base_f["risco_geral"].value_counts().reindex(NIVEIS_GERAL_ORDEM, fill_value=0)

    col_pizza, col_barra = st.columns(2)
    with col_pizza:
        fig_p = go.Figure(go.Pie(
            labels=dist_risco.index, values=dist_risco.values,
            marker=dict(colors=[nivel_geral_para_cor(n) for n in dist_risco.index],
                        line=dict(color=COR_BG, width=2)),
            hole=0.55, textinfo="percent",
            textfont=dict(size=13, color=COR_TEXTO),
        ))
        fig_p.update_layout(
            annotations=[dict(text=f"<b>{n_total}</b><br>pessoas",
                              x=0.5, y=0.5, font=dict(size=14, color=COR_TEXTO), showarrow=False)],
            showlegend=True,
        )
        plotly_layout(fig_p, height=320)
        st.plotly_chart(fig_p, use_container_width=True, config=PLOTLY_CONFIG)

    with col_barra:
        fig_b = go.Figure()
        for nivel in NIVEIS_GERAL_ORDEM:
            cnt = dist_risco.get(nivel, 0)
            pct = cnt / n_total * 100 if n_total else 0
            fig_b.add_trace(go.Bar(
                x=[nivel], y=[cnt], name=nivel,
                marker_color=nivel_geral_para_cor(nivel),
                marker_line_width=0,
                text=[f"{pct:.1f}%<br>({cnt})"],
                textposition="outside", textfont=dict(size=11, color=COR_TEXTO),
            ))
        fig_b.update_layout(showlegend=False, bargap=0.35,
                             xaxis=dict(title=""),
                             yaxis=dict(title="Nº trabalhadores", gridcolor=COR_BORDA))
        plotly_layout(fig_b, height=320)
        st.plotly_chart(fig_b, use_container_width=True, config=PLOTLY_CONFIG)

    # ── Botão IA — distribuição de risco ─────────────────────────────────
    dist_data = {n: int(v) for n, v in dist_risco.items()}
    render_ai_analysis_button(
        visual_key   = "distribuicao_risco",
        data_for_hash= {"dist": dist_data, "n": n_total, "hash": DADOS_HASH},
        prompt_context= (
            f"GRÁFICO: Distribuição de risco global\n"
            f"N respondentes: {n_total}\n"
            f"Distribuição: {dist_data}\n"
            f"NR médio: {nr_medio:.2f}\n"
            f"Filtros ativos — Empresa: {sel_empresa}, Setor: {sel_setor}, Cargo: {sel_cargo}\n"
            f"Analise a distribuição de risco, destaque alertas e faça recomendações práticas."
        ),
        label="🤖 Analisar distribuição de risco",
    )

    st.markdown('<hr style="border-color:#2A2D3E;margin:2rem 0;">', unsafe_allow_html=True)

    # ── Score por dimensão ────────────────────────────────────────────────
    st.markdown('<div class="section-title">Score médio por dimensão</div>', unsafe_allow_html=True)

    scores_dim = {}
    for d in DIMENSOES:
        col_s = f"score_{d}"
        scores_dim[d] = base_f[col_s].mean() if col_s in base_f.columns else 0

    labels_dim = [DIMENSOES_LABEL[d] for d in DIMENSOES]
    vals_dim   = [round(scores_dim[d], 3) for d in DIMENSOES]
    cores_dim  = [cor_nivel(score_para_classificacao(scores_dim[d], d)) for d in DIMENSOES]

    fig_dim = go.Figure()
    fig_dim.add_trace(go.Bar(
        x=vals_dim, y=labels_dim, orientation="h",
        marker_color=cores_dim, marker_line_width=0,
        text=[f"{v:.2f}" for v in vals_dim],
        textposition="outside", textfont=dict(size=12, color=COR_TEXTO),
    ))
    fig_dim.add_vline(x=2, line_dash="dot", line_color=COR_MUTED, line_width=1)
    fig_dim.update_layout(xaxis=dict(range=[0, 4.5], title="Score médio (0–4)", gridcolor=COR_BORDA),
                          yaxis=dict(title=""))
    plotly_layout(fig_dim, height=360)
    st.plotly_chart(fig_dim, use_container_width=True, config=PLOTLY_CONFIG)

    render_ai_analysis_button(
        visual_key   = "score_dimensoes",
        data_for_hash= {"scores": {d: round(v, 3) for d, v in scores_dim.items()}, "hash": DADOS_HASH},
        prompt_context= (
            f"GRÁFICO: Score médio por dimensão HSE-IT\n"
            + "\n".join(f"- {DIMENSOES_LABEL[d]}: {scores_dim[d]:.2f} "
                        f"({score_para_classificacao(scores_dim[d], d)})"
                        for d in DIMENSOES)
            + f"\nDimensões negativas (alto = pior): Demandas, Relacionamentos.\n"
            f"Analise quais dimensões estão mais críticas e o que isso implica para a saúde dos trabalhadores."
        ),
        label="🤖 Analisar scores por dimensão",
    )


# ══════════════════════════════════════════════════════════════════════════
# TAB 2 — HEATMAP
# ══════════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.markdown('<div class="section-title">Heatmap — NR por Dimensão</div>', unsafe_allow_html=True)

    visao_hm = st.radio("Agrupar por:", ["Setor","Cargo"], horizontal=True, key="hm_visao")
    df_hm_src = setor_f if visao_hm == "Setor" else cargo_f
    col_hm    = visao_hm

    if df_hm_src is not None and not df_hm_src.empty:
        cols_nr_hm = [f"NR_{d}" for d in DIMENSOES if f"NR_{d}" in df_hm_src.columns]
        labels_hm  = [DIMENSOES_LABEL[d] for d in DIMENSOES if f"NR_{d}" in df_hm_src.columns]

        df_hm = df_hm_src.nlargest(min(20, len(df_hm_src)), "NR_geral")
        z_hm  = df_hm[cols_nr_hm].values
        y_hm  = df_hm[col_hm].tolist()

        fig_hm = go.Figure(go.Heatmap(
            z=z_hm, x=labels_hm, y=y_hm,
            text=[[f"{v:.1f}" for v in row] for row in z_hm],
            texttemplate="%{text}",
            textfont=dict(size=11, color=COR_TEXTO),
            colorscale=[[0., COR_VERDE],[.33, COR_AMARELO],[.66, COR_LARANJA],[1., COR_VERMELHO]],
            zmin=1, zmax=16,
            colorbar=dict(
                tickvals=[1,4,8,12,16], ticktext=["1","4","8","12","16"],
                tickfont=dict(color=COR_TEXTO, size=11),
                title=dict(text="NR", font=dict(color=COR_TEXTO)),
                bgcolor="rgba(0,0,0,0)", bordercolor=COR_BORDA,
            ),
        ))
        fig_hm.update_layout(
            xaxis=dict(title="", tickangle=-30, side="top"),
            yaxis=dict(title="", autorange="reversed"),
        )
        plotly_layout(fig_hm, height=max(400, len(y_hm)*32+80))
        st.plotly_chart(fig_hm, use_container_width=True, config=PLOTLY_CONFIG)

        # Resumo para o prompt
        top3 = df_hm.head(3)
        top3_txt = "\n".join(
            f"- {row[col_hm]}: NR={row['NR_geral']:.2f} ({row.get('classificacao','?')})"
            for _, row in top3.iterrows()
        )

        render_ai_analysis_button(
            visual_key   = f"heatmap_{visao_hm.lower()}",
            data_for_hash= {
                "visao": visao_hm,
                "top_grupos": top3[col_hm].tolist(),
                "top_nr":     top3["NR_geral"].round(2).tolist(),
                "hash":        DADOS_HASH,
            },
            prompt_context= (
                f"HEATMAP: NR por Dimensão — agrupado por {visao_hm}\n"
                f"Top 3 {visao_hm}s mais críticos:\n{top3_txt}\n"
                f"Dimensões disponíveis: {', '.join(labels_hm)}\n"
                f"Analise os padrões de risco, identifique clusters críticos e recomende prioridades de intervenção."
            ),
            label=f"🤖 Analisar heatmap por {visao_hm}",
        )
    else:
        st.info(f"Dados de {visao_hm} não disponíveis.")


# ══════════════════════════════════════════════════════════════════════════
# TAB 3 — POR DIMENSÃO
# ══════════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown('<div class="section-title">Distribuição de nível de risco por dimensão</div>', unsafe_allow_html=True)

    rows_dim = []
    for d in DIMENSOES:
        col_c = f"class_{d}"
        if col_c not in base_f.columns: continue
        vc    = base_f[col_c].value_counts()
        total = vc.sum()
        for nivel in NIVEIS_ORDEM:
            cnt = vc.get(nivel, 0)
            rows_dim.append({
                "Dimensão": DIMENSOES_LABEL[d],
                "Nível":    nivel,
                "Qtd":      cnt,
                "Perc":     cnt / total * 100 if total else 0,
            })

    df_dim_dist = pd.DataFrame(rows_dim)
    if not df_dim_dist.empty:
        fig_stack = go.Figure()
        for nivel in NIVEIS_ORDEM:
            sub = df_dim_dist[df_dim_dist["Nível"] == nivel]
            fig_stack.add_trace(go.Bar(
                name=nivel, x=sub["Dimensão"], y=sub["Perc"],
                marker_color=cor_nivel(nivel), marker_line_width=0,
                text=sub["Perc"].apply(lambda v: f"{v:.0f}%" if v >= 5 else ""),
                textposition="inside", textfont=dict(size=11, color="#fff"),
            ))
        fig_stack.update_layout(
            barmode="stack",
            xaxis=dict(title=""),
            yaxis=dict(title="% respondentes", gridcolor=COR_BORDA, range=[0, 105]),
            legend=dict(orientation="h", y=1.08, x=0, font=dict(size=11)),
        )
        plotly_layout(fig_stack, height=420)
        st.plotly_chart(fig_stack, use_container_width=True, config=PLOTLY_CONFIG)

        # Tabela pivot
        pivot = df_dim_dist.pivot_table(index="Dimensão", columns="Nível", values="Perc", fill_value=0)
        pivot = pivot.reindex(columns=[c for c in NIVEIS_ORDEM if c in pivot.columns]).round(1)
        st.dataframe(
            pivot.style.map(_perc_row_color).format("{:.1f}%"),
            use_container_width=True, height=320,
        )

        # Resumo para IA
        alto_risco_dim = {
            DIMENSOES_LABEL[d]: round(base_f[f"class_{d}"].eq("Alto Risco").mean()*100, 1)
            for d in DIMENSOES if f"class_{d}" in base_f.columns
        }
        render_ai_analysis_button(
            visual_key   = "distribuicao_dimensoes",
            data_for_hash= {"alto_risco": alto_risco_dim, "hash": DADOS_HASH},
            prompt_context= (
                f"GRÁFICO: Distribuição de nível de risco por dimensão\n"
                f"% em 'Alto Risco' por dimensão:\n"
                + "\n".join(f"- {k}: {v}%" for k, v in alto_risco_dim.items())
                + f"\nTotal respondentes: {n_total}\n"
                f"Identifique as dimensões mais comprometidas e o que essas distribuições indicam."
            ),
            label="🤖 Analisar distribuição por dimensão",
        )


# ══════════════════════════════════════════════════════════════════════════
# TAB 4 — PGR
# ══════════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.markdown('<div class="section-title">PGR — Programa de Gerenciamento de Riscos · Matriz NR</div>', unsafe_allow_html=True)

    visao_pgr = st.radio("Dimensão:", ["Setor","Cargo"], horizontal=True, key="pgr_visao")
    df_pgr    = setor_f if visao_pgr == "Setor" else cargo_f
    col_pgr   = visao_pgr

    if df_pgr is not None and not df_pgr.empty:
        rows_pgr = []
        for _, row in df_pgr.iterrows():
            rec = {
                col_pgr:         row[col_pgr],
                "N":             int(row.get("n_colaboradores",0)),
                "NR Geral":      round(float(row.get("NR_geral",0)), 2),
                "Classificação": row.get("classificacao",""),
            }
            for d in DIMENSOES:
                sv = float(row.get(f"score_{d}", 0))
                nv = float(row.get(f"NR_{d}", 0))
                pv = score_para_P(sv, d)
                rec[f"NR — {DIMENSOES_LABEL[d]}"] = round(nv, 2)
                rec[f"Class. — {DIMENSOES_LABEL[d]}"] = score_para_classificacao(sv, d)
            rows_pgr.append(rec)

        df_pgr_full = pd.DataFrame(rows_pgr).sort_values("NR Geral", ascending=False).reset_index(drop=True)
        nr_cols_pgr   = [f"NR — {DIMENSOES_LABEL[d]}" for d in DIMENSOES if f"NR — {DIMENSOES_LABEL[d]}" in df_pgr_full.columns]
        class_cols_pgr= [f"Class. — {DIMENSOES_LABEL[d]}" for d in DIMENSOES if f"Class. — {DIMENSOES_LABEL[d]}" in df_pgr_full.columns]

        styled = (df_pgr_full.style
                  .map(_nr_row_color, subset=["NR Geral"] + nr_cols_pgr)
                  .map(_class_row_color, subset=class_cols_pgr)
                  .format({c: "{:.2f}" for c in ["NR Geral"] + nr_cols_pgr}))
        st.dataframe(styled, use_container_width=True, height=min(600, (len(df_pgr_full)+1)*38))

        # Heatmap PGR
        cols_nr_pgr = [f"NR_{d}" for d in DIMENSOES if f"NR_{d}" in df_pgr.columns]
        labels_pgr  = [DIMENSOES_LABEL[d] for d in DIMENSOES if f"NR_{d}" in df_pgr.columns]
        df_pgr_hm   = df_pgr.sort_values("NR_geral", ascending=False)

        fig_pgr = go.Figure(go.Heatmap(
            z=df_pgr_hm[cols_nr_pgr].values,
            x=labels_pgr, y=df_pgr_hm[col_pgr].tolist(),
            text=[[f"{v:.1f}" for v in row] for row in df_pgr_hm[cols_nr_pgr].values],
            texttemplate="%{text}", textfont=dict(size=11),
            colorscale=[[0., COR_VERDE],[.25, COR_AMARELO],[.55, COR_LARANJA],[1., COR_VERMELHO]],
            zmin=1, zmax=16,
        ))
        fig_pgr.update_layout(
            xaxis=dict(title="", tickangle=-30, side="top"),
            yaxis=dict(title="", autorange="reversed"),
        )
        plotly_layout(fig_pgr, height=max(400, len(df_pgr_hm)*30+80))
        st.plotly_chart(fig_pgr, use_container_width=True, config=PLOTLY_CONFIG)

        top3_pgr = df_pgr.head(3)
        top3_pgr_txt = "\n".join(
            f"- {row[col_pgr]}: NR={row['NR_geral']:.2f}, class={row.get('classificacao','?')}, "
            f"% alto={row.get('perc_risco_alto',0)*100:.1f}%"
            for _, row in top3_pgr.iterrows()
        )
        render_ai_analysis_button(
            visual_key   = f"pgr_{visao_pgr.lower()}",
            data_for_hash= {
                "visao":   visao_pgr,
                "top_nr":  top3_pgr["NR_geral"].round(2).tolist(),
                "top_grupos": top3_pgr[col_pgr].tolist(),
                "hash":    DADOS_HASH,
            },
            prompt_context= (
                f"TABELA PGR: Matriz de Risco por {visao_pgr}\n"
                f"Top 3 mais críticos:\n{top3_pgr_txt}\n"
                f"Total de {visao_pgr}s analisados: {len(df_pgr)}\n"
                f"Analise a matriz de risco, identifique prioridades para o PGR e sugira medidas de controle conforme NR-1."
            ),
            label=f"🤖 Analisar PGR por {visao_pgr}",
        )
    else:
        st.info(f"Dados de {visao_pgr} não disponíveis.")


# ══════════════════════════════════════════════════════════════════════════
# TAB 5 — PROBLEMAS & PLANOS DE AÇÃO
# ══════════════════════════════════════════════════════════════════════════
with tabs[4]:
    st.markdown(f"""
    <div class="page-header">
        <h2 style="margin:0;font-size:18px;">🚨 Problemas Identificados & Planos de Ação</h2>
        <p style="margin:4px 0 0;font-size:13px;color:{COR_MUTED};">
            Lista automática de riscos críticos · Gere planos 5W2H individuais por problema
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Gerar lista de problemas ──────────────────────────────────────────
    # A lista é regerada apenas quando o hash dos dados muda
    if st.session_state.problems_hash != DADOS_HASH:
        st.session_state.problems_cache = None  # invalida cache
        st.session_state.problems_hash  = DADOS_HASH

    def gerar_lista_problemas() -> list[dict]:
        """
        Gera lista de problemas diretamente dos dados (sem IA),
        de forma determinística e sem custo de tokens.
        """
        problemas = []

        # 1. Setores — MODO TESTE: inclui todos os níveis (NR >= 1)
        for _, row in setor_f.iterrows():
            nr = float(row.get("NR_geral", 0))
            if nr < 1: continue
            classe = classificar_NR(nr)
            n_col  = int(row.get("n_colaboradores", 0))
            perc_a = float(row.get("perc_risco_alto", 0)) * 100

            # Pior dimensão neste setor
            worst_dim, worst_nr = "", 0
            for d in DIMENSOES:
                v = float(row.get(f"NR_{d}", 0))
                if v > worst_nr:
                    worst_nr  = v
                    worst_dim = DIMENSOES_LABEL[d]

            problemas.append({
                "id":         f"setor_{row['Setor']}",
                "tipo":       "Setor",
                "grupo":      row["Setor"],
                "nr":         nr,
                "classe":     classe,
                "n":          n_col,
                "perc_alto":  perc_a,
                "worst_dim":  worst_dim,
                "worst_nr":   worst_nr,
                "descricao":  (
                    f"Setor '{row['Setor']}' com NR={nr:.1f} ({classe}) — "
                    f"{perc_a:.0f}% dos {n_col} colaboradores em risco alto/crítico. "
                    f"Dimensão mais crítica: {worst_dim} (NR={worst_nr:.1f})."
                ),
                "plan":       None,
            })

        # 2. Dimensões críticas globais
        for d in DIMENSOES:
            col_s = f"score_{d}"
            if col_s not in base_f.columns: continue
            score_v = base_f[col_s].mean()
            classe  = score_para_classificacao(score_v, d)
            if classe not in ["Alto Risco", "Risco Moderado", "Risco Médio", "Baixo Risco"]: continue
            perc_alto_d = (base_f[f"class_{d}"] == "Alto Risco").mean() * 100 if f"class_{d}" in base_f.columns else 0

            problemas.append({
                "id":        f"dim_{d}",
                "tipo":      "Dimensão",
                "grupo":     DIMENSOES_LABEL[d],
                "nr":        score_para_P(score_v, d) * 4.0,  # proxy NR
                "classe":    classe,
                "n":         n_total,
                "perc_alto": perc_alto_d,
                "worst_dim": DIMENSOES_LABEL[d],
                "worst_nr":  score_v,
                "descricao": (
                    f"Dimensão '{DIMENSOES_LABEL[d]}' com score={score_v:.2f} ({classe}) — "
                    f"{perc_alto_d:.0f}% dos respondentes em Alto Risco nessa dimensão."
                ),
                "plan":      None,
            })

        # 3. Cargos — MODO TESTE: inclui todos os níveis (NR >= 1)
        for _, row in cargo_f.iterrows():
            nr = float(row.get("NR_geral", 0))
            if nr < 1: continue
            classe = classificar_NR(nr)
            n_col  = int(row.get("n_colaboradores", 0))
            perc_a = float(row.get("perc_risco_alto", 0)) * 100
            problemas.append({
                "id":        f"cargo_{row['Cargo']}",
                "tipo":      "Cargo",
                "grupo":     row["Cargo"],
                "nr":        nr,
                "classe":    classe,
                "n":         n_col,
                "perc_alto": perc_a,
                "worst_dim": "",
                "worst_nr":  0,
                "descricao": (
                    f"Cargo '{row['Cargo']}' com NR={nr:.1f} ({classe}) — "
                    f"{perc_a:.0f}% dos {n_col} profissionais em risco alto/crítico."
                ),
                "plan":      None,
            })

        # Ordena por NR decrescente — MODO TESTE: limite 50
        return sorted(problemas, key=lambda x: -x["nr"])[:50]

    if st.session_state.problems_cache is None:
        st.session_state.problems_cache = gerar_lista_problemas()

    problemas = st.session_state.problems_cache

    if not problemas:
        st.success("✅ Nenhum problema crítico identificado nos dados filtrados.")
    else:
        # ── Filtros da lista ─────────────────────────────────────────────
        col_f1, col_f2 = st.columns([2, 3])
        with col_f1:
            filtro_tipo = st.selectbox(
                "Filtrar por tipo",
                ["Todos","Setor","Dimensão","Cargo"],
                key="prob_tipo_filter"
            )
        with col_f2:
            filtro_classe = st.multiselect(
                "Filtrar por classificação",
                ["Crítico","Importante","Moderado","Aceitável","Alto Risco","Risco Moderado","Risco Médio","Baixo Risco"],
                default=["Crítico","Importante","Moderado","Aceitável","Alto Risco","Risco Moderado","Risco Médio","Baixo Risco"],
                key="prob_classe_filter"
            )

        probs_filtrados = [
            p for p in problemas
            if (filtro_tipo == "Todos" or p["tipo"] == filtro_tipo)
            and p["classe"] in filtro_classe
        ]

        st.markdown(
            f'<div style="font-size:12px;color:{COR_MUTED};margin-bottom:1rem;">'
            f'Exibindo <b>{len(probs_filtrados)}</b> de <b>{len(problemas)}</b> problemas identificados'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── Planos salvos — índice rápido ─────────────────────────────────
        saved_plan_ids = {p["metadata"]["problem_id"]: i
                          for i, p in enumerate(st.session_state.action_plans)
                          if "metadata" in p}

        # ── Renderiza cada problema ───────────────────────────────────────
        for prob in probs_filtrados:
            prob_id   = prob["id"]
            cor_classe = {
                "Crítico":       COR_VERMELHO,
                "Importante":    COR_LARANJA,
                "Alto Risco":    COR_VERMELHO,
                "Risco Moderado":COR_AMARELO,
            }.get(prob["classe"], COR_CINZA)

            badge_tipo = {
                "Setor":    (COR_ACCENT,  "#1e2a4a"),
                "Dimensão": (COR_PURPLE,  "#1e1a3a"),
                "Cargo":    (COR_AMARELO, "#2a2010"),
            }.get(prob["tipo"], (COR_MUTED, COR_CARD))

            has_saved_plan = prob_id in saved_plan_ids

            with st.expander(
                f"{'🔴' if prob['classe'] in ['Crítico','Alto Risco'] else '🟠'} "
                f"{prob['tipo']}: {prob['grupo']} · {prob['classe']} · NR={prob['nr']:.1f}"
                + (" ✅ Plano gerado" if has_saved_plan else ""),
                expanded=False,
            ):
                # Cabeçalho do problema
                st.markdown(f"""
                <div style="display:flex;gap:12px;align-items:center;margin-bottom:12px;flex-wrap:wrap;">
                    <span style="background:{badge_tipo[1]};color:{badge_tipo[0]};border:1px solid {badge_tipo[0]}44;
                          border-radius:6px;padding:3px 10px;font-size:11px;font-weight:600;">{prob['tipo']}</span>
                    <span style="background:{cor_classe}22;color:{cor_classe};border:1px solid {cor_classe}44;
                          border-radius:6px;padding:3px 10px;font-size:11px;font-weight:600;">{prob['classe']}</span>
                    <span style="font-size:12px;color:{COR_MUTED};">👥 {prob['n']} pessoas</span>
                    <span style="font-size:12px;color:{COR_LARANJA};">⚠️ {prob['perc_alto']:.0f}% em risco alto</span>
                </div>
                <div style="background:{COR_CARD};border:1px solid {COR_BORDA};border-radius:8px;
                     padding:12px 16px;font-size:13px;color:{COR_TEXTO};margin-bottom:16px;">
                    {prob['descricao']}
                </div>
                """, unsafe_allow_html=True)

                # ── Plano existente ──────────────────────────────────────
                if has_saved_plan:
                    saved_idx  = saved_plan_ids[prob_id]
                    saved_plan = st.session_state.action_plans[saved_idx]["plan"]
                    progress   = compute_progress(saved_plan)
                    prog_pct   = int(progress * 100)
                    n_acoes    = len(saved_plan.get("acoes",[]))
                    n_done     = int(progress * n_acoes)

                    st.markdown(f"""
                    <div style="margin-bottom:12px;">
                        <div style="display:flex;justify-content:space-between;font-size:11px;
                             color:{COR_MUTED};margin-bottom:4px;">
                            <span>Progresso do plano</span>
                            <span>{n_done}/{n_acoes} ações concluídas</span>
                        </div>
                        <div class="progress-bar-outer">
                            <div class="progress-bar-inner" style="width:{prog_pct}%;"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    plan_key = f"saved_{prob_id}"
                    edited_df = render_plan_card(saved_plan, plan_key, editable=True)

                    col_upd, col_del, col_new = st.columns([2, 2, 2])
                    with col_upd:
                        if st.button("💾 Salvar alterações", key=f"upd_{prob_id}",
                                     use_container_width=True, type="primary"):
                            acoes_up = df_to_acoes(edited_df)
                            st.session_state.action_plans[saved_idx]["plan"] = {
                                **saved_plan, "acoes": acoes_up
                            }
                            st.success("✅ Plano atualizado!")
                            st.rerun()
                    with col_del:
                        if st.button("🗑 Remover plano", key=f"del_{prob_id}", use_container_width=True):
                            st.session_state.action_plans.pop(saved_idx)
                            st.rerun()
                    with col_new:
                        if st.button("🔄 Regerar plano", key=f"regen_{prob_id}", use_container_width=True):
                            st.session_state.action_plans.pop(saved_idx)
                            st.rerun()

                # ── Gerar novo plano ──────────────────────────────────────
                else:
                    gen_key = f"gen_{prob_id}"
                    if st.button(
                        f"🤖 Gerar Plano de Ação 5W2H para '{prob['grupo']}'",
                        key=gen_key,
                        use_container_width=True,
                        type="primary",
                    ):
                        with st.spinner(f"🧠 Gerando plano para '{prob['grupo']}'..."):
                            try:
                                rag_ctx = buscar_contexto_normativo(prob["descricao"])
                                prompt  = (
                                    f"PROBLEMA IDENTIFICADO NOS DADOS HSE-IT:\n"
                                    f"{prob['descricao']}\n\n"
                                    f"Tipo: {prob['tipo']} | Grupo: {prob['grupo']}\n"
                                    f"Classificação: {prob['classe']} | NR: {prob['nr']:.1f}\n"
                                    f"N respondentes: {prob['n']} | % em risco alto: {prob['perc_alto']:.0f}%\n"
                                    + (f"Dimensão mais crítica: {prob['worst_dim']}\n" if prob["worst_dim"] else "")
                                    + f"\n{rag_ctx}" if rag_ctx else ""
                                    + "\n\nGere um plano de ação 5W2H completo e específico para este problema."
                                )
                                raw    = call_groq(SYSTEM_PLAN, prompt)
                                result = parse_json_response(raw)

                                if result.get("tipo") == "plano_acao" and result.get("acoes"):
                                    for a in result["acoes"]:
                                        a.setdefault("status", "⏳ Pendente")

                                    st.session_state.action_plans.append({
                                        "plan":       result,
                                        "metadata":   {
                                            "problem_id": prob_id,
                                            "tipo":       prob["tipo"],
                                            "grupo":      prob["grupo"],
                                        },
                                        "created_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
                                    })
                                    st.success(f"✅ Plano gerado e salvo para '{prob['grupo']}'!")
                                    st.rerun()
                                else:
                                    st.error("❌ O modelo não retornou um plano válido. Tente novamente.")
                            except Exception as e:
                                st.error(f"❌ Erro ao gerar plano: {e}")
                                st.markdown(f'<pre style="font-size:10px;color:{COR_VERMELHO};">'
                                            f'{traceback.format_exc()}</pre>', unsafe_allow_html=True)

        # ── Seção de planos salvos ─────────────────────────────────────────
        st.markdown('<hr style="border-color:#2A2D3E;margin:2.5rem 0;">', unsafe_allow_html=True)
        st.markdown(f'<div class="section-title">📋 Planos de Ação Salvos ({len(st.session_state.action_plans)})</div>',
                    unsafe_allow_html=True)

        orphan_plans = [
            (i, p) for i, p in enumerate(st.session_state.action_plans)
            if "metadata" not in p  # planos sem vínculo com problema (importados)
        ]
        if orphan_plans:
            st.caption("Planos sem vínculo a problema específico:")
            for idx, saved in orphan_plans:
                with st.expander(f"📌 {saved['plan'].get('problema','Plano')[:80]} · {saved.get('created_at','—')}"):
                    plan_key = f"orphan_{idx}"
                    edited_df = render_plan_card(saved["plan"], plan_key)
                    if st.button("💾 Salvar", key=f"save_orphan_{idx}", type="primary"):
                        st.session_state.action_plans[idx]["plan"]["acoes"] = df_to_acoes(edited_df)
                        st.success("✅ Atualizado!")
                        st.rerun()
                    if st.button("🗑 Remover", key=f"del_orphan_{idx}"):
                        st.session_state.action_plans.pop(idx)
                        st.rerun()

        if not st.session_state.action_plans:
            st.markdown(f"""
            <div style="text-align:center;padding:40px 20px;color:{COR_MUTED};">
                <div style="font-size:40px;margin-bottom:12px;">📋</div>
                <div style="font-size:14px;">Nenhum plano gerado ainda.<br>
                Clique em <b>Gerar Plano de Ação</b> em qualquer problema acima.</div>
            </div>
            """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="margin-top:3rem;padding-top:1.5rem;border-top:1px solid {COR_BORDA};
     display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
  <span style="font-size:12px;color:{COR_MUTED};">
      🧠 Dashboard HSE-IT · Vivamente 360° · NR-1 · IA por Groq + Llama 3.3
  </span>
  <span style="font-size:11px;color:{COR_MUTED};font-family:'DM Mono',monospace;">
      {datetime.now().strftime("%d/%m/%Y %H:%M")} · {n_total} respondentes · hash {DADOS_HASH}
  </span>
</div>
""", unsafe_allow_html=True)
