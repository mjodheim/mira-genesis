# M061 — development result

## Status

**POSITIVE ON ITS CENTRAL QUESTION — PENDING QUALIFICATION.**

The instructions that move data and direct control were discovered, and they compute. This is a
bounded, noncanonical development result.

## What was observed

| Observation | Value |
|---|---|
| Opcode space scanned, per scaffold | **256** |
| Scaffolds | `memory_load`, `memory_store`, `conditional_branch` |
| Witnesses recovered | **3 / 3** |
| Candidates that never terminate | **1 per scaffold** |
| Structural instructions resolved | **5** |
| Match what M060 authored | **all five** |
| Shapes the probes could not separate | `0x2e`, `0x2f` |
| Copy loop from discovered instructions alone | 97 bytes, phrase recovered |

| Instruction | Recovered as | How |
|---|---|---|
| `i32.load8_u` | `0x2d` | one byte, unsigned |
| `i32.load` | `0x28` | four bytes |
| `i32.store8` | `0x3a` | footprint of one byte |
| `i32.store` | `0x36` | footprint of four bytes |
| `br_if` | `0x0d` | returned 7 when taken, 9 when not |

## The branch

This is what M060 said was qualitatively harder, and it is the substance of the result.

A conditional branch produces no value. The scaffold gives it one: a block that leaves `7` on the
stack and branches out, or falls through to `9`. `0x0d` returns `7` on a true condition and `9` on
a false one, and nothing else in 256 candidates does. The instruction was identified purely by
what it caused to happen.

## What the instrument had to survive

**A malformed scaffold is silent.** A first attempt emitted the memory section before the function
section, which the format forbids, and the substrate refused all 256 candidates in every shape.
*Nothing exists* and *the instrument is broken* produce identical output, and two attempts were
lost before the cause was found.

Every scaffold now declares a witness it must recover, and a permanent test builds a deliberately
misordered module and asserts it is refused.

**Some candidates never terminate.** `0x12` is a tail call. A scaffold calling its own function
through it recurses without growing the stack: it never traps and never returns. `0x10`, an
ordinary call, exhausts the stack and traps — the two differ only in whether the loop is
observable as a failure. Each scan counts exactly one non-terminating candidate, and each
candidate runs in its own process under a deadline because nothing inside the probe can decide
termination.

M058's arithmetic scan met neither hazard: its scaffold was trivially well-formed, and every
candidate returned.

## Refusing rather than choosing

The probes were too weak twice, and both times the **probe was widened rather than the resolver
loosened**.

A one-byte value cannot separate stores of width one, two and four — writing `0x5E` and reading
that cell looks the same for all three. Writing a value that overflows a byte and reading the
neighbouring cells gives each width a different footprint.

A pattern whose bytes are all positive cannot separate the signed and unsigned byte loads. The
scan reported them as unresolved, correctly; a second call planting `0xFF` separates 255 from -1.

One ambiguity remains and is recorded rather than arbitrated: `0x2e` and `0x2f` both read two
bytes, and both planted patterns are positive in that width.

## What the falsifier catches, and what it does not

Naming a byte is not the same as being able to build with it, so the recovered instructions were
assembled into a byte-copy loop — load, store and branch working together — which recovers its
phrase exactly.

Substituting the unconditional branch for the conditional one makes the loop copy nothing, so the
control is real.

**Substituting the four-byte store for the one-byte store does not break it**, and that is
recorded. Each iteration writes its byte plus three zeros and the next iteration overwrites them;
the width only shows past the end of the copied range, which the loop never reads. The control
falsifies the branch and is blind to that substitution. Saying so is better than implying the loop
falsifies everything it is given.

## The floor

`local.get`, `i32.const`, the module framing and the signature shape are **presupposed**. Every
scaffold presents an operand and returns a result, so it cannot discover the instructions that do
those things; a scaffold avoiding them would have no way to observe anything.

The compiler that arranges the discovered instructions also remains authored. M061 removes the
authored *instruction set* for structure, not the authored *compiler*.

## Claim boundary

One substrate, three shapes, five instructions, one loop. M061 does not establish arbitrary
runtime discovery, unrestricted code generation, open-ended evolution, general intelligence,
consciousness or production safety. Network, repository, credential, deployment and
external-system authority remain human-controlled.

M061 is noncanonical. **M042 remains the only positive canonical continuous-lineage
completion.**

## The line

| Experiment | What was handed | What was found |
|---|---|---|
| M048 | a compiler, a runtime, an instruction to migrate | nothing about the crossing |
| M056 | a compiler, a substrate | that acquisitions survive a second crossing |
| M057 | six named operations | what they do, how to compose them |
| M058 | a signature shape | which arithmetic exists |
| M059 | two shapes, no ranking | whether to move at all, and where |
| M060 | the structural instruction set | that the whole body can cross |
| M061 | three scaffold shapes and a floor | **which structural instructions exist** |

What remains handed is the compiler that arranges them, the scaffold shapes, and the tasks that
arrive.
