# services/action_plan.py

import json
import re
from services.llm import call_llm

def gerar_plano_acao(contexto):

    prompt = f"""
Gere um plano de ação em JSON puro.

IMPORTANTE:
- NÃO escreva texto fora do JSON
- NÃO use ```json
- Retorne apenas JSON válido

Formato:
{{
  "problema": "...",
  "objetivo": "...",
  "acoes": [
    {{
      "descricao": "...",
      "responsavel": "...",
      "prazo": "...",
      "prioridade": "...",
      "indicador_sucesso": "..."
    }}
  ]
}}

Contexto:
{contexto}
"""

    resposta = call_llm(prompt)

    try:
        # 🔥 EXTRAI JSON MESMO SE VIER SUJO
        json_str = re.search(r'\{.*\}', resposta, re.DOTALL).group(0)
        return json.loads(json_str)

    except Exception as e:
        return {
            "erro": "Falha ao parsear JSON",
            "raw": resposta[:500]
        }
