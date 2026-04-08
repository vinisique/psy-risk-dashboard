# services/recommendations.py

def gerar_recomendacoes(base_f):
    recs = []

    def safe_mean(col):
        return base_f[col].mean() if col in base_f.columns else None

    demandas = safe_mean("score_Demandas")
    controle = safe_mean("score_Controle")
    apoio = safe_mean("score_Apoio_Chefia")
    rel = safe_mean("score_Relacionamentos")

    if demandas and demandas > 3:
        recs.append("🔴 Reduzir carga de trabalho e redistribuir tarefas")

    if controle and controle < 2:
        recs.append("🟠 Aumentar autonomia dos colaboradores")

    if apoio and apoio < 2:
        recs.append("🟠 Treinar lideranças em gestão de pessoas")

    if rel and rel > 3:
        recs.append("🔴 Atuar em conflitos e clima organizacional")

    if not recs:
        recs.append("🟢 Nenhum risco relevante identificado")

    return recs
