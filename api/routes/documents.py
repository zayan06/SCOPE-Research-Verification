"""Document upload, version and status endpoints."""

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from scopecheck.contracts import DocumentSummary, DocumentUploadResponse
from api.database.models import Document, DocumentVersion, Project
from api.database.session import get_db
from api.schemas import DocumentDetail, DocumentStatusResponse, DocumentVersionResponse
from api.services.document_storage import UploadProblem, save_upload
from api.services.ingestion import parse_and_store

router = APIRouter(prefix="/api/documents", tags=["documents"])


def current_status(document: Document) -> str:
    latest = max(document.versions, key=lambda v: v.version_number, default=None)
    if latest is None:
        return "pending"
    return "uploaded" if latest.processing_status == "pending" else latest.processing_status


@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(..., description="PDF or DOCX source file"),
    project_id: str = Form(...),
    document_id: str | None = Form(default=None, description="Set to append a new version"),
    title: str | None = Form(default=None),
    session: Session = Depends(get_db),
) -> DocumentUploadResponse:
    if session.get(Project, project_id) is None:
        raise HTTPException(404, detail={"code": "project_not_found", "message": "Project not found."})
    stored_path: Path | None = None
    try:
        document, version = await save_upload(session, project_id=project_id, upload=file, document_id=document_id, title=title)
        stored_path = Path(version.storage_path)
        chunk_count = parse_and_store(session, document, version)
        session.commit()
    except UploadProblem as exc:
        session.rollback()
        raise HTTPException(exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc
    except RuntimeError as exc:
        session.rollback()
        if stored_path is not None:
            stored_path.unlink(missing_ok=True)
        raise HTTPException(503, detail={
            "code": "parser_unavailable",
            "message": "The parser required for this document type is unavailable.",
        }) from exc
    except (ValueError, OSError) as exc:
        session.rollback()
        if stored_path is not None:
            stored_path.unlink(missing_ok=True)
        raise HTTPException(422, detail={
            "code": "document_parse_failed",
            "message": "The uploaded document could not be parsed.",
        }) from exc
    except Exception:
        session.rollback()
        if stored_path is not None:
            stored_path.unlink(missing_ok=True)
        raise
    return DocumentUploadResponse(
        document_id=document.id, filename=document.source_filename, status="ready",
        message=f"Parsed version {version.version_number} into {chunk_count} evidence chunks.",
    )


@router.get("", response_model=list[DocumentSummary])
def list_documents(
    project_id: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_db),
) -> list[DocumentSummary]:
    query = select(Document).options(selectinload(Document.versions)).order_by(Document.created_at.desc())
    if project_id:
        query = query.where(Document.project_id == project_id)
    documents = session.scalars(query).all()
    values = [DocumentSummary(document_id=d.id, filename=d.source_filename, status=current_status(d)) for d in documents]
    return [item for item in values if status_filter is None or item.status == status_filter][:limit]


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(document_id: str, session: Session = Depends(get_db)) -> DocumentDetail:
    document = session.scalar(select(Document).options(selectinload(Document.versions)).where(Document.id == document_id))
    if document is None:
        raise HTTPException(404, detail={"code": "document_not_found", "message": "Document not found."})
    return DocumentDetail(
        document_id=document.id, project_id=document.project_id, title=document.title,
        filename=document.source_filename, document_type=document.document_type, status=current_status(document),
        versions=[DocumentVersionResponse.model_validate(v, from_attributes=True) for v in document.versions],
    )


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
def document_status(document_id: str, session: Session = Depends(get_db)) -> DocumentStatusResponse:
    document = session.scalar(select(Document).options(selectinload(Document.versions)).where(Document.id == document_id))
    if document is None:
        raise HTTPException(404, detail={"code": "document_not_found", "message": "Document not found."})
    latest = max(document.versions, key=lambda v: v.version_number, default=None)
    return DocumentStatusResponse(
        document_id=document.id, status=current_status(document),
        latest_version=DocumentVersionResponse.model_validate(latest, from_attributes=True) if latest else None,
    )
