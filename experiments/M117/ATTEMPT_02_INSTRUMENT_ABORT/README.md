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

Both candidates that reached the stress had declared 65,536 and answered **HTTP 400**. That 400 is
a malformed request of ours. It is not a capacity limit of theirs, and it must not be recorded as
one.

**This contradiction is visible in the frozen constants alone.** `MINIMUM_MAX_COMPLETION_TOKENS`
(32,768) and `STRESS_MAX_TOKENS` (131,072) contradict each other on their face; no observation was
needed to find it, and the pre-freeze hostile review should have caught it. Any candidate declaring
between 32,768 and 131,071 was guaranteed to fail `token_capacity_stress_holds` for an instrument
reason, so attempt 02 could not have produced a valid selection however long it ran.

## How the halt actually happened — stated plainly

Execution was halted after candidate 1 on the hypothesis that the identity clauses were failing
because the harness was misreading router metadata. **Candidates 2 and 3 did not support that
hypothesis**: both matched model, provider and canonical checkpoint exactly, which also confirmed
the revision-2 checkpoint repair was correct.

The halt is justified — but by the stress defect above, established afterwards and independently,
not by the reason it was made. The record says so rather than presenting a lucky stop as a
diagnosis.

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
