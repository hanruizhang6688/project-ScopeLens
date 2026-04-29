"""Data schemas for ScopeLens.

The schema is intentionally narrow. The app is an advisory triage memo generator,
not an automated accept/reject system.
"""
from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field

DecisionLabel = Literal[
    "in_scope",
    "borderline",
    "out_of_scope",
    "insufficient_information",
]
ConfidenceLabel = Literal["high", "medium", "low"]
HumanAction = Literal[
    "proceed_to_editor_review",
    "request_editor_review",
    "likely_desk_triage_review",
    "request_more_information",
]
EvidenceSource = Literal["title", "abstract", "keywords", "scope_rubric", "system_feature"]

LABELS: List[str] = [
    "in_scope",
    "borderline",
    "out_of_scope",
    "insufficient_information",
]


class EvidenceItem(BaseModel):
    """A short piece of evidence shown to the editor."""

    source: EvidenceSource
    quote_or_signal: str = Field(
        ...,
        description="A short quoted phrase from the submission, rubric criterion, or extracted signal.",
    )
    interpretation: str = Field(
        ...,
        description="Why this evidence matters for the scope decision.",
    )


class TriageOutput(BaseModel):
    """Structured output returned by the LLM or deterministic fallback."""

    decision_label: DecisionLabel = Field(
        ...,
        description="First-pass scope decision. This is not an editorial decision.",
    )
    confidence: ConfidenceLabel = Field(
        ...,
        description="Confidence in the first-pass label, calibrated to visible input evidence only.",
    )
    reasoning_summary: str = Field(
        ...,
        description="Brief rationale. Do not include hidden chain-of-thought.",
    )
    supporting_evidence: List[EvidenceItem] = Field(
        default_factory=list,
        description="Evidence visible to the editor. Evidence must be grounded in the submission or rubric.",
    )
    uncertainty_flags: List[str] = Field(
        default_factory=list,
        description="Specific reasons an editor should treat the label cautiously.",
    )
    editor_memo: str = Field(
        ...,
        description="Concise memo written for a handling editor.",
    )
    recommended_human_action: HumanAction = Field(
        ...,
        description="Recommended next human action. Never an automated final decision.",
    )
    should_not_automate: bool = Field(
        True,
        description="Always true. The tool is advisory only.",
    )
