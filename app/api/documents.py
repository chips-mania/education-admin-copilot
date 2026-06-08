import logging
from functools import lru_cache

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.schemas.documents import DocumentListResponse, DocumentUploadResponse, SOURCE_TYPES
from app.services.document_ingest_service import DocumentIngestService
from app.services.document_list_service import DocumentListService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["documents"])


@lru_cache
def get_document_list_service() -> DocumentListService:
    return DocumentListService()


@lru_cache
def get_document_ingest_service() -> DocumentIngestService:
    return DocumentIngestService()


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(service: DocumentListService = Depends(get_document_list_service)) -> DocumentListResponse:
    return service.get_documents()


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    source_type: str = Form(default="manual"),
    service: DocumentIngestService = Depends(get_document_ingest_service),
) -> DocumentUploadResponse:
    if source_type not in SOURCE_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid source_type. Allowed: {', '.join(SOURCE_TYPES)}")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    logger.info("Upload request file=%s source_type=%s", file.filename, source_type)
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        result = service.ingest_uploaded_file(file.filename, file_bytes, source_type=source_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Upload failed for file=%s", file.filename)
        raise HTTPException(status_code=500, detail="Failed to process uploaded document") from exc

    return DocumentUploadResponse(**result)
