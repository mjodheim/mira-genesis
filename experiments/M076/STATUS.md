# G2 grounding status

**POSITIVE QUALIFIED DEVELOPMENT RESULT — TRACK A, MODEL-FREE. NOT MERGED. NUMBER UNASSIGNED.**

- Target: generality gate **G2**, recorded as fully open before this work.
- Track A endogenous, no model call, no network, no external task, no third-party input required.
- Channels: UTF-8 instruction, ordered structured mapping, raw 1728-byte RGB888 raster.
- Outputs: symbolic `set_dial` calls (24 episodes) and embodied effector moves (12 episodes).
- Bound suite: 36 episodes, 3 families, 12 each; commitment `20ff63f3…a4f7e`.
- Full arm: **36/36** exact.
- Triple dissociation: each ablation zeroes its dependent family and leaves both others at exactly
  the full-arm score.
- Measured guessing floor: 3/36 against an expected 2.3 and a bound of 8.
- First result, attempt 1, no retry: `aa312e95…a52639`.
- Local regressions: 26 passed. Independent checker: `failures: []`. Orphan audit: clean.
- Gate advance: G2 open → partial mechanism evidence. **G2 is not closed.**

## Frozen ordering

1. `cd55035` froze `PROTOCOL.json` and `PROTOCOL.md` before any harness code existed; the salt was
   drawn first and episode content was absent from the freeze.
2. `4a56de6` added the harness and recorded amendment A1 before materialization.
3. `5fdf7b4` bound the 36-episode suite before any arm was run.
4. The result was preserved once, on attempt 1, with no retry and no episode replacement.

## Outstanding before merge

- Full `pytest -q` on Python 3.11 and 3.13 plus repository integrity in CI.
- Register updates: `MIRA_GENERALITY_CRITERIA.md` G2 row, `ROADMAP.md`, `PROJECT_STATE.md`,
  `PROJECT_STATE.yaml`, `CHANGELOG.md`, `SCIENTIFIC_HYPOTHESES.md` (a new hypothesis for
  per-channel causal dependence) and a `DECISIONS.md` entry.
- Assignment of the experiment number at merge, to avoid colliding with the concurrent M075 line.

These are deliberately left undone. The registers are digest-bound shared files that the concurrent
M075 work on `main` also edits, and editing them from a parallel worktree would create exactly the
audit-trail conflict this separation was meant to avoid.
