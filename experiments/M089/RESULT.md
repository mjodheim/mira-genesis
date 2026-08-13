# M089 result — endogenous meta-language extension

**NEGATIVE. H35 NOT SUPPORTED. ATTEMPT 1, NO RETRY. NO GATE ADVANCES. PRESERVED, NOT REPAIRED.**

Nine of ten frozen conditions passed. **P10 failed.**

- Protocol frozen at `f8ab249`, before any qualification data existed.
- Protocol blob SHA-256 `fb2cf4042955b55b38371033571def2c94b62ec2d1a82bd12c16fd70bc42b27b`.
- Result digest `20c432a39d91e03a63dc77dd245d704758efed221e18dcf8cf0a4e7bd5134f4b`.
- Model calls **0**, network calls **0**.

## What failed

P10 requires the language to be restorable **behaviourally** on both sides of the extension.

| Side | Probe | Intact | Damaged | Behaviour changed | Restored |
|---|---|---|---|---|---|
| L1 | the registered primitive | `[5, 0, 0, 0]` | refused | **true** | true |
| L0 | `COPY_INPUT` | `[2, 0, 0, 0]` | `[2, 0, 0, 0]` | **false** | true |

On L1 the fault removes the registered primitive and the probe is refused — recovery demonstrated.
On L0 the fault removes a base operation and **nothing changes**, because `execute` dispatches base
operations from the module constant `L0_OPERATIONS` rather than from `language.base_operations`.

**This is structural, not a badly chosen fault.** For a language with an empty registry, no fault to
the serialized state can change behaviour at all. The pre-extension language has nothing executable
to roll back. **Only the registry is real state.**

## What the attempt did establish

Motivation for a successor, not qualified evidence.

| Claim | Evidence |
|---|---|
| L0 cannot express it | invariant holds at any length and any budget; max sources reachable **1**, required **2**; exhaustive L0 search found nothing |
| Constructed, not selected | **85** primitives assembled from an eight-operation stack substrate, **84** rejected by an independent validator |
| Not the M055 trap | adopted source fanout **2**; not macro-reducible to L0; `macro_only_extension` could acquire nothing at all |
| Registration is the causal step | `extension_built_but_not_registered` builds and validates the same primitive, never registers it, scores 0/2 |
| Not a compute deficit | **266,400** programs against **2,664** inside Closure(L0), closing nothing |

Adopted primitive: `PUSH_INPUT($1) PUSH_INPUT($2) BINOP(add) STORE_SLOT($0)`

## Arms

| Arm | Correct | Programs examined | Used P* |
|---|---:|---:|---|
| `evolvable_meta_language` | 2/2 | 8,445 | yes |
| `fixed_meta_language` | 0/2 | 2,664 | no |
| `extension_acquisition_ablated` | 0/2 | 2,664 | no |
| `extension_built_but_not_registered` | 0/2 | 2,664 | no |
| `macro_only_extension` | 0/2 | 2,664 | no |
| `more_budget_same_meta_language` | 0/2 | 266,400 | no |
| `fresh_agent` | 0/2 | 2,664 | no |
| `authored_correct_primitive` *(ceiling)* | 2/2 | 8,445 | yes |

## Conditions

| Condition | Result |
|---|---|
| `P1_l0_provably_cannot_express_the_transformation` | PASS |
| `P2_primitive_constructed_from_substrate_after_rejections` | PASS |
| `P3_primitive_not_macro_reducible_to_l0` | PASS |
| `P4_primitive_independently_validated` | PASS |
| `P5_language_extended_and_versioned` | PASS |
| `P6_transformation_constructible_only_under_l1` | PASS |
| `P7_capability_discordance_against_fixed` | PASS |
| `P8_macro_only_and_unregistered_extensions_both_fail` | PASS |
| `P9_more_budget_same_language_cannot_close_it` | PASS |
| `P10_language_persisted_and_restored_on_both_sides` | **FAIL** |

## How this was found, and why it is not repaired

External review of PR #137 observed that the original L0 fault changed only a version number, which
nothing executes, so `fault_actually_changed_behaviour` was true on metadata alone and P10 passed
without demonstrating recovery. The finding was correct. Correcting the fault to remove a base
operation exposed the deeper fact and **flipped the verdict from positive to negative**.

Making `execute` consult `language.base_operations` would very probably restore a positive. Doing
that after seeing the verdict is exactly the result-saving retry D053 forbids — *"replaying it after
learning why the first verdict was unsound would be a result-saving retry."* The correction belongs
to a successor with its own protocol, not to this run.

## Amendment A1, disclosed

PR #137 also observed that `max_body_length = 5` is the bound on *executing* a body while
construction enumerates to length 4, and that quoting both adjacently implied the counts covered
length 5. The construction bound is now stated explicitly and every count recomputed at it: 54,240
bodies, 904 well-formed, 8 breaking the invariant. No threshold, arm or condition changed.

The checker was also corrected to **reproduce** the rollback record rather than require it to have
succeeded, so a negative result is verifiable exactly as faithfully as a positive one.

## Next causal ceiling

**The base language is not executable state.** A successor must make the whole language — base
operations included — the object the interpreter actually consults, so that extension and rollback
are claims about one thing. Until then, "the lineage extended its language" is a claim about the
half that was state. See D059.
