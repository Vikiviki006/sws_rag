"""
FastAPI Application Entry Point
================================
Exposes three REST endpoints:
  POST /api/chat    — ask a question, get a grounded answer + sources
  POST /api/upload  — upload a PDF and auto-ingest into ChromaDB
  GET  /api/health  — liveness check for monitoring / CI

Design decisions:
  • All heavy work (LLM calls, embedding, disk I/O) is delegated to rag.py and
    ingest.py — app.py is a thin HTTP adapter only.
  • Pydantic models enforce request/response contracts at the API boundary.
  • HTTPException is used for client errors; 500s surface the real error message
    in dev mode so debugging is fast.
"""

import os
import shutil
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from utils import get_settings, get_logger
from ingest import ingest_pdf, get_collection_stats
from rag import query_rag

logger = get_logger(__name__)
settings = get_settings()

# ── App initialisation ─────────────────────────────────────────────────────────
app = FastAPI(
    title="Company Policy RAG Chatbot API",
    description="Ask questions about internal company policies. Powered by local LLM + ChromaDB.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS — allow the React dev server to reach the API ─────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Ensure required directories exist ─────────────────────────────────────────
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.chroma_persist_dir, exist_ok=True)


# ── Pydantic Schemas ───────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        example="What is the annual leave entitlement?",
    )


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]


class UploadResponse(BaseModel):
    filename: str
    chunks_added: int
    status: str
    message: str


class HealthResponse(BaseModel):
    status: str
    vectorstore_stats: dict
    models: dict


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.post(
    "/api/chat",
    response_model=ChatResponse,
    summary="Ask a question about company policies",
    tags=["RAG"],
)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Retrieves relevant policy chunks from ChromaDB, injects them into the
    deepseek-coder-v2:16b prompt, and returns a grounded answer with source citations.
    """
    if not request.question.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Question cannot be empty.",
        )

    try:
        answer, sources = query_rag(request.question)
        return ChatResponse(answer=answer, sources=sources)
    except RuntimeError as exc:
        logger.error(f"/api/chat error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(f"/api/chat unexpected error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Check backend logs.",
        )


@app.post(
    "/api/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a policy PDF",
    tags=["Ingestion"],
)
async def upload_pdf(file: UploadFile = File(...)) -> UploadResponse:
    """
    Accepts a PDF upload, saves it to disk, and triggers the full
    ingestion pipeline (chunk → embed → store in ChromaDB).

    Only .pdf files are accepted. Duplicate uploads are safe — ChromaDB
    will upsert existing documents.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported.",
        )

    save_path = Path(settings.upload_dir) / file.filename
    try:
        # Stream to disk efficiently
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"Saved uploaded file to {save_path}")
    except Exception as exc:
        logger.error(f"File save failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(exc)}",
        )

    try:
        result = ingest_pdf(str(save_path))
        return UploadResponse(
            filename=result["filename"],
            chunks_added=result["chunks_added"],
            status="success",
            message=f"Successfully ingested {result['chunks_added']} chunks from {result['filename']}",
        )
    except Exception as exc:
        logger.error(f"Ingestion failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File saved but ingestion failed: {str(exc)}",
        )


@app.get(
    "/api/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["System"],
)
async def health() -> HealthResponse:
    """
    Returns the service status and vectorstore statistics.
    Used by monitoring systems and the frontend to show DB state.
    """
    stats = get_collection_stats()
    return HealthResponse(
        status="ok",
        vectorstore_stats=stats,
        models={
            "llm": settings.llm_model,
            "embedding": settings.embedding_model,
            "ollama_url": settings.ollama_base_url,
        },
    )


# ── Dev server entrypoint ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
