# M089 result — endogenous meta-language extension

**POSITIVE. H35 SUPPORTED. ATTEMPT 1, NO RETRY. NO GATE ADVANCES.**

- Protocol frozen at `f8ab249`, before any qualification data existed.
- Protocol blob SHA-256 `603b762c810c71e6bd9b1c89b65fbf3332de42bc3a916b20d8e4ed9bbd33cb76`.
- Result digest `7ec0c5bbe5dbf57832ad042014d47e67ace6b515da29cf7b2342985326ddc3a2`.
- Model calls **0**, network calls **0**.

## L0 cannot express it — proof, not failed search

L0 has three operations. Its invariant: **every program leaves every slot dependent on at most one
input position**, by induction on length — `SET_CONST` clears the dependency set, `COPY_INPUT` sets
it to one index, `APPLY_UNARY` is one-argument. No operation reads two values, so the bound holds at
**any** length and **any** budget.

- signatures enumerated at length ≤ 3: **175**
- maximum sources reachable: **1**
- sources the task requires: **2**
- exhaustive L0 search found a program: **False**

## The primitive was assembled, not chosen

`PUSH_INPUT($1) PUSH_INPUT($2) BINOP(add) STORE_SLOT($0)`

- candidates constructed from the substrate: **85**
- rejected by the independent validator: **84**
- source fanout of the adopted primitive: **2** (L0's bound is 1)
- macro-reducible to L0: **no**
- capabilities: `['pure_slot_write']` — no new authority

Of 54,240 enumerable bodies, 904 are well-formed and 8 can break the invariant.

## Language versioning

`L0` digest `794ba65d3b094960` → `L1` digest `bd06dc1996fbe38c`, version 1.

## Arms

| Arm | Correct | Programs examined | Language version | Used P* |
|---|---:|---:|---:|---|
| `evolvable_meta_language` | 2/2 | 7,143 | 1 | True |
| `fixed_meta_language` | 0/2 | 2,664 | 0 | False |
| `extension_acquisition_ablated` | 0/2 | 2,664 | 0 | False |
| `extension_built_but_not_registered` | 0/2 | 2,664 | 0 | False |
| `macro_only_extension` | 0/2 | 2,664 | 0 | False |
| `more_budget_same_meta_language` | 0/2 | 266,400 | 0 | False |
| `fresh_agent` | 0/2 | 2,664 | 0 | False |
| `authored_correct_primitive` *(ceiling)* | 2/2 | 7,143 | 1 | True |

**The arm that carries the argument** is `extension_built_but_not_registered`: it builds and
validates the same primitive and never registers it. It scores 0/2, because the interpreter refuses
an operation that is not in the language. That isolates **registration** as the causal step.

**The M055 control**, `macro_only_extension`, could not acquire any primitive at all — restricted to
invariant-preserving micro-operations, no assembly resolves the task.

**The decisive control** ran 100 complete independent exhaustive searches inside Closure(L0) —
266,400 programs against
2,664 — and closed nothing.

## Conditions

| Condition | Result |
|---|---|
| `P10_language_persisted_and_restored_on_both_sides` | PASS |
| `P1_l0_provably_cannot_express_the_transformation` | PASS |
| `P2_primitive_constructed_from_substrate_after_rejections` | PASS |
| `P3_primitive_not_macro_reducible_to_l0` | PASS |
| `P4_primitive_independently_validated` | PASS |
| `P5_language_extended_and_versioned` | PASS |
| `P6_transformation_constructible_only_under_l1` | PASS |
| `P7_capability_discordance_against_fixed` | PASS |
| `P8_macro_only_and_unregistered_extensions_both_fail` | PASS |
| `P9_more_budget_same_language_cannot_close_it` | PASS |

Verdict **positive**; failed conditions: none.

## Rollback, both sides

| Side | Corruption detected | Fault changed behaviour | Byte-identical restore |
|---|---|---|---|
| before extension (L0) | True | True | True |
| after extension (L1) | True | True | True |

The fault is written into the live state and restoration reads an independently preserved
checkpoint — the M064 defect refused on both sides.

## Qualification chronology

Drawn by a **separate process** that owns the pool, after `T12_l1_serialized`. Artifact digest
`21670c64729c6de5`, bound to the extended language digest.

## What this does not establish

Not AGI, not open-ended evolution, not arbitrary self-modification, not general programming-language
invention, not recursive self-improvement, not general autonomy, no generality gate, no independent
reproduction, no production authority.

**The extension substrate remains authored.** The lineage assembled a primitive from eight
micro-operations it did not choose, over a stack machine it did not design. The ceiling arm handed
the finished primitive also scores 2/2 — which is why the contribution is the construction and the
registration, not the use. See D059.
