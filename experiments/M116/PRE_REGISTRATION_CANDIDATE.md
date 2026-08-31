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

## DEVELOPMENT-only capacity gate

M116 adds a pre-freeze instrument gate because M115's small route smoke was not a large-output stress
test. The gate is not scientific evidence and may not use the qualifying input.

Before the H61 analysis plan or generator spec is frozen, a committed DEVELOPMENT harness must run a
synthetic strict-schema request on the exact Alibaba/checkpoint route. Its acceptance rule is fixed
before the first stress call.

The DEVELOPMENT delivery rule is also fixed before the first stress call: at most **three physical
stress attempts** are permitted; attempt 2 or 3 is permitted only after an explicit HTTP 429 carrying
no completion and no evidence that model execution occurred; each permitted retry waits **60
seconds**. The first completion, ambiguous execution, non-429 response, malformed materialization, or
other terminal response ends the DEVELOPMENT audit. A failed or exhausted DEVELOPMENT audit may not
be redrawn under this candidate. These DEVELOPMENT attempts are not H61 qualifying invocations.

The capacity gate requires:

- HTTP 200;
- `finish_reason=stop`;
- strict JSON parses and satisfies the synthetic schema;
- observed completion usage is **greater than 32,000 tokens**;
- requested/served alias and selected canonical checkpoint are exact;
- selected/served provider is Alibaba;
- direct router strategy;
- one selected endpoint;
- one router attempt;
- no fallback;
- no router pipeline intervention;
- the candidate `max_tokens=131072` is used;
- reasoning is explicitly disabled by the candidate control;
- no qualifying carrier input or carrier schema content is sent;
- no raw synthetic completion is persisted.

A failed stress gate blocks H61 freeze. Its threshold or interpretation may not be weakened after the
observation. A new design would require a later milestone or an explicitly reviewed pre-freeze
candidate revision made without any H61 qualifying observation.

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
- M116/H61: candidate only;
- H61 scientific observations: none;
- H61 carrier bank: absent;
- H61 qualifying invocation: absent;
- H61 freeze: absent;
- G1–G10 advancement from H61: none.
