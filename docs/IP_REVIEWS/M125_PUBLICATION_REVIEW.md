# M125 prospective publication review

**Prepared:** 6 September 2026  
**Owner decision recorded:** 6 September 2026  
**Disposition:** `PUBLIC_AGPL_COMMERCIAL_OPTION`  
**Register entry:** **P-029**  
**Status:** **PUBLIC ENABLING IMPLEMENTATION AND OFFLINE DEVELOPMENT HARDENING AUTHORISED; NETWORK/SCIENTIFIC EXECUTION REMAINS SEPARATELY GATED.**

This review was prepared before any M125 network request, DEVELOPMENT observation, enabling M125 implementation, carrier bank, scientific freeze or qualifying generation. Anthony Mets, sole human research director and release/acceptance decision-maker, explicitly accepted the proposed public disposition on 6 September 2026. The explicit owner record is `docs/IP_REVIEWS/P029_OWNER_DECISION_2026-09-06.md`.

The decision authorizes public enabling implementation and offline DEVELOPMENT hardening/tests. It does not authorize a network request or scientific execution merely because the implementation may now be public.

## Human and AI contribution provenance

Anthony Mets supplied the research direction and acceptance boundary, reviewed the M124 failure/audit record, explicitly accepted P-029, chose to preserve M124 without retrospective repair and remains the sole human authority for selecting, rejecting and releasing proposed changes.

OpenAI ChatGPT provided substantial AI-assisted synthesis of the M124 audit, prospective M125 research design, governance drafting and implementation planning. That contribution includes the bounded-probe/safety-envelope design, the missing isolated `items` coverage finding, the unified delivery predicate, deterministic stress pinning, fresh 8/16/32 calibration queue, no-redraw rule and separation of offline implementation from later network/scientific authority. The GitHub Codex review bot independently reviewed this branch and identified the provenance-completeness defect that caused this section and the companion owner record to be expanded. Anthropic Claude's earlier M124 implementation/audit findings are upstream technical inputs motivating several M125 repairs. All three are AI tooling/research assistance, not human authorship or release authority.

Anthony Mets selected which findings to accept, rejected retrospective alteration of frozen M124, explicitly approved the publication posture and instructed work to continue only to the next scientific/governance gate.

## Asset reviewed

M125 is the prospective readiness-instrument successor to closed M124/H69. It does **not** reopen or replay M124. Its purpose is to remove instrument defects discovered only after M124's preserved `not_ready_delivery` observation while keeping the never-yet-tested carrier proposition unchanged.

The successor hypothesis number is H70. The intended proposition repeats H69/H64 verbatim:

> A descendant carrying both pieces of acquired machinery — the attribution cascade and the
> diagnostic policy — resolves demands on carriers it did not design more often than a comparator
> that carries neither, on demands posed identically to both.

The number changes because the apparatus changes prospectively, not because the target moves. H70 is not frozen by this publication decision and no H70 evidence exists.

## Authorised prospective M125 instrument scope

The publication decision covers public implementation and offline testing of the following prospective instrument design. These rules still must be committed and mechanically verified before any M125 request:

1. **Bounded capability probes.** Non-target output dimensions are bounded. A probe output safety cap must be justified from a static bound or otherwise fixed before observation. Safety-envelope/truncation failures are instrument findings, never automatically target-feature findings.
2. **Complete named feature coverage.** Every feature class required by the candidate census must have explicit machine-checkable coverage. The inherited `items` diagnostic gap must be closed.
3. **One delivery predicate.** Request-level retry and verdict classification use the same pure definition of whether the route answered. Empty HTTP 200 and content without usable `finish_reason` are handled consistently.
4. **Correct retry metadata.** `Retry-After` is read from the transport's actual `response_headers` field; deterministic non-429 4xx request rejection is not treated as transient delivery.
5. **Prospective terminal precedence.** Completed terminal identity/feature/envelope/reasoning/calibration findings short-circuit later requests and cannot be masked by delivery failures.
6. **Pinned stress cardinalities.** The M122 non-carrier stress structure is copied prospectively with bounded inner-array cardinalities pinned by a deterministic rule independent of historical token observations. The implementation must prove the structural census is unchanged.
7. **Fresh calibration only.** M122/M123/M124 token rates, station counts and transport outcomes are historical motivation only. M125 uses a predeclared fresh calibration queue; completed points are persistent and never redrawn.
8. **One pre-calibration protocol digest.** The queue, pinning rule, retry semantics, route identity, thresholds, uncertainty formula, sizing derivation, verdict ladder and delivery accounting are bound before the first calibration request.
9. **Out-of-sample final stress.** Final size is a deterministic output of the frozen calibration protocol. A calibration-window miss or final out-of-band observation closes the instrument; no refit is permitted.
10. **Delivery ceiling preserved.** M124 closed with 4 of the globally bounded 6 delivery attempts spent. M125 does not reset that ceiling; only genuine whole-instrument delivery-only closures may consume the two remaining slots.

The detailed prospective scientific review is `docs/audits/M125_PREIMPLEMENTATION_REVIEW_2026-09-06.md`.

## Third-party, confidentiality and security review

The planned instrument stays on the already-used fixed DEVELOPMENT route and project-controlled Python apparatus. The expected implementation uses Python standard-library facilities plus existing repository development tooling. The external model/provider route remains an operational dependency, not project-owned evidence or task authorship.

No credential may be committed. No plaintext sealed bank, confidential third-party payload or security-sensitive authority is part of this review. No new filesystem, credential, deployment or repository authority is proposed for the tested descendant.

No concrete patent-first, intentional trade-secret, contractual-embargo, confidential-third-party or security-sensitive reason for private treatment was identified. The owner therefore accepted the default `PUBLIC_AGPL_COMMERCIAL_OPTION` disposition.

## Rights and licensing posture

The recorded disposition is:

`P-029 — M125/H70 prospective bounded readiness and fresh-calibration instrument — PUBLIC_AGPL_COMMERCIAL_OPTION`

Decision date: **2026-09-06**.

Project-controlled software may be published under `AGPL-3.0-only`; research prose/results remain under the documentation licence defined by `LICENSE_POLICY.md`; and separately negotiated commercial permissions remain available where the project controls the necessary rights.

## Scientific boundary

P-029 authorizes public enabling implementation and offline DEVELOPMENT hardening/tests only. It does **not**, by itself:

- authorize any M125/H70 network request before the exact request/calibration protocol is frozen, committed and mechanically verified;
- authorize a qualifying scientific generation, carrier bank, seal, reveal, scoring or result acceptance;
- reclassify or replay M124;
- reset the 4/6 cross-instrument delivery count;
- turn DEVELOPMENT calibration into H70 evidence;
- authorize reuse of M122/M123/M124 observations as M125 calibration data;
- authorize M121/H66 canonical execution, M092/H38 resumption or D063/H39 acceptance;
- satisfy H21/M075 or H31/M085 external-independence requirements;
- advance a generality gate or support an AGI claim.

A future M125 readiness result of `ready` would remain DEVELOPMENT evidence about apparatus readiness only. It would not support H70 and would not itself authorize the one-shot scientific generation.
