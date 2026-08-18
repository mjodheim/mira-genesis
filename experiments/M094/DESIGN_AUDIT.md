# M094 design audit — resolved before any freeze

**Status: audit complete, twelve defects found — four in the inherited diagnostic, one in the
replacement written here (repaired), and seven in the result checker (repaired). Nothing is
frozen. H39 is registered as an open question only. No qualification exists and none may be
generated until a protocol is frozen.**

This document exists because M094's implementation was committed *ahead* of its protocol, in
`df88d24` (PR #170), while carrying docstrings that claim more than the code does. The audit
below measures those claims against the real repository. Numbers come from
`scripts/audit_m094_design.py`, are re-runnable, and are stored in `DESIGN_AUDIT.json`
(digest `d41ea1ea…`).

Starting point: clean `main` at `df88d24851c018836a35e8102ff0aa7dbf81167c`. M093 is historical
evidence from here on; its record is read, never edited.

The audit asserts nothing about M094's eventual verdict. Its purpose is that these defects are
on the record with reproducible numbers *before* anything is frozen, so that no later correction
can be mistaken for a precommitment.

---

## What the inherited code claims

`metamorphosis/m094_component_discovery.py`:

> The lineage examines each component, produces diagnostic hypotheses, selects the most
> constrained component, and justifies the choice […] This is the first step toward removing
> the authored TARGET_FILE from M093.

`metamorphosis/m094_transform.py`:

> The winning patch emerges from the search, not from authored code. Contrast with M093's
> `CodePatch.generate` which contained the exact patch.

Both claims are currently false. M094 as committed reproduces M093's authored target and
M093's authored patch by construction.

---

## Defect 1 — the deciding indicator names one file rather than measuring a property

`missing_query_method` carries the highest authored severity (3) and is the pattern that
decides the selection. Its entire detection rule is the substring `event.kind`.

| indicator | severity | memory.py | safety.py | contracts.py | components matched |
|---|---|---|---|---|---|
| `event.kind` | 3 | 2 | 0 | 0 | **1 / 3** |
| `if not` | 2 | 5 | 0 | 3 | 2 / 3 |
| `__init__` | 1 | 1 | 0 | 0 | **1 / 3** |

`event.kind` occurs in exactly one eligible component. An indicator that matches exactly one
candidate does not discriminate between candidates; it names one. The "diagnosis" is the
authored `TARGET_FILE` of M093 rewritten as a string search.

## Defect 2 — the detector is inverted with respect to the capability it claims to detect

`missing_query_method` asserts that a component "exposes a collection but no declarative query
method". `mira_core/memory.py` **already defines** `MemoryLedger.events_by_kind` at line 107 —
M093 added it, and it is on `main`.

The pattern fires anyway, and measurably worse than at random:

- with `events_by_kind` present: the indicator occurs **2** times;
- with `events_by_kind` removed: the indicator occurs **1** time.

Adding the capability *raises* the score for the insufficiency that claims the capability is
absent, and the score never reaches zero. This is not a noisy detector, it is an inverted one:
`event.kind` is a fragment of the query implementation, so writing the method necessarily
introduces more occurrences of the evidence that the method is missing.

A diagnostic that reports a missing capability on a component that has it cannot support any
claim about autonomous diagnosis.

## Defect 3 — one eligible component can never be selected

`mira_core/safety.py` matches no indicator at all and scores 0. It is not a rejected
alternative; it is an unreachable one. `DiagnosticHypothesis` requires that "another hypothesis
must exist that could have been chosen instead", and for safety.py no weighting of the current
indicator set makes that true. The falsifiability the dataclass documents is not present.

The selection also does not depend on the authored severity weights: flattening every severity
to 1 selects `mira_core/memory.py` unchanged. What decides is the indicator set, which is the
part keyed to one file.

## Defect 4 — the transformation language contains the finished repair

`TRANSFORM_TEMPLATES` holds exactly **one** template, `suggest_query_method`. There is no search
space; there is one element. That template emits the complete method body as a literal, including
the guard clause and the filter expression:

```python
def {collection}_by_kind(self, kind: str) -> tuple[...]:
    if not kind:
        raise ValueError("...")
    return tuple(x for x in self._{collection} if x.kind == kind)
```

It also carries a component-specific branch, `before_method="history" if class_name ==
"MemoryLedger" else None`.

This is M093's `CodePatch.generate` with the class and collection names parameterised. The
docstring's contrast with M093 does not hold: what changed is that three identifiers became
arguments, not that the patch became constructed. Parameterisation is not synthesis.

---

## Consequence for the protocol

Were the current code frozen and run, every stage would succeed and the result would be a false
positive: a lineage "diagnosing" a component chosen for it by a substring, and "generating" a
repair it was handed whole. That is the failure M088's `authored_full_experiment_space` ceiling
arm and M089's P10 exist to catch, arriving one level up.

The protocol drafted in `PROTOCOL.json` therefore treats every defect as a **falsifier rather
than an implementation detail**, and the corresponding conditions are written so that the code
under audit fails them:

| defect | in | condition it must fail |
|---|---|---|
| 1 | inherited | `P2_the_insufficiency_is_a_measured_property_not_a_component_specific_string` |
| 2 | inherited | `P3_the_diagnostic_verdict_inverts_when_the_capability_is_supplied` |
| 3 | inherited | `P4_every_eligible_component_is_reachable_under_some_admissible_observation` |
| 4 | inherited | `P6_the_repair_is_assembled_from_composable_operations_and_is_not_a_template_body` |
| 5 | **the replacement** | `P5_..._is_stable_under_a_sweep_of_the_measure_s_own_constants` |

`scripts/audit_m094_design.py` is the instrument for all five and is re-runnable against any
candidate implementation. An implementation that cannot turn these red is not a successor to
M093; it is M093 with more indirection.

Defect 5 is documented below, after the measure it applies to.

---

## The corrected measure, and what it currently reports

`metamorphosis/m094_diagnosis.py` replaces the substring detector with a structural one. It rests
on a single separation, which is what makes it a measurement rather than a name lookup:

> demand is counted **outside** the component; supply is checked **inside** it.

A component is insufficient for a capability when callers that can actually reach it repeatedly
perform by hand an operation it could expose, and it does not expose one. Because the component's
own source is excluded from the demand count, implementing the capability can only ever *lower*
insufficiency — Defect 2 is structurally impossible rather than merely fixed. Demand is attributed
only to files that import the module or a name it defines through a package re-export, so an
unrelated class exposing a collection of the same name contributes nothing.

`tests/test_m094_diagnosis.py` drives this against synthetic repositories, so the properties do not
depend on what `mira_core` happens to contain on a given day.

Two capability shapes are implemented, both generic:

- **`filter_collection_by_attribute`** — callers filter a collection the component exposes,
  by hand, and the component exposes no method doing it;
- **`render_value_object_as_mapping`** — several callers each write the same fields of the same
  value object into a dict literal, and the object cannot render itself. A caller is attributed to
  a class only when the attributes it reads are a subset of that class's declared fields, and only
  above a three-field threshold, below which name coincidence would make the attribution guesswork.

### First result: one shape, and nothing to find

With only the collection shape implemented, the measure **selected nothing**. The capability the
old detector "diagnosed" is already supplied — M093 added `events_by_kind`, and the corrected
measure correctly reports it met — while the other two components expose no collection at all.
P1 and P4 would both have failed. That is recorded here rather than tuned away, because
discovering after a freeze that the diagnosis has nothing to find is an invitation to adjust the
eligible set until it does, and that is the retry D053 forbids.

### Second result: the measure selects a component nobody chose

Adding the second shape makes every eligible component reachable, and the selection changes:

| component | class | capability | demand | supplied | unmet |
|---|---|---|---|---|---|
| **`mira_core/safety.py`** | `SafetyDecision` | render as mapping | **3** | no | **yes — selected** |
| `mira_core/contracts.py` | `Observation` | render as mapping | 2 | no | yes |
| `mira_core/contracts.py` | `Goal` | render as mapping | 1 | no | yes |
| `mira_core/memory.py` | `MemoryLedger` | filter by attribute | 2 | **yes** | no |

The selected insufficiency is real and was not authored. `SafetyDecision` carries `allowed`,
`reason`, `missing_authorities` and `human_release_required`, and three independent
callers — `mira_core/agent.py`, `mira_core/harbor.py` and `metamorphosis/m074_ablation_arms.py` —
each unpack those fields into the same `action_admission` record by hand. The codebase's own idiom
confirms the gap: `MemoryEvent` already defines `to_dict`, and `SafetyDecision` does not.

Two things follow. The measure selected `mira_core/safety.py`, which is **not** M093's authored
target and not the component the inherited detector was keyed to; and it correctly declined to
re-diagnose `mira_core/memory.py`, whose capability is now met. Both are properties of the
repository rather than of a constant, which is what P2 asks for.

This satisfies P1 and P4 as far as diagnosis goes. **It does not make M094 freezable**, because
P6 remains open: the synthesis half is still the single authored template of Defect 4. A milestone
that diagnoses honestly and then applies a handed-in patch has answered half its own question.

### Defect 5 — the replacement reproduces Defect 3 in a new place

Defect 3 was established partly by showing that flattening the inherited severities changed
nothing, so the same question must be put to the replacement. `RenderAsMapping.min_fields` is an
authored constant. Sweeping it:

| `min_fields` | selected | why |
|---|---|---|
| 2 | `mira_core/contracts.py` | `Action` reaches demand 3, ties `SafetyDecision`, and wins on path order |
| **3** | **`mira_core/safety.py`** | the declared value |
| 4 | `mira_core/contracts.py` | `SafetyDecision` falls to demand 1; not every caller reads four fields |
| 5 | `mira_core/contracts.py` | only `Observation` survives |
| 6 | *nothing* | no caller reads six fields of one object |

**The selection is not stable, so the authored constant is what selects.** Three of the five
thresholds pick a different component than the declared one, and the value that makes
`mira_core/safety.py` win is the value that was written down. This is Defect 3 in a new place: the
measure removed an authored *severity* and introduced an authored *threshold*.

The result reported above therefore stands only relative to `min_fields = 3`, and P5 —
"the selection is justified against rivals by measurement rather than by authored weight" —
**currently fails on the corrected measure too**. It is recorded rather than repaired by choosing
whichever threshold gives the tidiest answer, which is the move the sweep exists to make visible.

`scripts/audit_m094_design.py` computes this sweep on every run, so the instability cannot be
silently forgotten, and `tests/test_m094_design_audit.py` fails if the sweep stops being reported.

Two admissible directions, neither presupposed:

- **make demand threshold-free** — for instance by scoring the number of *callers* that would be
  simplified rather than fixing a minimum field count, so no constant sits between the evidence
  and the verdict;
- **require stability as a condition** — treat a selection that moves under a sweep of its own
  constants as a failed diagnosis, which is a stronger and more honest reading of P5.

The second is the more conservative and is the recommended one, because it turns the sweep from a
disclosure into a gate.

## Defect 5, repaired — and a correction to what this document previously reported

The threshold is gone. Attribution no longer asks *how many* fields a site reads; it asks a
question the repository answers:

> Of the classes this file can actually reach, how many could have produced this site?

Exactly one is evidence about that class. Several is evidence about none, because the site does not
say which. Zero is not evidence at all. No number appears anywhere in that rule, so there is nothing
left to sweep — and `scripts/audit_m094_design.py` now verifies that no capability shape carries a
numeric constant, rather than sweeping one.

**The earlier headline was wrong, and this is the correction.** The superseded sweep read:

| `min_fields` | selected |
|---|---|
| 2 | `mira_core/contracts.py` |
| **3** (declared) | **`mira_core/safety.py`** |
| 4 | `mira_core/contracts.py` |
| 5 | `mira_core/contracts.py` |

The declared value was **the outlier**. Three of the four live values chose
`mira_core/contracts.py`, and the threshold-free rule chooses it too. So the previously reported
result — "the measure selects `mira_core/safety.py`, a component nobody chose" — was a property of
the one authored constant rather than a finding about the repository. The robust answer is
`mira_core/contracts.py`.

What the measure reports now, with no constant in it:

| component | class | demand | fields read | unmet |
|---|---|---|---|---|
| **`mira_core/contracts.py`** | `Goal` | **4** | 3 | **yes — selected** |
| `mira_core/contracts.py` | `Observation` | 4 | 5 | yes |
| `mira_core/contracts.py` | `Action` | 3 | 2 | yes |
| `mira_core/safety.py` | `SafetyDecision` | 3 | 4 | yes |
| `mira_core/contracts.py` | `Policy` | 2 | 1 | yes |
| `mira_core/memory.py` | `MemoryLedger` | 2 | — | no — supplied |
| `mira_core/memory.py` | `MemoryEvent` | 2 | 2 | no — supplied |

The selection is robust to the one modelling choice left: excluding single-field attributions
entirely still selects `mira_core/contracts.py`, because `Goal` and `Observation` lead on multi-field
sites alone. `SafetyDecision` remains a genuine unmet insufficiency; it is simply not the largest.

**One limitation, stated rather than hidden.** Dropping the threshold means a site reading a single
distinctive field — `Policy.policy_id` — now counts, and a `to_dict()` would not obviously help such
a caller. The shape is named *render as mapping*, and one field is not a mapping worth a method. Any
minimum that excluded it would be a new authored constant and would reintroduce Defect 5, so the
over-attribution is accepted and disclosed instead. It ranks last and changes no selection today;
if it ever changes one, that is a defect to be reported, not tuned away.

P5 now passes. **P6 does not**, and M094 remains unfreezable for that reason alone.

---

## Defects 6-12 — the result checker decided what it could not see

`scripts/check_m094_result.py` and `metamorphosis/m094_synthesis.py` arrived together, 1,390 lines
with **zero test assertions**. The repository's orphan-module check was satisfied by adding a bare
`import metamorphosis.m094_synthesis as _m094_syn  # noqa: F401` to the diagnosis test file, so CI
was green because nothing exercised either module. The checker's first report read
`"verdict": "negative"`, which was correct by accident: two of its six failures were real and four
were its own defects.

**Defect 6 — the checker was unsatisfiable by construction.** `check_p1` fails unless
`ceiling_arms == {authored_target_component}`; `check_p9` fails unless
`more_budget_same_operations ∈ ceiling_arms`; `check_p10` fails unless
`random_component_selection ∈ ceiling_arms`. P1 and {P9, P10} cannot both hold for any protocol.
The underlying error is a category confusion: those two are **control** arms, which must be able to
fail the verdict, not ceiling arms, which are excluded from it.

**Defect 7 — P11 demanded a violation of the discipline.** It failed unless
`retry_policy.reroll_permitted` was `True`. `false` is the correct value; permitting rerolls is
what D053 forbids. The check also performed no rollback — it read protocol fields.

**Defect 8 — P7 was inverted and passed vacuously.** Named "the adopted repair satisfies a
requirement drawn after the mechanism was fixed", it was implemented as "no `RESULT.json` exists and
the status is draft". It passed *because* nothing had been qualified, and would have flipped to FAIL
the moment M094 produced a real result.

**Defect 9 — P3's failure was its own fixture.** It wrote the component to `pkg2/decision.py` while
its caller imported `pkg.decision`, so the import-reach gate correctly reported zero demand and the
checker read that as a broken diagnosis. Reproduced directly: with the package corrected, the same
fixture yields `unmet=True, demand=1`. **The diagnosis was never at fault**, and P3 passes now.

**Defect 10 — P8 tested a prose disclosure for `is True`.** The
`experimenter_blindness_is_not_claimed` field is a statement of what is and is not claimed, as in
M091. Testing it for a boolean failed every protocol that actually made the disclosure.

**Defect 11 — P6 omitted the assertion its docstring promised.** The docstring lists "No operation
contains a finished body as a literal"; the implementation checked digest length and path
substrings. So the one condition written to catch Defect 4 passed on a synthesis that emits
`def to_dict(self) -> dict: ... return {` as an f-string template.

**Defect 12 — a verdict was declared over conditions that could not be computed.** P7 through P11
make claims about what a qualification run would show. No run exists. Forcing them into pass/fail is
what produced both the vacuous pass and the meaningless failures.

### What was changed

Each defect above is repaired, and `Condition` now carries a `computed` flag. The verdict rule
follows the protocol's own wording — "positive iff every condition is true; each is computed and
each can fail" — and reads: **negative** if any computed condition fails, **incomplete** while any
condition remains uncomputed, **positive** only when every condition is computed and true. A
condition that cannot be decided is no longer a pass.

The report now says:

| | conditions |
|---|---|
| pass | P1, P2, P3, P4, P12 |
| **fail** | **P5** (threshold instability, Defect 5), **P6** (authored repair shape, Defect 4 in milder form) |
| uncomputed | P7, P8, P9, P10, P11 — no qualification run exists |

Verdict: **negative**, now for two real reasons rather than six mixed ones.

`tests/test_m094_checker.py` and `tests/test_m094_synthesis.py` cover both modules, including a
mutated-protocol case for P11 and a `RESULT.json`-under-draft case for P7, so each repaired defect
fails a test if it returns.

### On the synthesis itself

The progress is real and should not be understated: Defect 4's `if class_name == "MemoryLedger"`
branch is gone, every identifier is derived from the AST, and applying the generated repair makes
the diagnosed insufficiency measure as met — the loop closes. A different class yields a different
repair with no shared identifiers.

But P6 asks for a repair **assembled from composable operations**, and an f-string of a method is
not one. There are two templates, no composition and no search; only the identifiers vary. That is
Defect 4 with generic names, and it is recorded as a failing condition rather than an omission.
`tests/test_m094_synthesis.py::test_the_repair_shape_is_still_an_authored_template` pins the honest
position, and must be inverted deliberately if synthesis ever becomes compositional.

## Defect 4 and Defect 11, repaired — the repair is now assembled

`metamorphosis/m094_composition.py` replaces the f-string. Nothing in it emits source. Each
operation contributes **one decision** to a method under construction — a name, a field, a
container, a guard, the shape of the return — and the method is the abstract syntax tree those
decisions produce, unparsed only at the last moment. No operation is a method.

The adopted repair for the diagnosed insufficiency is a **five-operation composition**:

```
name=as_dict
return=mapping
include=success_criteria:list
include=goal_id
include=instruction
```

Acceptance is the diagnosis itself: a candidate is kept when the insufficiency stops being unmet.
Nothing in the search knows what the winning method looks like.

### The numbers, without flattery

| | count |
|---|---|
| compositions examined | 2,711 |
| — incomplete drafts (prefixes, **not** wrong answers) | 2,036 |
| complete methods built | 675 |
| — refused: requirement not satisfied | 189 |
| — accepted | **486** |
| distinct behaviours | 225 |

Two things must be said plainly rather than left to the totals.

**"2,225 refused" would be a misleading headline.** 2,036 of those are partial compositions that are
not yet methods — the search pruning its own frontier. The honest refusal count is **189**: complete
methods that were built, applied, and rejected because they did not satisfy the requirement.

**486 survivors is a loose result, and that is a property of the acceptance predicate.** `is_supplied_by`
accepts any public method returning a mapping that covers the required keys, so the method's name,
the container wrapping of each field, and the presence of extra fields are all unconstrained. Many
compositions therefore satisfy it, and the tie is broken by content address rather than by
preference. Contrast M091, where 3,247 of 3,248 candidates were refused because its requirement was
behavioural equivalence on drawn worlds. **M094's requirement is structural, and structural
requirements are cheap to satisfy.** A tighter predicate — behavioural agreement with the call sites
the demand came from — is the obvious next step and is not claimed here.

So P6 passes, and what it certifies is exactly this: the repair shape is no longer written down. It
does **not** certify that the search is discriminating.

### What remains authored

The operation set and the composition-length bound, exactly as M091's assembly substrate was
authored and was named the next ceiling. `MAX_COMPOSITION_LENGTH` is 12 and is disclosed. What is
not authored is which composition survives.

`scripts/check_m094_result.py` scans **every** `m094_*.py` module for method-body literals rather
than the one that happened to hold the template, since a template moved to a new module would
otherwise pass unnoticed — the failure mode this audit keeps finding. The detector is exercised
against a synthetic module that does carry one, so P6 cannot pass by the instrument going blind.

### Checker state

| | conditions |
|---|---|
| pass | P1, P2, P3, P4, P5, **P6**, P12 |
| fail | *none* |
| uncomputed | P7, P8, P9, P10, P11 — no qualification run exists |

Verdict: **incomplete**. Every statically decidable condition now passes, and that is deliberately
not a result. A milestone cannot become positive by having nothing left that anyone checked; P7
through P11 concern what a qualification run would show, and no run exists. **M094 is still not
freezable, and the reason has moved from a defect to a missing run.**

## What is not in question

The transformation *infrastructure* M093 rehearsed — subprocess sandbox, A/B comparison,
transactional adoption, digest-verified persistence, exact rollback — is sound and is not
re-litigated here. M094's question is upstream of it: who chooses the target, and who writes
the repair.

## Status of H39 and D063

Unregistered and unclaimed. No hypothesis may be registered, no protocol frozen and no
qualification generated until the project owner records the decision. Nothing in this audit
constitutes a freeze.
