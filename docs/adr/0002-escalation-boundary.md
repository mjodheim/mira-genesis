# ADR 0002 — The escalation boundary between fast and slow paths

**Status: accepted for M038. No mechanism implemented yet.**

## Context

Mira's kernel is already compact and free of any external model. The risk is not that it
becomes a committee of chatbots; it is that the proof machinery becomes the critical path,
and that an adaptive router reintroduces a signal this repository has already measured as
misleading.

## Decision

A single boundary separates two regimes. Below it, the organism acts. Above it, it changes
what it is.

```
fast path (deterministic or seeded, light trace, rolling commitment)
        │
   persistent limitation?
        │
   no ──► continue
        │
   yes ─► ESCALATION BOUNDARY ──► checkpoint ──► full causal journal
                                                        │
                        diagnose → propose → isolate → evaluate
                                                        │
                                          adopt or reject → rollback test
                                                        │
                                                 return to fast path
```

## Only one trigger is active in M038

**`proved_structural_incapacity`.**

The Myhill–Nerode bound over the organism's own oracle answers: prefixes separated by an
observed suffix cannot share a state, so a pairwise-distinguishable set lower-bounds the
required size. When that bound exceeds the body's size, no rearrangement of the current
states can express what has already been observed.

It is chosen because it is computable, sound, independent of the hidden result, already
implemented, and directly tied to the need it triggers. Measured: 0 unsoundness in 24
checks, and it never demanded growth against the organism's own behaviour.

### Two distinct causes of a false negative, and only one is fixable

An earlier draft recorded the bound's false negatives as inherent under-claiming. That was
wrong, and measurement corrected it.

**A — algorithmic incompleteness.** The distinguishability graph may hold a larger
pairwise-distinguishable set than the greedy insertion order finds. This is a weakness of the
certificate *search*, and it is repairable.

**B — evidence incompleteness.** Even the exact maximum over the *observed* prefixes and
suffixes can fall below the true requirement, when no observed suffix separates the relevant
pair. This is epistemic, a property of what has been seen, and no algorithm removes it.

Measured on the committed sizes, over twelve cases:

| Observation words | Prefixes | Worst exact solve | Gap A (algorithmic) | Gap B (evidence) |
|---|---:|---:|---:|---:|
| 63 | 63 | 0.03 s | 4 | **0** |
| 127 | 127 | **0.77 s** | 4 | **0** |

Exact maximum-clique search over the distinguishability graph is **entirely tractable** at
these sizes, and the exact bound equalled the true minimal state count in all twelve cases.
**Every false negative was cause A.** The greedy missed 3 of 6 cases that genuinely required
growth; the exact search missed none of them.

M038 therefore uses an **exact** maximum pairwise-distinguishable set: deterministic, always
sound, strictly more complete than greedy, and producing a verifiable certificate.

The historical greedy function in `m035_evolution.py` is **not** silently changed. The exact
version is introduced as an M038 mechanism under its own name, so M035's recorded behaviour
stays reproducible.

Cause B remains, and the claim is scoped to it:

> **When the certificate exists, structural incapacity is proved and escalation is
> justified.**

It may never become *"M038 detects every situation requiring growth"*.

### The certificate

```
StructuralIncapacityCertificate
- body_state_count
- certified_lower_bound
- witness_prefixes
- distinguishing_suffix_for_each_pair
- evidence_digest
- algorithm_id
- algorithm_version
```

An independent verifier must confirm that each recorded pair is genuinely separated by its
recorded suffix. The slow path **verifies the certificate from the recorded body and
evidence**; it never trusts an `escalation_reason` field.

### Specified but not activated

`repeated_failure_under_comparable_conditions` — requires "comparable" to be defined by
observable canonical fields, not by similarity judged after the fact. Until those fields are
frozen, the trigger is a back door.

`sustained_cost_above_committed_threshold` — requires the threshold to be committed before
measurement.

### Rejected for M038

`persistent uncertainty` and `saturation`. Neither has an exact definition here, and an
inexact trigger would be tuned by whoever reads the results.

## What M026–M031 do and do not forbid

An earlier draft of this design claimed those experiments disqualified adaptive routing.
That was an overstatement, and it is corrected here.

They show that allocation driven by **immediate performance** stayed anti-aligned with
hidden potential in the domains studied — M028 measured −478 per mille. They do not show
that all adaptive routing fails.

The rule this ADR adopts:

> **M038 forbids a router based naively on immediate performance. It permits escalation
> founded on a demonstrated property of the current body.**

`proved_structural_incapacity` is itself adaptive routing. Its signal is a *certificate*,
not a performance measure, and that is the whole distinction.

## The router may not be omniscient

It reads only permitted observations. Its decisions are serialised, reproducible, ablatable,
comparable to a baseline, budget-limited, and independent of sealed data.

**It may never read the hidden result it is trying to predict.** A test asserts this.

## Cost classes

| Level | Meaning |
|---|---|
| 0 | local deterministic operation |
| 1 | lightweight specialist |
| 2 | retrieval, search, or bounded simulation |
| 3 | general foundation model |
| 4 | full metamorphosis cycle |

Every operation declares a `ComputationRequest`: requested level, reason, expected
information gain, maximum cost, fallback, timeout, evidence references. The system starts at
the cheapest level that could resolve the problem, and an escalation must be justified by an
observable signal.

**Level 3 is unreachable in the canonical lineage.** No component of M038 uses a foundation
model. The level exists in the scale so that any future use must be declared rather than
introduced silently.

## Information gain must be exact or diagnostic

"Information gain per cost" is a candidate proxy, and this repository has an expensive
history with proxies. It may enter the decision rule **only** with an exact definition:

- reduction in the number of bodies still consistent with the observations;
- exact reduction of a finite hypothesis set;
- a newly proved distinguishable prefix pair;
- a certified increase in the Myhill–Nerode bound.

Any heuristic estimate stays diagnostic and may not drive escalation.

## Alternatives rejected

**Always-on diagnosis loop.** Already measured. M036 built it with a decidable diagnosis and
scored 2/8 against 6/12 for a population without it. Once growth is in the search
vocabulary, the search finds when to grow by itself.

**Escalate on any failure.** Rejected: a single failure is not evidence of a structural
limit, and this reduces to immediate-performance routing.

**Multiple triggers active at once in the first experiment.** Rejected on attributability. A
result under three simultaneous triggers cannot be assigned to any of them.

**A central orchestrator that sees everything.** Rejected: it would hold knowledge the
components cannot audit, and its decisions could not be ablated independently.

## Test obligations

**Fast path.** A simple task calls no foundation model; a deterministic function stays at
level 0; components pass artifact references rather than duplicated context; a simple action
does not trigger metamorphosis; cost is measured; the router reads no hidden data.

**Escalation.** An isolated failure does not trigger metamorphosis; a proved structural
incapacity does; the trigger is deterministic under identical inputs; the maximum budget
holds; an unjustified escalation is detected; ablating the router yields a comparable
baseline.

**Slow path.** The candidate is evaluated in isolation; proposal and judgement are separate
components; a rejected candidate stays archived; adoption is versioned; rollback restores
body, tools and memory exactly.

**Architecture.** Replacing one specialist does not require changing the kernel; no component
is secretly omniscient; no external model is called implicitly; disabling detailed
journalling changes the evidence produced and not any decision.
