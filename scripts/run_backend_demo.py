#!/usr/bin/env python3
"""Run real project, upload, parse, analyze and result API requests locally."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from api import main as main_module
from api.database.models import Base
from api.database.session import get_db, make_engine
from api.main import app
from api.services.analysis import ScopePipelineAdapter

SOURCE_FILE = ROOT / "data/samples/development_demo.md"
CLAIM = "On dataset CellBench-1, the cobalt catalyst increased reaction yield by 12% at 80 °C."


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="scope-api-demo-") as temp_dir:
        root = Path(temp_dir)
        engine = make_engine(f"sqlite:///{root / 'demo.db'}")
        Base.metadata.create_all(engine)
        sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

        def override_db():
            with sessions() as session:
                yield session

        previous_init = main_module.initialize_database
        previous_adapter = app.state.pipeline_adapter
        previous_overrides = dict(app.dependency_overrides)
        old_storage = os.environ.get("SCOPE_STORAGE_DIR")
        old_max = os.environ.get("SCOPE_MAX_UPLOAD_BYTES")
        main_module.initialize_database = lambda: Base.metadata.create_all(engine)
        app.state.pipeline_adapter = ScopePipelineAdapter()
        app.dependency_overrides[get_db] = override_db
        os.environ["SCOPE_STORAGE_DIR"] = str(root / "uploads")
        os.environ["SCOPE_MAX_UPLOAD_BYTES"] = str(1024 * 1024)
        try:
            with TestClient(app) as client:
                project_request = {"name": "Local pipeline demonstration", "description": "Synthetic development fixture"}
                project_response = client.post("/api/projects", json=project_request)
                project_response.raise_for_status()
                project_id = project_response.json()["id"]

                upload_request = {
                    "project_id": project_id,
                    "filename": SOURCE_FILE.name,
                    "content_type": "text/markdown",
                }
                upload_response = client.post(
                    "/api/documents",
                    data={"project_id": project_id},
                    files={"file": (SOURCE_FILE.name, SOURCE_FILE.read_bytes(), "text/markdown")},
                )
                upload_response.raise_for_status()
                document_id = upload_response.json()["document_id"]

                analyze_request = {"draft_text": CLAIM, "selected_document_ids": [document_id]}
                analyze_response = client.post("/api/analyze", json=analyze_request)
                analyze_response.raise_for_status()
                runs = client.get(f"/api/projects/{project_id}/analysis-runs")
                runs.raise_for_status()
                run_id = runs.json()[0]["id"]
                results_response = client.get(f"/api/analysis-runs/{run_id}/results")
                results_response.raise_for_status()

                artifact = {
                    "fixture_notice": "Synthetic development text; not scientific evidence or benchmark evaluation.",
                    "requests": {
                        "create_project": project_request,
                        "upload_document": upload_request,
                        "analyze": analyze_request,
                    },
                    "responses": {
                        "create_project": project_response.json(),
                        "upload_document": upload_response.json(),
                        "analyze": analyze_response.json(),
                        "analysis_results": results_response.json(),
                    },
                }
        finally:
            main_module.initialize_database = previous_init
            app.state.pipeline_adapter = previous_adapter
            app.dependency_overrides.clear()
            app.dependency_overrides.update(previous_overrides)
            if old_storage is None:
                os.environ.pop("SCOPE_STORAGE_DIR", None)
            else:
                os.environ["SCOPE_STORAGE_DIR"] = old_storage
            if old_max is None:
                os.environ.pop("SCOPE_MAX_UPLOAD_BYTES", None)
            else:
                os.environ["SCOPE_MAX_UPLOAD_BYTES"] = old_max
            engine.dispose()

    output = ROOT / "data/outputs/backend_demo.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Created project, parsed upload, and ran real pipeline; output: {output}")
    print(json.dumps({
        "upload_status": artifact["responses"]["upload_document"]["status"],
        "analysis_status": artifact["responses"]["analyze"]["status"],
        "relation": artifact["responses"]["analyze"]["analyses"][0]["comparisons"][0]["relation"],
        "stored_exact_quote": artifact["responses"]["analysis_results"]["results"][0]["evidence_quote"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
