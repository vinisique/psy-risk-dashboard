"""
dashboard_completo.py — Dashboard HSE-IT · Vivamente 360°
══════════════════════════════════════════════════════════
100% do app.py original (slides 13–23, 9 tabs) +
Agente IA em TODOS os gráficos e tabelas +
Tab 10: Problemas & Planos de Ação (5W2H)

Dependências extras: requests, (rag.py opcional)
Segredo necessário: GROQ_API_KEY em .streamlit/secrets.toml
"""

import hashlib
import json
import os
import re
import requests
import traceback
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard HSE-IT · NR-1",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Chave API Groq ────────────────────────────────────────────────────────────
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except (KeyError, FileNotFoundError):
    st.error("⚠️ Chave GROQ_API_KEY não encontrada em .streamlit/secrets.toml")
    st.stop()

# ─────────────────────────────────────────────
# PALETA & TEMA
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

RISCO_CORES = {
    "Baixo Risco":    COR_VERDE,
    "Risco Médio":    COR_AMARELO,
    "Risco Moderado": COR_LARANJA,
    "Alto Risco":     COR_VERMELHO,
    "Aceitável":      COR_VERDE,
    "Moderado":       COR_AMARELO,
    "Importante":     COR_LARANJA,
    "Crítico":        COR_VERMELHO,
    "Sem dados":      COR_CINZA,
}

DIMENSOES = [
    "Demandas", "Controle", "Apoio_Chefia",
    "Apoio_Colegas", "Relacionamentos", "Cargo", "Mudanca"
]
DIMENSOES_LABEL = {
    "Demandas":        "Demandas",
    "Controle":        "Controle",
    "Apoio_Chefia":    "Apoio da Chefia",
    "Apoio_Colegas":   "Apoio dos Colegas",
    "Relacionamentos": "Relacionamentos",
    "Cargo":           "Cargo / Função",
    "Mudanca":         "Comunicação e Mudanças",
}
DIM_NEGATIVAS = {"Demandas", "Relacionamentos"}

QS_NEGATIVAS = set(range(1, 9)) | set(range(24, 28))

NIVEIS_ORDEM       = ["Baixo Risco", "Risco Médio", "Risco Moderado", "Alto Risco"]
NIVEIS_GERAL_ORDEM = ["Aceitável", "Moderado", "Importante", "Crítico"]

COR_RESPOSTAS_NEG = ["#2D9E75", "#8BC4A8", "#F5A623", "#E8621A", "#D63B3B"]
COR_RESPOSTAS_POS = ["#D63B3B", "#E8621A", "#F5A623", "#8BC4A8", "#2D9E75"]

PLOTLY_CONFIG = dict(scrollZoom=False, doubleClick=False, displayModeBar=False)

CORES_RADAR = [
    "#4F8EF7","#2D9E75","#F5A623","#E8621A","#D63B3B",
    "#B97CF7","#5DCAA5","#F77F4F","#7FC8F8","#F7D44F",
]

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
_ss_defaults = {
    "action_plans":   [],
    "analysis_cache": {},
    "open_analysis":  {},
    "problems_cache": None,
    "problems_hash":  "",
    "parquet_mtime":  0.0,   # última data de modificação conhecida dos parquets
}
for _k, _v in _ss_defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ─────────────────────────────────────────────
# CSS — 100% idêntico ao app.py original + extras IA
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
    padding-top: 0 !important;
}}
[data-testid="stSidebar"] > div {{ padding-top: 0 !important; }}
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
.kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 14px; margin-bottom: 2rem; }}
.kpi-card {{
    background: {COR_CARD};
    border: 1px solid {COR_BORDA};
    border-radius: 12px;
    padding: 18px 20px;
}}
.kpi-label {{ font-size: 11px; font-weight: 500; color: {COR_MUTED}; text-transform: uppercase; letter-spacing: .08em; margin-bottom: 6px; }}
.kpi-value {{ font-size: 28px; font-weight: 600; color: {COR_TEXTO}; line-height: 1; }}
.kpi-sub {{ font-size: 12px; color: {COR_MUTED}; margin-top: 4px; }}
.section-title {{
    font-size: 13px; font-weight: 600; color: {COR_MUTED};
    text-transform: uppercase; letter-spacing: .1em;
    margin: 2rem 0 1rem;
    padding-bottom: 8px;
    border-bottom: 1px solid {COR_BORDA};
}}
.page-header {{
    background: linear-gradient(135deg, #1A1D27 0%, #0F1117 100%);
    border: 1px solid {COR_BORDA};
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}}

/* MOBILE FIX #2: scroll horizontal suave nas tabelas */
[data-testid="stDataFrame"] iframe {{
    touch-action: pan-x pan-y;
}}

/* ── Análise IA ── */
.ai-box {{
    background: #111827;
    border: 1px solid {COR_PURPLE}44;
    border-left: 3px solid {COR_PURPLE};
    border-radius: 0 12px 12px 12px;
    padding: 16px 20px; margin-top: 8px;
    font-size: 13px; line-height: 1.75; color: {COR_TEXTO};
}}

/* ── 5W2H progress ── */
.progress-bar-outer {{ background:{COR_BORDA}; border-radius:4px; height:6px; margin:10px 0 4px; }}
.progress-bar-inner {{ height:100%; border-radius:4px; background:linear-gradient(90deg,{COR_ACCENT},{COR_PURPLE}); }}

/* ── MOBILE FIX #4: media queries ── */
@media (max-width: 768px) {{
    .block-container {{ padding: 1rem 0.75rem 2rem !important; }}
    .kpi-grid {{ grid-template-columns: repeat(2, 1fr) !important; gap: 10px !important; }}
    .kpi-value {{ font-size: 22px !important; }}
    [data-testid="stPlotlyChart"] iframe, .js-plotly-plot, .plotly-graph-div {{ min-height: 380px !important; }}
    [data-testid="stPlotlyChart"] > div {{ min-height: 380px !important; }}
    [data-baseweb="tab-list"] {{
        overflow-x: auto !important; flex-wrap: nowrap !important;
        -webkit-overflow-scrolling: touch; padding: 6px !important; gap: 4px !important;
    }}
    [data-baseweb="tab"] {{ flex-shrink: 0 !important; padding: 10px 16px !important; font-size: 12px !important; }}
    [data-testid="stDataFrame"] {{ overflow: auto !important; -webkit-overflow-scrolling: touch; }}
    [data-testid="stDataFrame"] iframe {{ touch-action: pan-x pan-y !important; min-width: 100% !important; }}
    .page-header {{ flex-direction: column !important; align-items: flex-start !important; padding: 18px 20px !important; gap: 8px; }}
    .page-header h1 {{ font-size: 18px !important; }}
    .section-title {{ font-size: 11px !important; }}
}}

@media (max-width: 480px) {{
    .kpi-grid {{ grid-template-columns: 1fr 1fr !important; }}
    .kpi-value {{ font-size: 20px !important; }}
    [data-testid="stPlotlyChart"] iframe, .js-plotly-plot {{ min-height: 420px !important; }}
    [data-baseweb="tab"] {{ padding: 8px 12px !important; font-size: 11px !important; }}
}}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HELPERS — idênticos ao app.py original
# ─────────────────────────────────────────────

def cor_nivel(nivel: str) -> str:
    return RISCO_CORES.get(nivel, COR_CINZA)


def plotly_layout(fig, height=380, margin=None):
    m = margin or dict(l=48, r=24, t=30, b=20)
    fig.update_layout(
        height=height, margin=m,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans", color=COR_TEXTO, size=12),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=COR_BORDA, font=dict(size=11)),
        xaxis=dict(gridcolor=COR_BORDA, zerolinecolor=COR_BORDA),
        yaxis=dict(gridcolor=COR_BORDA, zerolinecolor=COR_BORDA),
        dragmode=False,
    )
    return fig


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


def _nr_row_color(val):
    try: v = float(val)
    except (TypeError, ValueError): return ""
    if v >= 13: return f"background-color: rgba(214,59,59,0.35); color: {COR_TEXTO}"
    if v >= 9:  return f"background-color: rgba(232,98,26,0.30); color: {COR_TEXTO}"
    if v >= 5:  return f"background-color: rgba(245,166,35,0.25); color: {COR_TEXTO}"
    return f"background-color: rgba(45,158,117,0.20); color: {COR_TEXTO}"


def _perc_row_color(val):
    try: v = float(str(val).replace("%", ""))
    except (TypeError, ValueError): return ""
    if v >= 60: return f"background-color: rgba(214,59,59,0.30); color: {COR_TEXTO}"
    if v >= 35: return f"background-color: rgba(232,98,26,0.25); color: {COR_TEXTO}"
    if v >= 15: return f"background-color: rgba(245,166,35,0.20); color: {COR_TEXTO}"
    return f"background-color: rgba(45,158,117,0.15); color: {COR_TEXTO}"


def _p_row_color(val):
    try: v = int(val)
    except (TypeError, ValueError): return ""
    if v == 4: return f"background-color: rgba(214,59,59,0.35); color: {COR_TEXTO}"
    if v == 3: return f"background-color: rgba(232,98,26,0.30); color: {COR_TEXTO}"
    if v == 2: return f"background-color: rgba(245,166,35,0.25); color: {COR_TEXTO}"
    return f"background-color: rgba(45,158,117,0.20); color: {COR_TEXTO}"


def _class_row_color(val):
    mapa = {
        "Alto Risco":     f"background-color: rgba(214,59,59,0.35); color: {COR_TEXTO}",
        "Risco Moderado": f"background-color: rgba(232,98,26,0.30); color: {COR_TEXTO}",
        "Risco Médio":    f"background-color: rgba(245,166,35,0.25); color: {COR_TEXTO}",
        "Baixo Risco":    f"background-color: rgba(45,158,117,0.20); color: {COR_TEXTO}",
    }
    return mapa.get(str(val), "")

# ─────────────────────────────────────────────
# CARGA DE DADOS — idêntica ao app.py
# ─────────────────────────────────────────────

@st.cache_data
def load_data(path_base, path_setor, path_cargo, path_unidade=None):
    base    = pd.read_parquet(path_base)
    setor   = pd.read_parquet(path_setor)
    cargo   = pd.read_parquet(path_cargo)
    unidade = pd.read_parquet(path_unidade) if path_unidade and os.path.exists(path_unidade) else None
    return base, setor, cargo, unidade


def reaplicar_agg(df, col, rename):
    if df.empty: return pd.DataFrame()
    g = df.groupby(col).agg(
        n_colaboradores=(col, "count"),
        IGRP=("IGRP", "mean"),
        NR_geral=("NR_geral", "mean"),
        **{f"score_{d}": (f"score_{d}", "mean") for d in DIMENSOES if f"score_{d}" in df.columns},
        **{f"NR_{d}":    (f"NR_{d}",    "mean") for d in DIMENSOES if f"NR_{d}"    in df.columns},
        **{f"P_{d}":     (f"P_{d}",     "mean") for d in DIMENSOES if f"P_{d}"     in df.columns},
        **{f"S_{d}":     (f"S_{d}",     "mean") for d in DIMENSOES if f"S_{d}"     in df.columns},
        perc_critico   =("risco_geral", lambda x: (x == "Crítico").mean()),
        perc_importante=("risco_geral", lambda x: (x == "Importante").mean()),
        perc_moderado  =("risco_geral", lambda x: (x == "Moderado").mean()),
        perc_aceitavel =("risco_geral", lambda x: (x == "Aceitável").mean()),
        perc_risco_alto=("risco_geral", lambda x: x.isin(["Crítico", "Importante"]).mean()),
    ).reset_index().rename(columns={col: rename})
    g["classificacao"] = g["NR_geral"].apply(classificar_NR)
    g["rank_risco"]    = g["NR_geral"].rank(ascending=False, method="min")
    return g.sort_values(["perc_risco_alto", "NR_geral"], ascending=False)


BASE_PATH    = "base.parquet"
SETOR_PATH   = "setor.parquet"
CARGO_PATH   = "cargo.parquet"
UNIDADE_PATH = "unidade.parquet"

base, setor, cargo, unidade = load_data(BASE_PATH, SETOR_PATH, CARGO_PATH, UNIDADE_PATH)

# ═══════════════════════════════════════════════════════════════════════════
# CAMADA IA — Groq + cache + análise + 5W2H
# ═══════════════════════════════════════════════════════════════════════════

def _make_hash(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()[:16]


def get_cached_analysis(cache_key):
    return st.session_state.analysis_cache.get(cache_key)


def set_cached_analysis(cache_key, text):
    st.session_state.analysis_cache[cache_key] = text


SYSTEM_ANALYSIS = """Você é o Agente HSE-IT — especialista em saúde mental ocupacional, riscos psicossociais e NR-1.
Recebe dados de um gráfico ou tabela e gera análise concisa, técnica e acionável.

Responda SEMPRE com JSON:
{
  "tipo": "analise",
  "titulo": "título curto (máx 10 palavras)",
  "resumo": "1 frase de diagnóstico direto",
  "insights": ["insight com dado específico","insight 2","insight 3"],
  "alertas": ["alerta crítico se existir — pode ser lista vazia"],
  "recomendacoes": ["ação imediata 1","ação 2"]
}
Seja direto. Cite números. Máximo 5 itens por lista."""

SYSTEM_PLAN = """Você é o Agente HSE-IT — especialista em saúde mental ocupacional, riscos psicossociais, NR-1 e ISO 45003.
Recebe um problema e gera plano de ação 5W2H completo.

Responda SEMPRE com JSON válido:
{
  "tipo": "plano_acao",
  "problema": "descrição curta",
  "objetivo": "objetivo SMART",
  "acoes": [
    {
      "descricao":"O quê?","porque":"Por quê?","onde":"Onde?",
      "responsavel":"Quem?","prazo":"Quando?","como":"Como?",
      "prioridade":"Alta | Média | Baixa",
      "indicador_sucesso":"Quanto? (métrica mensurável)",
      "status":"⏳ Pendente"
    }
  ]
}
Gere entre 3 e 5 ações específicas e acionáveis."""


def call_groq(system, user_content):
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


def parse_json_response(raw):
    try:
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        return json.loads(m.group(0)) if m else {"tipo": "analise", "resumo": raw}
    except Exception:
        return {"tipo": "analise", "resumo": raw}


# ─── PDCA — detecção de atualização dos parquets ─────────────────────────────

def _parquet_mtime():
    """Retorna o maior mtime (float) entre os arquivos parquet conhecidos."""
    paths = [BASE_PATH, SETOR_PATH, CARGO_PATH, UNIDADE_PATH]
    mtime = 0.0
    for p in paths:
        try:
            mtime = max(mtime, os.path.getmtime(p))
        except OSError:
            pass
    return mtime


def _nr_atual_do_grupo(prob_id, tipo, grupo):
    """
    Busca o NR atual do grupo nos DataFrames já filtrados em memória.
    Retorna None se não encontrado.
    """
    try:
        if tipo == "Setor":
            row = setor_f[setor_f["Setor"] == grupo]
            if not row.empty:
                return float(row.iloc[0]["NR_geral"])
        elif tipo == "Cargo":
            row = cargo_f[cargo_f["Cargo"] == grupo]
            if not row.empty:
                return float(row.iloc[0]["NR_geral"])
        elif tipo == "Dimensão":
            for d in DIMENSOES:
                if DIMENSOES_LABEL[d] == grupo:
                    col_s = f"score_{d}"
                    if col_s in base_f.columns:
                        score_v = base_f[col_s].mean()
                        return float(score_para_P(score_v, d) * 4.0)
    except Exception:
        pass
    return None


def _perc_alto_atual_do_grupo(tipo, grupo):
    """Retorna % em risco alto atual do grupo (0–100). None se não encontrado."""
    try:
        if tipo == "Setor":
            row = setor_f[setor_f["Setor"] == grupo]
            if not row.empty:
                return float(row.iloc[0].get("perc_risco_alto", 0)) * 100
        elif tipo == "Cargo":
            row = cargo_f[cargo_f["Cargo"] == grupo]
            if not row.empty:
                return float(row.iloc[0].get("perc_risco_alto", 0)) * 100
        elif tipo == "Dimensão":
            for d in DIMENSOES:
                if DIMENSOES_LABEL[d] == grupo:
                    if f"class_{d}" in base_f.columns:
                        return (base_f[f"class_{d}"] == "Alto Risco").mean() * 100
    except Exception:
        pass
    return None


SYSTEM_ADJUST = """Você é o Agente HSE-IT — especialista em saúde mental ocupacional, riscos psicossociais, NR-1 e ISO 45003.
Recebe um plano 5W2H existente, o resultado do Check PDCA (comparativo de NR antes/depois) e gera um plano 5W2H AJUSTADO — complementar ao anterior, focado nas lacunas que persistem.
NAO repita ações já concluídas. Foque no que ainda precisa melhorar.

Responda SEMPRE com JSON válido:
{
  "tipo": "plano_acao",
  "problema": "descricao curta do problema residual",
  "objetivo": "objetivo SMART ajustado",
  "acoes": [
    {
      "descricao":"O que?","porque":"Por que?","onde":"Onde?",
      "responsavel":"Quem?","prazo":"Quando?","como":"Como?",
      "prioridade":"Alta | Media | Baixa",
      "indicador_sucesso":"Quanto? (metrica mensuravel)",
      "status":"Pendente"
    }
  ]
}
Gere entre 3 e 5 ações específicas e acionáveis."""


def _render_pdca_card(saved, prob_id, saved_idx):
    """
    Renderiza o card PDCA abaixo do plano 5W2H.
    saved     — dict do plano em session_state.action_plans
    prob_id   — id do problema
    saved_idx — índice em session_state.action_plans
    """
    plan     = saved["plan"]
    meta     = saved.get("metadata", {})
    tipo     = meta.get("tipo", "")
    grupo    = meta.get("grupo", "")
    created  = saved.get("created_at", "—")

    nr_base     = saved.get("nr_baseline", None)
    perc_base   = saved.get("perc_alto_baseline", None)
    mtime_base  = saved.get("parquet_mtime_baseline", 0.0)
    mtime_atual = _parquet_mtime()
    dados_novos = (mtime_atual > mtime_base) and (mtime_base > 0)

    nr_atual   = _nr_atual_do_grupo(prob_id, tipo, grupo) if dados_novos else None
    perc_atual = _perc_alto_atual_do_grupo(tipo, grupo)   if dados_novos else None

    progress = compute_progress(plan)
    prog_pct = int(progress * 100)
    acoes    = plan.get("acoes", [])
    n_acoes  = len(acoes)
    n_done   = int(progress * n_acoes)

    def _dot(done):
        cor = COR_VERDE if done else COR_CINZA
        return (f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;'
                f'background:{cor};margin-right:6px;vertical-align:middle;"></span>')

    def _quadrant(letra, titulo, conteudo_html, ativo=False, concluido=False):
        borda_cor = COR_ACCENT if ativo else (COR_VERDE if concluido else COR_BORDA)
        borda_w   = "2px" if (ativo or concluido) else "1px"
        return (f'<div style="background:#16192A;border:{borda_w} solid {borda_cor};'
                f'border-radius:10px;padding:14px 16px;min-height:130px;">'
                f'<div style="font-size:10px;font-weight:700;color:{COR_MUTED};'
                f'text-transform:uppercase;letter-spacing:.1em;margin-bottom:6px;">{letra}</div>'
                f'<div style="font-size:13px;font-weight:600;color:{COR_TEXTO};margin-bottom:10px;">{titulo}</div>'
                f'{conteudo_html}</div>')

    # ── P — Plan ─────────────────────────────────────────────────────────────
    nr_b_fmt = f"{nr_base:.1f}" if nr_base is not None else "—"
    p_html = (
        f'{_dot(True)}<span style="font-size:12px;color:{COR_MUTED};">Problema identificado</span><br>'
        f'{_dot(True)}<span style="font-size:12px;color:{COR_MUTED};">5W2H gerado em {created}</span><br>'
        f'{_dot(nr_base is not None)}<span style="font-size:12px;color:{COR_MUTED};">NR baseline: {nr_b_fmt}</span>'
    )

    # ── D — Do ───────────────────────────────────────────────────────────────
    acoes_html = ""
    for a in acoes[:5]:
        done = a.get("status", "") == "✅ Concluído"
        acoes_html += (f'{_dot(done)}<span style="font-size:12px;color:{COR_MUTED};">'
                       f'{a.get("descricao","—")[:55]}</span><br>')
    d_html = (
        acoes_html
        + f'<div style="margin-top:8px;background:{COR_BORDA};border-radius:3px;height:5px;">'
        f'<div style="width:{prog_pct}%;height:5px;border-radius:3px;'
        f'background:linear-gradient(90deg,{COR_ACCENT},{COR_PURPLE});"></div></div>'
        f'<div style="font-size:11px;color:{COR_MUTED};margin-top:4px;">{n_done}/{n_acoes} ações concluídas</div>'
    )

    # ── C — Check ────────────────────────────────────────────────────────────
    if dados_novos and nr_atual is not None and nr_base is not None:
        delta   = nr_base - nr_atual
        delta_p = (delta / nr_base * 100) if nr_base > 0 else 0
        melhora = delta > 0
        cor_seta = COR_VERDE if melhora else COR_VERMELHO
        sinal    = "▼" if melhora else "▲"
        cor_nr_b = COR_VERMELHO
        cor_nr_a = COR_VERDE if melhora else COR_VERMELHO
        perc_b_fmt = f"{perc_base:.0f}%" if perc_base is not None else "—"
        perc_a_fmt = f"{perc_atual:.0f}%" if perc_atual is not None else "—"
        c_html = (
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">'
            f'<div style="flex:1;background:{COR_CARD};border-radius:8px;padding:8px;text-align:center;border:1px solid {COR_BORDA};">'
            f'<div style="font-size:18px;font-weight:600;color:{cor_nr_b};">{nr_base:.1f}</div>'
            f'<div style="font-size:10px;color:{COR_MUTED};">antes</div></div>'
            f'<div style="font-size:20px;color:{cor_seta};font-weight:700;">→</div>'
            f'<div style="flex:1;background:{COR_CARD};border-radius:8px;padding:8px;text-align:center;border:1px solid {COR_BORDA};">'
            f'<div style="font-size:18px;font-weight:600;color:{cor_nr_a};">{nr_atual:.1f}</div>'
            f'<div style="font-size:10px;color:{COR_MUTED};">agora</div></div></div>'
            f'<div style="font-size:12px;color:{cor_seta};font-weight:600;">'
            f'{sinal} {abs(delta_p):.0f}% {"melhora" if melhora else "piora"} no NR</div>'
            f'<div style="font-size:11px;color:{COR_MUTED};margin-top:4px;">'
            f'% risco alto: {perc_b_fmt} → {perc_a_fmt}</div>'
        )
        c_ativo = True
    else:
        data_base_fmt = datetime.fromtimestamp(mtime_base).strftime("%d/%m/%Y") if mtime_base > 0 else "—"
        extra = (f'<br><span style="font-size:10px;margin-top:4px;display:block;">Baseline: {data_base_fmt}</span>'
                 if mtime_base > 0 else "")
        c_html = (
            f'<div style="text-align:center;padding:12px 0;color:{COR_MUTED};font-size:12px;">'
            f'<div style="font-size:22px;margin-bottom:6px;">⏳</div>'
            f'Aguardando novo questionário.<br>'
            f'<span style="font-size:11px;">O check será calculado automaticamente quando os dados forem atualizados.</span>'
            f'{extra}</div>'
        )
        c_ativo = False

    # ── A — Act ──────────────────────────────────────────────────────────────
    a_ativo = dados_novos and nr_atual is not None
    a_html  = (
        f'<div style="font-size:12px;color:{COR_MUTED};">Escolha a próxima ação abaixo.</div>'
        if a_ativo else
        f'<div style="font-size:12px;color:{COR_MUTED};opacity:.5;">Disponível após o check ser concluído.</div>'
    )

    # ── Grid dos 4 quadrantes ─────────────────────────────────────────────────
    st.markdown(
        f'<div style="margin-top:20px;border-top:1px solid {COR_BORDA};padding-top:16px;">'
        f'<div style="font-size:11px;font-weight:700;color:{COR_MUTED};text-transform:uppercase;'
        f'letter-spacing:.1em;margin-bottom:10px;">🔄 Ciclo PDCA</div>'
        f'<div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;">'
        + _quadrant("P — Plan",  "Plano gerado",
                    p_html, ativo=False, concluido=True)
        + _quadrant("D — Do",    "Em execução",
                    d_html, ativo=(prog_pct < 100), concluido=(prog_pct == 100))
        + _quadrant("C — Check",
                    "Dados atualizados" if c_ativo else "Aguardando dados",
                    c_html, ativo=c_ativo, concluido=False)
        + _quadrant("A — Act",
                    "Decisão do gestor" if a_ativo else "Aguardando check",
                    a_html, ativo=a_ativo, concluido=False)
        + '</div></div>',
        unsafe_allow_html=True,
    )

    # ── Botões Act renderizados via Streamlit (fora do HTML) ──────────────────
    if a_ativo:
        col_enc, col_adj, col_new = st.columns([1, 1, 1])
        with col_enc:
            if st.button("✅ Encerrar ciclo", key=f"act_enc_{prob_id}", use_container_width=True):
                st.session_state.action_plans[saved_idx]["ciclo_encerrado"] = True
                st.session_state.action_plans[saved_idx]["encerrado_em"]    = datetime.now().strftime("%d/%m/%Y %H:%M")
                st.success("✅ Ciclo PDCA encerrado. Problema resolvido!")
                st.rerun()
        with col_adj:
            if st.button("🔄 Ajustar plano", key=f"act_adj_{prob_id}", use_container_width=True):
                with st.spinner("🧠 Gerando plano ajustado com base no check..."):
                    try:
                        nr_atual_inner   = _nr_atual_do_grupo(prob_id, tipo, grupo)
                        perc_atual_inner = _perc_alto_atual_do_grupo(tipo, grupo)
                        delta_txt = ""
                        if nr_base is not None and nr_atual_inner is not None:
                            dp = (nr_base - nr_atual_inner) / nr_base * 100 if nr_base > 0 else 0
                            delta_txt = (
                                f"CHECK PDCA: NR era {nr_base:.1f}, agora é {nr_atual_inner:.1f} "
                                f"({'melhora' if dp > 0 else 'piora'} de {abs(dp):.0f}%). "
                                f"% em risco alto: {perc_base:.0f}% -> {perc_atual_inner:.0f}%.\n"
                            )
                        concluidas = [a.get("descricao","") for a in acoes if a.get("status","") == "✅ Concluído"]
                        pendentes  = [a.get("descricao","") for a in acoes if a.get("status","") != "✅ Concluído"]
                        prompt_adj = (
                            f"PROBLEMA ORIGINAL: {plan.get('problema','')}\n"
                            f"GRUPO: {tipo} '{grupo}'\n"
                            f"{delta_txt}"
                            f"Acoes ja CONCLUIDAS: {', '.join(concluidas) or 'nenhuma'}\n"
                            f"Acoes PENDENTES: {', '.join(pendentes) or 'nenhuma'}\n"
                            f"Gere plano 5W2H AJUSTADO focado no que ainda precisa melhorar."
                        )
                        raw    = call_groq(SYSTEM_ADJUST, prompt_adj)
                        result = parse_json_response(raw)
                        if result.get("tipo") == "plano_acao" and result.get("acoes"):
                            for a in result["acoes"]:
                                a.setdefault("status", "⏳ Pendente")
                            novo = {
                                "plan": result,
                                "metadata": {"problem_id": prob_id, "tipo": tipo, "grupo": grupo},
                                "created_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
                                "nr_baseline":            nr_atual_inner,
                                "perc_alto_baseline":     perc_atual_inner,
                                "parquet_mtime_baseline": mtime_atual,
                                "plano_anterior_idx":     saved_idx,
                            }
                            st.session_state.action_plans.append(novo)
                            st.session_state.action_plans[saved_idx]["ciclo_encerrado"] = True
                            st.success("✅ Plano ajustado gerado! Novo ciclo PDCA iniciado.")
                            st.rerun()
                        else:
                            st.error("❌ Modelo não retornou plano válido.")
                    except Exception as e:
                        st.error(f"❌ Erro ao ajustar plano: {e}")
        with col_new:
            if st.button("↺ Novo ciclo", key=f"act_new_{prob_id}", use_container_width=True):
                st.info("Aplique novo questionário. Os dados serão comparados automaticamente quando o arquivo for atualizado.")


def _render_analysis_box(result):
    if isinstance(result, str):
        st.markdown(result)
        return
    titulo   = result.get("titulo", "Análise IA")
    resumo   = result.get("resumo", "")
    insights = result.get("insights", [])
    alertas  = result.get("alertas", [])
    recs     = result.get("recomendacoes", [])

    st.markdown(f"**{titulo}**")
    if resumo:
        st.markdown(
            f'<div style="background:#1a2030;border-left:3px solid {COR_ACCENT};'
            f'border-radius:0 8px 8px 0;padding:10px 14px;margin-bottom:12px;'
            f'font-size:13px;color:{COR_TEXTO};">{resumo}</div>',
            unsafe_allow_html=True)
    for section, cor, emoji in [
        (insights, COR_ACCENT,   "📊 Insights"),
        (alertas,  COR_VERMELHO, "⚠️ Alertas"),
        (recs,     COR_VERDE,    "✅ Recomendações"),
    ]:
        if section:
            st.markdown(
                f'<div style="font-size:11px;font-weight:600;color:{cor};'
                f'text-transform:uppercase;letter-spacing:.08em;margin:10px 0 6px;">'
                f'{emoji}</div>', unsafe_allow_html=True)
            for item in section:
                st.markdown(
                    f'<div style="border-left:2px solid {cor};padding:5px 10px;'
                    f'margin-bottom:4px;font-size:12px;color:{COR_TEXTO};">{item}</div>',
                    unsafe_allow_html=True)


def _buscar_rag(prompt_context):
    """Tenta importar rag.py; retorna string vazia se não disponível."""
    try:
        from rag import buscar_contexto_normativo
        return buscar_contexto_normativo(prompt_context[:300]) or ""
    except Exception:
        return ""


def render_ai_button(visual_key, data_for_hash, prompt_context, label="🤖 Analisar com IA"):
    """Botão de análise IA com cache por hash de dados. Funciona sem rag.py."""
    current_hash = _make_hash(data_for_hash)
    cache_key    = f"{visual_key}_{current_hash}"
    cached       = get_cached_analysis(cache_key)
    open_key     = f"open_{visual_key}"

    col_btn, col_status, _ = st.columns([2, 3, 4])
    with col_btn:
        clicked = st.button(
            "✅ Ver análise IA" if cached else label,
            key=f"ai_btn_{visual_key}",
            use_container_width=True,
        )
    with col_status:
        if cached:
            st.markdown(
                f'<div style="font-size:11px;color:{COR_VERDE};padding-top:8px;">'
                f'✅ Cacheada · <code>{current_hash}</code></div>',
                unsafe_allow_html=True)

    if clicked:
        st.session_state.open_analysis[open_key] = not st.session_state.open_analysis.get(open_key, False)

    if st.session_state.open_analysis.get(open_key, False):
        with st.expander("🤖 Análise gerada pela IA", expanded=True):
            if cached:
                _render_analysis_box(cached)
            else:
                with st.spinner("🧠 Gerando análise..."):
                    try:
                        rag_ctx = _buscar_rag(prompt_context)
                        full    = f"{prompt_context}\n\n{rag_ctx}" if rag_ctx else prompt_context
                        raw     = call_groq(SYSTEM_ANALYSIS, full)
                        result  = parse_json_response(raw)
                        set_cached_analysis(cache_key, result)
                        _render_analysis_box(result)
                    except Exception as e:
                        st.error(f"❌ Erro ao gerar análise: {e}")

# ─── 5W2H rendering ────────────────────────────────────────────────────────
STATUS_OPTIONS     = ["⏳ Pendente","🔄 Em andamento","✅ Concluído","❌ Cancelado"]
PRIORIDADE_OPTIONS = ["Alta","Média","Baixa"]

TH_COLORS = {
    "what"   :("#6B21A8","#E9D5FF"),
    "why"    :("#9D174D","#FCE7F3"),
    "where"  :("#BE123C","#FFE4E6"),
    "when"   :("#C2410C","#FFEDD5"),
    "who"    :("#B45309","#FEF3C7"),
    "how"    :("#065F46","#D1FAE5"),
    "howmuch":("#0E7490","#CFFAFE"),
    "status" :("#374151","#F9FAFB"),
}
STATUS_COLOR = {
    "⏳ Pendente"    :("#6B7280","#F3F4F6"),
    "🔄 Em andamento":("#2563EB","#DBEAFE"),
    "✅ Concluído"   :("#059669","#D1FAE5"),
    "❌ Cancelado"   :("#DC2626","#FEE2E2"),
}
PRIO_COLOR = {
    "Alta" :("#DC2626","#FEE2E2"),
    "Média":("#D97706","#FEF3C7"),
    "Baixa":("#059669","#D1FAE5"),
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


def render_5w2h_html(plan):
    acoes    = plan.get("acoes", [])
    objetivo = plan.get("objetivo", "—")
    W = {"what":"220px","why":"160px","where":"110px","when":"100px",
         "who":"130px","how":"130px","howmuch":"160px","status":"110px"}
    thead = ("<thead><tr>"
             +_th("O quê?","What?","what",W["what"])+_th("Por quê?","Why?","why",W["why"])
             +_th("Onde?","Where?","where",W["where"])+_th("Quando?","When?","when",W["when"])
             +_th("Quem?","Who?","who",W["who"])+_th("Como?","How?","how",W["how"])
             +_th("Quanto?","How much?","howmuch",W["howmuch"])+_th("Status","Status","status",W["status"])
             +"</tr></thead>")
    rows = ""
    for i, a in enumerate(acoes):
        bg = "#16192A" if i % 2 == 0 else "#1A1D2B"
        rows += f'<tr style="background:{bg};">'
        rows += _td(a.get("descricao","—"), W["what"])
        rows += _td(a.get("porque",objetivo), W["why"])
        rows += _td(a.get("onde","—"), W["where"])
        rows += _td(a.get("prazo","—"), W["when"], True)
        rows += _td(a.get("responsavel","—"), W["who"])
        rows += _td(a.get("como","—"), W["how"])
        rows += _td(a.get("indicador_sucesso","—"), W["howmuch"])
        rows += _td(_badge(a.get("status","⏳ Pendente"),STATUS_COLOR)+"<br>"
                    +_badge(a.get("prioridade","Alta"),PRIO_COLOR), W["status"], True)
        rows += "</tr>"
    return f"""
    <style>*{{box-sizing:border-box;margin:0;padding:0;}}body{{background:transparent;overflow-y:auto;}}
    .w2h-s{{overflow-x:auto;border-radius:10px;border:1px solid #2A2D3E;}}
    .w2h-t{{border-collapse:collapse;table-layout:fixed;width:100%;}}
    .w2h-t tr:last-child td{{border-bottom:none;}}
    .w2h-t td:last-child,.w2h-t th:last-child{{border-right:none!important;}}</style>
    <div class="w2h-s"><table class="w2h-t">{thead}<tbody>{rows}</tbody></table></div>"""


def plan_to_df(plan):
    objetivo = plan.get("objetivo", "—")
    rows = []
    for a in plan.get("acoes", []):
        rows.append({
            "O quê?"    : a.get("descricao",""),
            "Por quê?"  : a.get("porque",objetivo),
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


def df_to_acoes(df):
    return [{"descricao":r.get("O quê?",""),"porque":r.get("Por quê?",""),
             "onde":r.get("Onde?",""),"prazo":r.get("Quando?",""),
             "responsavel":r.get("Quem?",""),"como":r.get("Como?",""),
             "indicador_sucesso":r.get("Quanto?",""),
             "status":r.get("Status","⏳ Pendente"),
             "prioridade":r.get("Prioridade","Alta")}
            for _, r in df.iterrows()]


def compute_progress(plan):
    acoes = plan.get("acoes", [])
    if not acoes: return 0.0
    return sum(1 for a in acoes if a.get("status","") == "✅ Concluído") / len(acoes)


def render_plan_card(plan, plan_key, editable=True):
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

    n_acoes = len(plan.get("acoes", []))
    components.html(render_5w2h_html(plan), height=max(200, 120+n_acoes*110), scrolling=True)

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
                            height=min(500, 60+n_acoes*55))
    return df

# ─────────────────────────────────────────────
# SIDEBAR — idêntica ao app.py original
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
        <div style="text-align:center; padding:25px 0 15px 0; border-bottom:1px solid #2A2D3E;">
            <h2 style="margin:0; font-size:24px; color:#2D9E75;">🧠 HSE-IT</h2>
            <p style="margin:4px 0 0 0; font-size:13px; color:#8B8FA8;">
                Plataforma Vivamente 360° • NR-1
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("### 👥 Total de Colaboradores")
    st.caption("Informe o total cadastrado para calcular o índice de engajamento.")
    total_colaboradores = st.number_input(
        "Total de colaboradores da empresa",
        min_value=1,
        value=st.session_state.get("total_colab", 1),
        step=1,
        key="total_colab",
        help="Número total de funcionários cadastrados (100% base). Usado no indicador de engajamento.",
    )

    st.markdown("---")
    st.markdown("### 🔍 Filtros globais")

    empresas_disp = sorted(base["Empresa"].dropna().unique())
    sel_empresa   = st.multiselect("Empresa", empresas_disp, default=empresas_disp)

    unidades_disp = sorted(base[base["Empresa"].isin(sel_empresa)]["Informe sua unidade"].dropna().unique())
    sel_unidade   = st.multiselect("Unidade", unidades_disp, default=unidades_disp)

    setores_disp  = sorted(base[base["Informe sua unidade"].isin(sel_unidade)]["Informe seu setor / departamento."].dropna().unique())
    sel_setor     = st.multiselect("Setor", setores_disp, default=setores_disp)

    cargos_disp   = sorted(base[base["Informe seu setor / departamento."].isin(sel_setor)]["Informe seu cargo"].dropna().unique())
    sel_cargo     = st.multiselect("Cargo", cargos_disp, default=cargos_disp)

    top_n = st.slider("Top N (rankings)", 3, 10, 5)

    st.markdown("---")
    st.markdown(f'<div style="font-size:11px;color:{COR_MUTED};">Análises IA cacheadas: '
                f'<b>{len(st.session_state.analysis_cache)}</b> &nbsp;·&nbsp; '
                f'Planos salvos: <b>{len(st.session_state.action_plans)}</b></div>',
                unsafe_allow_html=True)
    if st.button("🗑 Limpar cache IA", use_container_width=True):
        st.session_state.analysis_cache = {}
        st.session_state.open_analysis  = {}
        st.rerun()

# ─────────────────────────────────────────────
# FILTRAR BASE — idêntico ao app.py
# ─────────────────────────────────────────────
base_f = base[
    base["Empresa"].isin(sel_empresa) &
    base["Informe sua unidade"].isin(sel_unidade) &
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
unidade_f = reaplicar_agg(base_f, "Informe sua unidade", "Unidade")
empresa_f = reaplicar_agg(base_f, "Empresa", "Empresa")

# ─────────────────────────────────────────────
# HEADER + KPIs — idêntico ao app.py
# ─────────────────────────────────────────────
n_total      = len(base_f)
perc_critico = (base_f["risco_geral"] == "Crítico").mean() * 100 if n_total else 0
perc_alto    = base_f["risco_geral"].isin(["Crítico", "Importante"]).mean() * 100 if n_total else 0
igrp_medio   = base_f["IGRP"].mean() if n_total else 0
nr_medio     = base_f["NR_geral"].mean() if n_total else 0

DADOS_HASH = _make_hash({
    "n": n_total, "nr": round(nr_medio, 3),
    "empresa": sorted(sel_empresa), "setor": sorted(sel_setor), "cargo": sorted(sel_cargo),
})

st.markdown(f"""
<div class="page-header">
  <div>
    <h1>🧠 Dashboard HSE-IT · Riscos Psicossociais</h1>
    <p>Plataforma Vivamente 360° — NR-1 · {n_total} respondentes no filtro atual</p>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-label">Respondentes</div>
    <div class="kpi-value">{n_total:,}</div>
    <div class="kpi-sub">no filtro selecionado</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">IGRP Médio</div>
    <div class="kpi-value">{igrp_medio:.2f}</div>
    <div class="kpi-sub">escala 0–4</div>
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

# ─────────────────────────────────────────────
# TABS — 9 originais + 1 nova (Problemas & Planos)
# ─────────────────────────────────────────────
tabs = st.tabs([
    "📊 Visão Geral",
    "📐 Por Dimensão",
    "❓ Por Questão",
    "🏢 Score de Clima",
    "⚕️ Risco de Saúde",
    "🔥 Impacto Org.",
    "🌡️ Heatmap",
    "👔 Por Cargo",
    "📋 PGR",
    "🚨 Problemas & Planos",
])

# ══════════════════════════════════════════════
# TAB 1 — VISÃO GERAL (Slides 13, 14, 15)
# ══════════════════════════════════════════════
with tabs[0]:

    # ── Slide 13 — Engajamento ────────────────────────────────────────────
    st.markdown('<div class="section-title">Slide 13 · Índice de Engajamento — Questionários Respondidos</div>', unsafe_allow_html=True)

    perc_engaj = (n_total / total_colaboradores * 100) if total_colaboradores > 0 else 0
    perc_engaj = min(perc_engaj, 100.0)

    cor_engaj = COR_VERDE if perc_engaj >= 70 else (COR_AMARELO if perc_engaj >= 50 else COR_VERMELHO)

    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=perc_engaj,
        number=dict(suffix="%", font=dict(size=36, color=COR_TEXTO)),
        delta=dict(reference=70, valueformat=".1f", suffix="%",
                   increasing=dict(color=COR_VERDE), decreasing=dict(color=COR_VERMELHO)),
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=1, tickcolor=COR_MUTED,
                      tickfont=dict(color=COR_MUTED, size=11)),
            bar=dict(color=cor_engaj, thickness=0.25),
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
            steps=[
                dict(range=[0,  50], color="rgba(214,59,59,0.15)"),
                dict(range=[50, 70], color="rgba(245,166,35,0.15)"),
                dict(range=[70,100], color="rgba(45,158,117,0.15)"),
            ],
            threshold=dict(line=dict(color=COR_VERDE, width=3), thickness=0.8, value=70),
        ),
        title=dict(text="Participação na pesquisa", font=dict(size=14, color=COR_MUTED)),
    ))
    fig_gauge.update_layout(
        height=280, margin=dict(l=40, r=40, t=60, b=20),
        paper_bgcolor="rgba(0,0,0,0)", font=dict(family="DM Sans", color=COR_TEXTO),
    )

    col_g1, col_g2, col_g3 = st.columns([1.5, 1, 1])
    with col_g1:
        st.plotly_chart(fig_gauge, use_container_width=True, config=PLOTLY_CONFIG)
    with col_g2:
        st.markdown(f"""
        <div class="kpi-card" style="margin-top:20px;">
            <div class="kpi-label">Responderam</div>
            <div class="kpi-value" style="color:{cor_engaj};">{n_total:,}</div>
            <div class="kpi-sub">de {total_colaboradores:,} colaboradores</div>
        </div>
        """, unsafe_allow_html=True)
    with col_g3:
        status_txt = "✅ Meta atingida" if perc_engaj >= 70 else ("⚠️ Atenção" if perc_engaj >= 50 else "🔴 Baixo engajamento")
        st.markdown(f"""
        <div class="kpi-card" style="margin-top:20px;">
            <div class="kpi-label">Status</div>
            <div class="kpi-value" style="font-size:16px; color:{cor_engaj};">{status_txt}</div>
            <div class="kpi-sub">Meta: 70% | Alerta: 50%</div>
        </div>
        """, unsafe_allow_html=True)

    render_ai_button(
        "engajamento",
        {"perc_engaj": round(perc_engaj, 1), "n_total": n_total,
         "total_colab": total_colaboradores, "hash": DADOS_HASH},
        f"GRÁFICO: Índice de Engajamento\nParticipação: {perc_engaj:.1f}%\n"
        f"Respondentes: {n_total} de {total_colaboradores} colaboradores.\n"
        f"Status: {status_txt}\nMeta: 70% | Alerta: 50%\n"
        f"Analise o engajamento, impacto na representatividade dos dados e recomende ações para ampliar participação.",
        "🤖 Analisar engajamento",
    )

    st.markdown('<hr style="border-color:#2A2D3E; margin:2rem 0;">', unsafe_allow_html=True)

    # ── Slide 14 — IGRP por Dimensão ─────────────────────────────────────
    st.markdown('<div class="section-title">Slide 14 · Índice Geral de Riscos Psicossociais (IGRP) por Dimensão</div>', unsafe_allow_html=True)

    scores_dim = {}
    class_dim  = {}
    for d in DIMENSOES:
        col_s = f"score_{d}"
        scores_dim[d] = base_f[col_s].mean() if col_s in base_f.columns else 0
        class_dim[d]  = score_para_classificacao(scores_dim[d], d)

    labels = [DIMENSOES_LABEL[d] for d in DIMENSOES]
    vals   = [round(scores_dim[d], 3) for d in DIMENSOES]
    cores  = [cor_nivel(class_dim[d]) for d in DIMENSOES]

    fig_igrp = go.Figure()
    fig_igrp.add_trace(go.Bar(
        x=vals, y=labels, orientation="h",
        marker_color=cores, marker_line_width=0,
        text=[f"{v:.2f}" for v in vals],
        textposition="outside", textfont=dict(size=12, color=COR_TEXTO),
    ))
    fig_igrp.add_vline(x=2, line_dash="dot", line_color=COR_MUTED, line_width=1,
                       annotation_text="Ponto central (2.0)", annotation_font_color=COR_MUTED,
                       annotation_position="top right")
    fig_igrp.update_layout(
        xaxis=dict(range=[0, 4.5], title="Score médio (0–4)", gridcolor=COR_BORDA),
        yaxis=dict(title=""),
    )
    plotly_layout(fig_igrp, height=360)
    st.plotly_chart(fig_igrp, use_container_width=True, config=PLOTLY_CONFIG)

    cols_leg = st.columns(4)
    for i, (nivel, cor) in enumerate([("Baixo Risco", COR_VERDE), ("Risco Médio", COR_AMARELO),
                                       ("Risco Moderado", COR_LARANJA), ("Alto Risco", COR_VERMELHO)]):
        with cols_leg[i]:
            st.markdown(f'<div style="display:flex;align-items:center;gap:8px;font-size:12px;color:{COR_MUTED};">'
                        f'<div style="width:12px;height:12px;border-radius:3px;background:{cor};"></div>{nivel}</div>',
                        unsafe_allow_html=True)

    render_ai_button(
        "igrp_dimensoes",
        {"scores": {d: round(scores_dim[d], 3) for d in DIMENSOES}, "hash": DADOS_HASH},
        f"GRÁFICO: IGRP por Dimensão\n"
        + "\n".join(f"- {DIMENSOES_LABEL[d]}: {scores_dim[d]:.2f} ({class_dim[d]})" for d in DIMENSOES)
        + "\nDimensões negativas (alto=pior): Demandas, Relacionamentos.\n"
        f"Identifique dimensões mais críticas e padrões de risco.",
        "🤖 Analisar IGRP por Dimensão",
    )

    st.markdown('<hr style="border-color:#2A2D3E; margin:2rem 0;">', unsafe_allow_html=True)

    # ── Slide 15 — % Trabalhadores por Nível ─────────────────────────────
    st.markdown('<div class="section-title">Slide 15 · % de Trabalhadores por Nível de Risco Global</div>', unsafe_allow_html=True)

    col_pizza, col_barra = st.columns([1, 1])

    with col_pizza:
        dist_risco = base_f["risco_geral"].value_counts()
        ordem      = ["Aceitável", "Moderado", "Importante", "Crítico"]
        labels_p   = [o for o in ordem if o in dist_risco.index]
        vals_p     = [dist_risco[o] for o in labels_p]
        cores_p    = [nivel_geral_para_cor(o) for o in labels_p]

        fig_pizza = go.Figure(go.Pie(
            labels=labels_p, values=vals_p,
            marker=dict(colors=cores_p, line=dict(color=COR_BG, width=2)),
            hole=0.55,
            textinfo="percent",
            textfont=dict(size=13, color=COR_TEXTO),
            insidetextorientation="horizontal",
        ))
        fig_pizza.update_layout(
            annotations=[dict(text=f"<b>{n_total}</b><br>pessoas", x=0.5, y=0.5,
                              font=dict(size=14, color=COR_TEXTO), showarrow=False)],
            showlegend=True,
            legend=dict(orientation="v", x=1, y=0.5, font=dict(size=12)),
        )
        plotly_layout(fig_pizza, height=320)
        st.plotly_chart(fig_pizza, use_container_width=True, config=PLOTLY_CONFIG)

    with col_barra:
        fig_abs = go.Figure()
        for nivel in ordem:
            cnt = dist_risco.get(nivel, 0)
            pct = cnt / n_total * 100 if n_total else 0
            fig_abs.add_trace(go.Bar(
                x=[nivel], y=[cnt], name=nivel,
                marker_color=nivel_geral_para_cor(nivel), marker_line_width=0,
                text=[f"{pct:.1f}%<br>({cnt})"],
                textposition="outside", textfont=dict(size=11, color=COR_TEXTO),
            ))
        fig_abs.update_layout(
            showlegend=False, xaxis=dict(title=""),
            yaxis=dict(title="Nº de trabalhadores", gridcolor=COR_BORDA), bargap=0.35,
        )
        plotly_layout(fig_abs, height=320)
        st.plotly_chart(fig_abs, use_container_width=True, config=PLOTLY_CONFIG)

    dist_data = {n: int(dist_risco.get(n, 0)) for n in ordem}
    render_ai_button(
        "distribuicao_risco_global",
        {"dist": dist_data, "n": n_total, "nr_medio": round(nr_medio, 2), "hash": DADOS_HASH},
        f"GRÁFICO: Distribuição de risco global\nN={n_total}\nDistribuição: {dist_data}\nNR médio: {nr_medio:.2f}\n"
        f"Filtros — Empresa:{sel_empresa}, Setor:{sel_setor}, Cargo:{sel_cargo}\n"
        f"Analise a distribuição, destaque alertas e faça recomendações.",
        "🤖 Analisar distribuição de risco",
    )


# ══════════════════════════════════════════════
# TAB 2 — POR DIMENSÃO (Slide 16)
# ══════════════════════════════════════════════
with tabs[1]:
    st.markdown('<div class="section-title">Slide 16 · Distribuição de Nível de Risco por Dimensão do HSE-IT</div>', unsafe_allow_html=True)

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

    df_dim = pd.DataFrame(rows_dim)

    if not df_dim.empty:
        fig_stack = go.Figure()
        for nivel in NIVEIS_ORDEM:
            sub = df_dim[df_dim["Nível"] == nivel]
            fig_stack.add_trace(go.Bar(
                name=nivel, x=sub["Dimensão"], y=sub["Perc"],
                marker_color=cor_nivel(nivel), marker_line_width=0,
                text=sub["Perc"].apply(lambda v: f"{v:.0f}%" if v >= 5 else ""),
                textposition="inside", textfont=dict(size=11, color="#fff"),
            ))
        fig_stack.update_layout(
            barmode="stack", xaxis=dict(title=""),
            yaxis=dict(title="% de respondentes", gridcolor=COR_BORDA, range=[0, 105]),
            legend=dict(orientation="h", y=1.08, x=0, font=dict(size=11)),
        )
        plotly_layout(fig_stack, height=420)
        st.plotly_chart(fig_stack, use_container_width=True, config=PLOTLY_CONFIG)

    alto_risco_dim = {
        DIMENSOES_LABEL[d]: round(base_f[f"class_{d}"].eq("Alto Risco").mean() * 100, 1)
        for d in DIMENSOES if f"class_{d}" in base_f.columns
    }
    render_ai_button(
        "distribuicao_dimensoes",
        {"alto_risco": alto_risco_dim, "hash": DADOS_HASH},
        f"GRÁFICO: Distribuição por dimensão — % em Alto Risco:\n"
        + "\n".join(f"- {k}: {v}%" for k, v in alto_risco_dim.items())
        + f"\nTotal respondentes: {n_total}\nIdentifique dimensões mais comprometidas e sugira intervenções.",
        "🤖 Analisar distribuição por dimensão",
    )

    st.markdown('<div class="section-title">Tabela detalhada por dimensão</div>', unsafe_allow_html=True)
    if not df_dim.empty:
        pivot  = df_dim.pivot_table(index="Dimensão", columns="Nível", values="Perc", fill_value=0)
        pivot  = pivot.reindex(columns=[c for c in NIVEIS_ORDEM if c in pivot.columns])
        pivot  = pivot.round(1)
        styled = pivot.style.map(_perc_row_color).format("{:.1f}%")
        st.dataframe(styled, use_container_width=True, height=320)

        render_ai_button(
            "tabela_dimensoes_detalhe",
            {"pivot": {d: {n: round(pivot.loc[d, n], 1) for n in pivot.columns if d in pivot.index}
                       for d in pivot.index.tolist()[:7]}, "hash": DADOS_HASH},
            f"TABELA: Distribuição detalhada por dimensão e nível de risco\n"
            + "\n".join(f"- {d}: Alto Risco={alto_risco_dim.get(d,0)}%" for d in alto_risco_dim)
            + f"\nAnalise padrões, quais dimensões têm maior concentração em risco elevado.",
            "🤖 Analisar tabela de dimensões",
        )


# ══════════════════════════════════════════════
# TAB 3 — POR QUESTÃO (Slide 17)
# ══════════════════════════════════════════════
with tabs[2]:
    st.markdown('<div class="section-title">Slide 17 · Distribuição de Respostas por Questão do HSE-IT</div>', unsafe_allow_html=True)
    st.caption("🔴 Questões negativas (Demandas, Relacionamentos): Frequentemente/Sempre = maior risco. "
               "🟢 Questões positivas: Nunca/Raramente = maior risco.")

    col_q_detect = [c for c in base_f.columns if c.startswith("Q") and c[1:].isdigit()]
    if not col_q_detect:
        known = {"Empresa","Informe sua unidade","Informe seu setor / departamento.","Informe seu cargo",
                 "IGRP","NR_geral","risco_geral","qtd_dimensoes_alto"}
        col_q_detect = [c for c in base_f.columns
                        if c not in known
                        and not c.startswith("score_")
                        and not c.startswith("NR_")
                        and not c.startswith("class_")
                        and not c.startswith("P_")
                        and not c.startswith("S_")]

    if col_q_detect:
        dim_por_q = {}
        mapa_dim_q = {
            "Demandas":        [1,2,3,4,5,6,7,8],
            "Controle":        [9,10,11,12,13,14],
            "Apoio_Chefia":    [15,16,17,18,19],
            "Apoio_Colegas":   [20,21,22,23],
            "Relacionamentos": [24,25,26,27],
            "Cargo":           [28,29,30,31,32],
            "Mudanca":         [33,34,35],
        }
        for d, qs in mapa_dim_q.items():
            for q in qs:
                dim_por_q[q] = d

        sel_dim_q = st.selectbox(
            "Filtrar por dimensão",
            ["Todas"] + [DIMENSOES_LABEL[d] for d in DIMENSOES],
            key="sel_dim_q"
        )

        rows_q = []
        for i, col in enumerate(col_q_detect[:35], start=1):
            vc      = base_f[col].value_counts().reindex([0,1,2,3,4], fill_value=0)
            total_q = vc.sum()
            dim_q   = dim_por_q.get(i, "")
            is_neg  = i in QS_NEGATIVAS
            cores_q = COR_RESPOSTAS_NEG if is_neg else COR_RESPOSTAS_POS
            for resp_val, resp_label, cor_r in zip(
                [0,1,2,3,4],
                ["Nunca","Raramente","Às vezes","Frequentemente","Sempre"],
                cores_q
            ):
                cnt = vc.get(resp_val, 0)
                rows_q.append({
                    "Q":        f"Q{i:02d}",
                    "Índice":   i,
                    "Dimensão": DIMENSOES_LABEL.get(dim_q, dim_q),
                    "Resposta": resp_label,
                    "Valor":    resp_val,
                    "Qtd":      cnt,
                    "Perc":     cnt / total_q * 100 if total_q else 0,
                    "Cor":      cor_r,
                    "Negativa": is_neg,
                })

        df_q = pd.DataFrame(rows_q)
        if sel_dim_q != "Todas":
            df_q = df_q[df_q["Dimensão"] == sel_dim_q]

        qs_filtradas = df_q["Q"].unique().tolist()
        resp_labels  = ["Nunca","Raramente","Às vezes","Frequentemente","Sempre"]

        fig_q = go.Figure()
        for resp_label in resp_labels:
            sub_r = df_q[df_q["Resposta"] == resp_label]
            fig_q.add_trace(go.Bar(
                name=resp_label, x=sub_r["Q"], y=sub_r["Perc"],
                marker_color=sub_r["Cor"].tolist(), marker_line_width=0,
                text=sub_r["Perc"].apply(lambda v: f"{v:.0f}%" if v >= 8 else ""),
                textposition="inside", textfont=dict(size=10, color="#fff"),
                showlegend=False,
            ))
        fig_q.update_layout(
            barmode="stack",
            xaxis=dict(title="Questão", tickangle=-45),
            yaxis=dict(title="% de respondentes", gridcolor=COR_BORDA, range=[0, 105]),
        )
        plotly_layout(fig_q, height=420, margin=dict(l=20, r=20, t=50, b=60))
        st.plotly_chart(fig_q, use_container_width=True, config=PLOTLY_CONFIG)

        col_ln, col_lp = st.columns(2)
        with col_ln:
            st.markdown("**🔴 Questões negativas** (Demandas / Relacionamentos):")
            for label, cor in zip(resp_labels, COR_RESPOSTAS_NEG):
                st.markdown(f'<span style="background:{cor};padding:2px 8px;border-radius:4px;color:#fff;font-size:11px;">{label}</span>', unsafe_allow_html=True)
        with col_lp:
            st.markdown("**🟢 Questões positivas** (demais dimensões):")
            for label, cor in zip(resp_labels, COR_RESPOSTAS_POS):
                st.markdown(f'<span style="background:{cor};padding:2px 8px;border-radius:4px;color:#fff;font-size:11px;">{label}</span>', unsafe_allow_html=True)

        # score médio por questão
        st.markdown('<div class="section-title">Score médio por questão (0–4)</div>', unsafe_allow_html=True)
        scores_q = []
        for i, col in enumerate(col_q_detect[:35], start=1):
            dim_q    = dim_por_q.get(i, "")
            media_q  = base_f[col].mean()
            classe_q = score_para_classificacao(media_q, dim_q) if dim_q else ""
            scores_q.append({
                "Q":            f"Q{i:02d}",
                "Score":        round(media_q, 2),
                "Dimensão":     DIMENSOES_LABEL.get(dim_q, dim_q),
                "Classificação":classe_q,
                "Polaridade":   "Negativa" if i in QS_NEGATIVAS else "Positiva",
            })
        df_sq = pd.DataFrame(scores_q)
        if sel_dim_q != "Todas":
            df_sq = df_sq[df_sq["Dimensão"] == sel_dim_q]

        fig_sq = go.Figure(go.Bar(
            x=df_sq["Q"], y=df_sq["Score"],
            marker_color=[cor_nivel(c) for c in df_sq["Classificação"]],
            marker_line_width=0,
            text=df_sq["Score"].apply(lambda v: f"{v:.2f}"),
            textposition="outside", textfont=dict(size=10, color=COR_TEXTO),
        ))
        fig_sq.update_layout(
            xaxis=dict(title="Questão", tickangle=-45),
            yaxis=dict(title="Score médio", gridcolor=COR_BORDA, range=[0, 4.8]),
        )
        plotly_layout(fig_sq, height=350, margin=dict(l=20, r=20, t=20, b=60))
        st.plotly_chart(fig_sq, use_container_width=True, config=PLOTLY_CONFIG)

        # top questões mais críticas para o prompt
        top_q_criticas = df_sq.sort_values("Score", ascending=(sel_dim_q not in ["Todas"] or True)).head(5)
        top_q_txt = "\n".join(f"- {r['Q']} ({r['Dimensão']}): score={r['Score']:.2f} — {r['Classificação']} [{r['Polaridade']}]"
                               for _, r in top_q_criticas.iterrows())
        render_ai_button(
            f"questoes_{sel_dim_q.replace(' ','_')}",
            {"dimensao": sel_dim_q, "top_q": df_sq[["Q","Score","Classificação"]].head(10).to_dict(), "hash": DADOS_HASH},
            f"GRÁFICO: Score médio por questão — Filtro: {sel_dim_q}\n"
            f"Questões analisadas: {len(df_sq)}\nTop questões mais críticas:\n{top_q_txt}\n"
            f"Polaridade: questões negativas (alto=pior): Q01-Q08, Q24-Q27.\n"
            f"Identifique as questões mais preocupantes e recomende intervenções específicas.",
            "🤖 Analisar questões",
        )

    else:
        st.warning("Colunas de questões individuais não encontradas no base.parquet.")


# ══════════════════════════════════════════════
# TAB 4 — SCORE DE CLIMA (Slide 18) — Radar chart
# ══════════════════════════════════════════════
with tabs[3]:
    st.markdown('<div class="section-title">Slide 18 · Score de Clima Psicossocial — Radar por Criticidade</div>', unsafe_allow_html=True)
    st.caption("Cada linha no radar representa um grupo (setor/cargo/unidade/empresa). "
               "Os eixos são as 7 dimensões HSE-IT. Score 0–4.")

    tabs_clima = st.tabs(["Por Setor", "Por Cargo", "Por Unidade", "Por Empresa"])

    def radar_chart(df_g, col_grupo, titulo):
        if df_g is None or df_g.empty:
            st.info("Sem dados disponíveis.")
            return

        top      = df_g.nlargest(top_n, "NR_geral")
        labels_r = [DIMENSOES_LABEL[d] for d in DIMENSOES if f"score_{d}" in top.columns]
        dims_r   = [d for d in DIMENSOES if f"score_{d}" in top.columns]

        if not dims_r:
            st.info("Dados de score por dimensão não disponíveis.")
            return

        fig = go.Figure()
        for idx, (_, row) in enumerate(top.iterrows()):
            scores_r = [float(row.get(f"score_{d}", 0)) for d in dims_r]
            scores_r_closed = scores_r + [scores_r[0]]
            labels_closed   = labels_r + [labels_r[0]]
            cor = CORES_RADAR[idx % len(CORES_RADAR)]
            grupo_nome = str(row[col_grupo])
            classif    = row.get("classificacao", "")
            fig.add_trace(go.Scatterpolar(
                r=scores_r_closed, theta=labels_closed,
                fill="toself",
                fillcolor=f"rgba({int(cor[1:3],16)},{int(cor[3:5],16)},{int(cor[5:7],16)},0.12)",
                opacity=0.85, line=dict(color=cor, width=2),
                name=f"{grupo_nome} ({classif})",
            ))

        fig.update_layout(
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                angularaxis=dict(tickfont=dict(size=11, color=COR_TEXTO), linecolor=COR_BORDA),
                radialaxis=dict(
                    range=[0, 4], gridcolor=COR_BORDA,
                    tickvals=[1, 2, 3, 4], ticktext=["1", "2", "3", "4"],
                    tickfont=dict(size=9, color=COR_MUTED),
                ),
            ),
            showlegend=True,
            legend=dict(orientation="h", y=-0.2, font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
            title=dict(text=titulo, font=dict(size=13, color=COR_TEXTO), x=0),
        )
        plotly_layout(fig, height=480, margin=dict(l=60, r=60, t=60, b=120))
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

        cols_show = [col_grupo, "n_colaboradores", "NR_geral", "IGRP",
                     "perc_risco_alto", "perc_critico", "classificacao"]
        cols_show = [c for c in cols_show if c in top.columns]
        df_show   = top[cols_show].copy().rename(columns={
            "n_colaboradores": "N", "NR_geral": "NR Geral",
            "perc_risco_alto": "% Alto/Crítico", "perc_critico": "% Crítico",
            "classificacao":   "Classificação",
        })
        df_show["NR Geral"] = df_show["NR Geral"].round(2)
        df_show["IGRP"]     = df_show["IGRP"].round(2)
        if "% Alto/Crítico" in df_show.columns:
            df_show["% Alto/Crítico"] = (df_show["% Alto/Crítico"]*100).round(1).astype(str) + "%"
        if "% Crítico" in df_show.columns:
            df_show["% Crítico"] = (df_show["% Crítico"]*100).round(1).astype(str) + "%"
        st.dataframe(df_show, use_container_width=True, hide_index=True,
                     height=min(400, (len(df_show)+1)*38))

        # botão IA para radar + tabela
        grupos_txt = "\n".join(
            f"- {row[col_grupo]}: NR={row['NR_geral']:.2f} ({row.get('classificacao','')})"
            for _, row in top.iterrows()
        )
        render_ai_button(
            f"radar_{col_grupo.lower()}",
            {"col_grupo": col_grupo, "grupos": top[col_grupo].tolist(),
             "nr_lista": top["NR_geral"].round(2).tolist(), "hash": DADOS_HASH},
            f"RADAR + TABELA: Score de Clima por {col_grupo}\nTop {top_n}:\n{grupos_txt}\n"
            f"Dimensões avaliadas: {', '.join(labels_r)}\n"
            f"Analise o perfil de risco de cada grupo, compare dimensões e aponte prioridades.",
            f"🤖 Analisar radar por {col_grupo}",
        )

    mapa_clima = [
        (setor_f,   "Setor",   f"Top {top_n} Setores — Score por Dimensão"),
        (cargo_f,   "Cargo",   f"Top {top_n} Cargos — Score por Dimensão"),
        (unidade_f, "Unidade", f"Top {top_n} Unidades — Score por Dimensão"),
        (empresa_f, "Empresa", f"Empresas — Score por Dimensão"),
    ]
    n_empresas = len(empresa_f) if empresa_f is not None and not empresa_f.empty else 0

    for tab_c, (df_c, col_c, titulo_c) in zip(tabs_clima, mapa_clima):
        with tab_c:
            if col_c == "Empresa" and n_empresas <= 1:
                st.info("Análise por empresa disponível apenas quando há mais de uma empresa nos dados.")
            else:
                radar_chart(df_c, col_c, titulo_c)


# ══════════════════════════════════════════════
# TAB 5 — RISCO DE SAÚDE (Slide 19)
# ══════════════════════════════════════════════
with tabs[4]:
    st.markdown('<div class="section-title">Slide 19 · Risco de Impacto na Saúde — Probabilidade (P) por Dimensão</div>', unsafe_allow_html=True)
    st.caption("Eixo: P discreto (1=Baixo Risco · 2=Risco Médio · 3=Risco Moderado · 4=Alto Risco) "
               "calculado a partir do score médio de cada dimensão.")

    def chart_probabilidade(df_g, col_grupo, titulo, ai_key):
        if df_g is None or df_g.empty:
            st.info("Sem dados disponíveis.")
            return

        top     = df_g.nlargest(top_n, "NR_geral").copy()
        dims_ok = [d for d in DIMENSOES if f"score_{d}" in top.columns]
        if not dims_ok:
            st.info("Dados de score não disponíveis.")
            return

        for d in dims_ok:
            top[f"P_calc_{d}"] = top[f"score_{d}"].apply(lambda s: score_para_P(s, d))

        fig = go.Figure()
        cores_d = [COR_VERMELHO, COR_LARANJA, COR_AMARELO, COR_VERDE, COR_ACCENT, "#B97CF7", "#5DCAA5"]
        for d, cor_d in zip(dims_ok, cores_d):
            fig.add_trace(go.Bar(
                name=DIMENSOES_LABEL[d],
                x=top[f"P_calc_{d}"], y=top[col_grupo],
                orientation="h", marker_color=cor_d, marker_line_width=0,
                text=top[f"P_calc_{d}"].astype(str),
                textposition="inside", textfont=dict(size=10, color="#fff"),
            ))

        fig.update_layout(
            barmode="group",
            title=dict(text=titulo, font=dict(size=13, color=COR_TEXTO), x=0),
            xaxis=dict(title="Probabilidade P (1–4)", gridcolor=COR_BORDA, range=[0, 5],
                       tickvals=[1,2,3,4], ticktext=["1 — Baixo","2 — Médio","3 — Moderado","4 — Alto"]),
            yaxis=dict(title="", autorange="reversed"),
            legend=dict(orientation="h", y=-0.25, font=dict(size=10)),
        )
        plotly_layout(fig, height=max(300, top_n * 60 + 100), margin=dict(l=20, r=20, t=40, b=120))
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

        top_txt = "\n".join(
            f"- {row[col_grupo]}: NR={row['NR_geral']:.2f}, "
            + ", ".join(f"{DIMENSOES_LABEL[d]}=P{int(row.get(f'P_calc_{d}',1))}" for d in dims_ok[:4])
            for _, row in top.iterrows()
        )
        render_ai_button(
            ai_key,
            {"col_grupo": col_grupo, "grupos": top[col_grupo].tolist(),
             "nr_lista": top["NR_geral"].round(2).tolist(), "hash": DADOS_HASH},
            f"GRÁFICO: Probabilidade P por Dimensão — {col_grupo}\n{top_txt}\n"
            f"P=4 indica maior risco de adoecimento. Identifique dimensões e grupos críticos.",
            f"🤖 Analisar probabilidade por {col_grupo}",
        )

    chart_probabilidade(setor_f, "Setor", f"Top {top_n} Setores — P por Dimensão", "prob_setor")
    chart_probabilidade(cargo_f, "Cargo", f"Top {top_n} Cargos — P por Dimensão", "prob_cargo")


# ══════════════════════════════════════════════
# TAB 6 — IMPACTO ORG. (Slide 20)
# ══════════════════════════════════════════════
with tabs[5]:
    st.markdown('<div class="section-title">Slide 20 · Impacto Organizacional Relacionado ao Risco</div>', unsafe_allow_html=True)

    st.markdown("##### Top setores por NR alto — Risco de Absenteísmo")
    st.caption("Barras horizontais empilhadas: distribuição dos 4 níveis de risco por setor.")

    if not setor_f.empty:
        top_abs = setor_f.nlargest(top_n, "NR_geral")

        niveis_abs = [
            ("Aceitável",  "perc_aceitavel",  COR_VERDE),
            ("Moderado",   "perc_moderado",   COR_AMARELO),
            ("Importante", "perc_importante", COR_LARANJA),
            ("Crítico",    "perc_critico",    COR_VERMELHO),
        ]

        fig_abs2 = go.Figure()
        for nivel_lbl, col_p, cor_n in niveis_abs:
            if col_p not in top_abs.columns: continue
            vals_perc = (top_abs[col_p] * 100).round(1)
            fig_abs2.add_trace(go.Bar(
                name=nivel_lbl, y=top_abs["Setor"], x=vals_perc,
                orientation="h", marker_color=cor_n, marker_line_width=0,
                text=vals_perc.apply(lambda v: f"{v:.1f}%" if v >= 5 else ""),
                textposition="inside", textfont=dict(size=11, color="#fff"),
            ))

        fig_abs2.update_layout(
            barmode="stack",
            xaxis=dict(title="% de trabalhadores", gridcolor=COR_BORDA, range=[0, 105]),
            yaxis=dict(title="", autorange="reversed"),
            legend=dict(orientation="h", y=1.08, x=0),
        )
        plotly_layout(fig_abs2, height=max(300, top_n * 52 + 80))
        st.plotly_chart(fig_abs2, use_container_width=True, config=PLOTLY_CONFIG)

        top_abs_txt = "\n".join(
            f"- {row['Setor']}: NR={row['NR_geral']:.2f}, "
            f"Crítico={row.get('perc_critico',0)*100:.0f}%, Alto={row.get('perc_risco_alto',0)*100:.0f}%"
            for _, row in top_abs.iterrows()
        )
        render_ai_button(
            "impacto_absenteismo",
            {"setores": top_abs["Setor"].tolist(), "nr_lista": top_abs["NR_geral"].round(2).tolist(), "hash": DADOS_HASH},
            f"GRÁFICO: Risco de Absenteísmo por Setor\n{top_abs_txt}\n"
            f"Analise setores com maior risco de absenteísmo e presenteísmo. Sugira ações preventivas.",
            "🤖 Analisar risco de absenteísmo",
        )

    st.markdown('<hr style="border-color:#2A2D3E; margin:2rem 0;">', unsafe_allow_html=True)

    st.markdown("##### Top setores por maior P × S — Probabilidade de Adoecimento")
    st.caption("Barras horizontais por dimensão (não empilhadas). Ordenados pela soma dos NR.")

    if not setor_f.empty:
        cols_nr_dim = [f"NR_{d}" for d in DIMENSOES if f"NR_{d}" in setor_f.columns]
        if cols_nr_dim:
            setor_ps = setor_f.copy()
            setor_ps["score_ps_total"] = setor_ps[cols_nr_dim].sum(axis=1)
            top_adoec = setor_ps.nlargest(top_n, "score_ps_total")

            cores_d = [COR_VERMELHO, COR_LARANJA, COR_AMARELO,
                       COR_VERDE, COR_ACCENT, "#B97CF7", "#5DCAA5"]

            fig_adoec = go.Figure()
            for d, cor_d in zip(DIMENSOES, cores_d):
                col_nr = f"NR_{d}"
                if col_nr not in top_adoec.columns: continue
                fig_adoec.add_trace(go.Bar(
                    name=DIMENSOES_LABEL[d], y=top_adoec["Setor"], x=top_adoec[col_nr],
                    orientation="h", marker_color=cor_d, marker_line_width=0,
                    text=top_adoec[col_nr].round(1).astype(str),
                    textposition="outside", textfont=dict(size=10, color=COR_TEXTO),
                ))

            fig_adoec.update_layout(
                barmode="group",
                xaxis=dict(title="NR médio (1–16)", gridcolor=COR_BORDA),
                yaxis=dict(title="", autorange="reversed"),
                legend=dict(orientation="h", y=-0.3, font=dict(size=10)),
            )
            plotly_layout(fig_adoec, height=max(300, top_n * 65 + 100), margin=dict(l=20, r=20, t=20, b=100))
            st.plotly_chart(fig_adoec, use_container_width=True, config=PLOTLY_CONFIG)

            top_adoec_txt = "\n".join(
                f"- {row['Setor']}: NR_total={row['score_ps_total']:.1f}"
                for _, row in top_adoec.iterrows()
            )
            render_ai_button(
                "impacto_adoecimento",
                {"setores": top_adoec["Setor"].tolist(), "hash": DADOS_HASH},
                f"GRÁFICO: Probabilidade de Adoecimento P×S por Setor\n{top_adoec_txt}\n"
                f"Identifique setores e dimensões com maior risco de adoecimento. Recomende ações prioritárias.",
                "🤖 Analisar probabilidade de adoecimento",
            )


# ══════════════════════════════════════════════
# TAB 7 — HEATMAP (Slide 21)
# ══════════════════════════════════════════════
with tabs[6]:
    st.markdown('<div class="section-title">Slide 21 · Heatmap — Nível de Risco (NR) por Dimensão</div>', unsafe_allow_html=True)

    visao_hm   = st.radio("Agrupar por:", ["Setor", "Cargo", "Unidade"], horizontal=True, key="hm_visao")
    mapa_visao = {"Setor": setor_f, "Cargo": cargo_f, "Unidade": unidade_f}
    df_hm_src  = mapa_visao.get(visao_hm, setor_f)

    if df_hm_src is not None and not df_hm_src.empty:
        col_grupo_hm = visao_hm
        cols_nr_hm   = [f"NR_{d}" for d in DIMENSOES if f"NR_{d}" in df_hm_src.columns]
        labels_hm    = [DIMENSOES_LABEL[d] for d in DIMENSOES if f"NR_{d}" in df_hm_src.columns]

        df_hm  = df_hm_src.nlargest(min(20, len(df_hm_src)), "NR_geral")
        z_hm   = df_hm[cols_nr_hm].values
        y_hm   = df_hm[col_grupo_hm].tolist()
        annot  = [[f"{val:.1f}" for val in row] for row in z_hm]

        fig_hm = go.Figure(go.Heatmap(
            z=z_hm, x=labels_hm, y=y_hm,
            text=annot, texttemplate="%{text}",
            textfont=dict(size=11, color=COR_TEXTO),
            colorscale=[[0.0, COR_VERDE],[0.33, COR_AMARELO],[0.66, COR_LARANJA],[1.0, COR_VERMELHO]],
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
        plotly_layout(fig_hm, height=max(400, len(y_hm) * 32 + 80))
        st.plotly_chart(fig_hm, use_container_width=True, config=PLOTLY_CONFIG)

        top3 = df_hm.head(3)
        top3_txt = "\n".join(f"- {row[visao_hm]}: NR={row['NR_geral']:.2f} ({row.get('classificacao','?')})"
                             for _, row in top3.iterrows())
        render_ai_button(
            f"heatmap_{visao_hm.lower()}",
            {"visao": visao_hm, "top_grupos": top3[visao_hm].tolist(),
             "top_nr": top3["NR_geral"].round(2).tolist(), "hash": DADOS_HASH},
            f"HEATMAP: NR por Dimensão — {visao_hm}\nTop 3:\n{top3_txt}\n"
            f"Dimensões: {', '.join(labels_hm)}\n"
            f"Analise padrões de risco, clusters críticos e prioridades de intervenção.",
            f"🤖 Analisar heatmap por {visao_hm}",
        )
    else:
        st.info(f"Dados de {visao_hm} não disponíveis.")


# ══════════════════════════════════════════════
# TAB 8 — POR CARGO (Slide 22)
# ══════════════════════════════════════════════
with tabs[7]:
    st.markdown('<div class="section-title">Slide 22 · Análise Detalhada por Cargo</div>', unsafe_allow_html=True)

    if not cargo_f.empty:
        cargos_lista = cargo_f["Cargo"].tolist()
        cargo_sel    = st.selectbox("Selecione o cargo:", cargos_lista)
        row_cargo    = cargo_f[cargo_f["Cargo"] == cargo_sel].iloc[0]

        n_resp_cargo = int(row_cargo.get("n_colaboradores", 0))

        st.markdown(f"""
        <div class="kpi-grid">
          <div class="kpi-card">
            <div class="kpi-label">N Respostas</div>
            <div class="kpi-value">{n_resp_cargo}</div>
            <div class="kpi-sub">respondentes neste cargo</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">NR Geral</div>
            <div class="kpi-value">{row_cargo.get('NR_geral',0):.2f}</div>
            <div class="kpi-sub">escala 1–16</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Classificação</div>
            <div class="kpi-value" style="font-size:18px;">{row_cargo.get('classificacao','—')}</div>
            <div class="kpi-sub">nível de risco geral</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Em Risco Alto/Crítico</div>
            <div class="kpi-value" style="color:{COR_LARANJA};">{row_cargo.get('perc_risco_alto',0)*100:.1f}%</div>
            <div class="kpi-sub">Importante + Crítico</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        scores_cargo = []
        labels_radar = []
        for d in DIMENSOES:
            col_s = f"score_{d}"
            if col_s in row_cargo:
                scores_cargo.append(round(float(row_cargo[col_s]), 3))
                labels_radar.append(DIMENSOES_LABEL[d])

        if scores_cargo:
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=scores_cargo + [scores_cargo[0]],
                theta=labels_radar + [labels_radar[0]],
                fill="toself",
                fillcolor="rgba(79,142,247,0.15)",
                line=dict(color=COR_ACCENT, width=2),
                name=cargo_sel,
            ))
            fig_radar.update_layout(
                polar=dict(
                    bgcolor="rgba(0,0,0,0)",
                    angularaxis=dict(tickfont=dict(size=11, color=COR_TEXTO), linecolor=COR_BORDA),
                    radialaxis=dict(range=[0, 4], gridcolor=COR_BORDA,
                                   tickfont=dict(size=10, color=COR_MUTED)),
                ),
                showlegend=False, dragmode=False,
            )
            plotly_layout(fig_radar, height=380)
            st.plotly_chart(fig_radar, use_container_width=True, config=PLOTLY_CONFIG)

            radar_txt = "\n".join(f"- {l}: {s:.2f}" for l, s in zip(labels_radar, scores_cargo))
            render_ai_button(
                f"cargo_radar_{cargo_sel.replace(' ','_')[:30]}",
                {"cargo": cargo_sel, "scores": dict(zip(labels_radar, scores_cargo)),
                 "nr_geral": float(row_cargo.get('NR_geral', 0)), "hash": DADOS_HASH},
                f"RADAR: Perfil de Risco — Cargo: {cargo_sel}\nNR Geral: {row_cargo.get('NR_geral',0):.2f} ({row_cargo.get('classificacao','?')})\n"
                f"N respondentes: {n_resp_cargo}\nScores por dimensão:\n{radar_txt}\n"
                f"Analise o perfil de risco deste cargo e recomende ações prioritárias.",
                f"🤖 Analisar perfil do cargo",
            )

        st.markdown('<div class="section-title">NR por Dimensão — Detalhamento</div>', unsafe_allow_html=True)

        tab_dim_cargo = []
        base_cargo    = base_f[base_f["Informe seu cargo"] == cargo_sel]
        n_resp_dim    = len(base_cargo)

        for d in DIMENSOES:
            score_val = float(row_cargo.get(f"score_{d}", 0))
            nr_val    = float(row_cargo.get(f"NR_{d}", 0))
            p_val     = score_para_P(score_val, d)
            s_val     = round(nr_val / p_val, 2) if p_val > 0 else 0.0
            class_val = score_para_classificacao(score_val, d)

            tab_dim_cargo.append({
                "Dimensão":               DIMENSOES_LABEL[d],
                "N Respostas":            n_resp_dim,
                "Score HSE-IT":           round(score_val, 2),
                "Probabilidade (P)":      p_val,
                "Severidade (S)":         s_val,
                "Classificação de Risco": class_val,
                "NR (P × S)":             round(nr_val, 2),
                "Polaridade":             "Negativa" if d in DIM_NEGATIVAS else "Positiva",
            })

        df_dim_cargo = pd.DataFrame(tab_dim_cargo)

        class_counts = df_dim_cargo["Classificação de Risco"].value_counts()
        class_predom = class_counts.index[0] if not class_counts.empty else "—"
        cor_predom   = cor_nivel(class_predom)

        st.markdown(f"""
        <div style="margin-bottom:12px; padding:10px 16px; background:{COR_CARD};
             border:1px solid {COR_BORDA}; border-radius:8px; display:inline-block;">
            <span style="font-size:11px; color:{COR_MUTED}; text-transform:uppercase;">
                Classificação Predominante:
            </span>
            <span style="font-size:14px; font-weight:600; color:{cor_predom}; margin-left:8px;">
                {class_predom}
            </span>
        </div>
        """, unsafe_allow_html=True)

        styled_cargo = (
            df_dim_cargo.style
            .map(_nr_row_color, subset=["NR (P × S)"])
            .map(_p_row_color,  subset=["Probabilidade (P)"])
            .map(_class_row_color, subset=["Classificação de Risco"])
            .format({"Score HSE-IT": "{:.2f}", "Severidade (S)": "{:.2f}", "NR (P × S)": "{:.2f}"})
        )
        st.dataframe(styled_cargo, use_container_width=True, hide_index=True)

        tabela_cargo_txt = "\n".join(
            f"- {r['Dimensão']}: Score={r['Score HSE-IT']:.2f}, P={r['Probabilidade (P)']}, "
            f"NR={r['NR (P × S)']:.2f} — {r['Classificação de Risco']}"
            for _, r in df_dim_cargo.iterrows()
        )
        render_ai_button(
            f"tabela_cargo_{cargo_sel.replace(' ','_')[:30]}",
            {"cargo": cargo_sel, "classificacao_predom": class_predom,
             "nr_geral": float(row_cargo.get('NR_geral', 0)), "hash": DADOS_HASH},
            f"TABELA: NR por Dimensão — Cargo: {cargo_sel}\nClassificação predominante: {class_predom}\n"
            f"NR Geral: {row_cargo.get('NR_geral',0):.2f}\nDetalhamento:\n{tabela_cargo_txt}\n"
            f"Analise quais dimensões exigem intervenção imediata neste cargo.",
            "🤖 Analisar tabela por cargo",
        )

        st.markdown(f'<div class="section-title">Distribuição individual ({n_resp_dim} respondentes)</div>',
                    unsafe_allow_html=True)

        dist_cargo = base_cargo["risco_geral"].value_counts().reindex(NIVEIS_GERAL_ORDEM, fill_value=0)
        fig_dist_c = go.Figure(go.Bar(
            x=dist_cargo.index, y=dist_cargo.values,
            marker_color=[nivel_geral_para_cor(n) for n in dist_cargo.index],
            marker_line_width=0,
            text=dist_cargo.values,
            textposition="outside", textfont=dict(size=12, color=COR_TEXTO),
        ))
        fig_dist_c.update_layout(
            xaxis=dict(title=""), yaxis=dict(title="Nº de respondentes", gridcolor=COR_BORDA),
            showlegend=False,
        )
        plotly_layout(fig_dist_c, height=280)
        st.plotly_chart(fig_dist_c, use_container_width=True, config=PLOTLY_CONFIG)

        dist_cargo_data = {n: int(dist_cargo.get(n, 0)) for n in NIVEIS_GERAL_ORDEM}
        render_ai_button(
            f"dist_individual_cargo_{cargo_sel.replace(' ','_')[:30]}",
            {"cargo": cargo_sel, "distribuicao": dist_cargo_data, "hash": DADOS_HASH},
            f"GRÁFICO: Distribuição individual de risco — Cargo: {cargo_sel}\n"
            f"N respondentes: {n_resp_dim}\nDistribuição: {dist_cargo_data}\n"
            f"Analise a distribuição de risco individual e impacto para a saúde dos trabalhadores.",
            "🤖 Analisar distribuição individual",
        )

    else:
        st.info("Dados de cargo não disponíveis.")


# ══════════════════════════════════════════════
# TAB 9 — PGR (Slide 23)
# ══════════════════════════════════════════════
with tabs[8]:
    st.markdown('<div class="section-title">Slide 23 · PGR — Programa de Gerenciamento de Riscos</div>', unsafe_allow_html=True)
    st.caption("Análise por Unidade / Setor / Cargo × Categorias — Matriz NR (P × S)")

    visao_pgr = st.radio("Dimensão de análise:", ["Setor", "Cargo", "Unidade"],
                         horizontal=True, key="pgr_visao")
    mapa_pgr  = {
        "Setor":   (setor_f,   "Setor"),
        "Cargo":   (cargo_f,   "Cargo"),
        "Unidade": (unidade_f if unidade_f is not None else pd.DataFrame(), "Unidade"),
    }
    df_pgr_src, col_pgr = mapa_pgr[visao_pgr]

    if df_pgr_src is not None and not df_pgr_src.empty:

        rows_pgr = []
        for _, row in df_pgr_src.iterrows():
            rec = {
                col_pgr:         row[col_pgr],
                "N":             int(row.get("n_colaboradores", 0)),
                "NR Geral":      round(float(row.get("NR_geral", 0)), 2),
                "Classificação": row.get("classificacao", ""),
            }
            for d in DIMENSOES:
                score_v = float(row.get(f"score_{d}", 0))
                nr_v    = float(row.get(f"NR_{d}",    0))
                p_v     = score_para_P(score_v, d)
                s_v     = round(nr_v / p_v, 2) if p_v > 0 else 0.0
                lbl     = DIMENSOES_LABEL[d]
                rec[f"Score — {lbl}"]  = round(score_v, 2)
                rec[f"P — {lbl}"]      = p_v
                rec[f"S — {lbl}"]      = s_v
                rec[f"Class. — {lbl}"] = score_para_classificacao(score_v, d)
                rec[f"NR — {lbl}"]     = round(nr_v, 2)
            rows_pgr.append(rec)

        df_pgr_full = pd.DataFrame(rows_pgr).sort_values("NR Geral", ascending=False).reset_index(drop=True)

        col_view = st.radio(
            "Visualizar:",
            ["Resumo (NR por dimensão)", "Score + P + S + Classificação", "Completo"],
            horizontal=True, key="pgr_col_view"
        )

        nr_cols    = [f"NR — {DIMENSOES_LABEL[d]}" for d in DIMENSOES]
        score_cols = [f"Score — {DIMENSOES_LABEL[d]}" for d in DIMENSOES]
        p_cols     = [f"P — {DIMENSOES_LABEL[d]}"     for d in DIMENSOES]
        s_cols     = [f"S — {DIMENSOES_LABEL[d]}"     for d in DIMENSOES]
        class_cols = [f"Class. — {DIMENSOES_LABEL[d]}" for d in DIMENSOES]

        if col_view == "Resumo (NR por dimensão)":
            cols_show_pgr = [col_pgr, "N", "NR Geral", "Classificação"] + nr_cols
        elif col_view == "Score + P + S + Classificação":
            cols_show_pgr = [col_pgr, "N"] + score_cols + p_cols + s_cols + class_cols
        else:
            cols_show_pgr = [col_pgr, "N", "NR Geral", "Classificação"] + score_cols + p_cols + s_cols + class_cols + nr_cols

        cols_show_pgr = [c for c in cols_show_pgr if c in df_pgr_full.columns]
        df_pgr_show   = df_pgr_full[cols_show_pgr]

        num_cols_fmt  = {c: "{:.2f}" for c in (nr_cols + score_cols + s_cols) if c in df_pgr_show.columns}
        style_pgr = df_pgr_show.style.format(num_cols_fmt)

        if col_view in ["Resumo (NR por dimensão)", "Completo"]:
            nr_present = [c for c in nr_cols if c in df_pgr_show.columns]
            if nr_present:
                style_pgr = style_pgr.map(_nr_row_color, subset=["NR Geral"] + nr_present)

        if col_view in ["Score + P + S + Classificação", "Completo"]:
            p_present     = [c for c in p_cols    if c in df_pgr_show.columns]
            class_present = [c for c in class_cols if c in df_pgr_show.columns]
            if p_present:
                style_pgr = style_pgr.map(_p_row_color, subset=p_present)
            if class_present:
                style_pgr = style_pgr.map(_class_row_color, subset=class_present)

        st.dataframe(style_pgr, use_container_width=True,
                     height=min(600, (len(df_pgr_full)+1) * 38))

        top3_pgr = df_pgr_src.head(3)
        top3_pgr_txt = "\n".join(
            f"- {row[col_pgr]}: NR={row['NR_geral']:.2f}, {row.get('classificacao','?')}"
            for _, row in top3_pgr.iterrows()
        )
        render_ai_button(
            f"pgr_tabela_{visao_pgr.lower()}",
            {"visao": visao_pgr, "view": col_view,
             "top_nr": top3_pgr["NR_geral"].round(2).tolist(),
             "top_grupos": top3_pgr[col_pgr].tolist(), "hash": DADOS_HASH},
            f"TABELA PGR: Matriz de Risco por {visao_pgr} — Visão: {col_view}\nTop 3:\n{top3_pgr_txt}\n"
            f"Total: {len(df_pgr_src)} {visao_pgr}s\n"
            f"Analise a matriz, identifique prioridades para o PGR e sugira medidas conforme NR-1.",
            f"🤖 Analisar tabela PGR por {visao_pgr}",
        )

        st.markdown('<hr style="border-color:#2A2D3E; margin:2rem 0;">', unsafe_allow_html=True)
        st.markdown("##### Matriz de Risco — Heatmap PGR")

        cols_nr_pgr = [f"NR_{d}" for d in DIMENSOES if f"NR_{d}" in df_pgr_src.columns]
        labels_pgr  = [DIMENSOES_LABEL[d] for d in DIMENSOES if f"NR_{d}" in df_pgr_src.columns]
        df_pgr_hm   = df_pgr_src.sort_values("NR_geral", ascending=False)

        z_pgr     = df_pgr_hm[cols_nr_pgr].values
        y_pgr     = df_pgr_hm[col_pgr].tolist()
        annot_pgr = [[f"{v:.1f}" for v in row] for row in z_pgr]

        fig_pgr = go.Figure(go.Heatmap(
            z=z_pgr, x=labels_pgr, y=y_pgr,
            text=annot_pgr, texttemplate="%{text}",
            textfont=dict(size=11),
            colorscale=[[0.0, COR_VERDE],[0.25, COR_AMARELO],[0.55, COR_LARANJA],[1.0, COR_VERMELHO]],
            zmin=1, zmax=16,
            colorbar=dict(
                tickvals=[2, 6, 10, 14],
                ticktext=["Aceitável","Moderado","Importante","Crítico"],
                tickfont=dict(color=COR_TEXTO, size=10),
                title=dict(text="NR", font=dict(color=COR_TEXTO)),
                bgcolor="rgba(0,0,0,0)", bordercolor=COR_BORDA,
            ),
        ))
        fig_pgr.update_layout(
            xaxis=dict(title="", tickangle=-30, side="top"),
            yaxis=dict(title="", autorange="reversed"),
        )
        plotly_layout(fig_pgr, height=max(400, len(y_pgr) * 30 + 80))
        st.plotly_chart(fig_pgr, use_container_width=True, config=PLOTLY_CONFIG)

        st.markdown(f"""
        <div style="display:flex;gap:16px;flex-wrap:wrap;font-size:12px;color:{COR_MUTED};margin-top:8px;">
          <span><b style="color:{COR_VERDE}">■</b> Aceitável (NR 1–4)</span>
          <span><b style="color:{COR_AMARELO}">■</b> Moderado (NR 5–8)</span>
          <span><b style="color:{COR_LARANJA}">■</b> Importante (NR 9–12)</span>
          <span><b style="color:{COR_VERMELHO}">■</b> Crítico (NR 13–16)</span>
        </div>
        """, unsafe_allow_html=True)

        render_ai_button(
            f"pgr_heatmap_{visao_pgr.lower()}",
            {"visao": visao_pgr, "top_grupos": top3_pgr[col_pgr].tolist(),
             "top_nr": top3_pgr["NR_geral"].round(2).tolist(), "hash": DADOS_HASH},
            f"HEATMAP PGR: Matriz de Risco por {visao_pgr}\nTop 3:\n{top3_pgr_txt}\n"
            f"Dimensões: {', '.join(labels_pgr)}\n"
            f"Analise a matriz PGR, identifique clusters críticos e prioridades de intervenção conforme NR-1.",
            f"🤖 Analisar heatmap PGR por {visao_pgr}",
        )

    else:
        st.info(f"Dados de {visao_pgr} não disponíveis.")


# ══════════════════════════════════════════════
# TAB 10 — PROBLEMAS & PLANOS DE AÇÃO
# ══════════════════════════════════════════════
with tabs[9]:
    st.markdown(f"""
    <div class="page-header">
        <div>
            <h2 style="margin:0;font-size:18px;">🚨 Problemas Identificados & Planos de Ação</h2>
            <p style="margin:4px 0 0;font-size:13px;color:{COR_MUTED};">
                Lista automática de riscos · Gere planos 5W2H por problema
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Invalida cache se dados mudaram
    if st.session_state.problems_hash != DADOS_HASH:
        st.session_state.problems_cache = None
        st.session_state.problems_hash  = DADOS_HASH

    def gerar_lista_problemas():
        problemas = []

        # Setores
        for _, row in setor_f.iterrows():
            nr = float(row.get("NR_geral", 0))
            if nr < 1: continue
            classe = classificar_NR(nr)
            n_col  = int(row.get("n_colaboradores", 0))
            perc_a = float(row.get("perc_risco_alto", 0)) * 100
            worst_dim, worst_nr = "", 0
            for d in DIMENSOES:
                v = float(row.get(f"NR_{d}", 0))
                if v > worst_nr: worst_nr = v; worst_dim = DIMENSOES_LABEL[d]
            problemas.append({
                "id": f"setor_{row['Setor']}", "tipo": "Setor", "grupo": row["Setor"],
                "nr": nr, "classe": classe, "n": n_col, "perc_alto": perc_a,
                "worst_dim": worst_dim, "worst_nr": worst_nr,
                "descricao": (f"Setor '{row['Setor']}' com NR={nr:.1f} ({classe}) — "
                              f"{perc_a:.0f}% dos {n_col} colaboradores em risco alto/crítico. "
                              f"Dimensão mais crítica: {worst_dim} (NR={worst_nr:.1f})."),
                "plan": None,
            })

        # Dimensões
        for d in DIMENSOES:
            col_s = f"score_{d}"
            if col_s not in base_f.columns: continue
            score_v  = base_f[col_s].mean()
            classe   = score_para_classificacao(score_v, d)
            perc_alt = (base_f[f"class_{d}"] == "Alto Risco").mean() * 100 if f"class_{d}" in base_f.columns else 0
            problemas.append({
                "id": f"dim_{d}", "tipo": "Dimensão", "grupo": DIMENSOES_LABEL[d],
                "nr": score_para_P(score_v, d) * 4.0, "classe": classe, "n": n_total, "perc_alto": perc_alt,
                "worst_dim": DIMENSOES_LABEL[d], "worst_nr": score_v,
                "descricao": (f"Dimensão '{DIMENSOES_LABEL[d]}' com score={score_v:.2f} ({classe}) — "
                              f"{perc_alt:.0f}% dos respondentes em Alto Risco nessa dimensão."),
                "plan": None,
            })

        # Cargos
        for _, row in cargo_f.iterrows():
            nr = float(row.get("NR_geral", 0))
            if nr < 1: continue
            classe = classificar_NR(nr)
            n_col  = int(row.get("n_colaboradores", 0))
            perc_a = float(row.get("perc_risco_alto", 0)) * 100
            problemas.append({
                "id": f"cargo_{row['Cargo']}", "tipo": "Cargo", "grupo": row["Cargo"],
                "nr": nr, "classe": classe, "n": n_col, "perc_alto": perc_a,
                "worst_dim": "", "worst_nr": 0,
                "descricao": (f"Cargo '{row['Cargo']}' com NR={nr:.1f} ({classe}) — "
                              f"{perc_a:.0f}% dos {n_col} profissionais em risco alto/crítico."),
                "plan": None,
            })

        return sorted(problemas, key=lambda x: -x["nr"])[:50]

    if st.session_state.problems_cache is None:
        st.session_state.problems_cache = gerar_lista_problemas()

    problemas = st.session_state.problems_cache

    if not problemas:
        st.success("✅ Nenhum problema identificado nos dados filtrados.")
    else:
        col_f1, col_f2 = st.columns([2, 3])
        with col_f1:
            filtro_tipo = st.selectbox("Filtrar por tipo", ["Todos","Setor","Dimensão","Cargo"], key="prob_tipo_filter")
        with col_f2:
            todas_classes = ["Crítico","Importante","Moderado","Aceitável","Alto Risco","Risco Moderado","Risco Médio","Baixo Risco"]
            filtro_classe = st.multiselect("Filtrar por classificação", todas_classes, default=todas_classes, key="prob_classe_filter")

        probs_filtrados = [p for p in problemas
                           if (filtro_tipo == "Todos" or p["tipo"] == filtro_tipo)
                           and p["classe"] in filtro_classe]

        st.markdown(f'<div style="font-size:12px;color:{COR_MUTED};margin-bottom:1rem;">'
                    f'Exibindo <b>{len(probs_filtrados)}</b> de <b>{len(problemas)}</b> problemas</div>',
                    unsafe_allow_html=True)

        saved_plan_ids = {p["metadata"]["problem_id"]: i
                          for i, p in enumerate(st.session_state.action_plans) if "metadata" in p}

        for prob in probs_filtrados:
            prob_id    = prob["id"]
            cor_classe = {"Crítico": COR_VERMELHO, "Importante": COR_LARANJA,
                          "Alto Risco": COR_VERMELHO, "Risco Moderado": COR_AMARELO}.get(prob["classe"], COR_CINZA)
            badge_tipo = {"Setor": (COR_ACCENT,"#1e2a4a"), "Dimensão": (COR_PURPLE,"#1e1a3a"),
                          "Cargo": (COR_AMARELO,"#2a2010")}.get(prob["tipo"], (COR_MUTED, COR_CARD))
            has_saved  = prob_id in saved_plan_ids

            with st.expander(
                f"{'🔴' if prob['classe'] in ['Crítico','Alto Risco'] else '🟠' if prob['classe'] in ['Importante','Risco Moderado'] else '🟡'} "
                f"{prob['tipo']}: {prob['grupo']} · {prob['classe']} · NR={prob['nr']:.1f}"
                + (" ✅ Plano gerado" if has_saved else ""),
                expanded=False,
            ):
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

                if has_saved:
                    saved_idx  = saved_plan_ids[prob_id]
                    saved_plan = st.session_state.action_plans[saved_idx]["plan"]
                    progress   = compute_progress(saved_plan)
                    prog_pct   = int(progress * 100)
                    n_acoes    = len(saved_plan.get("acoes", []))
                    n_done     = int(progress * n_acoes)

                    st.markdown(f"""
                    <div style="margin-bottom:12px;">
                        <div style="display:flex;justify-content:space-between;font-size:11px;color:{COR_MUTED};margin-bottom:4px;">
                            <span>Progresso</span><span>{n_done}/{n_acoes} ações concluídas</span>
                        </div>
                        <div class="progress-bar-outer"><div class="progress-bar-inner" style="width:{prog_pct}%;"></div></div>
                    </div>
                    """, unsafe_allow_html=True)

                    edited_df = render_plan_card(saved_plan, f"saved_{prob_id}", editable=True)

                    col_upd, col_del, col_new = st.columns([2, 2, 2])
                    with col_upd:
                        if st.button("💾 Salvar alterações", key=f"upd_{prob_id}", use_container_width=True, type="primary"):
                            st.session_state.action_plans[saved_idx]["plan"] = {**saved_plan, "acoes": df_to_acoes(edited_df)}
                            st.success("✅ Plano atualizado!"); st.rerun()
                    with col_del:
                        if st.button("🗑 Remover plano", key=f"del_{prob_id}", use_container_width=True):
                            st.session_state.action_plans.pop(saved_idx); st.rerun()
                    with col_new:
                        if st.button("🔄 Regerar plano", key=f"regen_{prob_id}", use_container_width=True):
                            st.session_state.action_plans.pop(saved_idx); st.rerun()

                    # ── Card PDCA — renderizado abaixo dos controles do 5W2H ──────
                    _render_pdca_card(
                        saved     = st.session_state.action_plans[saved_idx],
                        prob_id   = prob_id,
                        saved_idx = saved_idx,
                    )
                else:
                    if st.button(f"🤖 Gerar Plano 5W2H para '{prob['grupo']}'",
                                 key=f"gen_{prob_id}", use_container_width=True, type="primary"):
                        with st.spinner(f"🧠 Gerando plano para '{prob['grupo']}'..."):
                            try:
                                rag_ctx = _buscar_rag(prob["descricao"])
                                prompt  = (f"PROBLEMA HSE-IT:\n{prob['descricao']}\n\n"
                                           f"Tipo:{prob['tipo']} | Grupo:{prob['grupo']}\n"
                                           f"Classe:{prob['classe']} | NR:{prob['nr']:.1f}\n"
                                           f"N:{prob['n']} | % alto:{prob['perc_alto']:.0f}%\n"
                                           + (f"Dimensão crítica:{prob['worst_dim']}\n" if prob["worst_dim"] else "")
                                           + (f"\n{rag_ctx}" if rag_ctx else "")
                                           + "\n\nGere plano de ação 5W2H completo e específico.")
                                raw    = call_groq(SYSTEM_PLAN, prompt)
                                result = parse_json_response(raw)
                                if result.get("tipo") == "plano_acao" and result.get("acoes"):
                                    for a in result["acoes"]: a.setdefault("status", "⏳ Pendente")
                                    st.session_state.action_plans.append({
                                        "plan": result,
                                        "metadata": {"problem_id": prob_id, "tipo": prob["tipo"], "grupo": prob["grupo"]},
                                        "created_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
                                        # ── PDCA baseline ──────────────────────────────────────────────
                                        "nr_baseline":            prob["nr"],
                                        "perc_alto_baseline":     prob["perc_alto"],
                                        "parquet_mtime_baseline": _parquet_mtime(),
                                    })
                                    st.success(f"✅ Plano gerado para '{prob['grupo']}'!")
                                    st.rerun()
                                else:
                                    st.error("❌ Modelo não retornou plano válido. Tente novamente.")
                            except Exception as e:
                                st.error(f"❌ Erro ao gerar plano: {e}")
                                st.markdown(f'<pre style="font-size:10px;color:{COR_VERMELHO};">'
                                            f'{traceback.format_exc()}</pre>', unsafe_allow_html=True)

        # ── Planos salvos ─────────────────────────────────────────────────
        st.markdown('<hr style="border-color:#2A2D3E;margin:2.5rem 0;">', unsafe_allow_html=True)
        st.markdown(f'<div class="section-title">📋 Planos Salvos ({len(st.session_state.action_plans)})</div>',
                    unsafe_allow_html=True)

        orphan = [(i, p) for i, p in enumerate(st.session_state.action_plans) if "metadata" not in p]
        if orphan:
            st.caption("Planos sem vínculo a problema específico:")
            for idx, saved in orphan:
                with st.expander(f"📌 {saved['plan'].get('problema','Plano')[:80]} · {saved.get('created_at','—')}"):
                    edited_df = render_plan_card(saved["plan"], f"orphan_{idx}")
                    col_s, col_d = st.columns([1, 1])
                    with col_s:
                        if st.button("💾 Salvar", key=f"save_orphan_{idx}", type="primary"):
                            st.session_state.action_plans[idx]["plan"]["acoes"] = df_to_acoes(edited_df)
                            st.success("✅ Atualizado!"); st.rerun()
                    with col_d:
                        if st.button("🗑 Remover", key=f"del_orphan_{idx}"):
                            st.session_state.action_plans.pop(idx); st.rerun()

        if not st.session_state.action_plans:
            st.markdown(f'<div style="text-align:center;padding:40px 20px;color:{COR_MUTED};">'
                        f'<div style="font-size:40px;margin-bottom:12px;">📋</div>'
                        f'<div>Nenhum plano gerado ainda.<br>Clique em <b>Gerar Plano 5W2H</b> em qualquer problema acima.</div></div>',
                        unsafe_allow_html=True)


# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown(f"""
<div style="margin-top:3rem;padding-top:1.5rem;border-top:1px solid {COR_BORDA};
     display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
  <span style="font-size:12px;color:{COR_MUTED};">
    🧠 Dashboard HSE-IT · Plataforma Vivamente 360° · NR-1 · IA por Groq + Llama 3.3
  </span>
  <span style="font-size:11px;color:{COR_MUTED};font-family:'DM Mono',monospace;">
    base.parquet · setor.parquet · cargo.parquet · unidade.parquet
  </span>
</div>
""", unsafe_allow_html=True)
