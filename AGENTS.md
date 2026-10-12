# Shared agent instructions

Inspect the current repository, read this file and
`src/scopecheck/contracts.py`, and check Git status before editing. Preserve
existing commits and work. Implement only the assigned workstream and its
owned files; do not overwrite another worktree's changes.

## Engineering rules

1. Preserve the established shared contracts and public interfaces. Coordinate
   proposed changes to contracts or shared dependencies before editing them.
2. Use typed Python and TypeScript at module and API boundaries.
3. Write deterministic, meaningful tests for behavior you implement and run
   the relevant suite before reporting completion.
4. Keep local execution possible without paid APIs or cloud credentials.
   Gemini and Pinecone are optional replaceable adapters.
5. Preserve exact scientific source passages and their document/page/offset
   provenance when available. Keep unknown scope values explicitly unknown.
6. Do not invent citations, experiments, evaluation metrics, implementation
   progress, or student contributions. Distinguish synthetic examples from
   real benchmark data.
7. Do not expose credentials or secrets. Do not add dependencies without a
   clear need; document additions and keep optional services optional.
8. Keep documentation consistent with tested implementation and state known
   limitations honestly.
9. Use a meaningful commit message and commit completed work only on the
   assigned branch. Never merge directly into `main`.
10. Do not rewrite history, reset assigned branches, or discard another
    contributor's work.

## Workstream ownership

| Agent | Branch | Owned paths |
| --- | --- | --- |
| 1 Ingestion | `feat/ingestion` | `src/scopecheck/ingestion/`, `tests/test_ingestion.py` |
| 2 Claims | `feat/claims` | `src/scopecheck/claims/`, `tests/test_claims.py` |
| 3 Retrieval | `feat/retrieval` | `src/scopecheck/retrieval/`, `tests/test_retrieval.py` |
| 4 Alignment | `feat/alignment` | `src/scopecheck/alignment/`, `tests/test_alignment.py` |
| 5 Evaluation | `feat/evaluation` | `src/scopecheck/evaluation/`, `data/benchmarks/`, `tests/test_evaluation.py` |
| 6 Backend | `feat/backend` | `api/`, backend-owned API tests |
| 7 Frontend | `feat/frontend` | `web/` |
| 8 Literature | `docs/literature` | `docs/literature/`, `docs/methodology/research_design.md`, `docs/report/` |
| 9 Integration | `integrate/scope` | Cross-module integration only when required; preserve existing algorithms |

Shared `contracts.py`, root configuration, and other agents' tests are not
owned by an individual workstream. Coordinate before changing them.

## Handoff requirement

Each workstream creates `docs/handoffs/<workstream>.md` on its assigned branch.
Include workstream, branch, commit hash, changed files, implemented behavior,
public interfaces, dependencies, tests and actual results, limitations, and
integration steps. Do not modify another workstream's handoff.

## Integration rules

Start from the prepared common base. Keep each workstream independently
installable and testable. Use fixtures or mocks for unfinished dependencies.
Do not introduce circular imports. Agents do not merge their own branches;
the integration workstream validates and combines committed changes.
