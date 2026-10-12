"""Analysis orchestration and replaceable integrated-pipeline boundary."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from scopecheck.pipeline import analyze as run_pipeline
from scopecheck.contracts import AnalyzeRequest, AnalyzeResponse, ClaimAnalysis
from api.database.models import (
    AnalysisRun, AtomicClaimRecord, ComparisonResultRecord, Document,
    DocumentVersion, EvidenceChunkRecord,
)


class PipelineUnavailable(RuntimeError):
    pass


class PipelineAdapter(Protocol):
    algorithm_version: str

    def analyze(self, request: AnalyzeRequest, document_paths: list[tuple[str, str]]) -> AnalyzeResponse:
        """Return canonical results for document ID/path pairs in request order."""


class UnavailablePipelineAdapter:
    algorithm_version = "unavailable"

    def analyze(self, request: AnalyzeRequest, document_paths: list[tuple[str, str]]) -> AnalyzeResponse:
        raise PipelineUnavailable("The integrated SCOPE research pipeline is not installed.")


class ScopePipelineAdapter:
    """Adapter that runs the integrated local ingestion/retrieval/comparison pipeline."""

    algorithm_version = "scope-rules/0.1.0+tfidf"

    def analyze(self, request: AnalyzeRequest, document_paths: list[tuple[str, str]]) -> AnalyzeResponse:
        sources = dict(document_paths)
        if len(sources) != len(document_paths):
            raise ValueError("Selected document IDs must be unique.")
        response = run_pipeline(request, sources)
        # Parser metadata can contain the internal upload path. The document ID,
        # filename, offsets, chunk ID, and exact quote are sufficient provenance.
        for analysis in response.analyses:
            for hit in analysis.retrieval_hits:
                hit.chunk.metadata.pop("source_path", None)
        return response


def create_run(session: Session, request: AnalyzeRequest, adapter: PipelineAdapter) -> tuple[AnalysisRun, AnalyzeResponse]:
    if len(request.selected_document_ids) != len(set(request.selected_document_ids)):
        raise ValueError("Selected document IDs must be unique.")
    documents = session.scalars(
        select(Document).where(Document.id.in_(request.selected_document_ids))
    ).all()
    by_id = {document.id: document for document in documents}
    if len(by_id) != len(set(request.selected_document_ids)):
        raise ValueError("One or more selected documents do not exist.")
    project_ids = {document.project_id for document in documents}
    if len(project_ids) != 1:
        raise ValueError("Selected documents must belong to the same project.")
    project_id = next(iter(project_ids))
    run = AnalysisRun(
        id=str(uuid4()), project_id=project_id, input_claim=request.draft_text,
        corpus_selection={"document_ids": request.selected_document_ids},
        algorithm_version=adapter.algorithm_version, status="processing",
    )
    session.add(run)
    session.flush()
    versions: list[tuple[str, str]] = []
    for document_id in request.selected_document_ids:
        latest = session.scalar(
            select(DocumentVersion).where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version_number.desc()).limit(1)
        )
        if latest is None:
            raise ValueError(f"Document {document_id} has no uploaded version.")
        if latest.processing_status != "ready":
            raise ValueError(f"Document {document_id} is not ready for analysis.")
        versions.append((document_id, latest.storage_path))
    try:
        response = adapter.analyze(request, versions)
        selected_ids = set(by_id)
        for analysis in response.analyses:
            hit_by_id = {}
            for hit in analysis.retrieval_hits:
                if hit.chunk.document_id not in selected_ids:
                    raise RuntimeError("Pipeline returned evidence outside the selected project corpus.")
                hit_by_id[hit.chunk.id] = hit
                hit.chunk.metadata.pop("source_path", None)
                hit.chunk.metadata["source_filename"] = by_id[hit.chunk.document_id].source_filename
                doc_metadata = hit.chunk.metadata.get("document_metadata")
                if isinstance(doc_metadata, dict):
                    doc_metadata["filename"] = by_id[hit.chunk.document_id].source_filename
            for comparison in analysis.comparisons:
                hit = hit_by_id.get(comparison.evidence_chunk_id)
                if comparison.claim_id != analysis.claim.id or hit is None:
                    raise RuntimeError("Pipeline returned a comparison without its selected claim/evidence pair.")
                if comparison.evidence_quote not in hit.chunk.text:
                    raise RuntimeError("Pipeline returned an evidence quote absent from its source passage.")
        for analysis in response.analyses:
            persist_claim_analysis(session, run, analysis)
        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        run.algorithm_version = adapter.algorithm_version
        session.commit()
        return run, response
    except PipelineUnavailable as exc:
        run.status = "failed"
        run.failure_reason = str(exc)
        run.completed_at = datetime.now(timezone.utc)
        session.commit()
        exc.run_id = run.id
        raise
    except Exception as exc:
        run.status = "failed"
        run.failure_reason = f"Pipeline execution failed: {type(exc).__name__}"
        run.completed_at = datetime.now(timezone.utc)
        session.commit()
        raise


def persist_claim_analysis(session: Session, run: AnalysisRun, analysis: ClaimAnalysis) -> None:
    claim_version = latest_version(session, analysis.claim.document_id)
    if claim_version is not None and session.get(AtomicClaimRecord, analysis.claim.id) is None:
        session.add(AtomicClaimRecord(
            id=analysis.claim.id, document_version_id=claim_version.id, text=analysis.claim.text,
            claim_type=analysis.claim.claim_type.value, structured_scope=analysis.claim.scope.model_dump(mode="json"),
            source_span=analysis.claim.source_span.model_dump(mode="json"),
        ))
    for hit in analysis.retrieval_hits:
        chunk = hit.chunk
        chunk_version = latest_version(session, chunk.document_id)
        record_id = f"{chunk_version.id}:{chunk.id}" if chunk_version is not None else chunk.id
        if chunk_version is not None and session.get(EvidenceChunkRecord, record_id) is None:
            metadata = dict(chunk.metadata)
            metadata.pop("source_path", None)
            metadata["canonical_chunk_id"] = chunk.id
            session.add(EvidenceChunkRecord(
                id=record_id, document_version_id=chunk_version.id, text=chunk.text,
                section=chunk.section_name, page=chunk.page_number, start_offset=chunk.start_offset,
                end_offset=chunk.end_offset, metadata_json=metadata,
            ))
    for comparison in analysis.comparisons:
        session.add(ComparisonResultRecord(
            id=str(uuid4()), analysis_run_id=run.id, claim_id=comparison.claim_id,
            evidence_chunk_id=comparison.evidence_chunk_id, relation=comparison.relation.value,
            confidence=comparison.confidence, explanation=comparison.explanation,
            structured_comparison=comparison.model_dump(mode="json"),
        ))


def latest_version(session: Session, document_id: str) -> DocumentVersion | None:
    return session.scalar(
        select(DocumentVersion).join(Document).where(Document.id == document_id)
        .order_by(DocumentVersion.version_number.desc()).limit(1)
    )
