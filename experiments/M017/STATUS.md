# M017 — Status

- Protocol: **DEVELOPMENT DRAFT**
- Canonical results permitted: **NO**
- Sealed evaluation seeds: **none**
- Sequential structural language: **implemented**
- Self-extending library and abstraction rule: **implemented**
- Re-embodiment on an opaque substrate: **implemented**, 9/9 exact
- Development tests: **11 passing**, within a suite of 52
- Scientific status: `DEVELOPMENT — LANGUAGE GROWTH BENCHMARKING`

## Freeze gates

| # | Gate | State |
|---|---|---|
| 1 | Designate the decisive comparison before any new observation | **passed** — [`PRE_REGISTRATION_DRAFT.md`](PRE_REGISTRATION_DRAFT.md) |
| 2 | Establish that the margin exceeds the dispersion between environments | **passed, and it cost the threshold** — see below |
| 3 | Justify budget and depth from the hypothesis, not from the margin produced | **passed** — [`PROTOCOL_DRAFT.md`](PROTOCOL_DRAFT.md) |
| 4 | Transport the library to an environment with unseen motifs | **passed** — and it forces the scope to narrow |
| 5 | Abrupt distribution shift after absorption | **passed** — degrades without false successes |
| 6 | Source isolation audit and integer-only trace | **passed** — `scripts/audit_m017_isolation.py` |

**All six gates are passed**, and they were passed twice: first under an unreliable
confirmation, then again after it was corrected.

The confirmation drew 96 long words at random while claiming to cover the distinguishing
bound of two automata. It did not. The "zero false successes over 42 episodes" was a
favourable draw, not a guarantee: two 9-state automata confirmed identical are separated
by `(1,0,1,0,1,0,1)`.

`metamorphosis/conformance.py` replaces it with a complete conformance test — W-method
on a minimised hypothesis, transition cover, margin computed from the source's state
count. Three versions were needed, two of which were announced as correct and were not;
see `FAILURE_LOG.md`.

**The four measurements redone under that confirmation return identical figures.**
Search cost does not depend on confirmation; what did depend on it is the admission
condition, now genuinely established.

The complete protocol, thresholds included, is in
[`FROZEN_PROTOCOL_017_CANDIDATE.md`](FROZEN_PROTOCOL_017_CANDIDATE.md). It is **not
frozen**: freezing commits thresholds that will not move and opens an evaluation that
runs once. That signature is human.

## What gate 2 taught first

The initial decisive statistic — two medians aggregated separately — was **rejected by
measurement**. Across eight environments the advantage ranged from 2.4× to 605×, and the
confound was identified: the self-extending organism's cost is bimodal, about 42 nodes on
a pure motif and about 1,800 when a noise atom forces depth 2. The median flipped with
the draw.

Paired episode by episode, the same measurement gives 95× to 620×: **the dispersion is
divided by thirty-eight without the median moving**.

Gate 6 likewise found a real defect: `m017_engine` was importing the laboratory.

## What the fifty-environment sweep cost

Eight environments gave an order of magnitude, not a distribution.

| | 8 env. | 50 env. |
|---|---|---|
| minimum | 95.3× | **9.0×** |
| median | 377.2× | 123.8× |
| favourable | 8/8 | **50/50** |

**The 10× threshold about to be signed fails on one environment in fifty.** The
derivation justifying it assumed a macro is always reached at depth 1; when a late
episode carries a noise atom, depth 2 is needed and the ratio collapses. A typical case
had been taken for a worst-case bound.

D010 requires a margin to exceed the dispersion. The magnitude's is a factor of 69 — no
margin exceeds it. The direction's is zero: 50/50, none adverse. **The decisive criterion
therefore becomes directional**, and the magnitude is reported rather than decisive.

That is a weaker claim than "a hundred times faster", and it is the only one the
measurement allows. Passing gate 2 seriously cost the threshold.

## The cost of absorption, not to be hidden

On the worst single episode the self-extending organism is **35% slower**: its macros
inflate the branching factor without ever applying. That covers 8 late episodes out of
49. A sign-test guard is pre-registered so a degenerate absorption rule cannot pass.

## Risk to keep in view

The development benchmark shows a hundredfold collapse in search cost. The temptation
will be to freeze a threshold against the **closed catalogue**, which fails 0/42: that
criterion would pass trivially and would measure nothing beyond the already known fact
that a twelve-program catalogue cannot express a three-atom trajectory.

The comparison carrying the hypothesis is the self-extending organism **against open
search**, on the decline of cost across episodes — two organisms of identical capability
at the first episode, which only absorption separates afterwards.

That is M014b's exact fault in reverse: a threshold set against a baseline that does not
measure what the experiment claims to establish.
