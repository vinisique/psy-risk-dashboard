# services/action_plan.py

from services.llm import call_llm
import json

def gerar_plano_acao(contexto):
    prompt = f"""
Gere um plano de ação estruturado para o seguinte cenário:

{contexto}

Responda em JSON com:
problema, objetivo, acoes[]
"""

    resposta = call_llm(prompt)

    try:
        return json.loads(resposta)
    except:
        return {"erro": resposta}
