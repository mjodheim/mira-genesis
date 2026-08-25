# M110 — does the acquired machinery work outside the laboratory that produced it?

**Hypothesis:** H55
**Decision slot:** D079 (reserved; unfilled until a canonical result exists)
**Track:** A — endogenous bounded lineage
**Pre-registration date:** 25 August 2026
**Status:** **PRE-REGISTERED QUESTION; NO PROTOCOL, POPULATION OR RESULT EXISTS**

## The objection M109 leaves standing

M109/H54 (D078) qualified two successive lineage-acquired machinery generations: the lineage
determined its own blame labels by controlled trial, generation 1 modified the signal interface,
generation 2 modified the candidate space, and `ReachImprove` grew 6 ⊂ 20 ⊂ 243.

Every part of that happened inside one three-signal Boolean laboratory. The strongest remaining
objection is therefore not "can it do it a third time?" but:

> **This mechanism works because the laboratory was built for it.**

M110 attacks that objection directly, and only that one. It does not add a generation, does not widen
the registry and does not touch M109, which is frozen.

## The question

> Can a machinery modification acquired over M107 → M108 → M109, restored from its own frozen lineage
> state, causally change acquisition capability in a **materially different consumer family that took
> no part in producing it** — and if so, exactly where does that capability stop?

The second half is not a hedge. It is half the hypothesis.

## H55

**H55.** Restored M109 lineage state changes acquisition capability in the consumer family in a
**direction determined by the producer's own attribution census**:

- **H55-a (positive transfer).** On consumer demands whose failure feature row lies **inside** the
  producer's reachable attribution census, the restored cascades strictly increase resolved
  capability: `M0` refuses, `M1` resolves the row-7 demand, and only `M2` resolves the row-3 demand.
- **H55-b (negative transfer).** On a consumer demand whose failure feature row is **outside** the
  producer's reachable attribution census, the restored cascades strictly *decrease* resolved
  capability: a fresh `M0` resolves it and both `M1` and `M2` refuse.

H55 is refuted if either half fails, and either failure is a publishable qualified result. H55-a
failing means the acquired machinery is a Boolean-curriculum artefact. H55-b failing means the
conservative-adoption guarantee extends further than its own derivation licenses.

## Why row 5 is the whole experiment

The producer's feature vocabulary is three booleans, fixed at M109 and unchanged here:

| | |
|---|---|
| `g0` | the demand needs a signal the interface cannot read |
| `g1` | the candidate search for this demand exhausted without success |
| `g2` | some candidate strictly enlarges reach (demand-independent distractor) |

`¬g1 ⟹ g2` holds in **any** domain implementing these semantics: if an operator addition reaches an
unheld target, one-step reach strictly exceeds the held image. Rows 0 and 4 are therefore impossible
everywhere, not merely unobserved.

In the producer's Boolean world the interface truncates the signal row and every expression is
lifted, so **`g0 ⟹ g1`** as well: no operator can recover a signal the interface does not read. That
extra implication is a property of *that laboratory*, not of the vocabulary. It is why the M109
census found rows `{1, 2, 3, 6, 7}` reachable and rows `{0, 4, 5}` not.

Conservative adoption pins an acquired rule only on rows the census declares reachable. **Row 5 was
never pinned.** Yet the adopted generation-1 rule is the program `g0 ∧ g2`, and a program has a value
everywhere:

| row | (g0,g1,g2) | in producer census | `M0` | `M1` | `M2` |
|---|---|---|---|---|---|
| 3 | (F,T,T) | yes | operator table | operator table | **candidate space** |
| 7 | (T,T,T) | yes | operator table | **signal interface** | **signal interface** |
| **5** | **(T,F,T)** | **no** | operator table | **signal interface** | **signal interface** |

A consumer family in which `g0 ⟹ g1` fails makes row 5 reachable, and at row 5 the acquired rule
fires on evidence it never had. That is the experiment.

## The consumer family, and why it is materially different

**Reference-bearing records over a four-valued chain, transformed by synthesized Python.**

| | producer (M107–M109) | consumer (M110) |
|---|---|---|
| carrier | truth tables | JSON documents plus a side table |
| values | `{False, True}` | the chain `0 < 1 < 2 < 3` |
| world | all 2³ signal rows | five authored documents |
| target | a 3-signal Boolean function | a 5-tuple over the chain, 1 024 per world |
| held operators | `AND`, `OR` | `MIN`, `MAX` on the chain |
| adoptable | 1- and 2-ary Boolean operators | unary chain maps, and **accessors** |
| information boundary | prefix truncation of the signal row | **reference dereference into a side document** |
| execution | truth-table application | expression rendered as Python source, `compile`d and `exec`d |

The load-bearing difference is the last-but-one row. A document's `zeta` lives in a *different
document*, reached by following its `ref`. No interface width exposes it; only adopting an
**accessor** does. That single structural fact decouples "the interface cannot read it" from "no
operator can reach it", breaks `g0 ⟹ g1`, and makes row 5 reachable. It is a property of references,
which the producer's world does not have.

## What transfers, and what is authored on both sides

**Transferred (the claim).** Exactly the rule cascade, restored from `experiments/M109/RESULT.json`
and digest-verified to reproduce the frozen `M1` and `M2` state digests. Attribution is performed by
calling `m109_runtime.attribute` unchanged. A reimplementation would end the chain.

**Authored on both sides, and excluded from the claim (the adapter).**

- the three-component registry `{operator_table, signal_interface, candidate_space}` and its names;
- the three-feature vocabulary and its declared semantics;
- the consumer carrier, its documents, bounds, candidate spaces and evaluator.

The adapter is **identical across all three arms** — the arms' serialized states differ in the
`rules` field and nowhere else, and that is a measured predicate. The adapter is **non-informative
about the answer**, and row 5 is the proof: `g0` is true there while the correct component is the
operator table, so no feature determines a component by itself.

The consumer runtime must contain no producer-domain constant: no Boolean world, no M109 target,
no rule body, no truth table, no digest. A boundary audit measures this in both directions.

## Impossibility, not "not found in the budget"

Three lemmas, each budget-independent, each measured on every world:

1. **Visible-function lemma.** Every member of the image at interface width `w` is a function of the
   visible signals. A target that is not is outside the image at every bound and for every operator
   set reachable without an accessor. *Closes the row-7 demand against `M0` and the row-5 demand
   against `M1`/`M2` after they widen the interface.*
2. **Monotone-closure lemma.** `MIN`, `MAX`, every monotone chain map and every coordinate accessor
   are monotone in the full signal vector, and monotone functions compose. Every target reachable
   through the monotone candidate space is therefore monotone. A non-monotone target is excluded from
   the operator axis at every bound. *Closes the row-3 demand against `M0` and `M1`.*
3. **Fixed-point.** Images are identical at node bounds 7, 9, 11 and 13, so the declared bound records
   closure rather than a search budget.

A deeper-bound control at 13 nodes is carried as a second line of defence, not as the argument.

## The population

Consumer worlds are authored by a declared deterministic generator and admitted by a criterion that
mentions **only consumer census structure** — never the arms, never the restored rules:

- the attribution census is complete over all 1 024 targets and every declared probe state;
- **no feature row carries more than one label**;
- rows 3, 5 and 7 are each reachable with a determined label at the base state.

Development and canonical worlds come from disjoint declared seed ranges. The canonical population is
fixed at freeze time. The canonical demand for a row is the **lexicographically least** determined
target at the base state carrying that row — a rule that cannot see the arms.

## Decisive conditions

P1–P24 are computed by an independent checker from the preserved result. Every one is a measurement.

| | |
|---|---|
| P1 | input preflight confirmed: population canonical, seeds disjoint, no producer fixture reachable |
| P2 | the restored `M0`/`M1`/`M2` reproduce the frozen M109 state digests exactly |
| P3 | the boundary audit confirms no producer-domain constant in the consumer runtime or population |
| P4 | the three arms' serialized states differ in the `rules` field and in no other field |
| P5 | the image is a fixed point at bounds 7, 9, 11, 13 on every canonical world |
| P6 | the monotone-closure certificate confirms on every canonical world |
| P7 | the visible-function lemma holds on every canonical world at both interface widths |
| P8 | the attribution census is complete, with no ambiguous row, on every canonical world |
| P9 | row 5 is reachable in the consumer census and absent from the producer's reachable rows |
| P10 | consumer row labels agree with the producer census on every row both censuses reach |
| P11 | row-7 demand: `M0` refuses on every canonical world |
| P12 | row-7 demand: `M1` and `M2` resolve and execute to target on every canonical world |
| P13 | row-3 demand: `M0` and `M1` refuse on every canonical world |
| P14 | row-3 demand: `M2` resolves and executes to target on every canonical world |
| P15 | row-5 demand: `M0` resolves and executes to target on every canonical world |
| P16 | row-5 demand: `M1` and `M2` refuse on every canonical world |
| P17 | deeper-bound control: `M0` still refuses the row-7 and row-3 demands at 13 nodes |
| P18 | conservation: every row-1 demand `M0` resolves is also resolved by `M1` and `M2` |
| P19 | ablation is byte-exact in both directions, and each removal loses exactly its own demand |
| P20 | mutation of the generation-2 rule causally changes `M2` on the row-3 demand; corruption fails closed |
| P21 | `ReachImprove` is strict, `M0` ⊂ `M1` ⊂ `M2`, on every canonical world |
| P22 | every process isolated, zero model/network/remote calls, replay performed and equal |
| P23 | a host-widened candidate space resolves the row-3 demand and a host-widened interface resolves the row-7 demand |
| P24 | the recorded attribution map recomputes exactly from the restored truth tables, in the checker, importing nothing |

P21 with P16 is the dissociation this milestone exists to measure: **capacity may rise while realized
competence falls.**

## Corrections recorded before freeze

Recorded here because they change what the result can mean, and they were made before any protocol,
population or result existed.

**Correction 1 — the claim is not "transfer works".** The first draft pre-registered only H55-a and
treated a row-5 failure as a limitation to disclose. That is backwards: the row-5 outcome is derivable
from the adopted rule and the census before any consumer world is run, so pre-registering only the
positive half would have hidden the derivation behind a result. Both halves are hypotheses, and the
negative half is stated as strongly as the positive one.

**Correction 2 — the domain is chosen to reach row 5, and this is declared.** The consumer family was
not chosen neutrally: references were chosen *because* they break `g0 ⟹ g1`. That is a deliberate
stress test, not a neutral sample, and the claim is correspondingly conditional. What is **not**
tuned is the row → component map, which is measured per world by the consumer's own trial and is not
consulted when admitting a world.

**Correction 4 — two predicates could not fail, and one ceiling was implicit.** The first draft of
the apparatus carried a capsule-equality field asserting `len(group) >= 1` and a delegation field
comparing module names. Neither could be falsified by any arrangement, which is the defect M095
recorded as "record fields that are assertions disguised as measured booleans". Both are replaced:
capsules are grouped by the world and demand bytes they share, so a group must hold one capsule
per arm with pairwise-distinct state bytes; and the full attribution map is recorded and
recomputed by the checker from the restored truth tables alone. Separately, the host could always
have widened either component itself. Leaving that implicit would have let a reader hear a claim
about an extension the host cannot supply, so it is now measured as **P23** and the claim is
explicitly about *which component the restored cascade decides to extend*, not about reach the
host lacks. P23 and P24 raise the predicate count from 22 to 24, before any protocol exists.

**Correction 3 — "materially different" is bounded by shared vocabulary.** The registry names and the
feature vocabulary are shared authored vocabulary, not transferred content. M110 cannot claim that a
lineage would discover this vocabulary, nor that the consumer family is independently maintained. It
is project-authored, and G4 does not advance.

## What a positive M110 would not license

Independent external-domain transfer; open-ended or unbounded machinery growth; recursive depth of
three; measured acceleration; autonomous invention of the registry, the feature vocabulary or the
carrier; G1–G10 closure; general-agent evidence; self-hosting; AGI.

The defensible phrasing is **bounded multi-generation acquisition-machinery improvement with
census-conditional causal transfer**, and nothing stronger.

## Attempt discipline

One canonical attempt and one canonical checker replay. The first result is preserved even if
negative, and may not be repaired, relabelled or rerun. M109 and every earlier frozen artefact are
untouched.
