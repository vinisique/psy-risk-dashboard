# services/chat.py

from services.llm import call_llm

def build_context(base_f, setor_f, cargo_f):

    top_setor = setor_f.head(3)[["Setor", "NR_geral"]].to_dict("records")
    top_cargo = cargo_f.head(3)[["Cargo", "NR_geral"]].to_dict("records")

    contexto = f"""
Resumo dos dados:

NR médio: {base_f['NR_geral'].mean():.2f}

Top setores críticos:
{top_setor}

Top cargos críticos:
{top_cargo}
"""

    return contexto


def responder_pergunta(pergunta, contexto):
    prompt = f"""
Você é um analista de dados HSE.

Contexto:
{contexto}

Pergunta:
{pergunta}
"""

    return call_llm(prompt)
