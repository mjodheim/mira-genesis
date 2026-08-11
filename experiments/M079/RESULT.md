# M079 — first result

**POSITIVE QUALIFIED DEVELOPMENT RESULT — TRACK A, MODEL-FREE.**

Date: 2026-08-11. No external model, no network, no external task, no third-party attestation.

## Outcome

| Arm | static | revision | ambiguous solved | Clarifications (static/revision/ambiguous) | Unsafe | Replans |
|---|---:|---:|---:|---|---:|---:|
| planner | **8 / 8** | **8 / 8** | 0 | **0 / 0 / 8** | **0** | **8** |
| no_replan | 8 / 8 | **0 / 8** | 0 | 0 / 0 / 8 | 0 | 0 |
| never_ask | 8 / 8 | 8 / 8 | 2 | 0 / 0 / 0 | **6** | 8 |
| always_ask | 0 / 8 | 0 / 8 | 0 | 8 / 8 / 8 | 0 | 0 |

One unchanged planner, given only a goal predicate, affordance schemas with costs, a budget and an
initial observation, solved every unambiguous task within budget, revised its plan on all eight
revision episodes, asked for clarification on all eight ambiguous tasks and on none of the sixteen
others, and reached no unsafe terminal state.

## The two lines that carry the claim

`never_ask` reached **six** evaluator-detected unsafe terminal states. Without that, "the planner
asked" would prove nothing; with it, the ambiguity is demonstrably safety-relevant and the public
evidence demonstrably insufficient to resolve it. In the ambiguous episodes the hazardous resource is
placed strictly closer than the safe one, so a cost-minimising planner without a safety check takes
the hazardous branch deterministically rather than by luck. That is a deliberate construction choice
and it is recorded here rather than left implicit.

`always_ask` solved nothing at all. Asking is never scored as success on this bank: only the
evaluator's goal and safety checks score a task, so the planner's eight clarifications appear in the
`ambiguous solved` column as zero, exactly like the floor's.

## Each ablation loses exactly one capability

`no_replan` falls to 0/8 on revision while its static tasks stay at 8/8 and its ambiguous
clarifications stay at 8 — numerically identical to the planner. `never_ask` keeps static and
revision at 8/8 while losing safety on the ambiguous family. Neither degrades the family it was meant
to retain.

## Terminal verification

Success is read from world state after execution. `no_replan` stops at the blocked route and reports
itself done; the world says the goal is unmet, and the record scores the world. A regression pins
this: `claimed_done` is true while `goal_reached` is false.

## Recorded construction fixes

Both were applied before materialization and are stored in `RESULT.json`.

1. Sealed states are terminal in the search. Every goal requires a seal, so expanding sealed states
   made the state space intractable and the first run never finished.
2. The revision family blocks an edge the initial optimal plan actually traverses, and the generator
   verifies a detour remains feasible. An arbitrary block was routed around in three of eight
   episodes, so nothing was revealed and no revision was forced. That was a failure to implement the
   frozen specification — which requires that attempting one specific action reveals the block — not
   an inconvenient outcome.

No threshold moved. The budget is drawn from the salt, as the frozen selection rule requires.

## Preserved evidence

- Protocol frozen before the harness: commit `d5480b7`; salt
  `e43c8dca8669ad9cb9b2fb97fa28f4a9217adafa6b3740ecc0fdbbfb41ad43c6`.
- World, planner and ablations: commit `45886bc`.
- Bank commitment `3047ab09e1c0fb3e1df807a645f697d2f9d1fb655bd9d7d3c47f98ea23d9e5f9`.
- First result, attempt 1, no retry:
  `5f7ccf2131f36c9761a0cfd921f017bd7d616e344ea01c71b30a16e6502302b9`.

`python scripts/check_m079_result.py` rebuilds the bank, re-verifies that ambiguous goals really
admit two safety-differing terminal states and that each revision block sits on an edge the initial
plan traverses, re-derives all four arms and recomputes the digest. It reported `failures: []`.

## What this supports

All four G3 clauses inside one bank: planning with no supplied decomposition, revision under revealed
evidence, terminal verification from world state, and clarification calibrated to genuine
under-determination.

## What this does not support

G3 remains **open**. The world, goals and affordances are project-authored; closing G3 requires them
maintained outside this project plus independent reproduction. It establishes no open-ended or
natural-language planning — the affordance schemas are four fixed operators over six locations — no
cross-domain transfer, no Genesis Gate 2 evidence and no AGI claim.

It is not evidence about model behaviour. The planner is deterministic. M074 remains the only result
on whether a model asks or refuses, and it is negative.
