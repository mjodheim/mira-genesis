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
`conforming`, `truncated_completion`, `invalid_json`, `wrong_top_level_type`, `enum_violation`, `pattern_violation`,
`min_items_violation`, `max_items_violation`, `required_violation`,
`additional_properties_violation`, `bounds_violation`, `type_violation`, `nesting_violation`,
`other_schema_violation`, `missing_completion`, `transport_or_provider_failure`, `not_attempted`.

`truncated_completion` is decided **before** parsing, on affirmative finish-reason evidence, for the
same reason the scientific classifier does it that way: a truncated completion also fails to parse,
and letting the parse failure absorb it would record "the route emitted invalid JSON" — a different
and much stronger claim than the evidence supports. A truncated probe never counts as enforced.

`type_violation` and `nesting_violation` are kept apart deliberately. A wrong scalar type — a string
where the schema demands an integer — is a type violation. Only the two probes whose subject *is*
structure (nesting depth, nested arrays of objects) report a type or missing-link failure as a
nesting violation, because for those a failure at that point is exactly the depth shortfall under
test. Collapsing the two would put a structural claim in the capability profile that the evidence
does not support.

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

## Crash safety and resumption

A probe that already carries an observation in the ledger keeps it. Its one permitted delivery is
spent, and re-sending it would be a redraw, so a restart resumes from the ledger rather than
beginning again. A ledger belonging to a different frozen plan is refused outright.

A response the diagnostic cannot read becomes a `transport_or_provider_failure` observation rather
than an exception: a crash mid-matrix would abort before the report is written, leaving the
already-sent probes re-sendable, which is the redraw the rule forbids.

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

## Adversarial pre-mortem, recorded before observation

*If this matrix returned Case A — the result that lets M116 continue — how would a hostile reviewer
argue the finding was manufactured?*

**"The probes are far smaller than the real request."** This is the strongest objection and it is
correct. The isolated probes are small and shallow by construction, because isolation is their
purpose, and even the combined probe is a fraction of the qualifying request's scale. **Case A
therefore establishes feature *enforcement*, never enforcement *at carrier scale*.** That is exactly
why Case A does not license proceeding to H61: its consequence is to prepare an explicitly reviewed
revised stress candidate and run at most one further full stress audit, and it is that audit, not
this matrix, which tests whether enforcement survives the real volume and depth. A Case A read as
"the route works" would be a misreading of this instrument.

**"The model complied by chance."** Reduced by six independent constrained fields per applicable
probe, and recorded above as reduced rather than eliminated.

**"A retry produced the passing draw."** Only an explicit pre-generation 429 carrying no completion
and no execution evidence permits a second attempt; a schema violation never does.

**"The interpretation moved after the result."** The decision rule is committed in this document and
in code, and pinned by the plan digest that the report records.

**"A probe was added or reshaped once the failure was visible."** The sequence is a pure function of
the committed census, digest-pinned before the first call, and a test asserts the sent sequence
equals the planned one.

The residual limitations that no mechanism here removes: probe scale, coincidental compliance, and
the fact that this measures one route on one date.

## Claim discipline

This matrix can establish only which structured-output capabilities the fixed route enforces on
small synthetic schemas, on this date.

It cannot establish: the precise cause of M115; that M115 was not truncated; that all schemas fail
on this provider; that the model lacks the underlying capability; that enforcement holds at the
carrier request's scale; or any Genesis scientific proposition. G1–G10 remain unchanged whatever it
returns.

## Chronology at preregistration

M113/H58, M114/H59, M115/H60 closed and untouched, all three hypotheses untested. M116/H61:
candidate only; analysis plan not frozen; generator spec not frozen; bank nonce not committed;
tested-system freeze not built; qualifying input not sent; bank absent; **qualifying invocations 0**.
