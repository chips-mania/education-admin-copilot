"""Resample specific golden dataset samples with new chunks + AI questions."""

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
from scripts.build_golden_dataset import (  # noqa: E402
    AUTHORS,
    DEFAULT_OUTPUT,
    build_content_preview,
    build_generation_prompt,
    build_questions,
    fetch_all_chunks,
    filter_eligible_chunks,
    generate_ai_question,
    is_heading_only_chunk,
    normalize_text,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def chunk_key(chunk: dict) -> tuple[int, int]:
    return (chunk["document_id"], chunk["chunk_no"])


def sample_chunk_key(sample: dict) -> tuple[int, int]:
    return (sample["source"]["document_id"], sample["gold_chunks"][0])


def find_samples_with_empty_human(samples: list[dict]) -> list[int]:
    ids: list[int] = []
    for sample in samples:
        human = next(q for q in sample["questions"] if q["author"] == "human")
        if not (human.get("question") or "").strip():
            ids.append(sample["sample_id"])
    return ids


def validate_samples(samples: list[dict]) -> dict:
    issues: list[str] = []
    seen: dict[tuple[int, int], int] = {}

    for sample in samples:
        key = sample_chunk_key(sample)
        if key in seen:
            issues.append(
                f"duplicate chunk document_id={key[0]} chunk_no={key[1]} "
                f"(sample {seen[key]} and {sample['sample_id']})"
            )
        seen[key] = sample["sample_id"]

        heading = sample["source"].get("heading", "")
        preview = sample.get("content_preview", "")
        content_for_check = preview[:-3] if preview.endswith("...") else preview
        if is_heading_only_chunk(heading, content_for_check):
            issues.append(f"heading-only chunk at sample {sample['sample_id']}")

        for question in sample["questions"]:
            if question["type"] != sample["type"]:
                issues.append(
                    f"type mismatch sample {sample['sample_id']}: "
                    f"sample={sample['type']} question_id={question['question_id']}={question['type']}"
                )
            if question["gold_chunks"] != sample["gold_chunks"]:
                issues.append(
                    f"gold_chunks mismatch sample {sample['sample_id']} question_id={question['question_id']}"
                )

    return {"ok": not issues, "issues": issues, "unique_chunks": len(seen)}


def build_sample_from_chunk(*, sample_id: int, question_type: str, chunk: dict) -> dict:
    content = chunk["content"].strip()
    preview = build_content_preview(content)
    return {
        "sample_id": sample_id,
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
        "questions": build_questions(sample_id, chunk["chunk_no"], question_type),
        "_full_content": content,
    }


def generate_ai_for_sample(
    client: OpenAI,
    sample: dict,
    *,
    model: str,
) -> str:
    chunk_context = {
        "document_title": sample["source"]["document_title"],
        "chapter": sample["source"]["chapter"],
        "heading": sample["source"]["heading"],
        "content": sample["_full_content"],
    }
    return generate_ai_question(
        client,
        model=model,
        question_type=sample["type"],
        chunk=chunk_context,
    )


def resample_dataset(
    dataset: dict,
    *,
    sample_ids: list[int],
    seed: int,
    model: str,
    delay_seconds: float,
) -> dict:
    samples = dataset["samples"]
    id_set = set(sample_ids)

    reserved_keys = {sample_chunk_key(s) for s in samples if s["sample_id"] not in id_set}

    all_chunks = fetch_all_chunks()
    eligible, _ = filter_eligible_chunks(all_chunks)
    pool = [c for c in eligible if chunk_key(c) not in reserved_keys]

    if len(pool) < len(sample_ids):
        raise ValueError(f"Not enough replacement chunks: pool={len(pool)}, need={len(sample_ids)}")

    rng = random.Random(seed)
    picked = rng.sample(pool, len(sample_ids))
    picked.sort(key=lambda row: (row["document_title"], row["chunk_no"]))

    settings.validate_openai()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    replacement_map = dict(zip(sorted(sample_ids), picked))
    new_samples: list[dict] = []

    for sample in samples:
        sid = sample["sample_id"]
        if sid not in id_set:
            new_samples.append(sample)
            continue

        chunk = replacement_map[sid]
        updated = build_sample_from_chunk(
            sample_id=sid,
            question_type=sample["type"],
            chunk=chunk,
        )

        if is_heading_only_chunk(updated["source"]["heading"], updated["_full_content"]):
            raise ValueError(
                f"Picked heading-only chunk for sample {sid}: {updated['source']['heading']}"
            )

        logger.info(
            "Resampling sample %d (%s) -> %s / chunk_no=%d",
            sid,
            sample["type"],
            chunk["heading"][:50],
            chunk["chunk_no"],
        )

        ai_slot = next(q for q in updated["questions"] if q["author"] == "ai")
        ai_slot["question"] = generate_ai_for_sample(client, updated, model=model)
        logger.info("  AI q%d: %s", ai_slot["question_id"], ai_slot["question"])

        updated.pop("_full_content")
        new_samples.append(updated)

        if delay_seconds > 0:
            time.sleep(delay_seconds)

    new_samples.sort(key=lambda s: s["sample_id"])
    dataset["samples"] = new_samples
    dataset["resampled_at"] = datetime.now(timezone.utc).isoformat()
    dataset["resampled_sample_ids"] = sorted(sample_ids)
    dataset["resample_seed"] = seed

    ai_filled = sum(
        1
        for sample in new_samples
        for question in sample["questions"]
        if question["author"] == "ai" and question["question"]
    )
    human_pending = sum(
        1
        for sample in new_samples
        for question in sample["questions"]
        if question["author"] == "human" and not (question.get("question") or "").strip()
    )
    dataset["ai_questions_generated"] = ai_filled
    dataset["human_questions_pending"] = human_pending

    validation = validate_samples(new_samples)
    dataset["validation"] = validation
    if not validation["ok"]:
        raise ValueError("Validation failed after resample: " + "; ".join(validation["issues"]))

    return dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Resample golden dataset samples with new chunks")
    parser.add_argument("--input", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument(
        "--sample-ids",
        default="",
        help="Comma-separated sample_ids (default: samples with empty human question)",
    )
    parser.add_argument("--seed", type=int, default=142)
    parser.add_argument("--model", default=None)
    parser.add_argument("--delay", type=float, default=0.3)
    args = parser.parse_args()

    input_path = Path(args.input)
    dataset = json.loads(input_path.read_text(encoding="utf-8"))

    if args.sample_ids.strip():
        sample_ids = [int(x.strip()) for x in args.sample_ids.split(",") if x.strip()]
    else:
        sample_ids = find_samples_with_empty_human(dataset["samples"])

    if not sample_ids:
        logger.info("No samples to resample")
        return

    logger.info("Resampling sample_ids: %s", sample_ids)
    model = args.model or settings.OPENAI_MODEL
    dataset = resample_dataset(
        dataset,
        sample_ids=sample_ids,
        seed=args.seed,
        model=model,
        delay_seconds=args.delay,
    )

    output_path = Path(args.output)
    output_path.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Wrote %s", output_path)

    print(
        json.dumps(
            {
                "resampled_sample_ids": dataset["resampled_sample_ids"],
                "resample_seed": dataset["resample_seed"],
                "human_questions_pending": dataset["human_questions_pending"],
                "validation": dataset["validation"],
                "replaced": [
                    {
                        "sample_id": s["sample_id"],
                        "type": s["type"],
                        "heading": s["source"]["heading"],
                        "gold_chunks": s["gold_chunks"],
                        "ai_question": next(
                            q["question"] for q in s["questions"] if q["author"] == "ai"
                        ),
                    }
                    for s in dataset["samples"]
                    if s["sample_id"] in sample_ids
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
