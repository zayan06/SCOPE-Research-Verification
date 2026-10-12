"""Safe local file storage and document version creation."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.database.models import Document, DocumentVersion

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".markdown"}
DEFAULT_MAX_UPLOAD_BYTES = 25 * 1024 * 1024


class UploadProblem(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def upload_limit() -> int:
    try:
        limit = int(os.getenv("SCOPE_MAX_UPLOAD_BYTES", str(DEFAULT_MAX_UPLOAD_BYTES)))
    except ValueError as exc:
        raise RuntimeError("SCOPE_MAX_UPLOAD_BYTES must be an integer") from exc
    if limit < 1:
        raise RuntimeError("SCOPE_MAX_UPLOAD_BYTES must be positive")
    return limit


def storage_root() -> Path:
    root = Path(os.getenv("SCOPE_STORAGE_DIR", "./data/uploads")).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


async def save_upload(
    session: Session,
    *,
    project_id: str,
    upload: UploadFile,
    document_id: str | None = None,
    title: str | None = None,
) -> tuple[Document, DocumentVersion]:
    original = Path(upload.filename or "").name
    suffix = Path(original).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise UploadProblem("unsupported_file_type", "Supported formats are PDF, DOCX, TXT, and Markdown.", 415)
    limit = upload_limit()
    root = storage_root()
    generated_name = f"{uuid4().hex}{suffix}"
    destination = root / generated_name
    hasher = hashlib.sha256()
    size = 0
    try:
        with destination.open("xb") as output:
            while data := await upload.read(1024 * 1024):
                size += len(data)
                if size > limit:
                    raise UploadProblem("file_too_large", f"Upload exceeds the configured {limit}-byte limit.", 413)
                hasher.update(data)
                output.write(data)
        if size == 0:
            raise UploadProblem("empty_file", "The uploaded file is empty.", 400)

        if document_id:
            document = session.get(Document, document_id)
            if document is None:
                raise UploadProblem("document_not_found", "The requested document does not exist.", 404)
            if document.project_id != project_id:
                raise UploadProblem("project_mismatch", "The document does not belong to the selected project.", 409)
            number = max((version.version_number for version in document.versions), default=0) + 1
            document.source_filename = original
            document.document_type = suffix[1:]
            if title:
                document.title = title
        else:
            document = Document(
                id=str(uuid4()), project_id=project_id, title=(title or Path(original).stem)[:500],
                document_type=suffix[1:], source_filename=original,
            )
            session.add(document)
            number = 1
        version = DocumentVersion(
            id=str(uuid4()), document_id=document.id, version_number=number,
            storage_path=str(destination), checksum=hasher.hexdigest(), processing_status="pending",
        )
        session.add(version)
        session.flush()
        return document, version
    except Exception:
        destination.unlink(missing_ok=True)
        raise
