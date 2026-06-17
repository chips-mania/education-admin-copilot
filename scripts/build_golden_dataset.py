"""Build golden dataset: random 45 chunks + AI-generated questions + human slots."""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from openai import OpenAI  # noqa: E402

from app.config.settings import settings  # noqa: E402
from app.db.supabase_client import get_supabase_client  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

EVAL_DIR = ROOT_DIR / "data" / "evaluation"
DEFAULT_OUTPUT = EVAL_DIR / "golden_dataset.json"

QUESTION_TYPES = ("direct", "paraphrase", "situation")
AUTHORS = ("ai", "human")
CONTENT_PREVIEW_CHARS = 400
PAGE_SIZE = 1000
CONTENT_FOR_GENERATION_CHARS = 2000

TYPE_LABELS = {
    "direct": "직접 질의형",
    "paraphrase": "의미 변환형",
    "situation": "상황 기반형",
}

TYPE_PROMPTS = {
    "direct": (
        "청크의 핵심 용어·제목·키워드를 그대로 사용하는 직접적인 질문 1개를 작성하세요. "
        "예: '민원이란 무엇인가요?', '민원의 종류는 무엇인가요?'"
    ),
    "paraphrase": (
        "청크 내용과 같은 의미이지만 다른 표현을 쓰는 질문 1개를 작성하세요. "
        "본문 문장을 그대로 복사하지 말고, 동의어·구어체·다른 어순으로 바꾸세요. "
        "예: '학교 통장은 어떻게 관리하나요?'"
    ),
    "situation": (
        "정답 청크의 핵심 키워드·전문용어·제목을 질문에 넣지 말고, "
        "실무 상황만 설명하는 질문 1개를 작성하세요. "
        "예: '새로 받은 지원금을 기존 사업 예산에 같이 넣어도 되나요?'"
    ),
}


def normalize_text(text: str) -> str:
    return " ".join((text or "").split())


def build_content_preview(content: str) -> str:
    normalized = content.strip()
    preview = normalized[:CONTENT_PREVIEW_CHARS]
    if len(normalized) > CONTENT_PREVIEW_CHARS:
        preview += "..."
    return preview


def is_heading_only_chunk(heading: str, content: str) -> bool:
    """Exclude chunks where body is empty and only the heading remains."""
    heading_text = normalize_text(heading)
    if not heading_text:
        return False
    preview = build_content_preview(content)
    return heading_text == normalize_text(preview)


def filter_eligible_chunks(chunks: list[dict]) -> tuple[list[dict], int]:
    eligible: list[dict] = []
    excluded = 0
    for chunk in chunks:
        if is_heading_only_chunk(chunk["heading"], chunk["content"]):
            excluded += 1
            continue
        eligible.append(chunk)
    return eligible, excluded


def fetch_all_chunks() -> list[dict]:
    client = get_supabase_client()
    documents_response = client.table("documents").select("id, title, file_name, file_path, source_type").execute()
    documents = {row["id"]: row for row in (documents_response.data or [])}

    rows: list[dict] = []
    offset = 0
    while True:
        response = (
            client.table("chunks")
            .select("id, document_id, chunk_no, chapter, heading, content, source_type")
            .order("document_id")
            .order("chunk_no")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        batch = response.data or []
        if not batch:
            break

        for chunk in batch:
            document = documents.get(chunk["document_id"])
            if document is None:
                logger.warning("Missing document for chunk id=%s", chunk["id"])
                continue
            rows.append(
                {
                    "chunk_id": chunk["id"],
                    "document_id": chunk["document_id"],
                    "chunk_no": chunk["chunk_no"],
                    "chapter": chunk.get("chapter") or "",
                    "heading": chunk.get("heading") or "",
                    "content": chunk.get("content") or "",
                    "source_type": chunk.get("source_type") or document.get("source_type") or "",
                    "document_title": document.get("title") or "",
                    "file_name": document.get("file_name") or "",
                    "file_path": document.get("file_path") or "",
                }
            )

        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    logger.info("Fetched %d chunk(s) from Supabase", len(rows))
    return rows


def build_chunk_type_assignments(sample_count: int, *, seed: int) -> list[str]:
    """One question type per chunk; ai and human share the same type."""
    per_type = sample_count // len(QUESTION_TYPES)
    remainder = sample_count % len(QUESTION_TYPES)
    slots = list(QUESTION_TYPES) * per_type
    slots.extend(QUESTION_TYPES[:remainder])
    rng = random.Random(seed + 1)
    rng.shuffle(slots)
    return slots


def build_generation_prompt(*, question_type: str, chunk: dict) -> str:
    content = chunk["content"].strip()
    if len(content) > CONTENT_FOR_GENERATION_CHARS:
        content = content[:CONTENT_FOR_GENERATION_CHARS] + "..."

    location = " > ".join(
        part for part in (chunk["document_title"], chunk["chapter"], chunk["heading"]) if part
    )

    return (
        f"다음은 교육청 행정업무 매뉴얼의 한 청크입니다.\n\n"
        f"문서 위치: {location}\n\n"
        f"본문:\n{content}\n\n"
        f"유형: {TYPE_LABELS[question_type]}\n"
        f"지침: {TYPE_PROMPTS[question_type]}\n\n"
        "규칙:\n"
        "- 질문 1개만 출력 (번호, 따옴표, 설명 없이 질문 문장만)\n"
        "- 이 청크 내용에 답할 수 있는 질문이어야 함\n"
        "- 한국어로 작성\n"
        "- 80자 이내 권장"
    )


def generate_ai_question(
    client: OpenAI,
    *,
    model: str,
    question_type: str,
    chunk: dict,
) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "당신은 교육행정 RAG 검색 성능 평가용 질문을 만드는 전문가입니다. "
                    "지시된 유형에 맞는 질문 문장 하나만 출력하세요."
                ),
            },
            {"role": "user", "content": build_generation_prompt(question_type=question_type, chunk=chunk)},
        ],
        temperature=0.4,
    )
    question = (response.choices[0].message.content or "").strip()
    question = question.strip("\"'「」")
    if question.endswith("?"):
        return question
    if question.endswith("."):
        return question[:-1] + "?"
    return question + "?"


def build_questions(
    sample_index: int,
    chunk_no: int,
    question_type: str,
    *,
    ai_question: str = "",
) -> list[dict]:
    questions: list[dict] = []
    base_question_id = (sample_index - 1) * len(AUTHORS) + 1

    for author_index, author in enumerate(AUTHORS):
        questions.append(
            {
                "question_id": base_question_id + author_index,
                "author": author,
                "type": question_type,
                "question": ai_question if author == "ai" else "",
                "gold_chunks": [chunk_no],
            }
        )

    return questions


def generate_ai_questions_for_samples(
    samples: list[dict],
    *,
    model: str,
    delay_seconds: float,
) -> None:
    settings.validate_openai()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    for index, sample in enumerate(samples, start=1):
        ai_slot = next(q for q in sample["questions"] if q["author"] == "ai")
        if ai_slot["question"]:
            logger.info("Sample %d: AI question already set, skipping", sample["sample_id"])
            continue

        chunk_context = {
            "document_title": sample["source"]["document_title"],
            "chapter": sample["source"]["chapter"],
            "heading": sample["source"]["heading"],
            "content": sample.get("_full_content", sample["content_preview"]),
        }

        logger.info(
            "Generating AI question %d/%d (type=%s, heading=%s)",
            index,
            len(samples),
            sample["type"],
            chunk_context["heading"][:40],
        )
        question = generate_ai_question(
            client,
            model=model,
            question_type=sample["type"],
            chunk=chunk_context,
        )
        ai_slot["question"] = question
        logger.info("  -> %s", question)

        if delay_seconds > 0 and index < len(samples):
            time.sleep(delay_seconds)


def build_dataset(*, sample_size: int, seed: int, generate_ai: bool, model: str, delay_seconds: float) -> dict:
    all_chunks = fetch_all_chunks()
    chunks, excluded_heading_only = filter_eligible_chunks(all_chunks)
    logger.info(
        "Eligible chunks: %d (excluded heading-only: %d / total %d)",
        len(chunks),
        excluded_heading_only,
        len(all_chunks),
    )
    if len(chunks) < sample_size:
        raise ValueError(
            f"Not enough eligible chunks: have {len(chunks)}, need {sample_size} "
            f"(excluded {excluded_heading_only} heading-only chunk(s))"
        )

    rng = random.Random(seed)
    sampled = rng.sample(chunks, sample_size)
    sampled.sort(key=lambda row: (row["document_title"], row["chunk_no"]))

    chunk_type_assignments = build_chunk_type_assignments(sample_size, seed=seed)
    type_counts = {question_type: 0 for question_type in QUESTION_TYPES}
    chunk_type_counts = {question_type: 0 for question_type in QUESTION_TYPES}
    for question_type in chunk_type_assignments:
        chunk_type_counts[question_type] += 1
        type_counts[question_type] += len(AUTHORS)

    samples = []
    for index, chunk in enumerate(sampled, start=1):
        content = chunk["content"].strip()
        preview = build_content_preview(content)
        question_type = chunk_type_assignments[index - 1]

        sample = {
            "sample_id": index,
            "type": question_type,
            "chunk_id": chunk["chunk_id"],
            "gold_chunks": [chunk["chunk_no"]],
            "source": {
                "document_id": chunk["document_id"],
                "document_title": chunk["document_title"],
                "file_name": chunk["file_name"],
                "file_path": chunk["file_path"],
                "chapter": chunk["chapter"],
                "heading": chunk["heading"],
            },
            "content_preview": preview,
            "questions": build_questions(index, chunk["chunk_no"], question_type),
            "_full_content": content,
        }
        samples.append(sample)

    if generate_ai:
        generate_ai_questions_for_samples(samples, model=model, delay_seconds=delay_seconds)

    for sample in samples:
        sample.pop("_full_content", None)

    ai_filled = sum(
        1
        for sample in samples
        for question in sample["questions"]
        if question["author"] == "ai" and question["question"]
    )

    return {
        "version": "2.0",
        "description": "Golden dataset for Contextual Retrieval evaluation (45 chunks, 90 questions)",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "sample_size": sample_size,
        "total_chunks": len(all_chunks),
        "eligible_chunks": len(chunks),
        "excluded_heading_only_chunks": excluded_heading_only,
        "documents_in_corpus": len({chunk["document_id"] for chunk in all_chunks}),
        "question_slots_per_chunk": len(AUTHORS),
        "expected_total_questions": sample_size * len(AUTHORS),
        "ai_questions_generated": ai_filled,
        "human_questions_pending": sample_size - ai_filled if not generate_ai else sample_size,
        "question_types": list(QUESTION_TYPES),
        "type_labels": TYPE_LABELS,
        "type_distribution": type_counts,
        "chunk_type_distribution": chunk_type_counts,
        "matching_key": "document_id + chunk_no (gold_chunks)",
        "samples": samples,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build golden dataset from Supabase chunks")
    parser.add_argument("--sample-size", type=int, default=45)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument(
        "--generate-ai",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Generate AI questions via OpenAI (default: true)",
    )
    parser.add_argument("--model", default=None, help="OpenAI model (default: OPENAI_MODEL from .env)")
    parser.add_argument("--delay", type=float, default=0.3, help="Delay between API calls in seconds")
    args = parser.parse_args()

    model = args.model or settings.OPENAI_MODEL
    dataset = build_dataset(
        sample_size=args.sample_size,
        seed=args.seed,
        generate_ai=args.generate_ai,
        model=model,
        delay_seconds=args.delay,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info("Wrote %s", output_path)
    print(
        json.dumps(
            {
                "output": str(output_path.relative_to(ROOT_DIR)),
                "sample_size": dataset["sample_size"],
                "total_chunks": dataset["total_chunks"],
                "eligible_chunks": dataset["eligible_chunks"],
                "excluded_heading_only_chunks": dataset["excluded_heading_only_chunks"],
                "expected_total_questions": dataset["expected_total_questions"],
                "ai_questions_generated": dataset["ai_questions_generated"],
                "type_distribution": dataset["type_distribution"],
                "chunk_type_distribution": dataset["chunk_type_distribution"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
