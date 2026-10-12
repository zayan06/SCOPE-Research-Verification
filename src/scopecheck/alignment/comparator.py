"""Conservative local comparator for claim and retrieved evidence passages."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping

from scopecheck.contracts import (
    AtomicClaim,
    ClaimType,
    ComparisonResult,
    DimensionComparison,
    DimensionStatus,
    RecommendedAction,
    Relation,
    RetrievalHit,
    ScopeDimension,
)

from .factual import analyze_facts, numerical_relation
from .scope import compare_scope, extract_evidence_scope, score_status, weighted_scope_score


class ComparatorMode(StrEnum):
    TEXT_ONLY = "text_only"
    SCOPE_AWARE = "scope_aware"


_DEFAULT_WEIGHTS: dict[ScopeDimension, float] = {
    ScopeDimension.POPULATION_COMPATIBILITY: 1.5,
    ScopeDimension.DATASET_COMPATIBILITY: 1.0,
    ScopeDimension.METHODOLOGICAL_COMPATIBILITY: 1.0,
    ScopeDimension.SEMANTIC_AGREEMENT: 1.25,
    ScopeDimension.OUTCOME_METRIC_COMPATIBILITY: 1.5,
    ScopeDimension.EXPERIMENTAL_CONDITION_COMPATIBILITY: 1.0,
    ScopeDimension.CERTAINTY_GENERALIZATION_MISMATCH: 0.75,
    ScopeDimension.RELATION_DIRECTION_AGREEMENT: 1.5,
    ScopeDimension.NUMERICAL_AGREEMENT: 1.5,
    ScopeDimension.ENTITY_AGREEMENT: 1.25,
    ScopeDimension.LEXICAL_AGREEMENT: 0.5,
}

_TYPE_WEIGHT_MULTIPLIERS: dict[ClaimType, dict[ScopeDimension, float]] = {
    ClaimType.QUANTITATIVE: {ScopeDimension.NUMERICAL_AGREEMENT: 1.5},
    ClaimType.COMPARATIVE: {ScopeDimension.RELATION_DIRECTION_AGREEMENT: 1.25},
    ClaimType.CAUSAL: {ScopeDimension.METHODOLOGICAL_COMPATIBILITY: 1.25},
    ClaimType.GENERALIZATION: {ScopeDimension.POPULATION_COMPATIBILITY: 1.5, ScopeDimension.CERTAINTY_GENERALIZATION_MISMATCH: 1.5},
}


@dataclass(frozen=True)
class ComparatorConfig:
    """Stable evaluation switch and documented, configurable heuristic weights."""

    mode: ComparatorMode = ComparatorMode.SCOPE_AWARE
    weights: Mapping[ScopeDimension, float] = field(default_factory=lambda: dict(_DEFAULT_WEIGHTS))
    version: str = "rules/0.1.0"

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", ComparatorMode(self.mode))
        normalized_weights = {ScopeDimension(key): float(value) for key, value in self.weights.items()}
        object.__setattr__(self, "weights", normalized_weights)
        if any(weight < 0 for weight in self.weights.values()):
            raise ValueError("scope weights must be non-negative")


def _dimension_comparisons(
    claim: AtomicClaim, hit: RetrievalHit, config: ComparatorConfig,
) -> tuple[list[DimensionComparison], float | None]:
    if config.mode is ComparatorMode.SCOPE_AWARE:
        comparisons = compare_scope(claim, extract_evidence_scope(hit))
        weights = dict(config.weights)
        for dimension, multiplier in _TYPE_WEIGHT_MULTIPLIERS.get(claim.claim_type, {}).items():
            weights[dimension] = weights.get(dimension, 0.0) * multiplier
        return comparisons, weighted_scope_score(comparisons, weights)

    # Baseline retains lexical/factual observations but does not extract or
    # compare scientific scope fields. Unknown scope fields cannot raise its score.
    return [
        DimensionComparison(
            dimension=ScopeDimension.SEMANTIC_AGREEMENT,
            status=DimensionStatus.UNKNOWN,
            explanation="Text-only baseline does not perform structured entity or scope comparison.",
        ),
        DimensionComparison(
            dimension=ScopeDimension.LEXICAL_AGREEMENT,
            status=DimensionStatus.UNKNOWN,
            explanation="Lexical overlap is used for relevance only; it is not treated as scope agreement.",
        ),
    ], None


def _classify(
    claim: AtomicClaim,
    hit: RetrievalHit,
    comparisons: list[DimensionComparison],
    score: float | None,
) -> tuple[Relation, str, float, RecommendedAction]:
    claim_facts, evidence_facts = analyze_facts(claim.text, hit.chunk.text)
    if not claim_facts.relevant:
        return (
            Relation.UNRELATED,
            "The passage shares no substantive proposition terms with the claim and does not establish a relevant factual relationship.",
            0.86,
            RecommendedAction.SEARCH_FOR_ADDITIONAL_EVIDENCE,
        )

    material = {
        ScopeDimension.POPULATION_COMPATIBILITY,
        ScopeDimension.DATASET_COMPATIBILITY,
        ScopeDimension.METHODOLOGICAL_COMPATIBILITY,
        ScopeDimension.OUTCOME_METRIC_COMPATIBILITY,
        ScopeDimension.EXPERIMENTAL_CONDITION_COMPATIBILITY,
    }
    mismatches = [c for c in comparisons if c.dimension in material and c.status is DimensionStatus.INCOMPATIBLE]
    num_relation = numerical_relation(claim_facts, evidence_facts)
    opposite = bool(claim_facts.direction and evidence_facts.direction and claim_facts.direction != evidence_facts.direction)
    conditions_comparable = not mismatches

    # A mismatch blocks direct inference. It never itself becomes a contradiction.
    if mismatches:
        names = ", ".join(dict.fromkeys(c.explanation.split(":", 1)[0].lower() for c in mismatches))
        return (
            Relation.SCOPE_MISMATCH,
            f"The evidence addresses a related proposition, but materially different {names} prevent a direct comparison. "
            "This scope difference is not classified as a factual contradiction.",
            0.82,
            RecommendedAction.REVIEW_SOURCE_CONTEXT,
        )

    if conditions_comparable and (opposite or num_relation == "disagreement"):
        cue = "opposite outcome directions" if opposite else "numerical values that disagree in a matching unit"
        return (
            Relation.CONTRADICT,
            f"The claim and evidence assert {cue} while no explicit material scope conflict was found. "
            "Check the source context and the heuristic scope extraction before treating this as a confirmed contradiction.",
            0.76,
            RecommendedAction.CHECK_CONTRADICTORY_EVIDENCE,
        )

    if opposite and score is not None and score < 0.5:
        return (
            Relation.SCOPE_MISMATCH,
            "The passages point in opposite directions, but the available scope comparisons are too weak for a direct contradiction judgment.",
            0.65,
            RecommendedAction.REVIEW_SOURCE_CONTEXT,
        )

    qualification_reasons: list[str] = []
    if evidence_facts.conditional and not claim_facts.conditional:
        qualification_reasons.append("evidence is conditional while the claim is broader")
    if claim_facts.universal and not evidence_facts.universal:
        qualification_reasons.append("evidence does not establish the claim's universal wording")
    if evidence_facts.uncertainty and not claim_facts.uncertainty:
        qualification_reasons.append("evidence expresses greater uncertainty")
    if claim_facts.causal and evidence_facts.correlational:
        qualification_reasons.append("evidence reports association rather than causation")
    if claim_facts.direction and evidence_facts.direction == claim_facts.direction:
        if evidence_facts.uncertainty:
            qualification_reasons.append("evidence direction agrees but is tentative")

    if qualification_reasons:
        return (
            Relation.QUALIFY,
            "The evidence is directionally consistent but narrows or weakens the claim: " + "; ".join(qualification_reasons) + ".",
            0.72,
            RecommendedAction.CONSIDER_NARROWING_CLAIM,
        )

    if claim_facts.direction and evidence_facts.direction == claim_facts.direction:
        return (
            Relation.SUPPORT,
            "The passage addresses the same proposition and asserts the same outcome direction. "
            "This rule-based match is a review aid and does not establish scientific truth.",
            0.70 if score is None else min(0.9, 0.68 + 0.22 * score),
            RecommendedAction.NO_AUTOMATED_RECOMMENDATION,
        )
    if num_relation == "agreement":
        return (
            Relation.SUPPORT,
            "Extracted numerical values agree in a matching unit, and the passage is topically relevant. "
            "Verify that the values refer to the same endpoint and statistic.",
            0.7,
            RecommendedAction.REVIEW_SOURCE_CONTEXT,
        )
    return (
        Relation.INSUFFICIENT_EVIDENCE,
        "The passage is topically relevant, but the local rules found no sufficiently clear support or contradiction cue.",
        0.58,
        RecommendedAction.SEARCH_FOR_ADDITIONAL_EVIDENCE,
    )


def compare_claim_to_hit_with_config(
    claim: AtomicClaim,
    hit: RetrievalHit,
    config: ComparatorConfig,
) -> ComparisonResult:
    """Compare one claim and hit under the selected baseline/comparator mode."""
    comparisons, numeric_score = _dimension_comparisons(claim, hit, config)
    relation, rationale, confidence, action = _classify(claim, hit, comparisons, numeric_score)
    score_status_value = score_status(numeric_score)
    if config.mode is ComparatorMode.TEXT_ONLY:
        score_status_value = DimensionStatus.UNKNOWN
    score_explanation = (
        f"Scope compatibility score={numeric_score:.3f} over known weighted dimensions; unknown dimensions were excluded. "
        if numeric_score is not None
        else "Scope compatibility score=unavailable because no paired scope dimensions were known. "
    )
    explanation = f"{rationale} {score_explanation} {relation.value.capitalize()} is a heuristic label, not a calibrated probability."
    # The complete retrieved passage is an exact verbatim quote and therefore
    # cannot contain fabricated text or lose its original wording.
    return ComparisonResult(
        claim_id=claim.id,
        evidence_chunk_id=hit.chunk.id,
        relation=relation,
        confidence=confidence,
        scope_compatibility=score_status_value,
        dimension_comparisons=comparisons,
        explanation=explanation,
        evidence_quote=hit.chunk.text,
        recommended_action=action,
        model_version=f"{config.version}:{config.mode.value}",
    )


def compare_claim_to_hit(claim: AtomicClaim, hit: RetrievalHit) -> ComparisonResult:
    """Compare dimensions explicitly; unknown values must remain unknown."""
    return compare_claim_to_hit_with_config(claim, hit, ComparatorConfig())
