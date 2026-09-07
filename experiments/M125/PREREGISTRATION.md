# M125 / H70 — prospective bounded readiness and fresh-calibration preregistration

**Prepared:** 7 September 2026  
**Publication disposition:** P-029 / `PUBLIC_AGPL_COMMERCIAL_OPTION`  
**Current authority:** public implementation and offline DEVELOPMENT hardening only  
**M125 network observations:** 0  
**H70 scientific observations:** 0  
**Inherited global delivery ceiling:** 4 of 6 already spent

## Scientific identity

H70 repeats the never-yet-tested H69/H64 carrier proposition without weakening or moving it:

> A descendant carrying both pieces of acquired machinery — the attribution cascade and the
> diagnostic policy — resolves demands on carriers it did not design more often than a comparator
> that carries neither, on demands posed identically to both.

M125 is an apparatus-readiness successor. A future `ready` readiness verdict would be DEVELOPMENT
evidence about the fixed route only. It would not support H70, authorize a carrier-bank generation,
advance a generality gate, or authorize any scientific reveal/scoring.

M124 remains closed without replay at its preserved `not_ready_delivery` verdict. Nothing in M125
reclassifies M122, M123 or M124.

## Binding design record

This preregistration is subordinate to the already-merged prospective reviews:

- `docs/audits/M125_PREIMPLEMENTATION_REVIEW_2026-09-06.md`;
- `docs/audits/M125_DESIGN_CORRIGENDUM_HATI_2026-09-06.md`;
- `docs/IP_REVIEWS/M125_PUBLICATION_REVIEW.md`;
- `docs/IP_REVIEWS/P029_OWNER_DECISION_2026-09-06.md`.

Where an earlier design description is less strict than the Hati corrigendum, the corrigendum
controls.

## Frozen instrument rules to be bound by `PROTOCOL.json`

### 1. Candidate and route identity

The carrier contract is the existing M122 candidate contract. M125 does not redesign it. The fixed
route remains the M118 route: requested model `deepseek/deepseek-v4-flash-0731`, provider
`OpenInference`, no fallback/provider substitution, and endpoint
`https://openrouter.ai/api/v1/chat/completions`.

The candidate schema digest, route identity, request parameters and the committed source bytes that
interpret observations are protocol-bound before any M125 network request.

### 2. Bounded capability probes

Every feature class required by the candidate census must have explicit named decisive coverage.
The inherited diagnostic gap for `items` is closed with its own isolated probe.

Every non-target probe dimension is finite. The static probe builder computes a conservative upper
bound for compact JSON output and refuses any probe whose compliant output is not safely below the
fixed **4,096-token** request cap. The cap is an engineering safety envelope, not a scientific
threshold.

If a probe reaches `finish_reason == "length"`, the verdict is **`not_ready_probe_envelope`**. That is
an instrument-envelope finding and is never attributed to the feature being probed.

### 3. One shared definition of an answered request

A physical request is `answered` only when it carries non-empty assistant content and a usable
`finish_reason` of `stop` or `length`.

The retry layer and verdict layer use this same predicate. In particular:

- empty HTTP 200 is unanswered and request-level retryable;
- content-bearing HTTP 200 with no usable `finish_reason` is unanswered and request-level retryable;
- HTTP 429, transient 5xx and transport failure are request-level retryable when unanswered;
- deterministic non-429 HTTP 4xx without an answer is **not** transient and closes
  `not_ready_request`;
- a response with `finish_reason == "length"` is answered and is never retried merely to seek a
  cleaner outcome.

At most two retries are available for one logical step, for at most three physical attempts total.
`Retry-After` is read from the transport's actual `response_headers` field. Otherwise deterministic
exponential backoff is used.

### 4. Terminal precedence

Completed findings are terminal before later requests are considered. The prospective readiness
ladder is:

1. `not_ready_request` — deterministic request rejection;
2. `not_ready_identity` — an answered request is not the frozen route;
3. `not_ready_reasoning` — answered route used disallowed reasoning tokens;
4. `not_ready_probe_envelope` — a bounded capability probe truncated;
5. `not_ready_features` — answered `stop` probe does not satisfy its schema;
6. `not_ready_calibration_envelope` / `not_ready_calibration` — a fresh calibration point cannot be
   used under the frozen calibration contract;
7. `not_ready_stress` — the final out-of-sample observation misses the frozen admissible band or
   otherwise fails after successful calibration;
8. `not_ready_delivery` — the whole instrument could not obtain an answer for the current logical
   step after its request-level retry allowance;
9. `ready` — every required probe, fresh calibration point and final out-of-sample stress passes.

The implementation may encode equivalent local ordering, but delivery may not mask a completed
terminal finding.

Only a whole-instrument `not_ready_delivery` closure may be eligible for a later continuation under
the same exact protocol and within the global delivery ceiling. Every other verdict is terminal.
Missing, malformed or unrecognized verdict fields fail closed.

### 5. Anti-rearm and no redraw

Before any network-capable execution, M125 inspects all authoritative M125 result surfaces:

- working-tree canonical result;
- canonical result blob at committed `HEAD`;
- working-tree archived attempts;
- archived-attempt paths independently enumerated from committed `HEAD`.

The archive path set is the union of working-tree and HEAD paths. A terminal result committed at
HEAD cannot be bypassed by deleting, replacing, renaming or editing its working-tree copy.

Logical progress is persistent. Named steps are `probe:<name>`, `calibration:8`, `calibration:16`,
`calibration:32`, and one derived `final:<stations>` step. A completed answered step is never redrawn
on an allowed continuation.

### 6. Pinned stress cardinalities

M125 inherits the M122 non-carrier survey-station stress structure only. Every bounded inner array is
pinned deterministically at the inclusive upper midpoint:

`pinned = floor((minItems + maxItems + 1) / 2)`.

The root station array is separately fixed by the current calibration/final station count. The
implementation must mechanically prove that pinning changes values of cardinality bounds but leaves
the structural census bit-identical.

### 7. Fresh calibration only

M122, M123 and M124 token counts, rates, station counts and transport outcomes are **not calibration
data for M125**. They motivated redesign only.

The M125 calibration queue is fixed before observation at:

`8 → 16 → 32 stations`.

Each completed point must be answered with `finish_reason == "stop"`, conform to the pinned schema,
and carry a positive completion-token count. A completed point is persisted and never redrawn.

For the three fresh rates `tokens / stations`, let `r_low` be the minimum and `r_high` the maximum.
The admissible final station interval is computed deterministically:

- minimum = `floor(32000 / r_low) + 1`;
- maximum = `floor(52428 / r_high)`.

If minimum > maximum, M125 closes `not_ready_calibration`; no fit or threshold is changed.

The final station count is the integer midpoint of the admissible interval. If that exact midpoint
is one of 8/16/32, choose midpoint+1 when still admissible and new, otherwise midpoint-1 when still
admissible and new. If no out-of-sample point exists, close.

The final observation must be answered, stop normally, conform, use the derived station count and
produce **more than 32,000 and at most 52,428 completion tokens**. A miss closes
`not_ready_stress`. **No refit, redraw or second final size is permitted.**

The 65,536 request cap and the 52,428 upper operating bound are protocol constants fixed before any
fresh M125 calibration. Historical M122–M124 truncations do not derive either number.

### 8. Delivery accounting

The cross-instrument delivery ceiling remains **6 total**, with **4 already spent** when M125 opens.
M125 may not reset it. Delivery attempts are reconstructed from repository archives and deduplicated
by result digest rather than filename, because historical archives contain duplicate filenames for
one result.

A reconstruction below the inherited floor of four fails closed instead of manufacturing extra
allowance.

### 9. Interpreting-source manifest

Before any M125 network observation, `PROTOCOL.json` binds a deterministic mapping:

`repository-relative source path -> SHA256(LF-normalized committed bytes)`.

It includes every project-controlled source able to alter transport, validation, probe coverage,
stress construction, sizing, resume, delivery accounting or verdict interpretation. The manifest is
itself inside `protocol_sha256`.

Immediately before execution, the minimal gate verifies for each manifest path that:

1. the normalized committed HEAD blob hashes to the frozen manifest value; and
2. the normalized working-tree file is byte-identical to that HEAD blob.

Dirty, missing, substituted or newly committed interpreting code therefore invalidates the frozen
protocol before credential access.

### 10. Credential and network gate

`--execute` must remain fail-closed in this order:

1. inspect M125 anti-rearm surfaces;
2. load and verify committed `PROTOCOL.json` and working-tree equality;
3. verify `protocol_sha256` and the interpreting-source manifest;
4. load a separately committed `NETWORK_AUTHORIZATION.json`;
5. prove that authorization is DEVELOPMENT-only and binds this exact protocol digest;
6. reconstruct delivery accounting and resume state;
7. **only then** read `OPENROUTER_API_KEY`;
8. only after credential success may transport/network code become reachable.

No `NETWORK_AUTHORIZATION.json` is created by this implementation work. Therefore a repository-level
`--execute` must currently refuse before touching the credential accessor.

## Information boundary

M125 readiness records:

- no raw model completion;
- no carrier bank;
- no qualification statistic or carrier-quality comparison;
- no H70 evidence;
- only route identity, structural conformance, token counts, finite diagnostic locations and
  DEVELOPMENT apparatus state needed to reproduce the readiness verdict.

## Freeze and next gate

The exact implementation, offline tests, CI and hostile review must settle before `PROTOCOL.json` is
considered frozen. Once the committed protocol digest and source manifest are mechanically verified,
**the next owner gate is a separate decision whether to authorize DEVELOPMENT network observations
under that exact digest**.

Until that decision is recorded in a committed `NETWORK_AUTHORIZATION.json`, M125 must remain
network-inert and H70 remains untested.
