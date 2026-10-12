"""Canonical typed contracts shared by SCOPE modules and API boundaries.

Unknown values are explicit ``ScopeValue(status="unknown")`` objects. A missing
field must never be interpreted as scientific agreement.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

T = TypeVar("T")


class ContractModel(BaseModel):
    """Base model: reject misspelled fields while allowing forward metadata."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ScopeValueStatus(StrEnum):
    KNOWN = "known"
    UNKNOWN = "unknown"


class ScopeValue(ContractModel, Generic[T]):
    """A known value or an explicit unknown; never infer agreement from absence."""

    status: ScopeValueStatus = ScopeValueStatus.UNKNOWN
    value: T | None = None

    @model_validator(mode="after")
    def known_values_must_be_present(self) -> ScopeValue[T]:
        if self.status is ScopeValueStatus.KNOWN and self.value is None:
            raise ValueError("known scope values require a non-null value")
        if self.status is ScopeValueStatus.UNKNOWN and self.value is not None:
            raise ValueError("unknown scope values must not carry a value")
        return self


class Relation(StrEnum):
    SUPPORT = "support"
    CONTRADICT = "contradict"
    QUALIFY = "qualify"
    SCOPE_MISMATCH = "scope_mismatch"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    UNRELATED = "unrelated"


class DimensionStatus(StrEnum):
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    PARTIALLY_COMPATIBLE = "partially_compatible"
    UNKNOWN = "unknown"


class ScopeDimension(StrEnum):
    SEMANTIC_AGREEMENT = "semantic_agreement"
    LEXICAL_AGREEMENT = "lexical_agreement"
    ENTITY_AGREEMENT = "entity_agreement"
    POPULATION_COMPATIBILITY = "population_compatibility"
    DATASET_COMPATIBILITY = "dataset_compatibility"
    METHODOLOGICAL_COMPATIBILITY = "methodological_compatibility"
    OUTCOME_METRIC_COMPATIBILITY = "outcome_metric_compatibility"
    NUMERICAL_AGREEMENT = "numerical_agreement"
    RELATION_DIRECTION_AGREEMENT = "relation_direction_agreement"
    EXPERIMENTAL_CONDITION_COMPATIBILITY = "experimental_condition_compatibility"
    CERTAINTY_GENERALIZATION_MISMATCH = "certainty_generalization_mismatch"


class ClaimType(StrEnum):
    EMPIRICAL = "empirical"
    CAUSAL = "causal"
    COMPARATIVE = "comparative"
    QUANTITATIVE = "quantitative"
    GENERALIZATION = "generalization"
    OTHER = "other"
    UNKNOWN = "unknown"


class ExtractionMethod(StrEnum):
    RULE_BASED = "rule_based"
    MODEL_ASSISTED = "model_assisted"
    HUMAN = "human"
    UNKNOWN = "unknown"


class RetrievalMethod(StrEnum):
    TFIDF = "tfidf"
    BM25 = "bm25"
    DENSE = "dense"
    HYBRID = "hybrid"
    UNKNOWN = "unknown"


class RecommendedAction(StrEnum):
    REVIEW_SOURCE_CONTEXT = "review_source_context"
    CONSIDER_NARROWING_CLAIM = "consider_narrowing_claim"
    SEARCH_FOR_ADDITIONAL_EVIDENCE = "search_for_additional_evidence"
    CHECK_CONTRADICTORY_EVIDENCE = "check_contradictory_evidence"
    NO_AUTOMATED_RECOMMENDATION = "no_automated_recommendation"


class SourceSpan(ContractModel):
    document_id: str = Field(min_length=1)
    section_id: str | None = None
    page_number: int | None = Field(default=None, ge=1)
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, ge=0)
    exact_text: str = Field(min_length=1)

    @model_validator(mode="after")
    def offsets_are_a_valid_pair(self) -> SourceSpan:
        if (self.start_offset is None) != (self.end_offset is None):
            raise ValueError("start_offset and end_offset must be supplied together")
        if self.start_offset is not None and self.end_offset <= self.start_offset:
            raise ValueError("end_offset must be greater than start_offset")
        return self


class EvidenceChunk(ContractModel):
    id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    section_name: str | None = None
    page_number: int | None = Field(default=None, ge=1)
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def offsets_are_a_valid_pair(self) -> EvidenceChunk:
        if (self.start_offset is None) != (self.end_offset is None):
            raise ValueError("start_offset and end_offset must be supplied together")
        if self.start_offset is not None and self.end_offset <= self.start_offset:
            raise ValueError("end_offset must be greater than start_offset")
        return self


class ScientificScope(ContractModel):
    population: ScopeValue[str] = Field(default_factory=ScopeValue[str])
    dataset: ScopeValue[str] = Field(default_factory=ScopeValue[str])
    methodology: ScopeValue[str] = Field(default_factory=ScopeValue[str])
    intervention: ScopeValue[str] = Field(default_factory=ScopeValue[str])
    outcome: ScopeValue[str] = Field(default_factory=ScopeValue[str])
    metric: ScopeValue[str] = Field(default_factory=ScopeValue[str])
    time_period: ScopeValue[str] = Field(default_factory=ScopeValue[str])
    domain: ScopeValue[str] = Field(default_factory=ScopeValue[str])
    conditions: ScopeValue[list[str]] = Field(default_factory=ScopeValue[list[str]])
    certainty: ScopeValue[str] = Field(default_factory=ScopeValue[str])
    direction: ScopeValue[str] = Field(default_factory=ScopeValue[str])
    numerical_values: ScopeValue[list[str]] = Field(default_factory=ScopeValue[list[str]])


class AtomicClaim(ContractModel):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    claim_type: ClaimType = ClaimType.UNKNOWN
    scope: ScientificScope = Field(default_factory=ScientificScope)
    source_span: SourceSpan
    extraction_method: ExtractionMethod = ExtractionMethod.UNKNOWN


class RetrievalHit(ContractModel):
    chunk: EvidenceChunk
    score: float = Field(ge=0)
    rank: int = Field(ge=1)
    retrieval_method: RetrievalMethod = RetrievalMethod.UNKNOWN


class DimensionComparison(ContractModel):
    dimension: ScopeDimension
    status: DimensionStatus
    explanation: str = Field(min_length=1)


class ComparisonResult(ContractModel):
    claim_id: str = Field(min_length=1)
    evidence_chunk_id: str = Field(min_length=1)
    relation: Relation
    confidence: float = Field(ge=0, le=1)
    scope_compatibility: DimensionStatus
    dimension_comparisons: list[DimensionComparison]
    explanation: str = Field(min_length=1)
    evidence_quote: str = Field(min_length=1)
    recommended_action: RecommendedAction
    model_version: str = Field(min_length=1)


class DocumentSummary(ContractModel):
    document_id: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    status: str = Field(min_length=1)


class DocumentUploadResponse(DocumentSummary):
    message: str


class AnalyzeRequest(ContractModel):
    draft_text: str = Field(min_length=1)
    selected_document_ids: list[str] = Field(min_length=1)


class ClaimAnalysis(ContractModel):
    claim: AtomicClaim
    retrieval_hits: list[RetrievalHit]
    comparisons: list[ComparisonResult]


class AnalyzeResponse(ContractModel):
    analyses: list[ClaimAnalysis]
    status: str


class AnalyzeCorpusRequest(ContractModel):
    benchmark_id: str = Field(min_length=1)
    corpus_document_ids: list[str] = Field(min_length=1)


class AnalyzeCorpusResponse(ContractModel):
    benchmark_id: str
    status: str
    output_path: str | None = None
    message: str


class HealthResponse(ContractModel):
    status: str
    version: str
    mode: str
