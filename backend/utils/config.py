from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):

    # API
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # Embedding — must match what was used during ingest
    embedding_model: str = "all-mpnet-base-v2"  # ← was "nomic-embed-text", wrong

    # Ollama (kept for reference, not used when running Gemini stack)
    llm_model: str = "deepseek-coder-v2:16b"
    ollama_base_url: str = "http://localhost:11434"

    # RAG
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 4

    # Storage
    upload_dir: str = "uploads"
    chroma_persist_dir: str = "vectorstore"
    chroma_collection_name: str = "company_policies"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "protected_namespaces": (),  # ← fixes the model_* field name warning
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()