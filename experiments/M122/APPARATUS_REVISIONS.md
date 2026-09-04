# M122 apparatus revisions

M117 disclosed five apparatus revisions, some of which followed real endpoint observations, and
recorded that it could not claim its route selection was prospectively clean. That disclosure is
the precedent this file follows. A revision made after seeing a result is not automatically
illegitimate, but it is never invisible.

Every revision below happened **before any scientific freeze, before any qualifying generation and
before any carrier bank existed**. None of them touches a threshold, a minimum, a guard, a decision
rule or the scientific proposition.

---

## Revision 1 — the stress size is derived instead of inherited

**Date:** 4 September 2026
**Authorised by:** Anthony Mets, who chose this over closing the milestone
**Triggered by:** readiness attempt 3, which produced a conforming stress completion of 13,118
tokens against an inherited 32,000-token threshold

### What was wrong

`m122_stress_schema` carried `STATIONS = 24`, inherited from M120. That number came across while
the schema underneath it was being flattened from eight array-of-object levels to five — and a
shallower station serialises smaller. Twenty-four of them produced a **conforming** completion,
`finish_reason: stop`, of 13,118 tokens. The gate failed on a size nobody had re-checked after the
flattening.

The route did nothing wrong. It emitted a valid completion and stopped because the schema asked for
less than the threshold required.

### The deeper mistake

Neither M120's stress nor M122's first version was ever sized against **what the qualifying
generation will actually demand**. Both inherited a constant. A capacity stress whose size is
unrelated to the capacity the experiment needs is measuring an arbitrary number.

### What changed

`STATIONS` is now derived:

| input | value | source |
|---|---|---|
| observed tokens per station | 546.6 | attempt 3: 13,118 tokens over 24 stations, this route |
| contract ceiling | 29,520 tokens | 48 machines at the contract's ceiling, measured over devkit draws |
| inherited threshold | 32,000 tokens | M118's, **unchanged** |
| safety margin | 1.25 | applied to the larger of the two |
| **derived stations** | **74** | expected ~40,447 tokens |

### What deliberately did not change

- **The 32,000-token threshold is untouched.** A threshold rewritten to fit a stress would be
  tuning the gate to pass itself, which is the whole failure mode this record exists to prevent.
- The stress schema's *shape* is unchanged: still five array-of-object levels, still dominating the
  candidate census, still a non-carrier domain.
- No probe, no verdict ladder, no feature class, no retry rule.

### Why this is a fix and not tuning

The revision makes the stress harder, not easier, and ties its size to an external quantity — what
the generation will ask for — rather than to whether the gate passes. Had the derivation been done
first, it would have produced 74 regardless of any observed outcome.

What cannot be claimed is that the *need* for the derivation was noticed prospectively. It was not.
It was noticed because a run failed, and that is why this entry exists.

### Cost

Attempt 3 spent 22 DEVELOPMENT requests and consumed the second of three delivery attempts. The
verdict it recorded, `not_ready_delivery`, is archived and not deleted.

---

## Standing rule

The readiness gate remains single-use for every verdict except `not_ready_delivery`, and that
exception remains bounded and counted from the attempt archive. A revision to the apparatus does
not silently reset that bound: `experiments/M122/DELIVERY_ALLOWANCE.json` records each reset, who
authorised it and when.
