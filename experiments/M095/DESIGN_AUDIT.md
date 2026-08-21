# M095 — design audit, before any protocol

**Nothing is frozen.** This audit was run against the M095 mechanism *before* proposing a
protocol, because that is where M094's four amendments say defects are cheap. It attacks the
mechanism rather than confirming it. It has found **eight** defects across two passes: seven are
repaired, and the eighth is a boundary on the claim that cannot be repaired at this scale and is
therefore disclosed.

The attack that mattered most in the first pass was not clever. It was: *which of M094's lessons
has M095 already forgotten?* Four of the eight turned out to be regressions of amendments this
project paid for one milestone ago.

The attack that mattered most in the second pass was one question the first pass never asked.
`DESIGN.md` disclosed that the world arranges one thing — the relation between the two classes'
call-site counts — and separately that the diagnosis's selections are not authored. Both true.
Neither answers whether the result *depends* on the arrangement. It does: before defect 5 was
repaired, the milestone's central relation held in two of six arrangements. Defect 7 records the
measurement and the domain the claim now carries.

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

## Defect 7 — the claim's domain was never measured, and it is bounded — **DISCLOSED, NOT REPAIRED**

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

Eight defects, in two distinct families.

Three were in the **instrument** — defects 1, 2 and 3 — and all three would have made a
qualification report a false refutation. Two were in the **record** — defect 6 and the inert
parameter recorded beneath it — and would have made the evidence describe a world other than the
one that ran. Three were in the **selection** — defects 4, 5 and 8 — and those are the expensive
kind: an instrument defect costs a run, a selection defect costs the claim.

Seven are repaired. The eighth, defect 7, is not a defect that can be repaired at this scale, and
that is the finding this audit exists for.

**The pattern worth naming.** Defect 4 was the capability tie at S1; defect 5 was the same rule
missing at S0; both are amendment A4, which this project paid for one milestone earlier. Defect 1
was amendment A2. Defect 3 was amendment A1's family. Four of eight are regressions of amendments
already bought and recorded. The amendments were written down and were not carried forward into
new code — which suggests the register is doing less work than it looks like it is doing, and that
the next milestone should assume it will forget them too.

**What defect 7 changes about the milestone.** The central result was measured in one arrangement
of the authored world and read as a property of the mechanism. It is a property of the mechanism
*and* of the arrangement. In two of six arrangements the enabling relation does not hold at all,
and no amount of repair to this selection rule recovers them, because the enabling repair is
outranked by the repair it enables and a greedy rule cannot reach downward. The claim now carries
its domain, and the boundary is pinned by a test asserting a negative.

That is a smaller milestone than the one the mechanism appeared to support a day ago. It is also
the first version of it that a reader can check rather than trust.

What remains before a protocol is still the ordinary apparatus — a random-target arm, a
more-budget arm, a qualification pool drawn from outside this world with every hidden case
verified by construction, and a checker that recomputes rather than reads — with one addition
defect 7 forces: **a world-arrangement arm**, so the domain is measured by the run rather than
asserted by this document.
