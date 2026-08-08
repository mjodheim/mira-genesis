# M061 — development result

## Status

**POSITIVE ON ITS CENTRAL QUESTION — PENDING QUALIFICATION.**

The instructions that move data and direct control were discovered, and they compute. This is a
bounded, noncanonical development result.

## What was observed

| Observation | Value |
|---|---|
| Opcode space scanned, per scaffold | **256** |
| Scaffolds | six, in two stages |
| Witnesses recovered | **6 / 6** |
| Candidates that never terminate | **4**, and only in the shapes that can recurse |
| Structural instructions resolved | **10** |
| Match what M060's emitter writes | **all ten** |
| Shapes the probes could not separate | `0x2e`, `0x2f` |
| Copy loop | 97 bytes, phrase recovered |

| Instruction | Recovered as | How |
|---|---|---|
| `i32.load8_u` | `0x2d` | one byte, unsigned |
| `i32.load` | `0x28` | four bytes |
| `i32.store8` | `0x3a` | footprint of one byte |
| `i32.store` | `0x36` | footprint of four bytes |
| `br_if` | `0x0d` | returned 7 when taken, 9 when not |
| `br` | `0x0c` | returned 8, where `return` returned 7 |
| `local.set` | `0x21` | returned 33+x, where `drop` returned 33 and `return` returned x |
| `i32.add` | `0x6a` | computed a+b |
| `i32.sub` | `0x6b` | computed a−b |
| `i32.le_s` | `0x4c` | computed the signed comparison |

## The branch

This is what M060 said was qualitatively harder, and it is the substance of the result.

A conditional branch produces no value. The scaffold gives it one: a block that leaves `7` on the
stack and branches out, or falls through to `9`. `0x0d` returns `7` on a true condition and `9` on
a false one, and nothing else in 256 candidates does. The instruction was identified purely by
what it caused to happen.

## Discovery bootstrapping discovery

Two shapes cannot observe their candidate without an addition. `local.set` is indistinguishable
from `drop` unless the local is read back, and indistinguishable from `return` unless the read is
combined with something; `br` is indistinguishable from `return` unless the block's result is
changed after the branch lands.

Writing `0x6a` into the scaffold that discovers opcodes would have been the shortcut this
experiment exists to remove. So the scan runs in two stages, and the second is built from a byte
the first found. The dependency is in the code — `staged_scaffolds` takes the addition as an
argument — and a test asserts that a different byte produces a different module.

## The scan disagreed with the authored code, and was right

`i32.le_s` is `0x4c`. The first M061 copy loop hardcoded `0x4d`, which is the **unsigned**
comparison. Nothing caught it, because the loop's counter never goes negative and the two agree on
every value it ever sees. M060's own emitter had it right; the defect was local to M061.

The scan named `0x4c` from behaviour and contradicted the hand-written byte. A discovery procedure
found a latent bug in the authored code it was built to reproduce, which is a better argument for
the procedure than agreement would have been.

## What the review found, and what was done about it

An external review read the manifest against the builder and found that the loop hardcoded seven
opcodes — `block`, `loop`, `br`, `local.set`, `i32.le_s`, `i32.add`, `i32.sub` — while the manifest
asserted `copy_loop_uses_only_discovered_instructions: True` and
`structural_instructions_authored: False`.

**The review was correct and the manifest was materially false**, in a result whose subject is
honesty about what was found.

Six of the seven are now discovered, by three new scaffolds. `block` and `loop` are not: they are
not instructions with an observable effect on a value, they open a region and decide where a branch
lands, and a scaffold using one to expose the other would assume what it set out to find.

So the manifest now carries both lists at the same level —
`copy_loop_discovered_instructions` and `copy_loop_authored_elements` — and
`copy_loop_uses_only_discovered_instructions` reads **False**. The correction is a list, not softer
wording, and the protocol's anti-cheating clause now names this failure mode explicitly because
this experiment committed it.

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
observable as a failure. Each candidate runs in its own process under a deadline, because nothing
inside the probe can decide termination.

**A constant can be quietly negative.** Scaffold constants are one SLEB128 byte, where bit `0x40`
is the sign, so a version writing 99 produced −29. The witness vanished and the scan disqualified
itself rather than reporting a false negative — the self-check earning its place a second time.

M058's arithmetic scan met none of these: its scaffold was trivially well-formed, every candidate
returned, and its constants were small.

## Refusing rather than choosing

Four ambiguities were found and every one was resolved by **widening the probe rather than
loosening the resolver**: the store widths, the signed and unsigned byte loads, `local.set` against
`drop` and `return`, and `br` against `return`.

One remains and is recorded rather than arbitrated: `0x2e` and `0x2f` both read two bytes, and both
planted patterns are positive in that width.

## What the falsifier catches, and what it does not

Naming a byte is not the same as being able to build with it, so the recovered instructions were
assembled into a byte-copy loop — load, store, both branches, the local write and the arithmetic
working together — which recovers its phrase exactly. The loop refuses to be built at all if any
required instruction is missing from the resolution, so there is no silent fallback.

Substituting the unconditional branch for the conditional one makes the loop copy nothing, so the
control is real.

**Substituting the four-byte store for the one-byte store does not break it**, and that is
recorded. Each iteration writes its byte plus three zeros and the next iteration overwrites them;
the width only shows past the end of the copied range, which the loop never reads. The control
falsifies the branch and is blind to that substitution. Saying so is better than implying the loop
falsifies everything it is given.

## The floor

`local.get`, `i32.const`, the `end` that closes every body, the module framing and the signature
shape are **presupposed**. Every scaffold presents an operand and returns a result, so it cannot
discover the instructions that do those things.

`block` and `loop` remain authored, for the reason given above rather than for convenience.

The compiler that arranges the discovered instructions also remains authored. M061 removes the
authored *instruction set* for structural operations, not the authored *control structure* and not
the authored *compiler*.

## Claim boundary

One substrate, six shapes, ten instructions, one loop. M061 does not establish arbitrary runtime
discovery, unrestricted code generation, open-ended evolution, general intelligence, consciousness
or production safety. Network, repository, credential, deployment and external-system authority
remain human-controlled.

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
| M061 | six scaffold shapes and a floor | **which structural instructions exist** |

What remains handed is the compiler that arranges them, the control structure they run inside, the
scaffold shapes, and the tasks that arrive.
