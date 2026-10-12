"""Tests for deterministic and model-assisted claim extraction."""

import json

import pytest

from scopecheck.claims.extractor import extract_claims
from scopecheck.claims.gemini import _validated_claims
from scopecheck.contracts import ClaimType, ExtractionMethod, ScopeValueStatus


def test_simple_atomic_claim_and_traceability() -> None:
    text = "Method A improves accuracy."
    claims = extract_claims(text, "paper-1")
    assert len(claims) == 1
    claim = claims[0]
    assert claim.text == text
    assert claim.claim_type is ClaimType.EMPIRICAL
    assert claim.extraction_method is ExtractionMethod.RULE_BASED
    assert claim.source_span.exact_text == text
    assert text[claim.source_span.start_offset:claim.source_span.end_offset] == text
    assert claim.scope.metric.value == "accuracy"


def test_compound_contrast_is_split_with_distinct_datasets() -> None:
    text = "Model A improves accuracy on Dataset X, but performs worse than Model B on Dataset Y."
    claims = extract_claims(text, "paper-2")
    assert len(claims) == 2
    assert claims[0].scope.dataset.value == "Dataset X"
    assert claims[1].scope.dataset.value == "Dataset Y"
    assert claims[1].claim_type is ClaimType.COMPARATIVE
    assert claims[1].text.startswith("Model A performs worse")
    assert claims[1].scope.methodology.value == "Model A"
    assert all(text[c.source_span.start_offset:c.source_span.end_offset] == c.source_span.exact_text for c in claims)


def test_numerical_result_preserves_number_and_units() -> None:
    claim = extract_claims("Accuracy increased by 12% after 4 weeks.", "paper")[0]
    assert claim.claim_type is ClaimType.QUANTITATIVE
    assert claim.scope.numerical_values.value == ["12%", "4 weeks"]
    assert claim.scope.time_period.value == "after 4 weeks"


def test_negative_result_is_not_rewritten_as_positive() -> None:
    claim = extract_claims("Method A did not increase accuracy.", "paper")[0]
    assert "not increase" in claim.text
    assert claim.scope.direction.value == "negative"


def test_universal_generalization_is_retained() -> None:
    claim = extract_claims("Across all datasets, Method A improves accuracy.", "paper")[0]
    assert "Across all datasets" in claim.text
    assert claim.claim_type is ClaimType.GENERALIZATION
    assert claim.scope.conditions.value == ["Across all datasets"]


def test_dataset_specific_finding() -> None:
    claim = extract_claims("The treatment reduced symptoms on Dataset Z.", "paper")[0]
    assert claim.scope.dataset.value == "Dataset Z"


def test_conditional_finding_preserves_only_and_condition() -> None:
    text = "Method A improves accuracy only under low-light conditions."
    claim = extract_claims(text, "paper")[0]
    assert "only under low-light conditions" in claim.text
    assert claim.scope.conditions.value == ["only under low-light conditions"]


def test_qualified_finding_preserves_modality_and_significance() -> None:
    claim = extract_claims("Method A may produce a statistically significant improvement.", "paper")[0]
    assert "may" in claim.text and "statistically significant" in claim.text
    assert claim.scope.certainty.value == "possible; statistically_significant"


def test_causal_statement() -> None:
    claim = extract_claims("Exercise causes lower blood pressure.", "paper")[0]
    assert claim.claim_type is ClaimType.CAUSAL


def test_correlational_statement_is_not_marked_causal() -> None:
    claim = extract_claims("Exposure was associated with higher risk.", "paper")[0]
    assert claim.claim_type is ClaimType.EMPIRICAL
    assert claim.scope.certainty.value == "associated"


def test_comparative_finding() -> None:
    claim = extract_claims("Method A performed better than Method B.", "paper")[0]
    assert claim.claim_type is ClaimType.COMPARATIVE


def test_unknown_scope_is_explicit() -> None:
    claim = extract_claims("The intervention worked.", "paper")[0]
    assert claim.scope.dataset.status is ScopeValueStatus.UNKNOWN
    assert claim.scope.population.status is ScopeValueStatus.UNKNOWN


def test_no_checkable_assertion_and_empty_input() -> None:
    assert extract_claims("This paragraph describes the experiment.", "paper") == []
    assert extract_claims(" \n ", "paper") == []


def test_invalid_model_extraction_output_is_rejected() -> None:
    with pytest.raises(ValueError, match="malformed"):
        _validated_claims('{"claims":[{"text":"claim"}]}', "Method A works.", "paper")
    with pytest.raises(ValueError, match="does not occur"):
        _validated_claims(json.dumps({"claims": [{"text": "invented result", "source_text": "invented"}]}), "Method A works.", "paper")


def test_gemini_validated_output_has_model_method_and_exact_offsets() -> None:
    source = "Method A improved accuracy by 12%."
    payload = json.dumps({"claims": [{"text": source, "source_text": source}]})
    claim = _validated_claims(payload, source, "paper")[0]
    assert claim.extraction_method is ExtractionMethod.MODEL_ASSISTED
    assert source[claim.source_span.start_offset:claim.source_span.end_offset] == claim.source_span.exact_text
