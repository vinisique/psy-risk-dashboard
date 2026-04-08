# services/recommendations.py

def gerar_recomendacoes(base_f):
    recs = []

    if base_f["score_Demandas"].mean() > 3:
        recs.append("Reduzir carga de trabalho e redistribuir tarefas")

    if base_f["score_Controle"].mean() < 2:
        recs.append("Aumentar autonomia dos colaboradores")

    if base_f["score_Apoio_Chefia"].mean() < 2:
        recs.append("Treinar lideranças em gestão de pessoas")

    if base_f["score_Relacionamentos"].mean() > 3:
        recs.append("Atuar em conflitos e clima organizacional")

    return recs
