import json
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go

# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="OrgPulse · Risk Intelligence",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS mínimo: remove chrome do Streamlit e trava scroll da página host
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');
#MainMenu, footer, header,
[data-testid="stDecoration"],
[data-testid="stToolbar"] { display: none !important; }
section[data-testid="stMain"] { overflow: hidden !important; background: #0B0D12 !important; }
.block-container { padding: 0 !important; max-width: 100% !important; overflow: hidden !important; }
[data-testid="stSidebar"] { background: #0F1117 !important; border-right: 1px solid #1A1D28 !important; }
[data-testid="stSidebar"] > div:first-child { padding: 1.5rem 1.2rem; }
[data-testid="stSidebarContent"] label {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.72rem !important; color: #4A4F6A !important;
    font-weight: 600 !important; letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
}
</style>
""", unsafe_allow_html=True)

# =========================
# CONSTANTS
# =========================
COL_UNIDADE = "Informe sua unidade"
COL_SETOR   = "Informe seu setor / departamento."
COL_CARGO   = "Informe seu cargo"

DIMENSAO_LABELS = {
    "score_Demandas":        "Demandas",
    "score_Controle":        "Controle",
    "score_Apoio_Chefia":    "Apoio da Chefia",
    "score_Apoio_Colegas":   "Apoio dos Colegas",
    "score_Relacionamentos": "Relacionamentos",
    "score_Cargo":           "Cargo",
    "score_Comunicacao":     "Comunicação",
}
RISK_COLORS = {"Normal": "#00C9A7", "Alto": "#FFB547", "Crítico": "#FF4D6A"}

def risk_color(v):
    if v > 70: return "#FF4D6A"
    if v > 50: return "#FFB547"
    return "#00C9A7"

def risk_cls(v):
    if v > 70: return "danger"
    if v > 50: return "warn"
    return "ok"

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
with st.sidebar:
    st.markdown("""
    <div style='font-family:"DM Serif Display",serif;font-size:1.15rem;
                color:#E0E2EE;padding-bottom:0.8rem;
                border-bottom:1px solid #1A1D28;margin-bottom:1.2rem;'>
        Filtros
    </div>""", unsafe_allow_html=True)

    empresa_opts = sorted(df_base["Empresa"].unique())
    empresa = st.multiselect("Empresa", empresa_opts, default=empresa_opts)

    unidade_opts = sorted(df_base[COL_UNIDADE].unique())
    unidade = st.multiselect("Unidade", unidade_opts, default=unidade_opts)

    setor_opts = sorted(df_base[COL_SETOR].unique())
    setor = st.multiselect("Setor", setor_opts, default=setor_opts)

    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
    if st.button("↺  Limpar filtros", use_container_width=True):
        st.rerun()

    st.markdown("""
    <div style='margin-top:2rem;font-size:0.6rem;color:#1E2235;
                letter-spacing:0.06em;font-family:"DM Mono",monospace;'>
        OrgPulse · HSE Model · v2.0
    </div>""", unsafe_allow_html=True)

df = df_base[
    df_base["Empresa"].isin(empresa) &
    df_base[COL_UNIDADE].isin(unidade) &
    df_base[COL_SETOR].isin(setor)
]

# =========================
# COMPUTE METRICS
# =========================
total    = len(df)
igrp_med = round(df["IGRP"].mean(), 2) if total else 0
pct_alto = round(df["risco_geral"].isin(["Alto","Crítico"]).mean() * 100, 1) if total else 0
pct_crit = round((df["risco_geral"] == "Crítico").mean() * 100, 1) if total else 0

risco_df = df["risco_geral"].value_counts().reset_index()
risco_df.columns = ["Risco", "Qtd"]
risco_df["Cor"] = risco_df["Risco"].map(RISK_COLORS)

setor_chart = (
    df.groupby(COL_SETOR)["IGRP"].mean()
    .reset_index()
    .rename(columns={COL_SETOR: "Setor"})
    .sort_values("IGRP", ascending=True)
    .tail(8)
)
setor_chart["Cor"] = setor_chart["IGRP"].apply(risk_color)

dim_cols = list(DIMENSAO_LABELS.keys())
dim_df = df[dim_cols].mean().reset_index()
dim_df.columns = ["Col", "Score"]
dim_df["Dimensão"] = dim_df["Col"].map(DIMENSAO_LABELS)
dim_df["Cor"] = dim_df["Score"].apply(risk_color)
dim_df = dim_df.sort_values("Score", ascending=True)

try:
    setor_tab = (
        df.groupby(COL_SETOR)
        .agg({"IGRP": "mean", "risco_geral": lambda x: x.isin(["Alto","Crítico"]).mean()})
        .reset_index()
    )
    setor_tab.columns = ["Setor", "IGRP", "PctRisco"]
    setor_tab = setor_tab.sort_values("IGRP", ascending=False).head(8)
except Exception as e:
    setor_tab = pd.DataFrame({"Setor": [str(e)], "IGRP": [0.0], "PctRisco": [0.0]})

try:
    cargo_tab = (
        df.groupby(COL_CARGO)
        .agg({"IGRP": "mean", "risco_geral": lambda x: x.isin(["Alto","Crítico"]).mean()})
        .reset_index()
    )
    cargo_tab.columns = ["Cargo", "IGRP", "PctRisco"]
    cargo_tab = cargo_tab.sort_values("IGRP", ascending=False).head(8)
except Exception as e:
    cargo_tab = pd.DataFrame({"Cargo": [str(e)], "IGRP": [0.0], "PctRisco": [0.0]})

# =========================
# BUILD PLOTLY TRACE DICTS
# =========================
trace_donut = dict(
    type="pie",
    labels=risco_df["Risco"].tolist(),
    values=risco_df["Qtd"].tolist(),
    hole=0.62,
    marker=dict(colors=risco_df["Cor"].tolist(), line=dict(width=0)),
    textinfo="percent",
    textfont=dict(family="DM Sans", size=11, color="#E0E2EE"),
    hovertemplate="<b>%{label}</b><br>%{value} colaboradores<extra></extra>",
)

trace_setor = dict(
    type="bar",
    x=setor_chart["IGRP"].tolist(),
    y=setor_chart["Setor"].tolist(),
    orientation="h",
    marker=dict(color=setor_chart["Cor"].tolist(), line=dict(width=0), opacity=0.88),
    text=[f"{v:.1f}" for v in setor_chart["IGRP"]],
    textposition="outside",
    textfont=dict(color="#5A5F7A", size=9),
    hovertemplate="<b>%{y}</b><br>IGRP: %{x:.1f}<extra></extra>",
)

trace_dim = dict(
    type="bar",
    x=dim_df["Score"].tolist(),
    y=dim_df["Dimensão"].tolist(),
    orientation="h",
    marker=dict(color=dim_df["Cor"].tolist(), line=dict(width=0), opacity=0.85),
    text=[f"{v:.2f}" for v in dim_df["Score"]],
    textposition="outside",
    textfont=dict(color="#5A5F7A", size=9),
    hovertemplate="<b>%{y}</b><br>Score: %{x:.2f}<extra></extra>",
)

# =========================
# BUILD HTML TABLES
# =========================
def igrp_bar_html(val):
    pct = min(val / 100 * 100, 100)
    col = risk_color(val)
    return (
        f'<div class="bar-cell">'
        f'<span class="mono" style="color:{col};min-width:30px">{val:.1f}</span>'
        f'<div class="bar-bg"><div class="bar-fill" style="width:{pct:.0f}%;background:{col}"></div></div>'
        f'</div>'
    )

def make_table(data, col_name):
    rows = "".join(
        f'<tr><td title="{r[col_name]}">{r[col_name]}</td>'
        f'<td>{igrp_bar_html(r["IGRP"])}</td>'
        f'<td class="mono" style="color:#5A5F7A">{r["PctRisco"]*100:.0f}%</td></tr>'
        for _, r in data.iterrows()
    )
    return (
        f'<table class="ptable"><thead><tr>'
        f'<th>{col_name}</th><th>IGRP</th><th>% Risco</th>'
        f'</tr></thead><tbody>{rows}</tbody></table>'
    )

table_setor_html = make_table(setor_tab, "Setor")
table_cargo_html = make_table(cargo_tab, "Cargo")

# =========================
# BUILD PROBLEM PILLS
# =========================
def prob_pill(row, idx):
    c = ["d","w","n"][min(idx, 2)]
    col = ["#FF4D6A","#FFB547","#00C9A7"][min(idx, 2)]
    return (
        f'<div class="prob-card prob-{c}">'
        f'<span class="prob-name">{row["Dimensão"]}</span>'
        f'<span class="prob-score" style="color:{col}">{row["Score"]:.2f}</span>'
        f'</div>'
    )

probs_html = "".join(
    prob_pill(row, i)
    for i, (_, row) in enumerate(dim_df.head(3).iterrows())
)

# KPI classes
igrp_c = risk_cls(igrp_med)
alto_c = risk_cls(pct_alto)
crit_c = "danger" if pct_crit > 10 else "warn" if pct_crit > 3 else "ok"

COLOR_MAP = {"ok": "#00C9A7", "warn": "#FFB547", "danger": "#FF4D6A", "neutral": "#2A2F50"}

# =========================
# FULL PANEL HTML
# =========================
panel = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');
*, *::before, *::after {{ box-sizing: border-box; margin:0; padding:0; }}
html, body {{
  height: 100%; background: #0B0D12; color: #E0E2EE;
  font-family: 'DM Sans', sans-serif; overflow: hidden;
}}
.root {{
  display: grid;
  grid-template-rows: 52px 96px 1fr 1fr;
  height: 100vh;
  padding: 0 14px 10px 14px;
  gap: 8px;
}}
/* HEADER */
.header {{
  display:flex; align-items:center; gap:12px;
  border-bottom:1px solid #1A1D28;
}}
.logo {{ font-family:'DM Serif Display',serif; font-size:1.5rem; color:#E0E2EE; letter-spacing:-0.02em; }}
.logo em {{ color:#00C9A7; font-style:normal; }}
.sub {{ font-size:0.63rem; color:#2E3248; letter-spacing:0.06em; }}
.badge {{
  margin-left:auto; background:#0F1117; border:1px solid #1A1D28;
  border-radius:5px; padding:3px 10px; font-family:'DM Mono',monospace;
  font-size:0.62rem; color:#00C9A7; letter-spacing:0.1em;
}}
/* KPIS */
.kpis {{ display:grid; grid-template-columns:repeat(4,1fr); gap:8px; }}
.kpi {{
  background:#0F1117; border:1px solid #1A1D28; border-radius:9px;
  padding:8px 12px; display:flex; flex-direction:column;
  justify-content:space-between; position:relative; overflow:hidden;
}}
.kpi-accent {{ position:absolute; top:0;left:0;right:0; height:2px; border-radius:9px 9px 0 0; }}
.kpi-label {{ font-size:0.57rem; font-weight:600; letter-spacing:0.13em; text-transform:uppercase; color:#3A3F5A; margin-top:4px; }}
.kpi-val {{ font-family:'DM Serif Display',serif; font-size:2rem; line-height:1; letter-spacing:-0.02em; }}
.kpi-sub {{ font-size:0.57rem; color:#1E2235; font-style:italic; }}
/* ROWS */
.charts {{ display:grid; grid-template-columns:0.85fr 1.5fr 0.95fr; gap:8px; }}
.tables {{ display:grid; grid-template-columns:1fr 1fr; gap:8px; }}
.card {{
  background:#0F1117; border:1px solid #1A1D28; border-radius:9px;
  padding:8px 11px 5px; display:flex; flex-direction:column; overflow:hidden;
}}
.card-label {{ font-size:0.55rem; font-weight:600; letter-spacing:0.13em; text-transform:uppercase; color:#00C9A7; margin-bottom:1px; }}
.card-title {{ font-family:'DM Serif Display',serif; font-size:0.88rem; color:#C8CAD8; margin-bottom:3px; }}
.cw {{ flex:1; min-height:0; }}
/* PILLS */
.probs {{ display:flex; flex-direction:column; gap:5px; margin-top:5px; flex:1; }}
.prob-card {{ display:flex; justify-content:space-between; align-items:center; padding:7px 10px; border-radius:7px; border-left:3px solid; }}
.prob-d {{ background:#16101A; border-color:#FF4D6A; }}
.prob-w {{ background:#16130F; border-color:#FFB547; }}
.prob-n {{ background:#0F1310; border-color:#00C9A7; }}
.prob-name {{ font-size:0.73rem; color:#A0A3B8; }}
.prob-score {{ font-family:'DM Mono',monospace; font-size:0.88rem; font-weight:500; }}
/* TABLE */
.tbl-wrap {{ flex:1; overflow-y:auto; margin-top:3px; }}
.tbl-wrap::-webkit-scrollbar {{ width:3px; }}
.tbl-wrap::-webkit-scrollbar-thumb {{ background:#1A1D28; border-radius:2px; }}
.ptable {{ width:100%; border-collapse:collapse; font-size:0.7rem; }}
.ptable thead tr {{ border-bottom:1px solid #1A1D28; }}
.ptable th {{ text-align:left; padding:4px 6px; font-size:0.54rem; font-weight:600; letter-spacing:0.1em; text-transform:uppercase; color:#3A3F5A; }}
.ptable tbody tr {{ border-bottom:1px solid #111420; }}
.ptable tbody tr:hover {{ background:#13151E; }}
.ptable td {{ padding:5px 6px; color:#8B8FA8; }}
.ptable td:first-child {{ color:#C8CAD8; max-width:150px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.mono {{ font-family:'DM Mono',monospace; }}
.bar-cell {{ display:flex; align-items:center; gap:5px; }}
.bar-bg {{ flex:1; height:3px; background:#1A1D28; border-radius:2px; overflow:hidden; }}
.bar-fill {{ height:100%; border-radius:2px; }}
.dual {{ display:grid; grid-template-columns:1fr 1fr; gap:0; }}
.dual-right {{ border-left:1px solid #1A1D28; padding-left:12px; }}
</style>
</head>
<body>
<div class="root">

  <!-- HEADER -->
  <div class="header">
    <div>
      <div class="logo">Org<em>Pulse</em></div>
      <div class="sub">Psychosocial Risk Intelligence &nbsp;·&nbsp; Modelo HSE</div>
    </div>
    <div class="badge">LIVE &nbsp;·&nbsp; {total:,} respondentes</div>
  </div>

  <!-- KPIs -->
  <div class="kpis">
    <div class="kpi">
      <div class="kpi-accent" style="background:#2A2F50"></div>
      <div class="kpi-label">Colaboradores</div>
      <div class="kpi-val" style="color:#E0E2EE">{total:,}</div>
      <div class="kpi-sub">respondentes ativos</div>
    </div>
    <div class="kpi">
      <div class="kpi-accent" style="background:{COLOR_MAP[igrp_c]}"></div>
      <div class="kpi-label">IGRP Médio</div>
      <div class="kpi-val" style="color:{COLOR_MAP[igrp_c]}">{igrp_med}</div>
      <div class="kpi-sub">índice geral de risco psicossocial</div>
    </div>
    <div class="kpi">
      <div class="kpi-accent" style="background:{COLOR_MAP[alto_c]}"></div>
      <div class="kpi-label">Alto / Crítico</div>
      <div class="kpi-val" style="color:{COLOR_MAP[alto_c]}">{pct_alto}%</div>
      <div class="kpi-sub">colaboradores em risco elevado</div>
    </div>
    <div class="kpi">
      <div class="kpi-accent" style="background:{COLOR_MAP[crit_c]}"></div>
      <div class="kpi-label">Risco Crítico</div>
      <div class="kpi-val" style="color:{COLOR_MAP[crit_c]}">{pct_crit}%</div>
      <div class="kpi-sub">requer intervenção imediata</div>
    </div>
  </div>

  <!-- CHART ROW -->
  <div class="charts">

    <div class="card">
      <div class="card-label">Visão Geral</div>
      <div class="card-title">Distribuição de Risco</div>
      <div class="cw" id="c-donut"></div>
    </div>

    <div class="card">
      <div class="card-label">Por Setor</div>
      <div class="card-title">IGRP Médio por Setor</div>
      <div class="cw" id="c-setor"></div>
    </div>

    <div class="card">
      <div class="card-label">Atenção Imediata</div>
      <div class="card-title">Dimensões Críticas</div>
      <div class="probs">{probs_html}</div>
    </div>

  </div>

  <!-- TABLE ROW -->
  <div class="tables">

    <div class="card">
      <div class="card-label">Diagnóstico HSE</div>
      <div class="card-title">Score por Dimensão</div>
      <div class="cw" id="c-dim"></div>
    </div>

    <div class="card dual">
      <div style="display:flex;flex-direction:column;overflow:hidden;">
        <div class="card-label">Detalhamento</div>
        <div class="card-title">Top Setores</div>
        <div class="tbl-wrap">{table_setor_html}</div>
      </div>
      <div class="dual-right" style="display:flex;flex-direction:column;overflow:hidden;">
        <div class="card-label">Detalhamento</div>
        <div class="card-title">Top Cargos</div>
        <div class="tbl-wrap">{table_cargo_html}</div>
      </div>
    </div>

  </div>

</div>

<script>
const B = {{
  paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
  font:{{family:'DM Sans',color:'#5A5F7A',size:10}},
  margin:{{l:0,r:6,t:4,b:0}}, showlegend:false,
}};

Plotly.newPlot('c-donut',
  {json.dumps([trace_donut])},
  {{...B, annotations:[{{
    text:'<b>{total:,}</b>', x:0.5, y:0.5, showarrow:false,
    font:{{family:'DM Serif Display',size:24,color:'#E0E2EE'}}
  }}]}},
  {{responsive:true,displayModeBar:false}}
);

Plotly.newPlot('c-setor',
  {json.dumps([trace_setor])},
  {{...B,
    xaxis:{{showgrid:true,gridcolor:'#13151E',zeroline:false,tickfont:{{color:'#3A3F5A',size:8}}}},
    yaxis:{{showgrid:false,tickfont:{{color:'#8B8FA8',size:8}}}},
  }},
  {{responsive:true,displayModeBar:false}}
);

Plotly.newPlot('c-dim',
  {json.dumps([trace_dim])},
  {{...B,
    xaxis:{{showgrid:true,gridcolor:'#13151E',zeroline:false,tickfont:{{color:'#3A3F5A',size:8}}}},
    yaxis:{{showgrid:false,tickfont:{{color:'#8B8FA8',size:8}}}},
  }},
  {{responsive:true,displayModeBar:false}}
);
</script>
</body>
</html>"""

components.html(panel, height=1000, scrolling=False)
