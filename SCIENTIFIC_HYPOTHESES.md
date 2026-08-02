# Scientific hypotheses

Each status also states its **provenance**: `verifiable` if the frozen protocol, the
code and the sealed run all exist in this repository, `inherited` if the claim rests on
M001–M011, none of whose archives are versioned (see
[`archives/README.md`](archives/README.md)).

## H1 — Functional separation

A competence can be represented independently of the weights and architecture that
acquired it.

**Status:** validated only for the finite sequential competences of M001–M011.
**Provenance:** inherited, not verifiable here. Partly re-established by M013e, which
migrates an inherited competence exactly, without a task oracle.

## H2 — Heterogeneous re-embodiment

One passport can be executed by several computational physics without losing its
behaviour.

**Status:** validated within the finite contract of M010.
**Provenance:** inherited. Re-established verifiably by M013e across three families of
opaque Boolean machines.

## H3 — Portable plasticity

A re-embodied competence can receive a portable delta and evolve natively in each
substrate.

**Status:** validated **structurally**, not held **as to efficiency**.
**Provenance:** verifiable. M014b transported and executed the plasticity mechanism
exactly, 36/36, but the query-count advantage did not survive the distribution shift.
Transporting a policy does not imply transporting its efficiency.

## H4 — Autonomous morphogenesis

An organism can build its own body from a contract, primitives and a budget, without a
specialised compiler.

**Status:** validated within the finite domain.
**Provenance:** verifiable. M012b, sealed evaluation 36/36 and independent reproduction.

## H5 — Rich cognitive continuity

Memory, learning strategy, uncertainties and competences can survive a substrate change
together.

**Status:** not validated. Subject of M015, **deferred** behind M017 and M018.
**Reason for deferral:** transporting the memory of a closed-catalogue organism would
laterally extend a paradigm whose core is not established.

## H6 — Self-metamorphosis

An organism can diagnose a limit of its own body, propose descendants, evaluate them on
hidden tests and migrate to a better embodiment.

**Status:** not validated. **Blocked by H7**: an organism that cannot extend its
language cannot describe itself a body its primitives are unable to write.

## H7 — Self-extending language

An organism whose starting vocabulary holds only atoms can absorb the recurring
compositions of its environment, and gain expressive power it did not have.

**Status:** not validated, subject of M017, in development.
**Provenance:** verifiable. The development benchmark shows 0/42 for the closed
catalogue, 34/42 for open search at constant cost, and 37/42 for the self-extending
organism whose median cost falls from 4,222 to 43 nodes. No canonical result is claimed:
the protocol is not frozen.

H7 is not a new hypothesis for the project — it is the recognition that M017 was already
on the roadmap, and was badly placed on it.

## H8 — Scarcity is the missing mechanism

With no consequence to inefficiency, no efficiency mechanism pays off. Under real
scarcity, a selected population discovers ways of using the language that hand design
does not reach.

**Status:** **not tested.** M019 produced three degenerate rigs and none allows a
verdict. The hypothesis is neither supported nor refuted.
**Provenance:** verifiable. M018 measured that three hand-written forgetting mechanisms
did not pay off; the search budget there was 200,000 nodes and failure cost nothing. H8
holds that this is the explanation, rather than a property of the mechanisms.

What M019 established instead, and which was not in H8: **a short-horizon selection
selects for stagnation.** Learning costs immediately and pays later; a fitness observing
only one generation removes the learner before it repays. The evaluation horizon matters
more than the intensity of the pressure.

## H9 — The ways a measure comes loose are enumerable

The ways a proxy measure stops tracking the quantity it claims to track form a small,
identifiable-in-advance set, rather than an accident particular to each experiment.

**Status:** not validated. Six cases catalogued in [`MEASURES.md`](MEASURES.md), of
which four regularities already repeat: dynamic range not established, an incapable
baseline taken for a criterion, an incomplete verification procedure, a horizon shorter
than the payback period.

**Provenance:** verifiable, and this is what distinguishes this repository. Elsewhere, a
measure coming loose is noticed because a human finds the result suspicious; here
behavioural equivalence is provable, so the point where it comes loose can be located.

**What H9 does not claim:** neither the novelty of the problem — Goodhart, reward
hacking and quality-diversity have worked it for a long time — nor that a closed
enumeration is reachable. Only that these modes repeat often enough to be anticipated,
and that a decidable domain makes it possible to show so.

## H10 — Adaptive evaluation weighting can approximate maximum clade value

When productive descendants are already present, allocating finite evaluation evidence
according to individual observed performance makes clade aggregation behave more like
a soft maximum than uniform allocation does.

**Status:** not supported by the M028 development test.

**Pre-written implication:** on M026's mismatch rig after M027 coverage, adaptive
evaluation must improve median weighted-clade/exact-CMP concordance and final hidden
quality over uniform evaluation by at least 167 per mille, win at least 40 of 64 paired
seeds, and preserve the exact aligned control. The full conjunction and exclusions are
fixed in [`experiments/M028/PROTOCOL_DRAFT.md`](experiments/M028/PROTOCOL_DRAFT.md).

**Scope:** this is a mechanism hypothesis about a finite HGM-inspired adaptation, not a
claim about the complete HGM implementation or general metaproductivity.

**Result:** adaptive concordance remained negative at -478 per mille, only 40 per
mille above uniform. Median final hidden advantage was zero, with 2 wins, 60 ties and
2 losses. The adaptive policy allocated 34 per mille of its non-initial evaluations to
high-potential observed nodes versus 51 per mille under uniform allocation. Unequal
weighting by a misaligned proxy did not approximate the hidden clade maximum.

## H11 — Hidden-disjoint component probes expose reusable potential

When immediate performance rewards memorised shortcuts, a separate public suite that
tests generic motifs alone and under repetition routes evaluation toward reusable
lineages and improves observed clade guidance without exposing hidden cases.

**Status:** estimator implication supported, full M029 policy implication not
supported.

**Pre-written implication:** component-adaptive evaluation must shift at least 167 per
mille more observations toward high-potential observed nodes, achieve non-negative
clade/exact-CMP concordance with at least 167 per mille advantage, improve median final
hidden quality by at least 167 per mille and win at least 40 of 64 paired mismatch
seeds against the frozen M028 baseline. Probe disjointness, structural separation,
aligned equality and selector isolation must all pass. The full rule is fixed in
[`experiments/M029/PROTOCOL_DRAFT.md`](experiments/M029/PROTOCOL_DRAFT.md).

**Scope:** the component suite uses the finite rig's known public task grammar. H11 is
not a claim that the probe is a domain-independent measure of potential.

**Result:** component-adaptive concordance reached 699 per mille and exceeded the
development baseline by 1,177, but the allocation shift was only 92 per mille and the
paired final advantage remained zero, with 31 wins, 32 ties and 1 loss. The registered
conjunction therefore failed. The component-uniform diagnostic produced 50 wins,
14 ties and no losses, motivating an untouched-seed confirmation rather than a
retroactive change to H11.
