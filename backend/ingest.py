"""
PDF Ingestion Pipeline
======================
Uses SentenceTransformer("all-mpnet-base-v2") for 768-dim embeddings,
matching the rag.py query-time model exactly.
"""

import os
import chromadb
from pathlib import Path
from typing import List

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

from utils import get_logger

load_dotenv()
logger = get_logger(__name__)

# ── Config from .env ───────────────────────────────────────────────────────────
CHROMA_PERSIST_DIR    = os.getenv("CHROMA_PERSIST_DIR", "./vectorstore")
CHROMA_COLLECTION     = os.getenv("CHROMA_COLLECTION_NAME", "company_policies")
UPLOAD_DIR            = os.getenv("UPLOAD_DIR", "./uploads")
CHUNK_SIZE            = int(os.getenv("CHUNK_SIZE", 500))
CHUNK_OVERLAP         = int(os.getenv("CHUNK_OVERLAP", 50))
EMBEDDING_MODEL_NAME  = os.getenv("EMBEDDING_MODEL", "all-mpnet-base-v2")  # 768-dim

# ── Lazy singleton — loaded once, reused ──────────────────────────────────────
_embedding_model: SentenceTransformer | None = None


def _get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        logger.info(f"Embedding model loaded: {EMBEDDING_MODEL_NAME}")
    return _embedding_model


def _get_collection() -> chromadb.Collection:
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    # get_or_create so first run and subsequent runs both work
    return client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


# ── Core pipeline ──────────────────────────────────────────────────────────────

def load_and_split_pdf(file_path: str) -> List:
    logger.info(f"Loading: {file_path}")
    loader = PyPDFLoader(file_path)
    pages = loader.load()
    logger.info(f"  {len(pages)} pages loaded")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " ", ""],
    )
    chunks = splitter.split_documents(pages)
    logger.info(f"  {len(chunks)} chunks created")

    filename = Path(file_path).name
    for chunk in chunks:
        chunk.metadata["source"] = filename

    return chunks


def ingest_pdf(file_path: str) -> dict:
    try:
        chunks = load_and_split_pdf(file_path)
        texts = [c.page_content for c in chunks]
        metadatas = [c.metadata for c in chunks]

        model = _get_embedding_model()
        embeddings = model.encode(texts, show_progress_bar=True).tolist()

        collection = _get_collection()

        # Stable IDs prevent duplicate chunks on re-ingestion
        filename = Path(file_path).stem
        ids = [f"{filename}_chunk_{i}" for i in range(len(chunks))]

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

        logger.info(f"Upserted {len(chunks)} chunks from {Path(file_path).name}")
        return {"filename": Path(file_path).name, "chunks_added": len(chunks), "status": "success"}

    except Exception as exc:
        logger.error(f"Ingestion failed for {file_path}: {exc}")
        raise


def ingest_directory(directory: str = None) -> List[dict]:
    directory = directory or UPLOAD_DIR
    pdf_files = list(Path(directory).glob("*.pdf"))

    if not pdf_files:
        logger.warning(f"No PDFs found in {directory}")
        return []

    results = [ingest_pdf(str(p)) for p in pdf_files]
    logger.info(f"Bulk ingestion complete: {len(results)} files")
    return results


def get_collection_stats() -> dict:
    try:
        count = _get_collection().count()
        return {"total_chunks": count, "collection": CHROMA_COLLECTION}
    except Exception as exc:
        logger.error(f"Stats error: {exc}")
        return {"total_chunks": 0, "collection": CHROMA_COLLECTION}


def reset_collection() -> None:
    """Drop and recreate the collection. Run this before re-ingesting after a model change."""
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    existing = [c.name for c in client.list_collections()]
    if CHROMA_COLLECTION in existing:
        client.delete_collection(CHROMA_COLLECTION)
        logger.info(f"Deleted collection: {CHROMA_COLLECTION}")
    client.create_collection(CHROMA_COLLECTION, metadata={"hnsw:space": "cosine"})
    logger.info(f"Created fresh collection: {CHROMA_COLLECTION}")


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if "--reset" in sys.argv:
        reset_collection()
        print("Collection reset.")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    results = ingest_directory()
    for r in results:
        print(f"  ✓ {r['filename']} — {r['chunks_added']} chunks")
    print(f"\nTotal: {get_collection_stats()['total_chunks']} chunks")