# Scientific register consistency findings — 2026-09-05

This file records navigation/register inconsistencies found during the independent validation audit.
It does **not** change any historical hypothesis, verdict, decision or frozen artifact.

## F1 — Root hypothesis register is stale at H50

`SCIENTIFIC_HYPOTHESES.md` still describes H50 as `PRE-REGISTERED; UNTESTED` and says that no M105
implementation or result exists. The preserved M105 record contradicts that navigation text:
`experiments/M105/README.md` records a unique canonical attempt with a negative verdict under D074,
and the archived project state describes H50 as unsupported after that fail-closed result. M106/H51
is the corrective replication that follows it.

**Classification:** documentation/register inconsistency. The M105 frozen result is not reopened and
H50 is not re-scored here.

**Prospective repair:** update the reader-facing root register in a separate state-sync change, using
only already-public frozen records. Do not rewrite M105, M106 or their decisions.

## F2 — Root hypothesis register does not cover the current H51+ frontier

The root hypothesis register ends at H50 while later hypotheses are recorded in milestone-local
pre-registrations, README/outcome records and project-state history. The active carrier-blind line
therefore cannot be enumerated reliably from `SCIENTIFIC_HYPOTHESES.md` alone.

The current closed outcomes explicitly include H64 (M119), H65 (M120), H67 (M122) and H68 (M123) as
untested; M121 separately preregisters H66 against G7. Earlier M113–M118 records cover H58–H63.

**Classification:** navigation debt, not scientific evidence.

**Audit consequence:** the validation matrix must be built from the milestone-local frozen records
and decision/state files, not by treating the root hypothesis document as complete.

## F3 — `PROJECT_STATE.yaml` timestamp is stale relative to content

`PROJECT_STATE.yaml` declares `updated_at: 2026-09-02` while its content includes the M122 closure on
4 September. The content may still be useful as navigation, but the timestamp is not a reliable
freshness indicator.

**Classification:** metadata inconsistency only.

## F4 — M121/H66 remains owner-gated before implementation

M121/H66 is preregistered against G7, but its harness is intentionally absent and the recorded state
says enabling implementation is blocked on an owner publication disposition. This audit does not
silently convert the owner's general authorization for reversible testing into that specific
publication/IP decision.

**Classification:** explicit owner gate. No scientific or implementation failure.

## F5 — External blockers remain real blockers

Fresh readiness checks on the audit runner correctly refuse the M075/H21 private-evidence path and
the M085/H31 external cross-domain path because their independently maintained signed envelopes and
frozen external protocols are absent. These are not connector failures and must not be replaced by
project-authored or AI-authored banks while retaining the original claims.

**Classification:** external-blocked by claim definition.
