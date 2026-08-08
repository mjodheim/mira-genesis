# M061 — discovering the instructions that move data and control

**Status: PROPOSED — unqualified.**

## Research question

Can the instructions that move data and direct control be discovered the way M058 discovered
arithmetic — when a branch has no value to compare against, only an effect on what runs next?

## What M060 left

M060 migrated the whole body and authored every structural instruction it used: loads, stores,
branches, loops, calls, the memory layout. Its result named that as the next thing to remove, and
named the difficulty.

## The method

Place the candidate in a scaffold whose **return value depends on its effect**.

| Scaffold | Shape | How the effect becomes observable |
|---|---|---|
| `memory_load` | `(i32 address) -> i32` | a known pattern is planted; what comes back characterises the width and the signedness |
| `memory_store` | `(i32 address, i32 value) -> i32` | an overflowing value is written and the neighbouring cells are read; the footprint gives the width |
| `conditional_branch` | `(i32 condition) -> i32` | the body returns 7 when the branch is taken and 9 when it is not |

The scaffold shape is authored, exactly as M058's two-operand shape was. What is discovered is
which byte fills the hole.

## Two hazards this scan has and M058's did not

**A malformed scaffold is silent.** A first attempt emitted the memory section before the function
section, which the format forbids, and the substrate refused all 256 candidates. *Nothing exists*
and *the instrument is broken* produce identical output.

Every scaffold therefore declares a **witness** it must recover. A scan that misses its witness
disqualifies itself, and its silence is not a result about the substrate. A permanent test builds
a deliberately malformed module and asserts it is refused.

**Some candidates never terminate.** `0x12` is a tail call: a scaffold calling its own function
through it recurses without growing the stack, so it never traps and never returns. `0x10`, an
ordinary call, exhausts the stack and traps instead — the two differ only in whether the loop is
observable as a failure.

Termination is therefore a third outcome alongside *refused* and *observed*, enforced by running
one candidate per process under a deadline. Nothing inside the probe can decide it.

## Refusing rather than choosing

Where the probes do not separate two candidates, the scan reports the ambiguity.

Two were found and both were resolved by **widening the probe rather than loosening the
resolver**: a one-byte value cannot separate the stores of width one, two and four, and a pattern
whose bytes are all positive cannot separate the signed and unsigned byte loads.

One remains unresolved and is recorded as such: `0x2e` and `0x2f` both read two bytes, and both
planted patterns are positive in that width. The manifest names them rather than preferring one.

## Required lineage

1. scan all 256 opcodes in each of the three shapes;
2. recover each scaffold's witness, or stop;
3. characterise loads by width and signedness, stores by footprint;
4. resolve the five instructions M060 authored, refusing where the probes do not separate;
5. check the resolution against what M060 wrote;
6. build a working loop from the recovered instructions alone and compute with it.

## The falsifier

Step 6 exists because naming a byte is not the same as being able to build with it. A byte-copy
loop exercises load, store and branch together; if the discovery named the wrong bytes the module
fails to validate or moves the wrong data.

A permanent test substitutes the unconditional branch for the conditional one and asserts the loop
then copies nothing.

**What that control does not catch is recorded too.** Substituting the four-byte store for the
one-byte store leaves the copied range correct, because each iteration overwrites the previous
iteration's trailing zeros. The width shows only past the end of the range, which this loop never
reads. The control is real for the branch and blind to that substitution.

## The floor

`local.get`, `i32.const`, the module framing and the signature shape are **presupposed**. Every
scaffold must present an operand and return a result, so it cannot discover the instructions that
do those things. A scaffold avoiding them would have no way to observe anything.

This is a real limit, and the compiler that arranges the discovered instructions remains authored.

## Anti-cheating

M061 does not pass if any opcode list is supplied to a scan, if a scaffold reports a result while
missing its witness, if an ambiguity is resolved by preferring one candidate, or if the copy loop
uses an instruction the scans did not recover.

## Qualification rule

M061 may pass in development only when the complete Python 3.11 and Python 3.13 matrices and the
repository-integrity job pass on the exact documented head. A run that fails before the
experiment's code executes is an infrastructure event under D017 and is not a verdict.

## Claim boundary

One substrate, three shapes, five instructions. M061 does not establish arbitrary runtime
discovery, unrestricted code generation, open-ended evolution, general intelligence, consciousness
or production safety. Network, repository, credential, deployment and external-system authority
remain human-controlled.

M061 is noncanonical. M042 remains the only positive canonical continuous-lineage completion.
