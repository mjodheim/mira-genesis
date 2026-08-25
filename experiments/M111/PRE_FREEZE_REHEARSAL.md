# M111 — pre-freeze dress rehearsal

Recorded **before** the freeze and before any canonical attempt.

## What is rehearsed

A throwaway clone of this branch, checked out with `core.autocrlf true` so every Python and Markdown
member arrives with CRLF while the JSON members arrive raw. The clone then runs the entire canonical
path end to end: candidate protocol behind an annotated tag, final protocol behind a second, one
canonical attempt, one checker replay, and every refusal path the frozen instrument can meet.

The clone's own protocol and result digests are rehearsal artefacts and are deliberately **not**
recorded here: they depend on rehearsal tag names and would differ at the real freeze. The stable
evidence digest is not one of those — it excludes PIDs, search paths, return codes, elapsed times,
temporary paths and interpreter versions, so it should be identical on any machine running the
canonical interpreter over the same population and apparatus.

## The prediction

| | |
|---|---|
| population digest | `9ee85959f9be39be9c84fa083ac656863380a70dfcddb52bd961623139bc3313` |
| ambiguous worlds | 3 |
| witness worlds | 2 |
| predicted verdict | positive, P1–P24 all computed true |
| replay | performed and equal |

**Predicted stable evidence digest:** recorded in the commit that adds this line, before the freeze
commit and before any canonical attempt. A discrepancy at the canonical run is evidence, not
something to reconcile.

## What the development rehearsal already measured

On a two-ambiguous, one-witness development population, over 85 isolated processes:

| | |
|---|---|
| pooled record | 12 episodes from 3 worlds; undetermined `[3]`, determined `[1, 5, 7]` |
| generation 3 | acquired, rule space 127, 7 consistent policies, fires on rows `[2, 3]` |
| generation 2 ablated | **refused** — `no_expressible_policy_and_no_operator_makes_one_expressible` |
| expressibility | `M1` separating programs 0, `M2` separating programs 25 |
| `M0`, `M1` | fail both `A` and `B` |
| `M2` | resolves `A`, fails `B` |
| `always_signal` | resolves `B`, fails `A` |
| **the acquired policy** | **resolves both, in both probe orders, on one probe** |
| never-probe | fails `B` |
| always-probe | fails `B`, having spent the budget on the determined demand |
| ablation, mutation, corruption, rollback | byte-exact, causal, closed, unchanged |

The checker returned 22 of 24 true, with only the development-tag predicate and the no-replay
predicate false — both expected outside a canonical run.

## Every refusal path, exercised

| path | outcome |
|---|---|
| canonical before any protocol exists | refused, failed closed |
| canonical with a candidate but no final protocol | refused, failed closed |
| canonical without the owner flags | refused, failed closed |
| canonical on a dirty worktree | refused, failed closed |
| a second canonical attempt | refused, failed closed |
| checker before any result exists | refused, failed closed |
| a second checker report | refused, failed closed |
| truncated result bytes | refused, failed closed |
| bound apparatus changed after freeze | refused, failed closed |

## The tamper that matters

Not a broken file. A result whose evidence is **edited and whose every digest is then recomputed**, so
integrity alone cannot see it. One outcome is flipped and every dependent digest rebuilt; the claim
has to be caught by a predicate computed from the evidence rather than by a digest over it.

## What the rehearsal does not establish

Nothing about H56. It establishes that the instrument runs, refuses correctly, replays byte-stably
across a foreign checkout and cannot be edited into a positive verdict without being caught. The
scientific question is decided only by the single canonical attempt, whatever it returns.
