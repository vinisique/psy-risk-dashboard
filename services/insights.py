# services/insights.py

def gerar_insights_automaticos(setor_f, cargo_f, base_f):
    insights = []

    # 1. Setores críticos
    criticos = setor_f[setor_f["classificacao"] == "Crítico"]
    for _, row in criticos.iterrows():
        insights.append({
            "tipo": "critico",
            "texto": f"Setor {row['Setor']} está em nível CRÍTICO (NR={row['NR_geral']:.1f})"
        })

    # 2. Cargos críticos
    top_cargos = cargo_f.sort_values("NR_geral", ascending=False).head(3)
    for _, row in top_cargos.iterrows():
        insights.append({
            "tipo": "alerta",
            "texto": f"Cargo {row['Cargo']} com alto risco (NR={row['NR_geral']:.1f})"
        })

    # 3. Dimensões críticas
    for dim in ["Demandas", "Controle", "Apoio_Chefia"]:
        col = f"score_{dim}"
        if col in base_f.columns:
            media = base_f[col].mean()

            if dim == "Demandas" and media > 3:
                insights.append({
                    "tipo": "critico",
                    "texto": f"Alta sobrecarga (Demandas={media:.2f})"
                })

            if dim == "Controle" and media < 2:
                insights.append({
                    "tipo": "alerta",
                    "texto": f"Baixo controle (Controle={media:.2f})"
                })

    return insights
