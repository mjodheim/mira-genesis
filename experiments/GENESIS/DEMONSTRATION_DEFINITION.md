# The integrated Genesis Metamorphosis demonstration — definition

**DEVELOPMENT apparatus. Not a preregistration, not a protocol, not a scientific result.** It draws
no salt, records no observation, and advances no gate. The bodies it runs are fixtures.

This document says what the demonstration must show *before* reading what it does show, because a
demonstration defined after the fact is a description of whatever happened. `demonstrate()` in
`scripts/run_genesis_demonstration.py` is the executable form of what follows; the record it emits is
`DEMONSTRATION_RECORD.json`.

## What is being demonstrated

The stopping criterion in [`../../docs/METAMORPHOSIS_TARGET.md`](../../docs/METAMORPHOSIS_TARGET.md)
asks for **one lineage** that measures itself, diagnoses itself, transforms itself, verifies the
transformation, adopts or rejects it on evidence, keeps what it learned, progressively modifies the
machinery enabling later transformations, changes form, and continues evolving in the new form.

Every mechanism involved is already qualified in a bounded setting (see
[`../../docs/GENESIS_PRIMITIVE_AUDIT.md`](../../docs/GENESIS_PRIMITIVE_AUDIT.md)). What is new is
that they run as **one program, on one lineage, in one execution** — the audit's central finding was
that M107–M111 chain by *import*, so the ancestry existed in the source files and not in the run.

## The required properties

A run counts as a demonstration only if all of these hold in the same execution. Each names the
record field that carries it, so the claim and its evidence cannot drift apart.

| # | Property | Recorded as |
|---|---|---|
| 1 | It claims nothing scientific | `is_a_scientific_observation`, `advances_a_generality_gate`, `frozen` all false |
| 2 | A rejected transformation does not end the run, and is kept | `rejected_candidate_does_not_end_the_run` |
| 3 | A transformation is adopted **on measured evidence**, never on a self-report | `candidate_accepted_on_evidence` |
| 4 | The lineage extends its own diagnostic vocabulary against a **measured** confusable pair | `lineage_extends_its_own_diagnostic_vocabulary`, with `rests_on_a_host_supplied_oracle: false` |
| 5 | The lineage names a component class it did not have, against an exhaustion certificate produced by probes it **composed and ran** | `lineage_names_a_component_class_it_did_not_have`, with `probe_is_experimental_not_an_oracle: true` and `reachable_with_wider_operations: true` |
| 6 | It discovers a second substrate's semantics by probing, and migrates | `substrate_semantics_discovered_then_migrated` |
| 7 | The translation is **verified**: the arrival can still do what the departure could | same step, `capability_measured: true` and `capability_preserved: true` |
| 8 | It evolves again in the new form, and keeps going: **at least three accepted cycles** across the lineage | `evolved_again_in_the_new_form`, `accepted_cycles_in_the_lineage >= 3` |
| 9 | Each later generation is shown to have **needed** the one before it, by ablation at equal budget — at least two consecutive links | `causal_dependency:*`, each with `establishes_causal_dependency: true` |
| 10 | It dies and comes back with the same state digest and journal head | `survives_process_death` |
| 11 | The whole descent is one hash-chained journal across the substrate change | `journal_kinds` |
| 12 | The run is deterministic | `record_digest` stable across runs |

## What must be able to fail

A demonstration whose properties cannot come out false demonstrates nothing, which is the lesson
M121 v2 paid for. Each of these is driven to its negative in the test suite, on the same code paths:

- **property 5** — the same machinery over the same components refuses to license a new class when a
  held component resolves the demand, and refuses again when *nothing* resolves it, since exhaustion
  without reachability is a failed search rather than a finding
  (`tests/test_genesis_probe.py`);
- **property 4** — the confusable pair is refused when two demands share a measured cause, when the
  vocabulary already separates them, when either resolves through nothing, and when the budget cut
  the measurement short;
- **property 7** — a translation that solves strictly less is refused, and a migration nobody
  verified reports `capability_measured: false` rather than implying preservation
  (`tests/test_genesis_migration.py`);
- **property 9** — an "ablated" arm that never depended on the acquisition is refused even though
  the measured loss alone would accept it
  (`test_the_causal_check_refuses_an_arm_that_never_depended_on_the_acquisition`);
- **property 3** — a body that reports a flattering summary alongside honest per-task outcomes is
  scored on the outcomes (`LyingBody`, `tests/test_genesis_loop.py`).

## What this does not establish

Stated here rather than in a footnote, because the gap between what the run shows and what a reader
may take it to show is the whole risk of a demonstration like this one.

- **The bodies are fixtures.** The causal chain in property 9 exists because the fixtures route their
  later gains through the components that produced them. That shows the runtime can hold a causal
  claim *and refuse it*; it says nothing about any real mechanism having one.
- **The host still draws the partition.** The operations a lineage composes probes from, the task
  sets, and which operations each component reaches are all supplied from outside. The claim is only
  that the host supplies the alphabet and not the sentence.
- **No generality claim, and no AGI claim.** See `docs/METAMORPHOSIS_TARGET.md`; the generality
  evidence level is a separate and later thing, and this is not a step along it.
- **One author.** The runtime, its tests, this definition and the record all have the same source.
  `docs/audits/GENESIS_RUNTIME_HOSTILE_REVIEW_BRIEF.md` asks for the review that would change that.

## Reproducing

```sh
python scripts/run_genesis_demonstration.py            # print the record
python scripts/run_genesis_demonstration.py --write    # persist it
python -m pytest tests/test_genesis_demonstration.py -q
```
