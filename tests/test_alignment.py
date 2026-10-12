"""Synthetic development fixtures for deterministic claim-evidence rules.

These tests exercise intended cases; they are not a research benchmark or
evidence of real-world accuracy.
"""

from __future__ import annotations

import pytest

from scopecheck.alignment.comparator import (
    ComparatorConfig,
    ComparatorMode,
    compare_claim_to_hit,
    compare_claim_to_hit_with_config,
)
from scopecheck.contracts import (
    AtomicClaim,
    ClaimType,
    DimensionStatus,
    EvidenceChunk,
    ExtractionMethod,
    Relation,
    RetrievalHit,
    RetrievalMethod,
    ScopeValue,
    ScopeValueStatus,
    ScientificScope,
    SourceSpan,
)


def known(value):
    return ScopeValue(status=ScopeValueStatus.KNOWN, value=value)


def claim(text: str, *, scope: ScientificScope | None = None, kind=ClaimType.EMPIRICAL) -> AtomicClaim:
    return AtomicClaim(
        id="claim-1", text=text, document_id="draft", claim_type=kind,
        scope=scope or ScientificScope(),
        source_span=SourceSpan(document_id="draft", exact_text=text),
        extraction_method=ExtractionMethod.HUMAN,
    )


def hit(text: str, *, scope: dict | None = None) -> RetrievalHit:
    metadata = {"scope": scope} if scope else {}
    return RetrievalHit(
        chunk=EvidenceChunk(id="evidence-1", document_id="paper-1", text=text, metadata=metadata),
        score=0.9, rank=1, retrieval_method=RetrievalMethod.TFIDF,
    )


def compare(claim_text: str, evidence_text: str, *, claim_scope=None, evidence_scope=None, kind=ClaimType.EMPIRICAL):
    return compare_claim_to_hit(claim(claim_text, scope=claim_scope, kind=kind), hit(evidence_text, scope=evidence_scope))


def test_direct_factual_support():
    result = compare("Drug A reduces mortality.", "Drug A reduced mortality in the trial.")
    assert result.relation is Relation.SUPPORT
    assert result.evidence_quote == "Drug A reduced mortality in the trial."


def test_direct_contradiction_under_comparable_conditions():
    result = compare("Drug A reduces mortality.", "Drug A increased mortality in the trial.")
    assert result.relation is Relation.CONTRADICT


def test_qualified_support_for_conditional_uncertain_evidence():
    result = compare("Drug A reduces mortality.", "Drug A may reduce mortality among older patients.")
    assert result.relation is Relation.QUALIFY


def test_different_datasets_are_scope_mismatch():
    scope = ScientificScope(dataset=known("ImageNet"))
    result = compare("Model X improves accuracy on ImageNet.", "Model X improves accuracy on CIFAR-10.", claim_scope=scope,
                     evidence_scope={"dataset": {"status": "known", "value": "CIFAR-10"}})
    assert result.relation is Relation.SCOPE_MISMATCH


def test_different_populations_are_scope_mismatch():
    result = compare("In adults, Drug A reduces mortality.", "In children, Drug A reduces mortality.")
    assert result.relation is Relation.SCOPE_MISMATCH


def test_different_methodologies_are_scope_mismatch():
    cscope = ScientificScope(methodology=known("randomized controlled trial"))
    result = compare("Drug A reduces mortality in a randomized controlled trial.",
                     "Drug A reduces mortality in an observational study.", claim_scope=cscope,
                     evidence_scope={"methodology": {"status": "known", "value": "observational study"}})
    assert result.relation is Relation.SCOPE_MISMATCH


def test_different_outcomes_are_scope_mismatch():
    result = compare("Drug A reduces mortality.", "Drug A reduces pain.")
    assert result.relation is Relation.SCOPE_MISMATCH


def test_different_metrics_are_scope_mismatch():
    result = compare("Model X improves accuracy.", "Model X improves recall.")
    assert result.relation is Relation.SCOPE_MISMATCH


def test_multiword_outcome_is_not_truncated_to_modifier():
    result = compare(
        "On dataset CellBench-1, the cobalt catalyst increased reaction yield by 12% at 80 °C.",
        "On dataset CellBench-1, the cobalt catalyst increased reaction yield by 12% at 80 °C.",
        kind=ClaimType.QUANTITATIVE,
    )
    assert result.relation is Relation.SUPPORT


def test_numerical_disagreement_is_not_hidden_by_matching_direction():
    result = compare("Drug A reduces mortality to 10%.", "Drug A reduces mortality to 20%.", kind=ClaimType.QUANTITATIVE)
    assert result.relation is Relation.CONTRADICT


def test_numerical_agreement_supports_but_requests_context_check():
    result = compare("Model X achieves 90% accuracy.", "Model X achieves 90% accuracy on the test set.", kind=ClaimType.QUANTITATIVE)
    assert result.relation is Relation.SUPPORT


def test_negation_flips_the_asserted_direction():
    result = compare("Model X does not improve accuracy.", "Model X improves accuracy.")
    assert result.relation is Relation.CONTRADICT


def test_universal_generalization_is_qualified_by_narrower_evidence():
    result = compare("Drug A always reduces mortality.", "Drug A reduced mortality among adults.")
    assert result.relation is Relation.QUALIFY


def test_correlation_does_not_establish_causation():
    result = compare("Drug A causes lower mortality.", "Drug A is associated with lower mortality.", kind=ClaimType.CAUSAL)
    assert result.relation is Relation.QUALIFY


def test_relevant_but_vague_passage_is_insufficient():
    result = compare("Drug A reduces mortality.", "Drug A and mortality were discussed in the study.")
    assert result.relation is Relation.INSUFFICIENT_EVIDENCE


def test_unrelated_passage_is_unrelated():
    result = compare("Drug A reduces mortality.", "Quantum entanglement changes photon polarization.")
    assert result.relation is Relation.UNRELATED


def test_missing_scope_remains_unknown_and_is_not_scored_as_agreement():
    result = compare("Drug A is a medication.", "Drug A is a medication.")
    assert result.scope_compatibility is DimensionStatus.UNKNOWN
    assert all(c.status is DimensionStatus.UNKNOWN for c in result.dimension_comparisons)
    assert "score=unavailable" in result.explanation


def test_opposite_directions_under_different_conditions_are_not_contradiction():
    result = compare("Drug A reduces mortality at 20C.", "Drug A increases mortality at 80C.")
    assert result.relation is Relation.SCOPE_MISMATCH


def test_opposite_conclusions_with_comparable_explicit_population_contradict():
    scope = ScientificScope(population=known("adults"))
    result = compare("Drug A reduces mortality in adults.", "Drug A increases mortality in adults.",
                     claim_scope=scope, evidence_scope={"population": {"status": "known", "value": "adults"}})
    assert result.relation is Relation.CONTRADICT


def test_text_only_baseline_is_available_and_does_not_score_scope():
    c = claim("Drug A reduces mortality in adults.")
    h = hit("Drug A reduced mortality in children.")
    result = compare_claim_to_hit_with_config(c, h, ComparatorConfig(mode=ComparatorMode.TEXT_ONLY))
    assert result.relation is Relation.SUPPORT
    assert result.scope_compatibility is DimensionStatus.UNKNOWN
    assert result.model_version == "rules/0.1.0:text_only"


def test_metadata_scope_is_augmented_with_text_extraction_for_other_fields():
    result = compare("Model X improves accuracy on ImageNet.",
                     "Model X improves accuracy on CIFAR-10.",
                     claim_scope=ScientificScope(dataset=known("ImageNet")),
                     evidence_scope={"dataset": {"status": "known", "value": "CIFAR-10"}})
    assert any(c.explanation.startswith("Direction:") and c.status is DimensionStatus.COMPATIBLE
               for c in result.dimension_comparisons)


@pytest.mark.parametrize("left,right", [("adults", "children"), ("ImageNet", "CIFAR-10")])
def test_material_scope_conflicts_do_not_become_contradictions(left, right):
    field = "population" if left == "adults" else "dataset"
    result = compare(f"Drug A reduces mortality in {left}.", f"Drug A increases mortality in {right}.",
                     claim_scope=ScientificScope(**{field: known(left)}),
                     evidence_scope={field: {"status": "known", "value": right}})
    assert result.relation is Relation.SCOPE_MISMATCH
