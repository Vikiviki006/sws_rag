import shutil
from pathlib import Path
from fastapi import HTTPException, UploadFile, status

from utils import get_settings, get_logger
from ingest import ingest_pdf, get_collection_stats
from rag import query_rag
from .schemas import ChatRequest, ChatResponse, UploadResponse, HealthResponse

logger = get_logger(__name__)
settings = get_settings()

async def handle_chat(request: ChatRequest) -> ChatResponse:
    if not request.question.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Question cannot be empty.",
        )

    try:
        answer, sources = query_rag(request.question)
        return ChatResponse(answer=answer, sources=sources)
    except RuntimeError as exc:
        logger.error(f"Chat controller error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(f"Chat controller unexpected error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Check backend logs.",
        )

async def handle_upload(file: UploadFile) -> UploadResponse:
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

async def handle_health() -> HealthResponse:
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
