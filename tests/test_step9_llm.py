import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.llm_service import LLMService, build_context, build_user_message
from app.services.rag_service import RagService, build_sources
from app.services.retrieval_service import RetrievalResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SAMPLE_FILE_NAME = "01-01-01 민원의 종류.hwpx"


def _sample_result(chunk_no: int = 1, similarity: float = 0.62) -> RetrievalResult:
    return RetrievalResult(
        id=1,
        document_id=1,
        chunk_no=chunk_no,
        content="법정민원, 질의민원, 건의민원, 기타민원, 고충민원",
        source_type="manual",
        metadata={
            "chapter": "제1편 민원정보공개",
            "section": "민원의 처리",
        },
        similarity=similarity,
        document_title="민원의 종류",
        file_name=SAMPLE_FILE_NAME,
        file_path=f"data/raw/manuals/{SAMPLE_FILE_NAME}",
    )


def test_build_context_includes_source_metadata():
    context = build_context([_sample_result()])

    assert SAMPLE_FILE_NAME in context
    assert "제1편 민원정보공개" in context
    assert "민원의 처리" in context
    assert "법정민원" in context


def test_build_sources_maps_retrieval_fields():
    sources = build_sources([_sample_result(), _sample_result(chunk_no=2, similarity=0.41)])

    assert len(sources) == 2
    assert sources[0].file_name == SAMPLE_FILE_NAME
    assert sources[0].chapter == "제1편 민원정보공개"
    assert sources[1].chunk_no == 2


def test_llm_service_generate_answer_with_mock_client():
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="민원은 일반민원과 고충민원으로 구분됩니다."))]
    )

    service = LLMService(client=mock_client, model="gpt-4.1-mini")
    answer = service.generate_answer("민원 종류 알려줘", [_sample_result()])

    assert "민원" in answer
    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-4.1-mini"
    assert call_kwargs["messages"][1]["content"] == build_user_message("민원 종류 알려줘", [_sample_result()])


def test_llm_service_returns_fallback_when_no_results():
    mock_client = MagicMock()
    service = LLMService(client=mock_client)

    answer = service.generate_answer("민원 종류 알려줘", [])

    assert "찾지 못했습니다" in answer
    mock_client.chat.completions.create.assert_not_called()


def test_rag_service_answers_relevant_question():
    service = RagService(match_count=5, match_threshold=0.3)
    response = service.ask("민원 종류 알려줘")

    logger.info("answer=%s", response.answer)
    logger.info("sources=%s", [source.file_name for source in response.sources])

    assert response.query == "민원 종류 알려줘"
    assert response.answer.strip()
    assert len(response.sources) >= 1
    assert response.sources[0].file_name == SAMPLE_FILE_NAME
    assert any(keyword in response.answer for keyword in ("민원", "법정", "고충"))
