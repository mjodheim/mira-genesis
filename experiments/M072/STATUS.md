# M072 status

**POSITIVE QUALIFIED DEVELOPMENT RESULT — FULL REPOSITORY QUALIFICATION PENDING.**

M072 asks whether the authority-admission and tamper-evident audit mechanisms supplied by Mira have
a bounded causal effect that survives matched ablation. It does not sample another public benchmark
and does not measure model task competence.

## Frozen ordering

1. `a844b10` committed `PROTOCOL.json` before the M072 harness existed.
2. `de93ab7` documented the same preregistered hypothesis and safety boundary.
3. `87a5a9b` introduced the pure non-executing causal harness.
4. `5844926` added the deterministic materializer.
5. `dd74e17` and `ce9a25f` added protocol and harness regressions.
6. `1081ed1` repaired only repository integration after CI identified an orphan materializer; no M072 scientific input or outcome changed.
7. `59b7bdf` bound the exact 48-scenario suite and digest before the result was preserved.
8. `571f995` preserved the first M072 result without a retry or replacement.

No M072 external task was selected, no external task content entered the experiment and no external
model call contributes to its result.

## First result

The frozen threshold passed:

- full governance released **0** unauthorized proposals;
- full governance falsely refused **0** authorized controls;
- the tamper-evident ledger detected **18 / 18** committed corruptions;
- the admission-ablated baseline lost **18** authority invariants;
- the audit-ablated baseline lost **18** integrity invariants;
- all **48** committed scenarios were retained;
- no represented action was executed.

Canonical result SHA-256:
`ab555d2f0a7088193569053219f7edda4668a3f7b8849f03b6781eb3fe09005e`.

`scripts/check_m072_result.py` permanently recomputes the scenario suite, both arm contrasts and the
preserved result from the frozen protocol and commitment.

## Safety boundary

The admission-ablated arm and audit-ablated arm are incapable of executing actions. They exist only
to classify the same frozen scenarios. No Harbor or OS sandbox, no-network rule, repository boundary,
credential boundary, deployment boundary, permission boundary or physical boundary is weakened.

## Claim boundary

M072 supports only a bounded causal-mechanism claim under a project-authored threat model. It does
not establish private external-task robustness, model competence, endogenous transformation
ownership, Genesis Gate 2 or Gate 3, safe deployment or AGI.

The immutable scientific result is already preserved. Full Python 3.11/3.13 and repository-integrity
qualification belongs in a separate `DEVELOPMENT_QUALIFICATION.md` so later CI metadata cannot
rewrite the first observation.
