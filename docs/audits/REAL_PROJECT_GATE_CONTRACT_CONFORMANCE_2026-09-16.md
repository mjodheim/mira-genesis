# Real-project gate — frozen-contract conformance audit, 2026-09-16

## Disposition of this audit

**APPARATUS DEFECT FOUND AND REPAIRED PROSPECTIVELY. NO SCIENTIFIC RECORD IS AMENDED.**

This audit compares the merged generic adapter (`genesis/real_project.py`, merged 12 September 2026)
against the criterion frozen before implementation in
[`../REAL_PROJECT_TRANSFER_TARGET.md`](../REAL_PROJECT_TRANSFER_TARGET.md).

The frozen target is **not** amended, reinterpreted or relaxed by this audit. No canonical
real-project run has been accepted against the defective apparatus, so nothing is rescored: the
repairs below are prospective instrument corrections, in the sense the M124 line established, and they
apply only to runs performed after this commit. Publication remains under P-031
(`PUBLIC_AGPL_COMMERCIAL_OPTION`), which authorises public work on the generic adapter and does not
authorise any host-specific disclosure.

## What was already sound

The merged adapter already implemented the substantive mechanics the target demands: content-addressed
host binding, baseline-first evaluation, a disposable workspace per candidate, argv-only evaluator
commands, externally measured outcomes, complete candidate accounting including construction refusals,
strict-improvement selection, semantic replay of the winner, refusal of symbolic links in the tracked
snapshot, and a host source tree proved byte-identical after the run.

## Finding 1 — `passed` did not witness the required safety rejections

Criterion 6 requires that a qualifying run reject **at least one** boundary-violating candidate and
**at least one** otherwise plausible candidate that fails a real host check.

The gate enforced the boundary at construction time, so such candidates could not win. But nothing
required them to be *present*. A manifest containing only a single improving candidate produced
`"passed": true` with every recorded check satisfied. The report therefore certified a transfer whose
safety evidence had never been exercised — precisely the hand-picked-subset failure that criteria 4
and 6 exist to exclude.

Repair: the report now records `safety_invariant_evidence` and two checks,
`boundary_violating_arm_refused` and `host_check_failing_arm_rejected`. A refusal only counts toward
the first when its recorded `construction_refusal_kind` is `path_policy`, so a candidate refused for a
stale base digest cannot be mistaken for a safety rejection.

## Finding 2 — the accepted diff was constrained but never proved disjoint

Criterion 8 requires the accepted candidate's diff to be **proved** disjoint from evaluator/authority
files and from every forbidden prefix. The adapter enforced this by refusing such mutations during
construction, but the report contained no statement of the fact, so an auditor had to re-derive it from
the path policy rather than read it.

Repair: the winner's applied paths are recorded as `selected_candidate_paths` and re-checked against
the full path policy in `winner_diff_disjoint_from_authority`.

## Finding 3 — three mandatory host-contract fields were optional

The frozen host contract lists what a manifest must contain before candidate evaluation. Three items
were accepted as absent:

| Contract item | Previous behaviour | Now |
| --- | --- | --- |
| explicit forbidden path prefixes | defaulted to the empty set | at least one is required |
| an overall evaluation budget | absent from the schema entirely | `evaluation_budget_seconds` required |
| the Genesis trust/evaluation identities | defaulted to `{}` | non-empty `kind`/`value` bindings required for both |

Empty defaults are the wrong direction of failure for an authority boundary: a host that simply forgot
to declare its exclusions received an apparatus that excluded nothing, and criterion 11's
cross-repository provenance could be satisfied by two empty objects.

The declared budget must admit at least one complete evaluation pass, and a writable prefix may no
longer lie at or under a forbidden or authority prefix. An authority path *inside* a writable prefix
remains legitimate and is still honoured as a carve-out.

## Finding 4 — budget enforcement must not manufacture host-check failures

The obvious implementation of an overall budget is to shorten each command's timeout to the remaining
allowance. That was rejected. A command truncated by the budget fails for an instrument reason while
being recorded as a host-check outcome, which is the attribution defect the M124 hostile review named
as successor requirement 4.

The budget therefore refuses to start any command it cannot run to that command's full declared
timeout, and fails the whole run closed with `kind="budget"`. A run that cannot afford its complete
candidate image yields no verdict rather than a partial one, which also preserves criterion 4.

## What this audit does not establish

No canonical real-project run exists in this repository. Closing these defects does not satisfy the
DEVELOPMENT stopping criterion, does not bind a host, and does not license any claim about transfer.
It only makes `report["passed"]` mean what the frozen target says it must mean before a host is bound.

## Verification

`tests/test_real_project.py` covers each repair, including a gate run that is refused `passed` for
missing safety arms, a budget exhaustion that fails closed without mutating the host, and the recorded
refusal-kind and disjointness evidence.
