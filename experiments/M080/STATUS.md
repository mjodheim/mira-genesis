# M080 status

**POSITIVE QUALIFIED DEVELOPMENT RESULT WITH A MEASURED LIMITATION — TRACK A, MODEL-FREE.**

- Target: the gap the register names outright — M073 tested "no forgetting". Retention had never
  been at risk here, so it had never been measured.
- Lineage: **0** capabilities lost, **0** final retention failures, 6/6 skills generalising,
  **19** slots against a private-slot ceiling of 24, **3** rules reused, **2** byte-identical
  rollbacks, **0** checkpoint mismatches.
- `no_consolidation`: **5** capabilities lost — the interference is real.
- `no_rollback`: **3** checkpoint mismatches — the rollback check can fail.
- `no_replay`: **5** capabilities lost → retention is **`replay_dependent`**, not structural.
- Bank commitment `3769e826…3ec6d`; first result `42112139…5dfc99`, attempt 1, no retry.
- Local regressions: 29 passed. Independent checker: `failures: []`. Integrity: clean.
- Gate advance: **none.** G5 stays at stronger partial bounded evidence, now with forgetting
  measured.

## Frozen ordering

1. `b3e9aba` froze `PROTOCOL.json` and `PROTOCOL.md` before any harness code existed; the salt was
   drawn first and bank content was absent from the freeze.
2. `d68dfd3` added the lineage and ablations, with all three instrument fixes recorded.
3. The bank was bound and the result preserved in one pass, attempt 1, no retry.

## The finding that matters most

Retention is conditional on replay. Removing the replay of earlier examples costs exactly as much as
removing consolidation entirely. The mechanism rechecks old skills rather than structurally
protecting them, and any successor claiming robust continual learning must either fix that or state
the replay cost as part of the claim.

The protocol forbade preregistering a direction for this measure, which is why the answer can be
reported as it fell.

## Recorded instrument fixes

Capacity pressure alone never bound, so no arm evicted anything and there was no interference to
measure. Retention scored on holdouts alone hid the damage, which lands on exception keys forced
into the examples. And the rollback check was tautological: it compared the checkpoint against its
own digest and could never fail. All three are in `RESULT.json`; no threshold moved.

## What a successor would need

Not more skills or a bigger table — that repeats the instrument. Either structural retention that
survives without replay, or capabilities maintained outside this project with independent
reproduction, which is what closing G5 actually requires.
