"""Simpler baseline for ScopeLens.

The baseline is deliberately plain: a keyword classifier and templated memo.
It provides a credible comparison point without pretending to do nuanced editorial
reasoning.
"""
from __future__ import annotations

from .feature_extractor import extract_features
from .schema import EvidenceItem, TriageOutput


def keyword_baseline(title: str, abstract: str, keywords: str) -> TriageOutput:
    """Return a simple non-GenAI keyword-based triage label."""
    features = extract_features(title, abstract, keywords)

    if features.abstract_word_count < 25:
        label = "insufficient_information"
        confidence = "medium"
        reason = "The abstract is too short for a reliable keyword-based scope decision."
        action = "request_more_information"
    elif features.out_of_scope_score >= 5 and features.in_scope_score < 6:
        label = "out_of_scope"
        confidence = "high"
        reason = "The baseline found strong non-thermal-radiation trap terms."
        action = "likely_desk_triage_review"
    elif features.in_scope_score >= 5:
        label = "in_scope"
        confidence = "medium"
        reason = "The baseline found thermal-radiation keywords above threshold."
        action = "proceed_to_editor_review"
    elif features.borderline_score >= 4 and features.has_radiation_signal:
        label = "borderline"
        confidence = "low"
        reason = "The baseline found mixed thermal-management and radiation signals."
        action = "request_editor_review"
    elif features.has_radiation_signal and features.has_thermal_signal:
        label = "borderline"
        confidence = "low"
        reason = "The baseline found weak thermal and radiation signals but no clear central topic."
        action = "request_editor_review"
    else:
        label = "out_of_scope"
        confidence = "medium"
        reason = "The baseline did not find enough thermal-radiation signal terms."
        action = "likely_desk_triage_review"

    evidence = []
    for hit_group, interpretation in [
        (features.in_scope_hits, "Thermal-radiation keyword signal."),
        (features.out_of_scope_hits, "Possible vocabulary trap or adjacent-domain signal."),
        (features.borderline_hits, "Adjacent thermal-management or systems signal."),
    ]:
        for hit in hit_group[:2]:
            evidence.append(
                EvidenceItem(
                    source=hit.source, quote_or_signal=hit.example or hit.term,
                    interpretation=interpretation,
                )
            )

    if not evidence:
        evidence.append(
            EvidenceItem(
                source="system_feature",
                quote_or_signal="No strong thermal-radiation keywords found.",
                interpretation="The baseline has limited evidence and should not be trusted alone.",
            )
        )

    memo = (
        f"Keyword baseline label: {label}. {reason} This comparator uses only thresholded term "
        "matches and should be expected to fail on semantic borderline cases."
    )

    return TriageOutput(
        decision_label=label,
        confidence=confidence,
        reasoning_summary=reason,
        supporting_evidence=evidence[:4],
        uncertainty_flags=["Baseline is keyword-only; no semantic adjudication."],
        editor_memo=memo,
        recommended_human_action=action,
        should_not_automate=True,
    )
