#!/usr/bin/env python3
"""Run the reproducible, explicitly synthetic SCOPE pipeline demonstration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scopecheck.alignment import ComparatorMode
from scopecheck.contracts import AnalyzeRequest
from scopecheck.pipeline import analyze, serialize_result

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data/samples/development_demo.md"
DOCUMENT_ID = "synthetic-development-demo"
DRAFT = (
    "On dataset CellBench-1, the cobalt catalyst increased reaction yield "
    "by 12% at 80 °C."
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data/outputs/development_demo.json",
        help="where to write structured results",
    )
    args = parser.parse_args()
    request = AnalyzeRequest(draft_text=DRAFT, selected_document_ids=[DOCUMENT_ID])
    runs = {
        mode.value: json.loads(
            serialize_result(
                analyze(request, {DOCUMENT_ID: FIXTURE}, top_k=3, mode=mode)
            )
        )
        for mode in (ComparatorMode.TEXT_ONLY, ComparatorMode.SCOPE_AWARE)
    }
    # Keep the checked-in artifact portable across local checkout locations.
    for result in runs.values():
        for analysis in result["analyses"]:
            for hit in analysis["retrieval_hits"]:
                metadata = hit["chunk"]["metadata"]
                if metadata.get("source_path"):
                    metadata["source_path"] = Path(metadata["source_path"]).resolve().relative_to(ROOT).as_posix()
    artifact = {
        "fixture_type": "synthetic_development_fixture",
        "warning": "Not scientific evidence or benchmark evaluation.",
        "source_document_id": DOCUMENT_ID,
        "source_file": FIXTURE.relative_to(ROOT).as_posix(),
        "draft_claim": DRAFT,
        "runs": runs,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote synthetic development demonstration to {args.output}")
    for mode, result in runs.items():
        analyses = result["analyses"]
        labels = [
            comparison["relation"]
            for analysis in analyses
            for comparison in analysis["comparisons"]
        ]
        print(f"{mode}: status={result['status']}, relationships={labels}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
