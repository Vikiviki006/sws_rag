"""
FastAPI Application Entry Point
================================
Main entry point that initializes the FastAPI app, configures CORS,
and includes the API routers.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from utils import get_settings, get_logger
from api.router import router as api_router

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

# ── CORS ──────────────────────────────────────────────────────────────────────
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

# ── Include Routers ───────────────────────────────────────────────────────────
app.include_router(api_router)

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
