# M092 canonical criterion-search transport

## Status

This transport is **unarmed**.  Merging it does not execute the M092 target search, create a search
state, select a candidate, reveal qualification material, register a substrate operation, or support
H38/D062.

The unique first target search may run only from a later commit whose sole changed file is
`experiments/M092/CANONICAL_SEARCH_ARMED.json` and whose commit message is exactly:

`m092(canonical): arm first immutable criterion search`

The marker must bind its actual parent commit and the exact SHA-256 digests of every decisive
selection artifact: the frozen protocol and target theorem; criterion runner, freeze checker and
engine; resume validator; program enumerator; certificate-policy search; certificate generator;
proof search; candidate scanner; independent certificate verifier; K1 kernel; runtime; canonical
guard and workflow; and result packager.  The full program limit remains 2,000,000.  No reset,
reroll, alternate seed or post-result repair path is provided.

## Why transport and arming are separate

The transport itself is part of the authored experimental apparatus.  It therefore has to be
reviewed, tested and merged while the target search is still closed.  A later marker-only commit can
then open exactly that previously frozen apparatus without changing it at the moment the first
result is consumed.

The guard deliberately treats state SHA-256 values as integrity checks rather than authority.  Any
future resumed computation must still satisfy the full deterministic replay rule frozen by M092-D.

## Runtime gate before arming

A green transport PR is **not** sufficient reason to arm the first search.  Before the marker is
created, the execution envelope must be reviewed against the frozen worst-case budgets:

- 2,000,000 generated programs;
- at most 4,096 certificate-policy attempts per program;
- at most 2,000,000 certificate-policy attempts globally;
- no behaviour deduplication;
- a six-hour GitHub Actions job ceiling in the canonical transport.

This review may use neutral/non-target instrumentation only.  It must not rehearse the M092 target
search, inspect a target candidate, alter ordering, add a hidden budget, or tune the proof search from
target feedback.  If the frozen computation cannot be made to fit the available execution envelope
without changing its scientific meaning, that limitation must be recorded before any first-run
claim is consumed.

## Checkpoint and interruption semantics

Checkpointing is transport-only.  The criterion engine is unchanged: every chunk invokes the same
frozen `advance_search` function on the exact state produced by the previous chunk.  Tests require a
neutral one-chunk execution and a multi-chunk execution over the same program budget to end in the
same complete serialized state and state digest.

Before consuming any new program, the runner atomically writes the authenticated initial/resumed
state.  It then advances at most 1,000 programs at a time and atomically replaces the checkpoint only
after a fully validated chunk completes.  The canonical execution step has a 330-minute ceiling
inside a 360-minute job, leaving time for preservation after a normal search-step timeout.

Every armed workflow that actually reaches the target-search execution step receives a separate
attempt artifact containing the latest completed checkpoint, arming head/parent, GitHub run identity,
execution-step outcome, counters and state digest.  This attempt is preserved whether the execution
finishes or fails.  An interrupted attempt does not authorize a changed seed, changed implementation
or alternate search path: any retry is an exact deterministic reproduction on the same arming head.
A runner loss that prevents artifact upload must still be disclosed as infrastructure interruption;
the deterministic prefix remains reconstructible from the frozen arming head.

Only a completed terminal search creates the uniquely named `m092-first-canonical-search` artifact.
That completed artifact blocks any later purported first search.  Attempt artifacts do not silently
become scientific results and do not permit an undesirable partial outcome to be discarded.

## Canonical artifact

When eventually armed and completed, the workflow preserves both the raw terminal criterion state
and a packaged first-run artifact.  The package records the arming head, frozen parent, marker,
terminal status, program/certificate counts and exact search state.  Packaging does not execute or
qualify the selected candidate.  `candidate_selected`, `program_budget_exhausted` and
`certificate_budget_exhausted` are all legitimate terminal search outcomes; none by itself is an
M092 scientific verdict.

Qualification, causal ablations, registration, rollback, fresh-process persistence and any final
M092 claim remain later protocol phases and must stay separate from candidate selection.
