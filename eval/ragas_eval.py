"""RAGAS evaluation pipeline for the enterprise RAG system.

Dataset entry format (per spec):
{
    "question": "...",
    "ground_truth": "...",
    "retrieved_chunks": [...],
    "generated_answer": "..."
}

Run:
    python -m eval.ragas_eval --dataset eval/sample_dataset.json
"""
import argparse
import json
import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv

load_dotenv()


@dataclass
class EvalEntry:
    question: str
    ground_truth: str
    retrieved_chunks: list[str]
    generated_answer: str


@dataclass
class EvalResult:
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float

    def as_dict(self) -> dict[str, float]:
        return {
            "faithfulness": self.faithfulness,
            "answer_relevancy": self.answer_relevancy,
            "context_precision": self.context_precision,
            "context_recall": self.context_recall,
        }


def load_dataset(path: str) -> list[EvalEntry]:
    with open(path, encoding="utf-8") as f:
        raw: list[dict[str, Any]] = json.load(f)
    return [
        EvalEntry(
            question=item["question"],
            ground_truth=item["ground_truth"],
            retrieved_chunks=item["retrieved_chunks"],
            generated_answer=item["generated_answer"],
        )
        for item in raw
    ]


def run_evaluation(dataset: list[EvalEntry]) -> list[dict[str, Any]]:
    """Run RAGAS evaluation over a dataset. Returns per-entry results."""
    try:
        from ragas import evaluate
        from ragas.metrics import (
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        )
        from datasets import Dataset
    except ImportError as exc:
        raise ImportError(
            "Install ragas and datasets to run evaluation: pip install ragas datasets"
        ) from exc

    hf_dataset = Dataset.from_list(
        [
            {
                "question": e.question,
                "answer": e.generated_answer,
                "contexts": e.retrieved_chunks,
                "ground_truth": e.ground_truth,
            }
            for e in dataset
        ]
    )

    result = evaluate(
        hf_dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
    )

    df = result.to_pandas()
    return df.to_dict(orient="records")


def print_summary(results: list[dict[str, Any]]) -> None:
    if not results:
        print("No results.")
        return

    keys = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    print("\n=== RAGAS Evaluation Summary ===")
    for key in keys:
        values = [r[key] for r in results if key in r and r[key] is not None]
        avg = sum(values) / len(values) if values else float("nan")
        print(f"  {key:<22}: {avg:.4f}")
    print("================================\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RAGAS evaluation")
    parser.add_argument("--dataset", required=True, help="Path to JSON dataset file")
    parser.add_argument("--output", default=None, help="Optional path to save results JSON")
    args = parser.parse_args()

    dataset = load_dataset(args.dataset)
    print(f"Loaded {len(dataset)} entries from {args.dataset}")

    results = run_evaluation(dataset)
    print_summary(results)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to {args.output}")


if __name__ == "__main__":
    main()
