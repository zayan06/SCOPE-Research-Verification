"""Validation tests for central integration contracts."""

import pytest
from pydantic import ValidationError

from scopecheck.contracts import (
    AtomicClaim, ComparisonResult, DimensionComparison, DimensionStatus,
    EvidenceChunk, ExtractionMethod, Relation, RetrievalHit, RetrievalMethod,
    ScopeDimension, ScopeValue, ScopeValueStatus, ScientificScope, SourceSpan,
)


def sample_claim() -> AtomicClaim:
    return AtomicClaim(
        id="claim-1", text="Method A improves accuracy on Dataset X.",
        document_id="draft-1",
        source_span=SourceSpan(
            document_id="draft-1", section_id="results", page_number=2,
            start_offset=10, end_offset=53,
            exact_text="Method A improves accuracy on Dataset X.",
        ),
        extraction_method=ExtractionMethod.UNKNOWN,
    )


def sample_hit() -> RetrievalHit:
    return RetrievalHit(
        chunk=EvidenceChunk(
            id="chunk-1", document_id="paper-1",
            text="Method A improved accuracy on Dataset X.",
            section_name="Results", page_number=4, start_offset=100, end_offset=142,
        ),
        score=0.82, rank=1, retrieval_method=RetrievalMethod.TFIDF,
    )


def test_scientific_scope_defaults_to_explicit_unknowns() -> None:
    scope = ScientificScope()
    assert scope.population.status is ScopeValueStatus.UNKNOWN
    assert scope.population.value is None
    assert scope.dataset.status is ScopeValueStatus.UNKNOWN


def test_known_scope_requires_a_value() -> None:
    with pytest.raises(ValidationError):
        ScopeValue[str](status=ScopeValueStatus.KNOWN)


def test_unknown_scope_cannot_carry_a_value() -> None:
    with pytest.raises(ValidationError):
        ScopeValue[str](status=ScopeValueStatus.UNKNOWN, value="Dataset X")


def test_source_spans_reject_incomplete_or_reversed_offsets() -> None:
    with pytest.raises(ValidationError):
        SourceSpan(document_id="d1", start_offset=2, exact_text="x")
    with pytest.raises(ValidationError):
        SourceSpan(document_id="d1", start_offset=3, end_offset=2, exact_text="x")


def test_comparison_contract_serializes_relation_and_dimension_status() -> None:
    claim, hit = sample_claim(), sample_hit()
    result = ComparisonResult(
        claim_id=claim.id, evidence_chunk_id=hit.chunk.id,
        relation=Relation.QUALIFY, confidence=0.5,
        scope_compatibility=DimensionStatus.PARTIALLY_COMPATIBLE,
        dimension_comparisons=[DimensionComparison(
            dimension=ScopeDimension.DATASET_COMPATIBILITY,
            status=DimensionStatus.UNKNOWN,
            explanation="The claim does not identify a dataset.",
        )],
        explanation="The source passage requires researcher review.",
        evidence_quote=hit.chunk.text, recommended_action="review_source_context",
        model_version="contract-test",
    )
    data = result.model_dump(mode="json")
    assert data["relation"] == "qualify"
    assert data["scope_compatibility"] == "partially_compatible"
    assert data["dimension_comparisons"][0]["status"] == "unknown"


def test_retrieval_hit_rejects_invalid_rank() -> None:
    with pytest.raises(ValidationError):
        RetrievalHit(chunk=sample_hit().chunk, score=0.4, rank=0, retrieval_method="tfidf")


def test_comparison_rejects_confidence_outside_unit_interval() -> None:
    with pytest.raises(ValidationError):
        ComparisonResult(
            claim_id="c1", evidence_chunk_id="e1", relation="support",
            confidence=1.1, scope_compatibility="unknown", dimension_comparisons=[],
            explanation="Example.", evidence_quote="Exact quote.",
            recommended_action="review_source_context", model_version="test",
        )
