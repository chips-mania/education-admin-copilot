import argparse
import json
import logging
import sys

ROOT_DIR = __import__("pathlib").Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.services.rag_service import RagService

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask a question via RAG (retrieval + LLM)")
    parser.add_argument("question", help="User question")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--threshold", type=float, default=0.5)
    args = parser.parse_args()

    service = RagService(match_count=args.top_k, match_threshold=args.threshold)
    response = service.ask(args.question)
    print(json.dumps(response.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
