"""Main triage logic for ScopeLens."""
from __future__ import annotations

from typing import List

from .baseline import keyword_baseline
from .feature_extractor import FeatureSummary, TermHit, extract_features, features_as_text
from .llm_client import LLMUnavailable, call_openai_structured
from .prompts import SYSTEM_PROMPT, build_user_prompt
from .scope_rubric import SCOPE_RUBRIC
from .schema import EvidenceItem, TriageOutput


def _top_examples(hits: List[TermHit], limit: int = 3) -> List[EvidenceItem]:
    items: List[EvidenceItem] = []
    for hit in hits[:limit]:
        items.append(
            EvidenceItem(
                source=hit.source,
                quote_or_signal=hit.example or hit.term,
                interpretation=f"Matched rubric-relevant term: '{hit.term}'.",
            )
        )
    return items


def _rubric_evidence(label: str) -> EvidenceItem:
    return EvidenceItem(
        source="scope_rubric",
        quote_or_signal=SCOPE_RUBRIC[label][0],
        interpretation=f"This is the primary rubric criterion used for the {label} label.",
    )


def _determine_policy_label(features: FeatureSummary) -> tuple[str, str, str, str, list[str]]:
    """Heuristic adjudication used for offline demo and as LLM fallback."""
    flags: list[str] = []

    # Strong vocabulary traps should override brevity. Short biomedical/nuclear/wireless
    # abstracts are still out of scope rather than merely insufficient.
    if features.out_of_scope_score >= 5 and features.in_scope_score < 8:
        return (
            "out_of_scope",
            "high",
            "The dominant signals point to a non-thermal-radiation use of 'radiation' or an adjacent domain.",
            "likely_desk_triage_review",
            ["Vocabulary trap detected."],
        )

    # Generic/vague language should not be upgraded to borderline just because it
    # contains the words thermal or radiation.
    if features.vague_score >= 2 and features.in_scope_score < 10:
        return (
            "insufficient_information",
            "medium",
            "The submission uses broad or generic technical language without a clear radiation mechanism.",
            "request_more_information",
            ["Vague wording; central contribution unclear."],
        )

    # Clear thermal-radiation terms in the title/keywords can be enough even for a
    # compact abstract.
    if features.in_scope_score >= 7 and features.out_of_scope_score == 0 and features.borderline_score <= 4:
        return (
            "in_scope",
            "medium",
            "Thermal radiation appears to be the central physical mechanism and technical contribution.",
            "proceed_to_editor_review",
            [],
        )

    # Mixed heat-transfer/system cases should be flagged as borderline before they
    # are penalized for abstract length.
    if features.borderline_score >= 5 and features.has_radiation_signal and features.in_scope_score < 18:
        return (
            "borderline",
            "medium",
            "Radiation is present, but the stronger context is adjacent heat-transfer or system engineering.",
            "request_editor_review",
            ["Mixed-scope case; needs human review."],
        )

    if features.abstract_word_count < 25:
        return (
            "insufficient_information",
            "medium",
            "The abstract is too short to identify the central mechanism or contribution.",
            "request_more_information",
            ["Very short abstract."],
        )

    if features.abstract_word_count < 45 and features.in_scope_score < 5 and features.borderline_score < 5:
        return (
            "insufficient_information",
            "medium",
            "The submission contains limited detail and lacks strong thermal-radiation signals.",
            "request_more_information",
            ["Limited technical detail in abstract."],
        )

    if features.in_scope_score >= 10 and features.out_of_scope_score == 0 and features.borderline_score <= 4:
        return (
            "in_scope",
            "high",
            "Thermal radiation appears to be the central physical mechanism and technical contribution.",
            "proceed_to_editor_review",
            [],
        )

    if features.in_scope_score >= 10 and features.out_of_scope_score <= 3 and features.borderline_score <= 8:
        return (
            "in_scope",
            "medium",
            "The submission has strong thermal-radiation signals, though a human editor should still check emphasis.",
            "proceed_to_editor_review",
            ["Confirm that radiation is the main contribution, not a supporting model term."],
        )

    if features.in_scope_score >= 5 and features.borderline_score >= 4:
        return (
            "borderline",
            "medium",
            "The submission mixes thermal-radiation signals with broader thermal-management or systems framing.",
            "request_editor_review",
            ["Radiation may be a subsystem rather than the paper's core novelty."],
        )

    if features.borderline_score >= 5 and features.has_radiation_signal:
        return (
            "borderline",
            "low",
            "Radiation is present, but the stronger context is adjacent heat-transfer or system engineering.",
            "request_editor_review",
            ["Mixed-scope case; needs human review."],
        )

    if features.has_thermal_signal and features.has_radiation_signal and features.in_scope_score >= 3:
        return (
            "borderline",
            "low",
            "The submission contains weak thermal-radiation evidence but not enough to classify confidently as in scope.",
            "request_editor_review",
            ["Weak signal strength."],
        )

    if features.out_of_scope_score >= 4:
        return (
            "out_of_scope",
            "medium",
            "Available signals point away from a thermal-radiation contribution.",
            "likely_desk_triage_review",
            [],
        )

    return (
        "out_of_scope",
        "low",
        "The submission does not provide enough thermal-radiation evidence to support an in-scope classification.",
        "request_editor_review",
        ["Absence of strong scope terms is not proof of being out of scope."],
    )


def offline_policy_engine(title: str, abstract: str, keywords: str) -> TriageOutput:
    """Auditable non-RAG policy engine used for demo and fallback."""
    features = extract_features(title, abstract, keywords)
    label, confidence, reason, action, flags = _determine_policy_label(features)

    evidence: List[EvidenceItem] = []
    if label == "in_scope":
        evidence.extend(_top_examples(features.in_scope_hits, 3))
        evidence.append(_rubric_evidence("in_scope"))
    elif label == "borderline":
        evidence.extend(_top_examples(features.in_scope_hits, 2))
        evidence.extend(_top_examples(features.borderline_hits, 2))
        evidence.append(_rubric_evidence("borderline"))
    elif label == "out_of_scope":
        evidence.extend(_top_examples(features.out_of_scope_hits, 3))
        if features.in_scope_hits:
            evidence.extend(_top_examples(features.in_scope_hits, 1))
        evidence.append(_rubric_evidence("out_of_scope"))
    else:
        evidence.extend(_top_examples(features.vague_hits, 2))
        evidence.append(
            EvidenceItem(
                source="system_feature",
                quote_or_signal=(
                    f"abstract_word_count={features.abstract_word_count}; "
                    f"in_scope_score={features.in_scope_score}; "
                    f"vague_score={features.vague_score}"
                ),
                interpretation="The policy engine found inadequate concrete signal for a scope call.",
            )
        )
        evidence.append(_rubric_evidence("insufficient_information"))

    if not evidence:
        evidence.append(
            EvidenceItem(
                source="system_feature",
                quote_or_signal=features_as_text(features),
                interpretation="No direct term hits; decision is low-confidence.",
            )
        )

    memo = (
        f"First-pass scope triage: {label}. {reason} "
        "This memo is advisory and should be reviewed by a handling editor before any action."
    )

    return TriageOutput(
        decision_label=label,  # type: ignore[arg-type]
        confidence=confidence,  # type: ignore[arg-type]
        reasoning_summary=reason,
        supporting_evidence=evidence[:5],
        uncertainty_flags=flags,
        editor_memo=memo,
        recommended_human_action=action,  # type: ignore[arg-type]
        should_not_automate=True,
    )


def llm_triage(title: str, abstract: str, keywords: str, model: str | None = None) -> TriageOutput:
    """Structured-output LLM triage; falls back to the policy engine if unavailable."""
    features = extract_features(title, abstract, keywords)
    user_prompt = build_user_prompt(title, abstract, keywords, features)
    try:
        output = call_openai_structured(SYSTEM_PROMPT, user_prompt, model=model)
        # Enforce governance invariant even if the model omits or changes it.
        output.should_not_automate = True
        return output
    except LLMUnavailable as exc:
        fallback = offline_policy_engine(title, abstract, keywords)
        fallback.uncertainty_flags.append(f"LLM unavailable; offline policy fallback used. Reason: {exc}")
        return fallback


def triage_submission(
    title: str,
    abstract: str,
    keywords: str,
    mode: str = "offline_policy",
    model: str | None = None,
) -> TriageOutput:
    """Dispatch triage mode."""
    if mode == "baseline":
        return keyword_baseline(title, abstract, keywords)
    if mode == "llm":
        return llm_triage(title, abstract, keywords, model=model)
    if mode == "offline_policy":
        return offline_policy_engine(title, abstract, keywords)
    raise ValueError(f"Unknown mode: {mode}")
