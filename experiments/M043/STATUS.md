# M043 status

## Current phase

**Qualification gates Q1, Q2, Q3, Q4 and Q5 passed in development; Q6 is active. No
canonical result exists.**

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

CI workflow run `30983777610` passed the complete repository suite with **625 tests on
Python 3.11** and **625 tests on Python 3.13**. Repository integrity also passed.

## Q2 — certified capacity-changing rewrite language

The independent rewrite language is implemented in `metamorphosis/m043_rewrite.py` and
specified in [`Q2_REWRITE_LANGUAGE.md`](Q2_REWRITE_LANGUAGE.md). It provides exact
physical/reachable state effects, behaviour-preserving reachable-capacity growth, later
specialisation, exact indexed identities and parent-bound byte-identical trace replay.

Qualification workflow run `30992682534` passed **643 tests on Python 3.11**, **643 tests on
Python 3.13** and the complete integrity audit.

## Q3 — constructively available hidden tasks

Q3 is implemented in `metamorphosis/m043_task_model.py`,
`metamorphosis/m043_task_search.py` and `metamorphosis/m043_tasks.py`, with the protocol in
[`Q3_CONSTRUCTIVE_TASKS.md`](Q3_CONSTRUCTIVE_TASKS.md). It fixes:

- exact minimal-state structural-incapacity certificates;
- deterministic target-blind search over Q2 operations;
- exact parent-bound replay for every admitted target;
- mandatory capacity growth followed by actual exploitation;
- bounded observations without target tables or witness operations;
- six causally distinct equal-budget controls;
- a seed-free three-entry development catalogue;
- explicit negative termination.

Qualification workflow run `30997105933` passed **672 tests on Python 3.11**, **672 tests on
Python 3.13** and the complete integrity audit.

## Q4 — disposable validation, adoption and rollback

Q4 is implemented across:

- `metamorphosis/m043_adoption_codec.py`;
- `metamorphosis/m043_lineage_state.py`;
- `metamorphosis/m043_adoption_validation.py`;
- `metamorphosis/m043_adoption_transaction.py`;
- `metamorphosis/m043_adoption.py`;
- `metamorphosis/m043_validation_worker.py`.

The protocol is specified in
[`Q4_ADOPTION_ROLLBACK.md`](Q4_ADOPTION_ROLLBACK.md). It establishes:

- a strict candidate package bound to the full parent lineage, exact parent body, task,
  target commitment, Q2 trace and frozen Q3 budget;
- replay in a fresh isolated Python process that has no Q3 evaluator dependency and never
  receives the hidden target body;
- exact evaluator-side target comparison after isolated replay;
- immutable versioned lineage snapshots covering body, tool registry, portable learning
  state, target commitments and a hash-chained causal journal;
- commit only after a complete post-commit audit;
- byte-identical rollback after forced corruption of the body, registry, learning state or
  journal;
- explicit restoration from accepted version 1 to archived version 0;
- deterministic reporting independent of runtime process identifiers.

Final qualification workflow run `31001898372` passed **705 tests on Python 3.11**, **705
tests on Python 3.13** and all integrity checks. The prior run `31001191874` passed both test
matrices but exposed a static orphan-edge declaration for the dynamically launched worker;
that repository-integrity defect was corrected without changing Q4 behaviour.

## Q5 — opaque-native migration

Q5 is implemented across:

- `metamorphosis/m043_opaque_substrate.py`;
- `metamorphosis/m043_native_program.py`;
- `metamorphosis/m043_native_verify.py`;
- `metamorphosis/m043_migration.py`;
- `scripts/run_m043_q5_qualification.py`.

The protocol is specified in [`Q5_OPAQUE_NATIVE.md`](Q5_OPAQUE_NATIVE.md). It establishes:

- three opaque prime-field substrates whose opcode identifiers and semantic assignments
  differ while public descriptors reveal only arity and cost;
- recovery of stable addition, multiplication and negation semantics through bounded
  repeated public probes only;
- explicit rejection of missing, unstable and under-budget substrate discoveries;
- table-free native synthesis as a reachable scalar DAG of unary and binary opaque calls;
- finite-field Lagrange interpolation for next state and emitted output;
- exact reconstruction of every indexed state/symbol pair and exact Mealy equivalence;
- strict rejection of extra table fields, forward references, unreachable payload nodes,
  wrong substrates and wrong discovery bindings;
- independent recomputation of every synthesis-certificate field;
- a migration bundle bound to the complete Q4 snapshot, body, tool registry, portable
  learning state and causal journal;
- no selected seed, hidden task bank or canonical workflow authority.

Qualification workflow run `31008963611` passed **745 tests on Python 3.11** in 535.16
seconds, **745 tests on Python 3.13** in 581.31 seconds and every repository-integrity
check. No job failed and no rerun was used.

## Active work — Q6

The final M043 qualification boundary is complete deterministic development replay. Q6 must
regenerate from one frozen founder-side specification:

- the exact Mealy kernel identities;
- the Q2 rewrite traces and certificates;
- the Q3 constructive catalogue and control outcomes;
- the Q4 accepted snapshot, tool registry, learning state and causal journal;
- the Q5 public-probe discovery records, native DAGs, certificates and migration bundles;
- one complete manifest whose bytes and digests agree on Python 3.11 and Python 3.13.

No hidden task bank, development seed block or canonical workflow is authorised yet.

## Claim boundary

M042 remains the only positive canonical continuous-lineage completion result. M043 does
not widen or replace it. Q1–Q5 qualify the Mealy substrate, rewrite language, constructive
tasks, transactional adoption and exact opaque-native migration only. They do not yet
establish a complete seed-only replay or continuous post-migration learning in this domain.
