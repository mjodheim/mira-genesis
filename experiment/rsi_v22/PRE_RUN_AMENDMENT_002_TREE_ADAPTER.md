# RSI V22 pre-run amendment 002 — deterministic real-repair tree adapter and ingestion

Status: **prospective amendment before any V22 proposer output**.

V22 transfers the frozen V19 search policies into a real code-repair domain. Those policies consume an abstract search-tree view. The initial freeze named the policies but did not fully specify how a real repair observation is encoded into that view. This amendment removes that remaining human interpretation.

No V22 proposer has been invoked. No returned proposal has been exposed to a reserved V22 evaluator.

## Frozen adapter

Root action:

- `family = defect-root`
- `target_axes = [task_id]`
- `mechanisms = [seed-defect]`
- `changed_regions = [allowed_source_path]`

Every proposal action, regardless of transcript prose:

- `family = external-code-repair`
- `target_axes = [task_id]`
- `mechanisms = [source-patch]`
- `changed_regions = [allowed_source_path]`

Thus no human or model semantic classification of intent/rationale can influence G1/G2 selection.

All revealed nodes remain eligible parents until the frozen policy or its metadata budget stops the arm. The defect root is the initial champion at quality 0. A later node gets `ever_champion=true` only on strict best-quality improvement. `evolver_profile_generation=0` for real repair nodes. Root-branch identity and lineage depth are structural.

R1 is physically shared because both policies deterministically select the single root before observing any proposal. The one R1 request is charged once to each policy process. After divergence, observations are arm-private.

Frozen metadata controls maximum rounds, parallelism and consecutive-stall stopping. A stall is a completed represented round with no strict best-quality increase.

## Ingestion

`evaluate_proposal.py` first runs the proposer output verifier. A mechanically invalid return is not a represented search observation. It then compiles the exact supplied parent before applying the proposal; failure of that untouched-parent preflight is an evaluator-infrastructure failure and is also not represented.

A mechanically valid proposal applied in a valid evaluator environment is represented. It scores 1000 iff both the frozen public guard and retained reserved objective pass; otherwise it scores 0.

These rules do not alter the task set, reserved objectives, utility, G1/G2 policy bytes, or success criterion.
