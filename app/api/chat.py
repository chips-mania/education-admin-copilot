import logging

from fastapi import APIRouter, Depends

from app.schemas.chat import ChatRequest, ChatResponse, SourceResponse
from app.services.rag_service import RagService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


def get_rag_service() -> RagService:
    return RagService()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, service: RagService = Depends(get_rag_service)) -> ChatResponse:
    logger.info("POST /chat question=%s embed_version=%s", request.question, request.embed_version)
    response = service.ask(request.question, embed_version=request.embed_version)

    return ChatResponse(
        answer=response.answer,
        embed_version=response.embed_version,
        sources=[
            SourceResponse(
                file_name=source.file_name,
                document_title=source.document_title,
                chunk_no=source.chunk_no,
                similarity=source.similarity,
                file_path=source.file_path,
                source_type=source.source_type,
                chapter=source.chapter,
                section=source.section,
            )
            for source in response.sources
        ],
    )
