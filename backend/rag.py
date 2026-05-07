"""
RAG Pipeline
============
Orchestrates semantic retrieval + grounded generation:

  Query → Embed → ChromaDB similarity search → top-K docs
       → Inject into prompt → deepseek-coder-v2:16b → answer + sources

ARCHITECTURAL DECISION — Why RAG over fine-tuning?
  Fine-tuning permanently bakes knowledge into model weights. For company
  policies this is problematic:
    • Policies change (leave days, WFH rules) — retraining is expensive.
    • Fine-tuned models hallucinate confidently on out-of-distribution queries.
    • You can't audit which training document produced an answer.
  RAG solves all three:
    • Update policy → re-ingest PDF → instantly reflected in answers.
    • Answers are grounded in retrieved text, not hallucinated weights.
    • Every response cites exact source documents for auditability.

ARCHITECTURAL DECISION — How semantic retrieval works:
  1. User query is embedded using the same model as ingestion (nomic-embed-text).
  2. ChromaDB performs approximate nearest-neighbour search (HNSW index) in
     768-dim embedding space to find the top-K most semantically similar chunks.
  3. "Semantic" means conceptually related text ranks high even with zero
     keyword overlap — e.g. "days off" retrieves "annual leave entitlement".

ARCHITECTURAL DECISION — How source grounding prevents hallucinations:
  The prompt template hard-constrains the LLM:
    "Answer ONLY using the context below. If not found, say so."
  Combined with the retrieved chunks injected into the prompt, the model has
  no reason to invent facts. Source file names are returned alongside the
  answer so users can verify claims against the original documents.
"""

from typing import Tuple, List
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain.callbacks.manager import CallbackManagerForChainRun

from utils import get_settings, get_logger

logger = get_logger(__name__)
settings = get_settings()

# ── Prompt Engineering ─────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a helpful HR assistant for an organisation. Your job is to answer employee questions based ONLY on the company policy documents provided below.

Rules you must follow:
1. Answer ONLY from the provided context. Do not use external knowledge.
2. If the context does not contain enough information to answer, respond exactly:
   "I don't have that information in the company documents."
3. Be concise, clear, and professional.
4. If the answer spans multiple policies, mention each source explicitly.
5. Never make up numbers, dates, or entitlements.

Context from company policy documents:
-----------------------------------------
{context}
-----------------------------------------

Employee Question: {question}

Answer:"""

RAG_PROMPT = PromptTemplate(
    template=SYSTEM_PROMPT,
    input_variables=["context", "question"],
)


def _build_retriever(embeddings: OllamaEmbeddings):
    """
    Build a ChromaDB-backed retriever with MMR (Maximal Marginal Relevance).

    MMR diversifies the top-K results — instead of returning 4 near-identical
    chunks from the same paragraph, it balances relevance AND diversity so the
    LLM sees broader context across the document.
    """
    vectorstore = Chroma(
        collection_name=settings.chroma_collection_name,
        embedding_function=embeddings,
        persist_directory=settings.chroma_persist_dir,
    )
    return vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": settings.top_k,
            "fetch_k": settings.top_k * 3,  # fetch 3x, then MMR-select top_k
        },
    )


def build_rag_chain():
    """
    Assemble the full RAG chain:
      Retriever → PromptTemplate → LLM → Output

    RetrievalQA with return_source_documents=True ensures source metadata
    (filename, page number) is returned alongside the answer — essential
    for the source citation UI.
    """
    embeddings = OllamaEmbeddings(
        model=settings.embedding_model,
        base_url=settings.ollama_base_url,
    )

    # Detect provider from model name (e.g., "gemini-1.5-flash#gemini")
    model_name = settings.llm_model
    if "#" in model_name:
        base_model, provider = model_name.split("#", 1)
        if provider.lower() == "gemini":
            logger.info(f"Using Gemini model: {base_model}")
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(
                model=base_model,
                google_api_key=settings.gemini_api_key,
                temperature=0.1,
                max_output_tokens=1024,
            )
        else:
            # Fallback to Ollama if unknown provider
            llm = Ollama(
                model=base_model,
                base_url=settings.ollama_base_url,
                temperature=0.1,
                num_predict=1024,
                top_k=10,
                top_p=0.9,
            )
    else:
        llm = Ollama(
            model=model_name,
            base_url=settings.ollama_base_url,
            temperature=0.1,
            num_predict=1024,
            top_k=10,
            top_p=0.9,
        )

    retriever = _build_retriever(embeddings)

    chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",           # "stuff" = inject all chunks into one prompt
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": RAG_PROMPT},
    )

    return chain


def extract_sources(source_documents: list) -> List[str]:
    """
    Deduplicate and normalise source file names from retrieved documents.
    Returns a clean list like: ["Leave Policy.pdf", "HR Policy.pdf"]
    """
    seen = set()
    sources = []
    for doc in source_documents:
        src = doc.metadata.get("source", "Unknown Source")
        if src not in seen:
            seen.add(src)
            sources.append(src)
    return sources


def query_rag(question: str) -> Tuple[str, List[str]]:
    """
    Main entry point for the /api/chat endpoint.

    Args:
        question: The employee's natural-language question.

    Returns:
        (answer, sources) — answer string and list of source file names.

    Raises:
        RuntimeError: If the vectorstore is empty or Ollama is unreachable.
    """
    logger.info(f"RAG query: {question!r}")

    try:
        chain = build_rag_chain()
        result = chain.invoke({"query": question})

        answer = result.get("result", "").strip()
        source_docs = result.get("source_documents", [])
        sources = extract_sources(source_docs)

        logger.info(f"Answer generated. Sources: {sources}")
        return answer, sources

    except Exception as exc:
        logger.error(f"RAG pipeline failed: {exc}")
        raise RuntimeError(f"RAG pipeline error: {str(exc)}") from exc
