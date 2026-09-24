# RSI V23 policy guard contract

Status: development apparatus, not yet the canonical V23 candidate ABI.

The policy object is executable Python, so V23 needs a boundary between "improve the search
procedure" and "gain arbitrary host authority".

The development guard accepts ordinary pure-Python policy logic and rejects obvious authority and
information channels:

- imports;
- filesystem or console I/O;
- dynamic compilation/evaluation/import;
- reflective namespace access;
- dunder attribute traversal;
- known system/network/process module names;
- async/yield/context-manager machinery;
- non-literal top-level state.

The guard can additionally receive a list of development-only tokens (task IDs, node IDs, campaign
identifiers). Those tokens may not appear in string/bytes literals in candidate source.

This is intentionally described as a **guard**, not a proof:

- a sufficiently adversarial program can encode a forbidden string indirectly;
- static analysis cannot prove termination;
- pure computation can still overfit numerical patterns in development history.

Therefore canonical V23 must also use process isolation, an execution timeout, fresh task identities
and a decisive fresh online holdout. Replay performance alone cannot qualify G3.
