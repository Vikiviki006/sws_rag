"""
PDF Ingestion Pipeline
======================
Handles the full document ingestion lifecycle:
  1. Load PDF → extract text via PyPDFLoader
  2. Split into chunks using RecursiveCharacterTextSplitter
  3. Generate embeddings via Ollama (nomic-embed-text)
  4. Persist embeddings into ChromaDB

ARCHITECTURAL DECISION — Why chunk_overlap=50?
  Context windows in RAG are fragmented. A sentence split at a chunk boundary
  loses its semantic neighbour. Overlap of 50 tokens ensures boundary sentences
  appear in BOTH adjacent chunks, so retrieval never misses a concept that
  straddles a split point. Think of it as a sliding window, not a hard cut.

ARCHITECTURAL DECISION — Why RecursiveCharacterTextSplitter?
  It tries splitting on paragraph → sentence → word → character boundaries in
  order, preserving natural language units as long as possible before falling
  back to hard cuts. This produces semantically coherent chunks vs naive
  fixed-length splitting.
"""

import os
import shutil
from pathlib import Path
from typing import List

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma

from utils import get_settings, get_logger

logger = get_logger(__name__)
settings = get_settings()


def _get_embeddings() -> OllamaEmbeddings:
    """
    Instantiate Ollama embeddings.

    ARCHITECTURAL DECISION — Why nomic-embed-text?
      nomic-embed-text is a fast, high-quality open-source embedding model
      optimised for retrieval tasks. It produces 768-dim vectors that balance
      quality vs latency on commodity hardware — ideal for local RAG.
      Alternative: mxbai-embed-large (1024-dim, higher quality, slower).
    """
    return OllamaEmbeddings(
        model=settings.embedding_model,
        base_url=settings.ollama_base_url,
    )


def _get_vectorstore(embeddings: OllamaEmbeddings) -> Chroma:
    """
    Connect to (or create) the persisted ChromaDB collection.

    ARCHITECTURAL DECISION — Why ChromaDB?
      ChromaDB is an embedded vector database that stores and indexes embeddings
      locally with zero infrastructure overhead. Unlike Pinecone/Weaviate it
      needs no network call, no API key, and persists to disk as SQLite + HNSW
      index files. For a company-internal chatbot with 10-20 PDFs and a private
      threat model, ChromaDB is the right default — simple, fast, offline.
    """
    os.makedirs(settings.chroma_persist_dir, exist_ok=True)
    return Chroma(
        collection_name=settings.chroma_collection_name,
        embedding_function=embeddings,
        persist_directory=settings.chroma_persist_dir,
    )


def load_and_split_pdf(file_path: str) -> List:
    """
    Load a single PDF and return a list of Document chunks.

    Steps:
      1. PyPDFLoader extracts text page-by-page (preserves page metadata).
      2. RecursiveCharacterTextSplitter cuts pages into ~500-token chunks
         with 50-token overlap.
    """
    logger.info(f"Loading PDF: {file_path}")
    loader = PyPDFLoader(file_path)
    pages = loader.load()
    logger.info(f"  Loaded {len(pages)} pages from {Path(file_path).name}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""],  # natural language hierarchy
    )
    chunks = splitter.split_documents(pages)
    logger.info(f"  Split into {len(chunks)} chunks")

    # Enrich metadata so source citations are meaningful in the UI
    filename = Path(file_path).name
    for chunk in chunks:
        chunk.metadata["source"] = filename
        chunk.metadata["file_path"] = file_path

    return chunks


def ingest_pdf(file_path: str) -> dict:
    """
    Full ingestion pipeline for a single PDF.
    Returns a summary dict consumed by the /api/upload endpoint.
    """
    try:
        chunks = load_and_split_pdf(file_path)
        embeddings = _get_embeddings()
        vectorstore = _get_vectorstore(embeddings)

        # Upsert — ChromaDB deduplicates by document ID automatically
        vectorstore.add_documents(chunks)
        logger.info(
            f"Ingested {len(chunks)} chunks from {Path(file_path).name} "
            f"into collection '{settings.chroma_collection_name}'"
        )

        return {
            "filename": Path(file_path).name,
            "chunks_added": len(chunks),
            "status": "success",
        }
    except Exception as exc:
        logger.error(f"Ingestion failed for {file_path}: {exc}")
        raise


def ingest_directory(directory: str = None) -> List[dict]:
    """
    Bulk-ingest all PDFs in a directory.
    Used during initial setup when PDFs are pre-loaded.
    """
    directory = directory or settings.upload_dir
    pdf_files = list(Path(directory).glob("*.pdf"))

    if not pdf_files:
        logger.warning(f"No PDFs found in {directory}")
        return []

    results = []
    for pdf_path in pdf_files:
        result = ingest_pdf(str(pdf_path))
        results.append(result)

    logger.info(f"Bulk ingestion complete: {len(results)} files processed")
    return results


def get_collection_stats() -> dict:
    """Return metadata about the current ChromaDB collection."""
    try:
        embeddings = _get_embeddings()
        vectorstore = _get_vectorstore(embeddings)
        count = vectorstore._collection.count()
        return {"total_chunks": count, "collection": settings.chroma_collection_name}
    except Exception as exc:
        logger.error(f"Could not fetch collection stats: {exc}")
        return {"total_chunks": 0, "collection": settings.chroma_collection_name}


# ── CLI helper ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    """
    Run from backend/ directory:
        python ingest.py
    Ingests all PDFs from the uploads/ directory.
    """
    import sys

    directory = sys.argv[1] if len(sys.argv) > 1 else settings.upload_dir
    os.makedirs(directory, exist_ok=True)
    results = ingest_directory(directory)
    for r in results:
        print(f"  ✓ {r['filename']} — {r['chunks_added']} chunks")
    stats = get_collection_stats()
    print(f"\nTotal chunks in vectorstore: {stats['total_chunks']}")
