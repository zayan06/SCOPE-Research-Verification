"""Parse uploaded document versions and persist their traceable chunks."""

from __future__ import annotations

from scopecheck.ingestion import parse_document
from sqlalchemy.orm import Session

from api.database.models import Document, DocumentVersion, EvidenceChunkRecord


def parse_and_store(
    session: Session, document: Document, version: DocumentVersion
) -> int:
    """Parse one stored version, save chunks, and mark processing complete."""
    chunks = parse_document(version.storage_path, document_id=document.id)
    for chunk in chunks:
        metadata = dict(chunk.metadata)
        # API responses need stable document provenance, never server paths.
        metadata.pop("source_path", None)
        metadata["source_filename"] = document.source_filename
        document_metadata = metadata.get("document_metadata")
        if isinstance(document_metadata, dict):
            document_metadata["filename"] = document.source_filename
        metadata["canonical_chunk_id"] = chunk.id
        record_id = f"{version.id}:{chunk.id}"
        session.add(EvidenceChunkRecord(
            id=record_id,
            document_version_id=version.id,
            text=chunk.text,
            section=chunk.section_name,
            page=chunk.page_number,
            start_offset=chunk.start_offset,
            end_offset=chunk.end_offset,
            metadata_json=metadata,
        ))
    version.processing_status = "ready"
    version.failure_reason = None
    session.flush()
    return len(chunks)
