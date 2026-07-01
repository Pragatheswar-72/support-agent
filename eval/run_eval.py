"""Router evaluation harness.

Measures whether the orchestrator's routing LLM classifies realistic customer
messages into the correct specialist (ORDER/REFUND/PAYMENT/FAQ/ESCALATE). This
is distinct from tests/test_routing.py, which only checks the graph wiring
with a mocked LLM — this harness measures actual LLM classification quality
against a curated dataset, including deliberately tricky/ambiguous messages.

Run:  python eval/run_eval.py            (calls the real LLM, one request per
                                           message; needs GEMINI_API_KEY or
                                           GROQ_API_KEY; respects --sleep to
                                           stay under free-tier rate limits)
      python eval/run_eval.py --dry-run  (no API calls; validates the dataset
                                           and prints what would run)
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.orchestrator import ROUTES, route_node  # noqa: E402

HERE = os.path.dirname(__file__)


def load_dataset() -> list[dict]:
    with open(os.path.join(HERE, "eval_dataset.json"), encoding="utf-8") as f:
        return json.load(f)


def classify(message: str) -> str:
    return route_node({"user_message": message})["route"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="validate the dataset without calling the LLM")
    parser.add_argument("--sleep", type=float, default=2.0, help="seconds between live LLM calls")
    args = parser.parse_args()

    dataset = load_dataset()
    assert all(item["expected_route"] in ROUTES for item in dataset), "bad expected_route in dataset"

    if args.dry_run:
        print(f"Dataset OK: {len(dataset)} scenarios, all expected_route values valid. Skipping LLM calls (--dry-run).")
        return

    print(f"{'message':<55}{'expected':<10}{'actual':<10}{'result'}")
    print("-" * 90)

    correct = 0
    confusion: dict[str, dict[str, int]] = {}
    for i, item in enumerate(dataset):
        message, expected = item["message"], item["expected_route"]
        actual = classify(message)
        ok = actual == expected
        correct += int(ok)
        confusion.setdefault(expected, {}).setdefault(actual, 0)
        confusion[expected][actual] += 1
        print(f"{message[:53]:<55}{expected:<10}{actual:<10}{'PASS' if ok else 'FAIL'}")
        if i < len(dataset) - 1:
            time.sleep(args.sleep)

    n = len(dataset)
    print("-" * 90)
    print(f"Routing accuracy: {correct}/{n} = {correct / n:.0%}")
    print("\nConfusion (expected -> {actual: count}):")
    for expected, actuals in confusion.items():
        print(f"  {expected}: {actuals}")


if __name__ == "__main__":
    main()
