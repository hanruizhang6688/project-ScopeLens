from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluator import run_evaluation  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ScopeLens evaluation.")
    parser.add_argument(
        "--mode",
        choices=["offline_policy", "baseline", "llm"],
        default="offline_policy",
        help="Evaluation mode.",
    )
    parser.add_argument("--model", default=None, help="Optional OpenAI model name for llm mode.")
    parser.add_argument("--out", default=None, help="Optional path for predictions CSV.")
    args = parser.parse_args()

    results, metrics, cm = run_evaluation(mode=args.mode, model=args.model)
    print("Metrics")
    for key, value in metrics.items():
        if key == "n":
            print(f"{key}: {int(value)}")
        else:
            print(f"{key}: {value:.3f}")
    print("\nConfusion matrix")
    print(cm.to_string())

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        results.to_csv(out_path, index=False)
        print(f"\nSaved predictions to {out_path}")


if __name__ == "__main__":
    main()
