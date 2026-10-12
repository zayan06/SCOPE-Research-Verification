"""Analysis submission and persisted run-history endpoints."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from scopecheck.contracts import AnalyzeCorpusRequest, AnalyzeCorpusResponse, AnalyzeRequest, AnalyzeResponse
from api.database.models import AnalysisRun, ComparisonResultRecord, Document, Project
from api.database.session import get_db
from api.schemas import AnalysisResultsResponse, AnalysisRunResponse
from api.services.analysis import PipelineUnavailable, create_run

router = APIRouter(tags=["analysis"])


@router.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(body: AnalyzeRequest, request: Request, session: Session = Depends(get_db)) -> AnalyzeResponse:
    if not body.draft_text.strip():
        raise HTTPException(422, detail={"code": "empty_draft", "message": "draft_text must contain non-whitespace text."})
    adapter = request.app.state.pipeline_adapter
    try:
        _run, response = create_run(session, body, adapter)
        return response
    except ValueError as exc:
        session.rollback()
        raise HTTPException(422, detail={"code": "invalid_analysis_selection", "message": str(exc)}) from exc
    except PipelineUnavailable as exc:
        raise HTTPException(503, detail={"code": "pipeline_unavailable", "message": str(exc), "analysis_run_id": getattr(exc, "run_id", None)}) from exc
    except Exception as exc:
        raise HTTPException(500, detail={"code": "analysis_failed", "message": "The analysis pipeline failed."}) from exc


@router.post("/api/analyze-corpus", response_model=AnalyzeCorpusResponse, status_code=status.HTTP_202_ACCEPTED)
def analyze_corpus(body: AnalyzeCorpusRequest, request: Request, session: Session = Depends(get_db)) -> AnalyzeCorpusResponse:
    documents = session.scalars(select(Document).where(Document.id.in_(body.corpus_document_ids))).all()
    ids = {document.id for document in documents}
    if len(ids) != len(set(body.corpus_document_ids)):
        raise HTTPException(422, detail={"code": "invalid_corpus_selection", "message": "One or more corpus documents do not exist."})
    projects = {document.project_id for document in documents}
    if len(projects) != 1:
        raise HTTPException(422, detail={"code": "invalid_corpus_selection", "message": "Corpus documents must belong to one project."})
    adapter = request.app.state.pipeline_adapter
    run = AnalysisRun(
        id=str(uuid4()), project_id=next(iter(projects)), input_claim=f"benchmark:{body.benchmark_id}",
        corpus_selection={"benchmark_id": body.benchmark_id, "document_ids": body.corpus_document_ids},
        algorithm_version=adapter.algorithm_version, status="pending",
        failure_reason="Corpus evaluation adapter is not connected.",
    )
    session.add(run)
    session.commit()
    corpus_method = getattr(adapter, "analyze_corpus", None)
    if corpus_method is None:
        run.status = "failed"
        run.failure_reason = "The integrated SCOPE corpus evaluation adapter is not installed."
        run.completed_at = datetime.now(timezone.utc)
        session.commit()
        raise HTTPException(503, detail={"code": "pipeline_unavailable", "message": run.failure_reason})
    try:
        result = corpus_method(body.benchmark_id, body.corpus_document_ids)
        run.status = result.status
        run.completed_at = datetime.now(timezone.utc)
        session.commit()
        return result
    except Exception as exc:
        run.status = "failed"
        run.failure_reason = f"Corpus evaluation failed: {type(exc).__name__}"
        run.completed_at = datetime.now(timezone.utc)
        session.commit()
        raise HTTPException(500, detail={"code": "analysis_failed", "message": "Corpus evaluation failed."}) from exc


@router.get("/api/analysis-runs/{run_id}", response_model=AnalysisRunResponse)
def get_analysis_run(run_id: str, session: Session = Depends(get_db)) -> AnalysisRun:
    run = session.get(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(404, detail={"code": "analysis_run_not_found", "message": "Analysis run not found."})
    return run


@router.get("/api/projects/{project_id}/analysis-runs", response_model=list[AnalysisRunResponse])
def list_analysis_runs(project_id: str, limit: int = 50, session: Session = Depends(get_db)) -> list[AnalysisRun]:
    if not 1 <= limit <= 200:
        raise HTTPException(422, detail={"code": "invalid_limit", "message": "limit must be between 1 and 200."})
    if session.get(Project, project_id) is None:
        raise HTTPException(404, detail={"code": "project_not_found", "message": "Project not found."})
    return list(session.scalars(select(AnalysisRun).where(AnalysisRun.project_id == project_id).order_by(AnalysisRun.created_at.desc()).limit(limit)).all())


@router.get("/api/analysis-runs/{run_id}/results", response_model=AnalysisResultsResponse)
def get_analysis_results(run_id: str, session: Session = Depends(get_db)) -> AnalysisResultsResponse:
    run = session.get(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(404, detail={"code": "analysis_run_not_found", "message": "Analysis run not found."})
    rows = session.scalars(select(ComparisonResultRecord).where(ComparisonResultRecord.analysis_run_id == run_id)).all()
    return AnalysisResultsResponse(analysis_run_id=run_id, status=run.status, results=[row.structured_comparison for row in rows])
