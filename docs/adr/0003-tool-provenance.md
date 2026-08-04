# ADR 0003 — Tool provenance, and what the lineage may claim to own

**Status: accepted for development implementation.**

This authorises the canonical serialisation, the append-only journal, its integrity tests,
the projected archive and the checkpoint structures. It does **not** authorise opening a
sealed block, any M038 claim, freezing the protocol, or changing a rule after observing a
future block.

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

An earlier draft used one exclusive enum — `primitive_tool`, `composed_tool`, `learned_tool`,
`external_development_tool`. Those are not points on a single axis. A primitive is almost
always designed externally yet is legitimately committed as the initial language; an external
tool added *after* the freeze is forbidden. One label cannot express both facts.

Provenance is therefore recorded on **three independent axes**:

```
ToolProvenance
- origin:              protocol_supplied | lineage_constructed | external_development
- construction_kind:   primitive | composition | accepted_transformation_trace
- introduction_phase:  birth | cycle | post_run
- introduced_by_event
- protocol_commitment
- eligible_for_gate2
```

`eligible_for_gate2` is **computed, never assigned**:

```
origin == lineage_constructed
  and introduced_by_event is a valid construction event in the journal
  and every construction input belongs to the committed registry
  and the tool was causally required
```

The construction event names the lineage, the generation and the primitives consumed. A tool
with no such event cannot be `lineage_constructed`, whatever its contents.

## Absorbing a trace is not the same as building a tool

A trace absorbed after adoption becomes a tool available *afterwards*. It was not
necessarily a tool that helped build the thing it came from.

Gate 2 requires that at least one tool be constructed or composed by the organism **during**
the evaluation lineage and used to inspect, transform, build or test a candidate. Under a
single cycle, that is approachable only if a tool is:

1. composed during the slow path;
2. causally used to inspect, construct or test the candidate;
3. shown necessary by ablation.

Registering a tool with `construction_kind = accepted_transformation_trace` after adoption
satisfies none of these: `introduction_phase` records that it arrived too late to have built
what it came from. M038 must therefore not describe Gate 2 as "addressable" without this
causal criterion attached.

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
provenance
- origin
- construction_kind
- introduction_phase
- introduced_by_event
- protocol_commitment
- eligible_for_gate2
```

The artifact carried a single `provenance_category` field until this revision — the very
exclusive label the decision above replaces. A one-axis field cannot express that a
primitive is externally designed *and* legitimately part of the initial language, while an
externally written tool added after the freeze is not.

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

Restated on the three axes. The earlier list still named `composed_tool`, `learned_tool` and
`external_development_tool` — the exclusive categories this ADR abandoned.

- a tool cannot be `origin = lineage_constructed` without a valid construction event in the
  journal naming the lineage, the generation and the primitives consumed;
- `origin = external_development` is never `eligible_for_gate2`, whatever its
  `construction_kind` or contents;
- `origin = protocol_supplied` may belong to the initial language and never counts as
  autonomous construction;
- `eligible_for_gate2` is recomputed from the other axes and the journal; a supplied value is
  ignored, and a supplied value disagreeing with the computed one is an error;
- a trace absorbed after adoption is not counted as a tool that enabled that same adoption;
- reuse is reported only when the tool proposed a step of the adopted trace, and a tool
  absorbed by the current cycle is not reuse of an earlier one;
- ablating a tool removes the causal role claimed for it, and the difference — or its absence
  — is measured and reported;
- the registry states which cost rule is in force when any reachability claim is made.
