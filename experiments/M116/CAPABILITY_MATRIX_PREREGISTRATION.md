# M116 — DEVELOPMENT-only structured-output capability matrix

**Status:** preregistered before any probe request. **DEVELOPMENT only. Not a scientific
observation.** H61 remains unfrozen, no H61 bank exists, and the qualifying invocation count
remains **0**.

**Authorisation:** the owner explicitly authorised this DEVELOPMENT-only diagnostic revision and
capability matrix on the **same fixed M116 route**. It does not authorise an H61 qualifying
generation, a route change, a threshold change, a change to the scientific proposition, or a
regeneration of the failed DEVELOPMENT stress observation.

## Why this exists

The first DEVELOPMENT stress attempt is preserved exactly and is not redrawn. It established:

- HTTP 200, correct provider, model and canonical checkpoint, direct routing, no fallback;
- `finish_reason = stop`;
- 23,484 completion tokens of 131,072 available;
- zero reasoning tokens;
- output that did not satisfy the census-dominating strict schema.

That materially weakens the output-budget hypothesis behind M116 — the budget was never reached and
reasoning consumed nothing. **It does not retrospectively establish the cause of M115**, whose
record preserved no finish reason or token usage and where truncation remains neither established
nor excluded.

What the attempt could not say is *which* constraint was ignored, because `strict_output_parsed`
collapsed every outcome into one boolean and no discriminating evidence was persisted. This matrix
answers that, and only that.

**Its purpose is not to make H61 pass.** A result showing the route does not enforce a required
capability is a success of this instrument, not a failure.

## The observability contract

For every probe, under a strict non-content telemetry boundary, the record preserves: whether
content exists; whether it parses as JSON; whether the top-level type is correct; whether schema
validation passes; the first failing keyword; the failing schema location; the failing instance
path; observed top-level key count; observed nesting depth; `finish_reason`; completion tokens;
reasoning tokens; and response byte count.

It never preserves: completion content, arbitrary values from generated objects, or free-text
provider messages. Instance paths are built only from schema-declared property names and array
indices, so no generated value crosses the boundary. Free text is refused even in allowlisted
telemetry fields.

The frozen outcome vocabulary, every member of which the classifier can actually assign:
`conforming`, `invalid_json`, `wrong_top_level_type`, `enum_violation`, `pattern_violation`,
`min_items_violation`, `max_items_violation`, `required_violation`,
`additional_properties_violation`, `bounds_violation`, `nesting_violation`,
`other_schema_violation`, `missing_completion`, `transport_or_provider_failure`, `not_attempted`.

Every observation is independently replayable from the preserved record: the outcome is a pure
function of the recorded diagnostic fields, and the decision is a pure function of the outcomes.

## The probes, derived not chosen

The required feature classes are computed from the committed carrier census
(`CARRIER_SCHEMA_CENSUS.json`, itself derived from the frozen M115 output schema). Every keyword the
census counts at least once gets an isolated probe; every keyword it counts zero times gets none.
On the current census that is: `enum`, `pattern`, `required`, `additionalProperties:false`,
`minItems`, `maxItems`, `minimum`/`maximum`, nested arrays of objects (5 levels) and nesting depth
(13). `exclusiveMinimum`, `exclusiveMaximum`, `minLength`, `maxLength` and `uniqueItems` are counted
zero and are therefore not probed.

Each probe isolates **one** class. Vocabulary is synthetic (weather bands, gauges, shipping
references), screened against carrier terms, and no probe carries carrier semantics or the H61
qualifying input.

### How a probe distinguishes enforcement from coincidence

A schema and a prompt that agree prove nothing: a model that would have complied anyway is
indistinguishable from a decoder that forced it. So each probe leaves the constrained dimension
**underspecified in the prompt** and constrained only in the schema — the prompt asks for "a
weather-band label", the schema permits four unusual words. A value inside the enumeration can then
only come from enforcement.

Where a bound cannot be probed by underspecification, the prompt asks for a quantity the schema
forbids: "a list of exactly twenty integers" against `maxItems: 3`, "two or three integers" against
`minItems: 40`, extra keys against `additionalProperties: false`. That is a measurement of our own
endpoint, preregistered here rather than improvised later.

Coincidence is reduced by repetition — six independent constrained fields per applicable probe — but
**not eliminated**. A recorded limitation: "enforced" means "the constraint held across six
independent fields", which is strong evidence and not proof. "Not enforced" is the stronger
direction: the endpoint returned something the schema forbids.

## Fixed before observation

- the exact probe schemas and prompts, pinned by digest in the plan record;
- the exact order: the isolated probes in the sequence above, then the combined probe;
- the number of calls: one per isolated probe, plus at most one combined probe;
- **the combined probe is reached only if every isolated probe passed**;
- per probe: at most **three physical attempts**, and attempt 2 or 3 only after an explicit HTTP 429
  carrying no completion and no evidence that the model executed; each permitted retry waits 60
  seconds;
- the interpretation, the pass/fail rule and the decision rule, all below.

**No probe may be added, removed, reordered or adapted after seeing an observation.** The plan is a
pure function of the committed census and is digest-pinned before the first call.

## No content-dependent redraw

The first materialized response is the observation for that probe. It is never redrawn because it
violated the schema, never repaired, never regenerated, and the model is never asked to fix it. The
only permitted retry is the inherited explicit pre-generation 429 with no completion and no
execution evidence — the one class provably independent of content.

## Decision rule, precommitted

**Case A — every required isolated capability is enforced *and* the combined probe conforms.**
Preserve the matrix evidence; retain the same route; prepare an explicitly reviewed revised M116
DEVELOPMENT stress candidate under the new diagnostic instrumentation; execute at most one further
full stress audit; if that holds, continue toward the H61 freeze.

**Case B — one or more required capabilities are not enforced reliably.**
Do not retry M116. Do not weaken the carrier schema to accommodate the provider. Do not change the
route inside H61. Classify the M116 instrument family as **unsuitable for H61**, preserve H61 as
**untested**, and close the M116 corrective-replication path. Then propose **M117/H62** as a
genuinely new milestone with a prospectively specified route-qualification and selection procedure —
candidate eligibility, reliability threshold, capability matrix, scoring and ordering rule,
tie-break, minimum structural capability, token-budget capability, identity attestation, no-fallback
requirement and any budget ceiling — with the route chosen mechanically from that frozen rule before
any H62 generator specification is frozen.

This structure exists to prevent outcome-driven provider substitution inside M116.

## Claim discipline

This matrix can establish only which structured-output capabilities the fixed route enforces on
small synthetic schemas, on this date.

It cannot establish: the precise cause of M115; that M115 was not truncated; that all schemas fail
on this provider; that the model lacks the underlying capability; or any Genesis scientific
proposition. G1–G10 remain unchanged whatever it returns.

## Chronology at preregistration

M113/H58, M114/H59, M115/H60 closed and untouched, all three hypotheses untested. M116/H61:
candidate only; analysis plan not frozen; generator spec not frozen; bank nonce not committed;
tested-system freeze not built; qualifying input not sent; bank absent; **qualifying invocations 0**.
