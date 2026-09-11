# Canonical Genesis metamorphosis reproduction

This command reproduces the integrated bounded **DEVELOPMENT** metamorphosis milestone using the
current hardened runtime. It is a reproduction artifact, not a scientific gate runner.

## Run

From a clean checkout with the development dependencies installed:

```bash
pip install -e ".[dev]"
python scripts/run_genesis_metamorphosis_reproduction.py \
  --output-dir /tmp/genesis-metamorphosis-reproduction
```

The driver deliberately uses **three fresh Python interpreters**. The only lineage continuity across
those boundaries is the persisted Genesis checkpoint. It produces:

- `phase-1.json` — objective 1, bounded architectural `stay`/`migrate` comparison, selected form
  transition, capability-preserving migration, and persisted cursor;
- `phase-2.json` — fresh-interpreter reconstruction, objective 2, continued MetaPolicy/Policy/body
  evolution in the migrated executable form, retention, and runtime causal ablation;
- `phase-3.json` — a second fresh reconstruction proving that completed campaign state replays without
  executing another stage or spending the probe budget again;
- `report.json` — a compact self-checking semantic report with the relevant digests, budgets and
  verdicts.

A successful report has:

```json
{
  "classification": "DEVELOPMENT_REPRODUCTION",
  "passed": true,
  "fresh_interpreter_boundaries": 2
}
```

`report.json` also carries a `reproduction_digest` over the complete semantic report excluding that
digest field itself.

## What the reproduction demonstrates

The bounded campaign exercises one persistent executable lineage through:

`observe -> diagnose -> hypothesize -> construct -> isolate -> test -> compare -> adopt/reject -> persist -> continue`

The run additionally checks that the same lineage:

- retains the first objective while acquiring the second;
- changes body and acquisition machinery;
- selects a bounded executable-form transition under unique-strict-maximum comparison;
- preserves measured capability across that migration;
- reconstructs from a persistent checkpoint in a fresh interpreter;
- continues machinery/body evolution in the migrated executable form;
- establishes runtime ablation dependence of the later acquired task on the retained predecessor;
- keeps the admitted trust-root source identity and evaluation contract unchanged.

## Claim boundary

This is **DEVELOPMENT reproduction evidence**. It does not move a scientific gate and does not establish
AGI, generality, consciousness, open-ended evolution, self-generated goals, arbitrary self-programming,
or lineage-generated migration algorithms. Environmental constraints, admitted mutation languages,
search ceilings, migration adapter, evaluator and trust root remain prospectively supplied apparatus.

The historical threshold remains frozen separately in
`docs/milestones/GENESIS_DEVELOPMENT_METAMORPHOSIS_TARGET_2026-09-11.md`: post-threshold hardening and
this reproducer do not redefine when the target was first reached.
