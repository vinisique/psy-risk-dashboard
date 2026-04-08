# services/diagnosis.py

from services.llm import call_llm

def gerar_diagnostico(setor_row):
    prompt = f"""
Você é um especialista em riscos psicossociais (NR-1).

Analise os dados abaixo e gere um diagnóstico profissional:

Setor: {setor_row['Setor']}
NR médio: {setor_row['NR_geral']}
% risco alto: {setor_row['perc_risco_alto']}

Gere:
- Diagnóstico
- Principais causas
- Riscos organizacionais
"""

    return call_llm(prompt)
