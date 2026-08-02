# M025 — Portable proof-gated rewrite lifecycle protocol draft

**Status: DEVELOPMENT ONLY. Not frozen or canonical.**

## Question

Can one bounded rewrite move through proposal, independent validation, adoption,
migration, learned-tool replay and forced rollback as a single auditable transaction?

## Transaction boundary

The initial transaction contains a `VersionedCodeBody` and its `ToolRegistry`.

1. M020 searches development cases and selects only a strict source improvement.
2. M023 independently runs the parent and candidate on development cases and the
   candidate on a separate regression suite.
3. Adoption occurs only if every workspace completes, the candidate independently
   improves and all regression cases pass.
4. M024 exports and reimports the adopted body, archive, digest history, primitive tools
   and learned traces.

M020 absorbs a selected trace before M023 makes its independent adoption decision.
M025 therefore owns an additional invariant: any rejection or exception restores both
the body and learned-tool registry exactly. A rejected transformation must not leak into
future search through the registry.

## Development gates

- a two-edit improvement is selected without regression answers entering search;
- independent parent, candidate and regression workspace identities are recorded;
- the accepted body and learned tool migrate exactly;
- held-out regression behaviour remains perfect after migration;
- the learned tool replays the same transformation on a structurally equivalent body;
- forced rollback on the migrated body restores the exact parent source and behaviour;
- rollback on the migrated copy does not mutate the source lineage;
- a regression-rejected candidate leaves body, archive, digest history and registry
  byte-for-byte equivalent to their pre-run state;
- an already optimal body is neither replaced nor exported;
- repeated independent lifecycles produce identical bodies, passports and evidence.

## Scope boundary

M025 does not diagnose its own fault, invent an AST operation type, mutate multiple
files, compile into an unknown substrate, authenticate a passport signer, migrate
autobiographical memory, prove post-migration advantage or complete repeated improvement
cycles. It integrates existing bounded capabilities so later experiments have one
explicit lifecycle to widen.
