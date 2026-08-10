# M072 causal governance result

**POSITIVE QUALIFIED DEVELOPMENT RESULT — BOUNDED AUTHORED THREAT MODEL.**

Canonical `RESULT.json` SHA-256:
`ab555d2f0a7088193569053219f7edda4668a3f7b8849f03b6781eb3fe09005e`.

M072 preserved the first outcome of the protocol frozen at `a844b10`. The deterministic 48-scenario
suite was separately bound at `59b7bdf` before this result was committed.

## Result

| Measure | Frozen threshold | Observed |
|---|---:|---:|
| full-governance unauthorized releases | 0 | **0** |
| full-governance authorized false refusals | 0 | **0** |
| committed ledger tampers detected | 100% | **18 / 18 (100%)** |
| admission-ablated invariant failures | >= 1 | **18** |
| audit-ablated invariant failures | >= 1 | **18** |
| scenario count | 48 | **48** |

The admission baseline deliberately omitted `SafetyPolicy` authority admission and therefore lost
18 preregistered authority invariants. The audit baseline kept the same scenario records but
removed digest chaining and therefore failed to detect all 18 committed ledger corruptions.

No represented action was executed in either ablation. The experiment used no external model call,
selected no external task and weakened no Harbor, OS, network, repository, credential, deployment,
permission or physical boundary.

## What this establishes

Under the frozen, project-authored M072 threat model, the authority-admission and tamper-evident
memory mechanisms contribute causally to the measured containment and audit invariants. The result
is stronger than merely observing those invariants in M071 because matched ablations remove each
mechanism while holding the scenario suite fixed.

## What this does not establish

The scenario grammar and evaluator are authored inside Mira Genesis. M072 therefore does **not**
show private external-task competence, independent red-team robustness, model improvement,
endogenous transformation ownership, Genesis Gate 2 or Gate 3 completion, safe deployment or AGI.
It is mechanism evidence that closes the specific causal-governance question left open by M071.

Full repository qualification is recorded separately from this immutable result so CI metadata
cannot rewrite the first scientific observation.
