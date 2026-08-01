# M019 — Status

- Protocol: **DEVELOPMENT DRAFT**
- Canonical results permitted: **NO**
- Scientific status: `DEVELOPMENT — RIG NOT VALID, STRUCTURAL CAUSE IDENTIFIED`
- Development tests: **9 passing**, within a suite of 52

## The rig does not test what it claims to test

Three calibrations, three degeneracies. Freeze gate 1 — "scarcity must bite" — is passed
by none of them. No conclusion is drawn on hypothesis H8.

| Calibration | Result | Deaths |
|---|---|---|
| reward 25,000 | energy doubled, `none` 8/8 | 0 |
| reward 6,000 | depth → 2, macros → 0 | 0 |
| reward 6,000 + energy carry-over | depth → 2, macros → 0 | 0 |

Population: 11 episodes solved. Control organism, alone, unselected: **103**, with 18
macros.

## The cause is structural, not numerical

The invariant across all three: **a short-horizon selection cannot value an investment
whose payoff is deferred.**

Learning costs about 23,000 nodes against a 6,000 reward, so −17,000 immediately. Not
trying costs 1,296. At the first cull the learner ranks below the cautious one and is
removed — before solving the three motifs of its environment, the only point at which its
library would start repaying.

Energy carry-over fixes nothing, because it assumes the investor survives to the next
generation. It is eliminated before that.

**Selection discovered that not trying is cheaper than trying**, and it was right about
the horizon it was given.

## A badly chosen guard

"Non-zero mortality" was a poor gate. Zero deaths did not signal weak scarcity but the
reverse: **it bit hard enough that the winning strategy was to spend nothing.** An
organism searching at depth 2 spends 1,296 nodes and never dies.

A correct guard would have been: *is the population learning anything?*, measured by
macro count. It was zero in all three runs.

## Why the work stops here

A fourth calibration would be tuning until the wanted answer appears — exactly what this
repository's discipline exists to prevent. Three runs, one identified invariant and a
named cause are enough to conclude that **the rig is wrong**, not that the hypothesis is
refuted.

## What M019b must change

The evaluation horizon must exceed the payback period of learning:

1. select every **N generations**, not every generation;
2. or integrate fitness over the lineage's whole life rather than one generation;
3. or amortise the learning cost — the first solve of a motif opens a series, and a
   fitness seeing only its first term is measuring the wrong quantity.

The lesson generalises past this project: **a badly formed selection pressure selects for
stagnation.** Too weak, it sorts nothing; too impatient, it eliminates exploration before
it pays. The horizon matters more than the intensity.

That is M014b's trap in another form — a criterion that measures the wrong thing does not
become right by changing its thresholds.

## What came of it

M021 carries the correction: selection every `SELECT_EVERY` generations. Its first smoke
run showed mortality and learning coexisting for the first time, which none of M019's
three calibrations achieved.
