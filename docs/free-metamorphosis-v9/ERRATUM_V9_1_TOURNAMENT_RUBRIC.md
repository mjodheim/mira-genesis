# Genesis Free Metamorphosis v9.1 — tournament-rubric disclosure erratum

**Status:** prospective control-plane repair, 22 September 2026  
**Applies before:** the first canonical V9 evaluator observation  
**Scientific V9 observations consumed before this erratum:** 0 / 24  
**Frozen evaluator authority:** unchanged  
**Base V9 control head:** `48462cbd6e326f92ce2bb6c370c251d73b8fbc1f`

## Reason for the erratum

The original V9 Attempt 001 proposer bundle required the external proposer to generate exactly six candidate hypotheses, score them with the inherited evolver-profile weights and the frozen V9 tournament rubric, and implement only the deterministic winner.

The bundle exposed the weights, aggregate research memory, primary parent, reference-parent slot, candidate schema and tie-break rule. It did **not** expose the actual frozen component formula used by `research_strategy_v9.py::score_candidate`.

The first external A001 output therefore passed byte, schema, context and information-boundary checks but was rejected by the deterministic tournament gate before evaluator entry with:

`ValueError: v9 transcript did not select deterministic tournament winner`

GitHub Actions run `35718280644` failed in the preflight step **Reproduce state, context, tournament and preflight before evaluator**. The evaluator-image restore, canonical evaluation, result publication and A002 handoff steps were all skipped.

No result branch `result/genesis-free-v9-attempt-001` and no handoff branch `handoff/genesis-free-v9-attempt-002` were produced. Consequently this rejection is not a V9 scientific observation and does not consume the 24-observation budget.

## Scope of the repair

V9.1 repairs proposer-side information completeness only. It does **not** change:

- the frozen scorer implementation;
- evolver-profile weights;
- candidate count;
- research memory;
- parent-selection rule;
- seed organism;
- evaluator;
- hidden holdout;
- capability rubric;
- promotion or archive-admission rules;
- attempt budget.

The rejected A001 proposal is not repaired in place and its post-hoc ranking is not supplied to the next proposer.

## Exact frozen V9 tournament rubric

For candidate `c`:

- `family_state = memory.families.get(c.family)`;
- `family_unseen` is true when no family state exists;
- `new_mechanisms = c.mechanisms - memory.seen_mechanisms`;
- `new_regions = c.changed_regions - memory.seen_changed_regions`;
- `mechanism_pivot` is true when the family is known and the candidate contains at least one mechanism absent from that family's recorded mechanisms;
- `unresolved_hits = |c.target_axes ∩ memory.unresolved_axes|`;
- `weakened = family_state.empirically_weakened`, false for an unseen family.

The deterministic components are:

```text
novelty_units =
    |new_mechanisms|
  + |new_regions|
  + (2 if family_unseen else 0)

information_units =
    unresolved_hits
  + (2 if weakened and mechanism_pivot
     else 1 if family_unseen
     else 0)

causal_units = min(4, |c.causal_claims|)
validation_units = min(4, |c.local_checks|)
safety_units = max(0, 3 - |c.risk_flags|)

repeat_penalty =
    family_state.zero_signal_count if the family is known else 0
  + (2 if weakened and not mechanism_pivot else 0)

stepping_units =
    0 if primary_parent.is_current_champion
    else min(4, 1 + primary_parent.lineage_depth)

unresolved_units = unresolved_hits
```

`cross_lineage_units = 1` only when a reference parent exists, its node id appears in `c.source_nodes`, and the candidate actually reuses at least one mechanism or changed region recorded in that reference parent's `research_signature`. Otherwise it is 0.

Using the exact integer weights supplied in the inherited evolver profile:

```text
score =
    weight.novelty            * novelty_units
  + weight.information_gain   * information_units
  + weight.causal_specificity * causal_units
  + weight.local_validation   * validation_units
  + weight.safety             * safety_units
  + weight.stepping_stone     * stepping_units
  + weight.unresolved_axis    * unresolved_units
  + weight.cross_lineage      * cross_lineage_units
  - weight.repeat_failure     * repeat_penalty
```

Rank by descending integer `score`. On a tie, select the lexicographically smallest candidate `id`. No other proposer-authored score or evaluator information participates in selection.

## Prospective A001 continuation

A fresh external proposer run must start from the same untouched V9 seed state and use a corrected bundle that contains this exact rubric before any candidate is generated.

The corrected handoff prepared for this continuation is content-addressed as:

- original V9 A001 bundle SHA-256: `737b8a300ace3c65e2d8e6be2bd0fef0e69d2d69bec8d5e37b031a52999bc729`;
- V9.1 corrected A001 bundle SHA-256: `d8470b7d18fef8cc6053f8d816085aef13297e98755d18c8ac9eebad44650639`;
- corrected proposer prompt SHA-256: `2db1fae19f12f94c0ef35d1d9e06bcb01ea2e58cd0eacd1efecc4498d677325c`;
- disclosed rubric SHA-256: `e1a3173dd1da304a688cebdd11e9f0c9fc073a0e0551f6ce67fd894544fa8438`.

The next proposer remains constrained to the supplied bundle only. It must independently generate its six candidates, compute the frozen tournament, and implement its deterministic winner without access to the rejected proposal, evaluator results, GitHub, prior chats or human attempt-specific guidance.

## Interpretation

This is an information-completeness defect in the proposer contract, not evidence for or against the organism mutation attempted by the rejected A001 output. The V9 campaign therefore remains at zero canonical observations until a fresh V9.1 A001 output passes the pre-evaluator gate.
