from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="사용자 질문")
    embed_version: Literal["v1", "v2"] = Field(
        default="v2",
        description="v1=Prototype(embedding_v1), v2=Contextual Retrieval(embedding_v2)",
    )


class SourceResponse(BaseModel):
    file_name: str
    document_title: str
    chunk_no: int
    similarity: float
    file_path: str
    source_type: str
    chapter: str | None = None
    section: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceResponse]
    embed_version: Literal["v1", "v2"]
