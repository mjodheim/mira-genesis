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
| `i32_binary` | `(i32, i32) -> i32` | M058's shape over integers; each operation is named by what it computes |
| `local_set` | `(i32 x) -> i32`, one spare local | the local is written, then read back and added to a constant |
| `unconditional_branch` | `(i32) -> i32` | a branch lands after the block and has one added to it; a return never comes back |

The scaffold shape is authored, exactly as M058's two-operand shape was. What is discovered is
which byte fills the hole.

## Two stages, because a discovery enables the next one

The last two shapes cannot observe their candidate without an addition, and writing `0x6a` into the
scaffold that discovers opcodes would be the shortcut this experiment exists to remove. So the scan
runs in two stages: the first four shapes are self-contained, and the integer scan supplies the
addition that the last two are built from.

## Three hazards this scan has and M058's did not

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

**A constant can be quietly negative.** Scaffold constants are emitted as one SLEB128 byte, where
bit `0x40` is the sign. A version that wrote 33 as 99 produced −29, its witness vanished, and the
scan disqualified itself — which is the mechanism working. Every scaffold constant stays below 64.

## Refusing rather than choosing

Where the probes do not separate two candidates, the scan reports the ambiguity, and every
ambiguity found so far was resolved by **widening the probe rather than loosening the resolver**.

- A one-byte value cannot separate the stores of width one, two and four. Writing a value that
  overflows a byte and reading the neighbouring cells gives each width a different footprint.
- A pattern whose bytes are all positive cannot separate the signed and unsigned byte loads. A
  second call plants `0xFF`, where the unsigned form returns 255 and the signed form returns −1.
- Ending the `local_set` shape on the constant made `local.set` and `drop` identical, because
  nothing read the local back. Ending it on `local.get 1` made `local.set` and `return` identical,
  because both surface the parameter. Reading the local *and* adding the constant separates all
  three.
- The `unconditional_branch` shape matched `br` and `return` alike until one was added to the
  block's result: a branch lands after `end` and is incremented, a return never comes back.

One remains unresolved and is recorded as such: `0x2e` and `0x2f` both read two bytes, and both
planted patterns are positive in that width. The manifest names them rather than preferring one.

## Required lineage

1. scan all 256 opcodes in each of the four first-stage shapes;
2. recover each scaffold's witness, or stop;
3. characterise loads by width and signedness, stores by footprint, integer operations by what
   they compute;
4. scan the two staged shapes using the addition the first stage recovered;
5. resolve the ten instructions M060 authored, refusing where the probes do not separate;
6. check the resolution against what M060's emitter writes;
7. build a working loop from the recovered instructions and compute with it.

## The falsifier

Step 7 exists because naming a byte is not the same as being able to build with it. A byte-copy
loop exercises load, store, both branches, the local write and the integer arithmetic together; if
the discovery named the wrong bytes the module fails to validate or moves the wrong data.

A permanent test substitutes the unconditional branch for the conditional one and asserts the loop
then copies nothing. Another asserts the loop refuses to be built at all when a required
instruction is missing from the resolution, so there is no silent fallback to an authored byte.

**What that control does not catch is recorded too.** Substituting the four-byte store for the
one-byte store leaves the copied range correct, because each iteration overwrites the previous
iteration's trailing zeros. The width shows only past the end of the range, which this loop never
reads. The control is real for the branch and blind to that substitution.

## The floor

`local.get`, `i32.const`, the `end` that closes every body, the module framing and the signature
shape are **presupposed**. Every scaffold must present an operand and return a result, so it cannot
discover the instructions that do those things. A scaffold avoiding them would have no way to
observe anything.

`block` and `loop` stay authored for a different reason: they are not instructions with an
observable effect on a value. They open a region and decide where a branch lands, and a scaffold
using one to expose the other would assume what it set out to find. The blocktype byte and the
label immediates are part of the encoding rather than opcodes at all.

The manifest names these at the same level as what was discovered. The compiler that arranges the
discovered instructions also remains authored.

## Anti-cheating

M061 does not pass if any opcode list is supplied to a scan, if a scaffold reports a result while
missing its witness, if an ambiguity is resolved by preferring one candidate, if the copy loop
falls back to an authored byte for an instruction the scans did not recover, or if the manifest
claims the loop uses only discovered instructions while the builder writes any in.

That last clause is there because an earlier version of this experiment did exactly that.

## Qualification rule

M061 may pass in development only when the complete Python 3.11 and Python 3.13 matrices and the
repository-integrity job pass on the exact documented head. A run that fails before the
experiment's code executes is an infrastructure event under D017 and is not a verdict.

## Claim boundary

One substrate, six shapes, ten instructions. M061 does not establish arbitrary runtime discovery,
unrestricted code generation, open-ended evolution, general intelligence, consciousness or
production safety. Network, repository, credential, deployment and external-system authority remain
human-controlled.

M061 is noncanonical. M042 remains the only positive canonical continuous-lineage completion.
