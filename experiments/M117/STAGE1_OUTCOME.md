# M117 Stage 1 — a route qualified

**Stage 1 selected a route on attempt 05.** It is the first qualifying candidate in an order frozen
before any candidate was probed, and it is the only candidate that qualified.

| | |
|---|---|
| Frozen plan | `b3b345907221081b260a8eb7da01aa692d018f18d31b4e35c60cf1b564e73168` (revision 5) |
| Candidate universe | `94b8819432a0880a…` — 282 assessed, 91 eligible, 75 distinct requests |
| Candidates probed | 16 (one position skipped as an identical request) |
| Requests spent | 144 of 160 |
| **Selected** | `deepseek/deepseek-v4-flash-0731` on **OpenInference** |
| Canonical checkpoint | `deepseek/deepseek-v4-flash-20260731` |
| Independent checker | **PASSED** |
| Qualifying invocations | **0** |

## What qualifying required

All twelve clauses, no partial credit:

- **All nine schema feature classes enforced** — enum, pattern, required, additionalProperties,
  minItems, maxItems, integer bounds, nested arrays, nesting depth — plus the combined structural
  probe conforming.
- **Token-capacity stress held**: HTTP 200, `finish_reason: "stop"`, **68,368 completion tokens**,
  and the output **conforming** to the census-dominating stress schema. Not a partial emission and
  not a truncation — a complete, valid document at carrier scale.
- **Identity exact**: requested model, provider and canonical checkpoint all matched what the router
  attested; direct strategy, routing attempt 1, exactly one selected endpoint, no fallback, no
  pipeline intervention.
- Reliability minimum held.

Verified independently rather than taken on the runner's word: the selection is the earliest
qualifying position, it recomputes from the committed universe and profiles alone, the report digest
self-verifies, and the report is bound to the committed universe and frozen plan.

## What this is not

**This is not evidence for H62.** Stage 1 is instrument qualification: it establishes that a route
exists which enforces the schema features the carrier design depends on and can emit a conforming
document at the required scale. It says nothing about the hypothesis. **G1–G10 are unchanged, and
qualifying invocations remain 0.** H62 is not frozen and no bank exists.

The measurement is one date, small synthetic schemas, 16 of 91 eligible candidates, a single
observation per probe. Nothing here licenses treating the route as characterised.

## Suggestive, not established: the same checkpoint on a different provider

M116 closed because its route enforced **none** of the nine feature classes. That route served the
**same canonical checkpoint** — `deepseek/deepseek-v4-flash-20260731` — from **Alibaba**. Attempt 03
reproduced it: nine of nine unenforced, identity exact. The route that qualified here serves that
same checkpoint from **OpenInference**, enforcing all nine.

This suggests M116's negative was a property of the **provider's serving stack**, not of the model.
**It is not established.** The two observations come from different attempts under different
apparatus revisions, and attempt 05 applied the reasoning-off control that attempts 01–04 never sent.
`google/gemini-2.5-pro` returned nine of nine unenforced here having returned zero of nine in attempt
03, so run-to-run variation in this measurement is real and unexplained. A within-run,
same-configuration comparison would be needed to make the provider claim, and none was made.

## What the earlier attempts cost, and why they were not shortcuts

Five attempts, four superseded. None was a failure of the routes; each was a defect in the instrument
that would have produced a false negative:

| | defect | consequence if unnoticed |
|---|---|---|
| 01 | three catalogue fields read where the API does not publish them | universe of 0; "no route qualifies" |
| 02 | stress requested more tokens than eligibility guarantees | halted; attribution later refuted by 03 |
| 03 | two clauses required fields this API emits on no request | ceiling reached, no selection |
| 04 | reasoning control never sent; 15 of 90 rows the same request | superseded before any request |

Attempts 03 and 04's fixes touched what counts as qualification, so both were put to the owner and
authorized rather than decided here. No threshold, ordering key, tie-break or budget bound was ever
changed, and the stress bar stayed at 32,000 throughout.

## Still open

Why the stress schema is rejected by the Google routes remains unestablished — the provider returns
an opaque error with no cause. That question is untouched by this selection and is **not** answered
by having found a route that accepts the schema.
