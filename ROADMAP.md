# Roadmap

| Step | Goal | Status | Exit condition |
|---|---|---|---|
| M001–M011 | Metamorphosis foundations | VALIDATED in their finite domains, **not verifiable here** | No versioned archive; see `archives/README.md` |
| M012 | Autonomous morphogenesis | INCONCLUSIVE — CONTAMINATED | Evaluation seeds were executed in tests |
| M012b | Clean autonomous morphogenesis | VALIDATED in the bounded domain | Sealed 36/36 evaluation and scientific reproduction |
| M013 / M013b | Unknown substrate | INCONCLUSIVE — CONTAMINATED | No result claimed |
| M013c | Unknown substrate | INCONCLUSIVE — NON-REPRODUCIBLE | The announced commit was incomplete |
| M013d | Unknown substrate, absolute threshold | FAILED IN DEVELOPMENT | No-probe baseline scored 12/36 against a ceiling of 8/36 |
| M013e | Unknown substrate, relative advantage | VALIDATED in the bounded domain | 36/36, sealed opcode discovery and independent reproduction |
| M014 | Initial portable plasticity | HALTED — NEVER EVALUATED | Prerequisites revoked; replaced by M014b |
| M014b | Sealed portable plasticity | FAILED — NO GENERALISABLE ADVANTAGE | 36/36 exact, but two efficiency criteria failed |
| M014c | Out-of-distribution portable plasticity | **HALTED — SUPERSEDED BY M017** | Never evaluated; measured a closed catalogue. Code is tagged `archive/m014c-halted` |
| M017 | Self-extending language | **READY TO FREEZE** | Six gates passed; the criterion became directional after a 50-environment sweep |
| M018 | Dissolution — knowing what to destroy | **HYPOTHESIS NOT SUPPORTED** | None of the three mechanisms removes the liability; forgetting is reactive and destruction is blind |
| M019 | Selection pressure | **RIG NOT VALID** | Selection is too impatient to value learning; the structural cause is identified |
| **M021** | **Proxy-measure divergence under decidable ground truth** | **ACTIVE** | Show whether the implemented measures move exact hidden quality and where they separate |
| M019b | Long-horizon selection | PLANNED | Evaluation horizon exceeds the learning payback period |
| M020 | Self-metamorphosis | DEFERRED | Detect, construct and adopt a better-adapted body without human architecture changes |
| M015 | Memory and strategy | DEFERRED | Migrate memories, uncertainty and exploration strategy |
| M016 | Sensorimotor competence | DEFERRED | Transport a world model between different architectures |

## Direction correction — 31 July 2026

The roadmap order was wrong. The experiment names were not.

The complete M012b → M014c line shared a limitation that none of its criteria measured:
**the organism could express only what had been handwritten for it.** In
`m014c_meta.py`, identification enumerated exactly twelve programs; learning only
reweighted counters over that closed catalogue.

Adding memory through M015 or sensorimotor competence through M016 would therefore have
expanded a paradigm laterally before its core was established. Those steps are delayed,
not abandoned. They resume when there is an organism whose language can grow and can
therefore carry them.

M017 attacks that core. M020, self-metamorphosis, depends on it directly: an organism
that cannot extend its language cannot describe a body that its current primitives do
not already know how to write.

## M014b — informative canonical failure

M014b proved exact portability of the plasticity chain: 36/36 exact adaptations, three
machines at 12/12, intact archive, 12/12 negative abstentions and zero false successes.
But Genesis used a median of 14 queries, and L* from scratch also used 14. The relative
advantage criteria failed.

The lesson reaches beyond M014b: **transporting a policy does not imply that its
advantage survives**, and a criterion measured over a four-query range cannot reliably
separate signal from sampling noise.

## M017 — ready to freeze

Development results across 42 episodes and three environments:

| Organism | Solved | Median nodes, first half | Median nodes, second half |
|---|---:|---:|---:|
| Closed catalogue, M014c capability | **0 / 42** | — | — |
| Open search without absorption | 34 / 42 | 7,154 | 8,545 |
| Self-extending | **37 / 42** | 4,222 | **43** |

Search cost collapses by roughly two orders of magnitude only for the organism that
extends its language; it remains flat for the organism that searches but never absorbs.
Re-embodiment is exact in 9/9 cases across three opaque-machine families, with 4/4
negative abstentions and zero false successes.

All six freeze gates have passed. The complete protocol and thresholds await a human
signature in `experiments/M017/FROZEN_PROTOCOL_017_CANDIDATE.md`. No canonical run is
permitted before that signature because freezing commits the thresholds permanently and
the evaluation runs only once.

Three measurements changed the development protocol before freezing:

- the first decisive statistic was rejected by measurement. Unpaired advantage ranged
  from 2.4× to 605× depending on environment; episode-paired advantage ranged from 95×
  to 620×. Pairing reduced dispersion by a factor of thirty-eight without changing the
  median;
- the proposed 10× threshold did not survive a wider 50-environment sweep. The minimum
  fell to 9.0×, so the criterion became directional: all 50 environments favourable,
  with zero sign dispersion;
- an extended language does not automatically transport. A library inherited from an
  environment with disjoint motifs scored 0.69×, strictly worse than no library, in all
  four trials. Unused macros inflated the branching factor even though they never
  applied.

The claim is therefore restricted in advance: the language grows within a distribution
of transformations, and its advantage transfers only when the destination shares that
structure.

## M018 — hypothesis not supported

Three destruction mechanisms were tested, and none removed the 0.69× liability. A fixed
budget is cheap but recovers only 6%; dissolution is **350× worse** in the stable regime.

The diagnosis moved the cause: **forgetting is reactive.** An irrelevant symbol is paid
for at every search node before the organism can know that it is useless. Blind
destruction also removes useful structure together with harmful structure.

Two consequences follow:

1. the remedy is not deletion alone but **selection at the moment of use**;
2. destruction is not viable for an isolated individual. A caterpillar dissolves once;
   if the metamorphosis fails, that individual dies, while the lineage may continue.

## M019 — invalid rig, retained lesson

M019 introduced scarcity. Energy became the search budget, a population replaced the
single organism, and duplication-divergence complemented absorption. The initial
population contained all four forgetting policies, allowing selection rather than the
researcher to choose among them.

The question was: **can a population under selection discover what the researcher did
not know how to design?**

The rig could not answer it. Three calibrations produced three degeneracies, and the
invariant was structural: **short-horizon selection cannot value an investment whose
return is delayed.** Learning cost about 23,000 search nodes for a reward of 6,000,
while declining to try cost only 1,296. The learner was removed at the first cut before
its library could repay the investment.

Selection discovered that not trying was cheaper than trying, and it was correct under
the horizon it had been given. The rig was wrong; the hypothesis was not refuted. A
fourth calibration would have been tuning until the desired answer appeared.

## Reorientation — the measure becomes the question

Four failures occurred, and none was in the organism. Each time, the constructed
mechanism held while the judgement of whether it was better failed. The project now
follows the evidence produced by its own failures:

**When does a proxy measure stop tracking what it claims to measure, and under what
optimisation pressure?**

This problem is neither new nor untouched. Goodhart's law, reward hacking,
specification gaming, novelty search and quality-diversity all address parts of it. The
repository's distinctive angle is that finite-automaton behavioural equivalence is
**decidable**. It can show exactly where a proxy separates from ground truth rather than
merely judging a result as suspicious.

Six cases are catalogued in [`MEASURES.md`](MEASURES.md), with four repeated
regularities. See D011 and H9.

The metamorphosis line is not abandoned. It produced the decidable domain, two sealed
validations and the failure cases. It is now the experimental support for the measure
question rather than the sole question itself.

## M019b — delayed, lesson retained

The evaluation horizon must exceed the payback period of learning, either through
selection every N generations or fitness integrated across a lineage's life.

**Horizon matters more than pressure intensity.** This is the most transferable lesson
produced by the project so far.

## Ultimate test of the first complete phase

Genesis learns in body A, receives an unknown substrate B, discovers its operational
rules, constructs a new body, transfers memory, competence, tools and plasticity, then
learns a genuinely new task faster than a fresh organism — without a human redesigning
its architecture.

That test requires Genesis to express competences and transformations that nobody wrote
for it in advance. M017 establishes the first language-growth prerequisite; M020 must
establish proof-gated self-rewrite before complete self-metamorphosis can be attempted.
