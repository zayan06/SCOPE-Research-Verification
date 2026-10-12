"""End-to-end local document-to-claim evidence analysis pipeline."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from scopecheck.alignment import (
    ComparatorConfig,
    ComparatorMode,
    compare_claim_to_hit_with_config,
)
from scopecheck.claims import extract_claims
from scopecheck.contracts import (
    AnalyzeRequest,
    AnalyzeResponse,
    AtomicClaim,
    ClaimAnalysis,
    RetrievalMethod,
)
from scopecheck.ingestion import parse_document
from scopecheck.retrieval import build_index

DocumentSource = str | Path


def analyze(
    request: AnalyzeRequest,
    source_documents: Mapping[str, DocumentSource],
    *,
    top_k: int = 5,
    mode: ComparatorMode | str = ComparatorMode.SCOPE_AWARE,
    retrieval_method: RetrievalMethod | str = RetrievalMethod.TFIDF,
) -> AnalyzeResponse:
    """Extract draft claims and compare them with selected source documents.

    ``source_documents`` maps stable document IDs to local paths. The draft is
    extracted separately and never added to the evidence index.
    """
    if not request.draft_text.strip():
        raise ValueError("draft_text must not be empty")
    claims = extract_claims(request.draft_text, document_id="draft")
    return analyze_claims(
        claims,
        source_documents,
        selected_document_ids=request.selected_document_ids,
        top_k=top_k,
        mode=mode,
        retrieval_method=retrieval_method,
    )


def analyze_claims(
    claims: Sequence[AtomicClaim],
    source_documents: Mapping[str, DocumentSource],
    *,
    selected_document_ids: Sequence[str] | None = None,
    top_k: int = 5,
    mode: ComparatorMode | str = ComparatorMode.SCOPE_AWARE,
    retrieval_method: RetrievalMethod | str = RetrievalMethod.TFIDF,
) -> AnalyzeResponse:
    """Run supplied atomic claims against a selected local source corpus."""
    if top_k < 1:
        raise ValueError("top_k must be at least 1")
    comparator_mode = ComparatorMode(mode)
    strategy = RetrievalMethod(retrieval_method)
    selected = list(source_documents) if selected_document_ids is None else list(selected_document_ids)
    if len(selected) != len(set(selected)):
        raise ValueError("selected_document_ids must be unique")
    missing = [document_id for document_id in selected if document_id not in source_documents]
    if missing:
        raise ValueError(f"selected source documents are unavailable: {', '.join(missing)}")

    # A direct-claim caller may include a draft path in its document mapping;
    # never permit claim-origin documents to serve as their own evidence.
    draft_ids = {claim.document_id for claim in claims}
    selected = [document_id for document_id in selected if document_id not in draft_ids]
    chunks = [
        chunk
        for document_id in selected
        for chunk in parse_document(source_documents[document_id], document_id=document_id)
    ]
    index = build_index(chunks, method=strategy)
    config = ComparatorConfig(mode=comparator_mode)

    analyses: list[ClaimAnalysis] = []
    has_missing_evidence = False
    for claim in claims:
        hits = index.search(
            claim.text,
            k=top_k,
            allowed_document_ids=selected,
            method=strategy,
        )
        comparisons = [
            compare_claim_to_hit_with_config(claim, hit, config) for hit in hits
        ]
        if not hits:
            has_missing_evidence = True
        analyses.append(ClaimAnalysis(claim=claim, retrieval_hits=hits, comparisons=comparisons))

    if not analyses:
        status = "no_claims"
    elif has_missing_evidence and any(item.retrieval_hits for item in analyses):
        status = "partial_insufficient_evidence"
    elif has_missing_evidence:
        status = "insufficient_evidence"
    else:
        status = "completed"
    return AnalyzeResponse(analyses=analyses, status=status)


def serialize_result(response: AnalyzeResponse, *, indent: int = 2) -> str:
    """Serialize a pipeline result using the canonical API contract models."""
    return response.model_dump_json(indent=indent)
