# M039 — three-cycle cumulative lineage with causal tool reuse

**Status: PRE-RESULT DEVELOPMENT PROTOCOL.** No sealed block exists, no canonical task has
been derived, and no Gate 2 or Gate 9 claim is authorised by this document.

## 1. Question

Can one bounded lineage, starting from one founder and one immutable seed:

1. complete three sequential, strictly improving metamorphosis cycles;
2. preserve its functional body, portable state and tool registry between cycles;
3. construct a tool from committed primitive tools during cycle 1;
4. causally reuse that earlier tool in an adopted trace during a later cycle;
5. show by equal-budget ablation that the claimed tool use was load-bearing rather than
   incidental registry membership;
6. survive a failing provisional change and restore the last accepted body;
7. replay the whole lineage from the original seed and immutable protocol inputs, including
   task generation, oracle observations, proposals, rejections, costs, tool construction,
   tool use, adoptions, rollback and all externally anchored journal heads?

M039 is a direct continuation of two bounded results:

- M037 reached adopted-mutation replay from a supplied founder, not full causal replay;
- M038 reached one frozen two-speed F0 → F1 cycle, not three cycles or earlier-tool reuse.

M039 must integrate them. It may not describe three independent M038 runs as one lineage.

## 2. Non-claims

Before a separate frozen canonical run, every M039 output is development evidence only.
Even a positive development run does not establish:

- Gate 2;
- Gate 9;
- trans-substrate migration;
- post-migration plasticity;
- open-ended improvement;
- general intelligence or consciousness.

M039 remains in the decidable deterministic-DFA domain.

## 3. One lineage, not three resets

The functional state carried across the experiment is:

```text
active body
portable learning state
tool registry
lineage generation
accepted-cycle count
RNG algorithm and state, where any RNG exists
```

Cycle `n + 1` receives the exact accepted state of cycle `n`. It may not reconstruct a new
founder from the seed, clear the registry, or silently restore birth-state counters.
Audit state remains append-only across all rollbacks.

The experiment succeeds functionally only if all three accepted bodies form one strict chain:

```text
F0 -> F1 -> F2 -> F3
```

For every cycle `i`:

- `Fi` is not exactly equivalent to its hidden target before the cycle;
- `F(i+1)` is exactly equivalent after adoption;
- the target's exact minimal state count exceeds the current body's state count;
- an exact structural-incapacity certificate is obtained from admitted oracle evidence;
- the no-growth control is therefore impossible by capacity, not merely unsuccessful.

## 4. Tool provenance and the only admissible reuse claim

Birth registry entries are protocol-supplied primitive structural symbols. They never count
as autonomous construction.

After cycle 1 accepts its transformation, the lineage may compose one macro tool from the
primitive symbols in the accepted trace. The construction must be represented by a
`ToolConstructed` causal event naming:

- the lineage identity and generation;
- the cycle in which construction occurred;
- every consumed registry tool ID;
- the canonical program or IR;
- the protocol commitment;
- a replay digest;
- the event hash that introduced it.

The resulting provenance axes are fixed:

```text
origin = lineage_constructed
construction_kind = composition
introduction_phase = cycle
```

`eligible_for_gate2` is computed, never accepted from serialized input. It can become true
only if the construction event verifies, all inputs were already committed, and equal-budget
ablation later shows that this tool was causally required to inspect, transform, build or
test an adopted candidate.

A later tool-reuse claim is valid only when the adopted trace records the earlier tool ID as
a proposing block. Registry membership, availability, target generation, or post-hoc trace
compression do not count.

## 5. Cost rule

A registry tool is one structural symbol at proposal depth, while its complete primitive
expansion is recorded and charged in deterministic construction operations. This is the
same distinction already stated in ADR 0003:

- macro depth governs reachable search under a bounded symbolic budget;
- primitive expansion cost remains visible and cannot disappear from accounting.

The protocol must report both. It may not claim that a macro extends the mathematical
reachable set without naming this symbolic cost rule.

## 6. Task family

The laboratory derives one three-task chain from an immutable 64-bit seed only after the
future arming commit exists.

The generator is deterministic and bounded:

1. derive one minimal four-state founder;
2. derive cycle 1 from a primitive-only reachable program whose exact target requires a
   larger minimal body and whose incapacity certificate is available from the committed
   observation set;
3. construct the cycle-1 lineage tool from the accepted trace;
4. derive cycles 2 and 3 from the current accepted body using a program containing that
   earlier tool plus committed primitives;
5. reject a generated task unless primitive-only search under the same later-cycle symbolic
   depth and node budget cannot solve it exactly;
6. reject it unless the full registry search can solve it and the adopted trace actually
   contains the earlier tool ID.

The target is visible only to the task generator and independent exact evaluator. Candidate
proposal receives the current body, admitted evidence, committed registry and budgets, never
the target.

Development seeds and all tasks they reveal are consumed by implementation decisions. They
may not later validate the canonical claim.

## 7. Committed development bounds

The first implementation must use explicit constants and report them in every artifact:

| Bound | Development value |
|---|---:|
| cycles | 3 |
| alphabet | `{0, 1}` |
| observation maximum word length | 6 |
| founder minimal states | 4 |
| cycle-1 symbolic search depth | 3 |
| later-cycle symbolic search depth | 2 |
| task-generation attempts per cycle | 32 |
| task-generation programs per attempt | 100,000 |
| candidate search nodes per cycle | 150,000 |
| exact certificate search nodes | inherited committed M038 bound |
| exact certificate prefix count | inherited committed M038 bound |

Changing one after a development outcome consumes the prior task and requires a new recorded
protocol revision. No bound may be widened during a frozen run.

## 8. Controls

### Capacity control

For each task, the pre-cycle body is evaluated without capacity increase. Failure must be
backed by the exact lower bound exceeding its minimal state count.

### Tool ablation

Cycles 2 and 3 are repeated with the earlier lineage-constructed tool removed while every
other immutable input, target, primitive, ordering rule and budget remains identical.

The strong causal-reuse criterion is:

```text
full registry succeeds
and adopted trace contains the earlier tool ID
and equal-budget ablation fails to produce an exact candidate
```

If ablation succeeds, the tool may still have been used, but it was not shown causally
required and neither Gate 2 eligibility nor load-bearing reuse is supported.

### Replay control

Replay receives only:

- the original seed;
- frozen protocol commitment and constants;
- initial primitive registry specification;
- externally committed expected root/head/digest values.

Replay may not receive a founder DFA, hidden target DFA, admitted answer table, accepted
program, selected candidate ID, mutation chain, tool-construction output or final body from
the original run.

It must recompute and match:

- founder and all three targets;
- every observation and evidence digest;
- all certificates and budgets consumed;
- proposal and evaluation ordering, including rejected candidates;
- all tool-construction and reuse events;
- each accepted body and failed provisional body;
- rollback targets;
- functional and audit counters;
- compact trace heads, checkpoint digests and causal journal heads;
- final lineage manifest and final body digest.

## 9. Required event semantics

M039 may reuse M038 typed encoding and hash rules but must represent the multi-cycle facts
explicitly. Required semantics include:

```text
LineageStarted
CycleEscalationCheckpointCreated
StructuralIncapacityCertified
CandidateProposed
CandidateEvaluated
CandidateRejected
MutationProvisionallyAdopted
MutationAdopted
ToolConstructed
ToolReused
RollbackRequested
RollbackCompleted
CycleCompleted
LineageCompleted
```

If the M038 closed event vocabulary cannot express `ToolReused` or repeated checkpoints,
M039 must introduce a separately versioned journal schema. It must not mutate the frozen
M038 schema and pretend the old canonical artifact was produced by the new code.

## 10. Falsifiers

The expected M039 claim is false if any of the following occurs:

1. fewer than three cycles are accepted;
2. any cycle is not a strict F(i) → F(i+1) functional improvement;
3. any capacity control lacks an exact impossibility certificate;
4. the body, portable state or registry is reset between cycles;
5. the constructed tool lacks a valid causal construction event or committed inputs;
6. no later adopted trace names the earlier tool as a proposing block;
7. equal-budget ablation also solves every claimed reuse cycle;
8. a provisional failure does not restore the exact previous accepted functional digest;
9. replay reads any generated target, accepted trace or final body from the original result;
10. replay diverges in any proposal, rejection, counter, event byte, anchor or final digest;
11. a protocol-supplied or externally developed tool is reported as lineage-constructed;
12. a result is selected from multiple seeds, widened budgets or replacement first runs;
13. unit tests or ordinary CI open a future sealed block;
14. any M038 artifact, protocol hash or first-run identity is rewritten.

## 11. Development sequence

1. implement an independently versioned M039 lineage journal and manifest;
2. implement deterministic three-cycle task generation;
3. implement persistent tool registry with computed provenance;
4. implement candidate proposal with symbolic macros and explicit primitive expansion cost;
5. implement equal-budget tool ablation;
6. implement full seed-to-head replay and mutation tests;
7. run only committed development seeds and mark every revealed task consumed;
8. review failures and freeze a separate canonical protocol only after the mechanism and
   falsifiers are stable.

No canonical workflow, marker or sealed seed belongs in this draft PR until those eight steps
are complete and reviewed.