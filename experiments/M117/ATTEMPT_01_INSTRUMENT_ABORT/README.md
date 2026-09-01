# M117 Stage 1, attempt 01 — instrument abort

**This directory is not a result.** It is the record of an apparatus that could not read its own
input. It is preserved verbatim so that the correction applied afterwards is auditable.

| | |
|---|---|
| Frozen plan | `d22c3fde72c70c8f73948aba95250685befcdca5ae90c7b85934c8a6e8508c67` |
| Catalogue snapshot | `aede20474c7d918c…` |
| Candidate universe | `ad5526f9d582b2b6…` |
| Endpoint entries assessed | 282 |
| Eligible candidates | **0** |
| Candidates probed | **0** |
| Generation requests sent | **0** |
| Selection | none |

Attempt 01 read the model catalogue and the per-model endpoints listing — metadata `GET`s only —
and derived a candidate universe of zero. No candidate was probed, no generation request was sent,
no completion was received, no bank exists. **Qualifying invocations remain 0.**

## What went wrong

Three fields were read from places this API does not populate:

| Field | Attempt 01 read | The API publishes it as | Populated |
|---|---|---|---|
| `uptime_last_1d` | `endpoint["stats"]["uptime_last_1d"]` | `endpoint["uptime_last_1d"]` | 43/43 |
| `latency_last_30m_p50` | `endpoint["stats"]["latency_last_30m"]` | `endpoint["latency_last_30m"]["p50"]` | 42/43 |
| `canonical_checkpoint` | `endpoint["model_variant_slug"]` | `model["canonical_slug"]` | 420/420 |

`endpoint["stats"]` is `null` on every endpoint this API returns; `model_variant_slug` is not a
field it returns at all. So `uptime_last_1d` and `latency_last_30m_p50` were `None` for **282 of
282** endpoints, and every candidate was excluded on `missing_required_metric` — 167 of them for
that reason and no other. `canonical_checkpoint` silently fell back to the endpoint's display name
(`"Mancer 2 | anthracite-org/magnum-v4-72b"`), which would have made the checkpoint-identity clause
satisfiable by a string that is not a checkpoint identifier.

`uptime_last_30m` was unaffected: it happened to also be read from the endpoint directly.

## Why this is an abort and not a finding

A zero-eligibility universe is what a route-qualification stage looks like when nothing qualifies,
which is exactly why it must not be reported that way without checking. **A metric null for 282 of
282 endpoints is not a fact about the provider population.** The exclusion was produced by the
instrument, not measured by it. Reporting it as "no route qualifies" would have converted an
instrument failure into a scientific result — the specific error M115 exists to prevent.

## Why the correction is not post-hoc optimisation

The revised apparatus (plan `5cc9c648f9881fd3…`, revision 2) changes **extraction only**:

- The decision rule module `metamorphosis/m117_route_qualification.py` is **byte-for-byte
  unchanged**. Every threshold, ordering key, tie-break, budget bound and qualification clause is
  the value attempt 01 carried; `tests/test_m117_apparatus_revision.py` pins each one against the
  universe committed here, and checks each of the twelve qualification clauses is still
  individually load-bearing.
- The defect was **content-independent and candidate-independent**: it nulled the metric for every
  endpoint uniformly, so it cannot have favoured or disfavoured any candidate. No candidate's
  values were used to choose the repair; the API's response shape forced it.
- The corrected checkpoint field is confirmed against a record that **predates M117**: M116
  recorded the router attesting `deepseek/deepseek-v4-flash-20260731` for requested model
  `deepseek/deepseek-v4-flash-0731`, and the catalogue's `canonical_slug` for that model reproduces
  that string exactly.
- The checkpoint repair makes qualification **stricter**, not looser: it replaces a display name
  that would always have been present with the identifier the router actually attests.

Nothing here licenses lowering a threshold, enlarging eligibility, adding a preferred provider,
weakening the carrier schema, or re-running until something passes. Those remain prohibited. If the
corrected apparatus returns no qualifying route, Stage 1 ends with no selection and H62 is not
created.

## Disclosed exposure

The catalogue was observed before the corrected universe was derived. The ordering is M115's,
frozen before either attempt and unchanged, and the repair was forced by response shape rather than
by any candidate's values — but the exposure is real and is recorded here rather than left implicit.

## Guarding against a repeat

Attempt 01 failed uniformly and *legibly* only because the excluded rows retained their null
metrics. The identity clauses had no such protection: had the checkpoint field been wrong at probe
time, every candidate would have failed `canonical_checkpoint_exact` with nothing in the record to
distinguish that from a real negative. Revision 2 therefore records each observed identity string
beside the declared one, so a systematic mismatch is diagnosable as an instrument abort instead of
being reported as a result.

## Claim boundary

Attempt 01 measured nothing. It is not evidence for or against H62, says nothing about any route's
structured-output enforcement, and leaves G1–G10 untouched.
