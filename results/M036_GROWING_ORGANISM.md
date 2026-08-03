# M036 — a single growing organism, and why the population wins

**Status: recorded negative. Development only.**

M035 showed a population with a capacity-increasing operator reaching targets its founder
provably cannot express: 6/12, against 0/12 for a control that fails by impossibility
rather than by budget.

M036 asked whether that could be compressed into one organism: meet a task, prove the body
is too small, grow, solve, keep the acquisition. It cannot. Three attempts measured it.

| Architecture | Solved |
|---|---:|
| control, no growth | **0** of 8 |
| M036, single organism | 2 of 8 |
| M035, population | **6** of 12 |

The population explores roughly four thousand bodies over sixty generations. A single
organism explores one depth-3 trajectory. **The exploration volume is the mechanism**, not
an implementation detail around it.

## Three findings worth keeping

### 1. The explicit diagnosis is unnecessary

`required_states_lower_bound` lets an organism prove it needs more states without seeing
the target, by Myhill–Nerode: prefixes separated by an observed suffix cannot share a
state. It is sound — measured over 24 checks, it never exceeded the true minimum and never
demanded growth against the organism's own behaviour.

It is also unnecessary. Once the growth atom is in the search vocabulary, the search finds
*when* to grow by itself, exactly as it finds any other edit. In the runs that solved, the
diagnosis path never fired.

And it is too weak to gate on. The greedy set understates, so on 3 of 6 cases requiring
growth the bound did not exceed the body size. Gating growth behind it suppressed the very
episodes that needed it. **Failure is the better trigger than proof.**

### 2. Growth must be composable, not preparatory

| Growth placement | Solved |
|---|---:|
| inside the search vocabulary | 2 of 8 |
| as a phase before the search | **0** of 8 |

In the vocabulary, a depth-3 trajectory can be *edit → grow → edit*: the organism may
enlarge itself in the middle of a repair. A grow-then-search phase can only produce
*grow → edit → edit*, which is strictly less expressive.

The price is paid on every episode: depth-3 enumeration widens from 36³ ≈ 46,000 nodes to
44³ ≈ 85,000, whether or not growth is needed.

### 3. Growing is not enough, and the target is not always reachable

Exhaustive enumeration from every candidate child, at depth 3, on six cases:

| Outcome | Cases |
|---|---:|
| diagnosis missed, no growth attempted | 3 |
| grew, target reachable | 2 |
| grew, target **still unreachable** | 1 |

A size bound establishes *that* a body must grow, never *where* the missing distinction
lives. Duplicating the wrong state produces capacity the organism cannot use, and the role
vocabulary compounds it: four roles address only three or four states of a five- or
six-state body, so part of any grown body is beyond every edit.

## An error in the measurement of this experiment

The first run reported 0/8 and was presented as a structural failure. It was not: the
smoke test used a 60,000-node budget while depth-3 enumeration over 44 symbols requires up
to 85,184. At the protocol's 200,000 the same code solves 2/8.

The finding stands — a single organism is worse than a population — but the first number
was an artifact of the harness, not of the organism.

## What is kept

The `grow` atom in `metamorphosis/structural.py`. It is additive: `all_atoms()` is
unchanged, so every recorded experiment keeps its vocabulary, its reachable set and its
digests. 304 repository tests pass with it present.

## Limits

Eight cases, one generator, development only. No canonical claim. The selector remains the
open problem it has been since M014b, and nothing here addresses it.
