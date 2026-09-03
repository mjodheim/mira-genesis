# M120 — closed at the DEVELOPMENT readiness gate; H65 untested

**Date:** 3 September 2026

| | |
|---|---|
| Hypothesis | **H65 — untested** |
| Status | instrument development closed before the scientific freeze |
| Qualifying scientific invocations | **0** |
| Scientific freeze taken | **no** |
| Carrier bank | **none** |
| Reveals | **none** |
| DEVELOPMENT requests spent | 16 |
| Generality gate advanced | **none** |

**This is not a result about H65.** No freeze was taken, no bank was generated, no arm ran and no
comparison was made. The hypothesis is exactly as open as it was before. It is not a negative
result, it is not weak evidence, and it may not be cited as either.

## What happened

The M120 readiness gate ran once against the fixed route and returned `not_ready_identity`. The
substantive finding is not the one that label names, and both are recorded below.

Seven of the nine feature classes the M120 candidate schema requires were enforced cleanly:

| probe | HTTP | finish | conforms | completion tokens |
|---|---|---|---|---|
| `enum` | 200 | stop | yes | 51 |
| `pattern` | 200 | stop | yes | 91 |
| `required` | 200 | stop | yes | 70 |
| `additional_properties` | 200 | stop | yes | 7 |
| `min_items` | 200 | stop | yes | 341 |
| `max_items` | 200 | stop | yes | 12 |
| `nested_arrays` | 200 | **length** | **no** | **101,379** |
| `nesting_depth` | 200 | stop | yes | 56 |
| `combined` | **429** | — | no | — |
| token-capacity stress | **429** | — | no | — |

Runtime identity held on every one of the eight requests that carried a completion.

## The finding: this route does not enforce the contract's array nesting

`array_of_object_levels` is recorded **unenforced**.

The probe asks for a structure the prompt does not describe, at the depth the candidate schema
demands. Every level is `minItems: 1, maxItems: 1`, so the conforming answer is a single chain
eight levels deep — on the order of fifty tokens. Enforcement would have produced it.

Instead the route returned HTTP 200 with `finish_reason: length` after **101,379 completion
tokens**: the model free-ran and was truncated at the cap. Structured-output enforcement did not
hold the shape.

The number that matters is the depth. M115's schema — inherited by M116 and M119, and the one
M118's readiness gate certified — needs **five** array-of-object levels. M120's candidate schema
needs **eight**, because splitting actions into `conditional_actions` and `actions` and moving
`initial` inside its own cell added nesting. Seven of nine classes survived that change. This one
did not.

**M120's candidate schema is therefore not enforceable on the fixed route as designed.** That is a
real property of the contract and the route together, and it is exactly what a readiness gate
exists to find.

## Why the verdict says `identity`, and why that label is misattributed

After the runaway probe, the `combined` probe and the token-capacity stress each returned HTTP 429
and exhausted the two retries the frozen rule permits. A 429 body carries no router metadata, so
`identity_holds` cannot attest anything about it and returns false. `identity_held_on_every_request`
therefore went false, and the frozen verdict ladder checks identity before features.

The label is wrong about the cause. **The outcome is not.** Had identity held on every request, the
ladder would have reported `not_ready_features`, because `unenforced_feature_classes` is non-empty
either way. A cleaner run stops M120 at the same place for the same reason.

This is an instrument defect in the gate, and it is recorded rather than repaired: **attesting
runtime identity on an error response conflates "the route served something else" with "the route
served nothing."** A successor should attest identity only on responses that carry a completion, and
should classify a retry-exhausted 429 as a delivery outcome rather than an identity failure.

## The other instrument defect, recorded before it cost anything

The gate's first attempt crashed before sending a single request. It imported M117's transport,
which reaches for `fcntl` at import time — for a *file lock*, unrelated to HTTP — making the gate
unrunnable off POSIX. Nothing was spent.

The fix was not merely portability. A readiness gate that certifies a route through code the
qualifying generation will never execute is not certifying the right thing, so the gate was given
the same stdlib request path `run_m120_generation.py` uses, and its endpoint is now asserted against
the one the frozen generator spec names. Twenty-four tests cover it, written before it ran because
the gate is single-use once its result is committed.

## What this cost, and what it saved

Sixteen DEVELOPMENT requests. **No qualifying scientific generation, no seal, no reveal.**

M119 discovered its contract was unusable by spending its one qualifying generation on it. M120
discovered the same class of problem — a contract the route cannot serve — for the price of a
calibration run, and stopped. The gate that made the difference is the one M119 did not have: a
readiness measurement taken against *this* candidate schema rather than inherited across a schema
change.

## What is not being done

- The candidate schema is **not** shallowed and re-run. The gate is single-use, and redrawing it
  until the route agrees is the forking path this record exists to prevent.
- The unenforced class is **not** dropped from the required set to let the route through.
- The 429s are **not** waited out and retried beyond the frozen allowance.
- The verdict is **not** relabelled to the cause it should have named.
- No milestone before M120 is reopened or modified.

## For a successor

Three things, in the order they bind.

1. **The carrier contract must fit inside what the route enforces.** Eight array-of-object levels
   does not. A successor should either flatten the representation until its census sits at or below
   the five levels this route has been observed to enforce, or establish a higher depth on the route
   *before* adopting a schema that needs it.
2. **Identity must be attested only where there is something to attest.** A retry-exhausted 429 is a
   delivery outcome, not a substituted route.
3. **A runaway probe is evidence, not an accident.** 101,379 tokens against a fifty-token
   requirement is the signature of enforcement failing open, and a successor should treat
   `finish_reason: length` on a probe as its own recorded class rather than folding it into
   non-conformance.

## Claim boundary

H65 remains **untested**. No generality gate is advanced. No claim of AGI, recursive
self-improvement or open-ended intelligence is made or implied. The apparatus built for M120 — the
carrier contract and its decoder, the pre-seal adequacy gate, the reproducing checker — is untested
against a real bank and carries no scientific evidence of any kind.

## Artifacts

| | |
|---|---|
| Readiness plan | `f44955179b5b3acc15c0cbd834cc7f7fa3f84200eebc3a1ae0d6e279faeae45e` |
| Readiness result | `e4b0243bd3ab37b2ae2f47a87659a38bcbf1da1ea219dccd209dd475850d442f` |
| Candidate schema | `2ebf4b46fc16ff2d0b5ec8eb4a75ba76e7297717eb10b32cc14be0c055aabea6` |
