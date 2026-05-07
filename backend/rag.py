from typing import Tuple, List
import os
import chromadb
import google.generativeai as genai

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from utils import get_logger, get_settings

load_dotenv()

logger = get_logger(__name__)
settings = get_settings()

SYSTEM_PROMPT = """
You are a helpful HR assistant.

Answer ONLY using the context below.

If the answer is not found in the context, say:
"I don't have that information in the company documents."

Context:
{context}

Question:
{question}

Answer:
"""


def extract_sources(metadatas) -> List[str]:
    seen = set()
    sources = []
    for meta in metadatas:
        source = meta.get("source", "Unknown Source")
        if source not in seen:
            seen.add(source)
            sources.append(source)
    return sources


_gemini_model = None
_embedding_model = None
_collection = None


def _get_gemini_model():
    global _gemini_model
    if _gemini_model is None:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not set in .env")
        if not settings.gemini_model:
            raise RuntimeError("GEMINI_MODEL is not set in .env")

        genai.configure(api_key=settings.gemini_api_key)
        _gemini_model = genai.GenerativeModel(settings.gemini_model)
        logger.info(f"Gemini model loaded: {settings.gemini_model}")

    return _gemini_model


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        model_name = settings.embedding_model  # ← was hardcoded, now from settings
        _embedding_model = SentenceTransformer(model_name)
        logger.info(f"Embedding model loaded: {model_name}")
    return _embedding_model


def _get_collection():
    global _collection
    if _collection is None:
        if not settings.chroma_persist_dir:
            raise RuntimeError("CHROMA_PERSIST_DIR is not set in .env")
        if not settings.chroma_collection_name:
            raise RuntimeError("CHROMA_COLLECTION_NAME is not set in .env")

        client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        _collection = client.get_collection(settings.chroma_collection_name)
        logger.info(f"ChromaDB collection loaded: {settings.chroma_collection_name}")

    return _collection


def query_rag(question: str) -> Tuple[str, List[str]]:
    logger.info(f"Query: {question}")

    try:
        collection = _get_collection()
        model = _get_gemini_model()
        embedding_model = _get_embedding_model()

        query_embedding = embedding_model.encode(question).tolist()

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=settings.top_k,  # ← was hardcoded 4, now from settings
        )

        retrieved_docs = results["documents"][0]
        retrieved_metadata = results["metadatas"][0]

        print("\n===== RETRIEVED CHUNKS =====")
        for i, chunk in enumerate(retrieved_docs):
            print(f"\nChunk {i + 1}:\n{chunk}\n{'=' * 50}")

        context = "\n\n".join(retrieved_docs)
        prompt = SYSTEM_PROMPT.format(context=context, question=question)

        response = model.generate_content(prompt)
        answer = response.text
        sources = extract_sources(retrieved_metadata)

        logger.info(f"Sources: {sources}")
        return answer, sources

    except Exception as exc:
        logger.error(f"RAG Error: {exc}")
        raise RuntimeError(f"RAG pipeline error: {str(exc)}") from exc