"""Deterministic factual cues used by the local alignment comparator."""

from __future__ import annotations

import re
from dataclasses import dataclass

_STOP = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being", "of", "to", "in", "on", "for", "by", "with", "from", "as", "at", "and", "or", "but", "that", "this", "these", "those", "it", "its", "we", "our", "they", "their", "study", "result", "results", "evidence", "show", "shows", "found", "find", "reported", "significant", "significantly", "effect", "effects", "associated", "using", "used", "based", "model", "method", "approach",
}
_NEGATION = re.compile(r"\b(no|not|never|neither|without|fail(?:ed|s|ure)?|lack(?:s|ed)?)\b", re.I)
_POSITIVE = re.compile(r"\b(improv\w*|increas\w*|higher|greater|better|benefit\w*|enhanc\w*|reduc\w*|decreas\w*|lower|worse|harm\w*|declin\w*)\b", re.I)
_NUMERIC = re.compile(r"(?P<number>\d+(?:\.\d+)?)\s*(?P<unit>%|percent|percentage points?|ms|milliseconds?|seconds?|minutes?|hours?|days?|years?|fold|x)?", re.I)


@dataclass(frozen=True)
class FactualCues:
    relevant: bool
    overlap: set[str]
    direction: str | None
    numbers: tuple[tuple[float, str], ...]
    conditional: bool
    universal: bool
    causal: bool
    correlational: bool
    uncertainty: bool
    negated: bool
    explanation: str


def content_terms(text: str) -> set[str]:
    tokens = re.findall(r"[a-z][a-z0-9-]{2,}", text.lower())
    return {t for t in tokens if t not in _STOP}


def _direction(text: str) -> tuple[str | None, bool]:
    matches = list(_POSITIVE.finditer(text))
    if not matches:
        if re.search(r"\b(no effect|unchanged|equivalent|same)\b", text, re.I):
            return "no_change", False
        return None, False
    m = matches[0]
    prefix = text[max(0, m.start() - 30):m.start()]
    negated = bool(re.search(r"\b(?:not|no|never|fail(?:ed|s)?)\b(?:\W+\w+){0,2}\W*$", prefix, re.I))
    word = m.group().lower()
    if word.startswith(("improv", "increas", "higher", "greater", "better", "benefit", "enhanc")):
        return ("negative" if negated else "positive"), negated
    return ("positive" if negated else "negative"), negated


def _numbers(text: str) -> tuple[tuple[float, str], ...]:
    out: list[tuple[float, str]] = []
    for match in _NUMERIC.finditer(text):
        unit = (match.group("unit") or "").lower().replace(" ", "")
        out.append((float(match.group("number")), unit))
    return tuple(out)


def analyze_facts(claim_text: str, evidence_text: str) -> tuple[FactualCues, FactualCues]:
    claim_terms, evidence_terms = content_terms(claim_text), content_terms(evidence_text)
    overlap = claim_terms & evidence_terms
    # Require lexical connection on subject or outcome; generic result language
    # is filtered above, so one shared substantive term is a conservative floor.
    relevant = bool(overlap)
    claim_direction, claim_negated = _direction(claim_text)
    evidence_direction, evidence_negated = _direction(evidence_text)

    def cues(text: str, direction: str | None, negated: bool, shared: set[str]) -> FactualCues:
        conditional = bool(re.search(r"\b(if|when|among|only|provided that|under|in patients with|for patients with)\b", text, re.I))
        universal = bool(re.search(r"\b(all|every|always|never|everyone|universally)\b", text, re.I))
        causal = bool(re.search(r"\b(cause[sd]?|causing|led to|resulted in|due to|effect of|impact of)\b", text, re.I))
        correlational = bool(re.search(r"\b(associated with|correlated with|linked to|relationship between)\b", text, re.I))
        uncertainty = bool(re.search(r"\b(may|might|could|possibly|possibly|suggests?|appears? to|likely|probably|trend toward)\b", text, re.I))
        return FactualCues(
            relevant=relevant, overlap=shared, direction=direction,
            numbers=_numbers(text), conditional=conditional, universal=universal,
            causal=causal, correlational=correlational, uncertainty=uncertainty,
            negated=negated,
            explanation=(f"Shared substantive terms: {', '.join(sorted(shared)) or 'none'}; "
                         f"direction={direction or 'unknown'}, negated={negated}, "
                         f"conditional={conditional}, universal={universal}, "
                         f"causal={causal}, correlational={correlational}, "
                         f"uncertain={uncertainty}."),
        )

    return cues(claim_text, claim_direction, claim_negated, overlap), cues(evidence_text, evidence_direction, evidence_negated, overlap)


def numerical_relation(claim: FactualCues, evidence: FactualCues) -> str:
    """Return unknown/agreement/disagreement for comparable extracted numbers."""
    if not claim.numbers or not evidence.numbers:
        return "unknown"
    claim_values, evidence_values = claim.numbers, evidence.numbers
    matching_units = [(a, b) for a in claim_values for b in evidence_values if a[1] == b[1]]
    if not matching_units:
        return "unknown"
    return "agreement" if any(abs(a[0] - b[0]) <= max(1e-9, abs(a[0]) * 0.01) for a, b in matching_units) else "disagreement"
