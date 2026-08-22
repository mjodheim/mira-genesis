# M095 — improvement enabling improvement

**Status: mechanism built and demonstrated. Nothing is frozen, no hypothesis is registered, no
protocol exists, and no run has been armed.** Freezing a protocol and arming its evaluation are
the project owner's acts. This document records what exists and what it measures, so the decision
is made against evidence rather than a proposal.

## The question

M094 established that a lineage can locate the component limiting it and build the repair. The
question one step along, and the one the project is actually for:

> does an adopted repair change what the lineage can **reach**?

Not "can it repair twice". Two repairs in sequence prove a sequence. The claim worth making is
that the second was *unreachable* before the first and reachable after it, with nothing changed
in between but the adoption.

## The shape

```
S0 --(A, chosen by the diagnosis)--> S1 --(B, chosen by the diagnosis)--> S2

control:         from S0, target B directly and exhaust the operation set   -> nothing
counterfactual:  every S0 repair except A, target B again, same set, bound  -> nothing
```

## What was measured

Run by `metamorphosis/m095_chain.run`, pinned by `tests/test_m095_chain.py`:

| | examined | survivors | confirmed by execution | reached |
|---|---|---|---|---|
| **B from S0** — the control, run first | 191 | **0** | 0 | **no** |
| A from S0 | 191 | 3 | 3 | yes |
| **B from S1, nested operation withheld** | 191 | **0** | 0 | **no** |
| **B from S1** | 239 | 12 | **12** | **yes** |
| **B without A** — the counterfactual | 191 | **0** | 0 | **no** |

Every reached repair is confirmed by *running* it. `experiments/M095/DESIGN_AUDIT.md` records why
that column exists: the search had been accepting candidates on the structural predicate alone,
which is the defect M094's amendment A2 repaired one milestone earlier.

The repairs:

```python
Reading.as_mapping()  ->  {'reading_id': self.reading_id, 'unit': self.unit}
Sample.as_mapping()   ->  {'reading': self.reading.as_mapping()}
```

B calls the method A created. The dependency is in the code, not only in the timing.

## Why this is an enabling claim and not a sequence

**The control runs before the chain**, on untouched S0, so nothing about it can be informed by
what the chain later found. It exhausts the same operation set under the same bound and reports
*why* it failed: `include=reading<-render(reading)` is offered and cannot apply.

**The counterfactual removes A and keeps everything else.** It replays the S0 round into a
separate world, skipping only the repair that made the nested operation applicable, and then
asks again. In the declared world A is the sole tied repair, so nothing is replayed and it
examines exactly as many compositions as the control did — 191. Where several capabilities
tie at S0 the distinction bites: the other repair is kept, only A is dropped, and B is still
unreachable at 143 examined.

It used to leave that world untouched, which made it byte-identical to the state the control
had already searched — the control run a second time, presented as a fourth independent
pillar. `DESIGN_AUDIT.md` defect 16.

**The search space grows, 191 → 239.** At S0 the nested operation prunes every branch it touches,
so those compositions are never grown. At S1 it applies and they are. The reach change has a
number attached, not just a boolean.

## The one mechanism this rests on

`m095_reach.IncludeRenderedField` binds a key to a field that is itself a value object, by calling
that object's own renderer. Whether it *applies* is read from the inner class's syntax tree when
the operation is asked — not set by anyone, and not remembered from an adoption.

**The operation set is identical at S0 and S1.** Nothing is added between the states. A test pins
that, because it is the whole distinction: if M095 worked by handing the lineage a new operation at
S1 it would demonstrate a larger *language*, which is M096's question, not a larger *reach*.

Two properties keep it honest, both tested:

- **reach is a property of the state, not of the history.** A class that always had a renderer
  enables the operation just as well as one the lineage repaired. Otherwise the control would be
  bookkeeping rather than a measurement.
- **half a repair is not a repair.** A renderer that does not cover what the call sites wrote
  enables nothing.

## What is authored, and disclosed

- **The world.** Two value objects, one nested in the other, and call sites that destructure both
  by hand. `mira_core` does not present this demand — `AgentResult` holds an `Observation`, but its
  callers reach *through* it into `.state` rather than rendering it, so the demand would have had
  to be planted. Planting the demand the diagnosis then discovers is the defect M094's design audit
  spent twelve findings removing; a disclosed authored world is the honest alternative.
- **The operation set and the capability shapes**, exactly as M094 disclosed its own. They are the
  next ceiling.
- **The ordering pressure.** `Reading` has three callers and `Sample` two, so `Reading` measures the
  greater demand and is selected first. That is the only thing the world arranges, and it arranges
  it by giving `Reading` more callers rather than by ranking anything.

  **The result used to depend on it.** That was disclosed as an arrangement and never measured
  as a dependency until `DESIGN_AUDIT.md` defect 7 varied it — and it turned out to decide
  whether the milestone demonstrated anything at all. It no longer does: the lineage descends
  to the enabler its own failed search names, so the ordering sets which repair happens first
  and not whether the relation holds. See "The domain of the claim" below.

What is **not** authored: which target the diagnosis selects at either step, what either repair
contains, or whether the second is reachable. All three are measured, and the third is the
milestone.

## What this does not claim

- The lineage does not invent the operation, extend its language, or acquire a capability it
  lacked. That is M096.
- Nothing here is persistent across process death or restart. That is M097.
- No AGI, no recursive self-improvement, no open-ended evolution. One repair enabling one other
  repair, in an authored world, with the language fixed.

## Before this could be run as science

1. **A hypothesis and a protocol**, frozen before any qualification data exists, with conditions
   that can each fail and a falsifier list. M094's is the model.
2. **A qualification pool** drawn from outside the development world, materialised after adoption
   from the adopted mechanism's digest — and, learning from M094's amendment A1, with every hidden
   case verified by construction before the pool is frozen.
3. **Arms**: the withheld-operation arm is part of the chain, and the random-target,
   more-budget and world-arrangement arms are built in `metamorphosis/m095_arms.py` — see
   "The domain of the claim" and the arm table below. Three report `satisfied`; the
   random-target arm reports `unrunnable`, because this world contains no rival that could
   test it.
4. **A decisive checker** that recomputes rather than reads, in the shape
   `scripts/check_m094_result.py` now has.

## The claim is conjunctive, and says so

An earlier draft of this document ended by noting that the counterfactual removes A but not the
*operation*, so a reader could ask whether the enabling was A's or the operation's. That arm is now
built and run: at S1, with A adopted, the nested operation is withheld and B is unreachable again —
191 examined, 0 survivors, the same count as the control.

So neither suffices alone:

| | operation available | operation withheld |
|---|---|---|
| **A adopted (S1)** | B reachable — 12 survivors | B unreachable |
| **A absent (S0)** | B unreachable | B unreachable |

**A is necessary; the operation is the vehicle.** That is a smaller and more accurate statement
than "A enabled B", and it is the one the evidence supports.

> **The right-hand column is true by construction, not by measurement.**
> `IncludeRenderedField` is the only operation in the set that can satisfy
> `RenderNestedValueObject`, so withholding it makes the shape unsatisfiable whatever the
> state. Measured in the most favourable case available — a world whose inner class already
> renders itself, so nothing is missing but the operation — the withheld search still reaches
> nothing: 191 examined against 239 with it present.
>
> The withheld arm therefore records that the operation is the vehicle, which is true, but it
> is **not a control that could have come out the other way**. The left-hand column is the
> measured half of the table. `DESIGN_AUDIT.md` defect 19.

## The domain of the claim

The chain was measured in one arrangement of the authored world and the result was read as a
property of the mechanism. It is a property of the mechanism **and** of the arrangement.

| inner callers | outer callers | regime | enabling demonstrated |
|---|---|---|---|
| 3 | 2 | inner>outer — the declared world | yes |
| 4 | 2 | inner>outer | yes |
| 2 | 2 | inner==outer | yes |
| 3 | 3 | inner==outer | yes |
| 2 | 3 | inner<outer | **no** |
| 1 | 3 | inner<outer | **no** |

The `inner==outer` rows only hold because amendment A4's rule now applies at S0 as well as at S1;
before that repair the relation held in two of six arrangements rather than four.

The `inner<outer` rows were recorded as a **boundary the milestone had to carry**: when the outer
class has more call sites, the repair that would enable B carries less demand than B itself, so the
measure never ranks it first and the greedy rule never reaches it. The search stalled with B unmet
and an untried repair below it that would have unblocked it.

**It is not a boundary.** A failed search already names its own obstacle — the operation it could
not apply — and that operation knows which class must supply which rendering. So the lineage asks
the failure what would unblock it and repairs that, even though the measure does not rank it.
Nothing is added to the operation set: the same operations are offered in the same states, and only
which target is attempted changes. That distinction is what keeps this inside M095 rather than
M096, which is about a larger *language*.

| inner callers | outer callers | regime | before the descent | now | ranking needed help |
|---|---|---|---|---|---|
| 2 | 1 | inner>outer | yes | yes | no |
| 3 | 2 | inner>outer — the declared world | yes | yes | no |
| 1 | 1 | inner==outer | yes | yes | no |
| 2 | 2 | inner==outer | yes | yes | no |
| 1 | 2 | inner<outer | **no** | **yes** | **yes** |
| 1 | 3 | inner<outer | **no** | **yes** | **yes** |
| 0 | 1 | the inner class is never rendered | no | no | — |
| 0 | 3 | the same, larger outer demand | no | no | — |

**The last column separates two results the count would otherwise conflate.** In four
arrangements the diagnosis's own ranking produces the enabling order *unaided* — A is selected by
demand and happens to enable B, and that coincidence is the interesting part. In two the descent
selects A **because** it enables B. Both measure the same relation, with the same control and the
same counterfactual; only the second says something weaker about the ranking. The arm records
`demonstrated: 6` and `demonstrated_without_descending: 4` rather than one number.

So the claim keeps a domain, but a smaller and more natural one — about **existence** rather than
rank:

> An adopted repair changes what the lineage can reach, **wherever there is an enabling repair for
> it to find.**

And a second, narrower claim sits inside it, which is the one the milestone originally made and
which the descent does not widen:

> Where the enabling repair also carries the greatest unmet demand, the diagnosis's **own ranking**
> produces the enabling order without being told — four of the eight arrangements, including the
> declared world.

If the inner class is never rendered directly it presents no demand of its own, so there is no
insufficiency to descend to; reading the obstacle does not help when the remedy is not something
the diagnosis can see. The arrangement arm sweeps two such points, so it still has arrangements
that must come out negative.

M086-C's failure named the selection rule as the thing that failed and recorded making selection
mutable as a candidate successor. This is a narrow instance of that: the rule still ranks by
demand, and only consults the obstacle when the ranking has run out.

## The selection blocker, and how often it came back

The first audit pass found four defects. The last of them was the one that mattered most: at S1
two capabilities on `Sample` tie at demand 2, and the one repaired was decided by alphabetical
order on the capability name. Had the tie fallen the other way, the lineage would have repaired
the plain renderer and **no enabling would have been demonstrated**.

> **It was declared settled here twice before it was.** The same defect — amendment A4's, a tie
> broken by a name — was found three times in this milestone: at S1 (defect 4), then missing
> entirely at S0 (defect 5), then still deciding the domain through the order of the S0 loop
> (defect 10). Each time this section was updated to say it was resolved. What finally settled
> it is not another argument but a test that **permutes every tie and requires the whole sweep
> unchanged**, because A4's own premise is that tied members carry no information about order.
> The fourth-pass snapshot recorded sixteen defects, fifteen repaired. The current audit records
> thirty-one across seven passes, thirty repaired; defect 19 remains disclosed rather than
> repaired.

Amendment A4's rule applies at the capability level as it does at the class level: every capability
the measure ranks equal first is repaired. At S1 the lineage now repairs both — `as_mapping` for the
nested requirement, `as_dict` for the plain one — and **nothing is left unmet at S2**. The tie and
the ordering are unchanged; neither is load-bearing.

A name the class already defines is no longer available, which is what makes two repairs on one
class safe: without it the second would have been called `as_mapping` and shadowed the first.

Three arms are now built, in `metamorphosis/m095_arms.py`, each reporting M094's three-valued
outcome so an instrument failure cannot be read as a refutation:

| arm | asks | measured |
|---|---|---|
| **world arrangement** | does the recorded domain match the measured one? | `satisfied` — six points, every regime with a minimal and a larger witness |
| **random target** | does repairing something the diagnosis *rejected* also unlock B? | **`unrunnable`** — see below |
| **more budget** | is B unreachable, or only deeper than the bound? | `satisfied` — nothing reached at any bound 1–13, the search closes at 4, and the same searcher reaches B at S1 |

None of their numbers is chosen. The arrangement points are the minimal witness of each regime
plus a larger one; the rival set is exhausted rather than sampled, so no seed is needed; and the
budget ceiling is the size of the offered operation set, which bounds composition length by
construction because no operation applies twice.

**The random-target arm reports `unrunnable`, and that is the honest verdict.** B becomes
reachable only when the *inner* class supplies a renderer, every repair is inserted into its
own target's class, and the sole eligible rival targets the outer one — so its pass was decided
before it ran. It said `satisfied` until an adversarial pass killed the mechanism underneath it
and watched it keep saying so. What this world can support is: it contains no rival capable of
testing the claim. Making the arm informative needs a second insufficiency on the inner class,
which is a different world rather than a different check. The arm does have teeth against a
*mis-selecting* diagnosis: rank the outer class first and it reports `refuted`.

The other two arms each needed a positive control before they could fail. `DESIGN_AUDIT.md`
defects 10 to 13 carry the arithmetic.

What remains before a freeze: a qualification pool drawn from outside this world with every hidden
case verified by construction, a checker that recomputes rather than reads, a runner, and a
protocol. Freezing it and arming a run are the owner's acts, not an agent's.

Seven adversarial passes have now recorded thirty-one defects; thirty are repaired and defect
19 remains disclosed because making its withheld-operation arm falsifiable would require inventing
a second operation for the sake of a control. The sixth pass found seven further defects in method
selection, nested-demand attribution, the evidence record, tied-round completeness and the
random-target arm's subject. `DESIGN_AUDIT.md` preserves each counterexample and its regression
test. Five of the first nineteen defects were regressions of amendments the project had already
paid for and written down, which is evidence that recording an amendment does not, by itself,
carry it into the next milestone's code.
