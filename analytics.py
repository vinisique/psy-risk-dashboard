"""
analytics.py — Módulo compartilhado HSE-IT · Vivamente 360°
============================================================
Centraliza toda a lógica analítica usada pelo Dashboard (app.py)
e pelo Agente de IA (agente_ia.py).

Importação:
    from analytics import (
        load_all_data, reaplicar_agg, build_context,
        classificar_NR, score_para_classificacao,
        DIMENSOES, DIMENSOES_LABEL, DIM_NEGATIVAS,
        NIVEIS_ORDEM, NIVEIS_GERAL_ORDEM,
    )
"""

import json
import os
import pandas as pd
import numpy as np

# ─────────────────────────────────────────────
# CONSTANTES COMPARTILHADAS
# ─────────────────────────────────────────────

DIMENSOES = [
    "Demandas", "Controle", "Apoio_Chefia",
    "Apoio_Colegas", "Relacionamentos", "Cargo", "Comunicacao_Mudancas"
]

DIMENSOES_LABEL = {
    "Demandas":             "Demandas",
    "Controle":             "Controle",
    "Apoio_Chefia":         "Apoio da Chefia",
    "Apoio_Colegas":        "Apoio dos Colegas",
    "Relacionamentos":      "Relacionamentos",
    "Cargo":                "Cargo / Função",
    "Comunicacao_Mudancas": "Comunicação e Mudanças",
}

# Alias usado no agente_ia.py original (mantido por compatibilidade)
DIMENSOES_ALIAS = {
    "Mudanca": "Comunicacao_Mudancas",
}

DIM_NEGATIVAS = {"Demandas", "Relacionamentos"}

NIVEIS_ORDEM       = ["Baixo Risco", "Risco Médio", "Risco Moderado", "Alto Risco"]
NIVEIS_GERAL_ORDEM = ["Aceitável", "Moderado", "Importante", "Crítico"]

# ─────────────────────────────────────────────
# CARGA DE DADOS
# ─────────────────────────────────────────────

def load_all_data(
    base_path:    str = "base.parquet",
    setor_path:   str = "setor.parquet",
    cargo_path:   str = "cargo.parquet",
    unidade_path: str = "unidade.parquet",
):
    """Carrega os 4 parquets e devolve (base, setor, cargo, unidade).
    unidade é None se o arquivo não existir."""
    base    = pd.read_parquet(base_path)
    setor   = pd.read_parquet(setor_path)
    cargo   = pd.read_parquet(cargo_path)
    unidade = pd.read_parquet(unidade_path) if os.path.exists(unidade_path) else None
    return base, setor, cargo, unidade


# ─────────────────────────────────────────────
# CLASSIFICAÇÕES
# ─────────────────────────────────────────────

def classificar_NR(nr: float) -> str:
    """Classifica um valor de NR geral nas 4 faixas NR-1."""
    if nr >= 13: return "Crítico"
    if nr >= 9:  return "Importante"
    if nr >= 5:  return "Moderado"
    return "Aceitável"


def score_para_classificacao(score: float, dim: str) -> str:
    """Converte score de dimensão (0–4) em nível de risco.
    Dimensões negativas: score alto = pior.
    Dimensões positivas: score baixo = pior."""
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


# ─────────────────────────────────────────────
# AGREGAÇÃO POR GRUPO
# ─────────────────────────────────────────────

def reaplicar_agg(df: pd.DataFrame, col: str, rename: str) -> pd.DataFrame:
    """Agrega base filtrada por coluna de grupo (setor, cargo, unidade, empresa).
    Inclui scores, NRs por dimensão, percentuais de risco e classificação NR-1."""
    if df.empty:
        return pd.DataFrame()

    agg_dict = {
        "n_colaboradores": (col, "count"),
        "IGRP":            ("IGRP", "mean"),
        "NR_geral":        ("NR_geral", "mean"),
        "perc_critico":    ("risco_geral", lambda x: (x == "Crítico").mean()),
        "perc_importante": ("risco_geral", lambda x: (x == "Importante").mean()),
        "perc_risco_alto": ("risco_geral", lambda x: x.isin(["Crítico", "Importante"]).mean()),
    }

    for d in DIMENSOES:
        if f"score_{d}" in df.columns:
            agg_dict[f"score_{d}"] = (f"score_{d}", "mean")
        if f"NR_{d}" in df.columns:
            agg_dict[f"NR_{d}"] = (f"NR_{d}", "mean")

    g = (
        df.groupby(col)
        .agg(**agg_dict)
        .reset_index()
        .rename(columns={col: rename})
    )
    g["classificacao"] = g["NR_geral"].apply(classificar_NR)
    g["rank_risco"]    = g["NR_geral"].rank(ascending=False, method="min")
    return g.sort_values(["perc_risco_alto", "NR_geral"], ascending=False)


# ─────────────────────────────────────────────
# ANÁLISE COMPLETA — usada pelo agente
# ─────────────────────────────────────────────

def build_full_analytics(base_f: pd.DataFrame) -> dict:
    """
    Executa TODAS as análises disponíveis sobre base_f (já filtrada)
    e devolve um dicionário rico com:
      - kpis globais
      - distribuição de risco
      - scores por dimensão (com classificação)
      - top setores, cargos, unidades e empresas (com NR por dimensão)
      - NR por dimensão × grupo (matriz heatmap)
      - 10 questões mais críticas
      - resumo PGR

    É idêntico ao que o dashboard calcula visualmente, mas em forma de dados.
    """
    n = len(base_f)
    if n == 0:
        return {}

    # ── KPIs globais ──
    nr_medio    = float(base_f["NR_geral"].mean())
    igrp_medio  = float(base_f["IGRP"].mean())
    dist_risco  = base_f["risco_geral"].value_counts().to_dict()
    perc_alto   = (dist_risco.get("Crítico", 0) + dist_risco.get("Importante", 0)) / n
    perc_crit   = dist_risco.get("Crítico", 0) / n

    # ── Scores por dimensão (Tab 1 / Tab 2 do dashboard) ──
    scores_dim = {}
    class_dim  = {}
    nr_dim     = {}
    for d in DIMENSOES:
        cs = f"score_{d}"
        cn = f"NR_{d}"
        if cs in base_f.columns:
            s = float(base_f[cs].mean())
            scores_dim[DIMENSOES_LABEL[d]] = round(s, 3)
            class_dim[DIMENSOES_LABEL[d]]  = score_para_classificacao(s, d)
        if cn in base_f.columns:
            nr_dim[DIMENSOES_LABEL[d]] = round(float(base_f[cn].mean()), 2)

    # ── Agregados por grupo (Tab 7 Heatmap / Tab 9 PGR do dashboard) ──
    setor_agg   = reaplicar_agg(base_f, "Informe seu setor / departamento.", "Setor")
    cargo_agg   = reaplicar_agg(base_f, "Informe seu cargo",                 "Cargo")
    empresa_agg = reaplicar_agg(base_f, "Empresa",                           "Empresa")
    unidade_agg = (
        reaplicar_agg(base_f, "Informe sua unidade", "Unidade")
        if "Informe sua unidade" in base_f.columns else pd.DataFrame()
    )

    def _top_records(df: pd.DataFrame, key: str, n_top: int = 5) -> list:
        """Serializa os top n grupos com todos os campos relevantes."""
        cols_base = [key, "n_colaboradores", "NR_geral", "classificacao",
                     "perc_risco_alto", "perc_critico", "IGRP"]
        nr_cols   = [f"NR_{d}" for d in DIMENSOES if f"NR_{d}" in df.columns]
        sc_cols   = [f"score_{d}" for d in DIMENSOES if f"score_{d}" in df.columns]
        use_cols  = [c for c in cols_base + nr_cols + sc_cols if c in df.columns]

        rows = []
        for _, r in df[use_cols].head(n_top).iterrows():
            rec = {}
            for c in use_cols:
                v = r[c]
                rec[c] = round(float(v), 3) if isinstance(v, (float, np.floating)) else v
            # Adiciona classificação por dimensão
            for d in DIMENSOES:
                cn = f"NR_{d}"
                if cn in rec:
                    rec[f"class_{d}"] = classificar_NR(rec[cn])
            rows.append(rec)
        return rows

    top_setores  = _top_records(setor_agg,   "Setor")
    top_cargos   = _top_records(cargo_agg,   "Cargo")
    top_empresas = _top_records(empresa_agg, "Empresa")
    top_unidades = _top_records(unidade_agg, "Unidade") if not unidade_agg.empty else []

    # ── Matriz NR dimensão × setor (Tab Heatmap do dashboard) ──
    nr_cols_hm = [f"NR_{d}" for d in DIMENSOES if f"NR_{d}" in setor_agg.columns]
    matriz_setor = {}
    for _, row in setor_agg.iterrows():
        setor_nome = row["Setor"]
        matriz_setor[setor_nome] = {
            DIMENSOES_LABEL[d]: round(float(row[f"NR_{d}"]), 2)
            for d in DIMENSOES if f"NR_{d}" in setor_agg.columns
        }

    # ── Questões mais críticas (Tab 3 do dashboard) ──
    excluir = {
        "Empresa", "Informe sua unidade",
        "Informe seu setor / departamento.", "Informe seu cargo",
        "IGRP", "NR_geral", "risco_geral", "qtd_dimensoes_alto",
    }
    questoes_raw = [
        c for c in base_f.columns
        if c not in excluir
        and not any(c.startswith(p) for p in ("score_", "NR_", "class_", "P_", "S_"))
    ]
    questoes_criticas = sorted(
        [{"questao": q[:90], "score": round(float(base_f[q].mean()), 2)} for q in questoes_raw[:40]],
        key=lambda x: x["score"],
        reverse=True
    )[:10]

    # ── Resumo PGR (Tab 9 do dashboard) ──
    pgr_setores = []
    for _, row in setor_agg.iterrows():
        nr_dims = {
            DIMENSOES_LABEL[d]: round(float(row[f"NR_{d}"]), 2)
            for d in DIMENSOES if f"NR_{d}" in setor_agg.columns
        }
        nr_dims_criticos = {k: v for k, v in nr_dims.items() if v >= 9}
        pgr_setores.append({
            "setor":          row["Setor"],
            "NR_geral":       round(float(row["NR_geral"]), 2),
            "classificacao":  row["classificacao"],
            "n":              int(row["n_colaboradores"]),
            "perc_risco_alto": round(float(row["perc_risco_alto"]) * 100, 1),
            "dimensoes_NR":   nr_dims,
            "dimensoes_criticas_ou_importantes": nr_dims_criticos,
        })

    return {
        # KPIs
        "n_respondentes":   n,
        "nr_medio":         round(nr_medio, 2),
        "igrp_medio":       round(igrp_medio, 3),
        "perc_risco_alto":  round(perc_alto * 100, 1),
        "perc_critico":     round(perc_crit * 100, 1),
        "distribuicao_risco": dist_risco,

        # Dimensões
        "scores_por_dimensao":      scores_dim,
        "classificacao_por_dimensao": class_dim,
        "nr_por_dimensao":          nr_dim,

        # Top grupos
        "top_setores":   top_setores,
        "top_cargos":    top_cargos,
        "top_empresas":  top_empresas,
        "top_unidades":  top_unidades,

        # Heatmap
        "matriz_nr_setor_dimensao": matriz_setor,

        # Questões
        "questoes_mais_criticas": questoes_criticas,

        # PGR
        "pgr_por_setor": pgr_setores,
    }


# ─────────────────────────────────────────────
# CONTEXTO TEXTUAL PARA O LLM
# ─────────────────────────────────────────────

def build_context_text(analytics: dict) -> str:
    """
    Converte o dicionário de analytics em texto estruturado
    para ser injetado no prompt do agente.
    Muito mais rico que o build_context original do agente_ia.py.
    """
    if not analytics:
        return "Nenhum dado disponível com os filtros selecionados."

    a = analytics
    linhas = [
        "# CONTEXTO — DASHBOARD HSE-IT (Riscos Psicossociais / NR-1)",
        "",
        "## 1. KPIs Globais",
        f"- Respondentes: {a['n_respondentes']}",
        f"- NR Geral médio: {a['nr_medio']:.2f}  (escala 1–16 | Crítico ≥ 13)",
        f"- IGRP médio: {a['igrp_medio']:.3f}  (escala 0–4)",
        f"- Em risco Alto/Crítico: {a['perc_risco_alto']:.1f}%",
        f"- Em risco Crítico: {a['perc_critico']:.1f}%",
        "",
        "## 2. Distribuição por Nível de Risco",
        json.dumps(a["distribuicao_risco"], ensure_ascii=False, indent=2),
        "",
        "## 3. Scores por Dimensão (0–4)",
        "Dimensões NEGATIVAS (score alto = pior): Demandas, Relacionamentos",
        "Dimensões POSITIVAS (score baixo = pior): demais",
    ]

    for label, score in a["scores_por_dimensao"].items():
        cls = a["classificacao_por_dimensao"].get(label, "—")
        nr  = a["nr_por_dimensao"].get(label, "—")
        linhas.append(f"  {label}: score={score:.3f}  NR={nr}  → {cls}")

    linhas += [
        "",
        "## 4. Top Setores Críticos (NR × Dimensão)",
    ]
    for s in a["top_setores"]:
        dims_crit = s.get("dimensoes_criticas_ou_importantes", {})
        linhas.append(
            f"  [{s['Setor']}]  NR={s['NR_geral']:.2f}  ({s['classificacao']})  "
            f"n={s['n_colaboradores']}  alto_risco={s['perc_risco_alto']*100:.1f}%"
        )
        if dims_crit:
            linhas.append(f"    Dimensões críticas/importantes: {dims_crit}")

    linhas += ["", "## 5. Top Cargos Críticos"]
    for c in a["top_cargos"]:
        linhas.append(
            f"  [{c['Cargo']}]  NR={c['NR_geral']:.2f}  ({c['classificacao']})  "
            f"n={c['n_colaboradores']}  alto_risco={c['perc_risco_alto']*100:.1f}%"
        )

    if a["top_unidades"]:
        linhas += ["", "## 6. Top Unidades Críticas"]
        for u in a["top_unidades"]:
            linhas.append(
                f"  [{u['Unidade']}]  NR={u['NR_geral']:.2f}  ({u['classificacao']})  "
                f"n={u['n_colaboradores']}"
            )

    linhas += [
        "",
        "## 7. Matriz NR por Setor × Dimensão (heatmap PGR)",
        json.dumps(a["matriz_nr_setor_dimensao"], ensure_ascii=False, indent=2),
        "",
        "## 8. 10 Questões com Score Mais Preocupante",
        "(Demandas/Relacionamentos: alto = ruim | demais: baixo = ruim)",
        json.dumps(a["questoes_mais_criticas"], ensure_ascii=False, indent=2),
        "",
        "## 9. PGR — Programa de Gerenciamento de Riscos por Setor",
        json.dumps(a["pgr_por_setor"], ensure_ascii=False, indent=2),
        "",
        "---",
        "Escalas: NR  Aceitável(≤4) | Moderado(5–8) | Importante(9–12) | Crítico(≥13)",
    ]

    return "\n".join(linhas)


def build_context(
    base: pd.DataFrame,
    filtro_empresa=None,
    filtro_setor=None,
    filtro_cargo=None,
    filtro_unidade=None,
):
    """
    Ponto de entrada único para agente e dashboard.
    Aplica filtros → roda build_full_analytics → devolve (texto, dict).
    """
    df = base.copy()
    if filtro_empresa:
        df = df[df["Empresa"].isin(filtro_empresa)]
    if filtro_unidade:
        df = df[df["Informe sua unidade"].isin(filtro_unidade)]
    if filtro_setor:
        df = df[df["Informe seu setor / departamento."].isin(filtro_setor)]
    if filtro_cargo:
        df = df[df["Informe seu cargo"].isin(filtro_cargo)]

    analytics = build_full_analytics(df)
    contexto  = build_context_text(analytics)
    return contexto, analytics
