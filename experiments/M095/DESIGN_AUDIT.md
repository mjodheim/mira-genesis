# M095 — design audit, before any protocol

**Nothing is frozen.** This audit was run against the M095 mechanism *before* proposing a
protocol, because that is where M094's four amendments say defects are cheap. It attacks the
mechanism rather than confirming it. It found four defects, all now repaired — three in the
instrument, one in the selection, and the selection one only after being stopped at and settled
deliberately rather than patched in passing.

The attack that mattered most was not clever. It was: *which of M094's lessons has M095 already
forgotten?* Two of the four are regressions of amendments this project paid for one milestone ago.

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

Three of four defects were in the *instrument*, and all three would have made a qualification
report a false refutation. The fourth was in the *selection*, and it was the one that would have
made a positive result depend on an accident. That asymmetry is worth keeping in view: an
instrument defect costs a run, a selection defect costs the claim — which is why the selection one
was stopped at and settled deliberately rather than patched in passing.

All four are now repaired. What remains before a protocol is the ordinary apparatus — a
random-target arm, a more-budget arm, a qualification pool drawn from outside this world with
every hidden case verified by construction, and a checker that recomputes rather than reads.
