# M086-B result — NEGATIVE, and it does not refute H32

**NEGATIVE SCIENTIFIC RESULT — TRACK A, MODEL-FREE. ATTEMPT 1, NO RERUN. NO GATE MOVES.**

Protocol `95a5022` frozen before any harness. Harness `96f4fcb`. Bank and holdout materialized at
`3d30168`. Result `8b7f80d4…d31c32`, attempt 1, no rerun, no model, no network.

**H32 remains untested.** M086-A did not test it because its threshold could not fail. M086-B did not
test it because the bank it drew made the limitation unrepairable by any mechanism at all. The two
failures are not the same kind, and the difference is the point of this attempt.

## The verdict table

Every one of the ten conditions was computed, and a single false makes the result negative.

| | Result | Evidence |
|---|---|---|
| P1 | **FAIL** | adopted 0 meta-transformations; 10 rejected |
| P2 | **FAIL** | `evolvable_meta` did not solve the holdout |
| P3 | PASS | `fixed_meta` did not solve it, and the starting mechanism's image is 0 candidates |
| P4 | PASS | `meta_acquisition_ablated` did not solve it |
| P5 | PASS | `task_only_mutable` did not solve it at triple budget |
| P6 | **FAIL** | no holdout patch was adopted |
| P7 | **FAIL** | the journal stops at `meta_search`; no adoption step exists |
| P8 | **FAIL** | no rollback evidence, because no adoption transaction ever began |
| P9 | PASS | chronology proved from recorded digests: phase 1 saw no holdout, never imported the holdout module, and the holdout binds the adopted artifact |
| P10 | PASS | 6 differential probes against M047's frozen pair |

The five failures have **one** cause. Nothing was adopted, so there was no adoption to fault, no
journal step to record and no patch to carry.

## Why nothing was adopted

The salt drew a development limitation whose routeless operation is `add`:

```
routes    : {"mul": "mul"}
aliases   : {add, max, mean, mul}
cases     : "sum2 9 8" -> 72   (unknown token, canonical mul, which has a route)
            "add 2 6"  -> 8    (parses, no route)
```

The mechanism behaved correctly. `widen_hypothesis` diagnosed both modules and generated 9
candidates; with `compose_expansions` it generated 20, including exactly the right one —
alias `sum2 → mul` together with a route and tool for `add`. Every such candidate is then **rejected
by the sandbox**:

```
RuntimeError: duplicate tool registration: add
```

`tool_core` already registers `add`. A synthesized `tool_add` module registers it again, and the body
is refused before it runs. So no mechanism — starting, widened, composed or any combination — could
repair this limitation. The search was not weak; the bank was impossible.

This is a defect in **my grammar**, not in the lineage. `ROUTELESS_CANDIDATES` was reasoned about on
the availability of a correct *expression* (`sum` does compute `a + b`) and not on whether the tool
*name* was already taken. `mean` is repairable; `add` is not; the salt chose `add`.

## What this result is, and is not

It **is** a valid negative of M086-B's single scientific attempt, preserved and not redrawn. The bank
is materialized and the protocol forbids rerunning it.

It is **not** evidence against H32. A negative that refuted H32 would show a lineage that could have
repaired its limitation and failed to improve its mechanism. Here no mechanism could have repaired
anything, so the hypothesis was never put at risk.

It is also not a repeat of M086-A's failure. M086-A recorded *positive* against a threshold where
four of ten conditions could not fail. M086-B recorded *negative* against ten conditions that all
could, and the table says precisely which failed and why. The instrument reported its own
inadequacy instead of hiding it — which is the whole purpose of the corrections the disqualification
mandated.

## What the corrections did deliver

- **P9 passed**: the chronology is proved from recorded digests. Phase 1 recorded that it saw no
  holdout and never imported the holdout module; the holdout record binds adopted mechanism
  `2762e65f` and the phase-1 artifact commitment; the generator imported no lineage module. The
  holdout genuinely did not exist while the meta-search ran.
- **P10 passed**: the starting mechanism is still differentially equivalent to M047's
  `diagnose_limiting_module` + `_candidate_sources`.
- **P3 passed**: the starting mechanism's constructive image for the holdout is empty, enumerated
  rather than inferred.
- **Every artifact is byte-identical between the working tree and the committed blob**, because the
  `-text` declarations landed in the protocol commit before any digest existed. M086-A's
  disqualifying defect does not recur.

## What a successor needs

`ROUTELESS_CANDIDATES` must contain only operations whose tool name is not already registered by
`tool_core`, which on the current renderers means `mean` alone — and a grammar with one choice is not
a grammar. Widening it honestly requires either a second synthesizable operation in M047's renderers
or a body whose `tool_core` registers less. That is a change to the bank grammar and therefore a new
protocol, a new salt and a new experiment; it may not be applied to this one.

## CI

Run `31577302582`: **1,752 passed, 10 skipped** on Python 3.11 and 3.13, plus repository integrity;
attribution run `31577301158` passed.

An earlier CI run on the same result, `31575612491`, failed on one test. That test was a
disqualification regression asserting the exact H32 status string, which recording this negative had
just changed; the assertion was made stable and CI rerun. **The experiment itself was not rerun** —
`8b7f80d4` is attempt 1 and the bank was never redrawn. The distinction matters: CI may be rerun for
a defect in a test, a materialized scientific bank may not be rerun for anything.

## Claim boundary

No gate moves. H32 is untested. This result is not evidence for or against endogenous transformation
of an improvement mechanism, is not a reproduction of anything, does not replace M085 and does not
touch its fail-closed boundary. No foundation model was called at any point.
