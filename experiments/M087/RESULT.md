# M087 result — evolvable evidence acquisition and candidate selection

**POSITIVE. H33 SUPPORTED. ATTEMPT 1, NO RETRY. NO GATE ADVANCES.**

- Protocol frozen at `db609a0`, before any qualification data existed.
- Protocol blob SHA-256 `4183bae2ea17f12b90e5130ae3312bc193860efc7aec002495d80d6f31f22605`.
- Result digest `cb06bd7a0abd84aebcdccfc5bfe7278281be4891cb4a0655fde855554754d132`.
- Salt digest `2ea85b3166dd8a49b24dba28a19fc50165748a38a08859b6bf7906e7e1b41614`; qualification cases drawn only after T6.
- Model calls **0**, network calls **0**.

## The limitation, reproduced

M0 — `[SCORE_PUBLIC, ARGMAX_FIRST]`, which is M086's rule — met 2 candidates that pass
every public case: `synthesize_tool:mean:mean`, `synthesize_tool:mean:midpoint`. It adopted
`synthesize_tool:mean:midpoint`, recorded **no** ambiguity, made **0** acquisitions and scored
0/2 on the hidden cases. That is M086-C's failure reproduced exactly.

## The meta-transformation

6 rejected on disposable descendants, then one adopted and validated outside the mutable
body. Adopted policy digest `3b17374fea5f658584ebfe5e30e44fa4eb0c4eb29627f2858436896ea5e98816`.

Adopted steps: `add_ambiguity_guard`, `add_prediction_projection`, `add_equivalence_partition`, `add_experiment_enumerator`, `add_scoring_rule`, `add_acquisition_transition`, `add_survivor_filter`, `set_acquisition_budget`, `add_defer_condition`.

## Arms

| Arm | Correct | Acquisitions | Candidates evaluated | Families correct |
|---|---:|---:|---:|---|
| `evolvable_selection_evidence` | 3/3 | 3 | 11 | interpretation_routing, planning_structure, tool_semantics |
| `fixed_selection_evidence` | 1/3 | 0 | 11 | interpretation_routing |
| `selection_acquisition_ablated` | 0/3 | 0 | 11 | — |
| `more_budget_same_evidence` | 1/3 | 0 | 110 | interpretation_routing |
| `fresh_agent` | 1/3 | 0 | 11 | interpretation_routing |

**Correctness discordance:** evolvable-only correct on `planning_structure`, `tool_semantics`; fixed-only correct on
nothing.

**Cost, reported separately and claimed for nothing:** the evolvable arm evaluated
11 candidates and made
3 acquisitions; `more_budget_same_evidence` evaluated
110 and made none. Ten times the computation over the same
evidence closed neither discordant situation, which is the falsifier the protocol named first.

## Conditions

| Condition | Result |
|---|---|
| `P10_chronology_holds` | PASS |
| `P1_ambiguity_represented` | PASS |
| `P2_meta_transformation_adopted_after_rejections` | PASS |
| `P3_evolvable_correct_on_every_situation` | PASS |
| `P4_capability_discordance_against_fixed` | PASS |
| `P5_more_budget_same_evidence_cannot_close_it` | PASS |
| `P6_acquisition_ablation_loses_the_capability` | PASS |
| `P7_cross_family_reuse` | PASS |
| `P8_policy_persisted_and_restored_byte_identically` | PASS |
| `P9_no_evidence_leak` | PASS |

Verdict **positive**; failed conditions: none.

## Rollback

Corruption detected **True**, byte-identical restore
**True**, digest match **True**.
Checkpoint `3b17374fea5f6585`, corrupted `617a53a943ece5fe`.

## Evidence boundary

`leak_findings`: **none**. Every acquisition stayed inside the frozen per-family
experiment space, which is disjoint from the hidden domain by construction, and no arm other than
the evolvable one acquired anything.

## Amendment A1, disclosed

After the qualifying run an adversarial test found that `LOOP_ACQUISITION` re-enters while budget
remains even when every experiment has been consumed, and never terminates. The interpreter is a
frozen component, so the fix is recorded as an amendment and the run was repeated. The qualifying
run never took that path — eight experiments against a budget of four, so it always terminated on
budget — and the re-run produced a **byte-identical** result digest. The amendment is disclosed
rather than absorbed, and the identity of the digests is the evidence that it changed nothing.

## What this does not establish

Not AGI, not open-ended evolution, not general autonomy, no generality gate, no independent
reproduction, no release or repository authority. The meta-primitives, the instruction set and the
three families are authored. `interpretation_routing` is a preregistered no-harm situation in which
the frozen tie-break lands correctly by luck, kept rather than tuned away. See D057.
