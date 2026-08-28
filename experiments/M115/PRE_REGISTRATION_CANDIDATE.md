# M115 — H60 candidate: same carrier-blind question, versioned model identity and provider route

**Hypothesis:** H60  
**Track:** A — endogenous bounded lineage, evaluated on a blindly materialized carrier family  
**Status:** **CANDIDATE. NOT FROZEN. NO H60 BANK EXISTS. NO QUALIFYING INPUT HAS BEEN SENT.**

## Scientific target

H60 states the same scientific proposition as H59, which M114 did not test because its three frozen delivery attempts were all explicit upstream shared-pool capacity rejections and materialized no bank.

**H60.** On a carrier family this project did not design, materialized blind and sealed before anyone reads it and revealed only after the tested system is frozen, the acquired M109–M111 machinery resolves demands derived by the frozen rule, and refuses structurally unsatisfiable demands rather than inventing an adapter, measurably better than an otherwise identical fresh lineage under the same budget.

The carrier-blind scientific target is unchanged. M113 remains closed with H58 untested. M114 remains `instrument-aborted` with H59 untested. Neither record is modified, repaired, re-frozen, reinterpreted, or completed by M115.

## Imported unchanged from M114

M115/H60 inherits every scientific rule and every delivery-safety rule from M114 except the explicitly versioned instrumental identity/provider clauses below. In particular, the candidate keeps:

- the M114/M113 qualifying input, generator prompt and output schema byte-for-byte;
- the strict `json_schema` structured-output contract;
- 24 requested carriers;
- minimum 3 qualifying carriers and minimum 3 distinct qualifying structures;
- exact fixed-point closure with no inherited bound;
- the M113 qualification, demand-derivation and scoring rules;
- all P1–P22 scientific/boundary computations as M114 defines them, including M114's versioned P15;
- no selection among generated carriers;
- no manual correction, repair parsing, second completion, or output selection;
- the M114 distinction between physical delivery attempts and bank materialization;
- at most 3 physical delivery attempts to obtain at most 1 bank materialization;
- a retry only after an explicit HTTP 429 with no completion and no evidence of model execution;
- the frozen 60-second wait before any permitted retry;
- ambiguous delivery, any non-429, malformed/truncated/refused/schema-invalid completion, insufficient bank, and every scientific outcome as terminal;
- no fallback, no automatic routing, and `require_parameters=true`;
- an insufficient bank as a negative scientific result, never a reason to generate again;
- no qualifying rerun after terminal failure.

M114's delivery semantics therefore remain the safety boundary for H60 rather than being relaxed in response to its failure.

## Versioned model identity — owner-authorized before any H60 freeze

The M113/M114 generator request names the public OpenRouter alias:

`deepseek/deepseek-v4-flash-0731`

The corrected DEVELOPMENT route audit records that OpenRouter's selected endpoint catalogue identifies the corresponding dated checkpoint as:

`deepseek/deepseek-v4-flash-20260731`

and that the relationship is carried by an explicit recorded mapping, not inferred by trimming or rewriting strings.

For H60, the owner explicitly authorized the successor contract to treat this **explicitly attested alias → canonical-checkpoint relation** as acceptable model identity. This authorization occurred:

1. after M113 and M114 had already terminated;
2. after the DEVELOPMENT route matrix observations existed;
3. before any H60 freeze;
4. before any H60 carrier bank exists;
5. before any H60 qualifying input is sent;
6. without any observation of H58, H59 or H60 scientific outcomes.

This rule is M115's. It was never part of M113 or M114.

The candidate identity rule is fail-closed:

- requested model must be exactly `deepseek/deepseek-v4-flash-0731`;
- OpenRouter metadata must report that exact requested alias;
- the served completion must echo that requested alias;
- exactly one selected endpoint must exist;
- the selected endpoint model must be exactly the registered canonical checkpoint `deepseek/deepseek-v4-flash-20260731`;
- no pattern-derived or suffix-derived equivalence is accepted;
- an unknown alias/checkpoint relationship is a failure;
- selected and served provider must both equal the frozen provider;
- router strategy must be direct;
- a single router attempt and no fallback must be positively attested;
- router pipeline intervention must be absent.

The identity gate is instrumental and strictly subtractive: a failure invalidates/terminates a materialization; it cannot make P22 true.

## Provider selection — Alibaba

The preserved DEVELOPMENT reliability policy in `scripts/audit_generator_matrix.py` was written before the first route matrix. It orders otherwise admissible routes by:

1. 1-day uptime descending;
2. 30-minute uptime descending;
3. p50 latency ascending;
4. provider name ascending.

That policy explicitly said it was **not** a milestone provider-selection rule when it was written. The owner has now authorized using that already-declared ordering to derive the H60 successor provider.

The chronology is therefore recorded without pretending the rule was preregistered for milestone selection:

- the reliability ordering itself predates the matrix observations;
- the decision to adopt it as the **H60 milestone-selection rule** occurs **after** those matrix observations;
- that adoption occurs **before** any H60 freeze, bank, qualifying input, or scientific observation.

Recomputing the preserved matrix under the owner-authorized alias→checkpoint admissibility rule yields the eligible smoke-tested routes and applying the preserved reliability ordering selects **Alibaba**.

The decisive first ordering key in the preserved matrix observation is:

- Alibaba `uptime_last_1d = 99.98945871422205`
- OpenInference `uptime_last_1d = 99.9887349028133`

Alibaba therefore ranks first before later tie-break keys are reached. Quantization and BYOK are not ranking inputs. Alibaba's catalogue quantization remains `unknown` and is not upgraded by inference.

The machine-readable chronology and measurements are recorded in `ROUTE_SELECTION_DECISION.json`; `metamorphosis/m115_route_selection.py` independently recomputes the selection from the preserved matrix.

## What this candidate does not authorize yet

This file is not a freeze and cannot authorize a qualifying request. Before H60 may consume any freeze, the complete candidate apparatus must be present in a reviewable PR, merged to `main`, and final preregistration/readiness checks must demonstrate at least:

- byte/digest equality for every scientific artifact claimed imported unchanged;
- explicit versioning of only the alias→checkpoint identity and provider-selection clauses;
- Alibaba route identity and no-fallback checks fail closed;
- M114 delivery-ledger semantics remain unchanged and independently validated;
- the qualifying input is absent from every DEVELOPMENT smoke path;
- no secret or account identifier is tracked;
- no bank, seal, reveal, qualification or result exists before freeze;
- M113 and M114 closed-record guards still pass;
- CI, repository integrity and sealed-bank boundary are green on the merged apparatus.

Only after those conditions pass on `main` may the already-authorized separate freeze action be consumed. That freeze must precede the first H60 qualifying request.

## Current chronology

At candidate creation time:

- M113: closed, `instrument-aborted`, H58 untested;
- M114: closed, `instrument-aborted`, H59 untested;
- M115/H60: candidate only;
- H60 scientific observations: none;
- H60 carrier bank: absent;
- H60 qualifying invocation: absent;
- H60 freeze: absent;
- G1–G10 advancement: none.
