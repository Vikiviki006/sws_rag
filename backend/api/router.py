from fastapi import APIRouter, UploadFile, File, status
from .schemas import ChatRequest, ChatResponse, UploadResponse, HealthResponse
from .controllers import handle_chat, handle_upload, handle_health

router = APIRouter(prefix="/api")

@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Ask a question about company policies",
    tags=["RAG"],
)
async def chat(request: ChatRequest):
    return await handle_chat(request)

@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a policy PDF",
    tags=["Ingestion"],
)
async def upload_pdf(file: UploadFile = File(...)):
    return await handle_upload(file)

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["System"],
)
async def health():
    return await handle_health()
