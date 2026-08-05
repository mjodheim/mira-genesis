# M043 status

## Current phase

**Qualification gate Q1 passed in development. No canonical result exists.**

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
Python 3.11** and **625 tests on Python 3.13**. Repository integrity also passed: every
module imports, no orphan module remains and declared dependencies match real imports.

## Active work — Q2

The next boundary is the independent Mealy rewrite language. It must:

- declare exact state-count effects for every primitive;
- include at least one behaviour-preserving capacity-increasing operation;
- include later operations that can exploit the duplicated capacity;
- replay every trace byte-identically from its declared parent;
- remain independent from the executable M039/M042 DFA macro and target generators;
- expose permanent falsification tests before any hidden task bank or seed block exists.

No M043 canonical workflow, selected seed, hidden-task result or ten-gate claim is
authorised.

## Claim boundary

M042 remains the only positive canonical continuous-lineage completion result. M043 does
not widen or replace it. Q1 qualifies only the formal Mealy substrate; it does not yet
establish self-rewrite, task construction, migration or post-migration plasticity in that
domain.
