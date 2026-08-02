# Mira Genesis

Mira Genesis is a bounded, auditable research program about the gap between what an
adaptive system optimises and what actually makes it better.

Its active question is:

> **When does a proxy measure stop tracking exact hidden quality, and under what
> optimisation pressure?**

The question is studied in deterministic finite-automaton worlds, where behavioural
equivalence is decidable. Ground truth can therefore be proved rather than judged by
appearance.

## The construction goal behind the testbed

The project began with a concrete long-term test: an organism learns in substrate A,
diagnoses a limitation in its own cognitive body, rewrites that body, discovers the
undeclared semantics of substrate B, migrates its competence and tools, and continues
learning there without a human redesigning its architecture.

That construction program remains the first-phase completion target. It also created
the decidable laboratory in which the measurement question became visible. Four times,
the mechanism under study held while the rule used to judge it failed:

| Experiment | What failed |
|---|---|
| M014b | A relative advantage threshold was larger than the measurement's useful dynamic range. |
| M017 | A typical 10× advantage was mistaken for a lower bound. |
| M018 | Search cost had no consequence, so there was no pressure to become efficient. |
| M019 | Selection acted before learning could repay its initial cost. |

The project now advances on two connected tracks:

1. **measurement:** identify where proxy objectives diverge from exact hidden quality;
2. **construction:** assemble proof-gated self-rewrite, isolated validation, portable
   tools and unknown-substrate migration into one replayable lineage.

## What is established

Canonical claims are deliberately narrow:

| Experiment | Status | Supported claim |
|---|---|---|
| M012b | **VALIDATED** | Autonomous morphogenesis in a bounded finite domain. |
| M013e | **VALIDATED** | Exact competence migration after experimental discovery of an opaque finite substrate. |
| M014b | **FAILED** | Transport was exact, but its pre-registered learning advantage did not generalise. |

Current development evidence:

| Experiment | Development status |
|---|---|
| M017 | All six freeze gates passed for a self-extending language; a human signature is still required before a one-shot canonical run. |
| M020 | Bounded executable self-rewrite, strict-improvement adoption, exact archive, rollback and learned rewrite tools passed CI. |
| M021 | A 24-seed paired comparison showed that selection measure strongly changes exact hidden quality; minimal criterion ranked first. It did **not** show post-selection adaptation. |
| M022 | The seed-0 repeated-motif controls exposed adaptation during the audit: 224.84× late-search advantage for the self-extending organism and exactly 1.00× for open search. Cross-seed stability remains untested. |
| M023 | Disposable subprocess evaluation and a fail-closed independent adoption gate passed CI. |
| M024 | A canonical, integrity-checked passport for active source, rollback history and learned rewrite tools passed CI. |
| M025 | One transactional lifecycle now searches, independently validates, adopts, migrates, replays and rolls back a bounded rewrite; rejection and exceptions restore both body and tool registry exactly. |
| M026 | A decidable DGM/HGM-inspired benchmark exposed an exact performance/potential mismatch, but observed clade guidance alone did not beat immediate guidance across 64 paired seeds. |
| M027 | Exhaustive hidden-blind coverage exposed productive descendants before selection, but clade guidance still tied immediate guidance in all 64 paired seeds. |
| M028 | A pre-written development comparison now isolates adaptive versus uniform allocation of finite evaluation evidence over the same breadth-seeded archive. |

These are bounded development results, not claims of AGI, consciousness, unrestricted
code execution or open-ended recursive self-improvement.

## Current work

M026 showed that a known performance/potential reversal is not enough when productive
descendants are rarely exposed. M027 then enumerated every lineage through the first
reward-bearing depth before policy selection. The clade estimate still remained
anti-aligned with exact maximum hidden utility, and HGM-inspired guidance tied
DGM-inspired guidance in all 64 seeds.

M028 implements the next separable measurement. It keeps M027's coverage and changes
only which node receives each remaining development case: uniform allocation versus
individual-performance Thompson sampling. Its 64-seed rule is written before the full
development run. Merely increasing coverage depth or relaxing M027's thresholds is
not an admissible alternative.

The next construction step is to carry M025's verified lifecycle across an initially
unknown substrate together with memory and exploration state, then measure learning on
a new post-migration task family. The full finish line is defined in
[`GENESIS_COMPLETION_CRITERIA.md`](GENESIS_COMPLETION_CRITERIA.md).

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

Replay the catalogue of measurement failures:

```bash
python scripts/reproduce_measure_failures.py
```

Run the non-canonical M022 development controls:

```bash
python scripts/run_m022_adaptation_smoke.py --seed 0
```

Run the non-canonical M026 comparison on four workers:

```bash
python scripts/run_m026_metaproductivity_comparison.py --seeds 64 --workers 4
```

Run the non-canonical M027 seeded-clade comparison:

```bash
python scripts/run_m027_seeded_clade_comparison.py --seeds 64 --workers 4
```

Run the non-canonical M028 adaptive evaluation comparison:

```bash
python scripts/run_m028_adaptive_evaluation_comparison.py --seeds 64 --workers 4
```

## Repository map

- [`PROJECT_STATE.md`](PROJECT_STATE.md) — authoritative human-readable snapshot;
- [`PROJECT_STATE.yaml`](PROJECT_STATE.yaml) — machine-readable project state;
- [`ROADMAP.md`](ROADMAP.md) — completed, active and next experimental layers;
- [`GENESIS_COMPLETION_CRITERIA.md`](GENESIS_COMPLETION_CRITERIA.md) — frozen definition
  of the first complete form;
- [`MEASURES.md`](MEASURES.md) — catalogue of proxy/ground-truth divergences;
- [`FAILURE_LOG.md`](FAILURE_LOG.md) — failures and contaminations, never deleted;
- `metamorphosis/` — experimental implementation, one module prefix per experiment;
- `experiments/<ID>/` — protocols, status and scope;
- `results/` — versioned scientific and development evidence;
- `scripts/` — runners, audits and repository guardrails;
- `tests/` — permanent development regression suite;
- `archives/` — historical code indexes, consumed workflows and archive tags.

## Scientific discipline

A canonical protocol is frozen and hashed before its result is observed. Its workflow
runs once on an immutable commit. No rerun replaces the first attempt, no threshold is
relaxed afterward, and failures remain part of the record.

Development runs may improve a rig but may not be described as canonical evidence.
English is the only language permitted on the active repository surface; historical
immutable evidence is governed by [`LANGUAGE_POLICY.md`](LANGUAGE_POLICY.md).
