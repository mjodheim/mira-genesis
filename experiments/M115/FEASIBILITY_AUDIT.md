# M115 — the DeepSeek BYOK route does not satisfy the frozen contract

**Date:** 27 August 2026
**Status:** **DEVELOPMENT AUDIT ONLY. No freeze consumed. No qualifying invocation. No bank.**
**Verdict:** the requested route cannot serve the frozen contract, and the decision on what to do
about that belongs to the owner.

M115 was opened to correct the instrumental ceiling that ended M113 and M114: a shared, non-BYOK
OpenRouter provider pool that returned four cumulative qualifying 429s across the two milestones.
The first route to qualify was **`deepseek/deepseek-v4-flash-0731` served by DeepSeek first-party,
BYOK, with OpenRouter as router only**.

It was audited before any freeze, as required. **It fails.**

## Three independent blockers, two of them fatal on their own

### A. DeepSeek first-party cannot serve strict structured output — *fatal*

The frozen contract, unchanged since M113, requires `response_format` of type `json_schema` with
`strict: true`. The schema **is** the contract.

DeepSeek first-party lists 14 supported parameters. `response_format` is among them.
**`structured_outputs` is not.**

Measured, not inferred:

```
POST /api/v1/chat/completions
  provider: {only: ["deepseek"], allow_fallbacks: false, require_parameters: true}
  response_format: {type: "json_schema", json_schema: {strict: true, ...}}
→ HTTP 404  "No endpoints found that can handle the requested parameters."
```

This is not worked around. Substituting `json_object` would replace the schema that is the contract
with an instruction in prose, which `m113_carrier_bank.validate_generator_spec` rejects by name.

### B. The account's data policy excludes DeepSeek first-party — *fatal*

A plain probe with **no** structured output and `require_parameters: false`:

```
provider: {only: ["deepseek"], allow_fallbacks: false}
→ HTTP 404  "No endpoints available matching your guardrail restrictions and data policy."
```

**Control:** the identical probe returns **HTTP 200** against Morph and against Together. The
rejection is specific to DeepSeek first-party and is not a global condition. This is an owner-side
setting on the OpenRouter account, not something this session can or should change.

That control matters. M113 recorded what it costs to act on a network denial as though it were a
fact about a provider: a discovery that could not read the catalogue once produced
`model_is_in_the_catalogue: false` for a model that was there all along. A diagnosis that cannot
distinguish *this provider is excluded* from *everything is excluded* is a guess.

### C. BYOK has never been exercised on this key — *not independently fatal, but unresolved*

`byok_usage` is **0** for the daily, weekly, monthly and lifetime windows. No BYOK request has ever
succeeded on this account.

The limit of that claim, stated rather than glossed: this is evidence that no BYOK request has been
*served*, not proof that no integration is *configured*. **`is_byok` could not be observed either
way**, because blockers A and B stop the request before any provider is reached. Property 4 —
`is_byok == true` attested on the probe — is therefore not merely unmet but currently
unobservable on this route.

### D. The frozen request body would have to change — a delta, recorded not absorbed

DeepSeek first-party does not list `seed` among its supported parameters. The frozen canonical
request body sends `seed: 0`.

Under `require_parameters: true` that is a further routing rejection. Under `false` the seed would
be dropped silently, so the request served would not be the request frozen. Recorded here rather
than absorbed: a delta hidden under "unchanged" is exactly the defect M114 was built to stop
repeating.

## One observation about model identity

OpenRouter's endpoint record for the first-party route is named:

```
DeepSeek | deepseek/deepseek-v4-flash-20260731
```

The first-party route appears to resolve to a **dated checkpoint** rather than a mutable service
alias, which would be the stronger identity the owner asked to prefer where available. This is a
**discovery-bound observation from the endpoint listing and is not runtime-attested**, and nothing
is claimed beyond it.

## What this audit did not do

- No freeze was consumed. M115 has no plan and no generator spec.
- No qualifying invocation was made.
- **The qualifying input was never sent.** Every probe used the throwaway smoke input, and the two
  digests were compared before sending.
- No schema was substituted.
- No model or provider was substituted.
- No direct DeepSeek API path was attempted.
- No artifact here carries a credential or a personal identifier.

## What stands

M113 and M114 are closed. H58 and H59 remain untested. M115 has no frozen instrument and no bank,
and the carrier question this lineage has been trying to reach since M113 remains unreached — still
for instrumental reasons, and still not for anything about carriers.

The next step is the owner's. This audit reports the defect and stops, as instructed.
