# Genesis MetaPolicy budget crash-consistency repair

## Scope

This is DEVELOPMENT apparatus hardening only. It addresses Hati PR #290 weakness W2: a process could die after an in-memory MetaPolicy budget spend but before the next checkpoint, allowing restore from the older allowance.

No scientific observation is created and no gate moves.

## Repair

The checkpointed MetaPolicy-evolution path now reserves the complete physical round before any candidate execution:

1. write a content-addressed round reservation into lineage state and checkpoint it;
2. charge the ordinary admitted `meta_policy_candidates` and `meta_policy_evaluations` budgets for the complete round;
3. checkpoint the charged ledger before candidate execution;
4. execute the existing MetaPolicy-evolution layer through an in-memory reserved-budget view so the lower-level `spend()` calls consume already-paid slots rather than double-charging them;
5. keep the underlying charged budget in every checkpoint written during the round.

The round identity excludes reservation size, so it remains discoverable if some measurements were committed before process death.

## Crash policy

- Crash after reservation checkpoint but before charge: safe to resume because no candidate execution has started.
- Crash after charged checkpoint with an incomplete durable measurement set: fail closed; the physical round is not redrawn and its budget remains spent.
- Charged round with a complete durable measurement set: may be finalised without physical re-execution.

This follows the same conservative non-redraw principle already used by earlier DEVELOPMENT readiness apparatus.

## Validation

Focused CI passed on run `34330007210`, including:

- normal complete round spends each reserved physical slot exactly once;
- simulated process death after reservation but before charge resumes safely;
- simulated process death after durable charge preserves the spent ledger and refuses redraw;
- #290 MetaPolicy evolution;
- #291 semantic retained-evidence revalidation;
- #289 order invariance;
- integrated meta loop, durable policy causality and cross-objective retention.

## Boundary

This does not make persisted evidence cryptographically authentic against a hostile host, and the raw lower-level `meta_policy_evolution.evolve_meta_policy` function remains a non-transactional primitive. The crash-consistent claim applies to `durable_meta_policy_evolution.evolve_meta_policy` with a checkpoint directory. The next integration step is to make that path the one used by the canonical metamorphic runtime loop.
