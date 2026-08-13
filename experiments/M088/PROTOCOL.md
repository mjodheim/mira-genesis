# M088 — Endogenous Experiment-Space Construction and Transfer

**STATUS: FROZEN BEFORE QUALIFICATION MATERIALIZATION. ONE ATTEMPT. NO REROLL.**

## The ceiling this attacks

D057 closed M087 by naming two remaining human assumptions. This milestone attacks the second.

M087's `execute_policy` takes `experiment_space: Sequence[str]`, and `encounter` passes in
`fam.acquirable_requests` — a literal tuple of eight request strings written by a person. The
policy filters it (`ENUMERATE_EXPERIMENTS`) and ranks it (`SCORE_EXPERIMENTS`). It never builds an
experiment. The lineage learned to *choose* where to look; it was still shown where looking was
possible.

**The causal question:** can the lineage construct part of the space in which it searches for the
information it needs, instead of receiving that space already enumerated?

## What an experiment becomes

Not an index into a list. An `ExperimentProgram` — an ordered sequence of interaction steps with a
construction trace, executed against a stateful world. The world offers a **vocabulary**
(`reset`, `send_a`, `observe`) and nothing else. A primitive is not an experiment.

## The mutable object

`ExperimentConstructor`: a serialized rule set plus a composition depth, executed by a fixed
constructor. `m0_constructor()` builds every program of the shape *reset, one action, observe* —
exactly the single-interaction depth at which M087's probes lived. That is a legitimate
limitation, made visible and, crucially, **enumerable**.

## The inexpressibility proof

Not "M0 did not find the right experiment". `constructive_image` enumerates M0's *complete*
constructive image over each world's vocabulary, and every program in it is executed
exhaustively against the surviving candidates. In the development world M0's image contains **two**
programs and **zero** of them discriminate; using all of them leaves all four candidates alive.
The adopted constructor builds a program that is checked to lie outside that enumerated image.

The claim is therefore *M1 built something M0 cannot build*, not *M1 got luckier*.

## Three structurally different worlds

| World | Where meaning lives | Depth-1 view | Separates at |
|---|---|---|---|
| `stateful_protocol` | order of messages | every send looks like `ack` | `a` then `b` unlocks; `b` then `a` faults |
| `path_graph` | path taken | every first edge looks like `node_mid` | `x` then `y` reaches a leaf; `y` then `x` a trap |
| `durable_service` | what survives | a write looks `buffered` | write→flush is durable; write→crash is not |

Development runs on `stateful_protocol`. **Both** qualification worlds are different from it, so
every qualification result is a transfer result.

## Two capabilities, both required

1. **Construct** an experiment outside the prior constructive image.
2. **Use** its observation causally — every acquisition must eliminate at least one candidate.

A lineage that invents programs and cannot use what they return fails the second. A lineage handed
the right program fails the first, which is why `authored_full_experiment_space` exists as a
**ceiling** and is never counted as evidence about Mira. It shows the M087 selector already knows
what to do once a space exists; what M088 adds is the construction.

## Why the world is not an oracle

The world answers *what happens if I do this*, which is what interacting with a system tells
anyone who interacts with it. The evaluator answers *is this candidate right*, on programs nobody
may run. `ASK_CORRECT_HYPOTHESIS()` does not exist; `RUN_EXPERIMENT(program)` really runs the
program against real state.

**The structural guarantee:** every hidden program uses three actions. The adopted constructor
composes at most two, so no hidden program lies inside its constructive image. The lineage cannot
build one, and therefore cannot run one, whatever budget or search it is given.

## Chronology

```
T0  protocol frozen and digested       T8  constructor serialized
T1  M0 constructor committed           T9  salt consumed; qualification drawn  <- after T8
T2  development world materialized     T10 M1 constructs experiments
T3  ambiguity encountered              T11 experiments executed
T4  M0 image enumerated and exhausted  T12 E_acquired updated
T5  meta-candidates produced           T13 adaptation selected
T6  descendant validation              T14 hidden evaluation
T7  M1 adopted                         T15 rollback proved; result sealed
```

## Arms

| Arm | What it has |
|---|---|
| `evolvable_experiment_constructor` | the adopted constructor, restored from serialized form |
| `fixed_experiment_constructor` | M0, never mutable |
| `constructor_acquisition_ablated` | the adopted constructor with its composition rules removed |
| `more_budget_same_experiment_space` | M0 at **10× real** exhaustive searches over the same image |
| `fresh_agent` | M0 with no development history |
| `authored_full_experiment_space` | **ceiling only** — handed M1's space without constructing it |

The budget arm performs ten *complete independent* searches — survivors and consumed set reset each
time — because PR #135 caught M087 multiplying a counter instead of doing the work.

## Ten conditions

Each computed, each able to make the verdict negative.

P1 prior constructor cannot resolve exhaustively · P2 meta-transformation adopted after rejections ·
P3 constructed experiment outside prior image · P4 observation used causally · P5 evolvable correct
in every qualification world · P6 capability discordance against fixed · P7 more budget in the same
space cannot close it · P8 ablation loses the capability · P9 cross-environment reuse without a new
meta-transformation · P10 constructor persisted and restored byte-identically.

## What a positive result would not establish

**Not** that Mira invents its own experiments in general. The interaction vocabulary, the
meta-primitives, the constructor rule vocabulary and the three worlds are authored. The honest
claim is bounded: *within one frozen meta-language and interaction vocabulary, the lineage
diagnosed that its experiment constructor could not express a discriminating observation program,
adopted a validated modification, constructed a previously inexpressible experiment, used its
result for a correctness-critical adaptation, persisted the mechanism and reused it in
structurally distinct environments.*

Not AGI, not open-ended evolution, not general autonomy, no generality gate, no independent
reproduction, no release or repository authority.
