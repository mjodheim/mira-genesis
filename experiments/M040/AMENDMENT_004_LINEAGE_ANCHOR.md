# M040 development amendment 004 — lineage anchor plus bounded adaptation

**Status: committed before implementation and before seed 400046 is evaluated.**

Consumed seeds 400043 and 400045 showed that an entire earlier continuation can cease to
produce an admissible larger task on a changed parent. Consumed seed 400044 showed that,
when applicable, a transported motif can reduce search from 7,700 nodes to 3.

## Transported object

The causal object transferred after migration is now a **lineage anchor** derived solely from
pre-migration adopted continuation programs.

For every transported continuation program, enumerate every canonical contiguous fragment
that:

- preserves the original tool order;
- contains at least one `lineage_constructed` tool;
- contains no tool absent from the transported registry;
- has one or two tool symbols;
- is deduplicated by the ordered tool-ID tuple.

The packet remains unchanged. The anchors are derived only after packet validation from the
packet's continuation programs and registry provenance.

## New post-migration task family

After packet validation, the generator uses task-seed order to enumerate:

1. a lineage anchor;
2. a suffix of one or two protocol-supplied primitive tools;
3. the resulting program `anchor + suffix`.

It accepts the first program that:

- has total symbolic length at most 4;
- produces a strictly larger minimal DFA than the migrated parent;
- is not reached by birth-registry enumeration within the same 4,096-node budget and depth 4;
- yields a sound exact structural-incapacity certificate from the committed observations.

The selected suffix, target, target digest and successful candidate are not stored in the
packet.

## Complete arm

The complete arm derives the same anchors from the packet and evaluates them before generic
search. For each anchor it enumerates one- then two-symbol primitive suffixes in committed
registry order. Every anchor and suffix symbol consumes one symbolic-search node.

The accepted program must:

- begin with one derived lineage anchor;
- add one or two protocol-supplied suffix tools;
- contain at least one pre-migration lineage-owned tool;
- pass exact source equivalence and exact native synthesis on substrate B.

## Controls

All arms receive equal depth 4, 4,096 symbolic nodes, observations and evaluators.

- Fresh and learned-tool-ablated arms enumerate only the birth registry.
- Learning-state ablation receives the full registry but no anchor frontier and uses generic
  depth-first enumeration.
- Unchanged-parent and output-only controls remain as previously specified.

## Audit

The independent post-search audit must reproduce:

- anchor derivation order;
- every anchor expansion;
- every one- and two-symbol suffix expansion;
- every generic expansion and evidence rejection;
- counters, accepted IDs, exact verdicts and transcript digests.

## Verdict

The resource-bounded plasticity verdict from amendment 003 remains unchanged. In particular,
fresh and learned-tool-ablated controls must not reach exact quality within the equal 4,096
nodes, while the complete lineage must solve and use strictly fewer nodes than the memory
ablation.

## Consumed identity

The first implementation uses seed `400046`.

Seeds 400040–400045 remain consumed and cannot confirm this task family or budget.

## Scope

This tests bounded transfer of a reusable transformation motif plus one or two new operations.
It is not arbitrary strategy synthesis, unrestricted generalisation or open-ended evolution.
