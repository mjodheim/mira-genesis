# M043 status

## Current phase

**Qualification gates Q1, Q2 and Q3 passed in development; Q4 is active. No canonical
result exists.**

M043 begins the second research phase after the positive M042 bounded completion. It tests
structural-domain transfer from deterministic binary DFAs to deterministic total Mealy
machines with three-symbol input and output alphabets.

## Q1 — exact formal kernel

The first independent Mealy-domain kernel is implemented in
`metamorphosis/m043_mealy.py`. It provides:

- an immutable, strictly validated `MealyMachine` representation;
- canonical reachable-state serialisation invariant under state renaming;
- exact product-equivalence checking;
- deterministic shortest distinguishing input words;
- exact behavioural minimisation;
- canonical byte identities and domain-separated SHA-256 digests;
- fail-closed deserialisation of malformed or partial machines.

The permanent metamorphic suite checks malformed dimensions and symbols, strict round
trips, state-renaming invariance, shortest-counterexample correctness, exact agreement
with exhaustive bounded exploration on 64 random machine pairs, minimisation idempotence
and behavioural preservation on 32 random machines.

CI workflow run `30983777610` passed the complete repository suite with **625 tests on
Python 3.11** and **625 tests on Python 3.13**. Repository integrity also passed.

## Q2 — certified capacity-changing rewrite language

The independent rewrite language is implemented in `metamorphosis/m043_rewrite.py` and
specified in [`Q2_REWRITE_LANGUAGE.md`](Q2_REWRITE_LANGUAGE.md). It provides:

- exact physical and reachable state-count certificates for every primitive;
- guarded behaviour-preserving duplication that adds exactly one reachable state;
- later output and transition operations that can specialise the duplicated history;
- behaviour-preserving removal of unreachable storage;
- exact indexed-body identities distinct from state-renaming-invariant behavioural
  identities;
- versioned canonical traces bound to one exact parent body;
- independent certificate recomputation during replay;
- fail-closed rejection of malformed traces, wrong parents and tampered certificates.

The permanent falsification suite rejects pseudo-growth where a clone merely replaces the
original target, demonstrates later use of the new capacity and checks every admitted
neutral duplication across 64 deterministic random machines.

Qualification workflow run `30992682534` passed the complete repository with **643 tests on
Python 3.11**, **643 tests on Python 3.13** and a successful integrity audit.

## Q3 — constructively available hidden tasks

The Q3 task model and target-blind search are implemented in:

- `metamorphosis/m043_task_model.py`;
- `metamorphosis/m043_task_search.py`;
- `metamorphosis/m043_tasks.py`;
- `scripts/run_m043_q3_catalogue.py`.

The protocol is specified in
[`Q3_CONSTRUCTIVE_TASKS.md`](Q3_CONSTRUCTIVE_TASKS.md). It establishes:

- an exact minimal-state certificate that the declared parent cannot express an admitted
  target within its current capacity;
- deterministic target-blind breadth-first search over Q2 operations;
- an exact parent-bound replay trace for every admitted target;
- mandatory growth followed by actual use of the new reachable state;
- bounded public observations and commitments without exposing target tables or witness
  operations;
- six causally distinct equal-budget control surfaces;
- a seed-free three-entry development catalogue;
- explicit `insufficient` termination when no admissible catalogue can be constructed.

The development parent has two minimal states. Every admitted task in the qualified
catalogue requires three minimal states and is reached within depth 2, 512 visited nodes and
a four-state cap. No task seed was selected and no hidden target body or witness trace was
exported to the public task surface.

Qualification workflow run `30997105933` passed the complete repository with **672 tests on
Python 3.11**, **672 tests on Python 3.13** and a successful integrity audit. No failed job
or rerun was needed.

## Active work — Q4

The next boundary is isolated validation, versioned adoption and exact rollback for Mealy
bodies. Q4 must establish that:

- candidates execute in fresh disposable resource-limited workspaces;
- an independent validator checks exact parent identity, totality, protected regressions,
  strict improvement and exact target behaviour;
- candidate code has no release authority;
- accepted source bodies, tool registries and causal journals are versioned and archived;
- a fixed invalid provisional rewrite is rejected;
- rollback restores the exact accepted body, registry and journal head.

No hidden task bank, development seed block or canonical workflow is authorised yet.

## Claim boundary

M042 remains the only positive canonical continuous-lineage completion result. M043 does
not widen or replace it. Q1–Q3 qualify the Mealy substrate, rewrite language and honest task
availability only; they do not yet establish isolated adoption, opaque-substrate migration
or post-migration plasticity in that domain.
