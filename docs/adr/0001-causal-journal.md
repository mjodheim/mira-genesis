# ADR 0001 — A single causal journal, with three levels of trace

**Status: accepted for development implementation.**

This authorises the canonical serialisation, the append-only journal, its integrity tests,
the projected archive and the checkpoint structures. It does **not** authorise opening a
sealed block, any M038 claim, freezing the protocol, or changing a rule after observing a
future block.

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

**`length` must itself be encoded exactly**, or the decoder cannot know where the length ends
and the payload begins. An earlier draft left this open, which made the whole encoding
underspecified. Fixed here, before any code:

```
type_tag: exactly one ASCII byte
length:   unsigned 64-bit big-endian integer, exactly 8 bytes
payload:  exactly `length` bytes
```

Element counts for lists, tuples and mappings use the **same** unsigned 64-bit big-endian
encoding.

| Tag | Type | Payload |
|---|---|---|
| `N` | absent | length 0, no bytes |
| `B` | boolean | exactly one byte, `0x00` or `0x01` |
| `I` | integer | canonical decimal ASCII, no leading zeros, minus sign only for negative values, `0` written as `0` |
| `S` | UTF-8 string | valid UTF-8, no BOM |
| `Y` | raw bytes | arbitrary bytes |
| `T` | tuple | element count, then each element encoded |
| `L` | list | element count, then each element encoded |
| `M` | mapping | field count, then each field as name (`S`) followed by its encoded value |

| Aspect | Decision |
|---|---|
| Field order | canonical, sorted by field name as UTF-8 bytes, declared per schema |
| Absent | tag `N`, distinct from an empty string, an empty list, and `false` |
| Schema version | mandatory; an unknown version is a replay failure, never a skip |
| Hash | SHA-256 |

### Domain separators are fixed byte constants

A domain separator supplied freely by the caller is not a separator: two call sites could
pass the same string, or one could pass a value derived from data. They are fixed constants,
one per decision, never reused:

```
DOMAIN_CAUSAL_EVENT     = b"m038-causal-event-v1"
DOMAIN_FUNCTIONAL_STATE = b"m038-functional-state-v1"
DOMAIN_CHECKPOINT       = b"m038-escalation-checkpoint-v1"
DOMAIN_COMPACT_TRACE    = b"m038-compact-trace-v1"
DOMAIN_TOOL             = b"m038-tool-v1"
DOMAIN_PROJECTED_ARCHIVE = b"m038-projected-archive-v1"

GENESIS_HASH = SHA256(b"m038-causal-journal-genesis-v1")
```

The journal API accepts a domain only from this closed set. A test asserts that no domain
constant is a prefix of another and that none is caller-supplied.

**Test obligation, stated realistically.** Proving that no two logically different structures
can ever collide is not achievable by testing. What is required instead: a documented
argument that the encoding is typed and length-prefixed, plus property tests over the known
confusable pairs — string against integer, empty against absent, tuple against list, a field
whose content contains a separator byte, and nested structures.

## External anchoring

Discovered during implementation and added before any claim rests on the chain. An ADR
`accepted for development implementation` is not immutable: the protocol is not frozen and no
M038 result exists, so a limit found while building the mechanism is integrated rather than
left as a footnote.

```
An internally consistent hash chain proves integrity only relative to an
expected head committed outside that chain.

A party that rewrites every event and recomputes every hash obtains another
internally valid chain with a different head.

Therefore:

- internal verification is necessary but not sufficient;
- the initial functional-state digest must be anchored to the escalation checkpoint;
- the checkpoint digest must be bound to the first causal event;
- the completed journal head must be compared with an externally committed expected head;
- a canonical result may not claim tamper detection without naming where that expected
  head was committed.
```

For a future canonical run, the expected head is recorded in an immutable artifact tied to
the commit and the canonical workflow. For development, the API already accepts it.

The two levels are therefore two methods, not one method with a lenient default:

| Method | Establishes |
|---|---|
| `verify_internal_consistency()` | the chain holds itself together — a wholly rebuilt chain also passes |
| `verify_against(expected_initial_state_digest, expected_head, expected_checkpoint_digest)` | the chain is the history committed elsewhere |

`verify_against` takes every expected value as a **required** argument. None of them defaults
to the journal's own state: an anchor read back from the thing it anchors proves nothing.

### The first event binds the checkpoint

`GENESIS_HASH` stays the fixed root, but the first event must be
`EscalationCheckpointCreated` and must carry the checkpoint digest in
`immutable_input_digests`. Verification refuses:

- a non-empty journal whose first event is of another type;
- a first event that does not reference the expected checkpoint;
- an initial state digest differing from the functional state held in that checkpoint.

The journal therefore keeps `initial_state_digest` and `state_digest` separately. The first
never moves; the second follows the functional continuation. Conflating them leaves the first
event's `previous_state_digest` compared against nothing, which is exactly the gap a rebuilt
chain exploits.

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

The chain's first record uses `previous_event_hash = GENESIS_HASH`, defined above as
`SHA256(b"m038-causal-journal-genesis-v1")` — a fixed constant, not a zero digest, so a
truncation to an empty chain cannot masquerade as a valid root.

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
- disabling the detailed journalling changes the produced evidence and **not** any decision;
- the encoding round-trips: decoding consumes exactly the bytes the encoder produced, with no
  trailing remainder, for every tag;
- a truncated length field, a truncated payload, and a payload longer than its declared
  length are each rejected rather than silently accepted;
- the known confusable pairs encode differently — `1` against `"1"`, `""` against absent,
  `false` against absent, a tuple against a list of the same elements, a field whose content
  contains a domain constant's bytes, and nested structures;
- no domain constant is a prefix of another, and none is caller-supplied;
- a wholly rebuilt chain passes internal verification and fails against an externally
  committed head;
- a first event carrying a forged `previous_state_digest`, with every downstream hash
  recomputed, is rejected by the initial-state anchor;
- `verify_against` exposes no default for any expected value;
- a journal opening with another event type, or whose opening event does not reference the
  expected checkpoint, or whose initial state is not the checkpoint's functional state, is
  rejected;
- an event read from the journal cannot be mutated into the record, because the authority is
  the stored canonical bytes and each read decodes a fresh copy.
