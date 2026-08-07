# M056 — development result

## Status

**POSITIVE ON ITS CENTRAL QUESTION — PENDING QUALIFICATION.**

A capability learned after a migration survives the next one. This is a bounded, noncanonical
development result.

## The question

M048 changed substrate once and then learned `tool_max` in the new runtime. Its compiler was
written by a human who knew the nine M047 modules it had to translate; `tool_max` did not exist
yet. Whether a second migration carries it separates continuity from translation, and had never
been tested.

## What was observed

| Observation | Value |
|---|---|
| Inherited state | M048 version **8**, reconstructed rather than asserted |
| Retained capabilities | **32**, of which 28 predate the first migration |
| Emitted WebAssembly module | 107 bytes, digest `2ea94e14…` |
| Declared imports | **0** |
| Inherited capabilities passing in WebAssembly | **32 / 32** |
| **Capability learned after migration one** | **survives**, 4 / 4 cases |
| Capabilities answering with the module removed | **0 / 32** |
| Capability learned in the migrated substrate | `minimum` → `min`, module grows to 5 tools |
| Inherited regression after adoption | **32 / 32** executed |
| Accepted version | **9** |
| Forced fault detected, exact restoration | yes |
| Replay, and manifest reproducibility across processes | identical |

Manifest digest `ad1c8ba1b117a4910a76afc58c32632569e05eb9b89a9df82129e9f3f1c677eb`.

## Why the answer is credible

Two observations frame the central one, and without them it would be worth little.

**The compiler does not know the answer.** It works from what each module declares, never from
its name. `tool_mean`, learned before the first migration, and `tool_max`, learned after it,
both declare `kind: synthesized_tool` and take the identical path. Permanent tests pin this
directly: a module named `tool_zzz` declaring `expression_id: maximum` compiles, and a module
named `tool_max` declaring an unknown expression is refused. A compiler with a hand-written case
for the post-migration tool would have carried it across while proving nothing.

**The semantics genuinely moved.** With the WebAssembly module removed, **nothing answers** —
0 of 32. The JavaScript shell retains none of the arithmetic. The module itself declares zero
imports, verified through `WebAssembly.Module.imports()`, so it cannot call back out.

A third check makes the operand type observable end to end. The inherited `critique` module
rounds a non-integer to two decimals, so `mean 1 2 4` reports `2.33`. Under integer division the
tool would have returned exactly `2` and the case would read `2`. The reported value therefore
discriminates `f64` from integer arithmetic rather than merely agreeing with it.

## Learning again in the new substrate

The lineage diagnoses the unknown token `minimum`, emits a tool module that declares itself the
way its predecessors do, and the compiler reaches it by the path it already had — nothing names
the new tool to the compiler. Independent validation runs the inherited bank, then public
probes, then hidden probes, and holds no adoption authority. Adoption reaches version nine, a
forced fault is detected before anything is restored, and the exact state returns.

## Claim boundary

**The tools migrate; the request shell does not.** Tokenising, routing, planning, critique and
orchestration remain in JavaScript. What moves is where the capabilities live, which the 0-of-32
counter-check demonstrates — but this is not the whole-body migration M048 performed, and it is
not presented as one.

**The compiler is written by a human.** In M048 and in M056 alike, the lineage carries its
capabilities across a substrate boundary but does not perform the crossing. Migration remains
something done *to* it rather than something it accomplishes. M056 does not close that gap and
does not claim to. It is the largest remaining distance between this line of work and the
objective the project was started for.

M056 does not establish arbitrary runtime discovery, unrestricted code generation, open-ended
evolution, general intelligence, consciousness or production safety. Network, repository,
credential, deployment and external-system authority remain human-controlled.

M056 is noncanonical. **M042 remains the only positive canonical continuous-lineage
completion.**

## Relation to the closed language line

**D019** closed M053–M055 because compositional acquisition inside a closed formation language
buys search cost, not expressive power. A substrate is not closed under composition: what is
acquired there is a body that executes natively, not a sub-expression of a grammar. That is why
the frontier moved here rather than stopping, and M056 is the first positive construction result
since M048.
