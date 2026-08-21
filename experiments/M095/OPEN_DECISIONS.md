# M095 — decisions that are the owner's, with the evidence for each

**Nothing here is decided.** This document exists because the apparatus reached the point where the
remaining questions are scientific judgements rather than engineering, and leaving them implicit in
code would be deciding them by default. Each entry states the question, what has been measured, the
options and what each costs. Freezing a protocol and arming a run remain the owner's acts.

Written 2026-08-21, against `experiments/M095/DESIGN.md` and `DESIGN_AUDIT.md` (nine defects, eight
repaired, one disclosed).

---

## 1. What the qualification pool draws

**The question.** M094 drew its pool from components *outside* the development set — real classes in
the real repository — and asked whether the adopted mechanism repaired them too. M095's claim is not
about components but about a **relation holding in a world**, and its worlds are authored. So the
analogue is not obvious.

**What is measured.** The world-arrangement arm already sweeps one dimension — the two classes'
call-site counts — across all three ordering regimes, and reports `satisfied`. That is a *domain*
measurement, not a qualification: it varies a number, not a structure.

**Options.**

| | what a pool entry is | what it would establish | what it costs |
|---|---|---|---|
| **A** | an authored world varying *structure* — different field names and arities, extra unrelated fields, deeper nesting, a collection in place of a scalar | the enabling relation is not an artifact of this particular two-class shape | authored worlds are still authored; a sceptic can ask who chose the variations |
| **B** | a real class pair from `mira_core` that already holds a value object | the relation appears outside anything written for the milestone | `DESIGN.md` records that `mira_core` does **not** present this demand — `AgentResult` holds an `Observation` but its callers reach *through* it — so the demand would have to be **planted**, which is the defect M094's design audit spent twelve findings removing |
| **C** | no pool; M095 reports as a mechanism demonstration with a measured domain and no qualification | honest about what an authored world can support | M095 never becomes a qualified result, and the lineage's next qualified milestone is deferred |

**The tension.** B is the only option that draws from outside anything authored, and it is the one
the project's own rules forbid. A is defensible but its strength depends entirely on the variation
axes being declared **before** any run and not tuned afterwards. C is the most conservative and may
simply be correct.

**If A is chosen**, amendment A1 binds: every pool world must be verified *by construction* before
the pool is frozen — it must build, present a nested unmet requirement at S0, and have B unreachable
from S0. Worlds failing any of those are excluded **and recorded**, never silently dropped. That
machinery does not exist yet and should not be written until the axes are chosen, because writing it
would choose them.

---

## 2. How the domain is stated in a protocol

**What is measured.** The enabling relation holds where the inner class's call sites are at least as
many as the outer's, and fails where they are fewer — four of six swept arrangements, with each
ordering regime carrying a minimal and a larger witness.

**Two ways to state it.**

- **As regimes.** "The claim holds where `inner_call_sites >= outer_call_sites`." Exactly what was
  measured, trivially checkable, and says nothing about why.
- **As outranking.** "The claim holds in worlds where the enabling repair is not outranked by the
  repair it enables." This is the sentence currently in `DESIGN.md`. It generalises: call-site count
  is *one* way to produce outranking, and the sentence claims the boundary is about the ranking, not
  about that particular cause.

**The risk in the second.** It has not been shown that other causes of outranking behave the same
way, because no other cause was varied. It is the better explanation and the weaker evidence. If it
is used in a protocol, the protocol should say which parts were measured and which are inference.

---

## 3. Is the arrangement arm a verdict condition, or a disclosed sensitivity?

M094 kept `corrected_measure_threshold_sensitivity` as a **preserved snapshot outside the verdict**,
and marked `authored_target_component` as a ceiling arm.

- **Inside the verdict**: the domain becomes falsifiable — if the boundary moves in either direction
  the run fails and the claim must be restated. That is the stronger discipline.
- **Outside, as a disclosed sensitivity**: a boundary that moves *outward* would not fail the run,
  which is arguably right because a wider domain is not a worse result — but it is exactly the
  direction an arm is most likely to be written to ignore, and the arm currently refuses to ignore it.

---

## 4. Register slots

`SCIENTIFIC_HYPOTHESES.md` holds no M095 hypothesis and `DECISIONS.md` ends at D061.

- **H38** and **D062** are reserved by reference for M092, which was aborted without verdict. They
  are cited across six files as unclaimed and should probably stay reserved rather than reused.
- **H39** is M094's; **D063** is M094's decision slot and is **unfilled**.
- **H40** and **D064** are therefore the next free slots for M095.

Registering either is a register act and is not done here.

---

## 5. Should M095 try to escape the boundary?

Where the outer class has more call sites, the repair that would enable B carries *less* demand than
B itself. It is never ranked first, the greedy rule never reaches it, and the search stalls with B
unmet and an untried repair sitting below it that would have unblocked it.

Escaping that means being willing to repair something the measure does not rank first — searching
for an **enabler** rather than for the greatest unmet demand.

- **As part of M095** it would widen the claim to all three regimes, at the cost of changing the
  selection rule the milestone is currently measuring, mid-milestone.
- **As a successor** it is a cleaner question and a larger one. It is close to what M086-C's failure
  already posed: *a mechanism that generates a correct candidate and then chooses a wrong one is not
  helped by generating more.* M086-C named the selection rule as the thing that failed and recorded
  that making selection mutable was a candidate successor, not added there.

Two milestones have now independently arrived at the selection rule as the ceiling. That is worth
weighing against the M096–M098 trajectory as currently sketched.

---

## 6. Whether the narrowed claim is still worth a milestone

Stated plainly, what M095 now supports is: *in an authored two-class world, where the enabling
repair is not outranked by the repair it enables, an adopted repair changes what the lineage can
reach* — with the control, both counterfactuals and three arms all measured, and every reached
repair confirmed by execution.

That is smaller than the milestone appeared to support before the domain was swept. It is also the
first version of it a reader can check rather than trust. Whether it is worth freezing, worth
widening first, or worth recording as a mechanism demonstration and moving on, is the decision the
rest of this document feeds.
