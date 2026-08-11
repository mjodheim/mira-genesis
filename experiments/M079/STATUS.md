# M079 status

**POSITIVE QUALIFIED DEVELOPMENT RESULT — TRACK A, MODEL-FREE.**

- Target: all four G3 clauses — no supplied decomposition, plan revision, terminal verification,
  calibrated clarification — in one bank of 24 episodes.
- Planner: static **8/8**, revision **8/8**, replanned **8**, clarifications **0/0/8**,
  unsafe terminal states **0**, budget overruns **0**.
- `no_replan`: revision **0/8**, static and ambiguous clarifications numerically unchanged.
- `never_ask`: **6** unsafe terminal states, static and revision numerically unchanged.
- `always_ask`: solves **0** tasks; asking is never scored as success.
- Bank commitment `3047ab09…e5f9`; first result `5f7ccf21…302b9`, attempt 1, no retry.
- Local regressions: 28 passed. Independent checker: `failures: []`. Integrity: clean.
- Gate advance: **none.** G3 stays at partial bounded evidence with all four clauses exercised.

## Frozen ordering

1. `d5480b7` froze `PROTOCOL.json` and `PROTOCOL.md` before any harness code existed; the salt was
   drawn first and bank content was absent from the freeze.
2. `45886bc` added the world, planner and ablations, with both construction fixes recorded.
3. The bank was bound and the result preserved in one pass, attempt 1, no retry.

## Why the two controls exist

Asking for clarification is worthless as evidence unless the alternative is demonstrably harmful.
`never_ask` reaches six unsafe terminal states because the hazardous resource is placed strictly
closer in every ambiguous episode, so a cost-minimising planner without a safety check takes it
deterministically. `always_ask` fixes the other end: a planner that never commits solves nothing.

## Recorded construction fixes

Sealed states became terminal in the search, without which the state space was intractable. The
revision family now blocks an edge the initial plan traverses; blocking an arbitrary edge let three
of eight episodes route around it, which failed the frozen specification rather than producing an
inconvenient result. Both are in `RESULT.json`. No threshold moved.

## What a successor would need

Not more locations, resources or episodes in this world — that repeats the instrument. Closing G3
requires goals, affordances and costs maintained outside this project, plus independent
reproduction. A successor must also not cite M079 as evidence that a model asks for clarification;
this planner is deterministic and M074 remains the only result on that question.
