# M057 — the lineage constructs its own migration path

**Status: PROPOSED — unqualified.**

## Research question

Can the continuing lineage discover the semantics of an opaque target substrate by probing it,
compose its own tools out of what it measured, and migrate on a path it constructed rather than
one it was handed?

## What this removes

M056 handed the lineage a compiler. `m056_wasm_compiler._body_for` mapped every declared tool to
a WebAssembly instruction sequence, authored in advance, and the M056 result stated the limit
twice: the lineage carried its capabilities across a substrate boundary but did not perform the
crossing.

M057 removes that map.

## The opaque substrate

The target instruction set is exposed as six handles named `h1` … `h6`. **No handle carries a
semantic name.** The lineage may run a handle and observe what comes back; that is the only way
it can learn what one does.

Two properties are structural rather than promised:

- the probe module and every emitted module declare **zero imports**, verified through
  `WebAssembly.Module.imports()`, so nothing can call back out;
- synthesis evaluates every candidate by **calling the substrate** —
  `instance.exports[handle](a, b)`. No table of handle meanings exists on the Python side, and a
  permanent test asserts its absence.

That test guards a defect that was present in an early draft: candidates were evaluated in
Python against a table of the opcodes' semantics, which would have let the lineage synthesize
using exactly the knowledge it was supposed to discover.

## Where the synthesis targets come from

The lineage observes **its own accepted tools** running in the substrate it currently occupies.
It knows what `mean` does because it can run `mean`, not because anything described it.

## Synthesis

Bottom-up by expression size, deduplicating candidates whose observed values coincide on the
probe domain.

That deduplication is **M052's equivalence argument**. D016 closed M052 as a search-efficiency
result rather than a capability gain, which it was. Here it is the technique that makes
compositional synthesis reachable at all: a beam search guided by numeric error was tried first
and failed at 49,156 candidates, because the useful subterm `add(a,b)` scores badly against
`mean` and never survives into the beam.

## Declared parameters

| Parameter | Value |
|---|---:|
| Handles | 6, opaque |
| Probe pairs | 4 |
| Maximum expression size | 7 nodes |
| Synthesis budget | 200,000 |
| Atoms | the tool's own parameters, plus a constant equal to its arity |

## Required lineage

1. begin from the accepted M048 version-eight state, reconstructed rather than asserted;
2. receive the instruction set as handles carrying no semantic labels;
3. probe them on shared pairs;
4. observe its own tools, and synthesize a body for each from what it measured;
5. reach at least one tool that **no single handle satisfies**;
6. verify every synthesized body on a hidden domain the synthesis never saw;
7. execute every inherited capability through the constructed path;
8. record both ablations.

## The falsifier

M057 fails, informatively, if step 5 fails — if synthesis succeeds only for tools a single handle
satisfies. That would say the lineage can *label* a substrate but not *build* in it, and it must
be recorded rather than repaired by supplying the composition.

## Ablations

| Arm | Required outcome |
|---|---|
| Probing, full composition | constructs a working path |
| Handles taken in the order the substrate exposes them, no probing | fails |
| Probing kept, composition denied | fails on the tool no single handle satisfies |

The second arm is the one that matters. If assigning handles in exposure order also worked, the
probing did nothing and the result would be an artifact of that order.

## On the search margin

The admissible space at the declared size is 281,188 expressions for a three-parameter tool, and
the synthesis constructs about 44,000 of them: roughly a sixth.

**This is a far weaker separation than M054's**, where the budget sat five orders of magnitude
below the space, and it is recorded rather than dressed up. Declaring a larger maximum size would
inflate the ratio without changing anything the search does, since the answer is found at size
seven and the search never reaches size nine. That is the tuning illusion M055 refused, and it is
refused here too.

The claim M057 makes does not rest on that margin. The separation that carries the result is
**discovery against being told**: the handles have no names, and the semantics were measured
rather than supplied. Both ablations test that property, and neither depends on the size of the
space.

## Anti-cheating

M057 does not pass if any handle carries a semantic name, if a handle-to-meaning table exists
anywhere, if a synthesized body delegates to the source runtime, or if a capability is served
from a lookup table.

The **set** of available operations remains authored by a human. What the lineage discovers is
what they do and how to build its tools from them. This is not a claim that the lineage invents
an instruction set.

## Qualification rule

M057 may pass in development only when the complete Python 3.11 and Python 3.13 matrices and the
repository-integrity job pass on the exact documented head. A run that fails before the
experiment's code executes is an infrastructure event under D017 and is not a verdict.

## Claim boundary

One lineage, one opaque instruction set of six binary operations, fixed tools. M057 does not
establish arbitrary runtime discovery, unrestricted code generation, open-ended evolution,
general intelligence, consciousness or production safety. Network, repository, credential,
deployment and external-system authority remain human-controlled.

M057 is noncanonical. M042 remains the only positive canonical continuous-lineage completion.
