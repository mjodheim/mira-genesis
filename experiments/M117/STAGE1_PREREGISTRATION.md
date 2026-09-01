# M117 Stage 1 — route qualification, frozen before the first request

**Status:** FROZEN. Committed before any candidate is probed.
**Frozen plan digest:** `47ff587ff36e994a498ae8d63b6cc185ded94a7b1c9f429290a754b3a1181564`
**Apparatus revision:** 4, superseding `687b239471245b96…` (r3), `5cc9c648f988…` (r2) and `d22c3fde72c7…` (r1).
**Phase:** DEVELOPMENT only. Not evidence for H62. **Qualifying invocations: 0.**

> **Revision 2 changes extraction only.** Attempt 01 read three catalogue fields out of places the
> endpoints API does not populate, derived a universe of zero eligible candidates, probed nothing
> and sent no generation request. It is preserved verbatim as an instrument abort in
> [`ATTEMPT_01_INSTRUMENT_ABORT/`](ATTEMPT_01_INSTRUMENT_ABORT/README.md), which records the defect,
> the correction, and why the correction is not post-hoc optimisation. The decision rule module is
> byte-for-byte unchanged: no threshold, ordering key, tie-break, budget bound or qualification
> clause moved, and `tests/test_m117_apparatus_revision.py` pins each of them against the universe
> attempt 01 committed.
>
> **Revision 3 bounds a malformed request.** Attempt 02 read its input correctly but sent every
> structurally qualified candidate a stress request for 131,072 tokens regardless of the ceiling
> that candidate declared, while eligibility admits candidates at 32,768 — a contradiction visible
> in the frozen constants alone. It is preserved halted, at 31 of 160 requests with no selection, in
> [`ATTEMPT_02_INSTRUMENT_ABORT/`](ATTEMPT_02_INSTRUMENT_ABORT/README.md). The stress threshold is
> unchanged; only the request is capped at the candidate's declared ceiling, and the plan now
> refuses to freeze a stress an eligible candidate could not clear.

> **Revision 4 re-specifies two unsatisfiable clauses, under owner authorization.** Attempt 03 ran
> to its 160-request ceiling and selected no route, but `no_fallback` and `no_pipeline_intervention`
> required the router metadata fields `attempts` and `pipeline` to be present **and** empty. Attempt
> 03's diagnostic established that this API emits neither key on any request — absent on successful
> requests as much as on rejected ones — so no route could satisfy them, and a run ending with no
> selection could not distinguish a route that fails from one that passes. Attempt 03 is preserved
> in [`ATTEMPT_03_INSTRUMENT_ABORT/`](ATTEMPT_03_INSTRUMENT_ABORT/README.md).
>
> The **fact required is unchanged** — exactly one routing attempt, no fallback, no pipeline
> intervention. It now rests on evidence the API does emit, and which already held on every fully
> enforcing candidate: `strategy: direct`, `attempt: 1`, exactly one selected endpoint, and the
> `allow_fallbacks: false` this harness sends on every request. Where the router *does* report the
> fields they are still judged on their contents — a single failed attempt record is not a clean
> single attempt — so absence never overrides a positive report to the contrary.
>
> This change was **not** made unilaterally. It was reached only after watching the clauses block
> every candidate, which is the post-hoc weakening the authorization prohibits, and so was put to
> the owner and authorized before being implemented. No threshold, ordering key, tie-break or budget
> bound moved.

## The premise this is built on

M116 closed because its fixed route enforced **none** of the nine schema feature classes the frozen
carrier schema relies upon — while the provider catalogue declared `supports_structured_outputs:
true` for it. So:

> **A catalogue claim is not evidence. Only measured enforcement is.**

Declared capability appears here in exactly one place: as an eligibility filter that bounds which
candidates are worth spending budget on. It qualifies nothing. A route that advertises everything
and enforces nothing fails Stage 1, exactly as M116's did.

## Order of operations — the safeguard

1. **This apparatus is frozen and committed** — before any network request.
2. **The catalogue is read and snapshotted** — metadata GETs only; no generation, no completion
   tokens, no carrier.
3. **The candidate universe is derived and committed**, with its digest and its total order.
4. **Candidates are probed in that order**, using the M116 capability matrix unchanged.
5. **The first qualifier in the frozen order is the selection.**

Nothing observed at step 4 can change the order fixed at step 3, the thresholds fixed at step 1, or
which candidate comes next. **No provider may be added once probing begins.**

## Why "first qualifier in the frozen order" is the entire selection algorithm

Candidates are totally ordered before any is probed, by the reliability ordering inherited from M115
— committed there before that milestone's first matrix and never re-derived. Reusing it verbatim is
deliberate: an ordering rewritten for M117 could be rewritten to put a preferred provider first.

Because the order is fixed in advance and independent of every observation, the first qualifier *is*
the best-ordered qualifier. There is no version of this rule under which continuing to probe could
produce a better answer, and none under which an observation changes who is next. It also spends the
smallest budget consistent with the rule.

## Eligibility — bounds budget, qualifies nothing

A catalogue entry is eligible only if it reports every required metric completely
(`uptime_last_1d`, `uptime_last_30m`, `latency_last_30m.p50` — a missing metric excludes rather
than defaults, because a default would be a value we chose), meets uptime ≥ 99.0 % over 1 day and
≥ 95.0 % over 30 minutes, declares `max_completion_tokens` ≥ 32,768, declares
`response_format`, `structured_outputs` and `seed`, declares a canonical checkpoint the endpoint
serves, and is available.

Exclusion reasons are a closed set, and every one is reachable: `missing_required_metric`,
`uptime_last_1d_below_minimum`, `uptime_last_30m_below_minimum`,
`max_completion_tokens_below_minimum`, `missing_supported_parameter`,
`no_canonical_checkpoint_declared`, `endpoint_not_available`.

The catalogue is read in **model-id ascending order**, fixed here, so the universe cannot depend on
the order the catalogue happens to return. At most 60 models' endpoints are fetched.

## Ordering and tie-break

`uptime_last_1d` descending, then `uptime_last_30m` descending, then `latency_last_30m.p50`
ascending, then **provider name ascending**, then model id ascending for a total order.

## Qualification — every clause, no partial credit

A candidate qualifies only if **all** hold: every census-required feature class enforced; the
combined structural probe conforms; the token-capacity stress holds; requested model identity
exact; canonical checkpoint exact; provider exact; direct routing; no fallback; one selected
endpoint; one router attempt; no pipeline intervention; reliability minimum holds.

**Partial capability is not qualification.** A route never qualifies because it looked promising.

The capability matrix is **M116's, inherited unchanged** — the same probes, derived from the same
census of the same frozen carrier schema, the same underspecified-prompt design, the same outcome
vocabulary, and literally the same classifier code rather than a copy. A copy could drift into being
kinder to a preferred provider.

Two request parameters are stated explicitly because fidelity matters: probes send the same
`max_tokens` the inherited matrix sends (131,072), so any truncation is the route's behaviour and
not this harness's artifact; and the reasoning-off control is sent **exactly when the catalogue
declares the parameter**, because `require_parameters: true` would otherwise exclude an endpoint
that does not accept it at all. That rule is mechanical and recorded per candidate.

The token-capacity stress runs **only after full structural qualification**, so a route that
enforces nothing never spends budget proving it can emit volume.

## Budget, fixed here

At most **3 requests per probe**, **40 per candidate**, and a **global ceiling of 160 DEVELOPMENT
requests**. Exceeding the ceiling ends Stage 1 **without a selection** rather than being widened. A
candidate cut short by the ceiling is recorded as incomplete — it cannot qualify, and dropping it
silently would hide budget spent on its behalf.

## Retry

The only permitted retry is an explicit HTTP 429 carrying no completion and no evidence that the
model executed. **No content-dependent redraw. No repair. No resend of a materialized observation.**
A schema violation never justifies another request. Crash-safe resumption preserves consumed
observations and never re-sends them.

## Prohibited

Adding a candidate after probing begins; manually preferring a candidate; carrier quality as a
selection input; weakening a threshold after an observation; changing a prompt or schema after an
observation; substituting a route; treating M116's previous route specially. A test asserts the
Stage 1 sources name no specific model or provider at all.

## Stopping rule

Probe in the frozen order until a candidate qualifies or the global ceiling is reached. **If none
qualifies, Stage 1 ends with no selection and H62 is not created** — that is a finding about the
reachable instrument family, recorded as one, and not a licence to lower a threshold, enlarge
eligibility, add a preferred provider, weaken the carrier schema, rewrite the matrix, or re-run
candidates until one passes.

## The selection rests on evidence, not on a recorded verdict

Qualification is **recomputed at the point of selection** from each candidate's own profile, rather
than read from the verdict stored alongside it. A stored verdict is a claim; the decision should
rest on the evidence it claims to summarise. Without this, a profile asserting `qualifies: true`
would select a route that never passed a single check. An incomplete candidate is skipped rather
than considered.

## Independent replay

`scripts/check_m117_stage1.py` recomputes from committed artifacts alone: every digest, the
chronology binding plan → catalogue → universe → report, the universe replayed from the catalogue
snapshot, every candidate's qualification replayed from its own profile, and the selection replayed
from the frozen order. It refuses a record whose chronology cannot be proven, and refuses any probed
candidate absent from the committed universe. Observations are never re-derived: they are what was
seen.

## What is never persisted

Credentials, generated completion content, reasoning content, arbitrary provider free text, or
carrier content. Diagnostic paths are built only from schema-declared property names and array
indices.

## Claim boundary

Stage 1 measures which structured-output capabilities candidate endpoints enforce, on small
synthetic schemas, on one date. It is instrument qualification and **is not evidence for H62 at
all**. G1–G10 are unchanged whatever it returns.
