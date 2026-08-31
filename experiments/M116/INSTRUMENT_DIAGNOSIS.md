# M116 — prospective instrument diagnosis after M115

**Milestone:** M116  
**Successor hypothesis:** H61  
**Status:** design evidence only; no H61 freeze, bank or qualifying request exists

## Closed predecessor observation

M115/H60 is closed and immutable. Its single materialized response passed the frozen route and model
identity gates, was sealed before reveal, and was revealed exactly once after the tested system was
frozen. The host then rejected the completion at the first carrier admission step because
`message.content` was not valid JSON. H60 therefore remained untested and P1-P22 were not computed.

M116 does not reopen the M115 ciphertext and does not infer carrier content from it.

## What the public M115 record establishes

The preserved DEVELOPMENT smoke for Alibaba returned HTTP 200, `finish_reason=stop`, the required
DeepSeek checkpoint, direct/no-fallback router evidence, and a strictly parsed small JSON-schema
response. Thus the route was capable of strict structured output on a small non-qualifying request.

The qualifying M115 request differed materially in output demand: it requested 24 nested machine
records while fixing `max_tokens=32000`. The preserved sealed-bank commitment records a sanitized
OpenRouter response of 197,496 bytes. The M115 request did not explicitly disable reasoning.

These facts make output-budget exhaustion or reasoning-budget competition plausible failure modes,
but they do **not** prove either one. M115 intentionally did not expose the carrier completion,
finish reason or token-usage details after closure, so M116 must not rewrite the historical cause as
"truncation" without evidence.

## Prospective correction

M116 therefore removes the identified *instrumental risk class* rather than claiming a proven root
cause. The candidate H61 generator keeps the M115 scientific generator content unchanged and changes
only two output-capacity controls:

1. `max_tokens`: 32,000 -> **131,072**;
2. reasoning: unspecified -> **explicitly disabled** using the frozen OpenRouter reasoning control.

The carrier prompt, qualifying input, output schema, model alias, canonical checkpoint, provider,
seed, temperature, strict JSON-schema mode, no-fallback policy, blindness contract and downstream
scientific rules remain unchanged.

## Development-only capacity gate

Before an H61 generator spec may be frozen, the same Alibaba/checkpoint route must pass a new
non-qualifying capacity stress test whose rule is committed before the test is run.

The stress request must:

- use a synthetic prompt and schema unrelated to carrier generation;
- use the candidate H61 `max_tokens` and explicit reasoning-off control;
- require enough schema-constrained output that the observed completion exceeds **32,000 completion
  tokens**, proving the route can complete beyond M115's old ceiling;
- return HTTP 200 with `finish_reason=stop`;
- parse as strict JSON and satisfy the synthetic schema;
- attest the exact requested alias, Alibaba provider and canonical checkpoint;
- attest direct routing, one selected endpoint, one router attempt, no fallback and no router
  pipeline intervention;
- record only allowlisted operational evidence, never the synthetic raw completion.

If that stress gate fails, M116 must stop before freeze. The gate may not be weakened after observing
its result, and the H61 qualifying input may not be sent as a DEVELOPMENT probe.

## Why this does not repair M115

The new capacity controls and stress gate apply prospectively to M116 only. M115 remains terminal
`instrument-aborted`; no M115 request, output, bank, result, checker or verdict is changed. H61 is a
new observation with a new freeze and a new one-bank budget.

A successful instrument only permits H61 to be tested. It is not itself evidence for H61 and cannot
advance a generality gate.
