# M086-A result — POST-HOC DISQUALIFIED DEVELOPMENT

> **This result is withdrawn as a scientific qualification. H32 is neither confirmed nor refuted by
> it.** The observations below are preserved exactly as recorded and remain diagnostic; the claim
> attached to them does not stand. Four defects are set out in
> [`DISQUALIFICATION.md`](DISQUALIFICATION.md): the recorded protocol commitment binds bytes absent
> from the repository, P8 was never implemented and P7–P10 never reached the verdict, the holdout
> existed before the meta-search, and the replay compared 3 of 14 preserved fields per arm.
>
> Nothing here may be cited as positive qualification, gate evidence or reproduction. The successor
> is **M086-B**, with its own protocol, salt, bank and holdout.

**Original header, preserved:** POSITIVE QUALIFIED DEVELOPMENT RESULT — TRACK A, MODEL-FREE. NO GATE
ADVANCES.

Protocol `8a8a6e7` frozen before any harness. Bank `fa647e27…c2a5` bound before the run. First result
`a0569361…93bd`, attempt 1, no retry, no external model, no network.

## What was frozen, and what the lineage did to it

M047's mechanism is two pieces: `diagnose_limiting_module`, whose `ModuleDiagnosis.sufficient` is
`self.module is not None`, and `_candidate_sources`, dispatching on that one module. A diagnosis is
usable only when **exactly one** module is at fault.

M086 expresses that pair as a serialized schema plus rule set, executed by a fixed interpreter, and
proves the expression faithful: over **10 differential probes on two bodies**, M0 and M047's own
functions return identical diagnoses and identical candidate replacement sets.

Both limitations in this bank pair an unparseable token with an unroutable operation, so the failure
evidence names `{interpretation, execution}` at once. Against that evidence M0 says *"public evidence
does not isolate one safely patchable module"* and emits **zero candidates**.

The lineage then searched its four meta-primitives, ran each on a disposable descendant against the
development limitation, **rejected seven** combinations and adopted one: `widen_hypothesis`. The
mechanism digest moved from `2762e65f…` to `3bdde34e…`, and the next cycles executed the new version.

## The arms

| Arm | Meta adopted | Development solved | Holdout solved (hidden cases) |
|---|---:|---|---|
| `evolvable_meta` | 1 | yes | **yes** |
| `fixed_meta` | 0 | no | no |
| `meta_acquisition_ablated` | 1 | yes | **no** |
| `task_only_mutable` | 0 | no | no |

Everything is matched across arms: identity, starting body, public evidence, primitives and
evaluator. `task_only_mutable` additionally received **three times** the ordinary patching budget and
still solved nothing, so the result is not more body patches.

`meta_acquisition_ablated` is the control that matters most. It ran the meta-search, adopted the same
modification and solved the development limitation — then had that acquisition stripped before the
holdout, its mechanism digest returning to `2762e65f…`. It failed. The difference is the acquisition,
not the lineage's continuity.

## Why the control's failure is structural

The harness enumerates the starting mechanism's **complete constructive image** for the holdout
evidence: **0 candidates**. There is nothing for `fixed_meta` to run, so no budget could change the
outcome. This is a capability difference, established by enumeration rather than inferred from a
score — which is the correction M084's efficiency-only result asked for.

## Success is evaluator-owned

The holdout is scored by executing four hidden cases the mechanism never receives, in a disposable
sandbox, from behaviour. A structural checker verifies that neither module names `HOLDOUT_HIDDEN`,
that the mechanism cannot reach `solves` or the sandbox, and that the meta-search is only ever handed
the development cases. M069 is the recorded precedent for why.

## The finding the design did not predict

**Composition turned out to be unnecessary.** The protocol expected the lock to be the single-module
dispatch and therefore expected a composed patch. It was not: widening the *hypothesis schema* alone
was sufficient, because once the mechanism can name two modules it repairs them across two ordinary
cycles. The successful holdout patch, `synthesize_tool:mean:mean`, is emitted by a rule M0 lists but
could never have fired — M0 refuses to diagnose at all.

Amendment A1, recorded before the bank was bound, re-states P6 as its own sentence already did:
outside M0's constructive image. That the search found the *minimal* sufficient change, rejecting
three of four primitives individually, is evidence against the lookup failure mode rather than for it.

## Construction defects, recorded

Two, both found before anything was bound, both properties of the bank rather than the hypothesis:

- an earlier bank aliased tokens onto routeless operations, so repairing an alias revealed a *new*
  missing route and the greedy tie-break locked in a wrong alias no later cycle could diagnose;
- M047's `render_tool_module` emits `def max(arguments): ... return max(arguments)` for a tool named
  `max`, shadowing the builtin its expression needs and recursing until the sandbox kills it. That is
  a latent defect in a qualified module; it is recorded in `FAILURE_LOG.md` and **not repaired here**,
  because changing that renderer would change M047's synthesized source bytes and its preserved
  digests.

## What is still frozen after M086

The interpreter, the evaluator, the sandbox, the transaction machinery, the task bank — and the
**meta-primitives themselves**. The lineage chose among four operations we wrote. It did not invent a
fifth. The human assumption moved up one level; it did not disappear, and the protocol names that as
the second possible negative precisely so it cannot be quietly forgotten now that the result is
positive.

## CI record (not a qualification)

The suite was green; it did not test any of the four defects. First CI run `31568691093`, attempt 1, no rerun: **1,703 passed, 9 skipped** on Python 3.11 in
1,210.84 s and on Python 3.13 in 1,276.50 s, plus repository integrity. Attribution run
`31568691081` passed. Local suite 1,702 passed / 10 skipped; 29 M086 regressions; checker
`failures: []`.

## Claim boundary

**Withdrawn.** The sentence below is what the attempt claimed; it is not supported, because the
verdict that produced it tested six of the ten frozen conditions and bound a protocol digest no
checkout can reproduce.

> ~~In one bounded, project-authored construction, the mechanism producing future transformations
> became itself an object of endogenous transformation, and that meta acquisition was causally
> necessary to a later capability.~~

Not AGI, not open-ended evolution, not arbitrary self-improvement, not general autonomy. No gate
advances — not G4, G6 or G7. It does not replace M085, does not touch M085's fail-closed boundary and
is not an independent reproduction. No foundation model was called: `docs/HYPERAGENTS_COMPARISON.md`
records why HyperAgents' method, in which a frontier model writes the modification, could not be
imported into Track A.

No archive, no population, no parent selection, no transfer, no migration.
