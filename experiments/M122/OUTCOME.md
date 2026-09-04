# M122 — closed at the DEVELOPMENT readiness gate; H67 untested

**Date:** 4 September 2026

| | |
|---|---|
| Hypothesis | **H67 — untested** |
| Verdict | `not_ready_stress`, and final |
| Qualifying scientific invocations | **0** |
| Scientific freeze taken | **no** |
| Carrier bank | **none** |
| Reveals | **none** |
| DEVELOPMENT requests spent | 76, across four attempts |
| Generality gate advanced | **none** |

**This is not a result about H67.** No freeze, no bank, no arm, no comparison. The hypothesis is
exactly as open as it was — not a negative result, not weak evidence, and citable as neither.

## The verdict, and what it was not

The stress produced a **conforming** completion: HTTP 200, `finish_reason: stop`, schema valid,
**30,957 tokens** against an inherited threshold of 32,000. Short by 1,043 tokens — **3.3%**.

Everything else was green, and this is the part that matters for a successor:

| probe | HTTP | finish | conforms | tokens |
|---|---|---|---|---|
| `enum` | 200 | stop | yes | 51 |
| `pattern` | 200 | stop | yes | 87 |
| `required` | 200 | stop | yes | 61 |
| `additional_properties` | 200 | stop | yes | 11 |
| `min_items` | 200 | stop | yes | 502 |
| `max_items` | 200 | stop | yes | 11 |
| `nested_arrays` | 200 | stop | yes | 76 |
| `nesting_depth` | 200 | stop | yes | 65 |
| `combined` | 200 | stop | yes | 582 |

**Nine of nine.** Zero enforcement failures. Identity held on every request. Zero requests carried
no completion. Thirteen requests — the cleanest of the four attempts.

## What this run does establish

**The flattened contract is validated against the live route.** Every capability class the M122
candidate schema requires was enforced, including the two that mattered most:

- **`nested_arrays`** — the class that closed M120. At M120's eight array-of-object levels this
  probe free-ran to 101,379 tokens and truncated. At M122's five it conforms in 76.
- **`combined`** — the probe that exercises every class at once, and which no previous run had ever
  reached cleanly. It conformed in 582 tokens.

That evidence stands whatever the verdict says. A successor inheriting this contract inherits a
schema the route has been observed to enforce end to end, rather than one certified by inheritance
across a schema change.

## Why it closed, and whose fault that is

The stress schema's size was wrong, twice, and both times it was the operator's error rather than
the route's or the contract's.

**First, inherited.** `STATIONS = 24` came from M120 while the schema underneath it was being
flattened from eight levels to five. A shallower station serialises smaller, so 24 produced 13,118
tokens where M120's deeper 24 had produced enough. Nobody re-checked the size after the flattening.

**Then, extrapolated.** Revision 1 replaced the constant with a derivation — and derived it from a
**single** measurement, 546.6 tokens per station over 24 stations, assuming that rate is constant.
It is not. At 74 stations the observed rate was **418.3** per station, 23% lower: the model grows
terser as the list lengthens. Seventy-six stations would have cleared the threshold. The derivation
chose 74.

A derivation from one point is an assumption wearing a derivation's clothes. That is the lesson,
and it cost the milestone.

## Why it was not re-run

`not_ready_stress` is not a delivery verdict. Under the allowance the owner authorised on
3 September and this gate enforces mechanically, **only `not_ready_delivery` may be superseded**;
every other verdict is final on its first occurrence.

Re-running with 76 stations would be adjusting the instrument until the gate passes, which is the
precise failure the allowance exists to prevent. The threshold was never touched for the same
reason: a threshold rewritten to fit a stress is a gate tuned to pass itself.

The gate worked. It closed the milestone on an instrument defect, before any qualifying generation,
for the price of a calibration run.

## The four attempts

All are preserved and none is deleted. `DELIVERY_ALLOWANCE.json` records each.

| attempt | verdict | requests | note |
|---|---|---|---|
| 1 | none | 15 | terminated by the operator's own harness timeout during the stress; produced no verdict, so consumed no allowance |
| 2 | `not_ready_delivery` | 23 | 7 of 9 probes answered, all conformed; three requests exhausted their retries on 429 |
| 3 | `not_ready_delivery` | 22 | stress conformed at 13,118 tokens; the sizing defect surfaced here |
| 4 | `not_ready_stress` | 13 | 9 of 9 probes conformed; stress conformed at 30,957 |

Attempts 2 and 3 were made against the 24-station instrument; attempt 4 against the 74-station one.
The allowance is counted per instrument by plan digest, with a ceiling of six across all of them.

## Instrument defects recorded, not repaired

1. **A derivation from a single measurement.** Token yield per unit is not constant across
   completion sizes, and revision 1 assumed it was.
2. **`unenforced_feature_classes` conflates *not enforced* with *not answered*.** An unanswered
   probe scores as non-conforming. Attempts 2 and 3 listed classes as unenforced when their probes
   had only ever returned 429. The verdict ladder checks delivery first, so the headline was right,
   but the field is misleading. Inherited from M120 and still unfixed.

## For a successor

1. **Inherit this contract.** It is validated: nine of nine classes enforced, five array-of-object
   levels, 400/400 decoded candidates accepted by the frozen host, and qualification measured at
   33.5% at the pessimistic corner against M120's 28.75%.
2. **Derive the stress size from at least two measurements at different scales**, or measure the
   yield at the size actually intended. One point is not a curve.
3. **Fix the unenforced/unanswered conflation** before the next gate, so a rate-limited probe never
   appears as a capability finding.
4. **Size with margin above the threshold, not against it.** 3.3% is the distance between a closed
   milestone and a green gate.

## Claim boundary

H67 remains **untested**. No generality gate is advanced. No claim of AGI, recursive
self-improvement or open-ended intelligence is made or implied. M122's contract, decoder and
readiness gate were never exercised against a carrier bank and carry no scientific evidence of any
kind. No `IP_ASSET_REGISTER.md` row is written for M122.

## Artifacts

| | |
|---|---|
| Readiness result | `309bc3be9df278425d1e641e3258222ed8340385162e7b737ef8d7fe16978f14` |
| Candidate schema | `8e766971941f1ca14c2d035f125c383230c62343329e9c6ee475e05e1b77cbbf` |
| Route-depth diagnostic | `experiments/M122/ROUTE_DEPTH_DIAGNOSTIC.json` |
| Apparatus revisions | `experiments/M122/APPARATUS_REVISIONS.md` |
| Delivery allowance and attempts | `experiments/M122/DELIVERY_ALLOWANCE.json` |
