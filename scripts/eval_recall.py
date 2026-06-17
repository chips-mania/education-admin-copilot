"""Evaluate V1 vs V2 retrieval on the golden dataset (Recall@k, MRR, mean rank)."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.services.retrieval_service import RetrievalService  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

EVAL_DIR = ROOT_DIR / "data" / "evaluation"
DEFAULT_DATASET = EVAL_DIR / "golden_dataset.json"
DEFAULT_OUTPUT = EVAL_DIR / "eval_results.json"

RECALL_KS = (1, 5, 10)
QUESTION_TYPES = ("direct", "paraphrase", "situation")
AUTHORS = ("ai", "human")
TYPE_LABELS = {
    "direct": "직접 질의형",
    "paraphrase": "의미 변환형",
    "situation": "상황 기반형",
}


@dataclass(frozen=True)
class EvalQuestion:
    question_id: int
    question: str
    question_type: str
    author: str
    document_id: int
    gold_chunks: tuple[int, ...]
    sample_id: int
    heading: str
    document_title: str


def load_questions(dataset: dict) -> list[EvalQuestion]:
    questions: list[EvalQuestion] = []
    for sample in dataset["samples"]:
        document_id = sample["source"]["document_id"]
        heading = sample["source"].get("heading", "")
        document_title = sample["source"].get("document_title", "")

        for slot in sample["questions"]:
            text = (slot.get("question") or "").strip()
            if not text:
                logger.warning("Skipping empty question_id=%s", slot.get("question_id"))
                continue

            questions.append(
                EvalQuestion(
                    question_id=slot["question_id"],
                    question=text,
                    question_type=slot["type"],
                    author=slot["author"],
                    document_id=document_id,
                    gold_chunks=tuple(slot["gold_chunks"]),
                    sample_id=sample["sample_id"],
                    heading=heading,
                    document_title=document_title,
                )
            )

    questions.sort(key=lambda row: row.question_id)
    return questions


def gold_keys(question: EvalQuestion) -> set[tuple[int, int]]:
    return {(question.document_id, chunk_no) for chunk_no in question.gold_chunks}


def find_rank(results: list, gold: set[tuple[int, int]]) -> int | None:
    for index, result in enumerate(results, start=1):
        if (result.document_id, result.chunk_no) in gold:
            return index
    return None


def empty_metrics() -> dict[str, Any]:
    metrics: dict[str, Any] = {f"recall@{k}": 0.0 for k in RECALL_KS}
    metrics["mrr"] = 0.0
    metrics["mean_rank"] = None
    metrics["hits"] = 0
    metrics["misses"] = 0
    metrics["count"] = 0
    return metrics


def summarize_ranks(ranks: list[int | None]) -> dict[str, Any]:
    total = len(ranks)
    hits = [rank for rank in ranks if rank is not None]
    misses = total - len(hits)

    metrics = empty_metrics()
    metrics["count"] = total
    metrics["hits"] = len(hits)
    metrics["misses"] = misses

    if not hits:
        return metrics

    for k in RECALL_KS:
        metrics[f"recall@{k}"] = round(sum(1 for rank in hits if rank <= k) / total, 4)

    metrics["mrr"] = round(sum(1 / rank for rank in hits) / total, 4)
    metrics["mean_rank"] = round(sum(hits) / len(hits), 2)
    return metrics


def evaluate_version(
    questions: list[EvalQuestion],
    *,
    embed_version: Literal["v1", "v2"],
    match_count: int,
    match_threshold: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    service = RetrievalService(
        match_count=match_count,
        match_threshold=match_threshold,
        embed_version=embed_version,
    )

    per_question: list[dict[str, Any]] = []
    ranks: list[int | None] = []
    ranks_by_type: dict[str, list[int | None]] = {t: [] for t in QUESTION_TYPES}
    ranks_by_author: dict[str, list[int | None]] = {a: [] for a in AUTHORS}

    logger.info("Evaluating %s (%d questions)", embed_version, len(questions))

    for index, question in enumerate(questions, start=1):
        gold = gold_keys(question)
        response = service.search(question.question)
        rank = find_rank(response.results, gold)
        ranks.append(rank)
        ranks_by_type[question.question_type].append(rank)
        ranks_by_author[question.author].append(rank)

        top_similarity = response.results[0].similarity if response.results else None
        result_count = len(response.results)

        per_question.append(
            {
                "question_id": question.question_id,
                "sample_id": question.sample_id,
                "type": question.question_type,
                "author": question.author,
                "question": question.question,
                "document_id": question.document_id,
                "gold_chunks": list(question.gold_chunks),
                "rank": rank,
                "hit": rank is not None,
                "reciprocal_rank": round(1 / rank, 4) if rank else 0.0,
                "result_count": result_count,
                "top_similarity": round(top_similarity, 4) if top_similarity is not None else None,
            }
        )

        if index % 10 == 0 or index == len(questions):
            logger.info("  %s progress %d/%d", embed_version, index, len(questions))

    overall = summarize_ranks(ranks)
    by_type = {question_type: summarize_ranks(ranks_by_type[question_type]) for question_type in QUESTION_TYPES}
    by_author = {author: summarize_ranks(ranks_by_author[author]) for author in AUTHORS}

    return (
        {
            "overall": overall,
            "by_type": by_type,
            "by_author": by_author,
        },
        per_question,
    )


def build_rank_shifts(
    questions: list[EvalQuestion],
    v1_results: list[dict[str, Any]],
    v2_results: list[dict[str, Any]],
    *,
    match_threshold: float,
    rank_shift_match_count: int,
    top_n: int,
) -> list[dict[str, Any]]:
    v1_service = RetrievalService(
        match_count=rank_shift_match_count,
        match_threshold=match_threshold,
        embed_version="v1",
    )
    v2_service = RetrievalService(
        match_count=rank_shift_match_count,
        match_threshold=match_threshold,
        embed_version="v2",
    )

    question_map = {question.question_id: question for question in questions}
    shifts: list[dict[str, Any]] = []

    for v1_row, v2_row in zip(v1_results, v2_results, strict=True):
        question = question_map[v1_row["question_id"]]
        gold = gold_keys(question)

        v1_deep = v1_service.search(question.question)
        v2_deep = v2_service.search(question.question)
        v1_rank = find_rank(v1_deep.results, gold)
        v2_rank = find_rank(v2_deep.results, gold)

        if v1_rank is None or v2_rank is None:
            continue

        improvement = v1_rank - v2_rank
        if improvement <= 0:
            continue

        shifts.append(
            {
                "question_id": question.question_id,
                "type": question.question_type,
                "type_label": TYPE_LABELS[question.question_type],
                "author": question.author,
                "question": question.question,
                "heading": question.heading,
                "document_title": question.document_title,
                "v1_rank": v1_rank,
                "v2_rank": v2_rank,
                "rank_improvement": improvement,
            }
        )

    shifts.sort(key=lambda row: (-row["rank_improvement"], row["question_id"]))
    return shifts[:top_n]


def build_report(
    dataset: dict,
    questions: list[EvalQuestion],
    v1_bundle: dict[str, Any],
    v2_bundle: dict[str, Any],
    v1_per_question: list[dict[str, Any]],
    v2_per_question: list[dict[str, Any]],
    rank_shifts: list[dict[str, Any]],
    *,
    match_count: int,
    match_threshold: float,
    rank_shift_match_count: int,
) -> dict[str, Any]:
    def flatten_version(bundle: dict[str, Any]) -> dict[str, Any]:
        overall = bundle["overall"]
        return {
            **{key: overall[key] for key in overall if key.startswith("recall@") or key in {"mrr", "mean_rank"}},
            "hits": overall["hits"],
            "misses": overall["misses"],
            "count": overall["count"],
        }

    by_type: dict[str, Any] = {}
    for question_type in QUESTION_TYPES:
        by_type[question_type] = {
            "label": TYPE_LABELS[question_type],
            "v1": {
                k: v
                for k, v in v1_bundle["by_type"][question_type].items()
                if k.startswith("recall@") or k in {"mrr", "mean_rank", "count"}
            },
            "v2": {
                k: v
                for k, v in v2_bundle["by_type"][question_type].items()
                if k.startswith("recall@") or k in {"mrr", "mean_rank", "count"}
            },
        }

    by_author: dict[str, Any] = {}
    for author in AUTHORS:
        by_author[author] = {
            "v1": {
                k: v
                for k, v in v1_bundle["by_author"][author].items()
                if k.startswith("recall@") or k in {"mrr", "mean_rank", "count"}
            },
            "v2": {
                k: v
                for k, v in v2_bundle["by_author"][author].items()
                if k.startswith("recall@") or k in {"mrr", "mean_rank", "count"}
            },
        }

    return {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_version": dataset.get("version"),
        "dataset_path": "data/evaluation/golden_dataset.json",
        "question_count": len(questions),
        "config": {
            "match_count": match_count,
            "match_threshold": match_threshold,
            "rank_shift_match_count": rank_shift_match_count,
            "matching_key": "document_id + chunk_no",
            "recall_ks": list(RECALL_KS),
        },
        "v1": flatten_version(v1_bundle),
        "v2": flatten_version(v2_bundle),
        "by_type": by_type,
        "by_author": by_author,
        "rank_shifts": rank_shifts,
        "per_question": {
            "v1": v1_per_question,
            "v2": v2_per_question,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate retrieval recall on golden dataset")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--match-count", type=int, default=10)
    parser.add_argument("--match-threshold", type=float, default=0.0)
    parser.add_argument("--rank-shift-match-count", type=int, default=50)
    parser.add_argument("--rank-shift-top-n", type=int, default=10)
    args = parser.parse_args()

    dataset = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    questions = load_questions(dataset)
    if not questions:
        raise ValueError("No evaluable questions found")

    v1_bundle, v1_per_question = evaluate_version(
        questions,
        embed_version="v1",
        match_count=args.match_count,
        match_threshold=args.match_threshold,
    )
    v2_bundle, v2_per_question = evaluate_version(
        questions,
        embed_version="v2",
        match_count=args.match_count,
        match_threshold=args.match_threshold,
    )

    logger.info("Computing rank shifts (match_count=%d)", args.rank_shift_match_count)
    rank_shifts = build_rank_shifts(
        questions,
        v1_per_question,
        v2_per_question,
        match_threshold=args.match_threshold,
        rank_shift_match_count=args.rank_shift_match_count,
        top_n=args.rank_shift_top_n,
    )

    report = build_report(
        dataset,
        questions,
        v1_bundle,
        v2_bundle,
        v1_per_question,
        v2_per_question,
        rank_shifts,
        match_count=args.match_count,
        match_threshold=args.match_threshold,
        rank_shift_match_count=args.rank_shift_match_count,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Wrote %s", output_path)

    summary = {
        "question_count": report["question_count"],
        "config": report["config"],
        "v1": report["v1"],
        "v2": report["v2"],
        "by_type": {
            question_type: {
                "label": section["label"],
                "v1_recall@10": section["v1"]["recall@10"],
                "v2_recall@10": section["v2"]["recall@10"],
            }
            for question_type, section in report["by_type"].items()
        },
        "rank_shift_examples": report["rank_shifts"][:3],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
