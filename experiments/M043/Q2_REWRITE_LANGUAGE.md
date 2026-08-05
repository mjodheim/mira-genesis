# M043 Q2 — certified capacity-changing Mealy rewrite language

**Status: passed in development. Qualification CI completed successfully.**

## Question

Can M043 expose a Mealy-specific rewrite language that can increase reachable structural
capacity without changing behaviour, later exploit that capacity, certify every structural
effect exactly and replay a complete rewrite trace byte-identically from one declared
parent?

This is a rig-qualification result only. It does not define a hidden task bank, select a
seed, authorise a canonical workflow or reproduce the M042 ten-gate claim.

## Independent implementation

The implementation lives in `metamorphosis/m043_rewrite.py`. It does not import the
M039/M042 DFA rewrite macro, DFA target generators, canonical task bank or result fields.
It depends only on the Q1 Mealy formal kernel.

The language contains four primitives:

| Primitive | Declared physical effect | Required certified effect |
|---|---:|---|
| `DuplicateReachableTarget(entry_state, input_symbol)` | `+1` state | Exact behavioural equivalence and exactly `+1` reachable state. |
| `ReplaceEmission(state, input_symbol, output_symbol)` | `0` states | Reachability unchanged and an exact distinguishing word exists. |
| `RedirectTransition(state, input_symbol, target_state)` | `0` states | Physical state count unchanged; the exact reachable-state and behavioural effects are recorded. |
| `PruneUnreachable()` | Negative | Only unreachable storage is removed and behaviour remains exactly equivalent. |

No-op output and transition edits are rejected. Edits that name unreachable source states,
invalid symbols or invalid targets fail closed.

## Neutral growth construction

`DuplicateReachableTarget` clones the complete transition/output row of the state reached by
one selected incoming arc, appends the clone and redirects only that arc to the clone. The
candidate is accepted only when independent certification proves all of the following:

1. the physical state count increased by exactly one;
2. the reachable state count increased by exactly one;
3. exact product equivalence reports no distinguishing input.

This third condition is not enough by itself: a clone can replace the only route to the
original target and therefore fail to create new reachable capacity. Such pseudo-growth is
explicitly rejected.

Once admitted, the clone has its own concrete state index. A later `ReplaceEmission` or
`RedirectTransition` can specialise only the cloned history while leaving histories that
still reach the original state unchanged. The permanent example first grows a two-state
machine neutrally, then changes the clone so that `(1, 0, 0)` distinguishes the specialised
body while `(0, 0, 0)` remains unchanged.

## Exact certificates

Every applied operation emits an immutable `RewriteCertificate` containing:

- exact parent and child indexed-body SHA-256 identities;
- canonical minimal-behaviour SHA-256 identities;
- physical and reachable state counts before and after;
- both exact deltas;
- exact equivalence status;
- the deterministic shortest distinguishing word when behaviour changes.

The Q1 canonical identity deliberately ignores state renaming and unreachable storage. Q2
operations refer to concrete indices, so replay uses a separate domain-separated exact body
identity that includes every indexed row and unreachable state. This prevents an equivalent
but structurally different body from being substituted as the declared parent.

## Replay contract

A `RewriteTrace` records the root exact-body digest, ordered operation/certificate pairs,
the final exact-body digest and a versioned canonical JSON format. Replay:

1. rejects a parent whose exact digest differs;
2. reapplies every operation;
3. recomputes every certificate independently;
4. rejects any certificate mismatch;
5. requires the final exact-body digest to match.

The serialised parser rejects unknown versions, missing or extra fields, invalid digests,
boolean/integer confusion and malformed operations. Rebuilding the same trace from the same
parent produces identical final body bytes, identical trace bytes and the same
domain-separated trace digest.

## Permanent falsification suite

`tests/test_m043_rewrite.py` includes 18 test cases covering:

- exact neutral reachable-capacity growth;
- rejection of apparent growth that merely replaces the original reachable state;
- later specialisation of the new state without editing the original;
- exact reachability effects of transition rewrites;
- behaviour-preserving unreachable-state compaction;
- byte-identical deterministic trace replay;
- wrong-parent and tampered-certificate rejection;
- strict operation and trace round trips;
- fail-closed parsing of malformed and extended records;
- 64 deterministic random machines, with every admitted duplication independently checked
  for exact equivalence and `+1` reachable capacity.

Qualification workflow run `30992682534` passed the complete repository with **643 tests on
Python 3.11**, **643 tests on Python 3.13** and a successful integrity audit covering clean
imports, orphan-module detection and dependency consistency.

## Exit and next boundary

Q2 is passed in development. The next authorised gate is Q3: constructively available
hidden Mealy tasks. Before any task can enter a development bank, the parent must be
structurally incapable of exact behaviour and an admissible Q2 trace must be proven to reach
the target within declared depth and node budgets.

M041's constructive-unavailability failure must be made impossible by admission, not hidden
by retries or larger search budgets. No hidden task bank, seed block or canonical workflow
is authorised yet.
