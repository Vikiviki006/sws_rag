"""
PDF Ingestion Pipeline
======================
Uses Ollama nomic-embed-text embeddings locally with ChromaDB.
"""

import os
from pathlib import Path
from typing import List
from utils import get_logger

logger = get_logger(__name__)

# ── Config from .env ───────────────────────────────────────────────────────────
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./vectorstore")
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION_NAME", "company_policies")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 500))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 50))

# ── Ollama Embedding Setup ────────────────────────────────────────────────────
import ollama


def get_embedding(text):
    response = ollama.embeddings(
        model="nomic-embed-text",
        prompt=text
    )

    return response["embedding"]


# ── ChromaDB Collection ───────────────────────────────────────────────────────
def _get_collection():
    import chromadb

    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

    return client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


# ── PDF Loading and Chunking ──────────────────────────────────────────────────
def load_and_split_pdf(file_path: str) -> List:
    logger.info(f"Loading: {file_path}")

    from langchain_community.document_loaders import PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter

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


# ── Main Ingestion Function ───────────────────────────────────────────────────
def ingest_pdf(file_path: str) -> dict:
    try:
        chunks = load_and_split_pdf(file_path)

        texts = [c.page_content for c in chunks]
        metadatas = [c.metadata for c in chunks]

        logger.info("Generating embeddings using Ollama...")

        embeddings = [get_embedding(text) for text in texts]

        logger.info("Embeddings generated successfully")

        collection = _get_collection()

        filename = Path(file_path).stem

        ids = [f"{filename}_chunk_{i}" for i in range(len(chunks))]

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

        logger.info(f"Upserted {len(chunks)} chunks from {Path(file_path).name}")

        return {
            "filename": Path(file_path).name,
            "chunks_added": len(chunks),
            "status": "success"
        }

    except Exception as exc:
        logger.error(f"Ingestion failed for {file_path}: {exc}")
        raise


# ── Bulk Directory Ingestion ──────────────────────────────────────────────────
def ingest_directory(directory: str = None) -> List[dict]:
    directory = directory or UPLOAD_DIR

    pdf_files = list(Path(directory).glob("*.pdf"))

    if not pdf_files:
        logger.warning(f"No PDFs found in {directory}")
        return []

    results = [ingest_pdf(str(p)) for p in pdf_files]

    logger.info(f"Bulk ingestion complete: {len(results)} files")

    return results


# ── Collection Stats ──────────────────────────────────────────────────────────
def get_collection_stats() -> dict:
    try:
        count = _get_collection().count()

        return {
            "total_chunks": count,
            "collection": CHROMA_COLLECTION
        }

    except Exception as exc:
        logger.error(f"Stats error: {exc}")

        return {
            "total_chunks": 0,
            "collection": CHROMA_COLLECTION
        }


# ── Reset Collection ──────────────────────────────────────────────────────────
def reset_collection() -> None:
    """
    Drop and recreate the collection.
    Run this before re-ingesting after changing embedding models.
    """

    import chromadb

    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

    existing = [c.name for c in client.list_collections()]

    if CHROMA_COLLECTION in existing:
        client.delete_collection(CHROMA_COLLECTION)

        logger.info(f"Deleted collection: {CHROMA_COLLECTION}")

    client.create_collection(
        CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"}
    )

    logger.info(f"Created fresh collection: {CHROMA_COLLECTION}")


# ── CLI Runner ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if "--reset" in sys.argv:
        reset_collection()
        print("Collection reset.")

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    results = ingest_directory()

    for r in results:
        print(f"✓ {r['filename']} — {r['chunks_added']} chunks")

    print(f"\nTotal: {get_collection_stats()['total_chunks']} chunks")