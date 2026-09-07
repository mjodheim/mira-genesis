# M125/H70 sizing reconciliation — 7 September 2026

**Status:** PROSPECTIVE, BEFORE ANY M125 NETWORK OBSERVATION  
**M125 network observations:** 0  
**H70 scientific observations:** 0  
**Network authority added:** none  
**Scientific-run authority added:** none  
**Frozen protocol:** `49e86626ffe3a5e835fa574f943072768e53fad40ca91b505d6294c09bff0257`

## Why this record exists

The merged preimplementation review described a conservative sizing rule using an uncertainty factor
`F = 1.25`, a 65,536-token operational ceiling and a requirement that the final observation fall
inside the uncertainty-expanded predicted band. During offline implementation, before any M125
network request and before any H70 observation, the final preregistration separated two concerns that
that rule had coupled:

1. choosing a final station count that is likely to clear the 32,000-token adequacy floor while
   remaining safely away from the request cap; and
2. validating a token-rate prediction model as though prediction accuracy were itself a readiness
   target.

The second is not part of H70 and is not required to establish route capacity. Leaving the change
implicit would nevertheless create an avoidable chronology ambiguity. This document records the
refinement prospectively and makes the controlling rule explicit.

## Controlling M125 sizing rule

For the three fresh M125 calibration rates at 8, 16 and 32 stations:

- `r_low = min(tokens / stations)`;
- `r_high = max(tokens / stations)`;
- `minimum = floor(32000 / r_low) + 1`;
- `maximum = floor(52428 / r_high)`;
- the final station count is the deterministic integer midpoint, adjusted only if needed to keep it
  out of the calibration set.

`52,428 = floor(65,536 * 4 / 5)`. It is a prospectively fixed 20% headroom boundary below the
65,536 request cap, not a value fitted from M122, M123 or M124 observations.

The single out-of-sample final observation must itself be answered, stop normally, conform to the
pinned schema, use the derived station count, contain more than 32,000 and at most 52,428 completion
tokens, preserve exact route identity and zero reasoning tokens, and occur only after every required
probe and fresh calibration point has passed. A miss closes `not_ready_stress`; it is never added to
calibration and there is no refit, redraw or second final size.

## Why this does not weaken a positive readiness verdict

Dropping the lower-side `F` expansion can only make the chosen final size smaller. If that makes the
final output fall below 32,000, the direct final measurement fails and M125 closes. It cannot turn a
sub-threshold final observation into `ready`.

Replacing the 65,536 upper boundary with 52,428 is stricter for a positive verdict and keeps explicit
headroom below the request cap. The final observation is measured directly; M125 therefore treats the
fresh rate envelope as a deterministic sizing device rather than a separate scientific prediction
that must itself be validated.

This refinement changes apparatus policy, not H70, the candidate carrier contract, the fixed route,
the 32,000 adequacy floor, the fresh-only 8/16/32 calibration requirement, the no-refit rule or the
cross-instrument 4/6 delivery history.

## Precedence and chronology

Because this reconciliation is recorded with **zero M125 network observations**, it is prospective.
For M125 sizing only, the final `experiments/M125/PREREGISTRATION.md`, the exact committed
`experiments/M125/PROTOCOL.json`, and this reconciliation control where sections 10–12 of
`docs/audits/M125_PREIMPLEMENTATION_REVIEW_2026-09-06.md` describe the earlier `F = 1.25` /
predicted-band rule.

The Hati binding corrigendum C1–C3 is unchanged and retains full precedence for anti-rearm,
interpreting-source binding and pre-credential execution ordering.

No `NETWORK_AUTHORIZATION.json` is created here. The next gate remains independent hostile review,
fully green offline CI, exact protocol/source verification, and only then a separate owner decision
on DEVELOPMENT network authorization for this exact protocol digest.
