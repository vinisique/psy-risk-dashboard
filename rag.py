"""
rag.py — Módulo RAG · Agente HSE-IT · Vivamente 360°
──────────────────────────────────────────────────────
Recupera trechos relevantes de NR-1, ISO 45003, NR-17, etc.
usando busca semântica no Pinecone + embeddings MiniLM (gratuito).

Secrets necessários no Streamlit Cloud:
    PINECONE_API_KEY = "..."
    INDEX_NAME       = "hse-normas"   # opcional, default abaixo
"""

import streamlit as st
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────
DEFAULT_INDEX_NAME   = "hse-normas"
EMBEDDING_MODEL      = "sentence-transformers/all-MiniLM-L6-v2"
RELEVANCE_THRESHOLD  = 0.50   # score mínimo de cosine similarity
DEFAULT_TOP_K        = 5      # quantos trechos recuperar por query

# Labels amigáveis para exibição
DOC_LABELS = {
    "NR-1_2025"              : "NR-1 (2025)",
    "Portaria_MTE_1419_2024" : "Portaria MTE nº 1.419/2024",
    "Guia_MTE_Psicossocial"  : "Guia MTE — Riscos Psicossociais",
    "ISO_45003_2021"         : "ISO 45003:2021",
    "Guia_ASSP_ISO45003"     : "Guia ASSP / ISO 45003",
    "WHO_ILO_2022"           : "WHO/ILO — Mental Health at Work (2022)",
    "NR-17_Ergonomia"        : "NR-17 (Ergonomia)",
    "NR-7_PCMSO"             : "NR-7 (PCMSO)",
}


# ─────────────────────────────────────────────
# INICIALIZAÇÃO COM CACHE
# O modelo (90MB) e a conexão Pinecone são carregados
# uma única vez e reutilizados em todas as requisições.
# ─────────────────────────────────────────────
@st.cache_resource(show_spinner="📚 Carregando base normativa...")
def _get_resources():
    """Retorna (model, pinecone_index) com cache de sessão."""
    model = SentenceTransformer(EMBEDDING_MODEL)

    api_key    = st.secrets["PINECONE_API_KEY"]
    index_name = st.secrets.get("INDEX_NAME", DEFAULT_INDEX_NAME)

    pc    = Pinecone(api_key=api_key)
    index = pc.Index(index_name)

    return model, index


# ─────────────────────────────────────────────
# FUNÇÃO PRINCIPAL
# ─────────────────────────────────────────────
def buscar_contexto_normativo(
    pergunta: str,
    top_k: int = DEFAULT_TOP_K,
    threshold: float = RELEVANCE_THRESHOLD,
) -> str:
    """
    Recebe a pergunta do usuário e retorna uma string formatada
    com os trechos normativos mais relevantes, pronta para injetar
    no system/context prompt da Groq.

    Retorna string vazia se nenhum trecho atingir o threshold.
    """
    if not pergunta or not pergunta.strip():
        return ""

    try:
        model, index = _get_resources()
    except Exception as e:
        # Se o Pinecone não estiver configurado, falha silenciosa
        # para não quebrar o agente
        st.warning(f"⚠️ RAG indisponível: {e}")
        return ""

    # Gera embedding da pergunta
    query_vector = model.encode(
        pergunta,
        normalize_embeddings=True,
    ).tolist()

    # Busca no Pinecone
    try:
        results = index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True,
        )
    except Exception as e:
        st.warning(f"⚠️ Erro na busca normativa: {e}")
        return ""

    matches = results.get("matches", [])
    if not matches:
        return ""

    # Filtra por relevância e formata
    trechos = []
    docs_usados = set()

    for match in matches:
        score = match.get("score", 0)
        if score < threshold:
            continue

        meta   = match.get("metadata", {})
        doc_id = meta.get("documento", "Desconhecido")
        texto  = meta.get("texto", "").strip()

        if not texto:
            continue

        label = DOC_LABELS.get(doc_id, doc_id)
        docs_usados.add(label)

        trechos.append(
            f"[Fonte: {label} | Relevância: {score:.0%}]\n{texto}"
        )

    if not trechos:
        return ""

    # Monta bloco formatado para injetar no prompt
    fontes_str = " · ".join(sorted(docs_usados))
    bloco = (
        "════════════════════════════════════════════\n"
        "BASE NORMATIVA RELEVANTE PARA ESTA RESPOSTA\n"
        f"Fontes: {fontes_str}\n"
        "════════════════════════════════════════════\n\n"
        + "\n\n---\n\n".join(trechos)
        + "\n\n════════════════════════════════════════════"
    )

    return bloco


# ─────────────────────────────────────────────
# UTILITÁRIO — lista documentos indexados
# Útil para debug / painel administrativo
# ─────────────────────────────────────────────
def listar_documentos_indexados() -> dict:
    """
    Retorna estatísticas do índice Pinecone.
    Use no Streamlit para mostrar o status da base normativa.
    """
    try:
        _, index = _get_resources()
        stats = index.describe_index_stats()
        return {
            "total_vetores": stats.get("total_vector_count", 0),
            "namespaces"   : stats.get("namespaces", {}),
            "status"       : "online",
        }
    except Exception as e:
        return {"status": "offline", "erro": str(e)}
