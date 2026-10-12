"""Optional Gemini adapter for structured claim extraction.

The core extractor remains local-only. This module imports the Gemini SDK
lazily and raises a clear error when credentials or the optional SDK are absent.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from scopecheck.contracts import AtomicClaim, ExtractionMethod, SourceSpan
from scopecheck.claims.extractor import _claim_type, _scope


class _ModelClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1)
    source_text: str = Field(min_length=1)


class _ModelResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claims: list[_ModelClaim]


_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "claims": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "text": {"type": "STRING"},
                    "source_text": {"type": "STRING"},
                },
                "required": ["text", "source_text"],
                "propertyOrdering": ["text", "source_text"],
            },
        },
    },
    "required": ["claims"],
    "propertyOrdering": ["claims"],
}


def _validated_claims(payload: str, text: str, document_id: str) -> list[AtomicClaim]:
    """Parse model JSON and rebuild trusted source spans from the input text."""
    try:
        response = _ModelResponse.model_validate_json(payload)
    except (ValidationError, ValueError) as exc:
        raise ValueError("Gemini returned malformed claim JSON") from exc
    result: list[AtomicClaim] = []
    used: set[tuple[int, int]] = set()
    for item in response.claims:
        start = text.find(item.source_text)
        while start >= 0 and (start, start + len(item.source_text)) in used:
            start = text.find(item.source_text, start + 1)
        if start < 0:
            raise ValueError("Gemini source_text does not occur verbatim in input")
        end = start + len(item.source_text)
        used.add((start, end))
        claim_id = hashlib.sha256(
            f"{document_id}\0{start}\0{end}\0{item.text}".encode("utf-8")
        ).hexdigest()[:20]
        result.append(AtomicClaim(
            id=claim_id,
            text=item.text,
            document_id=document_id,
            claim_type=_claim_type(item.text),
            scope=_scope(item.source_text),
            source_span=SourceSpan(
                document_id=document_id,
                start_offset=start,
                end_offset=end,
                exact_text=item.source_text,
            ),
            extraction_method=ExtractionMethod.MODEL_ASSISTED,
        ))
    return result


def extract_claims_gemini(
    text: str,
    document_id: str,
    *,
    model: str = "gemini-2.5-flash",
) -> list[AtomicClaim]:
    """Use Gemini structured output and validate each claim against contracts.

    Requires ``GOOGLE_API_KEY`` and the optional ``google-genai`` package.
    Raises ``RuntimeError`` when unavailable and ``ValueError`` on invalid output.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("Gemini extraction requires the GOOGLE_API_KEY environment variable")
    try:
        from google import genai  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("Gemini extraction requires the optional google-genai package") from exc
    prompt = (
        "Extract independently checkable scientific claims from the supplied text. "
        "Split compound claims when safe. Keep modality, polarity, comparison, "
        "conditions, quantities, and qualifications. Do not invent facts. For each "
        "claim, source_text must be an exact contiguous substring copied verbatim "
        "from the input. Return only the requested JSON structure.\n\n"
        f"SOURCE TEXT:\n{text}"
    )
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config={"response_mime_type": "application/json", "response_schema": _RESPONSE_SCHEMA},
        )
    except Exception as exc:
        raise RuntimeError(f"Gemini extraction request failed: {exc}") from exc
    output = getattr(response, "text", None)
    if not isinstance(output, str) or not output.strip():
        raise ValueError("Gemini returned an empty structured response")
    return _validated_claims(output, text, document_id)
