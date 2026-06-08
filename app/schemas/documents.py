from pydantic import BaseModel, Field

SOURCE_TYPE_LABELS = {
    "manual": "업무매뉴얼",
    "law": "법령",
    "regulation": "행정규칙",
    "interpretation": "법령해석례",
}

SOURCE_TYPES = tuple(SOURCE_TYPE_LABELS.keys())


class DocumentSummaryStats(BaseModel):
    total_documents: int
    total_chunks: int
    by_source_type: dict[str, int]


class DocumentItem(BaseModel):
    title: str
    file_name: str
    source_type: str
    chunk_count: int
    file_path: str | None = None
    created_at: str | None = None


class DocumentListResponse(BaseModel):
    summary: DocumentSummaryStats
    recent: list[DocumentItem]
    documents: list[DocumentItem]


class DocumentUploadResponse(BaseModel):
    title: str
    file_name: str
    source_type: str
    document_id: int
    chunk_count: int = Field(..., description="Stored chunk count after ingest")
