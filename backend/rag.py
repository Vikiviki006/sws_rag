from typing import Tuple, List
from utils import get_logger, get_settings

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


# ── Ollama Embedding Function ─────────────────────────────────────────────────
import ollama


def get_query_embedding(text):
    response = ollama.embeddings(
        model="nomic-embed-text",
        prompt=text
    )

    return response["embedding"]


# ── ChromaDB Collection ───────────────────────────────────────────────────────
_collection = None


def _get_collection():
    global _collection

    if _collection is None:
        import chromadb

        if not settings.chroma_persist_dir:
            raise RuntimeError("CHROMA_PERSIST_DIR is not set in .env")

        if not settings.chroma_collection_name:
            raise RuntimeError("CHROMA_COLLECTION_NAME is not set in .env")

        client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir
        )

        _collection = client.get_or_create_collection(
            settings.chroma_collection_name
        )

        logger.info(
            f"ChromaDB collection loaded: "
            f"{settings.chroma_collection_name}"
        )

    return _collection


# ── Main RAG Query Function ───────────────────────────────────────────────────
def query_rag(question: str) -> Tuple[str, List[str]]:
    logger.info(f"Query: {question}")

    try:
        collection = _get_collection()

        logger.info("Generating query embedding using Ollama...")

        query_embedding = get_query_embedding(question)

        logger.info("Searching ChromaDB...")

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=settings.top_k,
        )

        retrieved_docs = results["documents"][0]
        retrieved_metadata = results["metadatas"][0]

        print("\n===== RETRIEVED CHUNKS =====")

        for i, chunk in enumerate(retrieved_docs):
            print(f"\nChunk {i + 1}:\n{chunk}\n{'=' * 50}")

        context = "\n\n".join(retrieved_docs)

        prompt = SYSTEM_PROMPT.format(
            context=context,
            question=question
        )

        logger.info(
            f"Generating response using model: "
            f"{settings.llm_model}"
        )

        response = ollama.chat(
            model=settings.llm_model,
            messages=[
                {
                    'role': 'user',
                    'content': prompt
                },
            ],
            options={
                'temperature': 0.1,
            }
        )

        answer = response['message']['content']

        sources = extract_sources(retrieved_metadata)

        logger.info(f"Sources: {sources}")

        return answer, sources

    except Exception as exc:
        logger.error(f"RAG Error: {exc}")

        raise RuntimeError(
            f"RAG pipeline error: {str(exc)}"
        ) from exc