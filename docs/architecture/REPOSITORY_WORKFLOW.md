# Repository and branch workflow

- `main` is the integration branch. The foundation commit is the shared start.
- Create short-lived branches from this baseline using
  `feature/<module>-<short-description>`, e.g. `feature/ingestion-pdf`.
- Keep changes within the owned module and tests. Shared contracts and
  dependencies require an integration note.
- Integrate by review; do not force-push shared branches.
- Commit messages should state module and intent, e.g.
  `feat(retrieval): add local tf-idf index`.

The exact foundation hash is recorded in the repository handoff after creation.
