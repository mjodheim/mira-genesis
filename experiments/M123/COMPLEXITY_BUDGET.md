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

Three. The first was itself replaced after attempt 1 failed.

1. **The stress size is bounded by an envelope of observed rates. No model is fitted.**
   *Closes:* every sizing before this one assumed the token yield per station follows some law.
   M122 assumed it is constant and missed the threshold by 3.3%. M123's first attempt fitted a line
   to two points, predicted 64,137 tokens at 167 stations, and the route produced at least 100,657
   and truncated. Three rates are now known — 546.6, 418.3 and >=602.7 — and they go down and then
   up. **The relationship is not identified by three points, so nothing is fitted to them.** The
   size must sit inside the admissible window under every rate ever observed, and it is the
   computed midpoint of that window.

2. **An unanswered probe is no longer scored as an unenforced feature class.**
   *Closes:* `conforms` is false for an HTTP 429 exactly as it is for a completion the schema
   refuses, so M120 and M122 both listed classes as unenforced when their probes had only ever been
   rate-limited. The verdict ladder checked delivery first, so the headline stayed right — but a
   reader trusting the field would conclude the route lacks a capability nobody measured.
   **This one is no longer a proposal:** attempt 1 recorded two rate-limited probes in
   `feature_classes_never_answered` and left `unenforced_feature_classes` empty, which is the
   record M120 and M122 would both have got wrong.

3. **The delivery ceiling counts across milestones, not only within one.**
   *Closes:* M122 wrote the ceiling as "across every instrument" and globbed its own directory, so
   opening a successor reset the bound that exists to survive apparatus revisions.

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
| Stress observations behind the sizing | 0 | 1 | **3, one censored** |
| Model fitted to them | — | proportional | **none** |
| Stress stations | 24 | 74 | 167 -> **109** |
| Stress outcome | — | 30,957, short by 3.3% | 100,657, truncated -> *pending* |

The instrument lost a re-authored contract, lost its model entirely, and gained a third data point
that falsified the second. Nothing else moved.

### The sizing rule now in force

    floor    > 32,000 tokens at the lowest observed rate (418.3)    ->  >= 77 stations
    ceiling  < 85,000 tokens at the highest observed rate (602.7)   ->  <= 141 stations
    chosen   the computed midpoint of [77, 141]                     ->  109 stations

`85,000` is a conservative choice roughly 15.6% below `100,657`, which is itself **a truncation
that was observed and not a ceiling that is known**. The highest observed rate comes from that same
truncated run, so it is a lower bound: the real worst case can exceed the worst case this rule can
see, and the operational margin exists to cover what the envelope cannot.

## Order of operations

Unchanged from M122 and for the same reason: the readiness gate runs **before** the rest of the
apparatus is written. M120 built everything and then learned its contract was unserviceable. If
this gate fails, almost nothing is wasted.
