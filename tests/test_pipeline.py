from __future__ import annotations

import json
from pathlib import Path

import pytest

from scopecheck.alignment import ComparatorMode
from scopecheck.claims import extract_claims
from scopecheck.contracts import AnalyzeRequest, Relation
from scopecheck.pipeline import analyze, analyze_claims, serialize_result


def _write(tmp_path: Path, name: str, text: str, suffix: str = ".md") -> Path:
    path = tmp_path / f"{name}{suffix}"
    path.write_text(text, encoding="utf-8")
    return path


def _request(document_ids: list[str], text: str = "On dataset Alpha, Model A increased accuracy by 5%.") -> AnalyzeRequest:
    return AnalyzeRequest(draft_text=text, selected_document_ids=document_ids)


def test_ingestion_to_retrieval_preserves_document_identity(tmp_path: Path) -> None:
    source = _write(tmp_path, "paper", "On dataset Alpha, Model A increased accuracy by 5%.")
    result = analyze(_request(["paper"]), {"paper": source})
    hits = result.analyses[0].retrieval_hits
    assert hits
    assert all(hit.chunk.document_id == "paper" for hit in hits)


def test_claim_extraction_to_scope_comparison_and_exact_quote(tmp_path: Path) -> None:
    quote = "On dataset Alpha, Model A increased accuracy by 5%."
    source = _write(tmp_path, "paper", quote)
    claim = extract_claims(quote, "draft")[0]
    result = analyze_claims([claim], {"paper": source}, mode=ComparatorMode.SCOPE_AWARE)
    comparison = result.analyses[0].comparisons[0]
    assert comparison.relation is Relation.SUPPORT
    assert comparison.evidence_quote == quote
    assert comparison.evidence_quote in result.analyses[0].retrieval_hits[0].chunk.text


def test_full_pipeline_supports_text_only_and_scope_aware_modes(tmp_path: Path) -> None:
    quote = "On dataset Alpha, Model A increased accuracy by 5%."
    source = _write(tmp_path, "paper", quote)
    request = _request(["paper"])
    text_only = analyze(request, {"paper": source}, mode="text_only")
    scoped = analyze(request, {"paper": source}, mode="scope_aware")
    assert text_only.analyses[0].comparisons[0].model_version.endswith(":text_only")
    assert scoped.analyses[0].comparisons[0].model_version.endswith(":scope_aware")
    assert text_only.analyses[0].claim.source_span.document_id == "draft"


def test_draft_is_never_indexed_as_its_own_evidence(tmp_path: Path) -> None:
    draft = _write(tmp_path, "draft", "On dataset Alpha, Model A increased accuracy by 5%.")
    result = analyze_claims(
        extract_claims(draft.read_text(), "draft"),
        {"draft": draft},
        selected_document_ids=["draft"],
    )
    assert result.status == "insufficient_evidence"
    assert result.analyses[0].retrieval_hits == []


def test_selected_source_allow_list_is_respected(tmp_path: Path) -> None:
    selected = _write(tmp_path, "selected", "On dataset Alpha, Model A increased accuracy by 5%.")
    excluded = _write(tmp_path, "excluded", "On dataset Alpha, Model A decreased accuracy by 90%.")
    result = analyze(
        _request(["selected"]), {"selected": selected, "excluded": excluded}, top_k=5
    )
    assert result.analyses[0].retrieval_hits
    assert {hit.chunk.document_id for hit in result.analyses[0].retrieval_hits} == {"selected"}


def test_empty_corpus_reports_insufficient_evidence(tmp_path: Path) -> None:
    empty = _write(tmp_path, "empty", "  \n")
    result = analyze(_request(["empty"]), {"empty": empty})
    assert result.status == "insufficient_evidence"
    assert result.analyses[0].retrieval_hits == []
    assert result.analyses[0].comparisons == []


def test_invalid_document_is_reported(tmp_path: Path) -> None:
    source = _write(tmp_path, "paper", "bad", suffix=".unsupported")
    with pytest.raises(ValueError, match="unsupported document format"):
        analyze(_request(["paper"]), {"paper": source})


def test_missing_selected_document_is_reported() -> None:
    with pytest.raises(ValueError, match="unavailable"):
        analyze(_request(["missing"]), {})


def test_direct_claim_input_and_retrieval_filtering(tmp_path: Path) -> None:
    a = _write(tmp_path, "a", "On dataset Alpha, Model A increased accuracy by 5%.")
    b = _write(tmp_path, "b", "On dataset Beta, Model A decreased accuracy by 30%.")
    claim = extract_claims("On dataset Alpha, Model A increased accuracy by 5%.", "draft")[0]
    result = analyze_claims([claim], {"a": a, "b": b}, selected_document_ids=["b"])
    assert {hit.chunk.document_id for hit in result.analyses[0].retrieval_hits} == {"b"}


def test_json_serialization_contains_claim_hits_dimensions_and_verbatim_quote(tmp_path: Path) -> None:
    quote = "On dataset Alpha, Model A increased accuracy by 5%."
    source = _write(tmp_path, "paper", quote)
    response = analyze(_request(["paper"]), {"paper": source})
    serialized = serialize_result(response)
    decoded = json.loads(serialized)
    comparison = decoded["analyses"][0]["comparisons"][0]
    assert comparison["evidence_quote"] == quote
    assert comparison["dimension_comparisons"]
    assert decoded["analyses"][0]["retrieval_hits"][0]["chunk"]["document_id"] == "paper"


def test_top_k_and_invalid_k(tmp_path: Path) -> None:
    source = _write(tmp_path, "paper", "\n\n".join(
        f"On dataset Alpha, Model A increased accuracy by {number}%." for number in range(1, 5)
    ))
    result = analyze(_request(["paper"]), {"paper": source}, top_k=2)
    assert len(result.analyses[0].retrieval_hits) <= 2
    with pytest.raises(ValueError, match="top_k"):
        analyze(_request(["paper"]), {"paper": source}, top_k=0)
