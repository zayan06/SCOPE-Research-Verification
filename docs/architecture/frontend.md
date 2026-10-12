# Frontend architecture

## Component structure

The application entry point is web/src/main.tsx. web/src/App.tsx owns
lightweight hash navigation, project and workspace mode state, and the five screens:

- **Overview** — project selector/list, project creation, counts, recent activity, and finding summary.
- **Documents** — draft/source filters, search, document metadata, and upload dialog.
- **Analysis workspace** — three panels for draft claims, evidence passages, and scientific alignment, plus the scope comparison table and lightweight evidence path.
- **Analysis results** — relation, priority, source, and review filters with passage previews.
- **Analysis history** — recent comparison runs.

The design uses custom CSS with a restrained slate and navy palette. Tailwind is
configured for utility classes and build processing, while the current screens
use named styles so layout rules remain easy to inspect. Icons are small inline
SVG components; no icon or routing package is required. On narrow screens, the
navigation becomes a horizontal strip and analysis panels stack vertically.

web/src/contracts.ts mirrors the public Pydantic shapes in
src/scopecheck/contracts.py. Unknown scope is modeled explicitly as
{ status: "unknown" }; status compatibility values retain the API spelling
partially_compatible.

## API client and modes

web/src/api.ts provides typed calls for the documented API:

- GET /api/health
- GET /api/documents
- POST /api/documents with multipart field file, including upload progress
- POST /api/analyze with draft_text and selected_document_ids

VITE_API_BASE_URL configures the API origin. When blank, requests use the
current origin; the Vite development server proxies /api to
http://127.0.0.1:8000.

The default is **demo mode**, displayed in the sidebar and a persistent banner.
All example documents, passages, and findings are synthetic. The examples do
not assert authors, publication years, page locations, or real citations. Demo
uploads store only the filename in browser memory and simulate processing; the
file is not sent to a server. Demo project creation, review labels, and notes
are temporary in-memory state.

**Live API mode** is selected deliberately by the user or with
VITE_API_MODE=live. It requests health and document data. Failed live requests
show an error with an explicit button to enter demo mode; failed requests never
replace the current data with samples. Document upload and claim analysis call
the documented routes. API response fields that the current API does not
provide, such as authors, year, or project association, stay unavailable in the
interface. Project persistence and reviewer-state persistence are outside the
current API contract; the interface reports these limitations and does not
claim those live actions were saved.

## API integration expectations

The client expects the response models described in docs/API.md and shared
contracts. Analysis results retain claim IDs, evidence chunk IDs, exact quotes,
confidence, relation, scope compatibility, dimension comparisons, explanation,
recommended action, and model version. Evidence provenance uses section and
page only when supplied by EvidenceChunk.

The API currently documents product routes as specified but unimplemented; only
health is implemented on the foundation branch. In live mode a missing route is
shown as an API error. For deployment, configure a reverse proxy or an API base
URL and the appropriate CORS policy for the frontend origin.

## Startup and checks

From web/:

```sh
npm install
npm run dev
npm run typecheck
npm test
npm run build
```

For local API development, run uvicorn api.main:app --reload from the
repository root. The frontend development proxy forwards /api to port 8000.

## Current limitations

- The API contract has no project listing/creation or project membership routes; demo projects are local examples.
- The API contract does not persist review decisions or reviewer notes.
- The specified upload and analysis routes are not implemented in the foundation API. Live mode reports their errors directly.
- The documents endpoint exposes filename and status only. Bibliographic metadata is not inferred.
- Analysis history and activity are a compact presentation of current-session findings, not a persisted audit log.
- Demo upload processing and analysis are simulated and do not parse or analyze the selected file.
