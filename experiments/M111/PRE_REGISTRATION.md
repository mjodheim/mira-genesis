# M111 — can the lineage tell that it does not know?

**Hypothesis:** H56
**Decision slot:** D080 (reserved; unfilled until a canonical result exists)
**Track:** A — endogenous bounded lineage
**Pre-registration date:** 25 August 2026
**Status:** **PRE-REGISTERED QUESTION; NO PROTOCOL, POPULATION OR RESULT EXISTS**

## What M110 leaves behind

M110/H55 (D079) measured an acquired machinery improvement **doing harm**: at a failure row outside
the producer's attribution census, `M1` and `M2` were confident, wrong, and strictly worse than the
fresh `M0` they improved on. `ReachImprove` rose across the chain while realized competence fell.

The obvious repair — widen the census — misses the point. The deeper question is whether the lineage
can tell **when its own observation does not determine the answer**, and spend an experiment there
instead of committing.

## The question

> Can a lineage acquire, from its own record, a policy that identifies the failure rows its feature
> vocabulary does **not** determine, and spend a scarce diagnostic budget exactly on those — resolving
> demands that every static strategy over that vocabulary provably cannot?

## The impossibility is exhibited, not argued

In an ambiguous consumer world there exist two demands, **in the same world**, with the **identical
feature row** `(F, T, T)` and **different limiting components**:

| demand | target | feature row | limiting component |
|---|---|---|---|
| `A` | least row-3 target resolved by the candidate space | `(F,T,T)` | candidate space |
| `B` | least row-3 target resolved by the signal interface | `(F,T,T)` | signal interface |

No function of the feature vocabulary can be right on both, because the vocabulary assigns them the
same value. This is not a search bound and not a budget bound — it is an information bound, and it is
demonstrated by exhibiting the pair rather than by an argument about closure.

Every static arm therefore fails at least one, and which one it fails is determined by its rule:

| arm | `A` | `B` |
|---|---|---|
| `M0` hardwired to the operator axis | refuse | refuse |
| `M1` generation 1 | refuse | refuse |
| `M2` generation 2, restored from M110 | **resolve** | refuse |
| a fixed always-signal strategy | refuse | **resolve** |

## The probe

A **probe** extends one registered component, tests constructibility, and **rolls back**. It is an
experiment, not an adoption: the state after a probe is byte-identical to the state before it, and
that is a measured predicate. One probe distinguishes the two candidates at row 3 by elimination —
if widening the candidate space does not reach the target, the interface is the answer.

Probes are **scarce**. Each world grants a budget of exactly one. A demand sequence poses one
determined-row demand and one ambiguous-row demand, and the milestone runs **both orders**, so that
an always-probe strategy succeeds in one order and fails in the other while a correct policy succeeds
in both.

## Generation 3, and why generation 2 had to happen first

The policy must fire on row 3 and not on row 7. Row 3 is `(F,T,T)` and row 7 is `(T,T,T)`, so row 3
lies below row 7 componentwise and **every monotone program true at row 3 is true at row 7**. The
lineage holds `{MIN, MAX}`; its rule space is the monotone image of those operators.

Measured before this pre-registration was written, and stated here as a prediction the canonical run
must reproduce:

| | |
|---|---|
| monotone rule space | 18 programs |
| of those, firing at row 3 but not row 7 | **0** |
| after adopting one non-monotone operator | 127 programs |
| of those, firing at row 3 but not row 7 | 25 |

Non-monotone operators exist **only in the complete candidate space**, and the complete candidate
space is what generation 2 acquired. So generation 2 does not merely precede generation 3 in time: it
**creates the expressibility** of generation 3. That is the monotonicity lemma applied one level
further out than M109 applied it — to the policy language rather than to the attribution cascade.

```text
gen 1   signal interface        (M108/M109)
gen 2   candidate space         (M109)
          -> the complete space admits non-monotone operators
          -> adopting one takes the rule space 18 -> 127
          -> the diagnostic policy becomes expressible for the first time
gen 3   diagnostic policy       (M111)
```

## H56

**H56-a (acquisition).** From a record the lineage produces itself — episodes in which it observed one
feature row resolve through more than one component — it acquires a policy firing on exactly the rows
its record shows undetermined, and that policy is inexpressible in the rule space it held before
generation 2.

**H56-b (competence).** The lineage holding that policy resolves both `A` and `B` on every canonical
world and in both demand orders, while every static arm and both fixed probe strategies fail at least
one, under an equal total probe budget.

**H56-c (depth).** The dependency from generation 2 to generation 3 is a lemma over the rule space,
not a failed search, and is measured as such.

H56 is refuted if any half fails, and any failure is a publishable qualified result.

## What is authored, and declared

- the fourth registry entry `diagnostic_policy` and the other three component names;
- the three-feature vocabulary, unchanged since M108;
- the consumer carrier, inherited unchanged from M110;
- the probe primitive, the probe budget of one, and the two demand orders;
- the ambiguous-world admission criterion.

The lineage is not told which row is ambiguous, is not told which component is limiting, and receives
no episodes fixture. Probes are the only way it can learn either, and they are counted.

## Decisive conditions

P1–P24, computed by an independent checker from the preserved result.

| | |
|---|---|
| P1 | input preflight confirmed; population canonical; seeds disjoint; no producer fixture reachable |
| P2 | the restored `M0`/`M1`/`M2` reproduce the frozen M109 state digests, and M110's result bytes are bound |
| P3 | boundary audit confirms no producer-domain constant in the M111 runtime or population |
| P4 | all arms share one adapter and differ only in declared lineage state |
| P5 | every ambiguous canonical world exhibits `A` and `B` with the identical feature row and different components |
| P6 | ambiguity is confirmed by a complete census on every ambiguous world, and row 7 is determined on every witness world |
| P7 | the monotone rule space holds **zero** programs firing at row 3 and not row 7 |
| P8 | the M109 terminal state, reproduced at digest `5c08fa30…`, already holds the lineage's own non-monotone operator, and its policy rule space is 127 with at least one separating program |
| P9 | non-monotone operators are absent from the monotone candidate space and present in the complete one |
| P10 | the acquired policy is expressible only in the post-generation-2 rule space |
| P11 | one policy is acquired from a single record pooled across the whole population, with no episodes fixture present |
| P12 | the acquired policy fires on every undetermined observed row and on no determined observed row |
| P13 | a probe leaves the state byte-identical: it is an experiment, not an adoption |
| P14 | `M0`, `M1` refuse both `A` and `B` on every world |
| P15 | `M2` resolves `A` and refuses `B` on every world |
| P16 | a fixed always-signal strategy resolves `B` and refuses `A` on every world |
| P17 | the diagnostic lineage resolves both `A` and `B` on every world, in both demand orders |
| P18 | never-probe fails the ambiguous demand in both orders |
| P19 | always-probe fails the ambiguous demand when the determined demand comes first, in both probe orders, on the same total budget |
| P20 | every arm starts from the same probe budget, and the diagnostic arm never spends more probes than the always-probe arm |
| P21 | ablation of generation 3 is byte-exact and loses exactly the ambiguous demand |
| P22 | mutation of the acquired policy changes behaviour causally; corruption fails closed |
| P23 | earlier capabilities are conserved: every demand `M2` resolved is still resolved |
| P24 | every process isolated, zero model/network/remote calls, replay performed and equal |

## Pre-registered measurements that are not conditions

Recorded because a claim of acceleration must survive them, not because they decide the verdict:

- probes consumed per world and per arm;
- rule-space size before and after the non-monotone adoption;
- candidates examined during each acquisition;
- episodes consumed before the policy became derivable;
- `ReachImprove` for each arm.

Acceleration is reported if it appears and reported as absent if it does not. **Three generations do
not license the word "compounding" and never will without a pre-registered trend across generations
that survives its controls.**

## Corrections recorded before freeze

**Correction 1 — the non-monotone operator was already the lineage's own, and this is stronger than
what was first written.** The draft above describes M111 adopting a non-monotone operator to make the
policy expressible. That is not what the record shows. M109's *terminal* state — the state after
generation 2 resolved stage two, reproduced here byte-exactly at digest `5c08fa30…` — already holds
an operator the lineage acquired for itself, named `ACQUIRED_cfc43adf`, whose truth table is `[1, 0]`:
**negation**, and non-monotone. It entered the table because generation 2 widened the candidate space
and the widened search adopted it.

So the enabling step is not an M111 act at all. Generation 2 enlarged the policy language **as a side
effect of resolving its own demand**, from 18 programs to 127, of which 25 separate row 3 from row 7.
M111 inherits that and acquires generation 3 inside it. The predecessor is therefore the M109
terminal state and not the state at generation 2's adoption, and the ablation control removes
generation 2 *and the operator it brought*, which is what the dependency actually is.

**Correction 2 — the acquired policy fires on row 2 as well as row 3, and row 2 is unreachable.**
Conservative adoption pins a policy only on rows the record observed. Row 2 is `(F,T,F)`, and `¬g1`
implies `g2` in any domain implementing these features, so every reachable row here is odd and row 2
never arises. The policy firing there is unobservable rather than harmless-by-argument, and it is
disclosed rather than trimmed. **P12 is therefore stated over observed rows**, not over all eight.

**Correction 3 — the always-probe control must be run in both demand orders.** A single order would
let a reader believe the control fails for a reason of principle. It does not: it fails because it
spends a scarce budget on the first demand it meets. Both orders are run and both are reported, so
the control's order-dependence is visible instead of hidden, and the acquired policy's
order-independence is a measurement rather than a claim.

**Correction 4 — P20 as first written was false.** It said probe counts are equal between the
diagnostic arm and the fixed probe arms. The never-probe arm spends zero by construction, so no
run could ever satisfy that, and a predicate that cannot be true is as useless as one that cannot
be false. What the equalization claim actually needs is that no arm is handed a larger budget and
that the diagnostic arm does not buy its result with extra experiments. P20 now states exactly
that, and it is stated before any protocol exists.

**Correction 5 — the record is pooled across the lineage's worlds, because in this carrier no single
world can hold the barrier.** The design above acquired one policy per world. A pre-freeze survey of
**160 independently generated worlds** measured why that cannot work here:

| structure | worlds |
|---|---|
| rows `{1,3}` only | 96 |
| rows `{1,3,5,7}` | 44 |
| rows `{1,3,7}` | 13 |
| rows `{1,3,5}` | 7 |
| row 3 ambiguous | 10 |
| **row 3 ambiguous *and* row 7 present** | **0** |

Row 7 is reachable in 57 of 160 worlds and row 3 is ambiguous in 10, so independence would predict
about 3.6 co-occurrences. Zero were observed.

A second, wider search then scanned **1 000 further worlds** across both declared seed ranges — 500 in
the development range and 500 in the canonical range — looking for a single world carrying both. It
found **none**. Over **1 160 worlds** in total, at roughly 6 per cent ambiguity and 36 per cent row-7
reachability, independence predicts about **25** co-occurrences and **zero** were observed.

This is not rarity. In this carrier the ambiguity that makes a probe necessary and the row that
forces a policy out of the monotone language **do not co-occur in one world**, and no amount of
searching will produce one.

The repair is not to weaken the requirement, which would delete the depth-three claim. It is to
notice that a lineage does not live in one world. Its record spans everything it has met, so episodes
are **pooled across the population** and one policy is acquired from the whole history: an *ambiguous*
world contributes the undetermined row, a *witness* world contributes row 7 as determined, and the
pooled requirement is exactly the one no monotone program satisfies.

This is a stronger claim than the per-world one, not a weaker one: a single policy must hold across
every world in the population rather than being refitted for each. The population is therefore
declared in **two strata**, both admitted on structure only:

- **ambiguous worlds** — the only ambiguous base-state row is row 3;
- **witness worlds** — row 7 is present and determined at the base state.

Competence is measured on the ambiguous worlds, because that is where `A` and `B` live. The 160-world
measurement is recorded here rather than in a result, because it is what motivated the design and it
was taken before any protocol existed.

## What a positive M111 would not license

Open-ended machinery growth; unbounded recursive depth; autonomous invention of the registry, the
feature vocabulary, the probe primitive or the carrier; independent external-domain transfer;
G1–G10 closure; general-agent evidence; self-hosting; AGI.

The defensible phrasing is **bounded self-directed diagnosis and acquisition-machinery adaptation at
recursive depth three**, and nothing stronger.

## Attempt discipline

One canonical attempt and one canonical checker replay. The first result is preserved even if
negative and may not be repaired, relabelled or rerun. M109 and M110 are frozen and are not touched.
