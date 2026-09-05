# M125 prospective publication review

**Prepared:** 6 September 2026  
**Owner decision:** **PENDING**  
**Proposed disposition:** `PUBLIC_AGPL_COMMERCIAL_OPTION`  
**Proposed register entry:** **P-029 — not recorded**  
**Status:** **REVIEW ONLY — NO ENABLING IMPLEMENTATION IS AUTHORISED BY THIS DOCUMENT.**

This review is prepared before any M125 network request, DEVELOPMENT observation, enabling M125
implementation, carrier bank, scientific freeze or qualifying generation. It records the decision
surface the owner must accept, amend or refuse before the first enabling public implementation is
published.

The 5 September owner reconciliation explicitly preserves the distinction that M125 design may be
prepared publicly while that fact alone does **not** authorize any M125 scientific request. This
review stays on that side of the boundary: it documents a prospective design and proposed public
posture but writes no P-029 row to `IP_ASSET_REGISTER.md`.

## Asset reviewed

M125 is a proposed prospective readiness-instrument successor to closed M124/H69. It does **not**
reopen or replay M124. Its purpose is to remove instrument defects discovered only after M124's
preserved `not_ready_delivery` observation while keeping the never-yet-tested carrier proposition
unchanged.

The proposed new hypothesis number is H70. Its scientific proposition is intended to repeat H69/H64
verbatim:

> A descendant carrying both pieces of acquired machinery — the attribution cascade and the
> diagnostic policy — resolves demands on carriers it did not design more often than a comparator
> that carries neither, on demands posed identically to both.

The number changes because the apparatus changes prospectively, not because the target is being
moved. H70 is not frozen by this review and no H70 evidence exists.

## Proposed M125 instrument changes

The review currently covers the following prospective instrument design, all to be frozen before any
M125 request if the owner accepts public enabling implementation:

1. **Bounded capability probes.** Non-target output dimensions are bounded so a target-feature probe
   cannot grow arbitrarily. Probe output receives a small engineering token cap. A violation of a
   safety envelope is classified as an instrument failure, not attributed to the feature under test.
2. **Complete named feature coverage.** Every feature class required by the candidate census must
   have an explicit isolated probe or a mechanically documented coverage mapping. The inherited
   matrix currently lists `items` as required without giving it a named isolated probe; M125 must
   close that diagnostic gap.
3. **One delivery predicate.** Request-level retry and verdict classification use the same definition
   of whether the route answered. Empty HTTP 200 responses and content without a usable
   `finish_reason` are handled consistently rather than consuming a whole-instrument allowance while
   request-level retries remain unused.
4. **Correct retry metadata.** `Retry-After` is read from the transport's actual
   `response_headers` field. A 4xx request rejection other than the explicitly retryable delivery
   classes is not silently retried as though it were a transient route failure.
5. **Prospective terminal precedence.** A completed terminal identity/feature/envelope/reasoning
   finding is not maskable by a later delivery failure. Truncation is not assigned to a target
   feature merely because it happened during that probe.
6. **Pinned stress cardinalities.** The inherited M122 non-carrier stress shape is copied into a new
   M125 stress instrument with every bounded inner array pinned by a deterministic rule independent
   of the historical token observations. The current design candidate is the upper midpoint
   `ceil((minItems + maxItems) / 2)` for each bounded inner array. The pre/post structural census must
   remain byte-identical as a data structure even though the schema bytes change.
7. **Fresh calibration only.** M122/M123/M124 token rates, station counts and the M124 85,000-token
   operational ceiling are historical motivation, not M125 calibration data. A fixed geometric
   calibration queue of 8, 16 and 32 stations is proposed. Completed calibration points are
   persistent and may not be redrawn on a later delivery attempt.
8. **One pre-calibration protocol digest.** The calibration queue, pinning rule, retry semantics,
   verdict ladder, threshold, uncertainty formula and final-size derivation are all bound before the
   first calibration request. The final station count is a deterministic output of that protocol,
   not a new post-measurement plan choice.
9. **Out-of-sample final stress.** The proposed inherited lower threshold remains 32,000 completion
   tokens. The current design candidate uses an a-priori operational ceiling of 65,536 tokens — half
   of the 131,072 requested maximum — and a fixed multiplicative uncertainty factor of 1.25 around
   the fresh calibration rates. If those bounds yield no admissible station count, or if the final
   stress falls outside its derived band, M125 closes rather than refitting itself.
10. **Delivery ceiling preserved.** M124 closed with 4 of the globally bounded 6 delivery attempts
    spent. M125 does not reset that ceiling. Only genuine delivery-only closures may use the two
    remaining global slots; terminal instrument findings do not become replayable.

These details are prospective design candidates until an M125 preregistration/protocol freezes them.
No request has been sent under them.

## Third-party, confidentiality and security review

The proposed instrument stays on the already-used fixed DEVELOPMENT route and project-controlled
Python apparatus. The expected implementation uses Python standard library facilities plus existing
repository development tooling. The external model/provider route is an existing operational
dependency, not project-owned evidence or task authorship.

No credential may be committed. No plaintext sealed bank, confidential third-party payload or
security-sensitive authority is part of this review. No new filesystem, network, credential,
deployment or repository authority is proposed for the tested descendant.

At this review stage no concrete patent-first, intentional trade-secret, contractual-embargo,
confidential-third-party or security-sensitive reason for temporary private treatment has been
identified. That supports the proposed default `PUBLIC_AGPL_COMMERCIAL_OPTION`; it does not substitute
for the owner's decision.

## Scientific boundary

Acceptance of the proposed publication disposition would authorize public enabling implementation and
prospective DEVELOPMENT hardening only. It would **not**, by itself:

- authorize any M125/H70 network request before its request protocol is frozen;
- authorize a qualifying scientific generation, carrier bank, seal or reveal;
- reclassify or replay M124;
- reset the 4/6 cross-instrument delivery count;
- turn DEVELOPMENT calibration into H70 evidence;
- authorize M121/H66 canonical execution, M092/H38 resumption or D063/H39 acceptance;
- satisfy H21/M075 or H31/M085 external-independence requirements;
- advance a generality gate or support an AGI claim.

## Proposed owner decision

If the owner accepts the public path, the proposed decision is:

`P-029 — M125/H70 prospective bounded readiness and fresh-calibration instrument — PUBLIC_AGPL_COMMERCIAL_OPTION`

with the actual owner decision date recorded at the time of acceptance. Until that happens, P-029 is
**not** a ledger entry and enabling M125 implementation remains blocked by publication governance.
