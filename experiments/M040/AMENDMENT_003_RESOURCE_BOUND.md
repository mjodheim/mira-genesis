# M040 development amendment 003 — resource-bounded transfer

**Status: committed before seed 400045 is evaluated.**

Consumed seed `400044` showed that the transported prefix was highly useful but not uniquely
expressive under the original 20,000-node budget:

| Arm | Exact | Symbolic nodes |
|---|---:|---:|
| complete migrated lineage | yes | 3 |
| learning-state ablation | yes | 2,254 |
| fresh on B | yes | 7,700 |
| learned-tool ablation | yes | 7,700 |

That seed remains a negative result for the original strict criterion and cannot confirm a
new threshold.

## New development budget

For the next untouched development seed, the equal post-migration symbolic-node budget is:

```text
4,096 nodes
```

The value is explicitly calibration-derived from consumed seed 400044. It is not presented
as a prediction made before that result.

All arms receive the same 4,096-node budget, symbolic depth 3, observation set and exact
evaluator. There is no per-arm timeout, hidden fallback or deeper search.

## Verdict retained

Post-migration plasticity remains supported only if:

- the complete migrated lineage solves exactly;
- fresh-on-B, unchanged-parent, output-only and learned-tool-ablated controls have lower
  exact quality at the equal 4,096-node budget;
- the learning-state ablation receives the same full registry and may solve, but the complete
  arm must use strictly fewer symbolic nodes;
- the adopted complete-arm program begins with a transported pre-migration continuation
  prefix and adds exactly one protocol-supplied suffix;
- native re-synthesis, rollback, exhaustive audit and seed-only replay remain exact.

A control that reaches the node limit records a negative result; its best observed quality is
retained.

## Consumed identity

The first implementation of this resource-bound amendment uses development seed `400045`.
Seeds 400040–400044 remain consumed and cannot confirm it.
