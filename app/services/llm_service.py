import logging
from typing import Any

from openai import OpenAI

from app.config.settings import settings
from app.services.retrieval_service import RetrievalResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """당신은 교육행정 업무 매뉴얼·법령·규정·해석례를 바탕으로 답변하는 교육행정 AI 어시스턴트입니다.

규칙:
1. 제공된 참고 자료에 근거하여 답변하세요.
2. 참고 자료에 없는 내용은 추측하지 마세요.
3. 참고 자료가 부족하면 "제공된 자료에서 확인할 수 없습니다"라고 답하세요.
4. 답변은 명확하고 간결한 한국어로 작성하세요.
5. 가능하면 항목·구분을 구조화하여 설명하세요."""


def build_context(results: list[RetrievalResult]) -> str:
    sections: list[str] = []
    for index, result in enumerate(results, start=1):
        metadata = result.metadata or {}
        chapter = metadata.get("chapter", "")
        section = metadata.get("section", "")
        location = " > ".join(part for part in [chapter, section] if part)

        header = (
            f"[출처 {index}] "
            f"파일: {result.file_name} | "
            f"제목: {result.document_title} | "
            f"chunk: {result.chunk_no}"
        )
        if location:
            header += f" | 위치: {location}"

        sections.append(f"{header}\n내용:\n{result.content}")

    return "\n\n".join(sections)


def build_user_message(query: str, results: list[RetrievalResult]) -> str:
    context = build_context(results)
    return (
        f"질문:\n{query}\n\n"
        f"참고 자료:\n{context}\n\n"
        "위 참고 자료만을 근거로 질문에 답변하세요."
    )


class LLMService:
    def __init__(self, client: Any | None = None, model: str | None = None):
        settings.validate_openai()
        self.client = client or OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = model or settings.OPENAI_MODEL

    def generate_answer(self, query: str, results: list[RetrievalResult]) -> str:
        if not results:
            logger.info("No retrieval results; skipping LLM call")
            return "관련된 참고 자료를 찾지 못했습니다. 질문을 다시 입력해 주세요."

        logger.info("Generating answer with model=%s context_chunks=%d", self.model, len(results))
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_message(query, results)},
            ],
            temperature=0.2,
        )

        answer = (response.choices[0].message.content or "").strip()
        logger.info("Generated answer (%d chars)", len(answer))
        return answer
