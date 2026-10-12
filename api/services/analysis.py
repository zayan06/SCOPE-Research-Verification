"""Analysis orchestration and replaceable integrated-pipeline boundary."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

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


def create_run(session: Session, request: AnalyzeRequest, adapter: PipelineAdapter) -> tuple[AnalysisRun, AnalyzeResponse]:
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
        versions.append((document_id, latest.storage_path))
    try:
        response = adapter.analyze(request, versions)
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
        if chunk_version is not None and session.get(EvidenceChunkRecord, chunk.id) is None:
            session.add(EvidenceChunkRecord(
                id=chunk.id, document_version_id=chunk_version.id, text=chunk.text,
                section=chunk.section_name, page=chunk.page_number, start_offset=chunk.start_offset,
                end_offset=chunk.end_offset, metadata_json=chunk.metadata,
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
