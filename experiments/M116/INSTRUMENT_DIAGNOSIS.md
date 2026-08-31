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

## Two further defects the diagnosis missed, found before freeze

The capacity correction above is necessary and not sufficient. Reading the frozen apparatus rather
than the observation turned up two defects that no M113-M115 milestone could have surfaced, because
none of them ever reached carrier admission with a payload.

**The terminal taxonomy was wider than the classifier's discriminating power.** M115 classified its
terminal failure by matching the text of a Python exception. The frozen plan's `never_retried` list
names `truncated_completion` and `invalid_json` as distinct classes; `truncated_completion` occurs
exactly once in the repository, inside a tuple, and no code path can assign it. A truncated
completion is an unparseable string, so it would have been recorded as `invalid_json`. The label
therefore carries no information beyond "the parser raised" -- which is why this document could not
and still cannot say whether M115 truncated. The discriminating evidence existed at delivery time:
the runner read `finish_reason` and `usage.completion_tokens`, used them to decide whether model
execution could be excluded, and kept neither. Both are non-carrier operational metadata whose
preservation would have leaked nothing.

**The admission path did not connect to the generator.** The frozen generator asks the model for
`{"machines": [...]}` under an output schema that closes the object to that one key. The frozen
carrier host expects a payload carrying `schema`, `bank_nonce` and `carriers`, each tagged with the
opaque identifier derived from the nonce -- values a blind generator cannot produce, because the
nonce is the project's and exists so the generator never sees it. Nothing in the M115 path joined
the two. A complete, valid, schema-conformant carrier completion would have been refused at
`validate_carrier_bank_payload` regardless of the token budget. M116 corrects this with a
positional, total, content-independent envelope under a nonce committed before generation.

Neither finding revises M115's observed cause, and neither is an inference from its sealed
completion. Both are properties of the frozen source, readable without opening anything.

## Why this does not repair M115

The new capacity controls and stress gate apply prospectively to M116 only. M115 remains terminal
`instrument-aborted`; no M115 request, output, bank, result, checker or verdict is changed. H61 is a
new observation with a new freeze and a new one-bank budget.

A successful instrument only permits H61 to be tested. It is not itself evidence for H61 and cannot
advance a generality gate.
