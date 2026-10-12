"""Backend request/response DTOs outside the canonical scientific contracts."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)


class ProjectPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)


class ORMResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProjectResponse(ORMResponse):
    id: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class DocumentVersionResponse(ORMResponse):
    id: str
    version_number: int
    checksum: str
    processing_status: str
    failure_reason: str | None
    created_at: datetime


class DocumentDetail(BaseModel):
    document_id: str
    project_id: str
    title: str
    filename: str
    document_type: str
    status: str
    versions: list[DocumentVersionResponse]


class DocumentStatusResponse(BaseModel):
    document_id: str
    status: str
    latest_version: DocumentVersionResponse | None


class AnalysisRunResponse(ORMResponse):
    id: str
    project_id: str
    input_claim: str
    corpus_selection: dict
    algorithm_version: str
    status: str
    created_at: datetime
    completed_at: datetime | None
    failure_reason: str | None


class AnalysisResultsResponse(BaseModel):
    analysis_run_id: str
    status: str
    results: list[dict]


class ErrorEnvelope(BaseModel):
    code: str
    message: str
    details: dict | None = None
