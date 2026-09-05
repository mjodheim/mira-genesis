# M125/H70 preimplementation scientific review — 6 September 2026

**Review class:** prospective instrument design, before M125 implementation or requests  
**Current disposition:** **GO FOR DESIGN REVIEW ONLY; BLOCK ENABLING IMPLEMENTATION AND ALL NETWORK REQUESTS UNTIL THE PUBLICATION GATE IS RECORDED**  
**Scientific observation count for H70:** **0**  
**Inherited global delivery count:** **4 / 6 spent**

This review exists because M124 closed cleanly without replay while exposing defects that would make a
straight copy-and-retry scientifically weak. The correct successor is a newly numbered instrument,
not a repaired M124.

Nothing here edits, rescales or reinterprets M122, M123 or M124. Historical observations may explain
why a design problem matters; they may not provide M125 calibration values.

## 1. Scientific identity must not drift

Proposed H70 repeats the never-yet-tested carrier proposition verbatim from H69/H64:

> A descendant carrying both pieces of acquired machinery — the attribution cascade and the
> diagnostic policy — resolves demands on carriers it did not design more often than a comparator
> that carries neither, on demands posed identically to both.

A future M125 preregistration should state explicitly that the hypothesis number changes only because
the readiness apparatus changes. It must not introduce a new success criterion, easier carrier class,
new comparator or weaker notion of resolution.

A readiness result — including `ready` — is not evidence for H70. Readiness only determines whether
the later scientific apparatus is permitted to be frozen.

## 2. Boundaries inherited unchanged

Unless a later owner-approved preregistration explicitly says otherwise before observation, M125
should inherit these boundaries:

- M122's candidate carrier contract, not a new carrier target;
- the fixed M118 route identity and no-fallback requirement;
- the 32,000 completion-token lower capacity threshold;
- reasoning effort `none` and zero tolerated reasoning tokens;
- DEVELOPMENT probes that carry no qualifying carrier input or carrier-quality statistic;
- the global delivery ceiling, now 4 of 6 spent;
- no generality-gate movement from readiness;
- no raw completion content persisted by the readiness record.

The M124 candidate schema digest recorded in the closed result is
`8e766971941f1ca14c2d035f125c383230c62343329e9c6ee475e05e1b77cbbf`. A future M125 protocol should
recompute and bind the inherited contract digest rather than trusting this prose value.

## 3. Defect A — probes must have bounded non-target dimensions

M124 inherited probes whose target condition was narrower than their possible output volume:

- `required`: six string values without a length bound;
- `additional_properties`: `kept` is an unbounded string and the prompt invites extra material;
- `min_items`: `minItems: 40` with no `maxItems`;
- nested/depth helpers contain leaf strings that are not intrinsically bounded.

M124's `additional_properties` observation reached 101,757 tokens and `finish_reason=length`. Because
the JSON never parsed, that observation cannot establish that `additionalProperties: false` itself
failed.

### Prospective M125 rule

Every probe must have a **safety envelope distinct from the target feature**. Prefer already-required,
small-domain constraints rather than introducing unnecessary new decoder dependencies:

- bounded enum/pattern values for string leaves;
- an exact `maxItems` safety bound for the `minItems` probe;
- prompts that request only the minimum finite set of deliberately forbidden extras rather than
  open-ended additional keys;
- a small per-probe engineering output cap, proposed at **4,096 tokens**.

If a completion violates the target feature, record a target-feature finding. If it violates a
non-target safety envelope, or reaches the probe token cap, record a terminal **probe-envelope /
instrument** finding instead. A truncation is never automatically attributed to the target feature.

The instrument must inspect the validator's failing keyword/location before assigning a class.

## 4. Defect B — every required feature class needs named coverage

`m116_capability_probes.required_feature_classes()` can require `items`; the current M124 contract does.
But the inherited `build_matrix()` has no isolated probe named `items`. It is covered only indirectly by
nested/combined schemas.

That is a diagnostic hole: the result can list a feature as required without a one-to-one named
measurement explaining how it was tested.

### Prospective M125 rule

The frozen protocol must contain a machine-checkable coverage map:

`required census class -> one or more named decisive probes`

Every required class must appear in the map. Prefer an isolated `items` probe; if a class is genuinely
only testable jointly, the protocol must state why and the checker must verify that the mapped joint
probe contains a counterfactual capable of exposing non-enforcement of that class.

The test suite should fail if `required_feature_classes - covered_feature_classes` is non-empty.

## 5. Defect C — one definition of "the route answered"

M124 had two incompatible notions:

- `_send()` treated an empty HTTP 200 as a completed request because status 200 was not retryable;
- the verdict layer later classified that same shape as `undeliverable`.

That spent a whole-instrument delivery slot while request-level retries remained unused.

### Prospective M125 rule

Define one pure predicate before the first request, for example:

`answered := non-empty completion content AND usable string finish_reason`

Use that predicate in both transport and scoring.

Recommended request handling:

- answered response: never retry merely because of HTTP status; it is an observation and is scored;
- no answer + HTTP 200: retry inside the request-level budget;
- no answer + 429/5xx or transport failure: retry inside the request-level budget;
- no answer + deterministic non-429 4xx request rejection: terminal instrument/request error, not a
  capability finding and not a transient-delivery redraw.

Content with no `finish_reason` remains a delivery/no-answer shape, preserving M124's prospective
classification decision without replaying M124.

## 6. Defect D — Retry-After must use the transport's real field

`_http()` returns retained headers under `response_headers`; M124's wait function reads `headers`.
Therefore an advertised `Retry-After` can be silently ignored.

### Prospective M125 rule

- read only `observed["response_headers"]`;
- case-normalize the retained `retry-after` key;
- parse a numeric delay fail-closed to the frozen exponential fallback when malformed;
- cap the delay by a predeclared maximum;
- regression-test the actual `_http()` return shape, not a hand-written alternate key.

## 7. Defect E — terminal findings must not be masked by later delivery

M124 evaluated accumulated `undeliverable` state before `enforcement_failed_open`. A later delivery
failure could therefore mask an earlier terminal state.

### Prospective M125 rule

Prefer **short-circuit execution** over a complicated post-hoc priority table:

1. send a request only while no terminal completed observation exists;
2. exhaust request-level delivery retries for the current request;
3. if no answer remains, close the instrument as delivery-only;
4. if an answered response establishes a terminal identity, target-feature, safety-envelope,
   reasoning or calibration finding, stop immediately and persist that verdict;
5. never send later requests that could mask it.

The final checker should recompute the same order from persisted observations, so control flow and
verdict reconstruction agree.

## 8. Redesign the stress by deterministic pinning

The M122 stress has several bounded inner arrays whose lengths are selected by the model:

- `readings`: 1..3;
- `channels`: 1..3;
- `masts`: 3..4;
- `offline`: 0..1;
- `fault_codes`: 1..4;
- `instruments`: 2..3.

Those degrees of freedom change output size while station count stays fixed.

### Proposed pin rule

Before any fresh M125 measurement, pin every bounded **inner** array to:

`ceil((minItems + maxItems) / 2)`

which yields:

| Array | Old range | Proposed exact count |
| --- | ---: | ---: |
| readings | 1..3 | 2 |
| channels | 1..3 | 2 |
| masts | 3..4 | 4 |
| offline | 0..1 | 1 |
| fault_codes | 1..4 | 3 |
| instruments | 2..3 | 3 |

The top-level station count is deliberately **not** pinned by this rule; it is derived from fresh
calibration later.

The rule is independent of historical token outcomes. The implementation must mechanically prove that
M122's stress census and the pinned M125 stress census are exactly equal as census data. This is
expected because only existing `minItems`/`maxItems` values change; keyword occurrence, depth, type and
array-of-object structure do not. If the census changes, the implementation is wrong and no request is
permitted.

Pinning intentionally changes the schema bytes. Therefore all M122/M123/M124 token measurements are
invalid as M125 calibration and must stay historical-only.

## 9. Fresh calibration must be frozen before it begins

### Proposed fixed calibration queue

`8 -> 16 -> 32` stations.

These are a geometric sequence chosen as a structural design rule, not selected from historical token
rates. The queue order, request cap, route identity checks and completion requirements must live in the
pre-calibration protocol digest.

A calibration point is usable only when it:

- receives an answered response;
- reports `finish_reason == "stop"`;
- conforms to the pinned schema;
- holds exact route identity;
- respects the reasoning control;
- records only metadata needed for sizing, not raw completion content.

`finish_reason == "length"` at a calibration point is a terminal calibration/instrument finding, not a
rate estimate.

### Resume rule

A completed calibration point may **never be redrawn**. If delivery fails before a point receives an
answer, a permitted later delivery attempt resumes at the first unanswered point and skips every
completed point byte-for-byte.

Persist each completed point with a digest and bind all completed points before final-size derivation.
The final readiness stage must refuse if any calibration record can be modified without changing the
bound calibration digest.

## 10. One pre-calibration protocol digest, one deterministic sizing rule

Do not create a new selectable plan after seeing 8/16/32.

Before the first calibration request, bind one protocol containing at least:

- exact pinned schema digest and proof that its census equals the inherited census;
- calibration counts `[8, 16, 32]` and their order;
- request-level retry semantics;
- exact route identity;
- 32,000 inherited lower threshold;
- final operational ceiling;
- uncertainty factor;
- formula for the admissible station interval;
- deterministic final station choice;
- complete verdict ladder;
- local and global delivery accounting rules.

### Proposed sizing rule

For each fresh completed calibration point:

`rate_i = completion_tokens_i / stations_i`

Let:

- `raw_low = min(rate_i)`;
- `raw_high = max(rate_i)`;
- fixed uncertainty factor `F = 1.25`;
- `effective_low = raw_low / F`;
- `effective_high = raw_high * F`.

Use an a-priori operational ceiling of **65,536 completion tokens**, defined before calibration as half
of the 131,072 requested maximum. It is deliberately not the historical 85,000 choice.

Then derive:

- `min_stations = floor(32000 / effective_low) + 1`;
- `max_stations = floor(65536 / effective_high)`.

If `min_stations > max_stations`, the instrument closes `not_ready_calibration_window` (name may be
refined before freeze). It may not shrink the uncertainty factor or move either token boundary.

Otherwise choose the integer midpoint deterministically:

`stations = floor((min_stations + max_stations) / 2)`.

The predicted final band is
`[effective_low * stations, effective_high * stations]`.

No model fitting, curve family or post-calibration parameter selection is permitted.

## 11. Final stress is an out-of-sample test of the fresh calibration

The final stress uses the same pinned inner shape and the derived top-level station count. `ready`
requires all of the following conjunctively:

- exact route identity;
- answered completion with `finish_reason == "stop"`;
- schema conformance;
- zero disallowed reasoning tokens;
- completion tokens strictly above 32,000;
- completion tokens at or below 65,536;
- completion tokens inside the frozen predicted band;
- all required feature/safety probes already passed under the same M125 protocol;
- no prior terminal finding;
- delivery allowance not exceeded.

If the final stress lands outside its predicted band, the result is a terminal calibration miss. Do
**not** add the point to the calibration set and refit.

If the final stress truncates, record truncation as a stress/instrument capacity finding. Do not map it
to an unrelated capability class.

## 12. Delivery accounting cannot reset inside M125

M124 closed after the fourth globally counted delivery attempt, leaving **two of six**.

M125's pre-calibration protocol digest should identify one instrument across calibration and final
stress. Deriving the final station count from fresh measurements must not create a new instrument ID
or reset the local allowance.

A whole-instrument delivery-only closure consumes one global slot. Request-level retries do not each
consume a global slot. Previously completed calibration points remain completed on a permitted retry.

Any terminal non-delivery M125 verdict closes M125 and cannot be superseded.

## 13. Required tests before the first request

At minimum, DEVELOPMENT unit tests should prove:

1. every required census feature has named coverage;
2. all probe schemas have bounded non-target output dimensions;
3. a target-keyword failure and safety-envelope failure classify differently;
4. probe truncation never becomes a target-feature finding;
5. empty HTTP 200 is retried at request level;
6. content without `finish_reason` is retried as delivery/no-answer;
7. `Retry-After` is read from `response_headers`;
8. non-429 deterministic 4xx request rejection is terminal instrument error;
9. an earlier terminal finding short-circuits later requests;
10. pinned stress census equals inherited stress census;
11. calibration queue is exactly 8/16/32 and completed points are skipped on resume;
12. historical M122/M123/M124 observations are absent from the sizing function inputs;
13. uncertainty/window formulas reproduce exactly;
14. empty admissible window closes rather than tuning constants;
15. final out-of-band stress closes rather than refitting;
16. global delivery accounting begins at 4/6 and cannot reset through a derived final size;
17. no readiness artifact contains raw completion content or carrier-quality statistics;
18. no qualifying input is sent by any readiness/calibration path.

Run the complete repository suite on supported Python versions after these targeted tests.

## 14. Governance gates

This review does **not** record P-029 and does not authorize enabling implementation. The companion
`docs/IP_REVIEWS/M125_PUBLICATION_REVIEW.md` proposes `PUBLIC_AGPL_COMMERCIAL_OPTION`; the owner must
accept, amend or refuse it before enabling M125 implementation is publicly disclosed.

Even after a publication decision, a separate chronology boundary remains before any network request:
the exact M125 preregistration/protocol, probe coverage, pinning rule, calibration queue, sizing
formula, verdict ladder and delivery accounting must already be committed and mechanically verified.

A later `ready` result would authorize only the next frozen apparatus stage. It would not support H70
and would not itself authorize the one-shot scientific generation/reveal.

## Disposition

**M125 is scientifically repairable without loss, but only as a new prospective instrument.**

Proceed with publication review and offline implementation/tests after P-029 is decided. Do not send
M125 requests, do not reuse old calibration numbers, do not replay M124 and do not let a future
readiness pass be described as carrier evidence.
