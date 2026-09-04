# M123 complexity budget

Written before the analysis plan, the generator spec, the bank nonce and the tested-system freeze,
and before any H68 observation exists.

M122 closed at `not_ready_stress` with **nine of nine capability probes conforming**. The contract
was not the problem and is not touched. The instrument that measured it was, in exactly one place,
and that is the only place this milestone is permitted to change.

## What may not grow, and this time that includes the contract

Inherited by import and forbidden to change:

| | |
|---|---|
| Arms, endpoint, exact test, α, effect floor, guards, verdicts, decomposition | M119 |
| Comparator and its committed seed | M119 |
| Observation budget, 4000 per demand | M113 |
| Admissibility minimums, 3 qualifying carriers and 3 distinct structures | M115 |
| Fixed route | M118, byte-unchanged |
| Pre-seal adequacy gate and its information boundary | M120 |
| **The carrier contract and its decoder** | **M122, route-validated** |
| **The stress schema's shape** | **M122, route-validated** |

The last two are new to this list and they are the point. M122 established, on the live route, that
this contract's nine capability classes are enforced and that this stress shape conforms.
Re-authoring either to carry a new milestone number would discard the only thing M122 bought and
re-open a question already answered.

## What changes, and the failure each closes

Two. Both come from M122's outcome.

1. **The stress size is fit from two observations instead of extrapolated from one.**
   *Closes:* M122's sizing assumed token yield per station is constant. It is not — 546.6 at 24
   stations, 418.3 at 74 — and the single-point model overshot by 31%, leaving the stress 3.3%
   short of the threshold. A single point is a line through the origin, and this relationship has
   an intercept.

2. **An unanswered probe is no longer scored as an unenforced feature class.**
   *Closes:* `conforms` is false for an HTTP 429 exactly as it is for a completion the schema
   refuses, so M120 and M122 both listed classes as unenforced when their probes had only ever been
   rate-limited. The verdict ladder checked delivery first, so the headline stayed right — but a
   reader trusting the field would conclude the route lacks a capability nobody measured.

## What is refused

- No second route, no fallback, no provider substitution.
- **No change to the 32,000-token threshold.** A threshold rewritten to fit a stress is a gate
  tuned to pass itself. The stress moves; the bar does not.
- No re-running a verdict that is not `not_ready_delivery`.
- No additional arm, no second generation, no redraw, no repair, no resample.
- No repair of M115–M122. Their disclosed defects are requirements here.

## The running count

| | M120 | M122 | M123 |
|---|---|---|---|
| Array-of-object levels asked of the route | 8 | 5 | 5 |
| Capability probes conforming | 7 of 9 | **9 of 9** | inherited |
| Contract re-authored | yes | yes | **no** |
| Stress observations behind the sizing | 0 | 1 | **2** |
| Stress margin above the threshold | — | 1.25× intended, 0.97× actual | 1.5×, with a 25% model allowance |

The instrument lost a re-authored contract and gained a second data point. Nothing else moved.

## Order of operations

Unchanged from M122 and for the same reason: the readiness gate runs **before** the rest of the
apparatus is written. M120 built everything and then learned its contract was unserviceable. If
this gate fails, almost nothing is wasted.
