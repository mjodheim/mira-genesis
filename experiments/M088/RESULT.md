# M088 result — endogenous experiment-space construction and transfer

**POSITIVE. H34 SUPPORTED. ATTEMPT 1, NO RETRY. NO GATE ADVANCES.**

- Protocol frozen at `4d8a71a`, before any qualification data existed.
- Protocol blob SHA-256 `26bb572d9a9308c39335d62833102df4ac796ec07dea00f155450522e6e23607`.
- Result digest `084111a1a10f14309dcf7ec768592325795ab9cf5de7382baf18efe097069808`.
- Salt digest `1a1c225d5ba64e2711de69770f50826d76fbbccad0e951fef24061fa3c4644a5`; qualification programs drawn only after T8.
- Model calls **0**, network calls **0**.

## The limitation, proved by exhaustion

M0's complete constructive image in `stateful_protocol` holds **2**
programs:

- `reset send_a observe`
- `reset send_b observe`

**0** of them discriminate the surviving
candidates. Exhausting all of them leaves `always_ack, count_based, memoryless, order_sensitive` alive, so the
prior constructor does not resolve the world — and cannot, whatever budget it is given.

## The meta-transformation

**10** rejected on disposable descendants; adopted:
`add_sequence_constructor`, `add_order_sensitivity`.
Constructor digest `053e2f106cf13a2e` from prior `abde6ec6902ab841`.

No new primitive was invented. The lineage composed two it was given.

## The constructed experiment

- **path_graph**: `reset follow_y follow_x observe` -> `node_trap`, eliminating `depth_blind`, `symmetric_depth`
- **durable_service**: `reset flush observe` -> `empty`, eliminating `flush_only`

Each is verified absent from the enumerated prior image.

## Arms

| Arm | Correct | Programs executed | Acquisitions | Outside prior image |
|---|---:|---:|---:|---:|
| `evolvable_experiment_constructor` | 2/2 | 20 | 4 | 2 |
| `fixed_experiment_constructor` | 0/2 | 4 | 2 | 0 |
| `constructor_acquisition_ablated` | 0/2 | 4 | 2 | 0 |
| `more_budget_same_experiment_space` | 0/2 | 40 | 2 | 0 |
| `fresh_agent` | 0/2 | 4 | 2 | 0 |
| `authored_full_experiment_space` *(ceiling)* | 2/2 | 20 | 4 | 2 |

Discordant worlds: `durable_service`, `path_graph` — **both** structurally different from
the development world, so every discordance is also a transfer.

The tenfold arm ran ten *complete independent* exhaustive searches, 40 programs against 4, gained
**no** expressiveness and closed nothing. The ceiling arm scores 2/2 and is not evidence about the
lineage: it shows the selector already works once a space exists, so what M088 adds is the
construction.

## Conditions

| Condition | Result |
|---|---|
| `P10_constructor_persisted_and_restored_byte_identically` | PASS |
| `P1_prior_constructor_cannot_resolve_exhaustively` | PASS |
| `P2_meta_transformation_adopted_after_rejections` | PASS |
| `P3_constructed_experiment_outside_prior_image` | PASS |
| `P4_observation_used_causally` | PASS |
| `P5_evolvable_correct_in_every_qualification_world` | PASS |
| `P6_capability_discordance_against_fixed` | PASS |
| `P7_more_budget_same_space_cannot_close_it` | PASS |
| `P8_ablation_loses_the_capability` | PASS |
| `P9_cross_environment_reuse_without_new_meta_transformation` | PASS |

Verdict **positive**; failed conditions: none.

## Rollback and persistence

Corruption detected **True**, byte-identical restore
**True**, constructor present in restored state
**True**. Both qualification encounters used
one serialized constructor digest.

## No leak, structurally

Every hidden program uses three actions; the adopted constructor composes at most two, so no hidden
program lies inside its constructive image. The lineage cannot build one and therefore cannot run
one. `leak_findings`: **none**.

## Amendment A1, disclosed

An adversarial test found that P4, P5 and P8 could pass vacuously on an arm with no encounters — the
M086-A failure mode of a condition that cannot fail. All three now require the evidence to exist.
The run was repeated and produced a **byte-identical result digest**, which is the evidence the
hardening changed nothing.


## Corrections after external review, disclosed

PR #136 raised four findings. All are corrected and the run was repeated.

1. **Rollback corrupted a detached copy** and restored an untouched string, so recovery was never
   exercised. That is the **M064 defect** -- a receipt comparing the saved state to itself --
   recurring. The fault is now written into the live state, detection compares it against an
   independently preserved checkpoint, restoration reads that checkpoint, and P10 additionally
   requires the fault to have changed the constructor's behaviour.
2. **The qualification pool was a module constant** in `m088_worlds`, so every possible qualifying
   program existed in the development process before `meta_search` ran. That is the **M086-A
   defect**. The pool now lives in `scripts/materialize_m088_qualification.py`, which the lineage
   never imports, executed as a **separate process** after the adopted constructor is digested; a
   test asserts the pool is unreachable from anything the lineage imports.
3. **Repeated searches cleared their logs**, so the tenfold arm reported one search's acquisitions
   and no evidence for the other nine. Each repetition now keeps its own audit trail, and the
   checker requires ten preserved logs.
4. **No publication disposition** was recorded for M088. P-004 now records
   `PUBLIC_AGPL_COMMERCIAL_OPTION`.

The verdict, the arm outcomes and every condition are unchanged; the result digest moved from
`070b1cb3...` to `084111a1...` because the preserved artifacts are now richer, not because the
science moved.

## What this does not establish

Not that the lineage invents experiments in general. The interaction vocabulary, the constructor
rule set, the meta-primitives and the three worlds are authored, and **no new primitive was
invented**. Not AGI, not open-ended evolution, not general autonomy, no generality gate, no
independent reproduction, no release or repository authority. See D058.
