# M060 — development result

## Status

**POSITIVE ON ITS CENTRAL QUESTION — PENDING QUALIFICATION.**

The whole accepted body executes in WebAssembly, with nothing left in JavaScript. This is a
bounded, noncanonical development result.

## What was observed

| Observation | Value |
|---|---|
| Inherited state | M048 version **8**, reconstructed rather than asserted |
| Modules in the accepted body | **10** |
| Modules migrated | **10** — seven shell, three tool |
| Modules left in JavaScript | **0** |
| Emitted module | **1,792 bytes** |
| Declared imports | **0** |
| Instantiated with an import object | no |
| Exported functions | 11 pipeline stages plus `memory` |
| Inherited capabilities executed in the new substrate | **32 / 32** |
| Opcode space scanned | **256** |
| Operations discovered | **9** |
| Arithmetic opcodes resolved by scan, not authored | **4 / 4** |
| Emission deterministic | yes |

## What crossed that never had

M056 through M059 moved four arithmetic tools and left seven shell modules behind. Those seven
are the ones that made the crossing hard, because WebAssembly has no strings, no objects, no
allocator and no exceptions:

- **interpretation** — tokenising on bytes, ASCII lowering, an alias table compared character by
  character, and a recursive prefix parse building a tree in linear memory;
- **planning** — postorder emission into a step table at a fixed stride;
- **selection**, **allocation** — table lookup and the accepted `double_plan_length` policy;
- **execution** — a stack walk resolving literals and references, dispatching by route;
- **critique** — two-decimal rounding reproduced exactly, so `mean 1 2 2` still reports `1.67`;
- **orchestration** — the pipeline, with refusal expressed as a trap rather than a thrown value.

`mul add mean 1 2 3 mul 2 3 add mean 3 6 9 add 1 1` returns **64** in pure WebAssembly.

## Why the claim is structural rather than a promise

The module **declares no imports**, checked through `WebAssembly.Module.imports()`, and is
instantiated with no import object at all. A call outward is not discouraged; it is impossible.
This is the same check M048 used to establish that Python had left its execution path.

The pipeline stages survive as **separate functions**, not fused into one. Fusing would have
preserved behaviour and destroyed the structure the lineage's own adaptations target by name.

## Discovered and authored

This is the honest centre of the result, and it is stated before anything else is claimed.

**Discovered.** The four arithmetic opcodes the body computes with are resolved by M058's scan of
the 256-byte opcode space, performed by the experiment itself. Each is uniquely determined by its
behaviour on the shared probe pairs; an operation matched by two candidates, or by none, is
refused rather than guessed.

The manifest records the scan, the resolved bytes and the fact that they were not authored. An
earlier revision of this experiment verified the correspondence in an ad hoc command and shipped
a compiler that used its authored fallback, so the artifact asserted nothing about discovery at
all. A permanent test now asserts the scan happened and produced those bytes, and a second
asserts that ambiguous evidence is refused.

**Authored.** Everything structural — loads, stores, branches, loops, calls, local access, the
memory layout — is written by a human, as is the compiler that assembles them.

**M060 trades autonomy for breadth.** It reaches M048's coverage in a far more hostile substrate
while re-introducing an authored compiler that M057 and M058 had learned to do without for the
tools. The line now stands at:

| Experiment | Modules crossed | Compiler | Instruction set |
|---|---:|---|---|
| M048 | 9 | authored | authored |
| M056 | 4 tools | authored | authored |
| M057 | 4 tools | **constructed** | six named operations |
| M058 | 4 tools | **constructed** | **discovered** |
| M059 | judgement only | — | **discovered, two substrates** |
| M060 | **10** | authored for structure | **discovered for arithmetic** |

Breadth and full autonomy have still not met in one experiment. M060 narrows the gap; it does
not close it.

## The compiler is repository code

`metamorphosis/m060_body_compiler.py` emits the module through `metamorphosis/m060_wasm_emit.py`.
Nothing is compiled by an external toolchain at run time, nothing is read from a `.wat` file, and
no precompiled bytes are embedded. A test asserts this on the parsed syntax tree rather than on
the source text, because a first version flagged the module for its own docstring explaining that
it does not use a toolchain.

WebAssembly text was used during development as a specification and an oracle. The emitted module
was compared against the assembled WAT on every case; the 37-byte difference between them is
entirely the WAT's global section, folded into constants because the emitter has none.

## The defect this substrate produces

A first implementation passed **23 of 32**, and every one of the nine failures was a nested
request. The planner allocated a parent's step index before recursing into its children,
producing preorder indices where the accepted body emits postorder, so a parent read a result its
children had not yet written.

There was no exception and no stack trace — a structurally valid program returning a wrong
number. Flat requests never exposed it, and 23 cases passed throughout. This is why the reference
oracle earned its place.

## Claim boundary

One body, one target substrate, one authored structural compiler, fixed task families. M060 does
not establish arbitrary runtime discovery, unrestricted code generation, open-ended evolution,
general intelligence, consciousness or production safety. Network, repository, credential,
deployment and external-system authority remain human-controlled.

There is no post-migration learning, no forced fault and no rollback in M060. It establishes that
the whole body can cross and keep every capability; it does not re-establish what M048 and M056
showed about continuing to adapt afterwards.

M060 is noncanonical. **M042 remains the only positive canonical continuous-lineage
completion.**

## What remains handed

The structural instruction set and the compiler that arranges them. The signature shapes. The
tasks that arrive.

Closing the first of those means discovering loads, stores and control flow the way M058
discovered arithmetic — a qualitatively harder scan, because a branch has no observable value to
compare against, only an effect on what runs next.
