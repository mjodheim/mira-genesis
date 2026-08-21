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
counterfactual:  rebuild S0, target B again, same set, same bound           -> nothing
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

**The counterfactual rebuilds S0 from scratch** and asks again. It examines exactly as many
compositions as the control did — 191, the same number — and finds nothing. So B was not "always
reachable and reached later". A is what changed it.

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

  **And the result depends on it.** That was disclosed as an arrangement and never measured as a
  dependency until `DESIGN_AUDIT.md` defect 7 varied it. It is not a free parameter: it decides
  whether the milestone demonstrates anything. See "The domain of the claim" below.

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
3. **Arms**: at minimum a random-target arm and a more-budget arm. The arm that adopts A and
   searches for B with the nested operation withheld **is built** — see below.
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

The `inner<outer` rows are a **boundary, not a bug**. When the outer class has more call sites, the
repair that would enable B carries less demand than B itself, so the measure never ranks it first
and the greedy rule never reaches it. The search stalls with B unmet and an untried repair below it
that would have unblocked it. The operation is unchanged and would apply if the inner renderer
existed — what fails is the selection rule, not the mechanism.

So the claim carries its domain:

> An adopted repair changes what the lineage can reach, **in worlds where the enabling repair is
> not outranked by the repair it enables.**

Escaping that boundary means being willing to repair something the measure does not rank first — to
search for an *enabler* rather than for the greatest unmet demand. That is a different question,
and it is close to the one M086-C's failure already posed: a mechanism that generates a correct
candidate and then chooses a wrong one is not helped by generating more.

## The selection blocker, settled

`DESIGN_AUDIT.md` found four defects and all four are repaired. The last was the one that mattered
most: at S1 two capabilities on `Sample` tie at demand 2, and the one repaired was decided by
alphabetical order on the capability name. Had the tie fallen the other way, the lineage would have
repaired the plain renderer and **no enabling would have been demonstrated**.

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
| **random target** | does repairing something the diagnosis *rejected* also unlock B? | `satisfied` — the one repairable rival adopts `as_dict` and leaves B blocked at 143 examined |
| **more budget** | is B unreachable, or only deeper than the bound? | `satisfied` — nothing reached at any bound 1–13; the search closes at 4 |

None of their numbers is chosen. The arrangement points are the minimal witness of each regime
plus a larger one; the rival set is exhausted rather than sampled, so no seed is needed; and the
budget ceiling is the size of the offered operation set, which bounds composition length by
construction because no operation applies twice.

What remains before a freeze: a qualification pool drawn from outside this world with every hidden
case verified by construction, a checker that recomputes rather than reads, a runner, and a
protocol. Freezing it and arming a run are the owner's acts, not an agent's.

Later audit passes have since found five further defects (5 to 9), four repaired and one — the
domain boundary — disclosed above. `DESIGN_AUDIT.md` carries the arithmetic. Two things it says
are not about M095. Four of the nine defects were regressions of amendments this project had
already paid for and written down, which is evidence that recording an amendment does not, by
itself, carry it into the next milestone's code. And two of defect 9's three literals were
written by the commit that repaired defect 8 — asserting a property feels like establishing it,
and it feels that way most strongly while establishing something else.
