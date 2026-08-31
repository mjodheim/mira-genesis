# M116 — H61 candidate: capacity-hardened corrective replication of H60

**Hypothesis:** H61  
**Track:** A — endogenous bounded lineage, evaluated on a blindly materialized carrier family  
**Status:** **CANDIDATE. NOT FROZEN. NO H61 BANK EXISTS. NO H61 QUALIFYING INPUT HAS BEEN SENT.**

## Scientific target

H61 states the same scientific proposition as H60. M115 did not test that proposition because its
single legitimate reveal terminated at strict-JSON admission before a carrier payload existed.

**H61.** On a carrier family this project did not design, materialized blind and sealed before anyone
reads it and revealed only after the tested system is frozen, the acquired M109–M111 machinery
resolves demands derived by the frozen rule, and refuses structurally unsatisfiable demands rather
than inventing an adapter, measurably better than an otherwise identical fresh lineage under the same
budget.

M113/H58, M114/H59 and M115/H60 remain closed historical records. In particular, M115 remains
`instrument-aborted`, H60 remains untested, and its `invalid_json` completion is never repaired,
retried, regenerated or relabelled.

## Scientific rules inherited unchanged from M115

H61 keeps the scientific target and downstream evaluation contract unchanged. Before freeze, the
implementation must mechanically prove byte/digest equality or exact semantic inheritance for:

- the 24-carrier qualifying input;
- the generator prompt;
- the carrier output schema;
- minimum 3 qualifying carriers and minimum 3 distinct qualifying structures;
- exact fixed-point closure with no inherited bound;
- M113 demand derivation, qualification and scoring rules;
- M115/M114 P1–P22 computations, including the versioned P15 phase-boundary computation;
- no selection among generated carriers;
- no manual correction or repair parsing;
- no second completion to improve or replace a materialized output;
- the distinction between physical delivery attempts and the single bank materialization;
- at most one bank materialization;
- a physical retry only where the inherited delivery rule proves an explicit pre-generation HTTP 429
  with no completion and no evidence of model execution;
- ambiguous delivery, any non-429 terminal response, malformed/truncated/refused/schema-invalid
  completion, insufficient bank and every scientific outcome as terminal;
- no fallback, no automatic routing and `require_parameters=true`;
- an insufficient valid bank as a negative scientific result, never a reason to generate again;
- no scientific rerun after terminal failure;
- tested-system freeze before reveal;
- fail-closed reveal consumption, including terminal post-decryption admission failures;
- independent replay/checker rules;
- the M115 claim boundary: no G1/G4/generality-gate or AGI advancement from this experiment alone.

## Explicit M116 instrumental delta

Only the prospective generator capacity controls are versioned for H61.

The candidate keeps:

- requested model alias: `deepseek/deepseek-v4-flash-0731`;
- required canonical checkpoint: `deepseek/deepseek-v4-flash-20260731`;
- provider: `Alibaba`;
- transport: direct OpenRouter HTTP with router metadata;
- seed: `0`;
- temperature: `1.0`;
- stream: `false`;
- strict `json_schema` response format;
- the M115 prompt, qualifying input and output schema byte-for-byte;
- the M115 blindness/contamination contract;
- the M115 explicit alias -> canonical-checkpoint identity rule.

The only intended model-visible/request-capacity changes are:

1. `max_tokens = 131072` instead of `32000`;
2. an explicit reasoning-off control, frozen only after DEVELOPMENT demonstrates that the exact route
   accepts and honors the selected representation.

No H61 freeze may silently add any other prompt, system message, tool, retrieval, memory, MCP,
repository context, conversation history, fallback route, sampling change or output repair layer.

## Non-carrier operational telemetry

M115 preserved no `finish_reason` and no token usage. Its runner computed both to decide whether
model execution could be excluded and then discarded them, so its terminal record could not
distinguish output-budget termination from prose in the completion from a fenced payload. H61
therefore preserves, for every delivery attempt and under a strict allowlist, the operational
metadata needed to tell those cases apart: HTTP status, `finish_reason`, `native_finish_reason`,
prompt/completion/total tokens, reasoning tokens, response and content byte lengths, choice count,
generation identifier, requested and served model and provider, canonical-checkpoint attestation,
router direct/one-endpoint/one-attempt/no-fallback/no-pipeline evidence, model-execution evidence,
a structural refusal indicator, and any structural response-format enforcement the endpoint
reports.

It preserves none of: carrier completion content, reasoning content, free-text provider or account
errors, credentials, hidden prompt or context, or any recovered or transformed carrier data. Free
text is refused even in allowlisted fields, because free text is where a provider puts an account
identifier or a fragment of the prompt.

**Read barrier.** Before reveal authorization, a human or a checker may read this operational
telemetry and may not read carrier content. The barrier is mechanical: only scalars cross it, and
no container or long string may appear in a telemetry record. The telemetry contract is frozen
before H61 generation.

## Terminal failure classifier

M115 diagnosed its terminal failure by matching the text of a Python exception, so `invalid_json`
meant "the parser raised" and carried no further information. The frozen M115 plan enumerated
`truncated_completion` as a separate class, and no code path in the repository could assign it.

H61 replaces that with a deterministic classifier over the preserved structured evidence,
independently replayable from the committed record. Its classes are, in precedence order:
`post_validation_failure`, `ambiguous_transport`, `pre_generation_429`,
`provider_or_route_failure`, `runtime_identity_failure`, `refused_completion`,
`missing_completion`, `truncated_completion`, `invalid_json`, `output_schema_violation`, and the
fail-closed `unclassified_terminal`.

`truncated_completion` requires affirmative structured evidence -- a finish reason in the frozen
output-budget set -- and is decided **before** parsing, so that the parse failure a truncated
completion also produces cannot absorb it. A parse failure alone never concludes truncation. Where
the evidence does not determine a class, the classifier falls closed into `unclassified_terminal`
rather than choosing the nearest plausible story. `pre_generation_429` is the only class from which
a physical retry may follow.

## Machine-only pre-seal admission

Strict carrier admission moves from after the reveal to after the single completion and before it
is declared a valid bank and sealed.

The validator is a **pure predicate**. It may parse the completion, validate exact JSON, validate
the frozen carrier schema, compute the required digests, and produce allowlisted booleans, counts,
digests and a schema *location*. It may not repair, normalize, strip markdown fences, extract JSON
substrings, reformat, regenerate, ask the model to fix output, choose among outputs, alter carriers
or expose carrier content to a human. A violation names where in the schema it happened, never what
the value was.

**The carrier envelope.** The frozen generator asks the model for `{"machines": [...]}`; the frozen
carrier host expects a payload carrying `schema`, `bank_nonce` and `carriers`, each tagged with the
opaque identifier derived from the nonce. A blind generator cannot produce those, because the nonce
is the project's and its purpose is that the generator never sees it. Enveloping is therefore a
project-side structural projection, not a repair: positional, total and content-independent,
carrier *i* is machine *i*. It adds no information from the completion, drops none, reorders
nothing, and cannot rescue a malformed machine -- the host still refuses it, and a refused body is
counted rather than corrected. The bank nonce must be committed before generation, so that no
degree of freedom survives into this step.

## The one-shot rule

**The first completion carrying evidence of model execution consumes the scientific generation
opportunity.** Execution evidence is a completion, a token count, a finish reason or a generation
identifier; absence of a completion is not absence of execution.

If machine-only admission fails there is no second completion, no redraw, no repair, no bank
materialization, and the milestone ends terminal `instrument-aborted`.

If admission succeeds, that exact completion becomes the one admissible materialization; its raw
and completion digests are bound, it is sealed immediately, human carrier access remains forbidden,
and the existing tested-system-freeze-before-reveal protocol continues unchanged.

**"First schema-valid completion wins" is forbidden.** There is no sequence of content-dependent
model draws. Whether a completion parses is a function of its content: a long, varied,
structurally rich carrier family is the one that exhausts an output budget or stresses a
constrained decoder, and a short, repetitive one completes cleanly. Redrawing on a parse failure
would filter the carrier population toward smaller and simpler families -- the axis that decides
how hard the derived demands are -- and the bias would run toward the hypothesis, with no human
ever looking at anything.

A physical retry survives only under the already frozen conservative semantics: an explicit
pre-generation HTTP 429 carrying no completion and no evidence that the model executed.

## Pre-seal / post-reveal binding

The post-seal machinery recomputes the same validation from the exact decrypted bytes and must
prove equality with the pre-seal admission record. The bound fields are the validator and envelope
versions, the admitted/parsed/schema-valid/payload-admissible predicates, the raw response digest,
the carrier completion digest, the payload digest, the output-schema digest, the request-body
digest, the bank-nonce digest, the record counts, and the failure stage.

Any mismatch is terminal `post_validation_failure`, which outranks every observation about what
the endpoint did. No plaintext carrier content enters the repository at any point.

## DEVELOPMENT-only capacity and schema-capability gate

M116 adds a pre-freeze instrument gate because M115's small route smoke was neither a large-output
stress test nor a structurally demanding one. The gate is not scientific evidence and may not use
the qualifying input.

Before the H61 analysis plan or generator spec is frozen, a committed DEVELOPMENT harness must run
a synthetic strict-schema request on the exact Alibaba/checkpoint route. Its acceptance rule is
fixed before the first stress call, and it must establish **two separate properties**.

**A. Capacity.** Unchanged from the merged candidate:

- the candidate `max_tokens = 131072`;
- reasoning explicitly disabled by the candidate control;
- observed completion usage greater than **32,000 tokens**;
- HTTP 200 and `finish_reason=stop`;
- exact requested/served alias, canonical checkpoint and Alibaba provider;
- direct router strategy, one selected endpoint, one router attempt, no fallback, no router
  pipeline intervention;
- strict JSON parses and satisfies the synthetic schema;
- positive reasoning telemetry showing zero reasoning tokens.

**B. Structured-schema capability.** New. The original gate proved output volume with 1,536 flat
rows of eight bounded integers: no regex constraint, no enumeration, and a third of the carrier
schema's nesting depth. A route whose constrained decoder degrades on deep, pattern-constrained
schemas would pass that gate and then fail the qualifying request in exactly M115's way.

The synthetic stress schema must therefore be **at least as structurally demanding as the frozen
M115 carrier output schema on every censused feature class**, while remaining synthetic content
with no carrier semantics and no qualifying carrier input.

The census is derived mechanically from the frozen predecessor schema, never hard-coded. It
records maximum nesting depth, levels of arrays of objects, closed-object (`additionalProperties:
false`) counts, `required` counts, `enum` counts, regex `pattern` counts, array cardinality bounds,
string and integer constraints, composition constructs, declared types, and every other censused
keyword the qualifying carrier schema relies upon. Only the derived census and the deterministic
synthetic schema are committed.

The gate fails, before any network call, if the synthetic stress schema is structurally weaker than
the frozen carrier schema under the preregistered census rule, or if the committed census does not
match a fresh derivation from the frozen schema.

The real carrier schema and the H61 qualifying input are **not** sent as DEVELOPMENT traffic. A
synthetic structurally dominating schema is used instead, and the harness screens the stress input
and schema against the qualifying inputs and the carrier vocabulary before it will build a request
body.

**DEVELOPMENT delivery rule, unchanged.** At most **three physical stress attempts**; attempt 2 or
3 only after an explicit HTTP 429 carrying no completion and no evidence that model execution
occurred; each permitted retry waits **60 seconds**. The first completion, ambiguous execution,
non-429 response, malformed materialization or other terminal response ends the DEVELOPMENT audit.
No content-dependent DEVELOPMENT retry is permitted. A failed or exhausted DEVELOPMENT audit may not
be redrawn under this candidate, and a failed stress gate blocks H61 freeze. Its thresholds or
interpretation may not be weakened after the observation. These DEVELOPMENT attempts are not H61
qualifying invocations, and no raw synthetic completion is persisted.

## Research stopping rule

**H61 is the last corrective replication of this carrier-blind proposition under this
generator/instrument family.** The rule is frozen before H61.

If H61 is again `instrument-aborted` after passing the preregistered DEVELOPMENT gate, H62 may not
be created simply by adjusting another transport or generation parameter. Further work would
require a materially new instrument class, a new scientific justification, and explicit review of
whether continuing the proposition is worthwhile.

If H61 genuinely tests the proposition and yields a positive, negative or mixed scientific result,
that result is preserved and the corrective-replication sequence stops there.

The rule exists because three corrective replications on one proposition is a garden of forking
paths at the milestone level, however clean each individual freeze is. Each M113-M115 freeze was
sound; the sequence is what needed a bound.

## Why the change is scientifically bounded

M116 does not claim that M115 failed from truncation. The public M115 record proves only
`invalid_json`. The larger budget and explicit reasoning-off control remove plausible output-budget
competition prospectively while leaving carrier semantics and downstream evaluation unchanged.

The DEVELOPMENT stress result cannot count toward H61. It contains no carrier world and the tested
Genesis lineage never sees it.

## Freeze sequence

This candidate does not authorize a qualifying request. The intended order is:

1. merge the complete M116 candidate apparatus and DEVELOPMENT stress harness;
2. run the non-qualifying capacity gate and preserve only allowlisted evidence;
3. review the DEVELOPMENT result and ensure the predeclared gate passed without changing its rule;
4. finalize and freeze the H61 analysis plan;
5. deterministically derive and freeze the generator spec, including exact request-body digest;
6. verify repository/closed-record/sealed-boundary checks on `main`;
7. consume the future H61 qualifying delivery budget exactly once under the inherited physical-
   delivery rule;
8. if a valid materialization occurs, seal it immediately before inspection;
9. freeze the tested system before reveal;
10. reveal once and execute qualification/scoring/P1–P22 exactly as frozen;
11. preserve positive, negative, mixed or instrument-aborted outcome without rescue.

## Current chronology

At candidate creation time:

- M113/H58: closed, H58 untested;
- M114/H59: closed, H59 untested;
- M115/H60: closed, `instrument-aborted`, H60 untested after `invalid_json`;
- M116/H61: candidate only, with the pre-freeze instrument hardening merged and unfrozen;
- M116 DEVELOPMENT capacity/schema-capability gate: not yet run;
- H61 scientific observations: none;
- H61 carrier bank: absent;
- H61 qualifying invocation: absent;
- H61 freeze: absent;
- G1–G10 advancement from H61: none.
