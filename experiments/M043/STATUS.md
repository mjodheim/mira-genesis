# M043 status

## Final development status

**Qualification gates Q1, Q2, Q3, Q4 and Q5 passed in development. Q6 was absorbed by M044
and is not a separate experiment. No M043 canonical result exists.**

M043 tested structural-domain transfer from deterministic binary DFAs to deterministic total
Mealy machines with three-symbol input and output alphabets. It rebuilt the formal body,
rewrite language, constructive tasks and opaque-native representation independently while
reusing only domain-neutral serialisation, journal, sandbox, adoption and rollback
infrastructure.

## Qualified gates

| Gate | Result | Evidence |
|---|---|---|
| Q1 — exact formal kernel | **PASSED IN DEVELOPMENT** | Run `30983777610`; 625 tests on Python 3.11 and 3.13 plus integrity. |
| Q2 — certified capacity-changing rewrite language | **PASSED IN DEVELOPMENT** | Run `30992682534`; 643 tests on each version plus integrity. |
| Q3 — constructively available hidden tasks | **PASSED IN DEVELOPMENT** | Run `30997105933`; 672 tests on each version plus integrity. |
| Q4 — disposable validation, adoption and rollback | **PASSED IN DEVELOPMENT** | Run `31001898372`; 705 tests on each version plus integrity. |
| Q5 — opaque-native migration | **PASSED IN DEVELOPMENT** | Run `31008963611`; 745 tests on each version plus integrity. |
| Q6 — complete development replay | **ABSORBED BY M044** | Complete replay became an integrated M044 exit condition rather than another standalone qualification gate. |

Q1 established immutable exact Mealy representation, canonical serialisation, product
equivalence, shortest distinguishing inputs, minimisation and fail-closed parsing.

Q2 established exact state effects, behaviour-preserving reachable growth, later
specialisation, exact indexed identities and parent-bound trace replay.

Q3 established structural-incapacity certificates, target-blind constructive search, exact
trace replay, mandatory capacity exploitation, bounded observations, distinct equal-budget
controls and explicit negative termination.

Q4 established full-lineage candidate commitments, disposable replay without hidden-target
access, evaluator-side exact acceptance, immutable versioned snapshots and byte-identical
rollback after forced body, registry, learning-state and journal faults.

Q5 established bounded public discovery of opaque finite-field semantics, explicit rejection
of incomplete or unstable substrates, table-free finite-field DAG synthesis, exact indexed
body reconstruction, independent certificate recomputation and migration bundles bound to
the complete Q4 lineage state.

## Integration outcome

M044 reused Q1–Q5 directly and completed the former replay requirement inside one bounded
continuous Mealy lineage. Workflow run `31015992729` passed 755 tests on Python 3.11, 755 on
Python 3.13 and every integrity check. See
[`../M044/PROTOCOL.md`](../M044/PROTOCOL.md).

## Claim boundary

M043 is component-qualification evidence. M044 is a positive integrated development result.
Neither is canonical. M042 remains the only positive canonical continuous-lineage completion.
No M043 or M044 seed block, hidden task bank or canonical workflow was authorised.
