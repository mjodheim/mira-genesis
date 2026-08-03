# ADR 0003 — Tool provenance, and what the lineage may claim to own

**Status: accepted for M038. No mechanism implemented yet.**

## Context

Gate 2 reserves a specific thing for the organism:

> Every operation used to inspect, transform, build or test a candidate body is present in
> the organism's serialised tool registry. External infrastructure may execute a tool, but
> may not invent its transformation or choose its arguments on the organism's behalf.
>
> At least one required tool must be constructed or composed by the organism from more
> primitive tools during the evaluation lineage.

`ToolRegistry` in `m020_self_rewrite.py` stores primitives and learned patches. It records
what a tool *is* and nothing about where it came from. That gap is the single largest
methodological risk in the prior-art integration, and it is not hypothetical: this
repository is developed with an assistant that writes code into it.

**A tool written during development and committed to the repository must never become, by
its presence alone, a tool learned by the lineage.**

## Decision

Every registry entry declares its provenance as exactly one of:

| Category | Meaning | Counts toward Gate 2? |
|---|---|---|
| `primitive_tool` | given at birth, part of the declared body language | no — it is the floor |
| `composed_tool` | built by the organism from primitives during the lineage | **yes** |
| `learned_tool` | absorbed from an accepted transformation trace | **yes** |
| `external_development_tool` | written by a human or an assistant outside the lineage | **never** |

The category is not a label attached afterwards. It is determined by the **construction
event** in the causal journal, which names the lineage, the generation and the primitives
consumed. A tool with no construction event in the journal cannot be
`composed_tool` or `learned_tool`, whatever its contents.

## Artifact

```
tool_id
version
source_or_ir
input_schema
output_schema
preconditions
postconditions
substrate_requirements
construction_trace
proposing_lineage
validation_cases
replay_digest
cost_model
known_failure_modes
supersedes
provenance_category
```

The registry must be able to prove: who built the tool, from which primitives, when it was
adopted, when it was reused, what happens under ablation, and how it transports to another
substrate.

## What the existing measurements already say about tool value

Two results bound what a registry can be expected to deliver here, and both must appear in
any report using it.

**Under the current cost rule, a learned tool adds nothing to the reachable set.** M034
measured identical reachable sets with and without the tool, at every budget. A learned tool
is a composition of primitives charged what those primitives cost, so anything it reaches
was already reachable. It reorders search; it cannot extend reach.

**Charging a macro as one edit does extend reach** — 2/16 to 4/16 at budget 1, 7/16 to 10/16
at budget 3, with the old set a proper subset. M017's structural language already does this:
`walk` counts depth in *symbols*, and a macro is one symbol however many atoms it unfolds.

So a Voyager-style registry is decorative in M020's rewrite kernel and load-bearing in
M017's structural language. The ADR does not resolve that difference; it requires any report
to state which cost rule is in force.

## Reuse must be causal, not incidental

"Tool reused" is not "tool present in the registry when the task was solved". It requires
that the adopted trace was **proposed by** that tool.

`RewriteResult.reused_learned_tools` already records this: tools that existed before the
search and proposed a step of the adopted trace. A tool absorbed by the current cycle is
explicitly not counted as reuse of an earlier one.

Gate 9 requires a later cycle to reuse or extend a tool learned earlier. That claim rests on
this field, and on nothing weaker.

## Alternatives rejected

**Infer provenance from the tool's shape.** Rejected: a hand-written tool and a composed one
can be textually identical. Only the construction event distinguishes them.

**Treat an assistant-written tool as a primitive.** Rejected: it would silently widen the
declared body language, and every reachability result is stated relative to that language.

**One flat registry with no categories.** Rejected: it is exactly how the current registry
lost the distinction, and it makes a Gate 2 claim unfalsifiable.

**Count registry membership as reuse.** Rejected: it would let a tool that never fired be
reported as causally responsible.

## Test obligations

- a tool without a construction event cannot be categorised `composed_tool` or
  `learned_tool`;
- an `external_development_tool` never counts toward a Gate 2 claim;
- reuse is reported only when the tool proposed a step of the adopted trace;
- a tool absorbed by the current cycle is not counted as reuse of an earlier one;
- ablating a tool produces a measurable, reported difference — or its absence is reported;
- the registry states which cost rule is in force when any reachability claim is made.
