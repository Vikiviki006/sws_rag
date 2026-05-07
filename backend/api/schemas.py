from pydantic import BaseModel, Field
from typing import List, Dict

class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        example="What is the annual leave entitlement?",
    )

class ChatResponse(BaseModel):
    answer: str
    sources: List[str]

class UploadResponse(BaseModel):
    filename: str
    chunks_added: int
    status: str
    message: str

class HealthResponse(BaseModel):
    status: str
    vectorstore_stats: Dict
    models: Dict
