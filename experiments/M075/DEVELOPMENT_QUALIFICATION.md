# M075 — epistemic-context development qualification

**STATUS: APPARATUS AND PUBLIC MODEL-DEVELOPMENT RECORD QUALIFIED. NOT A SCIENTIFIC RESULT.**

Date: 2026-08-10. Docker 29.6.2.

## What is qualified

M075 adds one task-agnostic `epistemic_state` object to the existing structured policy request. It
reports current/remaining budget, observed success/failure counts, consecutive non-zero results,
generic failure class, exact action-script digests, repetition count and prior refusal count. It
does not decide solvability or automatically refuse.

The separate public development bank contains three authored matched pairs:

- Node execution under official digest-pinned `node@sha256:c610fc…` versus Alpine without Node;
- receipt creation in writable versus non-writable workspaces;
- token transformation from readable versus mode-`0000` inputs.

This bank is openly contaminated development material. Its tasks and M074's tasks cannot become a
future M075 scientific threshold.

## Real-container control

A deterministic zero-token policy attempted the declared task solution once, finished after return
code zero and refused after a visible non-zero result. Across twelve fresh containers:

- all six live labels matched the 3 feasible/3 capability-impossible bank declaration;
- 6/6 feasible arm episodes passed external evaluation in two steps;
- 0/6 impossible arm episodes passed external evaluation;
- terminal arm A refused 3/3 impossible tasks in two steps with zero false refusal;
- nonterminal arm B recorded the same policy refusals but exhausted four steps, wasting 12 total;
- every daemon-read security boundary matched; zero development defect occurred.

This outcome is a wiring control produced by the scripted policy. It says nothing about whether
`gpt-5.6-sol` or another model will use the added state correctly.

## Preserved evidence

`DEVELOPMENT_DRYRUN.json` has raw SHA-256
`cb194a4092c3900b0befbe259d851a8b145b14c8110f8df3b462a2ee5b745699`. Its aggregate calibration
digest is `71fc5f5d…`, coincidentally equal to M074's scripted development digest because both reports
contain the same counts; task, environment, certificate, label and epistemic-state digests differ.

`python scripts/check_m075_development.py` reconstructs exact coverage, task/environment bindings,
certificates, labels, boundaries, epistemic step/budget accounting, external outcomes and reports.
Mutation tests reject missing episodes, changed budgets, hidden-label injection and cross-arm label
drift. The focused campaign passes 19 tests and all repository integrity modes.

## Public model-development result

The model-development protocol was committed before any call. Its single twelve-episode campaign
preserved 43 live `gpt-5.6-sol` decisions with zero defect or retry. The baseline produced 0/3 true
refusals, margin 0.0 and 12 wasted impossible-task steps. The epistemic condition produced 2/3 true
refusals, no false refusal, margin 2/3 and four wasted steps. Both completed 3/3 feasible tasks
externally; only the context condition submitted those workspaces instead of repeating successful
actions through the budget.

This is a useful but non-causal signal because the conditions use independent samples. The one
missed read-only-write refusal remains a declared counterexample. Complete interpretation and
digests are in `MODEL_DEVELOPMENT_RESULT.md`.

## Next boundary

Public prompt tuning now closes rather than optimizing against that miss. A pre-private review must
first resolve the causal-control procedure and sealed external bank intake. A separate commit must
then freeze the unchanged policy, model, thresholds and attempts before an unopened private,
independently maintained, materially cross-domain bank is revealed.
