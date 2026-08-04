# M038 — two-speed lineage: escalation boundary and causal journal

**Status: FROZEN PROTOCOL CANDIDATE.** These bytes become the active frozen protocol when
their SHA-256 and the mechanism commit are recorded in `results/M038_FREEZE.md`. After that
record, this file may not be edited. No canonical task has been derived or observed at this
point.

## 1. Question

Can one bounded organism:

1. act through a compact fast path;
2. prove from its own oracle evidence that its current body is structurally insufficient;
3. cross an explicit escalation boundary;
4. construct and independently evaluate a changed body;
5. adopt a strictly improving F1;
6. survive a separate failing provisional change by exact rollback to F1;
7. return to the fast path with F1 active;
8. do so while spending less proof cost than an otherwise identical architecture that fully
   journals every fast-path operation?

M038 reports functional feasibility and proof efficiency separately. Neither may compensate
for the other.

## 2. Non-claims

M038 does not claim:

- Gate 9 or full level-3 replay;
- three cycles or later reuse of an earlier tool;
- trans-substrate migration or post-migration plasticity;
- a curriculum, a new intermediate representation, or a learned model;
- general intelligence;
- Gate 2, because every symbol in this experiment is protocol supplied.

The fast path is not replayed operation by operation in arm B. M038 commits the integrity and
order of a compact prehistory, then begins full causal replay from an escalation checkpoint.
That is level 2 plus a committed prehistory, not level 3.

## 3. Definitions

**Lineage.** One founder body plus the ordered adopted transformations recorded by the causal
journal.

**Infrastructure cycle.** Fast path → boundary decision → optional slow path → adoption or
rejection → return. It may end in rejection.

**Functional metamorphosis cycle.** The complete F0 → F1 sequence in §9. A bare rejection
cannot satisfy it.

**Fast path.** Oracle observations, compact typed events, a rolling commitment and no body
digest per observation.

**Slow path.** Checkpoint, certificate recomputation, proposal, isolated exact evaluation,
adoption, forced failing provisional adoption, rollback and archive projection.

**Functional state.** Active body, portable learning state, tool registry and RNG state where
it influences continuation.

**Audit state.** Compact trace, causal journal, external anchors, archive projection and audit
counters. Rollback never restores or erases audit state.

## 4. Domain and task generator

The body type is a deterministic finite automaton over alphabet `{0, 1}`. Exact behavioural
equivalence and a separating word are decidable.

The one canonical task is derived only after the immutable arming commit exists.

| Parameter | Frozen value |
|---|---:|
| Founder generator | `random_minimal_dfa(seed + attempt × 7919, 4, 4)`, normalised |
| Founder attempts | `16` maximum |
| Program enumeration | `(grow, atom)`, then `(grow, atom, atom)`, then `(atom, grow, atom)` |
| Programs examined per founder | `50000` maximum |
| Target condition | first program producing a minimal target larger than the founder and an available exact incapacity certificate |
| Observation words | every binary word of length at most `6` — `127` words |
| Task-family count | one |

The laboratory may use the hidden target to generate the task and to perform independent
exact evaluation. The organism-facing proposal surface receives only the founder and oracle
evidence. No component that proposes a candidate receives the hidden target.

A task-generator failure inside the committed bounds is a canonical negative infrastructure
result. The generator is not widened after observation.

## 5. Sealed specification

The canonical marker-only arming commit is the child of the frozen parent. Its full lowercase
40-hex SHA and the frozen protocol SHA-256 determine the task seed:

```text
master_nonce = SHA256(
  "m038:sealed-head:" || arming_head_sha || ":protocol:" || protocol_sha256
)

task_seed = first_8_bytes_as_unsigned_big_endian(
  SHA256("m038:" || master_nonce || ":task:0")
)
```

The marker schema is closed:

```text
schema = m038-canonical-arm/1
frozen_parent_sha
a protocol_sha256 matching these exact protocol bytes
first_run_only = true
reruns_are_reproductions_only = true
```

The arming commit must:

- have the exact message `m038(canonical): arm first immutable run`;
- change exactly `experiments/M038/CANONICAL_ARMED.json`;
- name its actual parent as `frozen_parent_sha`.

Every other commit leaves the block closed. A malformed marker-only commit fails loudly.

The first workflow artifact attached to that arming head is the canonical result. Any rerun
is a reproduction and may never replace it.

## 6. Exact structural-incapacity trigger

The only active trigger is `proved_structural_incapacity`.

From admitted oracle answers, prefixes separated by an observed suffix cannot share a DFA
state. An exact maximum pairwise-distinguishable set therefore certifies a Myhill–Nerode
lower bound. Escalation occurs only when an available certificate has a lower bound strictly
greater than the body's state count.

| Parameter | Frozen value |
|---|---:|
| Algorithm id | `exact-max-pairwise-distinguishable` |
| Algorithm version | `m038-certificate/1` |
| Maximum search nodes | `2000000` |
| Maximum prefixes | `512` |
| Equal-size maximum clique | lexicographically smallest |
| Pair witness | shortest separating suffix, then lexicographically smallest |
| Budget exhaustion | `unavailable_within_committed_budget` |
| Fallback | none; never greedy |

The certificate records:

- body state count;
- certified lower bound;
- canonical witness prefixes;
- one canonical separating suffix for every pair;
- evidence digest;
- algorithm identity and version;
- budgets and counted operations;
- availability status.

The slow path recomputes the certificate from checkpoint body and evidence and verifies every
witness. It never trusts an `escalation_reason` string.

Soundness comes from Myhill–Nerode distinguishability, not from a finite test sample. Evidence
incompleteness can still cause false negatives; M038 never claims complete detection.

## 7. Proposal search

| Parameter | Frozen value |
|---|---:|
| Vocabulary | 36 M017 structural atoms plus eight explicit growth atoms |
| Cost unit | one symbol application |
| Search depths | `1`, then `2`, then `3` |
| Vocabulary order | committed function order |
| Maximum candidate-search nodes | `100000` |
| Evidence filter | exact agreement on all 127 admitted answers |
| Independent evaluation | exact DFA equivalence with separating witness |
| Adoption | first evidence-consistent candidate passing exact equivalence |

Proposal and judgement are separate. Candidate construction records deterministic operations,
nodes, calls and bytes. Wall-clock time is diagnostic only.

The historical greedy diagnosis and historical experiments remain untouched.

## 8. Three arms

### A — fast path only

A performs the same observations and exact certificate computation but never crosses the
boundary and never changes the body.

### B — two-speed lineage

B produces the compact fast-path trace and rolling commitment. On a valid trigger it creates
one full checkpoint and begins the full causal journal only at the boundary.

### C — full critical-path journalling

C produces every B trace, commitment, checkpoint and slow-path event, plus one full immutable
causal record and functional-state digest for every fast-path observation.

Therefore C is an instrumental strict superset:

```text
evidence_B ⊂ evidence_C
```

C may not replace or omit B's compact trace.

B and C must have identical:

- observations and evidence digest;
- exact certificate;
- escalation decision;
- candidate identities and order;
- exact verdicts and separating words;
- adopted F1;
- forced failing probe and rollback decision;
- final functional state;
- compact trace head;
- checkpoint digest;
- slow causal-journal bytes and head;
- functional counters.

Any divergence invalidates the efficiency comparison.

## 9. Exact functional sequence

```text
F0 — pre-escalation functional state

1. collect the 127 admitted oracle answers;
2. compute and verify structural incapacity;
3. enter the slow path;
4. create and externally anchor the escalation checkpoint;
5. recompute the certificate from checkpoint body and evidence;
6. propose and independently evaluate candidates;
7. adopt the first strictly improving exact candidate;
8. obtain F1;
9. provisionally apply the fixed failing probe flip(initial) from F1;
10. independently reject that probe by exact equivalence;
11. append rollback request, restore F1 exactly, append rollback attestation;
12. return to the fast path with F1 active;
13. demonstrate competence at F1 unavailable at F0.
```

Functional success requires all of:

- A remains unsolved and the target's minimum state count exceeds F0's;
- B and C cross the boundary on a valid certificate;
- F1 is exactly equivalent to the target;
- F0 is not;
- the failing provisional probe is exercised and rejected;
- rollback restores the exact F1 functional-state digest;
- final active state equals F1;
- no external model and no implicit hidden-target access occurred.

## 10. Journal and anchors

Canonical serialization is typed and length-prefixed:

```text
type_tag: one ASCII byte
length: unsigned 64-bit big-endian integer
payload: exactly length bytes
```

Supported types are absent, boolean, integer, UTF-8 string, bytes, tuple, list and mapping.
Mappings have canonical UTF-8 key order. Unknown tags, versions, non-canonical integers,
duplicate or reordered fields, truncated values and trailing bytes fail.

Domain separators are a closed set of fixed byte constants. `GENESIS_HASH` is
`SHA256(b"m038-causal-journal-genesis-v1")`.

The journal authority is the canonical persisted bytes, not mutable Python objects. Every
read decodes a fresh copy.

The first event is `EscalationCheckpointCreated`. It must:

- start from the functional-state digest derived from the checkpoint;
- reference the exact checkpoint digest;
- chain from `GENESIS_HASH`.

Internal verification proves only self-consistency. Anchored verification additionally
requires externally supplied expected initial-state digest, checkpoint digest and final head.
None defaults to a value read from the journal being checked.

A completely rewritten and rehashed chain is internally valid with a different head. No
tamper-detection claim is valid without naming the external head commitment.

Rollback is additive:

```text
RollbackRequested → restore functional state → RollbackCompleted
```

The journal and audit counters continue.

The lineage archive is reconstructed from the journal. A persisted archive digest that does
not equal the projection fails. The archive is never a second source of authority.

## 11. Tool provenance

Every available symbol in M038 has:

```text
origin = protocol_supplied
construction_kind = primitive
introduction_phase = birth
eligible_for_gate2 = false
```

No `ToolConstructed` event is required or expected. M038 makes no Gate 2 claim.

A later experiment may claim Gate 2 only for a lineage-constructed tool with a valid
construction event, committed inputs, causal use during inspection/construction/validation
and a pre-registered ablation showing necessity.

## 12. Measures

Functional vector:

- oracle queries;
- functional deterministic operations;
- certificate search nodes, pair tests and suffix probes;
- search nodes;
- candidates constructed and evaluated;
- construction operations, nodes, tool calls and bytes;
- tool calls and RNG draws;
- escalations, false escalations and missed escalations.

Proof-cost vector:

- hash operations;
- hashed-event-payload serializations;
- persisted-event serializations;
- persisted journal bytes;
- compact events recorded;
- compact batches serialized;
- compact trace bytes;
- archive projection operations;
- body serializations;
- full checkpoint serializations;
- peak persistent audit artifacts;
- audit deterministic operations.

`audit_deterministic_operations` is derived as the sum of the named operation counts, excluding
byte magnitudes and peaks. It is never incremented independently.

Dimensions that must be exactly equal between B and C:

- all functional counters;
- final functional-state digest;
- decision transcript;
- compact head, checkpoint digest and slow journal.

B must be no worse than C on every proof-cost dimension and strictly better on all three
pre-registered primary dimensions:

```text
persisted_event_serializations
journal_bytes_persisted
audit_deterministic_operations
```

`body_serializations` is non-strict because it can legitimately tie under the instrumental
superset rule. No synthetic weighted score exists.

## 13. Verdicts

M038 reports independently:

1. `infrastructure_cycle_valid`;
2. `functional_metamorphosis_supported`;
3. `efficiency_claim_supported`.

The combined expected claim is supported only if:

- A is unsolved by proved state-capacity impossibility;
- B and C have valid infrastructure cycles;
- B and C support functional metamorphosis;
- B and C are decision equivalent;
- B's evidence is a strict subset of C's;
- the efficiency rule is supported.

A functional success with an efficiency failure is a supported functional result and a
rejected efficiency hypothesis. The combined expected claim is then unsupported.

## 14. Falsifiers

Any applicable falsifier is reported and preserved:

1. a certificate bound is unsupported by its witnesses;
2. the certificate cannot be recomputed from the checkpoint;
3. A solves a task declared structurally unreachable;
4. B and C diverge in compact trace, decision transcript, functional counters, checkpoint,
   slow journal or final functional state;
5. B or C fails the F0 → F1 sequence;
6. rollback does not restore F1 exactly;
7. a deleted, altered, reordered, re-versioned or unanchored event is not detected;
8. the archive projection diverges without error;
9. B fails the pre-registered efficiency ordering against C;
10. a hidden target reaches the proposal surface;
11. any external model is invoked in the lineage;
12. any protocol-supplied tool is reported as lineage constructed;
13. the canonical guard opens on a non-marker commit;
14. the sealed result is associated with a head, parent or protocol digest other than those
    committed by the marker.

Falsifier 9 rejects efficiency, not functional feasibility. Falsifiers 1–8 and 10–14 reject
the applicable infrastructure or functional claim.

## 15. Canonical execution and result preservation

The guarded workflow checks out the exact pull-request head with two commits of history. It
first verifies the marker-only arming commit. Only then does it install the package and derive
the sealed seed.

The runner:

- recomputes the SHA-256 of these protocol bytes;
- verifies it against the marker;
- derives the sealed specification from immutable arming head and parent;
- runs A, B and C once;
- writes one canonical JSON artifact;
- exits normally for either a positive or negative scientific result;
- aborts only on integrity or execution failure.

The first workflow artifact is authoritative. A rerun can reproduce it but never replace it.
The result report must record workflow run id, artifact id, archive digest, uncompressed JSON
SHA-256, head, parent, protocol digest and sealed-spec digest.

After the first artifact is retrieved, the live canonical workflow is moved to
`archives/workflows/`; the canonical JSON and report are committed without changing this
protocol.

## 16. Consumed material

Consumed material includes:

- M035–M037 development cases;
- the 12-row exact-trigger calibration;
- development seed `380038`;
- its derived task, candidate order, witnesses, F1, counters and heads;
- every development workflow reproduction.

Consumed material may reproduce, exercise or diagnose. It may not select or confirm a
canonical rule.

## 17. Stop condition

M038 stops after one canonical DFA cycle, positive or negative.

It does not continue into:

- another seed;
- parameter tuning;
- three cycles;
- POET;
- a new body representation;
- a learned model;
- migration;
- Gate 9.

No rerun replaces the first attempt. No threshold, budget, generator, order, metric or
falsifier is relaxed after observing the canonical artifact.

## 18. Expected claim

> An exact escalation boundary can leave a compact deterministic fast path, execute one
> bounded and causally journalled metamorphosis, preserve a valid F1 across a forced rollback,
> and return to the fast path while imposing less proof cost than full critical-path
> journalling.

A negative result is valid and remains part of the repository.
