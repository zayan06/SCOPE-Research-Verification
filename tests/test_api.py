from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from scopecheck.contracts import (
    AnalyzeResponse, AtomicClaim, ClaimAnalysis, ClaimType, ComparisonResult,
    DimensionStatus, EvidenceChunk, ExtractionMethod, RecommendedAction,
    Relation, RetrievalHit, RetrievalMethod, ScientificScope, SourceSpan,
)
from api.database.models import AnalysisRun, Base, EvidenceChunkRecord
from api.database.session import get_db, make_engine
from api.main import app


@pytest.fixture
def client(tmp_path, monkeypatch) -> Generator[TestClient, None, None]:
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    app.state.test_session = sessions

    def override_db() -> Generator[Session, None, None]:
        session = sessions()
        try:
            yield session
        finally:
            session.close()

    monkeypatch.setenv("SCOPE_STORAGE_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("SCOPE_MAX_UPLOAD_BYTES", "128")
    app.dependency_overrides[get_db] = override_db
    app.state.pipeline_adapter = __import__("api.services.analysis", fromlist=["UnavailablePipelineAdapter"]).UnavailablePipelineAdapter()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


def create_project(client: TestClient) -> str:
    response = client.post("/api/projects", json={"name": "Study"})
    assert response.status_code == 201
    return response.json()["id"]


def upload(client: TestClient, project_id: str, filename: str = "paper.pdf", content: bytes = b"%PDF-1.7 sample"):
    return client.post(
        "/api/documents",
        data={"project_id": project_id},
        files={"file": (filename, content, "application/pdf")},
    )


def test_health_and_openapi_documentation(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0", "mode": "local_development"}
    schema = client.get("/api/openapi.json")
    assert schema.status_code == 200
    assert "/api/analyze" in schema.json()["paths"]


def test_project_create_list_get_patch_and_database_persistence(client: TestClient) -> None:
    project_id = create_project(client)
    assert client.get("/api/projects").json()[0]["id"] == project_id
    assert client.get(f"/api/projects/{project_id}").json()["name"] == "Study"
    patched = client.patch(f"/api/projects/{project_id}", json={"description": "Literature review"})
    assert patched.status_code == 200
    assert patched.json()["description"] == "Literature review"


def test_invalid_project_id_returns_stable_error(client: TestClient) -> None:
    response = client.get("/api/projects/missing")
    assert response.status_code == 404
    assert response.json()["code"] == "project_not_found"


def test_document_upload_status_and_safe_file_persistence(client: TestClient, tmp_path) -> None:
    project_id = create_project(client)
    response = upload(client, project_id, "../../study.pdf")
    assert response.status_code == 201
    result = response.json()
    assert result["status"] == "uploaded"
    assert "parsing is pending" in result["message"]
    detail = client.get(f"/api/documents/{result['document_id']}").json()
    assert detail["versions"][0]["version_number"] == 1
    stored = list((tmp_path / "uploads").iterdir())
    assert len(stored) == 1
    assert stored[0].name != "study.pdf"
    assert client.get(f"/api/documents/{result['document_id']}/status").json()["status"] == "uploaded"


def test_invalid_empty_and_oversized_document_uploads(client: TestClient) -> None:
    project_id = create_project(client)
    assert upload(client, project_id, "notes.txt", b"text").status_code == 415
    assert upload(client, project_id, "empty.pdf", b"").json()["detail"]["code"] == "empty_file"
    too_large = upload(client, project_id, "large.pdf", b"x" * 129)
    assert too_large.status_code == 413
    assert too_large.json()["detail"]["code"] == "file_too_large"
    assert client.get("/api/documents").json() == []


def test_document_versioning_and_list_filter(client: TestClient) -> None:
    project_id = create_project(client)
    first = upload(client, project_id).json()["document_id"]
    second = client.post(
        "/api/documents", data={"project_id": project_id, "document_id": first},
        files={"file": ("revision.docx", b"PK docx bytes", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert second.status_code == 201
    detail = client.get(f"/api/documents/{first}").json()
    assert [v["version_number"] for v in detail["versions"]] == [1, 2]
    assert detail["document_type"] == "docx"
    assert len(client.get("/api/documents", params={"status": "uploaded"}).json()) == 1


def _analysis_response(document_id: str) -> AnalyzeResponse:
    claim = AtomicClaim(
        id="claim-1", text="The treatment improves outcome.", document_id="draft",
        claim_type=ClaimType.EMPIRICAL, scope=ScientificScope(),
        source_span=SourceSpan(document_id="draft", exact_text="The treatment improves outcome."),
        extraction_method=ExtractionMethod.HUMAN,
    )
    chunk = EvidenceChunk(id="chunk-1", document_id=document_id, text="The treatment improved outcome.")
    comparison = ComparisonResult(
        claim_id="claim-1", evidence_chunk_id="chunk-1", relation=Relation.SUPPORT,
        confidence=0.8, scope_compatibility=DimensionStatus.UNKNOWN, dimension_comparisons=[],
        explanation="The passage reports an improvement.", evidence_quote="The treatment improved outcome.",
        recommended_action=RecommendedAction.REVIEW_SOURCE_CONTEXT, model_version="test-1",
    )
    return AnalyzeResponse(analyses=[ClaimAnalysis(
        claim=claim, retrieval_hits=[RetrievalHit(chunk=chunk, score=0.9, rank=1, retrieval_method=RetrievalMethod.TFIDF)],
        comparisons=[comparison],
    )], status="completed")


class FakePipeline:
    algorithm_version = "test-pipeline-1"

    def __init__(self):
        self.called_with = None

    def analyze(self, request, document_paths):
        self.called_with = (request, document_paths)
        return _analysis_response(request.selected_document_ids[0])


def test_empty_analysis_request_is_rejected(client: TestClient) -> None:
    response = client.post("/api/analyze", json={"draft_text": " ", "selected_document_ids": ["x"]})
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)  # Pydantic rejects stripped empty text.
    assert client.post("/api/analyze", json={"draft_text": "draft", "selected_document_ids": []}).status_code == 422


def test_analysis_pipeline_invocation_and_result_storage(client: TestClient) -> None:
    project_id = create_project(client)
    document_id = upload(client, project_id).json()["document_id"]
    adapter = FakePipeline()
    app.state.pipeline_adapter = adapter
    response = client.post("/api/analyze", json={"draft_text": "A claim.", "selected_document_ids": [document_id]})
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert adapter.called_with[1][0][0] == document_id
    runs = client.get(f"/api/projects/{project_id}/analysis-runs").json()
    assert len(runs) == 1 and runs[0]["status"] == "completed"
    result = client.get(f"/api/analysis-runs/{runs[0]['id']}/results").json()
    assert result["results"][0]["evidence_quote"] == "The treatment improved outcome."
    assert result["results"][0]["relation"] == "support"
    # Retrieved evidence keeps its source document version in relational storage.
    with app.state.test_session() as session:
        chunk = session.get(EvidenceChunkRecord, "chunk-1")
        assert chunk is not None and chunk.document_version_id


def test_unavailable_adapter_persists_failed_run(client: TestClient) -> None:
    project_id = create_project(client)
    document_id = upload(client, project_id).json()["document_id"]
    response = client.post("/api/analyze", json={"draft_text": "A claim.", "selected_document_ids": [document_id]})
    assert response.status_code == 503
    run_id = response.json()["detail"]["analysis_run_id"]
    run = client.get(f"/api/analysis-runs/{run_id}").json()
    assert run["status"] == "failed"
    assert "not installed" in run["failure_reason"]


def test_invalid_analysis_document_and_run_ids(client: TestClient) -> None:
    response = client.post("/api/analyze", json={"draft_text": "claim", "selected_document_ids": ["missing"]})
    assert response.status_code == 422
    assert client.get("/api/analysis-runs/missing").status_code == 404
    assert client.get("/api/analysis-runs/missing/results").status_code == 404


def test_pipeline_failure_is_persisted(client: TestClient) -> None:
    project_id = create_project(client)
    document_id = upload(client, project_id).json()["document_id"]

    class BrokenPipeline:
        algorithm_version = "test-broken"

        def analyze(self, request, document_paths):
            raise RuntimeError("private details are not exposed")

    app.state.pipeline_adapter = BrokenPipeline()
    response = client.post("/api/analyze", json={"draft_text": "claim", "selected_document_ids": [document_id]})
    assert response.status_code == 500
    assert "private details" not in response.text
    run = client.get(f"/api/projects/{project_id}/analysis-runs").json()[0]
    assert run["status"] == "failed"
    assert run["failure_reason"] == "Pipeline execution failed: RuntimeError"


def test_upload_validation_rolls_back_document_rows(client: TestClient) -> None:
    project_id = create_project(client)
    response = client.post(
        "/api/documents", data={"project_id": project_id},
        files={"file": ("bad.txt", b"bad", "text/plain")},
    )
    assert response.status_code == 415
    assert client.get("/api/documents").json() == []
