# M116 — the DEVELOPMENT capacity/schema gate did not hold

**Date:** 31 August 2026
**Phase:** DEVELOPMENT. Non-qualifying. Not a scientific observation.
**Outcome:** `gate_holds: false` on one physical attempt.
**Consequence:** the preregistered gate **blocks the H61 freeze**. No H61 plan or generator spec is
frozen, no H61 qualifying input has been sent, and no H61 bank exists.

## What was observed

One physical attempt on the frozen route, using a synthetic mineral-consignment schema that the
committed census proves is at least as structurally demanding as the frozen M115 carrier schema on
every censused feature class.

| quantity | observed |
|---|---:|
| HTTP status | 200 |
| `finish_reason` | `stop` |
| completion tokens | 23,484 of 131,072 available |
| reasoning tokens | 0 |
| response bytes | 82,625 |
| served alias / checkpoint / provider | exact |
| router: direct, one endpoint, one attempt, no fallback | all attested |
| **strict output parsed and satisfied the schema** | **no** |
| **completion exceeded the old 32,000 ceiling** | **no** |

Eight of the ten gate checks passed. The two that failed are the two the gate exists to ask.

## What this rules out

**Output-budget exhaustion is not the binding constraint.** The generation stopped voluntarily —
`finish_reason=stop`, not `length` — after using 18 % of the available budget. Raising `max_tokens`
from 32,000 to 131,072 was honoured and did not help, because the ceiling was never reached.

**Reasoning-budget competition is not the binding constraint.** The explicit reasoning-off control
was accepted by the route under `require_parameters: true` and the response reports zero reasoning
tokens.

Both of M116's prospective capacity corrections were therefore honoured, and **neither was the
thing standing in the way.**

## What this points at

The route returned HTTP 200 with an attested identity, claimed to have finished, and produced
output that does not satisfy a schema it was given under `strict: true` with
`require_parameters: true`.

That is direct evidence for the competing hypothesis recorded in the pre-freeze review:
`require_parameters` gates whether an endpoint accepts `response_format` as a *parameter*, not
whether its constrained decoder implements every *feature* of the supplied schema. A schema with
depth 16, ten regex `pattern` constraints, five enumerations and nested arrays of objects is
exactly where that gap would show, and it is where it showed.

**This does not establish M115's cause.** M115 remains `instrument-aborted` with `invalid_json`,
and truncation there can still be neither established nor excluded — its record preserved no finish
reason and no token usage. The present observation is about a different (synthetic) schema on a
later date, and it is evidence about the *route's* structured-output behaviour, not a retroactive
reading of a sealed completion.

## What the gate bought

It cost one DEVELOPMENT attempt and no scientific budget. Had M116 gone straight to H61 on the
strength of the capacity correction alone, this failure would have consumed the one H61 qualifying
generation and produced a fourth consecutive `instrument-aborted` milestone. The schema-capability
half of the gate — added prospectively, with thresholds derived mechanically from the frozen carrier
schema rather than chosen — is what caught it.

## An instrument gap this observation exposes

`strict_output_parsed` is a single boolean covering two distinct outcomes: content that did not
parse as JSON at all, and content that parsed but violated the schema. The audit persists no
discriminating evidence and no raw completion, so the preserved record cannot say which occurred,
nor how many consignments were emitted, nor which schema location first failed.

This is the same class of defect corrected for the scientific path earlier in M116, where a terminal
taxonomy was wider than the classifier's discriminating power. It is recorded here rather than
repaired here: the audit is terminal and is not redrawn.

## What may and may not follow

Per the merged candidate: a failed stress gate blocks the H61 freeze; its threshold and
interpretation **may not be weakened after the observation**; and the DEVELOPMENT audit may not be
redrawn under this candidate. None of the following is permitted as a response to this result:
lowering the 32,000-token requirement, reducing the schema's structural demands, shrinking the
requested item count, relaxing strict mode, or re-running the audit.

A further DEVELOPMENT attempt requires an explicitly reviewed pre-freeze candidate revision, made
without any H61 qualifying observation — of which there have been none.

## Chronology

- M113/H58, M114/H59, M115/H60: closed, untouched, all three hypotheses untested.
- M116/H61: candidate only. Analysis plan **not frozen**. Generator spec **not frozen**. Bank nonce
  **not committed**. Tested-system freeze **not built**. Qualifying input **not sent**. Bank
  **absent**. Qualifying invocations: **0**.
- G1–G10: no movement. This is a DEVELOPMENT instrument observation and advances no gate.
