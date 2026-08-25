# M111 — can the lineage tell that it does not know?

**Hypothesis:** H56 · **Decision slot:** D080 (reserved) · **Track:** A — endogenous bounded lineage

M110 measured an acquired machinery improvement **doing harm**: outside its producer's attribution
census, `M1` and `M2` were confident, wrong, and strictly worse than the fresh `M0` they improved on.
Widening the census would not fix that. What would is a lineage that knows when to run an experiment
instead of committing.

## The impossibility is exhibited, not argued

In an ambiguous world there are two demands with the **identical feature row** `(F, T, T)` and
**different limiting components**. No function of the feature vocabulary can be right on both,
because the vocabulary gives them the same value. That is an information bound, and it is
demonstrated by showing the pair rather than by an argument about closure.

| arm | `A` | `B` |
|---|---|---|
| `M0` hardwired to the operator axis | refuse | refuse |
| `M1` generation 1 | refuse | refuse |
| `M2` generation 2, restored from M109's terminal state | **resolve** | refuse |
| `always_signal`, an authored fixed strategy | refuse | **resolve** |

## The probe

A **probe** extends one component, tests whether that would resolve the demand, and **rolls back**.
The serialized state before and after is compared in the record, so the rollback is measured rather
than promised. One probe settles the pair by elimination, and the milestone runs **both probe
orders** — with two live candidates either order is correct, which is how the order is shown to carry
no answer.

Probes are **scarce**: one per world, shared across a sequence. A policy that never spends is as
useless as one that always spends, and both are run as controls on the same budget.

## Generation 3, and why generation 2 had to happen first

The policy must fire on row 3 and not on row 7. Row 3 lies below row 7 componentwise, so **every
monotone program true at row 3 is true at row 7**.

M109's *terminal* state — reproduced here byte-exactly at `5c08fa30…` — already holds an operator the
lineage adopted for itself, `ACQUIRED_cfc43adf`, whose truth table is `[1, 0]`: **negation**, and
non-monotone. It entered because generation 2 widened the candidate space and the widened search took
it.

```text
gen 1   signal interface       rule space 18, monotone
gen 2   candidate space        the widened search adopts NOT
          -> rule space 18 -> 127, with 25 programs separating row 3 from row 7
gen 3   diagnostic policy      expressible for the first time, and acquired
```

Ablate generation 2 and the same acquisition is **refused**: 18 programs, none consistent, and no
operator in a monotone candidate space makes one. That is the depth-three dependency, by lemma.

## The record is pooled, and a measurement forced it

Across **1 160 worlds** — a 160-world census plus a 1 000-world search over both declared seed ranges
— row-3 ambiguity and row-7 reachability **never co-occur**. At roughly 6 per cent ambiguity and 36
per cent row-7 reachability, independence predicts about 25 such worlds and zero were found. In this
carrier the ambiguity that makes a probe necessary and the row that forces a policy out of the
monotone language do not live in the same world.

So the population has **two strata** and the record spans both: an *ambiguous* world contributes the
undetermined row, a *witness* world contributes row 7 as determined, and **one policy** is acquired
from the whole history. That is stronger than per-world fitting, not weaker.

## Files

| | |
|---|---|
| `PRE_REGISTRATION.md` | H56, the exhibit, P1–P24, and five corrections recorded before freeze |
| `ADVERSARIAL_REVIEW.md` | the strongest objections, and the ones that are conceded |
| `POPULATION.json` | three ambiguous and two witness worlds — worlds only, no census, no label, no pair |
| `ADMISSION_LOG.json` | which seeds landed in which stratum and why the rest landed in neither |
| `PROTOCOL.json` | the frozen protocol, once it exists |
| `RESULT.json`, `CHECK_REPORT.json` | the single canonical attempt and its single checker replay |

## Status

Pre-registered, apparatus complete, development rehearsal passed at 22/24 with only the
development-tag and no-replay predicates false. **No protocol and no result exist until the owner
authorizes a freeze.**

## What a positive M111 would not license

Open-ended machinery growth; unbounded recursive depth; autonomous invention of the registry, the
feature vocabulary, the probe primitive or the carrier; independent external-domain transfer;
G1–G10 closure; general-agent evidence; AGI.

The defensible phrasing is **bounded self-directed diagnosis and acquisition-machinery adaptation at
recursive depth three**, and nothing stronger.
