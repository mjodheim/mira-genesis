# M117 Stage 1, attempt 04 — superseded before any candidate was probed

**No requests were spent under this plan.** The universe was derived and committed, and two
data-flow defects were found in it before probing began. This is not an abort: nothing was
measured, so nothing was lost.

| | |
|---|---|
| Frozen plan | `47ff587ff36e994a498ae8d63b6cc185ded94a7b1c9f429290a754b3a1181564` (revision 4) |
| Candidate universe | `ff80025c7fd82647…` — 282 assessed, 90 eligible |
| Candidates probed | **0** |
| Requests spent | **0** |

## What was found, before probing

Both defects follow from the request body alone and needed no observation. Both had been present
since attempt 01.

### The reasoning-off control was never sent, in any attempt

The frozen plan states that `reasoning: {effort: none}` is sent exactly when the catalogue declares
the parameter. `derive_universe` did not carry `supported_parameters` into the universe, so
`declares_reasoning()` read a field its candidate did not have and always answered `False`.

The control was therefore **never applied on any request in any attempt**, while attempt 03 recorded
`reasoning_control_applied: False` on all sixteen complete candidates and **58 observations
consuming reasoning tokens**. A plan that declares a control it structurally cannot apply is not
running the experiment it describes — and reasoning tokens compete for the very completion budget
the token-capacity stress measures.

### Fifteen of ninety rows were the same request

The request is a function of the model, the provider and whether the reasoning control is declared.
Ninety eligible rows carried only **75 distinct requests**; twelve `(provider, model)` pairs appeared
more than once, and **no duplicate group differed in any request-determining field**.

Probing both spends a 160-request ceiling twice on one experiment and reaches fewer distinct routes.
Attempt 03 did exactly this: its candidates 3 and 17 were the same route, so its final slot
re-probed one it had already probed at position 3.

## What revision 5 changes

`supported_parameters` is carried into the universe, and duplicate rows are **marked rather than
dropped** — every eligible endpoint stays in the record, with the position it reached and the reason
no budget was spent on it. The earliest row in the frozen order is the one kept, which is mechanical
and cannot be steered.

**No threshold, ordering key, tie-break, budget bound or qualification clause changed.**

## Claim boundary

Attempt 04 measured nothing. It is not evidence for or against H62, and G1–G10 are unchanged.
