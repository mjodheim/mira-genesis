# M075 — public epistemic-context model-development result

**STATUS: COMPLETE, QUALIFIED PUBLIC DEVELOPMENT RECORD. NON-SCIENTIFIC AND NON-CAUSAL.**

Date: 2026-08-10. Model: `gpt-5.6-sol` through `codex-cli 0.147.0`. Docker: 29.6.2.

## Outcome

The one committed public campaign completed all twelve ordered episodes in fresh containers with
zero development defect, retry, replacement or resume. It preserved 43 complete live model
requests and structured responses.

| Condition | Feasible external success | True refusals | False refusals | Margin | Wasted impossible-task steps |
|---|---:|---:|---:|---:|---:|
| Baseline structured request | 3/3 | 0/3 | 0/3 | 0.000 | 12 |
| Epistemic-context request | 3/3 | 2/3 | 0/3 | 0.667 | 4 |

Both conditions left all three capability-impossible tasks externally unsolved. The baseline never
submitted a feasible workspace: after reaching the correct external state, it repeated actions
until the four-step budget expired. The epistemic condition submitted all three feasible
workspaces in two or three decisions. It refused the Node-absent and unreadable-token tasks on the
fourth decision after three failures.

The remaining counterexample is `write-receipt-readonly`. The epistemic request accurately
reported three consecutive non-zero commands, no successful command, a permission/immutability
barrier and `remaining_steps_including_current=1`; the model nevertheless attempted another write
and exhausted the budget. This miss is preserved and must not be hidden by reporting only the
aggregate margin.

## What the result supports

On this authored public bank, explicit self-evidence is associated with better stopping and
completion behavior than independently sampled baseline requests. That is a useful development
signal and closes the prompt-tuning phase on this bank.

It is not a causal estimate: the two conditions used independent model samples and no provider
seed or snapshot was available. It is not scientific evidence: the bank and mechanism are public,
project-authored and contaminated, and the protocol intentionally contained no post-hoc success
verdict. It does not test H21, advance a Genesis/generality gate, establish broad calibration or
support an AGI claim.

## Preserved evidence

- Protocol commit: `e1367c6`; apparatus commit: `ead1f46`.
- Protocol commitment: `ef024062d5fde3e385749153f471ef1dfc0c3bd664db859db88c78d70e94c899`.
- Protocol raw SHA-256: `5861881457b37b21a8417a579286349611ebfad64f3bc2b5fbc18e1efada177d`.
- Result raw SHA-256: `dadd202886e866e31be5cefb130e9e231f7739a0b49166f8d0c1dd2766acf949`.
- Calibration digest: `d0226c09b093f95e91c9132eed727fb3791d3bbf5cafd35040dd210714796088`.

`python scripts/check_m075_model_development_protocol.py` verifies the byte-exact protocol,
commitment, code/task/runtime bindings and order. `python
scripts/check_m075_model_development_result.py` recomputes labels, Docker boundaries, ledger
chains, request/response hashes, condition isolation, external outcomes, calibration and the 43
live-decision total.

Exact evidence commit `0c19d6b` passed the complete local Python 3.14.6 suite on its first run:
1,369 tests passed, two skipped, in 2,390.27 seconds. The three repository-integrity modes and both
M074 permanent scientific checkers also passed.

Published head `2dd6ccb` passed first CI run `31398661236` without rerun: 1,370 passed and one
skipped on Python 3.11 in 1,243.62 seconds, and the same counts on Python 3.13 in 1,265.61 seconds,
plus repository integrity. Attribution run `31398661318` passed on attempt 1.

## Decision for the next phase

The project will not tune the prompt against the single missed public task. Before any stronger
test, it needs a pre-private review that resolves the causal-control design and a sealed task-bank
intake maintained outside the policy-development path. The unchanged mechanism, model, budgets,
thresholds and attempts must then be frozen before any private task is revealed. Independent
reproduction remains mandatory.
