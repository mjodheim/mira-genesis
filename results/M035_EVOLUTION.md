# M035 — a capacity-increasing operator under selection

**Status: development result only. No canonical claim.**

## The problem this addresses

Two measurements bound what the existing stack can do.

**The tool layer adds nothing.** A learned tool is a composition of primitives charged
what those primitives cost, so anything it reaches was already reachable. Its reachable
set is *identical* to the toolless one at every budget (M034).

**The structural layer cannot grow.** Over 53,280 atom applications across 40 automata,
18,540 changed the state count and **none increased it**. Every change was a decrease.

| Atom applications | Changed state count | Grew | Shrank |
|---:|---:|---:|---:|
| 53,280 | 18,540 | **0** | 18,540 |

So an organism can rearrange or shrink, never gain capacity. Its expressive ceiling is
fixed at birth, and no descendant can be structurally novel. "Self-improvement" in that
architecture is search inside a budget it did not choose and cannot change.

## The operator

Duplication: append a behaviourally identical twin of an existing state and route one
incoming edge to it.

It is **neutral at birth** — the twin carries the same outgoing transitions and the same
acceptance, so the language is unchanged and selection cannot distinguish parent from
child. That is the mechanism, not a side effect: a mutation selection cannot see is free
to drift, which is how gene duplication produces novelty in biology rather than damage.

| Property | Result |
|---|---|
| Preserves behaviour exactly | **12/12** |
| Increases the state count | **12/12** |

This is not new. It is the *add node* mutation of NEAT (Stanley & Miikkulainen, 2002),
itself transposed from gene duplication. What this domain adds is not the mechanism but
the proof: here "unreachable" is demonstrated rather than observed.

## The decisive test

The target is `make_out_of_language_target`, which M017 uses as a **negative** control. It
is constructed by adding a state, and the structural language cannot add states, so M017
requires the organism to *abstain* on it.

That makes it provably unreachable for an organism without duplication. If a population
reaches it, that is not a better search — it is a capacity the lineage did not start with.

Twelve cases, all with targets requiring growth. Arms identical in founder, target, seed,
population, generations and budget; only the operator set and survival rule differ.

| Arm | Solved exactly | Median generation |
|---|---:|---:|
| control — atoms only | **0/12** | — |
| duplication, random trigger | **6/12** | 16 |
| duplication + speciation | 1/12 | 11 |
| duplication + diagnosed trigger | 2/12 | **8** |

The control's 0/12 is structural, not unlucky. The duplication arm used growth in 12/12
cases and reached the target in half of them.

Both refinements show the same signature: **faster when they succeed, successful less
often**. More directed, less exploratory — and in this rig breadth beats speed.

## The speciation arm failed, and it was predicted to succeed

Neuroevolution documents the failure mode this arm was meant to fix: a topological
innovation is born less fit than the incumbents and is eliminated before it can be
optimised. NEAT's answer is speciation — innovations compete inside their own niche.

Here it made things **worse**, 1/12 against 6/12.

The transposition was unfaithful, and that is the most likely explanation. NEAT allocates
offspring **proportionally to species fitness**. This implementation split the population
into equal shares by state count, so with 24 slots and four sizes each size received six,
including unproductive ones. The minimal criterion already preserves diversity; equal-share
speciation adds more and starves the search.

That explanation is **not** applied here. Correcting the rule and re-measuring on the same
seeds would be the post-hoc adjustment §7 of the M017 protocol and D010 forbid. A corrected
speciation rule must be pre-registered and measured on untouched seeds.

## The organism can diagnose its own insufficiency — and that did not help either

An organism can prove it needs more states **without ever seeing the target**, from the
oracle answers it already holds. Myhill–Nerode: prefixes separated by an observed suffix
cannot share a state, so a pairwise-distinguishable set is a lower bound on the required
size. When that bound exceeds its own, no rearrangement of its current body can express
what it has already observed.

| Property | Result |
|---|---:|
| Bound ever exceeds the true minimum (unsound) | **0/24** |
| Growth diagnosed when the target requires it | 8/12 |
| Growth demanded against its own behaviour | **0/12** |

The bound is sound but not tight — greedy selection understates the minimum — so it
under-claims rather than over-claims. That is the correct direction for the error: a
demanded growth is always warranted, a silent one is not always absent.

This is Gate 1 of the completion criteria, autonomous diagnosis of a limitation, in a form
that is decidable rather than heuristic. It is the piece this repository has listed as
unvalidated since the beginning.

**Using it as the trigger made results worse**, 2/12 against 6/12, while halving the time
to solve. The mechanism is identifiable: the policy is all-or-nothing. While the diagnosis
holds, *every* offspring duplicates, so no atom edit occurs and the population grows
without refining, then switches wholly to editing once the size is reached. The random
trigger interleaves growth and refinement instead.

A diagnosis that raises the *probability* of growth rather than forcing it would likely
behave differently. That is a hypothesis, not a correction: applying it to these same seeds
would be the adjustment §7 forbids.

## Selection — and a correction to how it was described

**The selector used here is `thresholded_elitist_truncation`.** It admits on a threshold,
ranks the admitted by descending agreement, favours the smaller body on a tie, and
truncates at capacity. The 6/12 recorded above belongs to that implementation.

It was originally documented as "the minimal criterion, chosen from this repository's own
measurement". **Both halves of that were wrong**, and the correction is recorded rather
than quietly applied:

- it is not a minimal criterion. It ranks the admitted, which is what a minimal criterion
  refuses to do;
- it is not M021's selector. `rank_by_minimal_criterion` filters on viability
  (`ledger.solved > 0`), ranks the viable by **novelty**, ranks the rejected by energy, and
  lets `Population.select` truncate. M021's 750 per mille belongs to that composite —
  viability, then novelty, then truncation — within its own domain, and its report says so.

Nothing in this experiment inherits M021's figure. M037 introduces a different selector
with its own name and its own record; the two are not interchangeable, and neither are the
rates or costs measured under them.

## Limits

- **Not a claim about general self-improvement.** A bounded, decidable mechanism in a
  finite automaton domain.
- **The selector remains unsolved.** Eight experiments in this repository died on it —
  M014b, M018, M019, M021, M026, M027, M028, M029 — each time with the mechanism intact
  and the judgement rule broken. Nothing here changes that.
- **Growth is capped** at the founder's size plus three. An uncapped duplicator would
  bloat until some behaviour fell out, which would measure nothing.
- **6/12 is not a solved problem.** Half the cases fail within sixty generations.
- The reachability figures quoted for duplication elsewhere in this session used a
  bounded search frontier in both arms, so the *count* of newly reachable behaviours is
  suggestive; the capacity increase itself is exact.
