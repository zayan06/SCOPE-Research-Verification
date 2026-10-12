# Stage A core integration handoff

## Branches and commits

Integrated on `integrate/scope`, starting at foundation commit
`358dfe9675aaf05a2d5040ef26e2b6b92c5a7ebe`, in the requested order:

| Branch | Implementation commit | Integration merge commit |
| --- | --- | --- |
| `feat/ingestion` | `96c483adc0ebb539624c67db39344f280532d1f1` | `0ab8267` |
| `feat/claims` | `46261acd57fa90af9b0b7bda55926f6459e80229` | `4684b9c` |
| `feat/retrieval` | `399c6a1c09e81697249ebfb0c8e7151789098e57` | `45b0d00` |
| `feat/alignment` | `71e7b9561fbcbe07b7a413a6b09c2a35803292f0` plus refinement `7341fca5ebcbc52d482bc523c7cf0f66ea1fc473` | `4af2e83` |
| `feat/evaluation` | `7ac6a16c0e74f3ef802e68878f63b47e1bcd6c5e` | `88ae82c` |

Backend (`feat/backend`) and frontend (`feat/frontend`) were not merged.
Integration merge commits preserve the workstream histories; no history was
rewritten.

## Integration changes

- Implemented `src/scopecheck/pipeline.py` to orchestrate parsing, claim
  extraction, evidence indexing, selected-document retrieval, and comparison.
- Added `scripts/run_demo.py`, a wholly synthetic source fixture, and generated
  output at `data/outputs/development_demo.json`.
- Added `scripts/run_development_checks.py` and generated output at
  `data/outputs/development_checks.json`.
- Added `tests/test_pipeline.py` for pipeline flow, source filtering, empty and
  invalid inputs, direct and extracted claims, both comparator modes, quotes,
  and JSON serialization.
- Corrected multiword outcome extraction so `reaction yield` is not truncated
  to `reaction`; added a regression check.
- Replaced the foundation README with current Stage A behavior, install/demo/
  test/evaluation instructions, limitations, and the Stage B boundary.

## Public pipeline interfaces

```python
analyze(
    request: AnalyzeRequest,
    source_documents: Mapping[str, str | Path],
    *, top_k: int = 5,
    mode: ComparatorMode | str = ComparatorMode.SCOPE_AWARE,
    retrieval_method: RetrievalMethod | str = RetrievalMethod.TFIDF,
) -> AnalyzeResponse

analyze_claims(
    claims: Sequence[AtomicClaim],
    source_documents: Mapping[str, str | Path],
    *, selected_document_ids: Sequence[str] | None = None,
    top_k: int = 5,
    mode: ComparatorMode | str = ComparatorMode.SCOPE_AWARE,
    retrieval_method: RetrievalMethod | str = RetrievalMethod.TFIDF,
) -> AnalyzeResponse

serialize_result(response: AnalyzeResponse, *, indent: int = 2) -> str
```

`source_documents` maps stable source document IDs to local paths. `analyze`
extracts claims from the request draft and never indexes that draft. Direct
claims are also excluded from the index by their `document_id`. The selected
ID allow-list is applied before retrieval. An empty retrieval result is
represented by empty hit/comparison arrays and response status
`insufficient_evidence` (or `partial_insufficient_evidence` if only some
claims have hits). Unsupported paths and formats raise clear errors.

## Contracts and dependencies

All modules use the canonical models in `src/scopecheck/contracts.py`:
`SourceSpan`, `EvidenceChunk`, `ScientificScope`, `AtomicClaim`, `RetrievalHit`,
`DimensionComparison`, and `ComparisonResult`. Existing pydantic validation
and JSON enum serialization are preserved. Evidence quotes are the exact full
retrieved chunk text, and IDs/offsets remain attached to source chunks.

Core parsing, extraction, BM25, alignment, and evaluation use Python and
Pydantic. TF-IDF requires `scikit-learn>=1.4,<2`, installed separately for the
baseline. PDF requires optional Docling; DOCX requires optional `python-docx`;
Gemini and dense retrieval adapters remain optional. The local pipeline needs
no credentials.

## Verification results

Using the prepared Python 3.12 environment with scikit-learn installed:

- `python -m pytest -q` — **87 passed, 0 failed**, one Starlette/httpx
  deprecation warning.
- `python scripts/run_demo.py` — completed in text-only and scope-aware modes;
  both returned `support` for the identical synthetic passage. Output:
  `data/outputs/development_demo.json`.
- `python scripts/run_development_checks.py` — completed on 6 synthetic
  development pairs. Comparator results: text-only accuracy **0.667**,
  macro-F1 **0.611**; scope-aware accuracy **0.833**, macro-F1 **0.778**.
  Retrieval results: TF-IDF MRR **1.000**, Recall@1 **1.000**; BM25 MRR
  **1.000**, Recall@1 **1.000**. Output:
  `data/outputs/development_checks.json`.

These are fabricated software-development fixture metrics only. No authentic
scientific dataset or human-reviewed SCOPE labels were available; scientific
benchmark evaluation remains pending. The development script evaluates both
comparator modes on identical pairs and both retrieval methods on identical
queries and relevance judgments.

## Known limitations

- Independent workstream unit tests are synthetic software checks, not
  scientific validity evidence. Rule-based English claim/scope extraction can
  miss aliases, paraphrases, negation nuance, and complex study designs.
- Confidence is heuristic, not calibrated. Retrieval scores are relevance
  signals. All relation labels require researcher review in source context.
- Real PDF parsing and quality, OCR, PDF page coordinates, and DOCX conversion
  have not been verified with representative papers.
- The demo text is explicitly synthetic. There are no authentic benchmark
  metrics, no persistent index, and no production security or multi-user
  isolation.
- Only the core Python pipeline is implemented here. The HTTP analysis routes,
  document persistence, and React application are separate workstreams.

## Stage B integration instructions

1. Merge or cherry-pick this `integrate/scope` result into the backend's
   integration branch after review; do not assume the backend branch contains
   these changes.
2. Resolve each authorized document ID to a local stored path in the backend,
   then call `analyze(AnalyzeRequest(...), source_documents=...)`.
3. Pass only request-selected IDs to the mapping; keep authorization and
   tenant/user filtering in the storage boundary. The core library enforces
   selection against the mapping but does not implement user authorization.
4. Return the canonical `AnalyzeResponse` serialization. Preserve document IDs,
   chunk IDs, source offsets, exact quotes, unknown scope statuses, and empty
   evidence results.
5. Do not label the outputs scientific findings or calibrated probabilities.
   Keep scientific benchmark evaluation pending until licensed data and
   human-reviewed labels are available.
6. Keep the current HTTP specification status accurate until its routes are
   implemented and tested.

## Integration commit

The completed Stage A pipeline, demo, development checks, regression coverage,
and README are committed as `854ee19c04816adba75116297a4292821b0492dc` on
`integrate/scope`. This handoff record follows as a documentation-only commit.
