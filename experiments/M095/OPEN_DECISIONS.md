# M095 — decisions that are the owner's, with the evidence for each

**The owner selected the bounded Option-A qualification on 2026-08-22 and instructed the local work
to proceed.** The selections are recorded beneath the questions rather than replacing their original
reasoning. H40, the protocol and population are frozen locally; the one armed run remains a separate
recorded act.

Written 2026-08-21 against `experiments/M095/DESIGN.md` and `DESIGN_AUDIT.md`, revised after the
fifth pass, and reconciled after the sixth local adversarial pass. The audit now records
**thirty-one defects, thirty repaired**.

**Two entries below have changed since they were written, and are marked.** Section 2 asked how to
state a domain that no longer exists in the form it described; section 5 asked whether escaping a
boundary was worth attempting, and it was attempted and succeeded. Both are kept with their original
reasoning rather than rewritten, because the reasoning is what a later reader needs in order to
judge how much the answers cost.

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

> **Resolved: Option A, exhaustive rather than drawn.** Three declared structures are crossed with
> three arrangements, so all nine entries run and no salt can discard an inconvenient one. The
> preflight builds and parses every S0, measures its demand, verifies absence of renderers and
> exhausts B from S0 without running the chain. The development world itself is excluded.

---

## 2. How the domain is stated in a protocol — **the question changed**

> **Superseded.** The ordering boundary this section is about no longer exists. The lineage now
> descends to the enabler its own failed search names, and the relation holds in six of eight swept
> arrangements — every one where an enabling repair exists to be found. What remains is a boundary
> about **existence**, not rank: an inner class that is never rendered directly presents no demand,
> so there is nothing to descend to. `DESIGN_AUDIT.md` defect 7.
>
> **The live question is now a different one.** Four of the six demonstrate the relation with the
> diagnosis's ranking finding the enabling order *unaided*; two only demonstrate it because the
> descent selected the enabler on purpose. Both measure the same relation with the same control and
> counterfactual, but they say different things about the ranking, and a protocol has to decide
> whether that is:
>
> - **one result with a recorded sub-count** — which is what the arm does today, reporting
>   `demonstrated: 6` and `demonstrated_without_descending: 4`; or
> - **two conditions**, one about the relation and one about the ranking finding it unaided, each
>   able to fail separately.
>
> The second is more honest and more expensive. The first risks a reader taking "six of eight" as
> six instances of the stronger claim.

> **Resolved: two conditions.** H40 scores the enabling relation and ranking autonomy separately.
> Qualification requires six of six demand-bearing structural entries to demonstrate the relation;
> it separately requires the three declared unaided cases and three declared descent cases to retain
> those modes.

The reasoning as originally written follows, and is what the answer had to overcome.

**What was measured.** The enabling relation holds where the inner class's call sites are at least
as many as the outer's, and fails where they are fewer — four of six swept arrangements, with each
ordering regime carrying a minimal and a larger witness.

**Two ways to state it.**

- **As regimes.** "The claim holds where `inner_call_sites >= outer_call_sites`." Exactly what was
  measured, trivially checkable, and says nothing about why.
- **As outranking.** "The claim holds in worlds where the enabling repair is not outranked by the
  repair it enables." It generalises: call-site count is *one* way to produce outranking, and the
  sentence claims the boundary is about the ranking, not about that particular cause.

**The risk in the second.** It had not been shown that other causes of outranking behave the same
way, because no other cause was varied. It was the better explanation and the weaker evidence.

---

## 3. Is the arrangement arm a verdict condition, or a disclosed sensitivity?

M094 kept `corrected_measure_threshold_sensitivity` as a **preserved snapshot outside the verdict**,
and marked `authored_target_component` as a ceiling arm.

- **Inside the verdict**: the domain becomes falsifiable — if the boundary moves in either direction
  the run fails and the claim must be restated. That is the stronger discipline.
- **Outside, as a disclosed sensitivity**: a boundary that moves *outward* would not fail the run,
  which is arguably right because a wider domain is not a worse result — but it is exactly the
  direction an arm is most likely to be written to ignore, and the arm currently refuses to ignore it.

> **Resolved: inside the verdict.** A moved boundary is a finding in either direction. The separate
> random-target arm remains outside the verdict because defect 19 shows that it cannot produce the
> causal rival its name implies.

---

## 4. Register slots

`SCIENTIFIC_HYPOTHESES.md` holds no M095 hypothesis and `DECISIONS.md` ends at D061.

- **H38** and **D062** are reserved by reference for M092, which was aborted without verdict. They
  are cited across six files as unclaimed and should probably stay reserved rather than reused.
- **H39** is M094's; **D063** is M094's decision slot and is **unfilled**.
- **H40** and **D064** are therefore the next free slots for M095.

> **Resolved in part.** H40 is now registered as proposed/unrun. D064 remains reserved and unfilled
> until a checked result exists; accepting or rejecting the result is still the owner's register act.

Registering either is a register act and is not done here.

---

## 5. Should M095 try to escape the boundary? — **answered: it did**

> **Resolved, and cheaply.** This section framed the escape as a choice between widening M095
> mid-milestone and deferring to a successor, and treated it as costly either way. It was neither.
>
> A failed search already names its own obstacle: the operation it could not apply knows which class
> must supply which rendering. The lineage asks the failure what would unblock it and repairs that.
> **Nothing is added to the operation set** — the same operations are offered in the same states,
> and only which target is attempted changes, which is what keeps it inside M095's boundary with
> M096 rather than crossing it.
>
> The cost was one function and one branch. The concern below about "changing the selection rule
> mid-milestone" was real but smaller than it reads: the rule still ranks by demand and only
> consults the obstacle when the ranking has run out.
>
> **What this section got right and should be kept for:** two milestones independently arriving at
> the selection rule as the ceiling. That observation stands, and the descent is a narrow instance
> of it rather than a general answer. M086-C's harder version — choosing well among candidates that
> all fit the public evidence — is untouched.

The reasoning as originally written follows.

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

---

## 6. Whether the narrowed claim is still worth a milestone

Stated plainly, what M095 now supports is: *in an authored two-class world, wherever an enabling
repair exists to be found, an adopted repair changes what the lineage can reach* — with the control,
both counterfactuals and three arms measured, and every reached repair confirmed by execution. In
four of the eight swept arrangements the diagnosis's ranking finds the enabling order unaided; in
two the descent has to select it.

That is smaller than the milestone appeared to support before the domain was swept. It is also the
first version of it a reader can check rather than trust. Whether it is worth freezing, worth
widening first, or worth recording as a mechanism demonstration and moving on, is the decision the
rest of this document feeds.

> **Resolved: qualify the bounded claim before M096.** The qualification does not promote the claim
> beyond its authored structural population and explicitly leaves new-operation acquisition to M096.
