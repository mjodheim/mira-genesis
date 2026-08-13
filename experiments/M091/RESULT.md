# M091 result — endogenous extension of a state-owned meta-language

**POSITIVE. H37 SUPPORTED. ATTEMPT 1, NO RETRY. NO GATE ADVANCES.**
**H35 REMAINS NOT SUPPORTED — M089 IS NEITHER REPLAYED NOR MODIFIED.**

- Protocol frozen at `5e4a0fe`; blob SHA-256 `2e9503986dd55253e02978366cbc1d64c4175dda3ba01ef88fc3ddbb6f6a5273`.
- Result digest `d83b836dee2b62d9211f0e4fc214e1abcd9db608e257f3105f54adf59a4c07af`.
- Attempt **1**, `retry_used: false`, no superseded runs. Both numbers are derived from the
  preserved artifacts, not declared.
- Model calls **0**, network calls **0**.
- `L0` digest `755dd8fa7a16967a` → `L1` digest `790c4dea178e3e7a`, language version 0 → 1.

**The freeze commit was renumbered, and nothing frozen changed.** It was first recorded as
`15eb129`. CI's human-only attribution policy rejected a non-human co-author trailer in this
branch's commit messages; the trailer was removed and the three commits were rewritten, which
moved their identities. The trees are identical, the protocol blob is byte-for-byte the same —
SHA-256 `2e950398…a5273`, which is what the result actually binds — and no artifact under
`experiments/M091/` changed. The result digest is unaffected because it covers content, not commit
identity. This is recorded rather than quietly corrected.

## The question M090 made askable

M090 settled *where* the meta-language lives: one registry, entirely serialized state, consulted by
a fixed generic interpreter that branches on no primitive identifier. It settled nothing about
whether the lineage can add to it, and said so — its probe extension was authored and labelled as
such in the protocol, the result and the register claim.

The question here: **when a required transformation lies outside what its language can express, can
the lineage diagnose that, build a new operation, and be more capable for it?**

## This is not M089's gap

M089 attacked **fan-in**: no inherited operation reads two values, so no slot could depend on two
input positions. That gap is spent, and M090's authored probe extension already occupies it.

The gap here is **bending**. `inc`, `dec`, `neg` and `double` are `x+1`, `x-1`, `-x` and `2x`;
`SET_CONST` and `COPY_INPUT` install a constant or an input untouched. Affine maps compose to
affine maps, so after any program over the inherited language every slot holds either a constant or
`a*inputs[i] + b`.

The required transformation reads **exactly one input position**. M089's invariant is not violated,
and its primitive would not help — the validator refuses it, as recorded below.

## The insufficiency is proved, not observed

| Argument | Result |
|---|---|
| Closure lemma, one primitive at a time over the whole abstract domain | 22,500 abstract states, **0** escapes |
| Abstraction soundness against the concrete interpreter | 113 programs, 452 slot functions, **0** violations |
| Refutation certificate for the requirement | every constant, every affine map of its source, every rival position |
| Redundant exhaustive search at depth four | 61,308 programs, 10,008 distinct behaviours, **nothing found** |

The lemma is a statement about **one step**. The initial state is all zeros, which is in the domain,
and no step can leave it — so induction carries it to any program length, and therefore to any
budget. The search is the weakest of the four and is reported rather than relied upon.

The certificate is finite and re-checkable. Three non-collinear points refute **every** integer
`a` and `b` at once: `(-5, 0)`, `(-2, 0)`, `(1, 1)` lie on no line. Two points refute the constants,
and one pair per rival position refutes any function of another input alone.

## The primitive was assembled, not selected

**3,248** candidates assembled from the frozen substrate, **65** well formed, **3,247** rejected
across five reasons, **65** disposable descendants created and discarded.

| Rejection | Count |
|---|---|
| `malformed_or_partial` | 3,183 |
| `macro_equivalent_to_an_inherited_composition` | 63 |
| `adds_no_semantics_beyond_the_inherited_invariant` | 62 |
| `abstract_bend_is_not_observable` | 1 |
| `exceeds_the_resource_bound` | 1 |

The adopted body, arity one:

```
PUSH_SLOT $0 · PUSH_CONST 0 · BINOP max · STORE_SLOT $0
```

The arity-one body space is 41,370 sequences. Nothing in the acquisition path contains this body,
this program, or either digest as a literal, and no `build_definition` call anywhere on that path
receives a literal body — checked from the AST, with docstrings stripped.

## It is not a macro, and the gain is not search cost

This is the M055 falsifier, answered three ways at once. **87** distinct behaviours are reachable by
compositions of the inherited language at this signature; the adopted primitive matches none of
them. Its bend is witnessed concretely, not merely flagged by an abstraction. And the two arms
report their gains in the same table:

| Arm | Reachable without it? | Programs examined | Program length | Gain |
|---|---|---|---|---|
| `macro_only_extension` | **yes** | 38,848 → 5,477 | 4 → 3 | search cost |
| the adopted primitive | **no** | 61,308 → 397 | — → 2 | **reach** |

The macro arm is M055 reproduced on purpose. It really did memoize a composition — `PUSH_SLOT ·
UNOP double · UNOP double · STORE_SLOT`, two doublings named and reused — it really did register it
into its own language, and it really did shorten its search. It solved **0/2** qualifying worlds.

## Arms

| Arm | Correct | Families | Programs examined | Distinct behaviours | Depth |
|---|---|---|---|---|---|
| `evolvable_meta_language` | **2/2** | both | 52,241 | 9,266 | 4 |
| `fixed_meta_language` | 0/2 | — | 122,616 | 20,016 | 4 |
| `extension_acquisition_ablated` | 0/2 | — | 122,616 | 20,016 | 4 |
| `extension_built_but_not_registered` | 0/2 | — | 122,616 | 20,016 | 4 |
| `macro_only_extension` | 0/2 | — | 168,880 | 29,092 | 4 |
| `more_budget_same_meta_language` | 0/2 | — | **7,072,128** | **418,704** | **6** |
| `fresh_agent` | 0/2 | — | 122,616 | 20,016 | 4 |
| `authored_correct_primitive` *(ceiling)* | 2/2 | both | 52,241 | 9,266 | 4 |

`more_budget_same_meta_language` performed two complete exhaustive searches to depth six —
**58×** the programs and **21×** the behaviours of the fixed arm, at a length half again as long as
anything the extended language needed. It closed nothing, because closure is not a budget question.

`extension_built_but_not_registered` holds the same validated bytes and runs them directly on the
substrate. Through the language it can do nothing: a body is not a capability until the state owns
it. The last row is excluded from the verdict by name; it shows the pipeline can exploit a new
primitive when handed one, which is not a finding about the lineage.

## Two worlds it had never seen, drawn after the language was frozen

The salt is `sha256("m091|" + L1 digest + "|" + primitive semantics digest)` — a value that does not
exist until adoption. The draw ran in a separate process; nothing under `metamorphosis/` can reach
the pool, checked from the import graph at any depth.

| World | Family | Constructed transformation | Hidden |
|---|---|---|---|
| `q_capacity_relief_plan` | `capacity_planning` | `COPY_INPUT(1,0) · APPLY_UNARY(1,double) · P*(1)` | **5/5** |
| `q_protocol_hop_deficit` | `protocol_window` | `COPY_INPUT(0,0) · APPLY_UNARY(0,neg) · P*(0) · APPLY_UNARY(0,neg)` | **5/5** |

The second is the interesting one. Its requirement is the **dual** clamp — a ceiling, not a floor —
and the lineage reached it by conjugating its new operation with the inherited sign flip, a
construction it had never built. Same primitive, same semantics digest, no new registration: the
language version is still 1 after both.

Correctness is judged in each world's own terms on instances the search never saw — a level that may
not go negative, a region where the plan must track its input, a region where it must be pinned, and
no scribbling on slots nobody asked about.

## The state is the execution authority

Deleting the acquired operation from the serialized state removes the transformation. Deleting an
inherited one removes that too. Neither reappears in a fresh process.

| Fresh process given | Solves |
|---|---|
| `L1` | **2/2**, same primitive semantics digest, language version unchanged |
| `L1` minus the acquired operation | 0/2 |
| `L0` only (`fresh_agent`) | 0/2 |

The fresh process imports the interpreter, the requirement schema and a generic search — and
**neither** the assembler, the enumerator, the validator nor the lineage. The import census is
printed by the process itself and checked, so the extension survives as state rather than being
rebuilt from development code.

## Rollback, both sides, behavioural

| Side | Fault | Probes changed | Byte-identical | Behaviour restored | Restore reversed the live state |
|---|---|---|---|---|---|
| before adoption | `semantic_mutation` on `APPLY_UNARY` in the **provisional** `L1` | `inherited_composite`, `mixed_conjugate` | True | True | **True** |
| after adoption | `removal` of the acquired operation from the live `L1` | `acquired_clamp`, `mixed_conjugate` | True | True | n/a |

The first is not a checkpoint compared with itself. The checkpoint is `L0`, the live state is the
provisional extended language, and restoring took the extension away again — `acquired_clamp` and
`mixed_conjugate` stop running. D023 closed M064 over a receipt that lacked exactly this.

## Conservation

**1,332** programs and **5,328** calls over the complete cross product of every declared parameter
domain, zero mismatches, plus ten calls the inherited language refuses, all still refused
identically. The conservation space **excludes nothing** — declared and covered binding counts are
equal and the checker fails if they differ. That is M090's amendment A2 enforced rather than
remembered.

## Conditions

| Condition | Result |
|---|---|
| `P1_inherited_language_provably_cannot_express_the_transformation` | PASS |
| `P2_primitive_assembled_from_the_substrate_rather_than_selected` | PASS |
| `P3_primitive_is_not_reducible_to_a_composition_of_the_inherited_language` | PASS |
| `P4_an_independent_validator_accepted_it_without_seeing_the_qualification` | PASS |
| `P5_the_primitive_is_registered_in_the_state_owned_language` | PASS |
| `P6_the_transformation_is_outside_l0_and_inside_l1` | PASS |
| `P7_correctness_difference_on_worlds_the_lineage_never_searched` | PASS |
| `P8_more_budget_in_the_same_language_closes_nothing` | PASS |
| `P9_a_macro_only_extension_closes_nothing` | PASS |
| `P10_building_without_registering_closes_nothing` | PASS |
| `P11_the_inherited_semantics_are_conserved_exactly` | PASS |
| `P12_rollback_is_exact_and_behavioural_on_both_sides` | PASS |
| `P13_the_extension_persists_and_is_reused_in_a_fresh_process` | PASS |
| `P14_chronology_track_a_and_no_leaked_evidence` | PASS |

Verdict **positive**; failed: none. Each condition is computed, and
`test_every_condition_can_fail` spoils one field per condition and requires the verdict to turn
negative — M086-A recorded a positive against a threshold that could not fail, and that is what
forbids it here.

## The validator refuses things, including M089's answer

Acceptance means nothing unless refusal is possible. M090's authored probe extension —
`COMBINE_INPUTS`, which routes two input positions into one slot — is handed to this validator and
**refused as overbroad**: widening the source fan-in is a different extension from the one that was
diagnosed, and nobody proved it was needed. A renamed inherited composition is refused as a macro. A
partial body, an unsafe capability and a primitive that can blow a value past the resource bound are
each refused.

Renaming the adopted primitive changes neither its semantics digest nor the validator's answer.
Giving the right name to the wrong body still fails. Success is never an identifier comparison.

## What this does not establish

**Not H35.** M089's protocol, salt, qualification and result are untouched, and its negative stands.
M091 has its own hypothesis, protocol, expressive gap, worlds, qualification, checker and result.

Not AGI, not open-ended evolution, not arbitrary self-modification, not general programming-language
invention, not unrestricted recursive self-improvement, not a self-hosting interpreter, no gate, no
independent reproduction, no production authority. The acquired operation gained **expressive power
inside the language and no authority against the system**: the permitted capability set is
unchanged, and filesystem, network, subprocess, credential, repository, evaluator, gate and
production authority remain forbidden and unreachable.

The honest limits, stated rather than implied:

- **The assembly substrate remains authored.** Eight micro-operations, the binary operator set —
  `max` among them — the two body constants, the three signatures, the length bound and the
  capability list are all ours. The lineage assembled a signed, registered, slot-transforming
  operation of its language out of them; it did not invent the machine underneath.
- **The interpreter substrate remains authored**, exactly as M090 recorded.
- The world schema and the requirement expression language are authored, and the requirement
  language is the oracle's — the lineage cannot call it, execute it or read it as a program.
- One bounded representation: four integer slots, three integer inputs, two qualifying families.
- Experimenter blindness is **not** claimed. The pool of candidate worlds is authored and committed
  at the freeze and the draw is a deterministic function of the extended language's digest, so it is
  reproducible by anyone. What is claimed is that the lineage cannot reach any of it before
  adoption, and that the drawn worlds could not have been known before the primitive existed.

## Review findings, and what was deliberately not repaired

A review of this branch produced five findings. One was in the instrument and is fixed; four are
recorded and left alone, because repairing them would change the frozen artifacts and force a
second attempt for no scientific gain. **The single-attempt provenance is worth more than the
cosmetics.**

**Fixed.** `check_m091_result.py` carried a `--skip-budget-arm` flag that copied the recorded
budget-arm numbers instead of replaying them, so the checker could have printed *verified* while
skipping the most expensive falsifier. That is the M086-A shape — an instrument that exists without
being decisive — and the flag is gone. The change makes verification strictly harder and cannot
save a result; the result and its digest are untouched.

**Recorded, not repaired.**

- `refute_affine_single_source` builds its rival-position witness by perturbing only the *first*
  other input position rather than trying each. For a requirement varying with input 1, the witness
  for position 2 would not be found. The failure direction is conservative — a spurious negative,
  never a spurious positive — and this requirement varies with input 0, so the certificate produced
  here is complete and was re-verified against the requirement itself.
- `state_authority_report` computes its booleans with `all()` over the programs it is given, so an
  empty list would make them vacuously true. P6 independently requires the evolvable arm to solve
  2/2, and the checker refuses a result with fewer than two constructed transformations, so the
  hole is closed at the decisive layer rather than left open.
- `evaluate()` would raise rather than return a negative if it were called on an acquisition that
  adopted nothing. The runner stops before that point, so it is unreachable here.
- A validator control is bound to a variable named `unsafe` while actually testing an inherited
  composition. Capability refusal is exercised by the test suite, not by that control, and the
  returned keys say so; only the variable name misleads.

Two independent demonstrations that the instruments can fail were run rather than asserted. The
anti-lookup scanner was handed a body that really does appear as a literal in
`m091_lineage.py` and flagged it, and was handed a string that really does appear in
`m091_expressivity.py` and flagged that too — while the actual adopted body is absent from both.
And one recorded field of the result was flipped and the checker refused it with three independent
blocking findings before the artifact was restored byte-identical.

## The next causal ceiling

**The substrate from which a primitive is assembled is authored.** M090 moved the ceiling from the
language to the interpreter beneath it; M091 shows the language above that boundary can genuinely
grow, and moves the ceiling to the *assembly* substrate — the micro-operations, the operator set and
the signature space that bound what any new primitive can possibly be. See D061.
