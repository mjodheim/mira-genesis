# M039 development implementation commitment

**Status: committed before the first integrated engine execution.**

This file fixes the first development run's inputs so that its task chain cannot be chosen
after observing whether the engine succeeds.

## Identity

| Field | Committed value |
|---|---|
| development seed | `390039` |
| protocol commitment | `m039-development-v1` |
| cycles | `3` |
| founder generator | `random_minimal_dfa(cycle_seed_1, 4, 4)`, normalized |
| observation words | every binary word of length at most `6` |
| cycle-1 symbolic depth | `3` |
| cycles 2 and 3 symbolic depth | `2` |
| task-generation attempts | `32` |
| task-generation program ceiling | `100000` |
| candidate-search node ceiling per cycle | `150000` |
| certificate bounds | M038's committed exact bounds |
| rollback probe | `flip(initial)` after every accepted cycle |

## Registry and cost semantics

The birth registry contains the existing structural atoms plus the separately declared growth
atoms. Each is `origin = protocol_supplied`, `construction_kind = primitive`, introduced at
birth, and permanently ineligible for Gate 2.

Cycle 1 searches the birth registry to depth 3. Its accepted expanded trace is composed into
one lineage-owned macro. The macro is one symbol at later proposal depth, while every
expanded primitive application remains charged.

Cycles 2 and 3 are generated only when:

- their target is exactly reachable using the earlier macro at symbolic depth 2;
- the target's minimal state count exceeds the active body's count;
- an exact incapacity certificate is available from the committed observations;
- primitive-only search to the same symbolic depth cannot reach an equivalent body.

The later adopted trace must name the macro as a proposing block. Registry presence alone is
not reuse.

## Replay

The original execution and replay call the same deterministic engine independently. Replay
receives only the master seed, protocol commitment, primitive-registry digest and external
expected digests/heads. It does not receive generated DFAs, evidence, candidates, programs,
registry outputs or selected mutations.

Success requires byte-identical M039 journal records, not merely the same final DFA.

## Consumption rule

The first GitHub workflow execution that reaches `run_m039_development()` consumes seed
`390039` and every task it reveals, whether the result is positive, negative or an exception.

Those tasks may be used to diagnose and repair implementation defects. They may not support
a later canonical claim, select a replacement seed, justify wider budgets or confirm a
revised mechanism.

No sealed block, canonical marker or canonical workflow exists in M039 at this stage.