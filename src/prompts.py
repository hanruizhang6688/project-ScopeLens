"""Prompt construction for the structured LLM mode."""
from __future__ import annotations

import json

from .feature_extractor import FeatureSummary, features_as_text
from .scope_rubric import few_shots_as_text, rubric_as_text
from .schema import TriageOutput

SYSTEM_PROMPT = """
You are ScopeLens, an advisory editorial triage assistant for a thermal-radiation journal.
Your job is to generate a first-pass scope memo from only the visible title, abstract, keywords,
static scope rubric, few-shot examples, and deterministic feature summary supplied by the app.

Decision labels:
- in_scope
- borderline
- out_of_scope
- insufficient_information

Operational rules:
1. Do not make an accept/reject recommendation. The output is advisory only.
2. Do not invent journal policy, citations, reviewer names, impact claims, or missing methods.
3. Prefer insufficient_information over confident guessing when the abstract is too vague.
4. Treat biomedical, nuclear, wireless, remote-sensing, and generic forecasting uses of "radiation" as vocabulary traps unless the submission clearly concerns thermal radiation.
5. For borderline cases, explain what evidence a human editor should inspect.
6. Give concise reasoning only. Do not reveal hidden chain-of-thought.
""".strip()


def build_user_prompt(title: str, abstract: str, keywords: str, features: FeatureSummary) -> str:
    schema = TriageOutput.model_json_schema()
    payload = {
        "submission": {
            "title": title,
            "abstract": abstract,
            "keywords": keywords,
        },
        "scope_rubric": rubric_as_text(),
        "few_shot_examples": few_shots_as_text(),
        "feature_summary": features_as_text(features),
        "output_schema": schema,
    }
    return (
        "Classify the submission and write an editorial triage memo. "
        "Use the schema exactly. Ground evidence in the provided submission, rubric, or feature summary.\n\n"
        + json.dumps(payload, indent=2, ensure_ascii=False)
    )
