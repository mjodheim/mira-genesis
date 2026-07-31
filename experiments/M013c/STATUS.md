# M013c — Status

- Protocol: **FROZEN**
- Frozen date: **2026-07-31**
- Announced evaluation commit: `40ac0f64a1fb9465e1c4cadf6c32c0cfde3b84dd`
- Engineering result: 36/36 recorded migrations exact
- Scientific status: `INCONCLUSIVE — NON REPRODUCIBLE AT ANNOUNCED COMMIT`
- Replacement experiment: **M013d**

## Cause

The announced evaluation commit predates the commits that add `experiments/M013c/protocol.yaml` and the frozen M013c protocol. The documented reproduction command checks out `40ac0f...` and then invokes a script that expects that protocol file, which is absent at that commit.

Consequently the pre-registered traceability criterion is not satisfied. The recorded summary and hashes are retained as engineering evidence, but the `VALIDATED` claim is revoked.

M013d must use a single immutable, self-contained commit containing the frozen protocol, laboratory, evaluation script and reproduction command before any reserved seed is executed.
