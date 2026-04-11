"""
rag.py — Módulo RAG · Agente HSE-IT · Vivamente 360°
──────────────────────────────────────────────────────
Recupera trechos relevantes de NR-1, ISO 45003, NR-17, etc.
usando busca semântica no PostgreSQL + pgvector + embeddings
multilingual-e5-large (mesmo modelo usado na indexação).

Secrets necessários no Streamlit Cloud:
    PG_HOST     = "..."
    PG_PORT     = "5432"
    PG_DB       = "hse_normas"
    PG_USER     = "..."
    PG_PASSWORD = "..."

ARQUITETURA DE CONEXÃO:
    - O modelo de embedding (~560 MB) é cacheado via @st.cache_resource
      e carregado apenas uma vez por sessão do servidor.
    - A conexão psycopg2 NÃO é cacheada: é aberta a cada chamada e
      fechada no bloco finally. Isso evita o erro "connection already
      closed" causado pelo timeout de conexões ociosas no PostgreSQL.
"""

import streamlit as st
import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer

# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────
EMBEDDING_MODEL     = "intfloat/multilingual-e5-large"
RELEVANCE_THRESHOLD = 0.50
DEFAULT_TOP_K       = 5

DOC_LABELS = {
    "ISO_45003_Preview"      : "ISO 45003:2021 (Preview WMS)",
    "WHO_ILO_2022"           : "WHO/ILO — Mental Health at Work (2022)",
    "Guia_MTE_Psicossocial"  : "Guia MTE — Riscos Psicossociais",
    "ISO_45003_2021"         : "ISO 45003:2021",
    "Guia_ASSP_ISO45003"     : "Guia ASSP / ISO 45003",
    "NR-1_2025"              : "NR-1 (2025)",
    "NR-7_PCMSO"             : "NR-7 (PCMSO)",
    "NR-17_Ergonomia"        : "NR-17 (Ergonomia)",
    "Portaria_MTE_1419_2024" : "Portaria MTE nº 1.419/2024",
    "Manual_GRO_PGR_NR1"     : "Manual GRO/PGR da NR-1",
}


# ─────────────────────────────────────────────
# CACHE APENAS DO MODELO — pesado (~560 MB)
# A conexão ao banco é intencionalamente excluída
# do cache para evitar conexões ociosas/fechadas.
# ─────────────────────────────────────────────
@st.cache_resource(show_spinner="📚 Carregando modelo de embeddings...")
def _get_model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL)


def _get_conn() -> psycopg2.extensions.connection:
    """
    Abre e retorna uma conexão nova ao PostgreSQL.
    Deve ser fechada pelo chamador (use try/finally).
    Nunca é cacheada — conexões ociosas são fechadas
    pelo servidor após o idle_timeout configurado.
    """
    conn = psycopg2.connect(
        host=st.secrets["PG_HOST"],
        port=int(st.secrets.get("PG_PORT", 5432)),
        dbname=st.secrets["PG_DB"],
        user=st.secrets["PG_USER"],
        password=st.secrets["PG_PASSWORD"],
        # Fecha a conexão automaticamente se ficar ociosa por 10s
        # antes de o servidor encerrar — evita erros na próxima query.
        options="-c statement_timeout=30000",
        connect_timeout=10,
    )
    register_vector(conn)
    return conn


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
    no context prompt da Groq.

    Retorna string vazia se nenhum trecho atingir o threshold
    ou se o banco estiver indisponível.
    """
    if not pergunta or not pergunta.strip():
        return ""

    # Embedding da query (modelo cacheado, nunca recriado)
    try:
        model = _get_model()
        query_vector = model.encode(
            f"query: {pergunta}",
            normalize_embeddings=True,
        ).tolist()
    except Exception as e:
        st.warning(f"⚠️ Erro ao gerar embedding: {e}")
        return ""

    # Conexão aberta aqui, fechada no finally — nunca vaza
    conn = None
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                documento,
                texto,
                1 - (embedding <=> %s::vector) AS score
            FROM documentos_chunks
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
        """, (query_vector, query_vector, top_k))

        rows = cur.fetchall()
        cur.close()

    except Exception as e:
        st.warning(f"⚠️ Erro na busca normativa: {e}")
        return ""

    finally:
        # Garante fechamento mesmo se a query lançar exceção
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass  # já estava fechada — ignorar

    if not rows:
        return ""

    # Filtra por relevância e formata
    trechos = []
    docs_usados = set()

    for doc_id, texto, score in rows:
        if score < threshold:
            continue

        texto = texto.strip()
        if not texto:
            continue

        label = DOC_LABELS.get(doc_id, doc_id)
        docs_usados.add(label)
        trechos.append(
            f"[Fonte: {label} | Relevância: {score:.0%}]\n{texto}"
        )

    if not trechos:
        return ""

    fontes_str = " · ".join(sorted(docs_usados))
    return (
        "════════════════════════════════════════════\n"
        "BASE NORMATIVA RELEVANTE PARA ESTA RESPOSTA\n"
        f"Fontes: {fontes_str}\n"
        "════════════════════════════════════════════\n\n"
        + "\n\n---\n\n".join(trechos)
        + "\n\n════════════════════════════════════════════"
    )


# ─────────────────────────────────────────────
# UTILITÁRIO — lista documentos indexados
# ─────────────────────────────────────────────
def listar_documentos_indexados() -> dict:
    """
    Retorna estatísticas do banco pgvector.
    Abre e fecha a própria conexão — seguro para chamar a qualquer momento.
    """
    conn = None
    try:
        conn = _get_conn()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM documentos_chunks;")
        total = cur.fetchone()[0]

        cur.execute("""
            SELECT documento, COUNT(*) AS chunks
            FROM documentos_chunks
            GROUP BY documento
            ORDER BY documento;
        """)
        por_documento = {row[0]: row[1] for row in cur.fetchall()}
        cur.close()

        return {
            "total_vetores" : total,
            "por_documento" : por_documento,
            "status"        : "online",
        }
    except Exception as e:
        return {"status": "offline", "erro": str(e)}
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
