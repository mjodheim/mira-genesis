# M072 status

**IN PROGRESS — NO SCIENTIFIC RESULT YET.**

M072 asks whether the authority-admission and tamper-evident audit mechanisms supplied by Mira have
a bounded causal effect that survives matched ablation. It does not sample another public benchmark
and does not measure model task competence.

## Frozen ordering

1. `a844b10` committed `PROTOCOL.json` before the M072 harness existed.
2. `de93ab7` documented the same preregistered hypothesis and safety boundary.
3. `87a5a9b` introduced the pure non-executing causal harness.
4. `5844926` added the deterministic materializer.
5. `dd74e17` and `ce9a25f` added protocol and harness regressions.

No M072 external task has been selected, no M072 external task content has been inspected, no model
call belongs to an M072 scientific result and no scenario-result artifact has yet been preserved.

## Safety boundary

The admission-ablated arm and audit-ablated arm are incapable of executing actions. They exist only
to classify the same frozen scenarios. No Harbor or OS sandbox, no-network rule, repository boundary,
credential boundary, deployment boundary, permission boundary or physical boundary is weakened.

## Next irreversible step

After the implementation qualifies, materialize the single 48-scenario suite from the already
committed salt and grammar and commit that suite before evaluating or recording its result. The
scenario set may not be filtered, replaced or regenerated after an arm outcome is observed.
