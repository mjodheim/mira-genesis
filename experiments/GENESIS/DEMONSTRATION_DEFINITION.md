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
| 2 | A rejected transformation does not end the run, and is kept | the `regressed` Transform step, `accepted: false` with `lineage.observations_kept: 1`, followed by further steps |
| 3 | A transformation is adopted **on measured evidence**, never on a self-report, and the candidate is never handed the answer | every Transform step carries `outcomes_are_self_reported: false`; the sandbox result's `withheld_from_the_candidate` |
| 4 | The lineage extends its own diagnostic vocabulary against a **measured** confusable pair | the `SeparateVocabulary` step, with `rests_on_a_host_supplied_oracle: false` |
| 5 | The lineage names a component class it did not have, against an exhaustion certificate produced by probes it **composed and ran** | the `AcquireComponent` step, with `probe_is_experimental_not_an_oracle: true` and `reachable_with_wider_operations: true` |
| 6 | It discovers a second substrate's semantics by probing, and migrates | the `Migrate` step, `found` / `missing` |
| 7 | The translation is **verified** on work the lineage was actually judged by: the arrival can still do what the departure could | same step, `capability_measured: true` and `capability_preserved: true` |
| 8 | It evolves again in the new form, and keeps going: **at least three accepted cycles** across the lineage, at least one of them shown to depend on what it carried across | `run.metamorphosis`, `accepted_after_migration >= 3`, `causally_established_after_migration >= 1` |
| 9 | Each later generation is shown to have **needed** the one before it, by an ablation at equal budget that the **runtime constructed** from the candidate itself | each Transform step's `causal_dependency`, with `established: true`, `arm_derived_by_the_runtime: true` and `caller_supplied_arm_used_as_evidence: false` |
| 9b | The lineage reports **how many** links were established, and does not convert that number into a verdict about recursion | `run.causal_chain`, carrying `makes_no_recursion_claim` |
| 10 | It dies and comes back with the same state digest and journal head | `survives_process_death` |
| 11 | The whole descent is one hash-chained journal across the substrate change | `journal_kinds` |
| 12 | The run is deterministic | `record_digest` stable across runs |
| 13 | The **runtime** performs the architectural transitions, not the driver | `architecture_sequenced_by: genesis.controller.run`; `tests/test_genesis_gpt56_round2_architecture.py` parses the script and requires no `genesis.state` assignment and no `genesis.journal.append` in it |


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
- **property 9** — a candidate that declares a dependency it routes no work through loses nothing
  when the runtime removes it, so the claim fails on the measurement rather than on the paperwork; a
  candidate the runtime cannot take apart establishes nothing rather than being credited; an
  acceptance naming no earlier acquisition is recorded as unestablished rather than passed; an arm
  that could not be constructed in the child aborts the cycle instead of being scored; and a run of
  acceptances with no named dependency reports a chain length of zero (`tests/test_genesis_loop.py`);
- **property 13** — the AST check fails the moment the driver assigns lineage state or appends a
  journal entry again (`tests/test_genesis_gpt56_round2_architecture.py`);
- **property 3** — a body that reports a flattering summary alongside honest per-task answers is
  scored on the answers (`LyingBody`); and, the sharper case, one body that claims every task wins
  everything when it grades itself and scores zero when the parent grades, so the flag in the record
  is a real distinction rather than a label (`CheatingBody`, `tests/test_genesis_loop.py`).

## What this does not establish

Stated here rather than in a footnote, because the gap between what the run shows and what a reader
may take it to show is the whole risk of a demonstration like this one.

- **The bodies are fixtures.** The links in property 9 exist because the fixtures route their later
  gains through the components that produced them. That shows the runtime can hold a causal claim
  *and refuse it*; it says nothing about any real mechanism having one.
- **A count of links is not a claim of recursion.** The run establishes three. An earlier version
  turned two into "a chain rather than a sequence", which set the threshold at the smallest number
  that permits the word; the record now reports the count and nothing more. How many links would be
  recursion is not a question this apparatus is entitled to settle about itself.
- **The host still draws the seed partition.** The operations a lineage composes probes from, the
  task sets, and which operations each *seed* component reaches are supplied from outside. An
  acquired component now derives its operations from its own certificate, so the partition is not
  host-drawn all the way down — but the starting one is. The claim is only that the host supplies the
  alphabet and not the sentence.
- **The mechanism is a programme, not a search.** The controller closes the authority question: the
  lineage-owned mechanism receives a frozen value and returns data, and cannot spend budget, run a
  probe or commit a state. What it returns here is a fixed sequence of intents. That the runtime
  performs the transitions is what the run shows; that a lineage discovered which ones to attempt is
  not.
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
