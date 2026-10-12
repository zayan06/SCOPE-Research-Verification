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
import api.main as main_module
from api.main import app
from api.services.analysis import ScopePipelineAdapter, UnavailablePipelineAdapter


@pytest.fixture
def client(tmp_path, monkeypatch) -> Generator[TestClient, None, None]:
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(main_module, "initialize_database", lambda: Base.metadata.create_all(engine))
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


def upload(
    client: TestClient,
    project_id: str,
    filename: str = "paper.md",
    content: bytes = b"On dataset Alpha, Model A increased accuracy by 5%.",
):
    media_type = "text/markdown" if filename.endswith((".md", ".markdown")) else "application/octet-stream"
    return client.post(
        "/api/documents",
        data={"project_id": project_id},
        files={"file": (filename, content, media_type)},
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
    response = upload(client, project_id, "../../study.md")
    assert response.status_code == 201
    result = response.json()
    assert result["status"] == "ready"
    assert "1 evidence chunks" in result["message"]
    detail = client.get(f"/api/documents/{result['document_id']}").json()
    assert detail["versions"][0]["version_number"] == 1
    stored = list((tmp_path / "uploads").iterdir())
    assert len(stored) == 1
    assert stored[0].name != "study.pdf"
    assert client.get(f"/api/documents/{result['document_id']}/status").json()["status"] == "ready"


def test_invalid_empty_and_oversized_document_uploads(client: TestClient) -> None:
    project_id = create_project(client)
    unsupported = upload(client, project_id, "notes.csv", b"text")
    assert unsupported.status_code == 415
    assert "TXT, and Markdown" in unsupported.json()["detail"]["message"]
    assert upload(client, project_id, "empty.md", b"").json()["detail"]["code"] == "empty_file"
    too_large = upload(client, project_id, "large.md", b"x" * 129)
    assert too_large.status_code == 413
    assert too_large.json()["detail"]["code"] == "file_too_large"
    assert client.get("/api/documents").json() == []


def test_document_versioning_and_list_filter(client: TestClient) -> None:
    project_id = create_project(client)
    first = upload(client, project_id).json()["document_id"]
    second = client.post(
        "/api/documents", data={"project_id": project_id, "document_id": first},
        files={"file": ("revision.md", b"On dataset Beta, Model B improved accuracy by 2%.", "text/markdown")},
    )
    assert second.status_code == 201
    detail = client.get(f"/api/documents/{first}").json()
    assert [v["version_number"] for v in detail["versions"]] == [1, 2]
    assert detail["document_type"] == "md"
    assert len(client.get("/api/documents", params={"status": "ready"}).json()) == 1


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
        chunk = session.query(EvidenceChunkRecord).filter(
            EvidenceChunkRecord.id.endswith(":chunk-1")
        ).one()
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
        files={"file": ("bad.csv", b"bad", "text/csv")},
    )
    assert response.status_code == 415
    assert client.get("/api/documents").json() == []


def test_real_pipeline_end_to_end_with_sqlite(client: TestClient) -> None:
    """Exercise upload parsing, persistence, retrieval and alignment without mocks."""
    app.state.pipeline_adapter = ScopePipelineAdapter()
    project_id = create_project(client)
    exact_source = "On dataset Alpha, Model A increased accuracy by 5%."
    uploaded = upload(client, project_id, "paper.md", exact_source.encode("utf-8"))
    assert uploaded.status_code == 201
    document_id = uploaded.json()["document_id"]
    assert uploaded.json()["status"] == "ready"

    with app.state.test_session() as session:
        records = session.query(EvidenceChunkRecord).all()
        assert len(records) == 1
        assert records[0].text == exact_source
        assert records[0].document_version_id
        assert records[0].metadata_json["canonical_chunk_id"].startswith(document_id + ":")
        assert "source_path" not in records[0].metadata_json

    # A same-project document outside the selected allow-list must not enter
    # the evidence hits, even when it discusses the same outcome.
    other_document_id = upload(
        client,
        project_id,
        "other.md",
        b"On dataset Alpha, Model A decreased accuracy by 5%.",
    ).json()["document_id"]

    analyzed = client.post("/api/analyze", json={
        "draft_text": exact_source,
        "selected_document_ids": [document_id],
    })
    assert analyzed.status_code == 200, analyzed.text
    body = analyzed.json()
    assert body["status"] == "completed"
    assert len(body["analyses"]) == 1
    analysis = body["analyses"][0]
    assert analysis["claim"]["document_id"] == "draft"
    assert analysis["claim"]["source_span"]["exact_text"] == exact_source
    assert analysis["retrieval_hits"][0]["chunk"]["document_id"] == document_id
    assert analysis["retrieval_hits"][0]["chunk"]["metadata"]["source_filename"] == "paper.md"
    assert all(hit["chunk"]["document_id"] != other_document_id for hit in analysis["retrieval_hits"])
    assert analysis["retrieval_hits"][0]["chunk"]["start_offset"] == 0
    assert analysis["retrieval_hits"][0]["chunk"]["end_offset"] == len(exact_source)
    assert analysis["comparisons"][0]["relation"] == "support"
    assert analysis["comparisons"][0]["evidence_quote"] == exact_source
    assert "source_path" not in analysis["retrieval_hits"][0]["chunk"]["metadata"]

    run_id = client.get(f"/api/projects/{project_id}/analysis-runs").json()[0]["id"]
    stored = client.get(f"/api/analysis-runs/{run_id}/results")
    assert stored.status_code == 200
    assert stored.json()["results"][0]["evidence_quote"] == exact_source
    assert stored.json()["results"][0]["evidence_chunk_id"] == analysis["retrieval_hits"][0]["chunk"]["id"]


def test_cross_project_document_selection_is_rejected(client: TestClient) -> None:
    app.state.pipeline_adapter = ScopePipelineAdapter()
    project_a, project_b = create_project(client), create_project(client)
    doc_a = upload(client, project_a).json()["document_id"]
    doc_b = upload(client, project_b).json()["document_id"]
    response = client.post("/api/analyze", json={
        "draft_text": "Model A improves accuracy.",
        "selected_document_ids": [doc_a, doc_b],
    })
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_analysis_selection"
    assert client.get(f"/api/projects/{project_a}/analysis-runs").json() == []
    assert client.get(f"/api/projects/{project_b}/analysis-runs").json() == []


def test_parse_failure_does_not_register_partial_document(client: TestClient) -> None:
    project_id = create_project(client)
    response = upload(client, project_id, "broken.md", b"\xff\xfe")
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "document_parse_failed"
    assert client.get("/api/documents", params={"project_id": project_id}).json() == []
