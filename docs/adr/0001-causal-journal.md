# ADR 0001 — A single causal journal, with three levels of trace

**Status: proposed for M038. Awaiting human review. No mechanism implemented yet.**

## Context

M037 established *adopted-mutation replay from a supplied founder*. That is level 2 of
three:

| Level | Meaning |
|---|---|
| 1 | body reconstruction |
| 2 | replay of the adopted transformations from a supplied founder |
| 3 | causal reproduction of the whole trajectory from the seed and committed inputs |

Gate 9 requires level 3. Reaching it needs a record of what actually happened, not only of
what was kept.

The obvious implementation is fatal. Emitting a full causal event — with a digest of the
state before and after — on every micro-operation would put the proof machinery inside the
hot loop. A depth-3 search over 44 symbols evaluates up to 85,184 candidates, and hashing
two complete automata per candidate would dominate everything the organism does. The proof
would cost more than the thought.

## Decision

**One append-only, hash-chained journal is the single source of authority.** The lineage
archive is a *projection* of it, never a second persisted state that could drift.

Three levels of trace, with different costs:

### 1. Light diagnostic trace — fast path

Per operation: an operation id, a counter, a cost, a compact result, references to
observations, and a success or failure code. **No digest of the body.** This is not
sufficient for causal replay and must never be described as if it were.

### 2. Rolling commitment — fast path

A rolling hash over the *compact events*, not over the body:

```
fast_trace_hash[n] = H( domain ‖ fast_trace_hash[n-1] ‖ canonical_fast_event[n] )
```

This adds one hash of a small record per operation. If even that proves too costly, a
**batched commitment every N operations** is permitted, with N fixed before any
measurement.

This is what lets the slow path prove *why* it was entered. Without it the journal would
begin at the escalation and the escalation itself would be unexplained.

### 3. Escalation checkpoint — the boundary

Serialised once, at the frontier:

- the relevant cognitive state;
- the body;
- the portable memory;
- the tool registry;
- the cost counters;
- **the seed and the RNG state**;
- the last rolling hash;
- the observations justifying the escalation.

The checkpoint is the immutable input of the full causal journal. Everything after the
boundary is fully journalled.

## Determinism is two classes, not one

The kernel was described in review as deterministic. That is false in the strict sense:
`offspring` in `m035_evolution.py` consumes a pseudo-random generator.

| Class | Meaning |
|---|---|
| `pure_deterministic` | same inputs, same output, no random source consulted |
| `seeded_reproducible` | reproducible **only** if the seed, the generator algorithm, its version, its initial state, the exact order of consumptions, and every operation that may consume the stream are all committed |

**The journal must never label a seeded operation as purely deterministic**, even when it
reproduces under the same seed. Component records carry the class explicitly, and a test
asserts that any component consuming the generator is classified `seeded_reproducible`.

This is why M037's capacity reduction derives its ordering from a separate hash rather than
the mutation generator: sharing the stream would make the count of admitted organisms shift
every later variation, coupling selection to variation through the random state.

## What M038 may and may not claim

M038 does **not** replay every fast-path micro-operation. It proves that the slow path
begins from a committed checkpoint whose compact history has not been altered.

That is **not level 3**, and the protocol must say so in those words.

## What the rolling hash does and does not prove

It proves that the recorded compact trace **has not been altered or reordered after the
fact**.

It does **not** prove, on its own:

- that every real event was recorded;
- that the events correctly describe the internal transitions;
- that the final state follows causally from the whole trace;
- that the fast path can be replayed in full.

The protocol must therefore use the bounded wording:

> **M038 commits the integrity and order of a compact prehistory, then begins full causal
> replay from an escalation checkpoint.**

It may not claim full causal replay of the fast path.

## Canonical serialisation, fixed before any code

A hash built by joining strings with a separator is ambiguous: two logically different
structures can produce the same byte sequence when a field contains the separator. That
would silently break every integrity claim built on it.

Length prefixing removes separator ambiguity. It does **not** remove *type* ambiguity: with
lengths alone, the integer `1` and the string `"1"` can share bytes. The encoding is
therefore **typed and length-prefixed**:

```
value := type_tag ‖ length ‖ payload
```

| Tag | Type |
|---|---|
| `N` | absent |
| `B` | boolean |
| `I` | integer |
| `S` | UTF-8 string |
| `Y` | raw bytes |
| `T` | tuple |
| `L` | list |
| `M` | mapping |

| Aspect | Decision |
|---|---|
| Field order | canonical, sorted by field name, declared per schema |
| Integers | decimal ASCII, no padding, explicit minus sign |
| Sequences | element count first, then each element typed and length-prefixed |
| Mappings | field count, then each field name encoded, canonical order, typed values |
| Absent | tag `N`, distinct from an empty string or empty list |
| Schema version | mandatory; an unknown version is a replay failure, never a skip |
| Domain separators | one per decision, never reused |
| Hash | SHA-256 |

**Test obligation, stated realistically.** Proving that no two logically different structures
can ever collide is not achievable by testing. What is required instead: a documented
argument that the encoding is typed and length-prefixed, plus property tests over the known
confusable pairs — string against integer, empty against absent, tuple against list, a field
whose content contains a separator byte, and nested structures.

## Rollback does not rewrite the journal

An append-only journal and an "exact rollback" are only compatible if two kinds of state are
separated:

| Kind | Contents | Restored by rollback? |
|---|---|---|
| `functional_state` | active body, portable memory, tool registry, exploration state, uncertainty, functional counters, RNG state where it influences continuation | **yes, exactly** |
| `audit_state` | the journal, its hashes, the audit counters | **no — it continues** |

Rollback is therefore three steps, all additive:

1. append a rollback request event;
2. restore the functional state;
3. append an event attesting the rollback outcome.

Nothing is erased or overwritten. "Exact rollback" is a claim about `functional_state` only,
and the protocol must say so.

## Event schema

```
sequence
event_type
schema_version
protocol_commitment
previous_event_hash
previous_state_digest
immutable_input_digests
operation_parameters
costs
result_state_digest
event_hash
```

`event_hash` must exclude itself, or the definition is circular:

```
event_hash = SHA-256( domain ‖ canonical_serialisation(all fields except event_hash) )
```

The chain's first record uses `previous_event_hash = GENESIS_HASH`, a fixed constant under
its own domain separator.

`previous_state_digest` and `result_state_digest` cover the **`functional_state` only**. They
do not include the journal being produced; the audit state is bound by
`previous_event_hash` instead. Without that split, a state digest would have to contain the
hash of the event containing it.

### Event types

An earlier draft listed seven, including `PopulationReduced` — which has no object in M038,
a single-organism lineage — and omitted rollback entirely, while the same ADR requires
rollback events. Aligned on the mechanism M038 actually needs:

```
EscalationCheckpointCreated
StructuralIncapacityCertified
CandidateProposed
CandidateEvaluated
CandidateRejected
MutationProvisionallyAdopted
MutationAdopted
RollbackRequested
RollbackCompleted
ToolConstructed
CycleCompleted
```

Only those actually emitted are implemented. None is added for a mechanism that does not
exist.

Replay must recompute transitions and fail when an event is missing, altered, reordered, or
carries an unknown schema version.

## Alternatives rejected

**Full causal event on every operation.** Rejected on cost: it places the proof machinery in
the hot loop, which is the specific failure this design exists to avoid.

**Journal starting at the escalation, with no prior commitment.** Rejected because it cannot
demonstrate why the escalation occurred. The rolling hash costs one small hash per operation
and closes that hole.

**A lineage archive with independent state, synchronised with the journal.** Rejected: two
persisted sources of truth diverge, and the divergence is invisible until it matters. The
archive is reconstructed from the journal and compared against any persisted copy.

**Digesting the body in the rolling hash.** Rejected on the same cost grounds as the first
option. The rolling hash covers the compact event; the body digest appears only in
checkpoints and slow-path events.

## Test obligations

- an archive reconstructed from the journal matches the persisted archive digest-for-digest;
- an archive modified without a corresponding event is detected;
- replay fails on a missing, altered, or reordered event, and on an unknown schema version;
- a component consuming the RNG is classified `seeded_reproducible`;
- disabling the detailed journalling changes the produced evidence and **not** any decision.
