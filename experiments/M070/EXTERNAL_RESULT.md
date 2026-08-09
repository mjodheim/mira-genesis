# M070 external result

## Verdict

**FAILED FALSIFIABLE THRESHOLD — 0/2 externally accepted tasks; required at least 1/2.**

Both official Harbor trials completed without a harness exception or retry and returned reward
`0.0`. Both `nop` floor controls also returned `0.0`, so neither environment was pre-solved.

| Task | `nop` | Mira | Agent status | Steps | Network |
|---|---:|---:|---|---:|---|
| `rstan-to-pystan` | 0.0 | 0.0 | `policy_error` | 2 | `no-network` |
| `llm-inference-batching-scheduler` | 0.0 | 0.0 | `policy_error` | 1 | `no-network` |

Mira never claimed success. Harbor's hidden verifier decided both rewards after the agent phase.
Reference solutions and evaluator tests were not exposed to the model or opened during analysis.

## What failed

The independently maintained tasks falsified the frozen model transport rather than demonstrating
task competence. `CodexExecBackend` launched `subprocess.run(..., text=True)` without declaring
UTF-8. On this Windows host Python selected `cp1252`; a true non-breaking hyphen (`U+2011`) in a
later prompt caused a `UnicodeEncodeError` in the stdin writer thread. The terminated command
wrapper's `node`/`codex` descendants then retained the pipe and delayed delivery of the configured
180-second timeout.

After the timeout had already elapsed, only the verified orphan descendants for that decision were
stopped. This allowed Python to record `ModelBackendError: Codex decision exceeded its time
budget`. No decision or task was retried and M070 was not repaired after target access.

## Interpretation

M070 establishes that Mira can be wired to real isolated task containers and externally scored,
but it does **not** establish external task competence. The 0/2 result is negative evidence against
the frozen design. A UTF-8/process-tree correction must be implemented as a separately frozen
attempt with newly selected tasks; reusing these tasks as the next scientific claim would violate
the contamination boundary.
