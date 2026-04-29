"""Deterministic feature extraction for ScopeLens.

These features serve two purposes:
1. They give the LLM an auditable summary of the input.
2. They support an offline fallback and a non-GenAI baseline comparison.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Dict, Iterable, List, Tuple

from .scope_rubric import (
    BORDERLINE_TERMS,
    IN_SCOPE_TERMS,
    OUT_OF_SCOPE_TERMS,
    VAGUE_TERMS,
)


@dataclass
class TermHit:
    term: str
    weight: int
    count: int
    source: str
    example: str


@dataclass
class FeatureSummary:
    in_scope_score: int
    borderline_score: int
    out_of_scope_score: int
    vague_score: int
    abstract_word_count: int
    title_word_count: int
    has_thermal_signal: bool
    has_radiation_signal: bool
    in_scope_hits: List[TermHit]
    borderline_hits: List[TermHit]
    out_of_scope_hits: List[TermHit]
    vague_hits: List[TermHit]

    def to_dict(self) -> Dict:
        data = asdict(self)
        return data


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _split_sentences(text: str) -> List[str]:
    text = _normalize(text)
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def _count_term(text: str, term: str) -> int:
    # Hyphen and space variants are intentionally not over-normalized: the rubric
    # already includes common variants for high-value phrases.
    pattern = re.compile(r"(?<![A-Za-z0-9])" + re.escape(term.lower()) + r"(?![A-Za-z0-9])")
    return len(pattern.findall(text.lower()))


def _example_sentence(text: str, term: str) -> str:
    for sent in _split_sentences(text):
        if term.lower() in sent.lower():
            return sent[:240]
    text = _normalize(text)
    idx = text.lower().find(term.lower())
    if idx == -1:
        return ""
    start = max(idx - 70, 0)
    end = min(idx + len(term) + 120, len(text))
    return text[start:end].strip()


def _find_hits(source_name: str, text: str, terms: Dict[str, int]) -> List[TermHit]:
    hits: List[TermHit] = []
    for term, weight in terms.items():
        count = _count_term(text, term)
        if count > 0:
            hits.append(
                TermHit(
                    term=term,
                    weight=weight,
                    count=count,
                    source=source_name,
                    example=_example_sentence(text, term),
                )
            )
    return hits


def _score_hits(hits: Iterable[TermHit]) -> int:
    return sum(hit.weight * hit.count for hit in hits)


def extract_features(title: str, abstract: str, keywords: str) -> FeatureSummary:
    title = _normalize(title)
    abstract = _normalize(abstract)
    keywords = _normalize(keywords)

    # Title and keyword signals receive a modest boost because they usually indicate
    # the stated primary contribution more strongly than buried abstract terms.
    title_blob = title
    abstract_blob = abstract
    keyword_blob = keywords

    def collect(terms: Dict[str, int]) -> List[TermHit]:
        title_hits = _find_hits("title", title_blob, {k: v + 1 for k, v in terms.items()})
        abstract_hits = _find_hits("abstract", abstract_blob, terms)
        keyword_hits = _find_hits("keywords", keyword_blob, {k: v + 1 for k, v in terms.items()})
        return title_hits + abstract_hits + keyword_hits

    in_hits = collect(IN_SCOPE_TERMS)
    borderline_hits = collect(BORDERLINE_TERMS)
    out_hits = collect(OUT_OF_SCOPE_TERMS)
    vague_hits = collect(VAGUE_TERMS)

    all_text = " ".join([title, abstract, keywords]).lower()
    abstract_word_count = len(re.findall(r"\b\w+\b", abstract))
    title_word_count = len(re.findall(r"\b\w+\b", title))

    return FeatureSummary(
        in_scope_score=_score_hits(in_hits),
        borderline_score=_score_hits(borderline_hits),
        out_of_scope_score=_score_hits(out_hits),
        vague_score=_score_hits(vague_hits),
        abstract_word_count=abstract_word_count,
        title_word_count=title_word_count,
        has_thermal_signal=bool(re.search(r"\b(thermal|heat|temperature|infrared|emissiv|blackbody)\b", all_text)),
        has_radiation_signal=bool(re.search(r"\b(radiation|radiative|emission|emitter|absorber|emissivity)\b", all_text)),
        in_scope_hits=in_hits,
        borderline_hits=borderline_hits,
        out_of_scope_hits=out_hits,
        vague_hits=vague_hits,
    )


def features_as_text(features: FeatureSummary) -> str:
    def format_hits(hits: List[TermHit]) -> str:
        if not hits:
            return "none"
        return "; ".join(
            f"{h.term} [{h.source}, weight={h.weight}, count={h.count}]" for h in hits[:12]
        )

    return (
        f"Scores: in_scope={features.in_scope_score}, "
        f"borderline={features.borderline_score}, "
        f"out_of_scope={features.out_of_scope_score}, vague={features.vague_score}.\n"
        f"Word counts: title={features.title_word_count}, abstract={features.abstract_word_count}.\n"
        f"Signals: thermal={features.has_thermal_signal}, radiation={features.has_radiation_signal}.\n"
        f"In-scope term hits: {format_hits(features.in_scope_hits)}\n"
        f"Borderline term hits: {format_hits(features.borderline_hits)}\n"
        f"Out-of-scope trap hits: {format_hits(features.out_of_scope_hits)}\n"
        f"Vague-language hits: {format_hits(features.vague_hits)}"
    )
