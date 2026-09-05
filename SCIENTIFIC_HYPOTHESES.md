# Scientific hypotheses — current register

This file is the **reader-facing current register**. It is navigation, not a substitute for frozen
protocols, immutable results, decisions, experiment-local evidence or the independent audit.

The previous long-form register is preserved byte-for-byte at
[`docs/state-history/SCIENTIFIC_HYPOTHESES_PRE_SYNC_2026-09-05.md`](docs/state-history/SCIENTIFIC_HYPOTHESES_PRE_SYNC_2026-09-05.md).
Nothing in that historical register is rewritten by this synchronization.

For H38–H68, the 2026-09-05 independent validation matrix is a navigation input:
[`docs/audits/HYPOTHESIS_VALIDATION_MATRIX_2026-09-05.json`](docs/audits/HYPOTHESIS_VALIDATION_MATRIX_2026-09-05.json).
Its original H39 status conflated a reproduced positive verdict with an owner-accepted register claim;
the matrix is preserved unchanged and that navigation error is corrected transparently by
[`docs/audits/HYPOTHESIS_VALIDATION_CORRIGENDUM_2026-09-05.json`](docs/audits/HYPOTHESIS_VALIDATION_CORRIGENDUM_2026-09-05.json).
H69 is later than that matrix and is navigated from the merged M124 frozen record and owner closure.
Replay is reproduction, never new scientific evidence; instrument closures remain untested rather
than being converted retrospectively into negative results.

## Earlier hypotheses

H1–H37 retain the statuses and detailed narratives preserved in the historical register and their
milestone-local records. H21 and H31 remain scientifically blocked on external evidence as recorded
below. This current register does not rescore any earlier result.

One historical assertion is repeated verbatim here because a permanent regression test uses it as a
cross-document integrity marker: **M086-A attempt is post-hoc disqualified**. Its detailed chronology
remains in the preserved long-form register and M086-local evidence.

## External blockers still open

| Hypothesis | Milestone | Current status | Blocker |
| --- | --- | --- | --- |
| H21 | M075 | external blocked | private human-maintained bank plus separate-maintainer reproduction absent |
| H31 | M085 | external blocked | independently maintained cross-domain bank/protocol plus independent reproduction absent |

Neither blocker can be satisfied by an internal, owner-authored or AI-authored substitute while
retaining the original claim.

## H38–H57 validated navigation

| H | Milestone | Current status | 2026-09-05 independent validation |
| --- | --- | --- | --- |
| H38 | M092 | unresolved; no verdict | canonical search remains first-run-only and was not advanced by the audit |
| H39 | M094 | **owner-pending; no register claim** | positive qualification verdict reproduced, but D063 remains unfilled and the post-verdict byte-restoration disclosure remains part of the record |
| H40 | M095 | not supported | negative direction reproduced |
| H41 | M096 | supported within frozen bounds | scientific core reproduced; historical exact mechanism binding is not fully reconstructible |
| H42 | M097 | supported within frozen bounds | positive 12/12 reproduced |
| H43 | M098 | not supported | negative reproduced; P12 replay condition remains false |
| H44 | M099 | supported within frozen bounds | positive 12/12 reproduced |
| H45 | M100 | supported within frozen bounds | positive 12/12 reproduced |
| H46 | M101 | supported within frozen bounds | scientific core P2–P14 reproduced; historical source-byte binding remains limited |
| H47 | M102 | supported within frozen bounds | scientific core P2–P14 reproduced; inherited M101 source-byte limit remains |
| H48 | M103 | not supported | negative reproduced |
| H49 | M104 | supported within frozen bounds | positive 15/15 reproduced byte-stably |
| H50 | M105 | **not supported** | preserved negative fail-closed result reproduced |
| H51 | M106 | supported within frozen bounds | P1–P15 reproduce; P16 has an absolute-path stable-projection portability defect |
| H52 | M107 | supported within frozen bounds | positive 16/16 reproduced byte-stably |
| H53 | M108 | supported within frozen bounds | positive 16/16 reproduced byte-stably |
| H54 | M109 | supported within frozen bounds | positive 18/18 reproduced byte-stably |
| H55 | M110 | supported within frozen bounds | positive 24/24 reproduced byte-stably |
| H56 | M111 | supported within frozen bounds | positive 24/24 reproduced byte-stably |
| H57 | M112 | mixed | procedure 10/10; diagnosis 24/24 positive; transfer 22/24 negative reproduced |

## H39 — preserved freeze-time chronology

H39's current navigation status is the table entry above. The following historical statements are
kept in the root register because M094's permanent design-audit regression checks that a later
verdict never erases the pre-run chronology.

**No register claim is made here.** Decision slot D063 is unfilled and remains the owner's act.

*Superseded statement, kept for chronology.* Until the canonical run this section read:
**No qualification run has been performed.** This sentence is historical freeze-time evidence, not a
current assertion that M094 lacks a result. The preserved M094 artifacts and the independent
2026-09-05 validation determine the reproduced-verdict evidence above; only the owner can fill D063.

### H50 correction

The prior root register still described H50 as pre-registered and untested. That statement had become
stale. M105 has a preserved unique canonical attempt with a negative fail-closed verdict, and the
2026-09-05 audit reproduced that negative result. H50 is therefore **not supported**, not untested.
This synchronization changes navigation only; M105 itself is untouched.

## H58–H69 — carrier and long-horizon frontier

| H | Milestone | Current status | Closure / gate |
| --- | --- | --- | --- |
| H58 | M113 | untested | instrument failure at transport; no retroactive verdict |
| H59 | M114 | untested | transport/capacity instrument abort; no retroactive verdict |
| H60 | M115 | untested | instrument aborted before carrier payload |
| H61 | M116 | untested | development route unsuitable for required structured-output classes |
| H62 | M117 | untested | development and route calibration only |
| H63 | M118 | untested | apparatus design/audit closed before scientific generation |
| H64 | M119 | untested | qualifying generation spent but bank inadequate before scientific arms |
| H65 | M120 | untested | readiness closure; candidate contract exceeded route enforcement depth |
| H66 | M121 | preregistered; canonical run owner-gated | P-025 publication disposition is recorded; prospective v2 hardening may proceed, but canonical salt/run/reveal remain unauthorized |
| H67 | M122 | untested | readiness `not_ready_stress`; contract validated, stress size missed threshold |
| H68 | M123 | untested | frozen ladder closed `not_ready_stress`; out-of-sample sizing itself landed inside the preregistered envelope |
| H69 | M124 | **untested; closed without replay** | preserved `not_ready_delivery`; no qualifying scientific invocation, bank or reveal; owner closure recorded 2026-09-05 |

H58–H65 and H67–H69 do **not** accumulate into a scientific negative. They are a sequence of
prospective instrument closures. The same carrier proposition may move only through a newly numbered,
prospectively frozen successor.

M124 did not test H69. Its narrow prospective rule classified a content-bearing HTTP 200 with no
`finish_reason` as a delivery outcome, but the decisive stress carried no completion content at all.
The archived verdict therefore remained `not_ready_delivery`, and the owner chose not to replay.
Post-observation defects are successor requirements only; they do not rescore M124.

## Current trigger

M124/H69 is now merged and closed. A later carrier successor is not yet part of this register merely
because M124 documented what it should repair. Any successor must be newly numbered, frozen before new
requests, preserve the cross-instrument delivery ceiling now at **4 of 6 spent**, and use fresh
prospective calibration if the stress schema is redesigned.

M121/H66 is a separate line. Its publication/IP disposition is no longer pending: P-025 records
`PUBLIC_AGPL_COMMERCIAL_OPTION` on 2026-09-05. That does not authorize the canonical salt or one-shot
scientific execution.

## Publication/governance reconciliation

The recent public carrier/long-horizon publication backlog is now reconciled without backdating:

| Ledger | Milestone | Recorded disposition | Decision date |
| --- | --- | --- | --- |
| P-024 | M120 / H65 | `PUBLIC_AGPL_COMMERCIAL_OPTION` | 2026-09-05 |
| P-025 | M121 / H66 | `PUBLIC_AGPL_COMMERCIAL_OPTION` | 2026-09-05 |
| P-026 | M123 / H68 | `PUBLIC_AGPL_COMMERCIAL_OPTION` | 2026-09-05 |
| P-027 | M122 / H67 | `PUBLIC_AGPL_COMMERCIAL_OPTION` | 2026-09-05 |
| P-028 | M124 / H69 | `PUBLIC_AGPL_COMMERCIAL_OPTION` | 2026-09-05 |

See [`docs/IP_REVIEWS/OWNER_RECONCILIATION_2026-09-05.md`](docs/IP_REVIEWS/OWNER_RECONCILIATION_2026-09-05.md).
These dispositions govern publication/release; they do not create scientific evidence or open any
separate canonical gate.

## Claim ceiling

Nothing in this register claims AGI, general intelligence, consciousness, unrestricted self-rewrite,
open-ended evolution, open-ended recursive self-improvement, unrestricted repository authority or
unrestricted network authority. Positive entries are bounded results under their frozen contracts.
