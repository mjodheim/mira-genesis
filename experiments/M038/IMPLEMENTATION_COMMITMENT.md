# M038 — integrated development-cycle implementation commitment

**Status: committed before the repository development-cycle workflow is run.**

This document fixes the implementation parameters that were not already fixed in
`PROTOCOL_DRAFT.md`. It authorises a development run only. It does not freeze M038, create or
open a sealed block, support an M038 outcome, or permit post-result tuning.

## Purpose of the development run

The run exists to establish that the integrated code can execute the protocol shape end to
end:

```
fast path → exact certificate → escalation checkpoint → isolated search and evaluation
→ F1 adoption → separate failing provisional adoption → rollback to F1 → fast-path return
```

The development task and all artefacts it reveals become consumed for implementation
debugging. They may not later confirm the trigger, functional result, or efficiency claim.

## Fixed task generator

| Parameter | Committed value |
|---|---:|
| Development seed | `380038` |
| Founder generator | `random_minimal_dfa(seed + attempt × 7919, 4, 4)`, normalised |
| Founder attempts | at most `16` |
| Target generator | first canonical structural program producing a minimal target larger than the founder and an exact incapacity certificate |
| Program enumeration | `(grow, atom)`, then `(grow, atom, atom)`, then `(atom, grow, atom)` |
| Maximum programs examined per founder | `50000` |
| Observation words | every binary word of length at most `6` — `127` words |
| Task-family count | one |

The laboratory may use the hidden target to generate the task and independently judge exact
behaviour. The organism-facing proposal search receives only the founder and oracle evidence.

## Fixed diagnosis

| Parameter | Committed value |
|---|---:|
| Algorithm | `exact-max-pairwise-distinguishable` |
| Algorithm version | `m038-certificate/1` |
| Maximum certificate search nodes | `2000000` |
| Maximum prefix count | `512` |
| Budget exhaustion | `unavailable_within_committed_budget`; no escalation and no greedy fallback |

The slow path recomputes and verifies the certificate from the checkpoint body and admitted
evidence. It does not trust `escalation_reason`.

## Fixed proposal search

| Parameter | Committed value |
|---|---:|
| Vocabulary | all 36 M017 structural atoms plus all 8 explicit growth atoms |
| Cost unit | one symbol application |
| Search order | depth `1`, then `2`, then `3`; vocabulary order as returned by the committed functions |
| Maximum candidate-search nodes | `100000` |
| Evidence filter | exact agreement on all 127 admitted oracle answers |
| Independent adoption test | exact DFA equivalence by the evaluator |
| Adoption rule | first evidence-consistent candidate passing exact equivalence |

Proposal and judgement remain separate. The proposal iterator has no target argument and may
not access the hidden target through another object.

## Fixed rollback probe

After the valid candidate reaches F1, the protocol applies the single committed provisional
probe `flip(initial)`. The evaluator must reject it by exact equivalence and provide a
separating word. The journal then restores the exact F1 functional-state digest. The audit
state continues.

This probe is a validation of rollback mechanics, not a candidate chosen after observing the
development result.

## Arms

- **A:** same fast evidence and exact certificate; no escalation and no body change.
- **B:** compact trace on the fast path, checkpoint, then full causal slow-path journal.
- **C:** every B artefact plus a full immutable causal record and functional-state digest for
  each fast-path observation. C is an instrumental strict superset of B.

B and C must have identical:

- admitted observations and evidence digest;
- exact certificate;
- escalation decision;
- candidate identities and order;
- evaluator verdicts and witnesses;
- adopted F1;
- rollback decision and restored F1;
- final functional-state digest;
- compact rolling head, checkpoint digest and slow journal head;
- functional counters.

Any divergence invalidates the efficiency comparison.

## Efficiency ordering

`body_serializations` is a non-strict proof-cost dimension. Under the instrumental-superset
rule it can legitimately remain equal, so making it a strict primary would let an unrelated
tie falsify the hypothesis.

B must be no worse than C on every committed proof-cost dimension and strictly better on all
three primary dimensions:

```
persisted_event_serializations
journal_bytes_persisted
audit_deterministic_operations
```

Wall-clock time is diagnostic only.

## Tool claim

The integrated development cycle uses only `protocol_supplied` primitive tools. It constructs
no lineage-owned tool and makes **no Gate 2 claim**. Registry membership, a committed program,
or an adopted trace must not be reported as autonomous tool construction.

## Development verdicts

The workflow reports separately:

- `infrastructure_cycle_valid`;
- `functional_metamorphosis_supported`;
- `efficiency_claim_supported`;
- `combined_expected_claim_supported`.

The development workflow exits non-zero when the combined expected claim is false. That makes
CI useful for implementation debugging; it is not a canonical scientific result.

## Consumption rule

Once the workflow executes this seed, seed `380038`, its derived task, candidate order,
separating words, F1, counters and journal heads are consumed. No parameter above may be
changed and then re-evaluated on that same task to support a result. Corrections may reproduce
or diagnose the consumed run, and must be recorded as such.
