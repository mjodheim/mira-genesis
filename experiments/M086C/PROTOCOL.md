# M086-C evolvable improvement mechanism — third attempt

**FROZEN BEFORE ANY HARNESS, BANK OR HOLDOUT. COMMIT 1 OF 4.**

M086-A is post-hoc disqualified (D053). M086-B is a preserved negative that did not refute H32: its
salt drew a limitation no mechanism could repair, because the sandbox refuses a synthesized tool whose
name `tool_core` already registers. M086-C is a third, separately numbered experiment with its own
protocol, salt, bank and holdout. Neither predecessor's bank or result is reused as evidence.

**H32 is unchanged** and still untested.

## What the correction actually is

Not a shorter list. Probing M047's frozen templates shows that of the four canonical operations, only
one can be repaired when it is missing a route:

| | |
|---|---|
| `add` | already registered by `tool_core` — a synthesized module collides |
| `mul` | already registered, and no frozen expression computes a product |
| `max` | the synthesized tool shadows the builtin its own expression needs |
| `mean` | repairable |

**`mean` is the only one.** That is a property of the inherited machinery, and it is a finding in its
own right: the frozen mechanism's constructive surface is narrower than its five-branch dispatch
suggests. The routeless operation therefore cannot vary in this grammar, and this protocol says so
rather than pretending to a choice it does not have.

## What is forced, and what is at risk

**Forced.** The premise — public evidence naming two stages at once, which `ModuleDiagnosis.sufficient`
cannot express — and the routeless operation being `mean`. The premise is M047's documented behaviour,
and without it there is nothing to study.

**At risk, and not arranged.** The salt still draws the unknown token, which canonical it means among
those that already have a route, and every operand. The operands carry the real uncertainty: a
`mean a b c` case is passed by the `mean` expression always, and by `midpoint` whenever
`(a + c) / 2 == (a + b + c) / 3`. When both pass the public case, the cycle adopts the first in the
frozen expression order — which is `midpoint` — and the evaluator's hidden cases then decide whether
that generalizes. Nothing in this protocol arranges for it to.

So P2 can fail on a bank where everything else succeeds, and that would be a genuine negative about
whether the repaired mechanism produces a transformation holding beyond the evidence it saw.

The salt was drawn before this document was written, and no outcome for it has been observed.

## Everything else is M086-B's, unchanged

The four corrections the disqualification mandated are inherited exactly: artifacts declared `-text`
in this commit before any digest exists; P1 through P10 each computed, with a single false making the
result negative; a real forced fault during the adoption transaction compared against an independent
pre-adoption record; and the holdout materialized by a separate process, after the adopted mechanism
is committed, with the chronology proved from recorded digests.

Arms, budgets and the meta-primitive set are unchanged. The generic lineage — cycle, meta-search,
faulted adoption, holdout arm and verdict — is imported from M086-B rather than restated, so nothing
M086-B recorded can shift.

## Threshold

P1–P10 exactly as frozen for M086-B. Positive if and only if all ten are true.

## Failure classification

**Negative** — any of P1–P10 false. A holdout repair that does not generalize, a control that
succeeds, or an empty meta-search are each informative and preserved.

**Inconclusive** — the sandbox cannot run.

## Claim boundary

Unchanged. A positive result would establish, in one bounded project-authored construction, that the
mechanism producing future transformations became an object of endogenous transformation and that the
acquisition was causally necessary to a later capability. No gate moves. Not AGI, not open-ended
evolution, not arbitrary self-improvement, not general autonomy, not a reproduction, and no contact
with M085's fail-closed boundary. The meta-primitives remain project-authored.

## Prohibited

Reusing a predecessor's bank or result as evidence; amending this protocol after the bank is
materialized; rerunning a materialized bank; materializing the holdout before the adopted mechanism is
committed; leaving any condition documentary; comparing a restored mechanism against its own
checkpoint; drawing a second salt after seeing this one's outcome.
