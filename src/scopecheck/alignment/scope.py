"""Evidence scope extraction and dimension-wise comparison helpers.

The adapter prefers producer-supplied structured metadata, then applies small,
auditable lexical rules. It deliberately leaves unsupported fields unknown.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from scopecheck.contracts import (
    AtomicClaim,
    DimensionComparison,
    DimensionStatus,
    RetrievalHit,
    ScopeDimension,
    ScopeValue,
    ScopeValueStatus,
    ScientificScope,
)

_PATTERNS: dict[str, tuple[str, ...]] = {
    "population": (r"\b(?:in|among|for)\s+((?:adult|adolescent|child|pediatric|older|female|male|human|patient|healthy|clinical)[\w -]{0,35})",),
    "dataset": (r"\b(?:dataset|corpus|benchmark|cohort)\s+(?:of\s+)?([A-Z][\w-]*(?:\s+[A-Z][\w-]*){0,2})", r"\b(?:using|on)\s+(?:the\s+)?(ImageNet|CIFAR-?\d+|MNIST|MIMIC-?IV?|PubMed|Wikipedia)\b"),
    "methodology": (r"\b(randomi[sz]ed controlled trial|observational study|cross-sectional study|longitudinal study|meta-analysis|systematic review|in vitro|in vivo|ablation study|simulation)\b",),
    "intervention": (r"\b(?:treatment|intervention|therapy)\s+(?:with|using|of)\s+([\w-]+(?:\s+[\w-]+){0,2})",),
    "outcome": (r"\b(?:reduc\w*|increas\w*|improv\w*|decreas\w*|predict\w*|classif\w*|associated with|correlated with|caused?)\s+([a-z][\w-]*)",),
    "metric": (r"\b(accuracy|precision|recall|F1(?: score)?|AUC|AUROC|mortality|survival|risk|error rate|latency|sensitivity|specificity)\b",),
    "time_period": (r"\b((?:19|20)\d{2}(?:\s*[-–]\s*(?:19|20)?\d{2})?)\b",),
    "domain": (r"\b(?:in|for|within)\s+(medicine|healthcare|oncology|radiology|education|finance|biology|computer vision|natural language processing|NLP)\b",),
    "certainty": (r"\b(possibly|possibly|may|might|could|likely|probably|suggests?|indicates?|demonstrates?|proves?|certainly|always|never)\b",),
    "direction": (r"\b(improv\w*|increas\w*|higher|greater|better|reduc\w*|decreas\w*|lower|worse|no effect|unchanged|equivalent)\b",),
    "numerical_values": (r"\b\d+(?:\.\d+)?\s*(?:%|percent|percentage points?|ms|milliseconds?|seconds?|minutes?|hours?|days?|years?|fold|x)?\b",),
}

_DIMENSION_BINDINGS: tuple[tuple[str, ScopeDimension], ...] = (
    ("population", ScopeDimension.POPULATION_COMPATIBILITY),
    ("dataset", ScopeDimension.DATASET_COMPATIBILITY),
    ("methodology", ScopeDimension.METHODOLOGICAL_COMPATIBILITY),
    ("intervention", ScopeDimension.SEMANTIC_AGREEMENT),
    ("outcome", ScopeDimension.OUTCOME_METRIC_COMPATIBILITY),
    ("metric", ScopeDimension.OUTCOME_METRIC_COMPATIBILITY),
    ("time_period", ScopeDimension.EXPERIMENTAL_CONDITION_COMPATIBILITY),
    ("domain", ScopeDimension.EXPERIMENTAL_CONDITION_COMPATIBILITY),
    ("conditions", ScopeDimension.EXPERIMENTAL_CONDITION_COMPATIBILITY),
    ("certainty", ScopeDimension.CERTAINTY_GENERALIZATION_MISMATCH),
    ("direction", ScopeDimension.RELATION_DIRECTION_AGREEMENT),
    ("numerical_values", ScopeDimension.NUMERICAL_AGREEMENT),
)


def _known(value: str | list[str]) -> ScopeValue[Any]:
    return ScopeValue[Any](status=ScopeValueStatus.KNOWN, value=value)


def _extract_text_scope(text: str) -> ScientificScope:
    values: dict[str, ScopeValue[Any]] = {}
    for field, patterns in _PATTERNS.items():
        match = next((m for p in patterns if (m := re.search(p, text, re.I))), None)
        if match:
            value = (match.group(1) if match.lastindex else match.group(0)).strip(" .,:;()").lower()
            if field == "numerical_values":
                values[field] = _known([m.group(0).strip().lower() for m in re.finditer(patterns[0], text, re.I)])
            elif field == "direction":
                values[field] = _known(_direction_class(value))
            else:
                values[field] = _known(value)
    condition_terms = re.findall(r"\b(?:under|with|without|during|at)\s+([\w-]+(?:\s+[\w-]+){0,2})", text, re.I)
    if condition_terms:
        values["conditions"] = _known([v.lower().strip(" .,:;") for v in condition_terms[:3]])
    return ScientificScope(**values)


def _direction_class(value: str) -> str:
    if re.search(r"\b(improv\w*|increas\w*|higher|greater|better)\b", value, re.I):
        return "positive"
    if re.search(r"\b(reduc\w*|decreas\w*|lower|worse)\b", value, re.I):
        return "negative"
    return value.lower()


def extract_evidence_scope(hit: RetrievalHit) -> ScientificScope:
    """Extract scope from ``chunk.metadata['scope']`` or from passage text.

    Metadata accepts a ``ScientificScope`` instance or its serialized mapping.
    Invalid third-party metadata is ignored in favor of conservative local
    extraction; this keeps optional upstream adapters replaceable.
    """
    raw: Any = hit.chunk.metadata.get("scope")
    if isinstance(raw, ScientificScope):
        supplied = raw
    elif isinstance(raw, Mapping):
        try:
            supplied = ScientificScope.model_validate(raw)
        except (TypeError, ValueError):
            supplied = None
    else:
        supplied = None
    parsed = _extract_text_scope(hit.chunk.text)
    if supplied is None:
        return parsed
    values = {}
    for field in ScientificScope.model_fields:
        explicit = getattr(supplied, field)
        values[field] = explicit if explicit.status is ScopeValueStatus.KNOWN else getattr(parsed, field)
    return ScientificScope(**values)


def extract_claim_scope(claim: AtomicClaim) -> ScientificScope:
    """Use explicit claim scope first, filling only unknown fields from text."""
    parsed = _extract_text_scope(claim.text)
    values = {}
    for field in ScientificScope.model_fields:
        explicit = getattr(claim.scope, field)
        values[field] = explicit if explicit.status is ScopeValueStatus.KNOWN else getattr(parsed, field)
    return ScientificScope(**values)


def _normalize(value: Any) -> set[str]:
    if isinstance(value, list):
        return {str(v).strip().lower() for v in value if str(v).strip()}
    return {str(value).strip().lower()} if value is not None else set()


def _compare_values(left: ScopeValue[Any], right: ScopeValue[Any], *, overlap_ok: bool = True) -> DimensionStatus:
    if left.status is not ScopeValueStatus.KNOWN or right.status is not ScopeValueStatus.KNOWN:
        return DimensionStatus.UNKNOWN
    a, b = _normalize(left.value), _normalize(right.value)
    if not a or not b:
        return DimensionStatus.UNKNOWN
    if a == b:
        return DimensionStatus.COMPATIBLE
    if overlap_ok and any(x in y or y in x for x in a for y in b):
        return DimensionStatus.PARTIALLY_COMPATIBLE
    return DimensionStatus.INCOMPATIBLE


def compare_scope(claim: AtomicClaim, evidence: ScientificScope) -> list[DimensionComparison]:
    """Compare all available scope fields; unknown pairs stay unknown."""
    comparisons: list[DimensionComparison] = []
    claim_scope = extract_claim_scope(claim)
    for field, dimension in _DIMENSION_BINDINGS:
        left: ScopeValue[Any] = getattr(claim_scope, field)
        right: ScopeValue[Any] = getattr(evidence, field)
        status = _compare_values(left, right)
        lv = left.value if left.status is ScopeValueStatus.KNOWN else "unknown"
        rv = right.value if right.status is ScopeValueStatus.KNOWN else "unknown"
        comparisons.append(DimensionComparison(
            dimension=dimension,
            status=status,
            explanation=f"{field.replace('_', ' ').capitalize()}: claim={lv!s}; evidence={rv!s}.",
        ))
    return comparisons


def weighted_scope_score(
    comparisons: list[DimensionComparison],
    weights: Mapping[ScopeDimension, float],
) -> float | None:
    """Return weighted compatibility over known comparisons only.

    Compatible=1, partial=0.5, incompatible=0. Unknown dimensions do not enter
    either numerator or denominator. Returns ``None`` when no pair is known.
    """
    scores = {
        DimensionStatus.COMPATIBLE: 1.0,
        DimensionStatus.PARTIALLY_COMPATIBLE: 0.5,
        DimensionStatus.INCOMPATIBLE: 0.0,
    }
    weighted = total = 0.0
    for comparison in comparisons:
        weight = weights.get(comparison.dimension, 0.0)
        if weight <= 0 or comparison.status is DimensionStatus.UNKNOWN:
            continue
        weighted += weight * scores[comparison.status]
        total += weight
    return weighted / total if total else None


def score_status(score: float | None) -> DimensionStatus:
    if score is None:
        return DimensionStatus.UNKNOWN
    if score >= 0.85:
        return DimensionStatus.COMPATIBLE
    if score <= 0.15:
        return DimensionStatus.INCOMPATIBLE
    return DimensionStatus.PARTIALLY_COMPATIBLE
