# M117 Stage 1 — outcome of attempt 03

**Stage 1 ran to its frozen stopping condition and selected no route. That is not a finding that no
route qualifies.** Two of the twelve qualification clauses demand evidence from response fields this
API does not emit, so the run could not distinguish a route that fails from a route that passes.

| | |
|---|---|
| Frozen plan | `687b239471245b968c874cfac2854755ca2a16511bff45ae2a4daf8d231c1849` (revision 3) |
| Candidate universe | `0a7e7b7a49be8957…` — 282 assessed, 94 eligible |
| Candidates probed | 17 of 94, in the frozen order |
| Requests spent | **160 of 160 — ceiling reached** |
| Selection | **none** |
| Independent checker | **PASSED** |
| Qualifying invocations | **0** |

The seventeenth candidate was cut short by the ceiling and is recorded `candidate_probing_incomplete`
rather than dropped, so the budget spent on its behalf stays visible.

## What was measured

Of the sixteen candidates probed to completion:

- **Six enforced all nine required schema feature classes** — enum, pattern, required,
  additionalProperties, minItems, maxItems, integer bounds, nested arrays and nesting depth — with
  every probe HTTP 200 and conforming.
- **Eight enforced none of the nine.**
- Two enforced some but not all.

Candidate 11 is **the M116 route itself** (`deepseek/deepseek-v4-flash-0731` on Alibaba). It returned
nine of nine unenforced with model, provider and canonical checkpoint exact — **independently
replicating M116's central finding on a freshly built apparatus**, three revisions removed from the
one that produced it.

That result stands on its own and does not depend on anything below.

## Why this is an instrument abort, not a negative result

Three clauses failed on **all sixteen** complete candidates. Five of the six fully enforcing
candidates failed on **nothing else**.

### `no_fallback` and `no_pipeline_intervention` are unsatisfiable by construction

Both clauses require a field to be present and to be an empty list:

```
router_no_fallback              = isinstance(attempts, list)  and len(attempts) == 0
router_no_pipeline_intervention = isinstance(pipeline, list)  and len(pipeline) == 0
```

The diagnostic recorded the router metadata's key set on six requests, four rejected and two
successful. It is identical every time:

```
['attempt', 'endpoints', 'is_byok', 'region', 'requested', 'strategy', 'summary']
```

**`attempts` and `pipeline` are not fields of this object.** They are absent on success as well as on
failure, so their absence carries no information about routing. No route can satisfy these clauses,
and a run that ends with no selection cannot mean anything until they are resolved.

### A correction: M116 never observed those fields either

Attempt 03's record was first read as evidence that the fields once existed, because
`experiments/M116/CAPACITY_STRESS_DEVELOPMENT.json` shows `attempts: []` and `pipeline: []` on one of
these same providers. **That reading was wrong, and the claim is withdrawn.**

`metamorphosis/m115_identity.py::safe_router_metadata` initialises both to `[]` and fills them only
when the source key is a list:

```python
attempts = value.get("attempts")
safe_attempts: list[dict[str, Any]] = []
if isinstance(attempts, list):
    ...
```

An **absent** field is therefore rendered as an **empty** one. M116's empty lists were manufactured by
that projection, not observed. The API has never emitted these keys within this project's record.

This is a latent defect in shared attestation code, and it points the wrong way: in a no-fallback
check, "absent" silently becomes evidence of "nothing happened". **It is reported here and has not
been changed.** `safe_router_metadata` is on the M115 and M116 verification paths, and those
milestones are closed and immutable. No recorded outcome depends on it — M115 was instrument-aborted
at `json.loads`, and M116 concluded its route enforced nothing — but the repair is not M117's to make
unilaterally.

### The clauses have **not** been relaxed

They failed on every candidate, and removing them now would be removing qualification criteria after
they blocked everything. `router_direct`, `router_one_attempt` (`attempt: 1`) and
`router_one_endpoint` did hold on the fully enforcing candidates, and it is arguable that they
already establish exactly one routing attempt. **That argument was reached only after watching the
clauses block every route, so it is not acted on here.** The decision is recorded as open.

## The stress rejection, bisected

`token_capacity_stress_holds` also failed on all sixteen, in two distinct ways.

**Alibaba `deepseek/deepseek-v4-pro`** accepted the request (HTTP 200), emitted **44,791 completion
tokens** — well past the 32,000 bar — and then returned `finish_reason: "error"` with non-conforming
output. That is a real observation about the route, not an instrument artifact.

**The Google routes rejected the request outright (HTTP 400).** Six requests bisected it one
dimension at a time against `gemini-3.5-flash`:

| case | result | excludes |
|---|---|---|
| probe schema, probe budget | **200** | baseline holds |
| stress **prompt**, probe schema | **200** | the prompt |
| stress schema, `max_tokens` 1024 | 400 | the token budget |
| stress schema, no reasoning control | 400 | the reasoning parameter |
| stress schema, cardinality reduced to 4 | 400 | array size |
| stress schema, depth truncated to 6 | 400 | nesting depth |

The **stress schema** is rejected, and neither shrinking its arrays nor flattening its nesting
rescues it. Two earlier explanations were already excluded by attempt 03 itself: the probes sent
`max_tokens = 131072` to an endpoint declaring 65,536 and returned 200, and the same endpoints
conformed to all ten probe schemas.

**Why the provider rejects it is not established, because the provider does not say.** The error body
is the opaque wrapper `Provider returned error` — 23 bytes, identical digest on all four rejections,
carrying no cause. Every case therefore classified `unclassified`; that is the vocabulary meeting an
opaque error, not a gap in the bisection. The report is left exactly as produced rather than
relabelled after the fact.

This silence is bounded, and differs from M115's in the way that matters: M115 could not say whether
its completion was truncated. Here the failing component is identified — the stress schema, not the
prompt, budget, parameters, cardinality or depth — and only the provider's private reason is missing.

## What Stage 1 does **not** license

No threshold was lowered, no eligibility enlarged, no provider preferred, no carrier schema weakened,
no capability matrix rewritten, and no candidate re-run until it passed. **H62 is not created.**

## Claim boundary

Stage 1 measured which schema features candidate endpoints enforce, on small synthetic schemas, on
one date, on 17 of 94 eligible candidates. It is instrument qualification. **It is not evidence for
or against H62**, and G1–G10 are unchanged. Qualifying invocations remain **0**.

## Open decisions

1. Whether `no_fallback` and `no_pipeline_intervention` may be re-specified against evidence this API
   actually emits, or whether Stage 1 stands as unresolvable on the present instrument family.
2. Whether the stress schema should be treated as a route-capability boundary or as an unmet
   requirement of the carrier design, given the provider states no cause.
3. Whether `safe_router_metadata`'s absent-to-empty projection is repaired, and by whom, given it sits
   on closed-milestone verification paths.
