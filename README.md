# Mira Genesis

Mira Genesis is a bounded, auditable research program about the gap between what an
adaptive system optimises and what actually makes it better.

Its active measurement question is:

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
   tools, unknown-substrate migration and post-migration plasticity into one replayable
   lineage.

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
| M025 | One transaction now searches, independently validates, adopts, serialises, replays and rolls back a bounded rewrite. |
| M026 | An exact performance/potential mismatch was exposed, but observed clade guidance did not beat immediate guidance across 64 paired seeds. |
| M027 | Exhaustive hidden-blind coverage exposed productive descendants, but unweighted clade guidance still tied immediate guidance in all 64 seeds. |
| M028 | Performance-adaptive evaluation remained anti-aligned with exact potential and tied uniform evaluation on median final hidden quality. |
| M029 | Hidden-disjoint component probes aligned the estimator, but adaptive concentration missed the registered policy gates. |
| M030 | Component-uniform guidance confirmed on untouched seeds 64–127: +1,000 per mille paired median hidden quality, 48 wins, 16 ties and no losses. |
| M031 | The component signal transported to a split-scaffold triad generator: +500 per mille paired median hidden quality, 43 wins, 18 ties and 3 losses. |
| M032 | An adopted M025 rewrite now compiles into a DFA, crosses an experimentally discovered opaque substrate with its passport, learned tools and declared learning state, and rolls back exactly on bridge failure. Five focused controls and 211 repository tests passed on Python 3.11 and 3.13. |

These are bounded development results, not claims of AGI, consciousness, unrestricted
code execution or open-ended recursive self-improvement.

## Current work

### Measurement

M026–M028 ruled out three tempting repairs for the finite performance/potential
mismatch: observed clade averaging alone, additional breadth alone and
individual-performance adaptive weighting. M029 introduced hidden-disjoint tests of
reusable components. Its adaptive policy missed the registered final gates, but the
pre-declared uniform component diagnostic produced 50 wins, 14 ties and no losses.

M030 promoted that diagnostic to an untouched-seed comparison and confirmed it with
48 wins, 16 ties and no losses. M031 then changed the task structure from pair
reversals and one scaffold to cyclic/permuted triads and two independent scaffolds. The
signal survived with 43 wins, 18 ties and 3 losses. The supported claim remains narrow:
component evidence predicts exact hidden potential in these two finite grammars better
than the frozen development-adaptive baseline.

The next distinct measurement question is optimisation: can a resource-aware adaptive
allocation improve on the frozen component-uniform baseline without recreating M029's
allocation failure?

### Construction

M032 closes the previous construction gap between M025 and M013e. One bounded lineage
can now:

1. search and independently adopt an executable rewrite;
2. compile the adopted policy exhaustively into a finite DFA;
3. discover the undeclared semantics of an opaque Boolean substrate by probing;
4. synthesise an equivalent native body there;
5. transport the M025 passport, learned rewrite tools, memory, uncertainty and
   exploration frontier in a validated canonical packet;
6. reject tampered packet contents and restore the exact pre-run body and registry when
   compilation or migration fails.

M032 proves transport and integrity of the declared state surface, not its functional
value. The next construction experiment must reveal a genuinely new task family only
after migration and compare the complete lineage against a fresh organism, the migrated
unchanged parent, an output-only body, a learning-state ablation and a learned-tool
ablation. That is the next test of whether transported state remains *plastic
intelligence* rather than transported output.

The full finish line is defined in
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

Run the focused non-canonical M032 bridge controls:

```bash
pytest -q tests/test_m032_trans_substrate_lifecycle.py
```

Replay the catalogue of measurement failures:

```bash
python scripts/reproduce_measure_failures.py
```

Run the non-canonical measurement experiments:

```bash
python scripts/run_m022_adaptation_smoke.py --seed 0
python scripts/run_m026_metaproductivity_comparison.py --seeds 64 --workers 4
python scripts/run_m027_seeded_clade_comparison.py --seeds 64 --workers 4
python scripts/run_m028_adaptive_evaluation_comparison.py --seeds 64 --workers 4
python scripts/run_m029_component_probe_comparison.py --seeds 64 --workers 4
python scripts/run_m030_unseen_component_confirmation.py --workers 4
python scripts/run_m031_structural_transport.py --workers 4
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
