"""Optional OpenAI structured-output client.

The app remains runnable without an API key by falling back to the policy engine.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from pydantic import ValidationError

from .schema import TriageOutput

DEFAULT_MODEL = os.getenv("SCOPELENS_MODEL", "gpt-4o-mini")


class LLMUnavailable(RuntimeError):
    """Raised when the structured LLM call cannot be completed."""


def _messages(system_prompt: str, user_prompt: str) -> List[Dict[str, str]]:
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _parse_json_text(text: str) -> TriageOutput:
    try:
        return TriageOutput.model_validate_json(text)
    except ValidationError:
        data = json.loads(text)
        return TriageOutput.model_validate(data)


def call_openai_structured(system_prompt: str, user_prompt: str, model: str | None = None) -> TriageOutput:
    """Call OpenAI and parse/validate the result as TriageOutput.

    The function first tries the modern Responses API Pydantic parser. If the
    installed SDK lacks that method, it falls back to Chat Completions with a
    JSON-schema response format and then to JSON-object mode plus local
    Pydantic validation.
    """
    if not os.getenv("OPENAI_API_KEY"):
        raise LLMUnavailable("OPENAI_API_KEY is not set.")

    model = model or DEFAULT_MODEL
    messages = _messages(system_prompt, user_prompt)

    try:
        from openai import OpenAI
    except Exception as exc:  # pragma: no cover - depends on environment
        raise LLMUnavailable(f"OpenAI package is unavailable: {exc}") from exc

    client = OpenAI()

    # Preferred path for recent SDKs.
    try:  # pragma: no cover - external API call
        response = client.responses.parse(
            model=model,
            input=messages,
            text_format=TriageOutput,
            temperature=0,
        )
        parsed = getattr(response, "output_parsed", None)
        if parsed is not None:
            if isinstance(parsed, TriageOutput):
                return parsed
            return TriageOutput.model_validate(parsed)
    except Exception:
        pass

    # JSON schema path for Chat Completions.
    schema: Dict[str, Any] = TriageOutput.model_json_schema()
    try:  # pragma: no cover - external API call
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "ScopeLensTriageOutput",
                    "schema": schema,
                    "strict": True,
                },
            },
        )
        text = response.choices[0].message.content
        if text:
            return _parse_json_text(text)
    except Exception:
        pass

    # Last-resort JSON-object mode; still validated locally.
    try:  # pragma: no cover - external API call
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
        )
        text = response.choices[0].message.content
        if text:
            return _parse_json_text(text)
    except Exception as exc:
        raise LLMUnavailable(f"OpenAI call failed: {exc}") from exc

    raise LLMUnavailable("OpenAI call returned no parseable content.")
