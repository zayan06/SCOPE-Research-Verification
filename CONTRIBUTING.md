# Contributing to SCOPE

## Ownership and contracts

Start from the repository baseline and work in the assigned module. Do not
independently redesign `src/scopecheck/contracts.py`. Keep APIs typed, document
public behavior, preserve provenance, and report dependency changes.

## Development setup

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Install optional extras only for the module being developed, e.g.
`python -m pip install -e '.[ingestion]'`.

## Tests

Run focused tests while working and the full suite before integration:

```sh
pytest tests/<module>
pytest
```

Tests must be deterministic, local, and independent of paid APIs or external
credentials. Never encode fabricated experiments or metrics as fixtures.

## Integration checklist

1. Implement the public signature in `docs/architecture/FOUNDATION.md`.
2. Return only canonical contract models at module boundaries.
3. Preserve source IDs, exact text, and offsets when available.
4. Keep unknown scope values unknown; do not coerce missing data to agreement.
5. Add module-owned tests and document optional dependencies.
6. Report what was run and its actual outcome.
