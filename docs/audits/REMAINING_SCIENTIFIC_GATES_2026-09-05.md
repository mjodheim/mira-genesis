# Remaining scientific gates after independent validation — 2026-09-05

This ledger is navigation only. It does not change any hypothesis verdict or authorize a one-shot
observation.

## What is no longer an open validation task

The historical M095–M112 line has been independently replayed as far as its preserved contracts
permit. M097, M099, M100, M104 and M107–M111 reproduce positive; M095, M098, M103 and M105 reproduce
negative; M112 reproduces mixed. M096/M101/M102 retain historical raw-byte binding limits while their
scientific cores reproduce, and M106 retains a cross-machine absolute-path replay defect while P1–P15
reproduce. Those limitations are now audit findings, not reasons to keep retrying the old experiments.

M113–M120 and M122–M123 that closed before a scientific observation remain `UNTESTED`. They must not
be retroactively filled. The carrier proposition moves only through a prospectively numbered
successor.

## Gate A — active carrier proposition (H64 lineage → next prospective successor)

**Current state:** M123/H68 is closed `UNTESTED`. No M124 branch or repository artifact was visible to
the audit at the last check.

**Allowed now:** inspect/audit any pushed successor, run development tests, verify chronology,
readiness, freeze integrity and fail-closed delivery classification.

**Not allowed silently:** create a scientific verdict for H58–H68 from old artifacts or spend a new
one-shot generation without the successor's own prospective rules.

**Next trigger:** M124 (or another explicitly numbered successor) appears on GitHub.

## Gate B — H66 / M121 / G7 bounded long-horizon mechanism

**Current state:** preregistered but blocked before implementation by P-025. Independent hostile review
also found repairable pre-implementation degrees of freedom in the v1 design.

A non-canonical v2 design candidate now exists in
`docs/audits/M121_V2_DESIGN_CANDIDATE_2026-09-05.md`. It fixes the main confounds by using a constant
fault budget at every horizon, freezing the schedule algorithm before the canonical salt, separating
operational and quiescent state semantics mechanically, isolating evaluator ground truth, and
specifying an explicit instrument-abort/negative/positive rule.

**Owner gate:** P-025 publication/IP disposition remains human-only. Even if the publication
classification is approved, the v1 proposal to materialize/run as written should not be treated as
approved: the audit recommends first converting the v2 candidate into a prospective amendment or
successor protocol, then freezing apparatus, then drawing a fresh canonical salt.

**Scientific ceiling:** a positive H66 result would be bounded partial evidence only; G7 remains open.

## Gate C — H38 / M092 self-generated substrate operation

**Current state:** unresolved; no verdict. M092's canonical search is explicitly `first_run_only` and
was voluntarily stopped before a terminal candidate/reproduction/qualification.

The proposition remains distinct from H52/M107: H38 requires generation of a finite new substrate
operation program, a global independent certificate without the evaluation corpus, registration, and
a downstream primitive whose blinded qualification depends on that new operation.

**Owner gate:** resuming the armed canonical search would continue the unique canonical observation.
The audit therefore does not resume it under general reversible-test authority.

**Allowed before owner decision:** static audit of the armed state, digest/chronology checks and design
review that do not advance the search cursor.

## Gate D — H21 / M075 private-bank causal claim

**Current state:** external blocked; readiness correctly fails closed.

Requires a real independent human maintainer, a sealed signed private bank, protocol freeze before
payload reveal, and ultimately a second separate bank/maintainer reproduction. An internal AI-authored
or project-authored substitute cannot satisfy the claim.

A precise handoff is prepared in `docs/audits/EXTERNAL_VALIDATION_HANDOFF_2026-09-05.md`.

## Gate E — H31 / M085 cross-domain transfer claim

**Current state:** external blocked; readiness correctly fails closed.

Requires an independently maintained sealed bank with at least three materially distinct domains,
post-freeze held-out target assignment and independent reproduction. The project cannot choose the
held-out target after seeing the bank.

The same external handoff document records the exact readiness paths and thresholds.

## Order of work

1. Audit the active carrier successor immediately when it is pushed.
2. Resolve P-025 and, if approved, harden H66 prospectively from the v2 candidate before implementation.
3. Keep H38 armed but untouched until explicit owner authority to continue the one-shot search.
4. Recruit independent human maintainer(s) for H21/H31; do not substitute internal agents.
5. Merge audit/navigation records only after ordinary repository CI is green.

This ordering maximizes new scientific information without rewriting history or spending a canonical
attempt to repair an instrument defect that could have been found in development.