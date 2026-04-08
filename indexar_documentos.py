"""
indexar_documentos.py
─────────────────────
Roda UMA VEZ no seu PC para popular o índice Pinecone.
Não vai para o GitHub (só o rag.py vai).

Pré-requisitos:
    pip install pinecone-client sentence-transformers pymupdf langchain-text-splitters

Uso:
    python indexar_documentos.py
"""

import os
import fitz  # pymupdf
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ─────────────────────────────────────────────
# CONFIGURAÇÃO — preencha antes de rodar
# ─────────────────────────────────────────────
PINECONE_API_KEY = "sua-chave-pinecone-aqui"
INDEX_NAME       = "hse-normas"
PASTA_NORMAS     = "./normas"   # pasta com os PDFs

# ─────────────────────────────────────────────
# MAPEAMENTO: nome amigável → arquivo PDF
# (ajuste os nomes de arquivo conforme salvou)
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
}

# ─────────────────────────────────────────────
# INICIALIZAÇÃO
# ─────────────────────────────────────────────
print("🔧 Carregando modelo de embeddings (MiniLM)...")
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

print("🌲 Conectando ao Pinecone...")
pc = Pinecone(api_key=PINECONE_API_KEY)

# Cria o índice se ainda não existir
existing = [idx.name for idx in pc.list_indexes()]
if INDEX_NAME not in existing:
    print(f"📦 Criando índice '{INDEX_NAME}'...")
    pc.create_index(
        name=INDEX_NAME,
        dimension=384,          # dimensão do MiniLM-L6-v2
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )
    print("✅ Índice criado.")
else:
    print(f"✅ Índice '{INDEX_NAME}' já existe.")

index = pc.Index(INDEX_NAME)

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

    # Gera embeddings em lote (mais rápido)
    embeddings = model.encode(
        chunks,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True
    )

    # Monta vetores para o Pinecone
    vectors = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        vectors.append({
            "id": f"{doc_id}_chunk_{i:04d}",
            "values": embedding.tolist(),
            "metadata": {
                "documento": doc_id,
                "texto": chunk,
                "filename": filename,
                "chunk_idx": i,
            }
        })

    # Upsert em lotes de 100
    BATCH = 100
    for start in range(0, len(vectors), BATCH):
        batch = vectors[start:start + BATCH]
        index.upsert(vectors=batch)
        print(f"   → Enviados {min(start + BATCH, len(vectors))}/{len(vectors)} vetores")

    total_chunks += len(chunks)
    print(f"   ✅ {doc_id} indexado com sucesso.")

# ─────────────────────────────────────────────
# RESULTADO FINAL
# ─────────────────────────────────────────────
stats = index.describe_index_stats()
print(f"\n{'='*50}")
print(f"✅ Indexação concluída!")
print(f"   Total de chunks enviados : {total_chunks}")
print(f"   Vetores no Pinecone      : {stats['total_vector_count']}")
print(f"   Índice                   : {INDEX_NAME}")
print(f"{'='*50}")
print("\nAgora adicione ao seu .streamlit/secrets.toml:")
print("  PINECONE_API_KEY = \"sua-chave\"")
print("  INDEX_NAME       = \"hse-normas\"")
