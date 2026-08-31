# M116 — capability matrix result: the fixed route enforces no schema constraint

**Date:** 31 August 2026
**Phase:** DEVELOPMENT. Non-qualifying. Not a scientific observation.
**Verdict:** **Case B** — nine of nine required capabilities unenforced.
**Consequence (precommitted):** the M116 instrument family is **unsuitable for H61**. H61 is
preserved **untested**. The M116 corrective-replication path is **closed**. M117/H62 follows.

**Qualifying invocations: 0.** H61 unfrozen, no bank, no gate movement. M113/M114/M115 untouched.

## The profile

| probe | feature class | outcome | first failing keyword |
|---|---|---|---|
| enum | `enum` | `enum_violation` | `enum` |
| pattern | `pattern` | `pattern_violation` | `pattern` |
| required | `required` | `required_violation` | `required` |
| additional_properties | `additionalProperties:false` | `additional_properties_violation` | `additionalProperties` |
| min_items | `minItems` | `min_items_violation` | `minItems` |
| max_items | `maxItems` | `max_items_violation` | `maxItems` |
| integer_bounds | `minimum`/`maximum` | `bounds_violation` | `minimum` |
| nested_arrays | 5 array-of-object levels | `nesting_violation` | `type` |
| nesting_depth | depth 13 | `nesting_violation` | `required` |
| combined | all of them | `not_attempted` | — (prerequisites failed) |

Every probe returned **HTTP 200** with **`finish_reason = stop`**, content that **parsed as JSON**
with the **correct top-level type**, at **6–61 completion tokens** and observed nesting depth
**1–2** where the structural probes demanded 5 levels and depth 13.

Each probe produced exactly the violation its feature class was built to detect. Nothing was
truncated, nothing was malformed, nothing failed in transport, and no probe was retried.

## What this establishes

**On this route, `"strict": true` with `require_parameters: true` provides no schema enforcement
at all.** The endpoint accepts the parameter, routes correctly — exact alias, canonical checkpoint,
Alibaba, direct, no fallback — returns 200, and emits well-formed JSON shaped entirely by the
prompt. The schema is inert.

This is not a marginal or partial finding. It is not "enforcement degrades on complex schemas". Not
one of nine feature classes held, on schemas small enough that the model answered in tens of tokens.

It also explains the earlier stress-gate failure completely and without residue: a route that emits
prompt-shaped JSON would produce, for a 96-item census-dominating request, roughly what was
observed — a voluntary stop well short of any budget with output that does not satisfy the schema.
The capacity hypothesis M116 was built around was answering a question the route was never asking.

## What this does not establish

- **Not the cause of M115.** M115 preserved no finish reason and no token usage; this is a
  different schema on a later date. Truncation there remains neither established nor excluded.
- **Not that the model lacks the capability.** This measures what the *endpoint enforces*, not what
  the model can do. A model that would have produced conforming output when told the constraints in
  the prompt is entirely consistent with everything here — the probes deliberately withheld them.
- **Not that all providers or all schemas behave this way.** One route, one date.
- **Nothing about any Genesis scientific proposition.** G1–G10 unchanged.

## Why the negative direction is the strong one

The preregistration recorded that "enforced" would be strong evidence rather than proof, because a
model may comply by chance. The observed direction is the other one, and it is the sound one: the
endpoint returned content the schema forbids, nine times out of nine, each time failing on precisely
the constraint under test. No coincidence argument is needed to read a violation.

## Correction to the persisted report

The report's `decision.combined_probe_ran` field reads `true`. It is mislabelled: a row exists for
the combined probe because the runner records that it was skipped, and the field asked whether a row
existed rather than whether a request was sent. The combined probe was **not** sent — its outcome is
`not_attempted`, exactly as the frozen rule requires when an isolated prerequisite fails.

The observations themselves are untouched and the verdict is unaffected: replaying `decide()` over
the preserved observations returns Case B either way. The predicate is corrected prospectively and a
test pins it; the report is preserved as produced rather than rewritten, because it is the record of
what was observed.

## What the frozen rule permits from here

Prohibited, explicitly: retrying M116; weakening the carrier schema to accommodate the provider;
reducing the census; relaxing strict mode; changing the route inside H61; or reinterpreting this
result.

Required: classify the M116 instrument family unsuitable for H61, preserve H61 as untested, close
the corrective-replication path, and propose **M117/H62** as a genuinely new milestone whose route
is chosen mechanically from a preregistered qualification rule — candidate eligibility, reliability
threshold, capability matrix, scoring and ordering, tie-break, minimum structural capability,
token-budget capability, identity attestation, no-fallback requirement, budget ceiling — with the
selection committed *before* any H62 generator specification is frozen.

That sequence is what makes M117 scientifically distinct from M116 rather than a silent repair of
H61 by provider substitution.

## Cost

Nine DEVELOPMENT requests totalling 282 completion tokens. No scientific budget was touched.
