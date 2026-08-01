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

---

## What the register already suggests

Four regularities, drawn from six cases rather than postulated:

1. **Establish the dynamic range before fixing a margin** (R001, R003).
2. **A criterion opposes two equal capabilities; an incapacity is a control** (R002).
3. **An admission condition is worth the completeness of its verification procedure**
   (R004).
4. **The evaluation horizon outranks the intensity of the pressure** (R005, R006).

None is new taken alone. What is unusual is having measured them where ground truth is
decidable, and therefore being able to show *where exactly* a measure comes loose rather
than noting that a result looks wrong.
