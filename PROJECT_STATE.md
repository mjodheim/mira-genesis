# Mira Genesis — Project state

## Central question

**When does a proxy measure stop tracking what it claims to track, and under what
optimisation pressure?** Asked in a domain where ground truth is decidable, so the
answer is proved rather than estimated.

See **D011**, **H9** and [`MEASURES.md`](MEASURES.md).

## The original goal, now the testbed

Build an intelligence able to learn in a substrate A, discover an unknown substrate B,
construct a new body there, then transfer its competences, memory and plasticity so it
keeps learning without human architectural intervention.

That line produced two sealed validations, a decidable domain, and four failures **none
of which was in the organism**. It remains the testbed; it is no longer the question.

## State on 1 August 2026

- Last validated experiment: **M013e — sealed migration to an opaque substrate**, within its finite domain
- M012b: **VALIDATED — BOUNDED FINITE DOMAIN**
- M013e: **VALIDATED — BOUNDED FINITE OPAQUE SUBSTRATE**
- M014b: **FAILED — PORTABILITY WITHOUT GENERALIZABLE LEARNING ADVANTAGE**
- M014c: **HALTED — SUPERSEDED BY M017**, never evaluated
- M017: **READY TO FREEZE**, criterion turned directional after a 50-environment sweep
- M018: **HYPOTHESIS NOT SUPPORTED** — destroying does not restore improvement
- M019: **RIG NOT VALID** — selection too impatient to value learning
- Active: **M021 — do these selection measures move true quality?**
- Overall: **a bounded, decidable research laboratory, two sealed validations, six catalogued cases of measures that came loose from what they claimed to measure**

## Direction correction — 31 July 2026

The whole M012b → M014c chain rested on a limit no criterion measured: **the organism
can only express what was hand-written for it.** M014c's identification enumerates
exactly twelve structural programs; its learning is only a reweighting of counters over
that closed catalogue.

M014c is therefore halted before evaluation and replaced by M017 — self-extending
language — whose starting vocabulary holds only atoms, where anything beyond an atom
must be built and can then be absorbed. The roadmap changes order, not names: M015 and
M016 move behind M017 and M018.

See D009, D010, `ROADMAP.md` and `experiments/M017/`.

## M017 development

42 episodes, three environments. The closed catalogue — M014c's capability — solves
**none**. Open search without absorption solves 34, at constant cost. The
self-extending organism solves 37, and its median search cost falls from 4,222 nodes
over the first half of the episodes to **43** over the second, while open search stays
flat.

9/9 exact reincarnations across three opaque machine families, archive intact, 4/4
abstentions on the negative controls, zero false successes.

**All six freeze gates are passed.** The complete protocol, thresholds included, awaits
a human signature in `experiments/M017/FROZEN_PROTOCOL_017_CANDIDATE.md`. No canonical
evaluation is permitted before it: freezing commits thresholds that will not move, and
the evaluation runs only once.

Three measurements changed the protocol along the way:

- **the initial decisive statistic was rejected by measurement.** Unpaired: 2.4× to
  605× depending on the environment. Paired episode by episode: 95× to 620×. Dispersion
  divided by thirty-eight without the median moving;
- **the threshold did not survive a wider sweep.** Over 50 environments the minimum
  falls to **9.0×**, below the proposed 10×. The criterion became directional — 50/50
  environments favourable, dispersion zero;
- **an extended language does not transport.** A library inherited from an environment
  with disjoint motifs gives 0.69×, strictly worse than no library at all, four times
  out of four. Its macros never apply and still inflate the branching factor.

The claimed scope is therefore restricted in advance: the language grows **inside** a
distribution of transformations, and its advantage follows only if the destination
shares that structure.

## M014b canonical result

M014b transported a serialised plasticity passport with twelve inherited competences to
three sealed opaque machines. For each behavioural modification, Genesis received only a
query oracle.

What succeeded:

- 36/36 complete chains exact;
- 12/12 on each machine;
- old and new bodies exact and serialisable;
- semantics of the used opcodes correctly discovered;
- old body preserved byte for byte;
- 12/12 negative controls rejected;
- zero false successes and zero archive mutation;
- total median of 44 queries, maximum 50.

What failed:

- Genesis identification median: 14;
- L\* learning from scratch: 14;
- random queries: 17;
- organism without a learned passport: 17.

Genesis therefore did not reach the pre-registered advantages of 25% over L\* and 20%
over both local baselines. Eight criteria out of ten pass, but the status remains
**FAILED**. No threshold is modified and no rerun replaces the first attempt.

Proof identity:

- evaluated SHA: `5a0947afb96d7d59438c222028f2cabb34bc0cd5`;
- protocol SHA-256: `215e442435e4f915e647ad1392f1172685f977f758053027adaa687b1126c881`;
- GitHub Actions run: `30650363802`, attempt 1;
- artifact SHA-256: `0b5cf2df20dc4fc05dba3f1540c6d07c557ebd4c4d963d6e6286d90358a2f28a`.

An independent replay recovered every metric, every body, the criteria and the
decision. Only the consolidation hash was non-portable, because it embedded
floating-point scores; later experiments must use a quantised or rational trace.

## Capabilities supported within the finite domain

- extraction of a behavioural passport;
- autonomous morphogenesis from an opaque contract;
- experimental discovery of an unknown finite substrate;
- exact migration of a competence without a task oracle;
- transport, execution and exact consolidation of a bounded plasticity mechanism;
- abstention on out-of-language modifications and unstable oracles.

## Not validated

- learning advantage transferable outside the development distribution;
- portable autobiographical memory;
- adaptation to continuous or analogue physics;
- self-extending cognitive language, in the strong sense of inventing primitives;
- open-ended self-metamorphosis.
