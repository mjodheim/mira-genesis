# Measure register

This register is the repository's second asset, beside [`FAILURE_LOG.md`](FAILURE_LOG.md).
It catalogues **measures that came loose from what they claimed to measure**, in a
domain where ground truth is decidable.

## Why this register exists

Four experiments failed. None failed in the organism.

| | What gave way |
|---|---|
| M014b | a 25% threshold on a window four queries wide |
| M017 | a 10× threshold derived from a typical case taken for a bound |
| M018 | no consequence to inefficiency, so nothing to optimise for |
| M019 | a fitness horizon shorter than the payback period of learning |

Each time, what was being built held. What gave way was the way of judging whether it
was better.

## What this repository has and the literature rarely does

Goodhart's law, reward hacking, specification gaming, novelty search and
quality-diversity algorithms have worked this problem for a long time. It is neither
new nor unexplored.

But those bodies of work almost all operate where **the true objective is not exactly
verifiable**. Reward hacking is diagnosed because a human finds the result suspicious.
Novelty is judged by what looks interesting. Behavioural descriptors are picked by hand.

Here, the behavioural equivalence of two finite automata is **provable**. So one can
ask, decidably:

> Does this proxy measure actually track the quantity it claims to track, and under
> what optimisation pressure does it stop?

This is a testbed for measure design, not an attempt to solve what others have not.

## Reproducing the failures

Every case replays on demand, with its ground truth:

```bash
python scripts/reproduce_measure_failures.py
```

```bash
python scripts/reproduce_measure_failures.py --case R004
```

The four fast cases run in about a minute. `--full` adds R003, which needs an
environment sweep. `tests/test_measure_failures.py` locks the mechanisms — a catalogue
that stops reproducing is no longer a catalogue.

Output of case R004, as an example:

| | |
|---|---|
| real differences generated | 418 |
| missed by the probabilistic set | **7** |
| missed by the conformance suite | **0** |

---

## R001 — a window too narrow for its threshold

- **Origin:** M014b, canonical failure.
- **Measure:** number of identification queries, 25% advantage threshold.
- **What it claimed to track:** transported learning efficiency.
- **Divergence:** Genesis 14 queries, L\* from scratch 14. The quantity varied over a
  window four queries wide; a 25% threshold on it measured sampling noise.
- **Detectable in advance?** Yes. It sufficed to establish the quantity's dynamic range
  before fixing the margin. That became **D010**.

## R002 — a structurally incapable baseline taken for a criterion

- **Origin:** M014c, halted; then avoided in M017.
- **Measure:** ratio to the cost of a closed catalogue.
- **Divergence:** the closed catalogue solves 0 of 700 episodes. Any threshold set
  against it passes trivially and measures only its incapacity, which was already known.
- **Rule:** an incapable baseline is a **control**, never a criterion. A criterion must
  oppose two systems of identical capability at the start, which only the mechanism
  under test separates afterwards.

## R003 — a typical case taken for a worst-case bound

- **Origin:** M017, threshold invalidated before freezing.
- **Measure:** paired ratio of search costs, threshold derived at 10×.
- **What it claimed to track:** the gain from extending the language.
- **Divergence:** the derivation predicted ~500× assuming an absorbed macro is always
  reached at depth 1. Over 8 environments, minimum 95×. Over **50**, minimum **9.0×** —
  below the threshold. An episode carrying a noise atom forces depth 2 and collapses the
  ratio by a factor of fifty.
- **Correction:** the magnitude disperses by a factor of 69, which no defensible margin
  exceeds; the criterion became **directional**, dispersion zero, 50/50.
- **Lesson:** a sample of 8 gave a minimum optimistic by a factor of ten.

## R004 — a verification unable to guarantee what it asserted

- **Origin:** M017, confirmation defect.
- **Measure:** "zero false successes", checked on every word up to length 6 plus 96
  words drawn at random.
- **Divergence:** 96 draws do not cover 2⁷+…+2²⁰. Two 9-state automata confirmed
  identical are separated by `(1,0,1,0,1,0,1)`. The reported result was correct; the
  procedure could not guarantee it.
- **Aggravation:** two successive corrections were announced as correct and were not,
  the second producing **10 false successes out of 73** — worse than the original defect.
- **Lesson:** an admission condition is not established because a benchmark reports it
  satisfied, but when the procedure verifying it is **complete**. And the test meant to
  guard the property exercised no redirect at all — which is exactly why it passed on a
  broken suite.

## R005 — a quantity with no consequence

- **Origin:** M018, hypothesis not supported.
- **Measure:** search cost, under a 200,000-node budget and a free failure.
- **Divergence:** no forgetting mechanism pays off, not for want of a mechanism but
  because **there was nothing to be efficient for**. A quantity optimised without
  costing anything exerts no pressure.

## R006 — a horizon shorter than the payback period

- **Origin:** M019, invalid rig.
- **Measure:** energy left at the end of a generation.
- **What it claimed to track:** the efficiency of a strategy.
- **Divergence:** learning costs ~23,000 nodes against a 6,000 reward; not trying costs
  1,296. Selection removes the learner at the first cull, before any repayment. Across
  three calibrations the population converges on shallow search and **zero macros**,
  solving 11 episodes against 103 for an unselected control.
- **Lesson:** **the evaluation horizon matters more than the intensity of the pressure.**
  Too weak, it sorts nothing; too impatient, it eliminates exploration before it pays.
- **The guard was itself wrong:** "non-zero mortality" signalled the opposite of what
  was assumed. Zero deaths did not indicate weak scarcity but the reverse — scarcity bit
  hard enough that the winning strategy was to spend nothing.

## R007 — a separation test blind to within-group variance

- **Origin:** the discarded three-seed M021 pilot.
- **Measure:** `rig_separates_measures`, initially defined as a between-measure spread
  of at least 100 per mille.
- **What it claimed to track:** whether the rig could distinguish four selection
  measures.
- **Divergence:** it answered **yes** while the between-measure spread was 750 per mille
  and the widest seed-to-seed spread inside one measure was 584. Five of twelve
  populations solved nothing during life and eight held no macro.
- **Why it matters:** D010 already required margins to be interpreted against observed
  dispersion. The guard written after that lesson repeated the same error.
- **Correction:** the pilot was discarded, the full comparison required 24 paired
  seeds, and its 100-per-mille floor remained explicitly a development separation gate
  rather than a significance or canonical decision rule.

## R008 — a long-term estimator without evidence about the long term

- **Origin:** M026, negative development result.
- **Measure:** observed mean task success aggregated over a node's current clade.
- **What it claimed to track:** exact best hidden quality reachable in that rooted
  clade.
- **Divergence:** the positive control proves that the zero-score platform can reach
  6/6 hidden cases while a one-score shortcut can reach only 3/6. Yet the HGM-inspired
  policy's median final hidden quality was 0 per mille, identical to the DGM-inspired
  policy, with only 4 paired wins among 64 seeds.
- **Cause:** before the platform lineage produces a successful descendant, its
  observed clade contains no evidence of its latent value. Aggregation cannot recover
  information that expansion has not exposed.
- **Lesson:** a long-horizon statistic does not create long-horizon evidence. Its
  exploration and evaluation process must reveal the lineage before the estimator can
  value it.

The exact mismatch and exhaustive aligned control make the failure localisable. The
result does not test full HGM, whose adaptive evaluation and scheduling mechanisms were
held out of M026.

## R009 — an unweighted clade mean aimed at a clade maximum

- **Origin:** M027, negative development result.
- **Measure:** equal-weight mean task success over every observed clade node after
  exhaustive public breadth coverage.
- **What it claimed to track:** exact maximum hidden utility reachable in the rooted
  clade.
- **Divergence:** coverage exposed a hidden-quality signal in every seed, yet the
  HGM-guided clade estimate remained -907 per mille concordant with exact CMP. It beat
  immediate-performance concordance by only 93 per mille and produced 64/64 policy
  ties at zero final hidden quality.
- **Cause:** shortcut descendants are numerous and visibly successful but have poor
  hidden potential. Their equal-weight contributions dominate the mean, while exact
  CMP depends on the rare generic descendant that reaches the maximum.
- **Lesson:** exploration can reveal the relevant evidence without making an average
  estimate a maximum. Observation allocation is part of the measure, not merely an
  efficiency layer around it.

M027 held adaptive evaluation weighting out of scope. The result motivates isolating
that mechanism and does not test full HGM.

## R010 — adaptive weighting sharpened the same misaligned proxy

- **Origin:** M028, negative development result.
- **Measure:** individual development performance used to allocate finite evaluation
  observations, followed by their weighted aggregation over each observed clade.
- **What it claimed to track:** a soft approximation to exact maximum hidden quality
  reachable in the rooted clade.
- **Divergence:** adaptive weighted-clade/exact-CMP concordance remained -478 per
  mille, only 40 per mille above uniform and far below the pre-written 167 separation
  gate. Median final hidden advantage was zero, with 2 wins, 60 ties and 2 losses.
- **Cause:** the allocation policy observes the same development proxy whose ordering
  the mismatch rig reverses. It allocated only 34 per mille of non-initial evaluations
  to high-potential observed nodes, versus 51 per mille under uniform allocation.
- **Lesson:** adaptive concentration cannot repair an information mismatch by itself.
  It can make an aggregate more certain about the wrong quantity. The routing signal
  must contain information that is independently justified as relevant to the target.

M028 still does not test full HGM. It isolates one finite evaluation-target adaptation
while holding asynchronous scheduling, software tasks and the rest of HGM out of scope.

## R011 — reusable components without remaining-budget viability

- **Origin:** M029, mixed development result.
- **Measure:** success on generic motifs alone and under exact repetition, aggregated
  over observed clades.
- **What it claimed to track:** reusable structure that preserves maximum hidden
  descendant quality.
- **What worked:** the probe was exactly disjoint from development and hidden suites,
  and median clade/exact-CMP concordance moved from -478 to 699 per mille.
- **Divergence:** component-adaptive guidance still had median paired final advantage
  zero and missed the 40-win gate with 31 wins, 32 ties and 1 loss.
- **Cause:** a generic component remains probe-successful inside a mixed lineage that
  has already spent scarce depth on shortcut edits. Reusability does not imply enough
  remaining budget to assemble the complete generic solution.
- **Lesson:** a potential proxy needs both **capability evidence** and **resource
  viability**. Measuring useful parts without the budget needed to compose them can
  still overvalue a doomed lineage.

The pre-declared component-uniform diagnostic produced 50 wins, 14 ties and no losses,
but this was not a registered decision gate. It motivates an untouched-seed
confirmation rather than changing M029 after observation.

M030 supplied that confirmation on untouched seeds 64–127. Component-uniform guidance
reached 662 per mille clade/exact-CMP concordance and +1,000 per mille median paired
final hidden quality, with 48 wins, 16 ties and no losses. The distinction is now
supported in development: reusable-component evidence is informative in this finite
rig, while adaptive concentration and resource viability remain separate mechanisms.

---

## What the register already suggests

Eight regularities, drawn from eleven cases rather than postulated:

1. **Establish the dynamic range before fixing a margin** (R001, R003, R007).
2. **A criterion opposes two equal capabilities; an incapacity is a control** (R002).
3. **An admission condition is worth the completeness of its verification procedure**
   (R004).
4. **The evaluation horizon outranks the intensity of the pressure** (R005, R006).
5. **A long-horizon estimate needs a process that reveals long-horizon evidence**
   (R008).
6. **Sampling weights determine what an aggregate actually estimates** (R009).
7. **Adaptive weighting cannot recover information absent from its routing signal**
   (R010).
8. **Reusable capability and remaining resource viability are separate quantities**
   (R011).

R007 is the internal warning: recording a lesson does not guarantee that the next
instrument applies it correctly.

None is new taken alone. What is unusual is having measured them where ground truth is
decidable, and therefore being able to show *where exactly* a measure comes loose rather
than noting that a result looks wrong.
