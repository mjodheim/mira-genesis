# M117 Stage 1, attempt 02 — halted, instrument abort

**This directory is not a result.** Attempt 02 read its input correctly but could not measure token
capacity, because it sent malformed requests its own eligibility rule guaranteed it would send.

| | |
|---|---|
| Frozen plan | `5cc9c648f9881fd36c8d882c08b513514a5236cf29f7ecc107aad2867f112997` (revision 2) |
| Candidate universe | `5c02ea3887fcec98…` — 282 assessed, 94 eligible |
| Candidates probed | 3 of 94, in the frozen order |
| Requests spent | **31 of a 160 ceiling** |
| Selection | none — **halted before the rule could run to its stopping condition** |
| Qualifying invocations | **0** |

## The defect

Eligibility admits any candidate declaring `max_completion_tokens >= 32768`. The token-capacity
stress then requested `STRESS_MAX_TOKENS = 131072` **unconditionally**, ignoring what the candidate
declared. A candidate admitted at the eligibility floor was therefore sent a request for four times
its own declared ceiling.

Both candidates that reached the stress had declared 65,536 and answered **HTTP 400**.

> ### Correction — this attribution was wrong
>
> Attempt 02 recorded that the HTTP 400 *was* the overage. **Attempt 03 refutes that.** With the
> request capped at exactly the declared ceiling (65,536 requested, 65,536 declared), the same
> endpoints still answered 400. And in the same run, all ten capability probes sent
> `max_tokens = 131072` — twice the declared ceiling — to those endpoints and every one returned
> **HTTP 200**.
>
> Exceeding a declared ceiling therefore does not cause a 400 on this route, the cap did not fix
> the failure, and **the cause of the 400 remains unestablished**. The bound below is defensible
> hygiene — do not ask for more than a candidate declares — but it is not a diagnosis, and revision
> 3's rationale claimed more than the evidence supported. The claim is corrected here rather than
> quietly amended.

The contradiction the bound removes is nonetheless real:

`MINIMUM_MAX_COMPLETION_TOKENS` (32,768) and `STRESS_MAX_TOKENS` (131,072) contradict each other on
their face, visible in the frozen constants alone; the pre-freeze hostile review should have caught
it. But **that contradiction is not what produced the 400s**, and attempt 02's halt is not
retrospectively justified by it after all. What justifies preserving attempt 02 rather than
resuming it is narrower and still sufficient: its stress clause could not be evaluated, for a
reason the apparatus could not state.

## How the halt actually happened — stated plainly

Execution was halted after candidate 1 on the hypothesis that the identity clauses were failing
because the harness was misreading router metadata. **Candidates 2 and 3 did not support that
hypothesis**: both matched model, provider and canonical checkpoint exactly, which also confirmed
the revision-2 checkpoint repair was correct.

The halt was therefore made for a reason the evidence did not support, and the reason offered in
its place — the token overage — did not survive attempt 03 either. **Neither justification holds.**
What remains true is that attempt 02's stress clause could not be evaluated and its cause could not
be read from the record. A lucky stop is not presented here as a diagnosis.

## What attempt 02 did observe

Recorded because it was measured, and bounded because it is DEVELOPMENT instrument data:

- Candidate 1 (CoreWeave, `ibm-granite/granite-4.2-8b`): **9 of 9** required feature classes
  unenforced, and no identity clause held.
- Candidates 2 and 3 (Google AI Studio, `gemini-3.5-flash`, `gemini-3.1-flash-lite-preview`):
  **0 of 9** feature classes unenforced — every required class enforced — with model, provider and
  canonical checkpoint exact, and `strategy: direct`.

**This is not a qualification and not evidence for H62.** Three of 94 candidates were probed under
a defective apparatus, on small synthetic schemas, on one date. No candidate qualified; none could,
because the stress could not be evaluated. Whether any route qualifies remains unmeasured.

## A second defect, found while diagnosing the first

The declared/observed identity pairs added in revision 2 — precisely so an identity mismatch would
stay diagnosable — **never reached the record**. The profile copied only the boolean verdicts from
a fixed key list, silently dropping the evidence for them. The diagnostic was itself blind, which
is why candidate 1's uniform identity failure could not be diagnosed from the artifact and prompted
the halt. Revision 3 carries every attestation field through, and records whether the router's
`attempts` and `pipeline` are absent, empty or populated, so missing metadata can never again be
indistinguishable from a real fallback.

## What revision 3 does *not* change

- The stress **threshold** is untouched at 32,000 completion tokens. Only the request is bounded,
  to the candidate's own declared ceiling. The bar was not lowered.
- The `no_fallback` and `no_pipeline_intervention` clauses are **not relaxed**, though both failed
  for all three candidates. Absent metadata still fails closed; it is now merely recorded, so the
  next decision rests on evidence rather than on a guess made after seeing candidates fail.
- No threshold, ordering key, tie-break, budget bound or qualification clause moved.
  `tests/test_m117_apparatus_revision.py` pins each one and asserts the plan now refuses to freeze
  a stress an eligible candidate could not clear.

## Disclosed exposure

Partial capability results for three candidates were observed before the corrected apparatus was
frozen. The selection rule is unchanged and remains first-qualifier in an order fixed before any
probe, computed mechanically, so this knowledge cannot advantage a preferred route — but the
exposure is real and is recorded here rather than left implicit.

## Claim boundary

Attempt 02 produced no selection and no qualification. It is not evidence for or against H62 and
leaves G1–G10 untouched.
