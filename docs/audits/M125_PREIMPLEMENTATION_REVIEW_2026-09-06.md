# M125/H70 preimplementation scientific review — 6 September 2026

**Review class:** prospective instrument design, before any M125 network request  
**Owner publication decision:** **P-029 / `PUBLIC_AGPL_COMMERCIAL_OPTION`, accepted 6 September 2026**  
**Current disposition:** **GO FOR PUBLIC ENABLING IMPLEMENTATION AND OFFLINE DEVELOPMENT TESTS; BLOCK ALL NETWORK REQUESTS UNTIL THE EXACT REQUEST PROTOCOL IS FROZEN, COMMITTED AND MECHANICALLY VERIFIED**  
**Scientific observation count for H70:** **0**  
**Inherited global delivery count:** **4 / 6 spent**

The explicit owner record is `docs/IP_REVIEWS/P029_OWNER_DECISION_2026-09-06.md`. P-029 resolves publication governance only. It does not authorize a DEVELOPMENT request, a qualifying scientific generation, a reveal or result acceptance.

This review exists because M124 closed cleanly without replay while exposing defects that would make a straight copy-and-retry scientifically weak. The correct successor is a newly numbered instrument, not a repaired M124.

Nothing here edits, rescales or reinterprets M122, M123 or M124. Historical observations may explain why a design problem matters; they may not provide M125 calibration values.

## 1. Scientific identity must not drift

H70 repeats the never-yet-tested carrier proposition verbatim from H69/H64:

> A descendant carrying both pieces of acquired machinery — the attribution cascade and the
> diagnostic policy — resolves demands on carriers it did not design more often than a comparator
> that carries neither, on demands posed identically to both.

The hypothesis number changes only because the readiness apparatus changes. M125 must not introduce a new success criterion, easier carrier class, new comparator or weaker notion of resolution.

A readiness result — including `ready` — is not evidence for H70. Readiness determines only whether a later scientific apparatus stage may be prepared under its own chronology.

## 2. Boundaries inherited unchanged

M125 offline implementation must inherit:

- M122's candidate carrier contract, not a new carrier target;
- the fixed M118 route identity and no-fallback requirement;
- the 32,000 completion-token lower capacity threshold;
- reasoning effort `none` and zero tolerated reasoning tokens;
- DEVELOPMENT probes carrying no qualifying carrier input or carrier-quality statistic;
- the cross-instrument delivery ceiling, currently 4 of 6 spent;
- no generality-gate movement from readiness;
- no raw completion content persisted by readiness/calibration records.

The implementation must recompute and bind the inherited candidate-schema digest mechanically. Prose copies of an old digest are not authoritative.

## 3. Defect A — bounded non-target probe dimensions

M124 inherited probes whose target condition was narrower than their possible output volume. Examples include unbounded strings, a `minItems` probe without a `maxItems`, and prompts inviting open-ended extras. M124's `additional_properties` observation reached 101,757 completion tokens with `finish_reason=length`; because the JSON never parsed, that observation cannot establish that `additionalProperties: false` itself failed.

### M125 rule

Every probe must have a safety envelope distinct from the target feature:

- string leaves receive finite `maxLength` or finite pattern/enum domains;
- the `minItems` probe receives a finite `maxItems` that remains above its target minimum;
- prompts request only a finite deliberate set of forbidden extras;
- all nested/depth leaves are bounded;
- the implementation provides a deterministic structural upper-bound report for every probe schema;
- a small per-probe output cap is an **engineering safety cap**, not a target-feature threshold.

The current implementation target is 4,096 completion tokens, but the tests must establish that every conforming probe instance has a comfortably smaller finite structural serialization bound. If that proof fails, the implementation must fail closed before any request rather than silently raising the cap after observation.

If a response violates the target feature, record a target-feature finding. If it violates a non-target safety envelope or hits the probe cap, record terminal `not_ready_probe_envelope` (or an equivalently frozen name). A truncation is never automatically attributed to the target feature.

## 4. Defect B — every required feature class needs named coverage

The inherited census can require `items`, while the M116/M124 matrix has no isolated probe named `items`. That is a diagnostic hole.

### M125 rule

The protocol must expose a machine-checkable mapping:

`required census class -> one or more named decisive probes`

Every required class must be covered. M125 should provide an isolated `items` probe unless a class is provably joint-only. Tests must fail whenever:

`required_feature_classes - covered_feature_classes != empty`.

The coverage proof itself is part of the pre-request protocol digest.

## 5. Defect C — one definition of "the route answered"

M124's transport and verdict layer disagreed on empty HTTP 200 responses. That allowed an empty 200 to consume a whole-instrument delivery slot while request-level retries remained unused.

### M125 rule

Define one pure predicate before any request:

`answered := non-empty completion content AND usable string finish_reason`

Use the same predicate for transport retry, persisted observation classification and verdict reconstruction.

Frozen request handling:

- answered response: never retry merely because of status; score the observation;
- no answer + HTTP 200: retry inside the request-level budget;
- no answer + HTTP 429, 5xx or transport failure: retry inside the request-level budget;
- no answer + deterministic non-429 4xx request rejection: terminal instrument/request error, not capability and not transient delivery;
- content without usable `finish_reason`: no-answer/delivery shape, preserving M124's prospective classification without replaying M124.

## 6. Defect D — `Retry-After` must use the transport's actual field

M124 retained headers under `response_headers` while retry logic read `headers`.

### M125 rule

- read `observed["response_headers"]` only;
- case-normalize `retry-after`;
- parse numeric delay; malformed values fall back to the frozen exponential rule;
- cap wait by a predeclared maximum;
- test the exact `_http()` return shape.

Offline tests replace sleeping and network I/O with stubs. No M125 request is authorized by P-029.

## 7. Defect E — terminal findings cannot be masked by later delivery

M124 accumulated multiple categories and could let later delivery precedence obscure an earlier terminal finding.

### M125 rule

Use short-circuit execution:

1. send a request only while no terminal completed observation exists;
2. exhaust request-level delivery retries for the current logical request;
3. if it remains unanswered, close the instrument as delivery-only;
4. if an answered response establishes terminal identity, target-feature, probe-envelope, reasoning, calibration or stress finding, persist it and stop immediately;
5. do not send later requests that could mask it.

The checker must reconstruct the same precedence from persisted metadata.

## 8. Deterministic stress pinning

The M122 stress contains bounded inner arrays whose model-selected lengths change output size at fixed station count:

| Array | M122 range | M125 exact count |
| --- | ---: | ---: |
| readings | 1..3 | 2 |
| channels | 1..3 | 2 |
| masts | 3..4 | 4 |
| offline | 0..1 | 1 |
| fault_codes | 1..4 | 3 |
| instruments | 2..3 | 3 |

Before any M125 measurement, pin every bounded inner array to:

`ceil((minItems + maxItems) / 2)`.

The top-level station count is not pinned by this rule; it is derived from fresh calibration.

The implementation must mechanically prove that the M122 stress census and pinned M125 stress census are exactly equal as census data. If any keyword occurrence, depth, type or array-of-object level changes, no request may be permitted.

Pinning changes schema bytes. Therefore M122/M123/M124 token measurements are invalid as M125 calibration and remain historical-only.

## 9. Fresh calibration queue

The fixed queue is:

`8 -> 16 -> 32` stations.

These values are a geometric structural design rule and are bound before the first request. They are not selected from historical token rates.

A calibration point is usable only when it:

- is answered;
- reports `finish_reason == "stop"`;
- conforms to the pinned schema;
- holds exact route identity;
- respects zero reasoning tokens;
- persists only sizing metadata, never raw completion content.

`finish_reason == "length"` at a calibration point is terminal calibration/instrument failure, not a rate estimate.

### Resume rule

A completed calibration point may never be redrawn. If a permitted delivery-only retry occurs before a point answers, the next attempt resumes at the first unanswered point and skips completed points byte-for-byte.

Each completed point has its own digest. Final-size derivation binds the complete calibration set.

## 10. One protocol digest before calibration

There must be no new selectable plan after observing 8/16/32.

Before the first M125 request, one protocol digest binds at least:

- exact pinned schema digest;
- exact census-equivalence proof;
- coverage map and bounded-probe proof;
- calibration counts `[8, 16, 32]` and order;
- request-level retry semantics and answered predicate;
- route identity and endpoint;
- reasoning controls;
- 32,000 lower threshold;
- 65,536 final operational ceiling;
- uncertainty factor `F = 1.25`;
- sizing formulas and deterministic final station choice;
- complete verdict/short-circuit rules;
- request budget;
- local/global delivery accounting;
- information-boundary fields.

The final station count is an output of this frozen protocol, not a post-measurement plan amendment.

## 11. Deterministic sizing rule

For each fresh completed calibration point:

`rate_i = completion_tokens_i / stations_i`

Let:

- `raw_low = min(rate_i)`;
- `raw_high = max(rate_i)`;
- `F = 1.25`;
- `effective_low = raw_low / F`;
- `effective_high = raw_high * F`.

The final operational ceiling is 65,536 completion tokens, fixed prospectively as half of the 131,072 request maximum rather than taken from an M122/M123/M124 observation.

Derive:

- `min_stations = floor(32000 / effective_low) + 1`;
- `max_stations = floor(65536 / effective_high)`.

If `min_stations > max_stations`, close `not_ready_calibration_window`. Do not shrink `F` or move either token boundary.

Otherwise choose:

`stations = floor((min_stations + max_stations) / 2)`.

Predicted final band:

`[effective_low * stations, effective_high * stations]`.

No curve-family selection, regression model choice or post-calibration parameter tuning is permitted.

## 12. Final stress is out-of-sample

The final stress uses the same pinned inner schema and the derived top-level station count.

`ready` requires conjunctively:

- exact route identity;
- answered completion with `finish_reason == "stop"`;
- schema conformance;
- zero reasoning tokens;
- completion tokens strictly above 32,000;
- completion tokens at or below 65,536;
- completion tokens inside the frozen predicted band;
- all required capability/safety probes already passed;
- no prior terminal finding;
- delivery allowance not exceeded.

If final stress falls outside the predicted band, close the instrument. Do not add it to calibration and refit.

If final stress truncates, record a stress/instrument capacity finding, not a target-feature failure.

## 13. Delivery accounting cannot reset

M124 closed after the fourth globally counted delivery attempt, leaving two of six.

M125 has one instrument identity across capability probes, calibration and final stress. Deriving final station count cannot create a fresh allowance.

- request-level retries do not each consume a global slot;
- a whole-instrument delivery-only closure consumes one global slot;
- completed calibration points remain completed on a permitted retry;
- any terminal non-delivery M125 verdict closes M125 and cannot be superseded.

## 14. Required offline tests before any request

At minimum, tests must prove:

1. every required census feature has named coverage, including `items`;
2. all probe schemas have finite non-target output bounds;
3. the probe safety cap is separated from target-feature inference;
4. target-keyword failure and probe-envelope failure classify differently;
5. probe truncation never becomes a target-feature finding;
6. empty HTTP 200 is retried at request level;
7. content without `finish_reason` is retried as no-answer;
8. `Retry-After` is read from `response_headers`;
9. deterministic non-429 4xx request rejection is terminal instrument error;
10. an earlier terminal finding short-circuits later requests;
11. pinned stress census equals inherited stress census;
12. calibration queue is exactly 8/16/32;
13. completed calibration points are skipped on resume;
14. M122/M123/M124 observations are absent from sizing inputs;
15. uncertainty/window formulas reproduce exactly;
16. empty admissible window closes rather than tuning constants;
17. final out-of-band stress closes rather than refitting;
18. global delivery accounting begins at 4/6 and cannot reset through a derived final size;
19. no readiness/calibration artifact contains raw completion content or carrier-quality statistics;
20. no qualifying input is sent by any readiness/calibration path;
21. the network-capable entry point refuses unless a committed protocol/freezing gate exists;
22. ordinary unit tests cannot accidentally call the real network.

The complete repository suite must pass on supported Python versions after these targeted tests.

## 15. Governance and execution gates

P-029 is now recorded by explicit owner decision. Public enabling implementation and offline tests are authorized.

**Still blocked:**

- any M125 request before the exact protocol is committed and mechanically verified;
- any H70 scientific generation, carrier bank, seal, reveal, scoring or result acceptance;
- reuse of old token observations as calibration;
- replay or rescore of M124.

A later readiness `ready` would authorize only the next frozen apparatus stage under its own chronology. It would not support H70 and would not itself authorize the one-shot scientific generation.

## Disposition

**M125 is scientifically repairable without loss as a new prospective instrument. P-029 permits implementation and offline hardening now. Network observation remains a separate future gate.**
