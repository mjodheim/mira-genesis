# M043 status

## Current phase

**Qualification gates Q1 and Q2 passed in development; Q3 is active. No canonical result
exists.**

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

## Active work — Q3

The next boundary is constructively available hidden Mealy tasks. Before admission, every
task must have:

- an exact certificate that the declared parent is structurally incapable of the target;
- at least one admissible Q2 trace reaching the exact target within frozen depth and node
  budgets;
- rewrite arguments that do not directly encode the target table;
- meaningful equal-budget fresh, unchanged-parent, output-only, learning-state and tool
  controls;
- explicit deterministic negative termination when no admissible task exists.

M041's constructive-unavailability failure must be impossible after bank admission, not
merely unlikely. No hidden task bank, development seed block or canonical workflow is
authorised yet.

## Claim boundary

M042 remains the only positive canonical continuous-lineage completion result. M043 does
not widen or replace it. Q1 and Q2 qualify the Mealy substrate and rewrite language only;
they do not yet establish hidden-task construction, isolated adoption, migration or
post-migration plasticity in that domain.
