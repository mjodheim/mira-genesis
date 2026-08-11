# M086 evolvable improvement mechanism

**FROZEN BEFORE IMPLEMENTING THE HARNESS, THE MECHANISM OR THE TASK BANK.**

## The line this attacks

Every result in this repository improves a *body* or a *policy* through a procedure we wrote and
froze. M046 searched candidates we enumerated. M047 patched modules through templates we listed.
M084 adopted one transformation we specified in advance. The lineage has never changed the thing that
changes it.

M047 is where that frozen thing is most explicit, and one line names it:

```python
@property
def sufficient(self) -> bool:
    return self.module is not None
```

`ModuleDiagnosis.sufficient` is true exactly when **one** module is at fault. When the evidence
implicates two, `diagnose_limiting_module` returns `ModuleDiagnosis(None, 'public evidence does not
isolate one safely patchable module')`, the engine returns `INSUFFICIENT_DIAGNOSIS`, and no candidate
is generated at all. `_candidate_sources` then dispatches on that single module through a hand-written
`if/elif` chain over five module names with fixed option lists.

This is not a budget limit. It is a **hypothesis representation** that cannot express a multi-module
fault, and a generator whose image therefore contains no multi-module patch. M047's own protocol
records the consequence: it faced a compound `maximum` task "requiring simultaneous interpreter,
selection and new-tool changes beyond the one-boundary proposal surface" and terminated for
insufficient evidence.

That termination was correct behaviour and a good result. It is also a standing admission that the
lineage's ceiling is our assumption, not its evidence.

**H32:** a lineage permitted to modify the mechanism that turns evidence into candidate
transformations will, after meeting a limitation that mechanism cannot express, construct and adopt a
validated modification of it; and on a later independently frozen problem the modified mechanism will
generate a corrective transformation lying **outside the constructive image** of the original
mechanism, producing a correct outcome that the same lineage with a frozen mechanism does not reach
under any budget.

## What becomes mutable, and what does not

The mutable artifact is the **improvement mechanism**: a serialized pair of

- a **hypothesis schema** — what a diagnosis is allowed to say;
- a **rule set** — guarded expansions from a diagnosis to candidate bodies.

It is executed by a fixed interpreter. The interpreter is not mutable, in the same way a CPU is not
part of the program it runs; what the lineage rewrites is the rule set and the schema, and the next
cycle really executes the rewritten version.

**M0 is behaviourally equivalent to M047's frozen mechanism.** A differential regression drives both
M0 and `diagnose_limiting_module` + `_candidate_sources` over the same evidence and requires identical
diagnoses and identical candidate sets. Without that, "we made the mechanism mutable" would be a claim
about a new mechanism we happened to write, not about the one the repository actually froze.

The following stay outside the mutable body, and a structural checker enforces it:

- the evaluator, its hidden cases and its threshold;
- the sandbox and the disposability rules;
- the transaction, checkpoint and rollback machinery;
- the task bank and the holdout.

Mira may propose a better way to improve itself. It may not edit the test that decides whether the
improvement worked, during the experiment that decides it. An evolvable evaluator is a different
milestone with its own external authority, and it is not this one.

## Avoiding a deferred human plan

The trap is a frozen generator that already contains "when you meet a compound fault, compose". Then
nothing is discovered; our plan simply executes late.

The protocol therefore separates four things, and the checker verifies the separation:

1. **Meta-primitives** — declared, bounded operations *over* a mechanism: `widen_hypothesis`,
   `compose_expansions`, `parameterize_constant`, `relax_guard`. These are authored, exactly as
   M046's transformation language and M047's templates are authored.
2. **The meta-transformation actually built** — a specific composition of primitives applied to a
   specific rule set. This is not enumerated anywhere in advance.
3. **Information available before the limitation** — the body, the public cases, the mechanism, the
   causal memory. Not the holdout, not the hidden cases, not which primitive works.
4. **What the lineage selects causally** — by running each candidate mechanism on a disposable
   descendant against the development limitation and keeping what validates.

No rule anywhere maps "multi-stage evidence" to "use composition". The lineage tries its primitives
and finds out. A regression asserts that no such mapping exists in the source, and that removing any
single primitive changes which mechanisms are reachable rather than being cosmetic.

## The two problems

**Development limitation** — a task whose public failure evidence implicates two modules. M0 returns
no diagnosis and generates nothing. This is where the meta-search runs.

**Holdout** — the compound `maximum` family: simultaneous interpretation, selection and new-tool
change. Frozen independently, materialized only after the meta-transformation is committed, and never
visible to the meta-search.

The holdout is not merely harder. The required patch is **provably outside M0's constructive image**:
the protocol requires the harness to enumerate every candidate M0 can emit for the holdout evidence
and record that the correct one is absent. `fixed_meta` therefore fails for a structural reason, and
the result reports that enumeration rather than asserting it.

## Arms

| Arm | What it removes | Predicted |
|---|---|---|
| `evolvable_meta` | nothing | adopts a mechanism change, then solves the holdout |
| `fixed_meta` | the mechanism cannot be modified | cannot express the holdout patch under any budget |
| `meta_acquisition_ablated` | the adopted mechanism change is stripped before the holdout; identity, body, memory and journal kept | separates lineage continuity from the meta acquisition |
| `task_only_mutable` | body patches allowed, mechanism frozen | shows the holdout is not solved by more ordinary patching |

`fixed_meta` is the primary control and is the same ablation HyperAgents runs against itself.
`task_only_mutable` exists because otherwise a positive result could be explained by the evolvable arm
simply making more body changes.

Every arm receives the same identity, the same starting body, the same observations, the same budget
and the same primitives.

## Success is correctness, from an independent evaluator

M084's ablation cost efficiency and not capability, and its own status file says a claim resting on
that would be weak. M086's primary outcome is whether the holdout is **solved**: the adopted body must
pass the evaluator's hidden cases, executed in a disposable sandbox, scored from behaviour and never
from the lineage's report.

Step and candidate counts are recorded and are **not** decisive.

## Positive threshold

All of the following, on the first materialized bank, no retry:

- **P1** `evolvable_meta` adopts exactly one validated mechanism modification, with the rejected
  alternatives recorded.
- **P2** `evolvable_meta` solves the holdout: hidden cases pass under the evaluator.
- **P3** `fixed_meta` does **not** solve the holdout, and the enumeration of M0's complete candidate
  image for the holdout evidence contains no passing candidate.
- **P4** `meta_acquisition_ablated` does not solve the holdout.
- **P5** `task_only_mutable` does not solve the holdout.
- **P6** the adopted mechanism is *used*: the holdout patch that succeeds is generated by a rule that
  did not exist in M0, and the harness records which.
- **P7** the causal chain is serialized and audited end to end: limitation → hypothesis →
  meta-transformation → experiment → outcome → adoption → the later transformation it made possible.
- **P8** exact rollback: a forced fault during meta-adoption restores a byte-identical prior
  mechanism, compared against an independently recorded digest.
- **P9** no holdout leakage: a structural checker finds no path from the evaluator or the holdout into
  the meta-search.
- **P10** M0 is differentially equivalent to M047's frozen mechanism.

## Failure classification

**Negative** — any of P1–P10 false. In particular, `fixed_meta` solving the holdout would refute the
capability claim outright, and would be the most informative outcome available.

**Inconclusive** — the sandbox cannot run; not runnable is not negative.

## What a negative would teach

1. **the limitation was expressible after all** — M0's image contains the patch and our reading of
   `sufficient` was wrong;
2. **the meta-primitives are the new frozen ceiling** — nothing reachable from them validates, which
   moves the human assumption up one level rather than removing it;
3. **the adopted change is inert** — adopted but the later success does not use it, so plasticity
   changed form without changing capability;
4. **the ablation leaks** — `meta_acquisition_ablated` solves it too, meaning the body or memory
   carried what we attributed to the mechanism;
5. **selection was ours, not the lineage's** — the primitive that works is the only one that could
   ever have worked, making the search a disguised lookup.

Outcome 5 is the one this protocol is most concerned with, and the reason the primitive set contains
alternatives that are individually plausible and individually insufficient.

## Attribution

Track A. No foundation model is called, no network is opened. The comparison in
`docs/HYPERAGENTS_COMPARISON.md` records why HyperAgents' method cannot be imported: their
modifications are written by a frontier model, so under this repository's attribution rule that
competence belongs to the composed system. M086 takes their question and refuses their method.

## Claim boundary

A positive result would establish, in one bounded project-authored construction, that the mechanism
producing future transformations became itself an object of endogenous transformation, and that this
meta acquisition was causally necessary to a later capability.

It would **not** establish AGI, open-ended evolution, arbitrary self-improvement, general
autonomy, or any gate: not G4, G6 or G7. It does not replace M085, does not touch M085's fail-closed
boundary, and is not an independent reproduction of anything. The bodies, tasks, primitives and
evaluator are all project-authored, and the mechanism after M086 remains frozen in every respect the
meta-primitives do not reach — which the result must enumerate.

No archive, no population, no parent selection, no transfer, no migration. If the result shows an
archive is the next real limitation, that is a candidate M087 and is not to be added afterwards to
rescue this one.

## Authority

The improved mechanism gains no authority. It may not touch the repository, credentials, the network,
deployment, production, the evaluator or the scientific gates. Adoption into the official project
remains a separately authenticated human decision.
