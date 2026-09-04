# M123 / H68 — outcome

**Verdict:** `not_ready_stress`, recorded 4 September 2026.
**Status:** **closed.** Terminal on first occurrence, per the rule this milestone inherited and did
not weaken.
**H68:** **UNTESTED.** Not supported, not refuted, not converted into a negative result.

No carrier bank was built. No qualifying invocation was spent. No generality gate moved.

## What the run measured

Attempt 2, plan `3838ad85…`, 109 stations, 10 requests, no retries needed.

| | |
|---|---|
| Probes answered | **9 of 9**, every one HTTP 200, `finish_reason: stop`, schema conforming |
| Requests carrying no completion | **0** |
| Identity | held on every request |
| Unenforced feature classes | none |
| Enforcement failed open | none |
| Combined probe | conformed |
| Reasoning | as intended |
| **Stress** | HTTP 200, **50,232 completion tokens**, `finish_reason: null`, **content did not validate** |

## The sizing rule was correct, and it is not what closed this

This is the part worth carrying forward, because it is the one thing three milestones had been
getting wrong and this one got right.

| | |
|---|---|
| Predicted band at 109 stations | 45,598 – 65,698 tokens |
| Observed | **50,232** |
| Implied rate | 460.8 per station |
| Envelope the rule was built from | 418.3 – 602.7 per station |
| Inherited threshold | cleared by 57% |
| Operational ceiling | 41% of headroom unused |

The empirical rate envelope made an out-of-sample prediction and the route landed inside it. The
two-point linear fit that preceded it had failed the same test by at least 57% in the other
direction. **Sizing by the envelope of observed rates is the method that survived**, and a
successor should inherit it rather than re-derive one.

## What actually closed it

The response arrived with HTTP 200, 50,232 tokens of content, **no `finish_reason` at all**, and a
body that does not validate against the stress schema. That is consistent with an object that was
never closed — a truncation that did not report itself as one.

`holds` requires HTTP 200 **and** `finish_reason == "stop"` **and** conformance **and** tokens over
the bar. Three of the four were satisfied. The verdict ladder reaches `not_ready_stress`, which is
terminal.

### The disclosed defect, stated as a requirement for a successor and not repaired here

**A response that answers malformed is scored as a stress failure, which is terminal, when it is
arguably a delivery failure, which is not.**

This is the same class of defect an adversarial panel found in this instrument hours earlier, and
which was fixed before this run: a run in which *nothing* answered was being scored
`not_ready_identity` — terminal — instead of `not_ready_delivery`. That fix covered the case where
the route returns no completion. **It did not cover the case where the route returns a completion
that is incomplete.** The panel's own finding recorded that `holds` is strict on `finish_reason`;
the possibility that the field could be *absent* rather than `"stop"` or `"length"` was read and
not acted upon.

A successor must decide, **prospectively and before any request is sent**, whether a 200 carrying
content with no `finish_reason` and unparseable JSON is a delivery outcome or a scientific one. It
is not decided here, and this verdict is not reinterpreted to reach a more convenient answer. The
rule in force when the run was made is the rule that governs it.

## What this milestone did establish

1. **The empirical rate envelope predicts out of sample.** 50,232 against a predicted 45,598–65,698.
2. **The contract inherited from M122 holds under load.** Nine of nine classes enforced on first
   ask, with no retries and no rate limiting, at a larger stress than any previous attempt.
3. **Unanswered is not unenforced.** Attempt 1 recorded two rate-limited probes as never answered
   and left `unenforced_feature_classes` empty; M120 and M122 would both have written a false
   record there.
4. **The delivery ceiling now crosses milestones**, so opening a successor no longer resets a bound
   that exists to survive apparatus revisions.
5. **Total delivery failure is retryable.** An expired credential or a dead network no longer closes
   a milestone permanently on zero measurements.
6. **The schema permits a wider spread than the pass window** — 4.06× against 3.15× at a fixed
   station count. Station count is not the variable that decides the verdict. A successor should
   pin the inner array cardinalities, which leaves the census M122 validated unchanged.

## What it did not establish

Nothing about H68. Nothing about the descendant, the comparator, the attribution cascade or the
diagnostic policy. No statistical test was performed. H59, H60, H62, H63, H64, H65, H67 and now
H68 are all recorded untested.

No external blocker was approached: the human-maintained sealed bank, the independent reproduction
and the external adversarial audit each require a person outside this project.

## Accounting

Attempt 2 is archived as `READINESS_ATTEMPT_02_not_ready_stress.json`, result digest
`23977b29…`. It is **not** a delivery attempt, so it consumes none of the delivery allowance; the
allowance is not the thing that ended this milestone. The verdict is.

Delivery attempts spent across every instrument remain **3 of 6**: M122's two, and M123 attempt 1.

## Owner gates that remain open

Unchanged, and none crossed by this record: **P-024** (M120), **P-025** (M121), a publication review
for **M122** that was never drafted, and **P-026** (M123, drafted). Four milestones of this line are
implemented, merged and public against zero recorded dispositions.
