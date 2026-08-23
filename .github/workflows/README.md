# Active GitHub Actions

Only workflows that are intentionally executable belong in this directory.

Permanent workflows:

- `ci.yml` — repository tests, integrity checks and preserved-result replay gates;
- `attribution-policy.yml` — authorship/attribution policy enforcement.

Milestone-specific workflows are temporary execution instruments.  Once a canonical run is consumed,
a milestone is superseded, or an experiment is abandoned, preserve the exact YAML under
`archives/workflows/` and remove it from this directory.

The lifecycle is documented in [`docs/REPOSITORY_ARCHITECTURE.md`](../../docs/REPOSITORY_ARCHITECTURE.md)
and checked by `scripts/audit_repository_layout.py`.
