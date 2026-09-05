# M124 retrospective publication review

**Prepared:** 5 September 2026  
**Owner decision recorded:** 5 September 2026  
**Disposition:** `PUBLIC_AGPL_COMMERCIAL_OPTION`  
**Register entry:** **P-028**  
**Status:** **RECONCILED AFTER PUBLIC DISCLOSURE.**

M124/H69 was already disclosed on the public PR before an M124-specific publication/IP disposition was recorded. This review cannot make that chronology pre-publication. Anthony Mets, sole human research director and release/acceptance decision-maker, subsequently accepted the proposed public treatment on 5 September 2026. The authoritative reconciliation is `docs/IP_REVIEWS/OWNER_RECONCILIATION_2026-09-05.md`; the ledger entry is P-028 in `IP_ASSET_REGISTER.md`.

## Asset reviewed

M124/H69 is a DEVELOPMENT-readiness successor in the existing carrier proposition line. Its prospective change was narrow: a response carrying content but lacking a usable `finish_reason` is classified as a retryable delivery failure before identity or stress interpretation. M122's carrier contract and M123's 109-station sizing rule were inherited rather than redesigned.

Readiness attempt 1 returned `not_ready_delivery`. The owner later decided to **close M124 without replay**. H69 therefore remains **UNTESTED**. No scientific freeze, qualifying scientific generation, sealed bank, reveal or scientific result exists.

The preserved attempt records 11 requests out of a 30-request operational budget and advances the cross-instrument delivery ceiling from 3/6 to 4/6. The stress carried no content, so M124's new no-`finish_reason` rule did not decide the observed run.

## Post-observation defects and boundary

Subsequent review identified instrument defects that are not retroactively repaired inside the archived M124 attempt:

- several probe schemas allow effectively unbounded output;
- `Retry-After` is not honoured because the transport records `response_headers` while retry logic reads `headers`;
- `_send` and the verdict ladder disagree about some empty-delivery cases;
- a terminal `enforcement_failed_open` state can be masked by an earlier delivery verdict;
- truncation can be attributed to a probed feature when an unrelated non-target dimension was unbounded.

The lazy carrier-contract import defect in `m124_chronology.py` was separately corrected to the actually inherited `m122_carrier_contract` and regression-tested; that path had not successfully executed and the correction did not change the archived readiness observation or its plan digest. The finality guard was also tightened prospectively to consult working-tree, committed and archived verdict sources, preventing a terminal committed verdict from being replaced locally to re-arm the gate.

The remaining defects are requirements for M125. The owner decision to stop M124 means they are not reasons to replay or rescore M124.

## Rights and publication posture

No patent-first, intentional trade-secret, contractual-embargo, confidential-third-party or security-sensitive reason for private treatment is identified. The work remains in the already-public M119 mechanism family and uses the same external DEVELOPMENT route. Credentials are environmental and are not committed.

The recorded disposition is `PUBLIC_AGPL_COMMERCIAL_OPTION`, P-028, decision date 2026-09-05. This entry truthfully records a **retrospective** owner decision and does not claim pre-publication review.

## Scientific boundary

This publication decision and closure do not:

- convert `not_ready_delivery` into a different archived verdict;
- fill H69 with a positive or negative scientific result;
- change the 32,000-token threshold, 109-station stress size or archived plan digest;
- authorize a replay of M124 — the owner explicitly declined one;
- authorize M125 or any later scientific request;
- authorize M121/H66 canonical execution or M092/H38 resumption;
- satisfy any external-maintainer or independent-reproduction requirement.

## Owner closure

M124 is closed without replay as recorded in `experiments/M124/OUTCOME.md`. The remaining delivery allowance is intentionally left unused. Known instrument defects are carried to a prospectively designed M125 rather than used to reinterpret the M124 archive.
