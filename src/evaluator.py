"""Evaluation utilities for ScopeLens."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pandas as pd

from .policy_engine import triage_submission
from .schema import LABELS

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEST_SET = ROOT / "data" / "test_cases.csv"


def load_test_set(path: str | Path = DEFAULT_TEST_SET) -> pd.DataFrame:
    return pd.read_csv(path)


def _precision_recall_f1(gold: List[str], pred: List[str], label: str) -> Tuple[float, float, float]:
    tp = sum(1 for g, p in zip(gold, pred) if g == label and p == label)
    fp = sum(1 for g, p in zip(gold, pred) if g != label and p == label)
    fn = sum(1 for g, p in zip(gold, pred) if g == label and p != label)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def compute_metrics(gold: Iterable[str], pred: Iterable[str]) -> Dict[str, float]:
    gold_list = list(gold)
    pred_list = list(pred)
    n = len(gold_list)
    accuracy = sum(1 for g, p in zip(gold_list, pred_list) if g == p) / n if n else 0.0
    f1s = [_precision_recall_f1(gold_list, pred_list, label)[2] for label in LABELS]
    return {
        "n": float(n),
        "accuracy": accuracy,
        "macro_f1": sum(f1s) / len(f1s) if f1s else 0.0,
        **{f"f1_{label}": f1 for label, f1 in zip(LABELS, f1s)},
    }


def confusion_matrix_df(gold: Iterable[str], pred: Iterable[str]) -> pd.DataFrame:
    matrix = pd.DataFrame(0, index=LABELS, columns=LABELS)
    for g, p in zip(gold, pred):
        if g not in matrix.index:
            matrix.loc[g, :] = 0
        if p not in matrix.columns:
            matrix[p] = 0
        matrix.loc[g, p] += 1
    matrix.index.name = "gold"
    matrix.columns.name = "predicted"
    return matrix


def evidence_support_score(output) -> float:
    """Lightweight automatic proxy for evidence quality.

    1.0 = at least one explicit piece of evidence and no automation violation.
    This is not a substitute for manual/editorial review; it exists to make the
    appendix reproducible.
    """
    score = 0.0
    if output.supporting_evidence:
        score += 0.5
    if any(ev.source in {"title", "abstract", "keywords"} for ev in output.supporting_evidence):
        score += 0.25
    if any(ev.source == "scope_rubric" for ev in output.supporting_evidence):
        score += 0.15
    if output.should_not_automate is True:
        score += 0.10
    return min(score, 1.0)


def run_evaluation(
    mode: str = "offline_policy",
    path: str | Path = DEFAULT_TEST_SET,
    model: str | None = None,
) -> tuple[pd.DataFrame, Dict[str, float], pd.DataFrame]:
    df = load_test_set(path)
    rows = []
    for _, row in df.iterrows():
        output = triage_submission(
            title=str(row["title"]),
            abstract=str(row["abstract"]),
            keywords=str(row.get("keywords", "")),
            mode=mode,
            model=model,
        )
        rows.append(
            {
                "case_id": row["case_id"],
                "gold_label": row["gold_label"],
                "predicted_label": output.decision_label,
                "confidence": output.confidence,
                "evidence_support_score": evidence_support_score(output),
                "uncertainty_flags": " | ".join(output.uncertainty_flags),
                "memo": output.editor_memo,
            }
        )
    result_df = pd.DataFrame(rows)
    metrics = compute_metrics(result_df["gold_label"], result_df["predicted_label"])
    cm = confusion_matrix_df(result_df["gold_label"], result_df["predicted_label"])
    return result_df, metrics, cm
