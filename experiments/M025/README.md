# M025 — Portable proof-gated rewrite lifecycle

M025 joins the three verified bounded rewrite layers into one transaction:

- M020 proposes a rewrite and learns its transformation;
- M023 independently validates the parent, candidate and regression evidence;
- M024 migrates the adopted source, rollback lineage and complete tool registry.

[`PROTOCOL_DRAFT.md`](PROTOCOL_DRAFT.md) defines the transaction and development gates.
[`STATUS.md`](STATUS.md) records the verified scope and remaining completion gaps.

This is an integration milestone, not a canonical experiment or unknown-substrate
migration.
