# Genesis Free Metamorphosis v7.1 — tournament-rubric disclosure erratum

**Status:** prospective control-plane repair, 20 September 2026  
**Applies before:** the next canonical Attempt 017 proposer run  
**Scientific observations consumed by this erratum:** 0  
**Campaign observations remain:** 16 / 24  
**Frozen evaluator authority:** unchanged

## Reason for the erratum

The v7 proposer prompt requires each proposer to score 4–6 inert candidate hypotheses using the exact strategy weights and deterministic rubric described in `proposal-context.json`, then to implement only the unique winner.

The distributed proposer context contains the research memory, current research-strategy weights, parent information and candidate-count bound, but does not serialize the scoring rubric itself. The laboratory retained the exact frozen scorer and recomputed every submitted tournament before evaluator entry, so a non-winning proposal was rejected without spending an external observation. The A017 pre-evaluation rejections exposed that the proposer-side contract was not information-complete.

This erratum repairs disclosure only. It does **not** change the scorer, weights, research memory, parent-selection rule, candidate schema, evaluator, capability rubric, promotion rule, neutral-frontier rule, attempt budget or any prior measurement.

## Frozen deterministic scoring rubric

For a candidate `c`, let:

- `family_state = memory.families.get(c.family)`;
- `family_unseen` be true when no family state exists;
- `new_mechanisms = c.mechanisms - memory.seen_mechanisms`;
- `new_regions = c.changed_regions - memory.seen_changed_regions`;
- `mechanism_pivot` be true when the family is known and the candidate contains at least one mechanism absent from that family's recorded mechanisms;
- `weakened` be the family's `empirically_weakened` value, false for an unseen family;
- `unresolved_hits = |c.target_axes ∩ memory.unresolved_axes|`.

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
    2  if selected_parent.kind == "neutral" and selected_parent.lineage_depth == 1
   -1  if selected_parent.kind == "neutral" and selected_parent.lineage_depth >= 2
    0  otherwise

unresolved_units = unresolved_hits
```

Using the exact integer weights in the supplied research strategy:

```text
score =
    weight.novelty           * novelty_units
  + weight.information_gain  * information_units
  + weight.causal_specificity* causal_units
  + weight.local_validation  * validation_units
  + weight.safety            * safety_units
  + weight.stepping_stone    * stepping_units
  + weight.unresolved_axis   * unresolved_units
  - weight.repeat_failure    * repeat_penalty
```

Rank by descending integer `score`. If scores tie, choose the lexicographically smallest candidate `id`.

No other proposer-authored score, subjective weight, hidden evaluator information or benchmark-case information participates in selection.

## A017 reconstruction check

The third rejected A017 transcript provides a direct prospective-repair check because it contains five exact v7 candidate objects. With the already-frozen A017 memory and generation-15 strategy weights, the disclosed rubric reproduces the laboratory ranking exactly:

1. `c05-personal-write-delivery-receipt = 240`
2. `c02-conversation-postgres-title-parity = 226`
3. `c01-conversation-memory-commit = 220`
4. `c04-personal-write-drive-upsert = 200`
5. `c03-conversation-stream-turn-commit = 180`

This equality is a disclosure check, not a new external observation.

## Continuation rule

Before another A017 proposer run, the proposer bundle must include this exact rubric in the supplied information boundary, preferably as structured context plus a human-readable mirror. The laboratory must still recompute the tournament independently before evaluator entry.

The prior A017 proposer outputs remain rejected pre-evaluator and are not repaired in place. Attempt 017 remains unspent until a fresh conforming proposer output passes the deterministic pre-evaluation gate.

## Retrospective scope

This erratum records an information-completeness defect in the proposer bundle contract. It does not rewrite previously accepted measurements. Earlier canonical v7 observations were admitted only after the external laboratory recomputed the frozen tournament and accepted the submitted winner; their measured evaluator results remain unchanged.

For reproduction, future public material should disclose this erratum alongside the v7 protocol so an independent proposer can reproduce candidate selection from the supplied aggregate state alone.
