# GitHub Actions workflow lifecycle

This directory contains two different kinds of tracked files and they must not be confused.

## Operational workflows

- `ci.yml` — repository tests, integrity checks and preserved-result replay gates;
- `attribution-policy.yml` — authorship/attribution policy enforcement.

These are the permanent repository automation surface.

## Frozen path-bound workflow evidence

Nine milestone workflow files remain here because preserved scientific protocols/tests commit not
only their bytes but their historical `.github/workflows/...` path:

- `m064-canonical.yml`, `m065-canonical.yml`, `m066-canonical.yml`;
- the six `m092-*` workflow files retained by the aborted M092 record.

They are **not classified as permanent operational CI** by the repository audit.  Relocating them
would invalidate frozen file commitments, so they remain byte-exact at the path the scientific
record names.

Other milestone-specific workflows should be moved to `archives/workflows/` once their execution
role is consumed, superseded or abandoned, provided no frozen protocol commits their original path.

The lifecycle and the path-bound exception are documented in
[`docs/REPOSITORY_ARCHITECTURE.md`](../../docs/REPOSITORY_ARCHITECTURE.md) and checked by
`scripts/audit_repository_layout.py`.
