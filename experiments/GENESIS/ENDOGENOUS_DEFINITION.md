# The endogenous-search demonstration — definition

**DEVELOPMENT apparatus. Not a preregistration, not a protocol, not a scientific result.** It draws
no salt, records no observation, and advances no gate.

This document says what the second demonstration must show *before* reading what it does show.
`demonstrate()` in `scripts/run_genesis_endogenous_demonstration.py` is the executable form; the
record it emits is `ENDOGENOUS_RECORD.json`.

## Why there is a second one

The first demonstration ([`DEMONSTRATION_DEFINITION.md`](DEMONSTRATION_DEFINITION.md)) drives a fixed
programme through the controller and stays as the integration regression for architecture
transitions — acquisition, vocabulary extension, migration, the causal chain. Its bodies are
importable symbols the host wrote before the run, so every descendant it adopts is **selected from a
catalogue**.

The stopping criterion in [`../../docs/METAMORPHOSIS_TARGET.md`](../../docs/METAMORPHOSIS_TARGET.md)
asks for a lineage that modifies its body and *progressively its own machinery of acquisition*. A
catalogue cannot supply either. This demonstration starts without one.

## The required properties

| # | Property | Recorded as |
|---|---|---|
| 1 | It claims nothing scientific | `is_a_scientific_observation`, `advances_a_generality_gate`, `frozen` all false |
| 2 | There was **nothing to select**: the world admits no body artifacts | `world_offered_no_body_to_select` |
| 3 | The parent has a visible limitation to overcome | `parent_answered`, one of six |
| 4 | The lineage's **acquisition machinery** changes on evidence about the descendants each policy produced, compared by the immutable trust root, graded by neither policy | the `AdoptPolicy` step: `policy_updated`, `incumbent_solved < candidate_solved`, `descendants_compared_by`, `graded_by_either_policy: false` |
| 5 | The lineage's **body** is constructed, not chosen, and had to be searched for | the `SearchTransform` step: `body_was_constructed_not_selected`, `candidates_considered > 1`, with rejected candidates present |
| 6 | The adopted body answers what the parent could not | `final_body.answers` |
| 7 | Its identity binds the bytes that execute | `final_body.artifact.binds_exact_executed_bytes` |
| 8 | The machinery changed **first**, and the search that worked ran under the new rule | step order, `machinery_in_force` |
| 9 | After process death the generated body is recovered with nobody able to supply it | `survives_process_death.body_recovered_without_a_caller_supplying_it` |
| 10 | The run is deterministic | `record_digest` stable across runs |

## What must be able to fail

A demonstration whose properties cannot come out false demonstrates nothing. Each is driven to its
negative on the same code paths:

- **property 4** — a policy whose descendants are no better is refused; one whose descendants lose
  work the incumbent's kept is refused for the loss; a policy the world does not admit cannot be
  adopted; adopting the policy already in force is not an update; a trial may not change the
  machinery it is measuring (`tests/test_genesis_policy_update.py`);
- **property 5** — a search over an alphabet that cannot express the answer is recorded as having
  found nothing; the declared bound stops the search rather than success
  (`tests/test_genesis_endogenous_search.py`);
- **property 7** — the grammar refuses forward references, unknown node kinds and unknown
  operations; one changed operation changes the identity;
- **property 9** — a missing artifact makes restore fail closed; the store refuses bytes that are
  not the ones a digest names, and refuses to imply it holds an importable symbol.

## What this does not establish

- **The policies are a host-admitted pair.** The lineage chooses *whether* to change its machinery
  and the trust root decides whether the change is licensed, but the catalogue of candidate policies
  is the host's, exactly as the operation alphabet is. What is endogenous is the body and the
  decision to change the rule — not the invention of a new rule.
- **The grammar is unary chains over four arithmetic operations.** No recursion, no branching, no
  state. That such programs compose is a property of the fixture.
- **A bounded exhaustive enumeration is not search sophistication.** It is deterministic and small
  on purpose, so a reader can see how large the space is before a lineage spends its budget on it.
- **One policy change is not recursive depth.** Showing that a later policy change *depended* on an
  earlier one needs the structural-ablation argument applied to policies, and that is not built.
- **No generality claim, and no AGI claim.** See `docs/METAMORPHOSIS_TARGET.md`.

## Reproducing

```sh
python scripts/run_genesis_endogenous_demonstration.py            # print the record
python scripts/run_genesis_endogenous_demonstration.py --write    # persist it
python -m pytest tests/test_genesis_endogenous_demonstration.py -q
```
