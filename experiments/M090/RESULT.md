# M090 result — executable meta-language state

**POSITIVE. H36 SUPPORTED. ATTEMPT 3, AFTER TWO DISCLOSED CORRECTIONS. NO GATE ADVANCES.**
**H35 REMAINS NOT SUPPORTED — M089 IS NEITHER REPLAYED NOR MODIFIED.**

- Protocol frozen at `ffe5086`; blob SHA-256 `e75589ba35616eef59f8be373b9bb7efa556cce3d5f1fee02cd7754479f7c0d3`.
- Result digest `79876238c9acd9659fe456d8ca013838c47ca5823b7eca00af608d6dcef8d8bd`.
- Attempt **3**, `retry_used: true`; superseded runs preserved: `WITHDRAWN_RESULT_ATTEMPT_2.json` (positive, `27b9501a...`); `WITHDRAWN_RESULT_PRE_AMENDMENT_A1.json` (negative, `daa75713...`).
- Model calls **0**, network calls **0**.

## The question D059 asked

*If I destroy a primitive in the serialized state of the lineage, does the lineage really lose it?*

In M089 the answer was **no** for inherited operations. Here it is **yes**, for inherited and
acquired alike, through one registry.

## Migration conserved the inherited semantics

**5,328** legacy programs over four input tuples, **0**
mismatches. Expressive power is unchanged; what is new is ownership.

`L0` digest `755dd8fa7a16967a` → `L1` digest `0da139a084175704`.

## State is the sole authority

| Arm | Behaviour changed | Probes affected |
|---|---|---|
| `state_owned_meta_language` | False | — |
| `base_state_ablated` | **True** | ['inherited_composite', 'inherited_copy'] |
| `base_state_semantically_mutated` | **True** | ['inherited_composite'] |
| `extension_state_ablated` | **True** | ['acquired_combine', 'mixed_const_then_combine', 'mixed_pipeline'] |
| `legacy_host_authority` *(historical)* | **False** | — |

The last row is the M089 defect reproduced: stripping its serialized base operations changes
nothing. It is a historical comparison, never a capability of the lineage.

## Rollback, both sides, behavioural

| Side | Fault | Probes changed | Byte-identical restore | Behaviour restored |
|---|---|---|---|---|
| L0 removal | `removal` on `COPY_INPUT` | ['inherited_composite', 'inherited_copy'] | True | True |
| L0 mutation | `semantic_mutation` on `APPLY_UNARY` | ['inherited_composite'] | True | True |
| L1 removal | `removal` on `COMBINE_INPUTS` | ['acquired_combine', 'mixed_const_then_combine', 'mixed_pipeline'] | True | True |

The fault strikes the live state; restoration reads a separately preserved checkpoint.

## Fresh process

Intact state reproduces the in-process behaviour exactly (**True**),
importing neither the historical host language (**False**) nor the migration
module (**False**). With `COPY_INPUT` removed from the state, the probes
using it are **refused** — resurrected probes: `[]`.

## Conditions

| Condition | Result |
|---|---|
| `P10_fresh_process_cannot_resurrect_a_removed_primitive` | PASS |
| `P11_no_host_side_base_operation_authority` | PASS |
| `P12_legacy_architecture_shows_the_defect_this_removes` | PASS |
| `P1_inherited_semantics_conserved_by_migration` | PASS |
| `P2_every_executable_primitive_is_state_owned` | PASS |
| `P3_inherited_removal_changes_behaviour` | PASS |
| `P4_inherited_semantic_mutation_changes_behaviour` | PASS |
| `P5_acquired_removal_changes_behaviour` | PASS |
| `P6_inherited_and_acquired_share_one_execution_path` | PASS |
| `P7_rollback_of_inherited_language_is_exact_and_behavioural` | PASS |
| `P8_rollback_of_extended_language_is_exact_and_behavioural` | PASS |
| `P9_fresh_process_reproduces_the_serialized_language` | PASS |

Verdict **positive**; failed: none.

## Amendments A1 and A2 — attempt provenance
**Attempt provenance, stated plainly.** This is **attempt 3**, `retry_used: true`. Two earlier
runs of this frozen protocol are preserved in the repository: `WITHDRAWN_RESULT_ATTEMPT_2.json` (positive, `27b9501a...`); `WITHDRAWN_RESULT_PRE_AMENDMENT_A1.json` (negative, `daa75713...`). External review of PR #138
was right that re-executing a frozen protocol after inspecting a completed result is another
attempt whatever changed between them, and that recording it otherwise asserts false provenance.
The checker now derives the attempt number from the preserved artifacts rather than accepting a
declared one. A third-attempt positive is weaker evidence than a first-attempt positive, and is
recorded as such.

The two corrections were: **A1**, a scanner that matched raw source text and flagged the module
docstring describing the M089 defect, which made attempt 1 negative on P11 — an instrument defect,
confirmed by an independent AST check that no such name existed in code; and **A2**, a genuine
conservation violation found in review — `identity` had been added to the shared unary domain, so
migrated `APPLY_UNARY` accepted a call M089 rejects, while the conservation report excluded that
very operator. A2 changed the system under test. The conservation space now excludes nothing.

### A1 — it flipped the verdict, and both runs are preserved

The first run was **negative** on `P11_no_host_side_base_operation_authority`, digest
`daa75713300ed1732917ccb8bcd47ceb9e41ddf235b46b0e6f2fb46ef13272cd`, kept at
`experiments/M090/WITHDRAWN_RESULT_PRE_AMENDMENT_A1.json`.

The cause was the scanner, not the architecture. It matched raw source text and flagged
`m090_language.py` for mentioning `L0_OPERATIONS` and `_execute_base` **in the module docstring
that describes the M089 defect being removed**. An independent AST check confirmed no such name,
import or function exists in code anywhere on the execution path. The scan now reads the AST with
docstrings stripped, which is also strictly stronger — it would catch a reference assembled by
string concatenation that a substring scan misses.

**Why this is not the M089 situation.** There, the failing condition measured a **true** property of
the system, so changing the system would have been a result-saving retry and the negative was
preserved. Here it measured a **false** property because the instrument was broken. The instrument
was corrected and the system was untouched. Both digests are recorded so the claim can be checked
rather than believed.

### A2 — a real conservation violation, not an instrument fix

Review found that `identity` had been added to the shared unary operator domain, so the migrated
`APPLY_UNARY` accepted a call M089 rejects, while `conservation_report` excluded that very
operator. Conservation therefore passed without being proved over the full domain. `identity` is
removed, the conservation space now excludes nothing, and the checker fails if the migrated unary
domain differs from the inherited one or if the conservation space omits any of it.

## What this does not establish

**Not H35.** The probe extension is authored and is described as such in the protocol, this result
and the register claim. M089's qualification is neither replayed nor modified.

Not AGI, not open-ended evolution, not arbitrary self-modification, not general language invention,
not a self-hosting interpreter, no gate, no independent reproduction, no production authority.

**The interpreter substrate remains authored** — eight micro-operations, a stack machine, the
parameter kinds and the capability list. The language owns everything above them and nothing below.
That is the next ceiling. See D060.
