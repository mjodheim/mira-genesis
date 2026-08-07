# M057 — development result

## Status

**POSITIVE ON ITS CENTRAL QUESTION — PENDING QUALIFICATION.**

The lineage discovered an opaque substrate by probing it and built its own way into it. This is a
bounded, noncanonical development result.

## The gap this closes

M056 answered its own question and named what it did not do, twice:

> A human authors the compiler. In M048 and here alike, the lineage carries its capabilities
> across a substrate boundary but does not perform the crossing.

M057 removes the authored map.

## What was observed

| Observation | Value |
|---|---|
| Inherited state | M048 version **8**, reconstructed rather than asserted |
| Handles exposed | **6**, named `h1`…`h6`, no semantic labels |
| Probe pairs | 4, sufficient to separate all six handles |
| Tools synthesized | `add`, `max`, `mean`, `mul` |
| Found by direct match, size 3 | `h1(p0,p1)`, `h6(p0,p1)`, `h3(p0,p1)` |
| **Requiring composition, size 7** | **`mean` → `h4(h1(p0,h1(p1,p2)),k)`** |
| Candidates constructed for `mean` | 44,240 across 16,883 behaviour classes |
| Hidden-domain verification | all four tools |
| Inherited capabilities on the constructed path | **32 / 32** |
| Declared imports, probe and emitted modules | **0** |

## Why the answer is credible

**No handle carries a name.** `h1`…`h6` are opaque. A permanent test asserts the naming
convention holds, so a future change that labelled one would fail.

**Synthesis calls the substrate.** Every candidate is evaluated through
`instance.exports[handle](a, b)`. A permanent test asserts that no table of handle semantics
exists on the Python side, because one did in an early draft: candidates were evaluated in
Python against the opcodes' meanings, which would have let the lineage synthesize using the
knowledge it was supposed to discover. That draft would have measured nothing.

**Both ablations fail as they must.**

| Arm | Outcome |
|---|---|
| Handles taken in exposure order, no probing | **fails** — probing does real work |
| Probing kept, composition denied | **fails on `mean` alone** |

The second is the falsifier the protocol named: without composition the lineage can *label* a
substrate but not *build* in it. It reaches `add`, `max` and `mul`, and stops.

## What made it reachable

Bottom-up enumeration with deduplication by observed behaviour — **M052's equivalence argument**.

A beam search guided by numeric error was tried first and failed, at beam 12, 24, 40 and 64, up
to 49,156 candidates. It cannot work here: the useful subterm `add(a,b)` scores badly against
`mean` and never survives into the beam. Enumerating by size and collapsing behavioural
duplicates finds the answer in 44,240 candidates.

D016 closed M052 as a search-efficiency result rather than a capability gain, which it was. It is
worth recording that the technique closed as non-advancing is what makes this experiment
possible. A result can fail to be a frontier and still be load-bearing.

## On the search margin

The admissible space at the declared size is 281,188 expressions for a three-parameter tool, and
synthesis constructed about 44,000: **roughly a sixth**.

This is a far weaker separation than M054's, where the budget sat five orders of magnitude below
the space. It is recorded rather than dressed up. Declaring a larger maximum expression size
would inflate the ratio without changing anything the search does, since the answer is found at
size seven and size nine is never reached — the tuning illusion M055 refused, refused again here.

**The result does not rest on that margin.** The separation that carries M057 is discovery
against being told: the handles have no names and their semantics were measured, not supplied.
Both ablations test that property and neither depends on the size of the space.

## Claim boundary

The **set** of available operations remains authored by a human — six binary `f64` operations.
What the lineage discovers is what they do and how to build its tools from them. This is not a
claim that it invents an instruction set, and the distance between the two is real.

The request shell also remains in JavaScript, as in M056: tokenising, routing, planning, critique
and orchestration did not migrate.

M057 does not establish arbitrary runtime discovery, unrestricted code generation, open-ended
evolution, general intelligence, consciousness or production safety. Network, repository,
credential, deployment and external-system authority remain human-controlled.

M057 is noncanonical. **M042 remains the only positive canonical continuous-lineage
completion.**

## Where this sits

M013e is recorded as *"exact migration after discovery of an opaque finite substrate"*, 36/36,
in deterministic automata. M057 asks the same of a real runtime, inside the lineage M048 migrated
and M056 migrated again. The shape was established years of experiments ago; what is new is the
substrate and the lineage carrying it.
