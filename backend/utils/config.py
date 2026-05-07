import os
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # API Settings
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"
    
    # Model Settings
    llm_model: str = "deepseek-coder-v2:16b"
    embedding_model: str = "nomic-embed-text"
    ollama_base_url: str = "http://localhost:11434"
    gemini_api_key: str = ""
    
    # RAG Settings
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 4
    
    # Storage Settings
    upload_dir: str = "uploads"
    chroma_persist_dir: str = "vectorstore"
    chroma_collection_name: str = "company_policies"

    @property
    def origins_list(self):
        return [o.strip() for o in self.allowed_origins.split(",")]

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
