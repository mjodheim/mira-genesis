# Mira Genesis

Mira Genesis is a bounded, auditable research program about self-rewrite,
trans-substrate continuity and the gap between what an adaptive system optimises and what
actually makes it better.

The laboratory uses finite models whose behaviour can be proved exactly. This keeps the
central question falsifiable:

> Can one lineage diagnose a limitation, construct the tools needed to change itself,
> adopt a verified improvement, migrate to an initially unknown substrate and continue
> improving there without human architectural intervention?

## Phase-one result

**The first bounded Genesis construction is complete.**

M042 produced a positive frozen continuous-lineage result in the deterministic binary-DFA
laboratory. It regenerated the immutable positive M040 lineage, passed the M041 passive
validation boundary, selected a further hidden post-migration task from a pre-verified
constructive bank and completed another exact rewrite without rerunning or retuning the
protocol.

The selected lineage reached **127/127** exact observations. Equal-budget alternatives
remained non-exact:

| Arm | Exact quality |
|---|---:|
| Complete continued lineage | **127 / 127** |
| Fresh learner on substrate B | 123 / 127 |
| Learned-tool ablation | 123 / 127 |
| Learning-state ablation | 123 / 127 |
| Unchanged parent migrated | 117 / 127 |
| Output-only body | 96 / 127 |

Passive isolated validation, exact native synthesis and exact rollback all succeeded.
The raw canonical result and the separate immutable first-result seal establish all ten
completion gates without replacing the first observation.

This is a narrow scientific result. It supports one continuous self-changing lineage
inside the frozen finite task, substrate and budget families. It does **not** establish
open-ended evolution, arbitrary program rewriting, general intelligence, consciousness or
permission to modify external systems.

The full evidence is preserved in:

- [`results/M042_CANONICAL_RESULT.md`](results/M042_CANONICAL_RESULT.md);
- [`experiments/M042/STATUS.md`](experiments/M042/STATUS.md);
- [`GENESIS_COMPLETION_CRITERIA.md`](GENESIS_COMPLETION_CRITERIA.md).

## Canonical construction lineage

| Experiment | Status | Supported result |
|---|---|---|
| M012b | **VALIDATED** | Autonomous morphogenesis in a bounded finite domain. |
| M013e | **VALIDATED** | Exact competence migration after discovery of an opaque finite substrate. |
| M014b | **FAILED** | Exact transport succeeded, but the registered generalisable learning advantage did not. |
| M038 | **POSITIVE CANONICAL** | One proof-gated F0→F1 rewrite with a two-speed causal journal and exact rollback. |
| M039 | **POSITIVE CANONICAL** | One replayable lineage completed F0→F1→F2→F3 and reused a lineage-owned tool. |
| M040 | **POSITIVE CANONICAL** | The lineage migrated to an opaque substrate and learned again after migration. |
| M041 | **NEGATIVE CANONICAL** | A sealed completion lineage failed before migration because its generated cycle-3 target was not constructively available. |
| M042 | **POSITIVE CANONICAL** | Constructive task availability repaired the M041 failure; all ten audited Genesis gates are true in one frozen lineage. |

Negative results remain part of the scientific record. M041 was not overwritten; M042 is
a separately named experiment with a separately frozen mechanism.

## Current work — Phase 2

Phase 2 tests whether the architecture is structurally transferable rather than merely
successful in one DFA representation.

M043 begins with deterministic total **Mealy machines**, where behaviour is an output
stream produced during interaction instead of a final accept/reject bit. Exact
equivalence, minimisation and finite distinguishing inputs remain decidable, but the body,
rewrite language, hidden tasks and opaque substrate must be rebuilt independently.

M043 is currently a protocol draft and rig-qualification effort. No development result or
canonical outcome exists. Its first implementation boundary is the exact formal kernel:
canonical state-renaming-invariant serialisation, product equivalence, shortest
counterexamples, minimisation and malformed-machine rejection.

See:

- [`PHASE_2_RESEARCH_AGENDA.md`](PHASE_2_RESEARCH_AGENDA.md);
- [`experiments/M043/PROTOCOL_DRAFT.md`](experiments/M043/PROTOCOL_DRAFT.md);
- [`experiments/M043/STATUS.md`](experiments/M043/STATUS.md).

## Parallel measurement track

The project also studies proxy divergence against exact hidden quality. M030 confirmed a
component-uniform signal on untouched seeds, and M031 transported it to a structurally
different finite grammar. The remaining distinct optimisation question is whether a
pre-written resource-aware adaptive allocation can beat that uniform baseline without
recreating M029's allocation failure.

The measurement and construction tracks remain separate: a stronger organism cannot
retroactively validate a proxy, and a proxy failure cannot be hidden inside a larger
construction result.

## Reproduce the repository

Mira Genesis requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\Scripts\activate        # Windows
pip install -e ".[dev]"
pytest -q
python scripts/check_repository_integrity.py
```

Canonical workflows are archived after their unique execution. Reproduction uses the
committed artifacts, deterministic replay engines and independent verifiers; it does not
replace a first canonical run.

## Repository map

- [`PROJECT_STATE.md`](PROJECT_STATE.md) — authoritative human-readable snapshot;
- [`PROJECT_STATE.yaml`](PROJECT_STATE.yaml) — machine-readable project state;
- [`ROADMAP.md`](ROADMAP.md) — completed phases and active experimental boundary;
- [`GENESIS_COMPLETION_CRITERIA.md`](GENESIS_COMPLETION_CRITERIA.md) — frozen phase-one
  completion definition;
- [`PHASE_2_RESEARCH_AGENDA.md`](PHASE_2_RESEARCH_AGENDA.md) — post-M042 research rules;
- [`MEASURES.md`](MEASURES.md) — proxy/ground-truth divergences;
- [`FAILURE_LOG.md`](FAILURE_LOG.md) — failures and contaminations, never deleted;
- `metamorphosis/` — experimental implementations;
- `experiments/<ID>/` — protocols, frozen commitments and status;
- `results/` — versioned scientific and development evidence;
- `scripts/` — runners, audits and repository guardrails;
- `tests/` — permanent regression and falsification suites;
- `archives/` — historical code indexes and consumed workflows.

## Scientific discipline

A canonical protocol is frozen and hashed before its result is observed. Its workflow
runs once on an immutable commit. No rerun replaces the first attempt, no threshold is
relaxed afterward, and failures remain visible.

Development runs may improve a rig but may not be described as canonical evidence.
English is the only language permitted on the active repository surface; historical
immutable evidence remains governed by [`LANGUAGE_POLICY.md`](LANGUAGE_POLICY.md).
