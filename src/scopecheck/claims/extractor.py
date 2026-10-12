"""Deterministic, source-grounded baseline for atomic scientific claims.

The rules intentionally prefer preserving an ambiguous complete clause over
splitting it into fragments that could change its meaning.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable

from scopecheck.contracts import (
    AtomicClaim,
    ClaimType,
    ExtractionMethod,
    ScientificScope,
    ScopeValue,
    SourceSpan,
)

_SPLIT_CLAUSE = re.compile(
    r"\s*(?:;\s*|,\s*(?:but|whereas|while|although|however)\s+|"
    r"\b(?:but|whereas|although)\s+|\bwhile\s+(?=[A-Z])|"
    r"\band\s+(?=[A-Z][\w-]*\s+(?:increased?|decreased?|improved?|reduced?|"
    r"outperformed|underperformed|was|were|is|are|showed|demonstrated|"
    r"correlated|associated|caused|predicts?)))\s*",
    re.IGNORECASE,
)
_NUMBER = re.compile(
    r"(?<!\w)(?:[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?%?"
    r"(?:\s*(?:±|\+/-)\s*\d+(?:\.\d+)?%?)?"
    r"(?:\s*(?:to|–|-)\s*[-+]?\d+(?:\.\d+)?%?)?"
    r"(?:\s*(?:ms|milliseconds?|seconds?|minutes?|hours?|days?|weeks?|months?|"
    r"years?|kg|mg|μg|ug|mm|cm|mL|ml|°C|K|fold|x|participants?|patients?)\b)?)",
    re.IGNORECASE,
)
_DATASET = re.compile(r"\b(?:dataset|corpus|benchmark)\s+([A-Z0-9][\w.-]*(?:\s+[A-Z0-9][\w.-]*){0,3})", re.I)
_CONDITIONAL = re.compile(
    r"\b(?:only\s+(?:if|when|under)|if|when|under|in\s+the\s+presence\s+of|"
    r"in\s+patients?\s+with|among|except\s+(?:for|when)|unless|across\s+(?:all|every))\b[^,;:.]*",
    re.I,
)
_CERTAINTY_PATTERNS = (
    ("suggestive", re.compile(r"\b(?:suggests?|indicates?)\b", re.I)),
    ("possible", re.compile(r"\b(?:may|might|could|possibly|potentially)\b", re.I)),
    ("associated", re.compile(r"\b(?:associated\s+with|correlated\s+with)\b", re.I)),
    ("statistically_significant", re.compile(r"\bstatistically\s+significant(?:ly)?\b", re.I)),
    ("certain", re.compile(r"\b(?:demonstrates?|shows?|proves?)\b", re.I)),
)
_NEGATION = re.compile(r"\b(?:not|never|no|neither|fails?\s+to|did\s+not|does\s+not|without)\b", re.I)
_CAUSAL = re.compile(r"\b(?:cause[sd]?|causal(?:ly)?|leads?\s+to|resulted?\s+in|due\s+to|drives?)\b", re.I)
_CORRELATIONAL = re.compile(r"\b(?:correlat(?:e|es|ed|ion)|associated\s+with|linked\s+to|relationship\s+between)\b", re.I)
_COMPARATIVE = re.compile(r"\b(?:compared\s+with|compared\s+to|than|versus|vs\.?|outperform(?:s|ed)?|underperform(?:s|ed)?|better|worse|higher|lower)\b", re.I)


def _known(value: str | list[str] | None) -> ScopeValue:
    return ScopeValue(status="known", value=value) if value else ScopeValue(status="unknown")


def _sentences(text: str) -> Iterable[tuple[int, int, str]]:
    """Yield trimmed sentences and their half-open offsets in the input."""
    start = 0
    for match in re.finditer(r"(?<=[.!?])\s+|\n+", text):
        end = match.start()
        left = start
        while left < end and text[left].isspace():
            left += 1
        right = end
        while right > left and text[right - 1].isspace():
            right -= 1
        if right > left:
            yield left, right, text[left:right]
        start = match.end()
    left = start
    while left < len(text) and text[left].isspace():
        left += 1
    right = len(text)
    while right > left and text[right - 1].isspace():
        right -= 1
    if right > left:
        yield left, right, text[left:right]


def _clauses(sentence: str) -> list[tuple[int, int, str]]:
    """Split clear contrasting/coordinated assertions, retaining exact spans."""
    pieces: list[tuple[int, int, str]] = []
    start = 0
    for match in _SPLIT_CLAUSE.finditer(sentence):
        left, right = start, match.start()
        while left < right and sentence[left].isspace():
            left += 1
        while right > left and sentence[right - 1] in " ,;":
            right -= 1
        if right > left:
            pieces.append((left, right, sentence[left:right]))
        start = match.end()
    left = start
    while left < len(sentence) and sentence[left].isspace():
        left += 1
    right = len(sentence)
    while right > left and sentence[right - 1] in " ,;":
        right -= 1
    if right > left:
        pieces.append((left, right, sentence[left:right]))
    return pieces or [(0, len(sentence), sentence)]


def _has_assertion(text: str) -> bool:
    return bool(re.search(
        r"\b(?:is|are|was|were|has|have|had|shows?|showed|demonstrates?|"
        r"demonstrated|increases?|increased|decreases?|decreased|improves?|performs?|"
        r"improved|reduces?|reduced|outperformed|underperformed|performed|"
        r"produces?|produced|works?|worked|affects?|affected|helps?|helped|"
        r"predicts?|"
        r"predicted|causes?|caused|correlates?|correlated|associated|"
        r"suggests?|suggested|found|finds|remains?|differs?|did\s+not|does\s+not)\b",
        text, re.I,
    ))


def _scope(text: str) -> ScientificScope:
    low = text.lower()
    dataset_match = _DATASET.search(text)
    numbers = list(dict.fromkeys(m.group(0).strip() for m in _NUMBER.finditer(text) if m.group(0).strip()))
    conditions = list(dict.fromkeys(m.group(0).strip() for m in _CONDITIONAL.finditer(text)))
    certainty_values = [name for name, pattern in _CERTAINTY_PATTERNS if pattern.search(text)]
    certainty = "; ".join(certainty_values) if certainty_values else None
    direction = None
    if _NEGATION.search(text):
        direction = "negative"
    elif re.search(r"\b(?:increase|increased|increases|improve|improved|higher|greater|better|positive|benefit)\w*\b", low):
        direction = "positive"
    elif re.search(r"\b(?:decrease|decreased|decreases|reduce|reduced|lower|worse|negative|harm)\w*\b", low):
        direction = "negative"
    elif _CORRELATIONAL.search(text):
        direction = "association"

    metric = next((name for name, pattern in (
        ("accuracy", r"\baccuracy\b"), ("precision", r"\bprecision\b"),
        ("recall", r"\brecall\b"), ("F1 score", r"\bF1(?:-score| score)?\b"),
        ("AUC", r"\bAUC\b"), ("mortality", r"\bmortal(?:ity|ity rate)\b"),
        ("error rate", r"\berror rate\b"), ("runtime", r"\b(?:runtime|run time|latency)\b"),
    ) if re.search(pattern, text, re.I)), None)
    outcome = metric or next((m.group(0).strip() for m in re.finditer(
        r"\b(?:performance|survival|risk|yield|expression|response|symptoms?)\b", text, re.I)), None)
    method = next((m.group(0).strip() for m in re.finditer(
        r"\b(?:model|method|algorithm|approach|treatment|therapy|intervention|"
        r"regression|randomized trial|randomised trial|cohort study|ablation)\s+[A-Z][\w.-]*",
        text, re.I)), None)
    pop = next((m.group(0).strip() for m in re.finditer(
        r"\b(?:patients?|participants?|subjects?|adults?|children|mice|rats|cells?)\b"
        r"(?:\s+with\s+[\w -]+)?", text, re.I)), None)
    time = next((m.group(0).strip() for m in re.finditer(
        r"\b(?:in|over|during|after|for)\s+(?:the\s+)?(?:\d+\s+)?"
        r"(?:days?|weeks?|months?|years?|follow[- ]up|baseline|202\d|19\d\d)\b", text, re.I)), None)
    domain = next((m.group(0).strip() for m in re.finditer(
        r"\b(?:in|for)\s+(?:the\s+)?(?:medical|clinical|biomedical|financial|"
        r"legal|agricultural|ecological|computer vision|natural language processing)\s+\w+", text, re.I)), None)
    return ScientificScope(
        population=_known(pop),
        dataset=_known(dataset_match.group(0).strip(" .,:;") if dataset_match else None),
        methodology=_known(method),
        intervention=_known(next((m.group(0).strip() for m in re.finditer(r"\b(?:treatment|therapy|intervention)\s+[A-Z][\w.-]*", text, re.I)), None)),
        outcome=_known(outcome),
        metric=_known(metric),
        time_period=_known(time),
        domain=_known(domain),
        conditions=_known(conditions),
        certainty=_known(certainty),
        direction=_known(direction),
        numerical_values=_known(numbers),
    )


def _claim_type(text: str) -> ClaimType:
    if _CAUSAL.search(text):
        return ClaimType.CAUSAL
    if _CORRELATIONAL.search(text):
        return ClaimType.EMPIRICAL
    if _COMPARATIVE.search(text):
        return ClaimType.COMPARATIVE
    if _NUMBER.search(text):
        return ClaimType.QUANTITATIVE
    if re.search(r"\b(?:all|every|always|never|across all|none)\b", text, re.I):
        return ClaimType.GENERALIZATION
    if _has_assertion(text):
        return ClaimType.EMPIRICAL
    return ClaimType.UNKNOWN


def extract_claims(text: str, document_id: str) -> list[AtomicClaim]:
    """Extract checkable assertion clauses without requiring network access.

    ``source_span`` offsets are zero-based, half-open Python character offsets
    into ``text``. IDs are stable for a given document and exact source span.
    """
    if not text.strip():
        return []
    if not document_id.strip():
        raise ValueError("document_id must not be empty")
    claims: list[AtomicClaim] = []
    for sent_start, _, sentence in _sentences(text):
        for local_start, local_end, clause in _clauses(sentence):
            if not _has_assertion(clause):
                continue
            # Exclude non-assertional lead-ins such as "However," while keeping
            # words like only, may, not, and statistically significant intact.
            absolute_start = sent_start + local_start
            absolute_end = sent_start + local_end
            source = text[absolute_start:absolute_end]
            if not source.strip():
                continue
            inherited = None
            if local_start > 0:
                subject = re.match(
                    r"((?:Model|Method|System|Algorithm|Treatment|Group)\s+[A-Z0-9][\w.-]*)\b",
                    sentence,
                )
                if subject and re.match(
                    r"(?:performs?|was|were|is|are|has|have|showed|demonstrated|"
                    r"improved?|increased?|decreased?|reduced?|outperformed|underperformed)\b",
                    clause,
                    re.I,
                ):
                    inherited = subject.group(1)
            claim_text = f"{inherited} {source.strip()}" if inherited else source.strip()
            claim_id = hashlib.sha256(
                f"{document_id}\0{absolute_start}\0{absolute_end}\0{source}".encode("utf-8")
            ).hexdigest()[:20]
            claims.append(AtomicClaim(
                id=claim_id,
                text=claim_text,
                document_id=document_id,
                claim_type=_claim_type(claim_text),
                scope=_scope(claim_text),
                source_span=SourceSpan(
                    document_id=document_id,
                    start_offset=absolute_start,
                    end_offset=absolute_end,
                    exact_text=source,
                ),
                extraction_method=ExtractionMethod.RULE_BASED,
            ))
    return claims
