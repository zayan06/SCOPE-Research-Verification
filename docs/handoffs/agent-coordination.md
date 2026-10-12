# Agent workspace coordination

This document is operational setup material. All branches derive from the
common setup commit on `main` (reported in the setup completion note). The
pre-existing `docs/literature` branch is preserved and includes its committed
research-draft work plus the common setup commit.

## Workspaces

| Agent | Workstream | Branch | Workspace |
| --- | --- | --- | --- |
| 1 | Scientific document ingestion | `feat/ingestion` | `/Users/zayan/Documents/Codex/2026-10-12/you-are-working-on-scope-scope/outputs/scope-ingestion` |
| 2 | Atomic claim extraction | `feat/claims` | `/Users/zayan/Documents/Codex/2026-10-12/you-are-working-on-scope-scope/outputs/scope-claims` |
| 3 | Evidence retrieval | `feat/retrieval` | `/Users/zayan/Documents/Codex/2026-10-12/you-are-working-on-scope-scope/outputs/scope-retrieval` |
| 4 | Scope-aware alignment | `feat/alignment` | `/Users/zayan/Documents/Codex/2026-10-12/you-are-working-on-scope-scope/outputs/scope-alignment` |
| 5 | Evaluation and benchmarking | `feat/evaluation` | `/Users/zayan/Documents/Codex/2026-10-12/you-are-working-on-scope-scope/outputs/scope-evaluation` |
| 6 | FastAPI backend and persistence | `feat/backend` | `/Users/zayan/Documents/Codex/2026-10-12/you-are-working-on-scope-scope/outputs/scope-backend` |
| 7 | React frontend and visualization | `feat/frontend` | `/Users/zayan/Documents/Codex/2026-10-12/you-are-working-on-scope-scope/outputs/scope-frontend` |
| 8 | Literature and methodology | `docs/literature` | `/Users/zayan/Documents/Codex/2026-10-12/you-are-working-on-scope-scope/outputs/scope-literature` |
| 9 | Core/full-system integration | `integrate/scope` | `/Users/zayan/Documents/Codex/2026-10-12/you-are-working-on-scope-scope/outputs/scope-integrate` |

Each workspace has its own Git worktree and `.venv`. Python dependencies are
installed from the shared project metadata; optional extras should be added
only for the relevant workstream.

## Launch order and dependencies

**Wave 1:** Agents 1–5 and 8 can begin concurrently against the shared
contracts. Use fixtures or mocks for unfinished modules. Agent 5 should keep
benchmark provenance and evaluation code independent from implementation
progress in agents 1–4.

**Wave 2:** Agents 6 and 7 can begin alongside Wave 1 using the documented API
and canonical DTOs. They should not depend on uncommitted worktree changes.

**Wave 3:** Agent 9 integrates agents 1–5 after committed implementations and
handoffs exist, then validates the scientific pipeline and traceability.

**Wave 4:** Agent 9 integrates backend and frontend after their interfaces are
stable, then incorporates verified research documentation. No agent merges
directly into `main`.

## Local commands

In any workspace:

```sh
source .venv/bin/activate
pytest
```

For the backend worktree, run `uvicorn api.main:app --reload` from the repository
root. The `main` worktree remains at
`/Users/zayan/Documents/Codex/2026-10-12/you-are-working-on-scope-scope/outputs/scope`.
