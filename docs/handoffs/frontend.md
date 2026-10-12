# Frontend handoff

## Workstream and branch

- Workstream: Agent 7 — React/TypeScript frontend
- Branch: `feat/frontend`
- Latest frontend implementation commit: `d1c116f612315e0d5f0748492bb9c5a2462f99c0`
- The handoff itself is committed in a follow-on documentation commit on this branch.

## Screens and behavior

- Project overview with project selection/creation, document and finding counts, recent activity, and relationship summary.
- Document library with draft/source filters, text search, metadata panel, empty/loading states, and PDF/DOCX upload dialog.
- Three-panel analysis workspace with claim selection, passage switching, exact quote, provenance, relationship/confidence, human review controls, scope comparison table, and lightweight evidence path.
- Results overview with relationship, priority, source, and review-state filters and source-passage preview.
- Analysis history view.
- Responsive navigation and stacked analysis panels on smaller screens.
- Synthetic examples are labeled as demo data. The example source names are synthetic and contain no authors, publication years, or page citations.

## Public interfaces and API expectations

`web/src/contracts.ts` mirrors the relevant shared Pydantic contracts, including `DocumentSummary`, `DocumentUploadResponse`, `AnalyzeRequest`, `AnalyzeResponse`, `ClaimAnalysis`, `ComparisonResult`, `DimensionComparison`, `ScientificScope`, and explicit `ScopeValue` unknown states.

`web/src/api.ts` exposes typed calls for:

- `GET /api/health`
- `GET /api/documents`
- `POST /api/documents` as multipart field `file` with upload progress
- `POST /api/analyze` with `draft_text` and nonempty `selected_document_ids`

The analysis UI preserves claim IDs, evidence chunk IDs, exact evidence quotes, relation, confidence, scope compatibility, dimension explanations, recommendation, and model version. Section/page labels are shown only when returned by the evidence chunk.

## Demo and live modes

- The default mode is demo. A persistent banner labels all sample data as synthetic.
- Demo project creation, uploads, analysis examples, notes, and review labels remain in memory for the current page session. Demo upload does not transmit file bytes; processing and analysis are simulated.
- Live mode calls the API. It displays request failures and provides a user-controlled button to enter demo mode; it never replaces a failed live response with sample data.
- `VITE_API_BASE_URL` configures the API origin. With no base URL, development requests use Vite's `/api` proxy to `http://127.0.0.1:8000`.
- Set `VITE_API_MODE=live` to start in live mode. `web/.env.example` documents the settings.

## Dependencies

Runtime: React 18 and React DOM 18.

Development/build: Vite 6, TypeScript 5, Tailwind CSS 3, PostCSS, Vitest 2, jsdom, and Testing Library. No icon, routing, or graph dependency was added.

`npm audit --omit=dev` reported 0 vulnerabilities. `npm audit` reports 13 advisories in development/build dependencies (5 moderate, 6 high, 2 critical); the suggested automated fixes require breaking major upgrades to Vitest and Tailwind. Production dependencies are clear.

## Actual checks

Run from `web/`:

- `npm run typecheck` — passed.
- `npm test` — passed; 2 files, 8 tests.
- `npm run build` — passed; Vite production build completed.
- `npm audit --omit=dev` — 0 vulnerabilities.

## Limitations

- The foundation backend implements only health. The document list, upload, and analysis routes are specified but unavailable until the backend implements them; live mode shows those errors.
- The API has no project persistence or project membership endpoints. Demo project changes are local only.
- The API has no review persistence endpoint. In live mode, review controls clearly say actions are not persisted.
- `DocumentSummary` contains only document ID, filename, and status, so live bibliographic metadata and draft/source distinctions are unavailable unless the backend adds fields or a coordinated contract change.
- Comparison results contain dimension status and explanation but no separate structured source-scope values. The source-evidence cell therefore states `Not extracted` for dimensions with a returned comparison and `Unknown` for explicitly unknown dimensions; researchers can inspect the exact passage beside the table.
- History/activity are session presentation, not an audit log.

## Instructions for Agent 9

- Integrate the `web/` application from this branch without changing the shared Pydantic contracts on behalf of the frontend.
- Preserve the documented JSON field names and enum values. In particular, the UI expects `partially_compatible` and explicit `ScopeValue(status="unknown")` values.
- For live analysis, return the documented `AnalyzeResponse` nesting and preserve the exact evidence quote and `EvidenceChunk` page/section provenance. The client uses those IDs and fields to link evidence to findings.
- When adding live document support, retain the current `DocumentSummary` response fields or coordinate any additions; authors, publication year, project association, and document kind are not part of the current response.
- Do not treat reviewer actions or projects as persisted until their endpoints are implemented. Add client calls only after the API contract and persistence behavior are agreed.
- Start the frontend with `cd web && npm install && npm run dev`; start the API from the repository root with `uvicorn api.main:app --reload`.
