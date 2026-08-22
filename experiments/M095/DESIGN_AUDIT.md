# M095 — design audit, before any protocol

**Nothing is frozen.** This audit was run against the M095 mechanism *before* proposing a
protocol, because that is where M094's four amendments say defects are cheap. It attacks the
mechanism rather than confirming it. It has found **twenty-six** defects across six passes:
twenty-five are repaired. One is not: defect 19 is a control that cannot fail, disclosed rather
than quietly carried.

The sixth pass was a local mutation attack. It constructed small Python worlds that contradicted
the apparatus's assumptions — two renderers on one class, two objects with the same nested field
name, misleading filenames, unrelated public methods, an incomplete tied round, and two competing
nested targets. The first attack produced eight failing regression tests; attacking the repairs
and the remaining attribution surface brought the pass to a dozen failing tests across seven
defect families. This was AI-assisted development review on the project owner's machine, not
independent human evaluation.

The fifth pass did not look for defects. It asked what the two disclosed ones would take to
remove, and one of them turned out to need far less than the audit had claimed.

The fourth pass was adversarial and ran against the apparatus rather than the mechanism. Five
independent review passes, none of them shown the others' findings, were each asked to break
the arms by killing the mechanism underneath them — machine review, under the AI-assisted
development provenance this project records in
`docs/AI_ASSISTED_DEVELOPMENT_PROVENANCE.md`, not independent human evaluation and not
evidence of the kind M085's external-maintainer requirement is about.

They did. Two of the three arms reported `satisfied` while the thing they measure was dead, and
amendment A4's defect was found for the **third** time in this milestone, inside the loop
written to remove it.

The attack that mattered most in the first pass was not clever. It was: *which of M094's lessons
has M095 already forgotten?* Five of the first nineteen turned out to be regressions of amendments this
project paid for one milestone ago.

The attack that mattered most in the second pass was one question the first pass never asked.
`DESIGN.md` disclosed that the world arranges one thing — the relation between the two classes'
call-site counts — and separately that the diagnosis's selections are not authored. Both true.
Neither answers whether the result *depends* on the arrangement. It did: before defect 5 was
repaired, the milestone's central relation held in two of six arrangements. Defect 7 records the
measurement, the domain it forced the claim to carry, and — after the fifth pass — how that
domain was widened again rather than merely disclosed.

## Defect 1 — the search had stopped executing candidates (A2, forgotten)

`m095_chain.search` accepted candidates on the structural predicate alone. Its own module
docstring claimed "the same execution-based acceptance", and that was false.

This is exactly the defect **amendment A2** repaired for M094: a candidate that binds the required
keys and raises when run passes a predicate that only reads it. M094's qualification refuted the
mechanism over it. M095 reintroduced it one milestone later, in a module whose docstring asserted
the opposite.

**Repaired.** The search now confirms survivors through `m094_execution` — the same shared probe —
and records `executed` and `confirmed_by_execution`. Pinned by
`test_the_search_confirms_its_survivors_by_execution`.

## Defect 2 — the nested requirement did not record what the call sites wrote

`RenderNestedValueObject` encoded a nested demand with an **empty wrapper**: it recorded *that* a
key held a nested mapping, not *which inner keys bound to which fields*.

So the probe computed the expected value as `getattr(instance, "reading")` — the inner **object** —
where the call site had written a **mapping**. Every correct candidate was refused.

The dangerous part is what that would have looked like in a run. With defect 1 present, the
structural predicate alone was deciding and the chain reported a healthy enabling relation. Fixing
defect 1 first is what exposed defect 2: **12 survivors, 0 confirmed.** Had they been fixed in the
other order, or had only defect 2 been found, the qualification would have reported the mechanism
refuted when the repair was correct — the same false-refutation shape as M094's amendment A1.

**Repaired.** The wrapper now carries the inner pairs (`nested:reading_id:reading_id;unit:unit`), so
anything checking the requirement can compute the expected value without discovering a method
first. Pinned by `test_the_nested_requirement_records_what_the_call_sites_wrote`.

## Defect 3 — a nested field was constructed as a string

`m094_execution.constructible_cases` filled a field annotated as another value object with a
generated **string**. A frozen dataclass accepts it, so the case *constructed* — and then every
method reaching into that field raised, so every candidate was refused.

Same family as M094's A1 and as the `ContainerSpec` case: the instrument cannot build the object,
and the failure reads as a refutation of the mechanism rather than of the instrument.

**Repaired.** A field annotated as a sibling class is now constructed. Because the probe runs in a
subprocess behind a JSON payload, the object travels as a construction recipe and is materialised
identically on both sides, so the parent verifies exactly what the child builds. Pinned by
`test_a_nested_case_is_built_as_an_object_not_a_string`.

## Defect 4 — the second target is chosen by a name — **REPAIRED**

> **Resolved.** Every capability the measure ranks equal first is now repaired, so the ordering
> decides nothing. At S1 the lineage repairs both of `Sample`'s tied capabilities —
> `as_mapping` for the nested requirement and `as_dict` for the plain one — and **nothing is
> left unmet at S2**. The tie and the alphabetical ordering are unchanged and still asserted by
> a test; what changed is that neither is load-bearing.
>
> The obstacle that made this hard is gone too. Both repairs land on the same class, and the
> method-name candidates are a short shared list, so the second was liable to be called
> `as_mapping` and shadow the first — silently undoing the earlier repair. A name the class
> already defines is now unavailable, read from the class rather than tracked, which is the same
> style of state-dependent applicability the milestone already rests on. M094's adopted
> mechanism is unchanged at `259e12f5…`: neither of its targets defined a public method, so the
> set of available names it saw is the same one.

The finding as originally written follows.

At S1 two capabilities on `Sample` tie at demand 2:

```
demand=2  Sample/render_nested_value_object_as_mapping
demand=2  Sample/render_value_object_as_mapping
```

The one repaired is decided by **alphabetical order on the capability name**: `render_nested_…`
sorts before `render_value_…`.

This is **amendment A4's defect at the capability level**. A4 removed it for class names by
repairing every class the measure ranks equal first. The capability-level tie survived.

It matters more here than A4's did. Had the tie fallen the other way, the lineage would have
repaired the plain renderer and **no enabling would have been demonstrated at all**. The chain's
central result currently depends on which capability name sorts first.

**Why it is not repaired here.** A4's remedy — repair everything tied — needs handling this
milestone does not have: two repairs land on the *same class*, and the composition names methods
from a small candidate set, so both are liable to be called `as_mapping` and the second would
shadow the first. Getting that right is a design decision about multi-capability repair, not a
patch, and rushing it is how the three defects above got written in the first place.

Pinned by `test_the_capability_tie_is_real_and_no_longer_decides_anything`, which keeps the tie
honest and the remedy honest at once: the tie and its alphabetical ordering are still asserted, and
so is the fact that both capabilities get repaired.

**This was the first thing to settle before an M095 protocol could be frozen. It is settled.**

## Defect 5 — amendment A4's rule was applied at S1 and not at S0 — **REPAIRED**

`run()` selected its first target with `s0.unmet[0]`: the head of a list sorted by descending
demand and then by name. At S1 it did the right thing — `s1.tied_selection()`, every capability
the measure ranks equal first — because that is what amendment A4 requires. At S0 it took one.

In the declared world this decided nothing, because nothing ties at S0: `Reading` draws demand 3
against `Sample`'s 2. That is exactly why it survived defect 4's audit, which looked at the tie
that was visible and not at the rule that was inconsistent.

Give the two classes equal call sites and all three insufficiencies tie at S0 — and the head of
that sorted list is `Sample/render_nested_value_object_as_mapping`, which is **B**. The chain
would have spent its first step on the target it exists to prove unreachable, failed, and reported
no enabling.

**Repaired.** S0 now applies the same rule as S1: every tied capability is attempted, and what is
reachable is adopted. Pinned by `test_the_s0_selection_applies_the_same_tie_rule_as_s1`.

## Defect 6 — the world's facts were the author's constants, not the world — **REPAIRED**

`WorldFacts` defaulted `inner_call_sites` and `outer_call_sites` to the module-level
`READING_CALLERS` and `SAMPLE_CALLERS`, and `Chain.to_dict` recorded `WorldFacts().to_dict()`.
So the record answered "three inner, two outer" whatever had been written to disk.

On its own that is a documentation bug. In combination with defect 7 it is worse than that: the
sweep that measures the claim's domain varies precisely those two numbers, and every point of it
would have been recorded as the declared world. The measurement and the record would have
disagreed silently, and the record is the evidence.

**Repaired.** `WorldFacts.of(root)` counts the files. The counts carry no defaults, so nothing can
construct the facts without stating them. Pinned by
`test_the_world_facts_are_counted_not_defaulted`.

A second defect was introduced while repairing this one and is recorded rather than quietly
fixed. `build()` first took `reading_callers: int = READING_CALLERS`, whose default binds at
import and made the parameter inert — patching the module constant changed nothing, and the first
sweep run silently reported a four-caller world as a three-caller one. The counts now resolve in
the body. Pinned by
`test_the_caller_counts_are_resolved_when_build_runs_not_when_it_is_defined`.

## Defect 7 — the claim's domain was never measured, and it was bounded — **REPAIRED**

> **Resolved.** The boundary was real and is gone. Where the enabling repair carries less demand
> than the repair it enables, the greedy rule never ranks it and the chain stalled with the remedy
> sitting untried below it. The audit recorded that as a limitation of the selection rule and said
> repairing it "needs handling this milestone does not have".
>
> It needed less than that. **A failed search already names its own obstacle.** When the nested
> requirement cannot be met, the search reports the operation that could not apply — and that
> operation knows which class must supply which rendering. So the lineage asks the failure what
> would unblock it and repairs *that*, even though the measure does not rank it.
>
> Nothing is added to the operation set. The same operations are offered in the same states; only
> which target is attempted changes. That matters for the milestone's boundary with M096: this is
> not a larger language, it is the same language used where it was previously left unused.
>
> | inner callers | outer callers | regime | before | after |
> |---|---|---|---|---|
> | 2 | 1 | inner>outer | yes | yes |
> | 3 | 2 | inner>outer — declared | yes | yes |
> | 1 | 1 | inner==outer | yes | yes |
> | 2 | 2 | inner==outer | yes | yes |
> | 1 | 2 | inner<outer | **no** | **yes** |
> | 1 | 3 | inner<outer | **no** | **yes** |
> | 0 | 1 | no inner demand | no | no |
> | 0 | 3 | no inner demand | no | no |
>
> **The boundary that remains is about existence, not rank.** If the inner class is never rendered
> directly it presents no demand of its own, so there is no insufficiency to descend to — reading
> the obstacle does not help when the remedy is not something the diagnosis can see. The
> arrangement arm now sweeps two such points, so it still has arrangements that must come out
> negative and remains falsifiable in both directions.
>
> The claim loses its ordering qualifier:
>
> > An adopted repair changes what the lineage can reach, **wherever there is an enabling repair
> > for it to find.**
>
> Pinned by `test_the_enabling_relation_holds_where_the_enabler_is_outranked` — which asserted the
> exact opposite until this was repaired, and was written precisely so that a boundary moving
> outward would be loud rather than silent. It was. That is the arm and the test doing the job
> they were built for, and it is the only reason this improvement was visible at all.
>
> `test_the_descent_target_is_read_from_the_obstacle_not_from_the_ranking` pins the part that makes
> it a measurement rather than a heuristic: the class repaired is the one the unreachable operation
> names.

The finding as originally written follows.

`DESIGN.md` disclosed the ordering pressure as "the only thing the world arranges", and said what
is *not* authored: "which target the diagnosis selects at either step". Both statements are true.
Together they invite a question neither answers: **if the arrangement were different, would the
milestone still hold?**

It was never asked. Asking it is one loop, and the answer was no.

| inner callers | outer callers | regime | enabling, before | enabling, after |
|---|---|---|---|---|
| 3 | 2 | inner>outer — **the declared world** | yes | yes |
| 4 | 2 | inner>outer | yes | yes |
| 2 | 2 | inner==outer | **no** | yes |
| 3 | 3 | inner==outer | **no** | yes |
| 2 | 3 | inner<outer | **no** | **no** |
| 1 | 3 | inner<outer | **no** | **no** |

Before defect 5 was repaired the central result held in **two of six** arrangements, and the two
it held in were the declared one and a scaling of it. A reader told only that the ordering is
"the only thing the world arranges" would not learn that the result rests on it.

Repairing defect 5 recovers the `inner==outer` row: with all three tied capabilities attempted,
the inner renderer is adopted, the nested operation flips, and B is repaired in the next round.
Four of six.

**`inner<outer` is a real boundary and is not repaired here.** When the outer class has more call
sites, the repair that would enable B carries *less* demand than B itself. It is never ranked
first, so the greedy rule never reaches it; the fixed point stalls with B unmet and an untried
repair sitting below it that would have unblocked it.

That is a limitation of the **selection rule**, not of the mechanism. The operation is the same in
that world and would apply if the inner renderer existed. Escaping it means being willing to
repair something the measure does not rank first — to search for an *enabler* rather than for the
greatest unmet demand — and that is a different question from the one M095 asks. It is close to
what M086-C's failure already identified: "a mechanism that generates a correct candidate and then
chooses a wrong one is not helped by generating more."

So the claim acquires a stated domain instead of an unstated dependency:

> An adopted repair changes what the lineage can reach, **in worlds where the enabling repair is
> not outranked by the repair it enables.**

That is narrower than the previous wording and it is what the evidence supports. Pinned in both
directions: `test_the_enabling_relation_holds_wherever_the_enabler_is_not_outranked` over four
arrangements, and `test_the_enabling_relation_fails_where_the_enabler_is_outranked`, which pins
the boundary as a negative so it cannot quietly move.

## Defect 8 — `A` was defined by position — **REPAIRED**

`step_a` was "the repair made first". Once S0 can adopt several repairs in one round, first is not
the same as enabling, and a chain that assumed it would have named the wrong repair as the cause
in exactly the arrangements defect 7 is about.

`A` is now **the repair after which the nested operation can apply**, determined by reading the
tree after each adoption rather than by counting. In the declared world it names the same repair
it always did. Pinned by `test_the_enabling_repair_is_the_one_that_flipped_the_operation`, which
runs in the tied world where position and cause come apart.

## Defect 9 — three fields in the record asserted what they claimed to measure — **REPAIRED**

`Chain.to_dict()` carried `second_target_was_not_supplied: True` and
`the_enabling_repair_was_identified_by_measuring_the_flip: True`. `WorldFacts.to_dict()` carried
`selection_is_the_lineage_s: True`. All three were hardcoded literals in the evidence record.

A boolean that is always `True` is not evidence. It cannot fail, it cannot be recomputed, and a
checker reading it would report a property that nothing established — the *checker passes without
evidence* shape, except sitting inside the record rather than inside the checker, where it is
harder to see.

**Two of the three were introduced during this same audit**, in the commit that repaired defect 8.
The defect being repaired was a claim the record could not support, and the repair wrote another
one. That is worth more than the fix: the failure mode is not carelessness about a known list, it
is that asserting a property feels like establishing it, at the moment of establishing something
else.

**Repaired.** `second_target_came_from` carries what the diagnosis actually named at S1, which a
checker can re-derive by re-measuring instead of believing a flag. `step_a_identified_by` records
*how* A was found — either the nested operation became applicable after that adoption, or the chain
fell back to the first repair that reached. **Both values occur**, which is what stops it becoming
the constant it replaced: the declared and equal-demand worlds report the measured case, and a
world where the enabling repair is outranked reports the fallback, having adopted something without
unlocking anything. Pinned by `test_the_record_distinguishes_a_measured_a_from_a_fallback`.

The world's asserted boolean is dropped rather than replaced. That the selection is the lineage's
own is an argument the prose makes and the arms measure; as a `True` in a data record it looked
like a finding.

## Defect 10 — the tie still decided the domain, in the loop that was written to stop it — **REPAIRED**

Defect 5 moved amendment A4's rule to S0 and the two documents recorded the ordering as no longer
load-bearing. It was. `tied_first` is computed once and iterated while the tree is rewritten under
it, and in the equal-demand worlds the tied set **contains B itself**. B survived to become
`step_b` only because `render_nested_value_object_as_mapping` sorts before
`render_value_object_as_mapping`, so it was attempted at index 0 — at true S0, where it correctly
fails — rather than after its enabler had been adopted.

A4's premise is that members of an equal-ranked set are indistinguishable by the measure. So
permute them. Reversing `tied_selection` and re-running the arrangement arm:

| | outcome | disagreements |
|---|---|---|
| as shipped | `satisfied` | none |
| tied set reversed | **`refuted`** | (1,1) and (2,2) |

Two of the four supported arrangements — the entire `inner==outer` regime, half of what defect 5's
repair had recovered — were held up by a string comparison. This is A4's defect for the **third**
time in one milestone, in the loop written to remove it, with both documents declaring it settled.

**What made it invisible is the part worth keeping.** Under the reversal the mechanism *worked*.
B was reached, in the first round, after its enabler, through A's method. The record only read the
S1 round, so a run whose mechanism succeeded reported nothing. The failure was not in the search
but in which loop index the record was willing to look at.

**Repaired.** The nested repair is recognised in whichever round it lands, provided its enabler was
already identified. Verified order-invariant: `satisfied` with no disagreements in both directions.
Pinned by `test_the_domain_survives_permuting_every_tie`, which permutes every tie and requires the
whole sweep to be unchanged — a stronger statement than any single tie assertion, and the one A4
has now needed three times.

## Defect 11 — two of the three arms could not fail — **REPAIRED, and one is now `unrunnable`**

Both were found by killing the mechanism and watching the arms pass.

**The more-budget arm had no positive rung.** Its verdict was `not any(rung.reached)` plus a
saturation check, and an empty sweep is exactly what a *dead searcher* produces. Three independent
kills each left it reporting `satisfied`: the enabling operation never applying, the operation never
being offered at all, and the execution probe able to construct no case. The third is amendment A1
running backwards — an unconstructible case read not as a refutation but as a *confirmation*.

**Repaired.** The arm now records the offered nested-operation census and refuses to read an empty
sweep unless the same searcher reaches B at S1, where it is reachable. All three kills now report
`unrunnable`. Pinned by `test_a_dead_searcher_makes_the_budget_arm_unrunnable_not_satisfied`.

**The random-target arm's `satisfied` was fixed before it ran.** B becomes reachable only when the
*inner* class supplies a renderer; every repair is inserted into its own target's class; and both
eligible rivals targeted the outer one. `b_reached` was False by construction. Worse, one of the two
"rivals" *was* B — the control's own target — so the census that the module docstring justified as
"exhausting a set of two" was one rival plus a re-run of the control, and a test asserted
`len(rivals) >= 2`, passing only because of the miscount.

**Repaired, and the verdict changed.** The nested capability is no longer counted as a rival, and
the arm reports `unrunnable` when no eligible rival can write into the class the requirement needs.
In the declared world that is now its verdict: **one eligible rival, targeting `Sample`, while the
requirement needs a renderer on `Reading`.** The honest statement is that this world contains no
rival capable of testing the claim. Making the arm informative needs a second insufficiency on the
inner class — a different world, not a different check.

The arm does have teeth against a *mis-selecting* diagnosis: ranking `Sample` first makes it report
`refuted`. So it is a control on the selection rule, and its docstring claimed the enabling relation.

## Defect 12 — a refutation was filed as an instrument failure — **REPAIRED**

Two shapes, both A1 inverted. A1 exists so an instrument failure is not read as a refutation; here
a refutation was read as an instrument failure.

`if after is None: row.error = "B is no longer unmet after the rival repair"`. B settled by a target
the diagnosis rejected is the single most decisive refutation this arm can observe. It was recorded
as `unrunnable`, with `b_reached_afterwards: false` — the opposite of what had happened.

And in every arm, `any(point.error)` was tested *before* the disagreement check, so one broken point
buried a three-point refutation as `unrunnable`.

**Repaired.** B being met is B being reached. A refutation among the points that did run outranks an
error elsewhere: A1 says an instrument failure is not evidence about the mechanism, not that the
points which ran stop counting. Pinned by `test_a_rival_that_settles_b_refutes_rather_than_erroring`
and `test_a_refutation_outranks_an_instrument_error`.

## Defect 13 — two more asserted booleans, and a verdict that accepted a run identifying nothing — **REPAIRED**

Defect 9 removed three hardcoded `True`s. It missed two, and one of them was introduced by the same
commit: `the_s0_tie_was_not_broken_by_a_name` was `bool(self.first_step)`, and
`every_eligible_rival_was_run` was the literal `True`. Neither compared anything.

Both now compute. The tie property checks the attempted set against the tied set the measure
produced, which is why `Chain` now stores `s0_tied` and `s1_tied` rather than only their joined
strings; the census property compares rivals run against rivals eligible.

Separately, `enabling_demonstrated` accepted a run in which `step_a` was the positional fallback —
the very pick defect 8 removed — and did not require the second repair to be the nested one, so the
claim could be carried by whatever else happened to be tied. Both are now required.

**The pattern across defects 9 and 13 is the finding.** Five asserted booleans have been removed in
two passes, and the pass that removed three wrote two more. Enumerating a record's literals is not
a fix; the habit that produces them is that asserting a property feels like establishing it.

## Defect 14 — a dead instrument reported as a refuted domain — **REPAIRED**

Kill the execution probe so that no candidate can ever be confirmed, and every arrangement
reports no enabling. That is indistinguishable, from the outside, from a domain that is simply
wrong — and the arrangement arm called it **`refuted`**, which is a claim about the mechanism.

The honest answer is that it could not measure. `unrunnable` exists for exactly this, and the
arm reached for `refuted` because a refutation is what an all-negative sweep looks like.

**Repaired.** A sweep in which nothing was repaired in any arrangement is `unrunnable`. The gate
is positive evidence — some point must have reached some repair — rather than an absence.
Pinned by `test_a_dead_instrument_is_unrunnable_not_a_refuted_domain`, with a companion test
making sure the gate does not swallow a real disagreement.

Two record fields had the same shape. `a_is_necessary` was `the counterfactual reached nothing`,
and a counterfactual reaches nothing trivially when there was no A to remove — so a run that
demonstrated no enabling still published `a_is_necessary: true`. Same for
`the_operation_is_the_vehicle_not_the_cause`. Both are claims about an enabling relation and now
say `null` when none was shown.

## Defect 15 — a probe that never ran was recorded as candidates that ran and failed — **REPAIRED**

`attempt.executed` was set from the survivor count whatever happened. When
`constructible_cases` returned nothing — the instrument unable to build a single case — the
search recorded *N candidates executed, 0 confirmed* and stopped with
`"no survivor reproduced the requirement when executed"`.

Nothing had been executed. The record described a repair that had been tested and failed, where
in fact the instrument could not test it. **This is amendment A1 for the fifth time in this
milestone** — an instrument failure wearing a refutation's clothes, in the field whose entire
purpose is to show that acceptance ran rather than read.

**Repaired.** `executed` counts the window actually handed to the probe, so a probe that ran
nothing reports zero, and the stop reason distinguishes "nothing agreed" from "nothing was
tested". Pinned by `test_a_probe_that_never_ran_is_not_recorded_as_candidates_that_failed`.

A second import-capture was fixed alongside it: `m095_arms.DECLARED` was a module-level tuple,
frozen at import, so the sweep would have ignored any change to the world constants — the same
inertness `build()`'s parameters were repaired for under defect 6.

## Defect 16 — the counterfactual was the control, run a second time — **REPAIRED**

The counterfactual root was built as S0 and then left untouched until the end of the run. So the
"world where A never happened" was **byte-identical** to the state the control had already
searched, for the same requirement, with the same operation set. Measured: both trees digest to
the same value, both examine 191, both find nothing.

It was a determinism check presented as a fourth independent pillar. `DESIGN.md` said it showed
"B was not always reachable and reached later" — which the control already showed.

The distinction it was supposed to draw is real and was simply not being drawn. Removing **A**
is not the same as removing **everything the first round adopted**, and once amendment A4's rule
applies at S0 the first round can adopt several repairs.

**Repaired.** The counterfactual now replays the S0 round into its own world, skipping only the
repair that flipped the operation. In the declared world A is the sole tied repair, so nothing
is replayed and the published measurement is unchanged at 191. Where three capabilities tie, the
other repair is kept and only A is dropped: **143 examined, B still unreachable.** That is a
stronger statement than the one the milestone was making — A *specifically*, not merely some
first-round repair. Pinned by `test_the_counterfactual_removes_a_rather_than_everything`.

## Defect 17 — the flip predicate chose its own subject — **REPAIRED**

`_nested_is_reachable` took its requirement from `diagnosis.considered`, which is unsorted.
Every other consumer of the nested requirement binds to `unmet`, which is ranked by demand:
`control_from_s0`, the S1 selection, and the counterfactual.

In a world presenting more than one nested requirement, the predicate that identifies **A**
would watch a different requirement from the one the milestone is about — and could name as A a
repair that the enabled repair never calls, while the record carried
`step_a_identified_by: the_nested_operation_became_applicable` and
`enabling_demonstrated: true`. The counterfactual cannot catch it, because it removes A and
asks about the *ranked* requirement.

The declared world presents one nested requirement, so nothing was wrong in it. That is what
makes it worth recording: it is the same shape as defect 5, which was also inert in the declared
world and decided the milestone everywhere else.

**Repaired.** The requirement is passed in from `run`, taken once from `unmet` at S0, so the
predicate and the claim are about the same thing. `run` now refuses a world that presents no
nested requirement at all rather than silently reporting one that is never reachable.

## Defect 18 — the record still described the world it expected — **REPAIRED**

Defect 6 removed the defaults from `WorldFacts`'s two call-site counts and stopped there. Three
fields kept theirs: `inner_class = "Reading"`, `outer_class = "Sample"`, `nested_field =
"reading"`. A world built from different classes would have been recorded as this one.

`nothing_renders_itself_at_s0` was worse than defaulted — it was computed by searching the
source text for `"def "` after the first `"class "`. A docstring or a comment mentioning `def`
would have decided a fact about the code.

**Repaired.** All four are read from the syntax tree. The outer class is whichever declares a
field annotated as another class present in the same module; the inner class is what that
annotation names; and whether anything renders itself is whether any class defines a public
method. Pinned by two tests, one of which builds a world of differently named classes and one
of which puts `def` in a docstring.

The arrangement arm had the same shape: each `Point` recorded the caller counts it **asked**
`build` for, not the ones the world reported. A build that ignored its parameters would have
been recorded as the arrangement it was meant to be and read as a refutation of the domain
rather than as a broken instrument — which is what the inert-parameter defect under 6 actually
did before it was caught. The arm now compares the two and records a mismatch as an error.

Defect 6 was "the record described the author's intention rather than the experiment's world",
and it was repaired in the two fields where it had been noticed. This is the rest of it.

## Defect 19 — the withheld-operation arm cannot succeed in any state — **DISCLOSED, NOT REPAIRED**

`search`'s docstring said that if the withheld arm ever reached B it "would say A was never
needed, which would refute the whole chain". It cannot reach B, in any state.

`IncludeRenderedField` is the **only** operation in the set that can satisfy
`RenderNestedValueObject`. Withholding it makes the shape unsatisfiable by construction rather
than by measurement, so the arm is testing that removing the only operation which satisfies a
shape makes that shape unsatisfiable.

Measured in the most favourable state available — a world whose **inner class already renders
itself**, so nothing whatever is missing except the operation:

| | examined | survivors | reached |
|---|---|---|---|
| with the operation | 239 | 12 | yes |
| operation withheld | 191 | 0 | **no** |

So the conjunctive table in `DESIGN.md` has a column that is true by construction. The arm
records that the operation is the vehicle, which is worth recording and is true; it is **not a
control that could have come out the other way**, and it was presented as one.

**Not repaired, because repairing it is a design change rather than a fix.** The arm would only
become falsifiable if the set contained a second, independent way to satisfy the nested shape —
and inventing one so that a control can fail is the wrong reason to extend a language. What is
corrected here is the claim: the docstring and the document now say what the arm can and cannot
show.

The left-hand column of that table — B reachable at S1, unreachable at S0 — remains measured,
and it is the half the milestone rests on.

## Defect 20 — the emitted call could name a method that did not supply the requirement — **REPAIRED**

`supplying_method` first asked whether *some* method on the class supplied the rendering, then
returned the first public method whose mapping merely contained the required keys. With a wrong
key-to-field renderer followed by a correct one, the class-wide predicate passed and the emitted
outer repair called the wrong method. Async functions and decorated properties could also be
selected even though the generated expression is synchronous `obj.method()`.

`RenderNestedValueObject.is_supplied_by` had the same call-contract gap for async,
argument-taking and decorated methods.

**Repaired.** Each candidate method must itself satisfy the exact key, field and wrapper mapping,
and it must be an undecorated synchronous instance method callable with no extra arguments. Pinned
by `test_the_supplier_is_the_method_that_satisfies_the_requirement`,
`test_an_async_or_decorated_renderer_cannot_be_called_as_a_plain_method`, and
`test_a_nested_supplier_must_also_be_a_plain_callable_method`. Both supply predicates now ignore
returns inside nested helper definitions, pinned separately for the plain and nested shapes.

## Defect 21 — nested demand combined two different base objects — **REPAIRED**

The nested-binding reader reduced `obj.field.subfield` to `(field, subfield)`, discarding `obj`.
It therefore accepted a mapping that combined `sample.reading.reading_id` with
`other.reading.unit` as one rendering of `reading`, although no single value object supplied both
values.

**Repaired.** A nested rendering now requires every value to share both the same base object and
the same field. Pinned by `test_nested_bindings_do_not_combine_two_different_base_objects`.

## Defect 22 — world demand was counted from filenames, not code — **REPAIRED**

`WorldFacts.of` counted `reading_caller_*.py` and `sample_caller_*.py`. Replacing one named caller
with a comment left the record at three inner call sites while the diagnosis measured two. The
evidence could therefore describe the files the author intended to build rather than the demand
that actually ran.

**Repaired.** The record now derives both call-site counts from the same diagnosis and capability
shapes as the chain. Pinned by
`test_the_world_facts_count_measured_demand_not_matching_filenames`.

## Defect 23 — any public method was recorded as a renderer — **REPAIRED**

The S0 fact `nothing_renders_itself_at_s0` became false when a class gained
`validate(self) -> True`. The record asked only whether any public method existed, not whether a
callable method rendered the class's declared fields or satisfied a measured nested rendering.

**Repaired.** `WorldFacts.of` now applies the structural rendering predicates and the same callable
contract as the reach operation. Pinned by
`test_an_unrelated_public_method_is_not_recorded_as_a_renderer` while the existing positive
renderer test keeps the check from becoming permanently true.

## Defect 24 — tied-round completeness was asserted but not bound to the tied set — **REPAIRED**

`every_tied_capability_repaired` meant `second_step` was non-empty and every recorded attempt
reached. It never compared those attempts with `s1_tied`; `to_dict` did not expose either tied set;
and `enabling_demonstrated` did not require the completeness claim. A record that omitted one of
two tied capabilities could therefore say both `every_tied_capability_was_repaired: true` and
`enabling_demonstrated: true`.

**Repaired.** Attempted targets must equal the measured tied set, both S0 and S1 sets are recorded,
and the central verdict requires both completeness checks. The permutation case where B is
reached after A in the S0 tied round is handled separately: it passes only if that entire S0 set
was attempted and reached. Pinned by `test_tie_completeness_is_bound_to_the_measured_s1_set` and
the existing full tie-permutation sweep.

## Defect 25 — instruments described different nested subjects — **REPAIRED**

The control binds B to the first ranked nested insufficiency in `diagnosis.unmet`. The helper that
decides which inner classes can enable B instead took the first nested entry from unsorted
`diagnosis.considered`. In a world with two outer/inner pairs, the control targeted the higher
demand `OuterTwo`/`InnerTwo` relation while the arm excluded rivals for
`OuterOne`/`InnerOne`.

`WorldFacts.of` also chose the first syntactic outer/inner annotation pair, so the evidence record
could describe `OuterOne` while the chain actually attacked `OuterTwo`.

**Repaired.** Both the arm and the world facts now derive their subject from the same ranked unmet
nested target as the control. Pinned by `test_random_target_arm_uses_the_ranked_nested_subject`.

## Defect 26 — nested demand ignored rival-class ambiguity — **REPAIRED**

`RenderNestedValueObject.demand_sites` accepted a nested literal for every class declaring the
same outer field name. When two reachable outer classes both declared `reading`, one caller was
credited as demand for both even though the site did not distinguish them. M094's plain-rendering
shape already rejects exactly this kind of ambiguous attribution; the M095 shape ignored the
`rivals` passed to it.

**Repaired.** A nested site is evidence only when exactly one reachable candidate class declares
the source field, and that candidate is the class under measurement. Pinned by
`test_nested_demand_is_not_attributed_when_two_reachable_classes_explain_it`.

## What the chain measures after the repairs

| | examined | survivors | executed | confirmed | reached |
|---|---|---|---|---|---|
| **B from S0** — control, run first | 191 | 0 | 0 | 0 | **no** |
| A from S0 | 191 | 3 | 3 | 3 | yes |
| **B at S1, operation withheld** | 191 | 0 | 0 | 0 | **no** |
| **B from S1** | 239 | 12 | 12 | **12** | **yes** |
| **B without A** — counterfactual | 191 | 0 | 0 | 0 | **no** |

Every reached repair is now confirmed by running it, not by reading it.

## What did not move

M094's diagnosis digest is still `48cd5e9c2354a365…` and its adopted mechanism `259e12f5cbf86ec7…`;
`check_m094_result.py --require-result` exits 0. Every change here is additive to shared code — a
`nested:` wrapper the probe understands, and nested construction for a case field — and M094
produces neither.

## The honest summary

Twenty-six defects across six adversarial passes.

Three were in the **instrument** — defects 1, 2 and 3 — and all three would have made a
qualification report a false refutation. Two were in the **record** — defect 6 and the inert
parameter recorded beneath it — and would have made the evidence describe a world other than the
one that ran. Three were in the **selection** — defects 4, 5 and 8 — and those are the expensive
kind: an instrument defect costs a run, a selection defect costs the claim.

The sixth pass added one method-selection defect, two nested-demand attribution defects, three
record/verdict defects, and one cross-instrument subject defect. All seven are repaired. In total,
twenty-five are repaired; defect 19 is not, and is disclosed instead.

**Defect 7 was repaired after being recorded as unrepairable**, which is worth more than the
repair. The audit said escaping it "needs handling this milestone does not have" and left it
as a boundary on the claim. It needed one observation: a failed search already names the
operation it could not apply, so the obstacle identifies its own remedy. The conclusion that
it could not be fixed was reached by describing the difficulty rather than by trying. Defect 9 is the one worth re-reading: two of its three literals
were written *by the commit that repaired defect 8*, which says the failure mode is not
forgetting a known list but that asserting a property feels like establishing it.

**The pattern worth naming.** Defect 4 was the capability tie at S1; defect 5 was the same rule
missing at S0; both are amendment A4, which this project paid for one milestone earlier. Defect 1
was amendment A2. Defect 3 was amendment A1's family. Five of the first nineteen are regressions
of amendments already bought and recorded, and A4 alone
accounts for three of them — defects 4, 5 and 10, each found after the previous one was
declared settled. The amendments were written down and were not carried forward into
new code — which suggests the register is doing less work than it looks like it is doing, and that
the next milestone should assume it will forget them too.

**What defect 7 changes about the milestone.** The central result was measured in one arrangement
of the authored world and read as a property of the mechanism. The later descent repair widened
the measured domain: the relation now holds in all six demand-bearing arrangements, but only four
have the diagnosis's own ranking produce the enabling order unaided. Two require the failed search
to name and descend to the lower-ranked enabler. The two zero-inner-demand arrangements remain
negative because no enabling insufficiency exists for the diagnosis to find.

What remains before a protocol is a project-owner decision about the qualification population,
then a pool verified by construction, a checker that recomputes, a runner, and a frozen protocol.
The random-target, more-budget and world-arrangement development arms already exist; their presence
does not turn this development mechanism into a qualified result.
