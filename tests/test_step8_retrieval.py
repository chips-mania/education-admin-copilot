import logging

from app.services.retrieval_service import RetrievalService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SAMPLE_FILE_NAME = "01-01-01 민원의 종류.hwpx"


def test_search_returns_results_for_relevant_query():
    service = RetrievalService(match_count=5, match_threshold=0.3)
    response = service.search("민원 종류 알려줘")

    logger.info("result_count=%d", len(response.results))
    for result in response.results:
        logger.info(
            "file=%s chunk_no=%s similarity=%.4f",
            result.file_name,
            result.chunk_no,
            result.similarity,
        )

    assert response.query == "민원 종류 알려줘"
    assert len(response.results) >= 1
    assert response.results[0].file_name == SAMPLE_FILE_NAME
    assert "민원" in response.results[0].content or "법정민원" in response.results[0].content


def test_search_top_result_has_metadata():
    service = RetrievalService(match_count=5, match_threshold=0.3)
    response = service.search("민원의 종류가 뭐야")

    assert response.results
    top = response.results[0]
    assert top.metadata["chapter"] == "제1편 민원정보공개"
    assert top.metadata["section"] == "민원의 처리"
    assert top.file_path.endswith(SAMPLE_FILE_NAME)
