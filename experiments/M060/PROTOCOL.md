# M060 — the whole body crosses

**Status: PROPOSED — unqualified.**

## Research question

Can the **entire** accepted body — not its arithmetic tools — execute in a substrate whose
primitives share nothing with the one it came from, with every inherited capability intact and
no part of it left behind?

## The gap this addresses

Five experiments each removed something the previous one was handed, and each narrowed what
crossed.

| Experiment | Modules that crossed | Left in JavaScript |
|---|---:|---:|
| M048 | **9** | 0 |
| M056–M059 | 4 tools | **7 shell modules** |

M048 had breadth and no autonomy: it was handed a compiler and an instruction. M056 through M059
removed the compiler, the operation list and the instruction, and in doing so narrowed what moved
to four arithmetic functions. Breadth and autonomy had never met.

## Why the shell was hard

WebAssembly has no strings, no objects, no allocator and no exceptions. The shell tokenises text,
lowers ASCII, compares tokens against a table, builds a tree, walks it in postorder and dispatches
by route. None of that survives a translation that only knows how to emit `f64.add`.

It had to be rewritten against linear memory: bytes at addresses, records at fixed strides,
recursion through the call stack, and refusal expressed as a trap rather than a thrown value.

## What is authored and what is discovered

This is the honest centre of the experiment, and the protocol states it before the results.

**Discovered.** The four arithmetic opcodes the body computes with — addition, maximum,
multiplication, division — are taken from M058's scan of the opcode space. Each is uniquely
identified by its behaviour on the shared probe pairs; none is named to the compiler.

**Authored.** The structural instructions are not. Loads, stores, branches, loops, calls, local
access and the memory layout are written by a human. M057 and M058 removed the authored operation
list for arithmetic; M060 does not remove it for structure, and re-introduces an authored compiler
for the shell.

**M060 therefore trades autonomy for breadth.** It reaches M048's coverage in a far more hostile
substrate while accepting a compiler M057 and M058 had learned to do without. It is not the
combination of breadth and autonomy, and does not claim to be.

## The compiler is repository code

The module is emitted by `metamorphosis/m060_body_compiler.py` through
`metamorphosis/m060_wasm_emit.py`. Nothing is compiled by an external toolchain at run time,
nothing is read from a `.wat` file, and no precompiled bytes are embedded.

WebAssembly text was used during development as a specification and a debugging oracle, and the
emitted module is compared against it. Shipping the compiled bytes instead would have made the
compiler an opaque blob, which is what M048's protocol forbids for a migrated body.

## Required lineage

1. begin from the accepted M048 version-eight state, reconstructed rather than asserted;
2. compile **all ten modules** — seven shell, three tool — into one WebAssembly module;
3. declare **no imports**, verified through `WebAssembly.Module.imports()`;
4. instantiate with no import object at all;
5. execute **every** inherited capability and pass;
6. reproduce refusals, including an unknown operator, an incomplete arity and an empty request;
7. reproduce the accepted body's two-decimal rounding exactly;
8. emit deterministically.

## The falsifier

M060 fails if any capability requires JavaScript. The check is structural rather than a promise:
a module declaring imports is rejected before it runs, and the instance is created without an
import object, so a call outward is not merely discouraged but impossible.

## What the development already found

A first implementation passed 23 of 32. **Every one of the nine failures was a nested request.**
The planner allocated a parent's step index before recursing into its children, producing preorder
indices where the accepted body emits postorder, so a parent read a result its children had not yet
written. Flat requests never exposed it.

This is recorded because it is the shape of defect this substrate produces: no exception, no stack
trace, just a wrong number from a structurally plausible program.

## Anti-cheating

M060 does not pass if the module imports anything, if any capability is served from a lookup table
of expected answers, if precompiled bytes are embedded rather than emitted, or if the shell remains
in JavaScript under another name.

## Qualification rule

M060 may pass in development only when the complete Python 3.11 and Python 3.13 matrices and the
repository-integrity job pass on the exact documented head. A run that fails before the
experiment's code executes is an infrastructure event under D017 and is not a verdict.

## Claim boundary

One body, one target substrate, one authored structural compiler, fixed task families. M060 does
not establish arbitrary runtime discovery, unrestricted code generation, open-ended evolution,
general intelligence, consciousness or production safety. Network, repository, credential,
deployment and external-system authority remain human-controlled.

M060 is noncanonical. M042 remains the only positive canonical continuous-lineage completion.
