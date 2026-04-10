"""
indexar_documentos_pgvector.py
──────────────────────────────
Roda UMA VEZ no seu PC para popular o índice no PostgreSQL + pgvector.

Pré-requisitos:
    pip install sentence-transformers pymupdf langchain-text-splitters psycopg2-binary pgvector

Uso:
    python indexar_documentos_pgvector.py
"""

import os
import sys
import fitz  # pymupdf
import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ─────────────────────────────────────────────
# CONFIGURAÇÃO — lida de variáveis de ambiente
# Configure em: GitHub → Settings → Codespaces → Secrets
# ─────────────────────────────────────────────
DB_CONFIG = {
    "host":     os.environ.get("PG_HOST", "localhost"),
    "port":     int(os.environ.get("PG_PORT", "5432")),
    "dbname":   os.environ.get("PG_DB", "hse_normas"),
    "user":     os.environ.get("PG_USER", "admin"),
    "password": os.environ.get("PG_PASSWORD", ""),
}

# Aborta se a senha não estiver definida
if not DB_CONFIG["password"]:
    print("❌ Variável de ambiente PG_PASSWORD não definida.")
    print("   Configure em: GitHub → Settings → Codespaces → Secrets")
    sys.exit(1)

PASTA_NORMAS = "./normas"   # pasta com os PDFs

# ─────────────────────────────────────────────
# MAPEAMENTO: nome amigável → arquivo PDF
# ─────────────────────────────────────────────
DOCUMENTOS = {
    "ISO_45003_Preview"      : "45003_2021_wms_preview.pdf",
    "WHO_ILO_2022"           : "9789240057944-eng.pdf",
    "Guia_MTE_Psicossocial"  : "Guia-Fatores-de-Riscos-Psicossociais-MTE.pdf",
    "ISO_45003_2021"         : "ISO-45003-2021.pdf",
    "Guia_ASSP_ISO45003"     : "iso_45003_tech_report_final_210703.pdf",
    "NR-1_2025"              : "nr-01-atualizada-2025-i-1.pdf",
    "NR-7_PCMSO"             : "nr-07-atualizada-2022-1.pdf",
    "NR-17_Ergonomia"        : "nr-17-atualizada-2023.pdf",
    "Portaria_MTE_1419_2024" : "portaria-mte-no-1-419-nr-01-gro-nova-redacao.pdf",
    "Manual_GRO_PGR_NR1"     : "Manual_GRO_PGR_da_NR_1.pdf",
}

# ─────────────────────────────────────────────
# INICIALIZAÇÃO
# ─────────────────────────────────────────────
print("🔧 Carregando modelo de embeddings (multilingual-e5-large)...")
model = SentenceTransformer("intfloat/multilingual-e5-large")

print("🐘 Conectando ao PostgreSQL...")
conn = psycopg2.connect(**DB_CONFIG)
register_vector(conn)   # habilita o tipo vector do pgvector
cur = conn.cursor()

# Garante extensão e tabela
print("📦 Criando extensão e tabela (se não existirem)...")
cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
cur.execute("""
    CREATE TABLE IF NOT EXISTS documentos_chunks (
        id          SERIAL PRIMARY KEY,
        chunk_id    TEXT UNIQUE NOT NULL,   -- ex: ISO_45003_Preview_chunk_0001
        documento   TEXT NOT NULL,
        filename    TEXT NOT NULL,
        chunk_idx   INTEGER NOT NULL,
        texto       TEXT NOT NULL,
        embedding   vector(1024)            -- dimensão do multilingual-e5-large
    );
""")
# Índice HNSW para busca rápida por similaridade
cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_embedding_hnsw
    ON documentos_chunks
    USING hnsw (embedding vector_cosine_ops);
""")
conn.commit()
print("✅ Tabela e índice prontos.")

# Splitter de texto
splitter = RecursiveCharacterTextSplitter(
    chunk_size=600,
    chunk_overlap=80,
    separators=["\n\n", "\n", ". ", " "]
)

# ─────────────────────────────────────────────
# INDEXAÇÃO
# ─────────────────────────────────────────────
total_chunks = 0

for doc_id, filename in DOCUMENTOS.items():
    filepath = os.path.join(PASTA_NORMAS, filename)

    if not os.path.exists(filepath):
        print(f"⚠️  Arquivo não encontrado: {filepath} — pulando.")
        continue

    print(f"\n📄 Processando: {doc_id} ({filename})")

    # Extrai texto do PDF
    doc = fitz.open(filepath)
    paginas = []
    for page_num, page in enumerate(doc):
        texto = page.get_text()
        if texto.strip():
            paginas.append((page_num + 1, texto))
    doc.close()

    texto_completo = "\n".join(t for _, t in paginas)
    chunks = splitter.split_text(texto_completo)
    print(f"   → {len(chunks)} chunks gerados")

    # Gera embeddings em lote
    embeddings = model.encode(
        chunks,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True
    )

    # Insere no PostgreSQL em lotes
    BATCH = 100
    rows = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        rows.append((
            f"{doc_id}_chunk_{i:04d}",  # chunk_id único
            doc_id,
            filename,
            i,
            chunk,
            embedding.tolist(),
        ))

    for start in range(0, len(rows), BATCH):
        batch = rows[start:start + BATCH]
        cur.executemany("""
            INSERT INTO documentos_chunks
                (chunk_id, documento, filename, chunk_idx, texto, embedding)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (chunk_id) DO UPDATE
                SET texto     = EXCLUDED.texto,
                    embedding = EXCLUDED.embedding;
        """, batch)
        conn.commit()
        print(f"   → Inseridos {min(start + BATCH, len(rows))}/{len(rows)} chunks")

    total_chunks += len(chunks)
    print(f"   ✅ {doc_id} indexado com sucesso.")

# ─────────────────────────────────────────────
# RESULTADO FINAL
# ─────────────────────────────────────────────
cur.execute("SELECT COUNT(*) FROM documentos_chunks;")
total_no_banco = cur.fetchone()[0]

cur.close()
conn.close()

print(f"\n{'='*50}")
print(f"✅ Indexação concluída!")
print(f"   Total de chunks enviados : {total_chunks}")
print(f"   Total no banco           : {total_no_banco}")
print(f"{'='*50}")
print("\nExemplo de busca por similaridade:")
print("""
    SELECT texto, documento,
           1 - (embedding <=> '[...vetor...]') AS similaridade
    FROM documentos_chunks
    ORDER BY embedding <=> '[...vetor...]'
    LIMIT 5;
""")