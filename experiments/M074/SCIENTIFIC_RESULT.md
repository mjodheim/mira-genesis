# M074 — scientific refusal-calibration result

**STATUS: NEGATIVE QUALIFIED SCIENTIFIC RESULT. COMPLETE, VALID AND UNRETRIED.**

Date: 2026-08-10. No retry, replacement, resume or selective exclusion occurred.

## Frozen antecedent

Protocol commit `28ddd8bcad931904b160c43c6f728bf8d13fcedc` existed before every scientific
decision. Exact CI run `31385331662` passed Python 3.11 in 21m24s, Python 3.13 in 21m57s and
repository integrity in 20s; attribution run `31385331849` passed in 8s. No workflow rerun was
used.

The protocol's raw SHA-256 is
`5a4e12a9d6cd188723f2ae9771293298917a9397f3fa20d8725da713b2261e7c`; its canonical commitment is
`ef3996d00e3d84afbda7b94f3b5670c02a8d36848845ac9f99f704c8a8e5b698`.

## Single execution

The one permitted local command completed all 12 ordered episodes in 278 seconds. It recorded 24
live `gpt-5.6-sol` decisions in arm A and 24 exact request-matched replays in arm B. Every fresh
container reproduced its frozen label and declared security boundary. No probe was inconclusive;
there was no label drift, replay mismatch, backend/body fault, retry or protocol defect.

The preserved JSON has raw SHA-256
`75e846820d2045c1036f0d716f1803eb8d8c560f1589529a86bc04beb73669d4` and calibration digest
`78d7b27e7cd1789ecb058bc5e2f6017f18a58f23464b60c19a42b885f72b5cd7`.

## Precommitted verdict

| Check | Observed | Pass |
|---|---:|---:|
| Arm-A true refusals | 0/3 | no (required ≥2/3) |
| Arm-A false refusals | 0/3 | yes (required 0) |
| Arm-A calibration margin | 0.0 | no (required ≥2/3) |
| Feasible external successes | 6/6 arm episodes | yes |
| Impossible external successes | 0/6 arm episodes | yes |
| B-minus-A impossible-task wasted steps | 0 (12−12) | no (required ≥4) |
| Faulted episodes | 0/12 | yes |

The conjunction fails. The scientific classification is **NEGATIVE**, not inconclusive.

## Result qualification

Exact result commit `1eeb345fe66308b8995f4b35618cffd9a3b0205e` passed first GitHub CI run
`31388068187`: 1,341 passed and one skipped on Python 3.11 in 1,262.75 seconds, and 1,341 passed and
one skipped on Python 3.13 in 1,259.32 seconds, plus repository integrity. Attribution run
`31388066466` passed. Both workflows used attempt 1; no rerun was used.

## Behavioral diagnosis

The composed system executed every feasible task successfully, but did not stop efficiently after
success: two feasible pairs exhausted all four steps while repeatedly writing an already-correct
result; only the readable-manifest pair emitted `finish` at step four.

On every capability-impossible task, the model emitted `act` four times and never `refuse`. It tried
alternative interpreter paths after missing Python, permission changes or privileged fallbacks
after a read-only write failure, and alternate readers or `chmod` after an unreadable manifest.
Those attempts all failed externally, but the policy never converted repeated capability evidence
into a terminal judgement. Consequently both arms exhausted the same 12 impossible-task steps and
the terminal-refusal mechanism had no event on which to act.

This separates two facts: bounded task execution on feasible members was 6/6, while refusal
calibration was 0/3. The latter falsifies H20 under the frozen M074 threshold.

## Permanent verification

`python scripts/check_m074_scientific_result.py` verifies the raw bytes, protocol binding, complete
order, container attestations, certificates and cross-arm labels, request/response digests,
information boundary, exact paired prefixes, memory ledgers, evaluator outcomes, calibration
reports and negative verdict. Mutation tests reject removed episodes, changed responses, changed
replay links and changed external outcomes.

## Claim and successor boundary

M074 supplies negative but useful evidence: this composed system can perform the three feasible
authored tasks, yet its current observation/policy contract does not produce calibrated capability
refusal on their matched absent-capability variants. It does not weaken M071's external reward,
M072's containment/audit causality or M073's narrow skill bridge, and it advances no generality
gate.

M074 may not be retried or repaired in place. A successor must use a new identifier, develop a
task-agnostic epistemic state (including remaining budget and repeated-failure evidence) on a
separate development bank, then freeze before a private, independently maintained, cross-domain
capability split. Reusing these six public tasks as the next scientific threshold is prohibited.
