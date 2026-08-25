# M110 — adversarial review

Written before freeze, against the milestone's own claim. Objections that survive are conceded in the
pre-registration and in `README.md`; objections that were repaired are recorded here with what
changed.

## Repaired before freeze

**D1 — a capsule-equality field that no arrangement could falsify.** The first apparatus recorded
`arm_capsules_differ_only_in_state` as `all(len(group) >= 1 …)`. That is true for every possible run.
It is exactly the M095 defect "record fields that are assertions disguised as measured booleans".
Repaired: capsules are grouped by the world and demand bytes they share, and the group must hold one
capsule per arm, with pairwise-distinct state bytes and uniform member lists. Each conjunct can fail.

**D2 — a delegation check that compared module names.** `attribute.__module__` equality is a
tautology about where a function is defined, not evidence that the consumer runs the producer's
cascade. Repaired: the full attribution map over all eight rows and all three arms is recorded, and
the checker recomputes it from the restored truth tables under the declared cascade order, importing
nothing.

**D3 — an implicit ceiling that would have inflated the claim.** Nothing measured what happens when
the *host* simply widens a component. A reader could therefore have heard "the restored cascade
reaches something the host cannot supply". It cannot: a host-widened candidate space resolves the
row-3 demand and a host-widened interface resolves the row-7 demand. Both are now measured as **P23**
and the claim is restated as being about *which component the cascade decides to extend*.

**D4 — the producer link was a digest of a decoded payload, not of bytes.** Repaired: the checker
binds the raw SHA-256 of `experiments/M109/RESULT.json` to the constant D078 preserved,
`0af98fb4…`. A functionally equivalent rebuild of M109 would now fail P2.

**D5 — the population could have carried the answer.** The authoring script emits worlds only. The
preflight asserts the file holds no `row_labels`, `canonical_targets`, `census` or `rows` key, and the
boundary audit rejects any digest in it that is not a world identity or the population identity.

## Conceded, and declared

**C1 — the consumer family was chosen to reach row 5.** References were selected *because* they break
`g0 ⟹ g1`. This is a deliberate stress test, not a neutral sample, and the claim is conditional on
that. What is not tuned is the row → component map: worlds are admitted on structure alone — census
complete, no ambiguous row, rows 3, 5 and 7 present at the base state — and the map is measured
afterwards by the consumer's own trial. In a pre-freeze survey of 60 independently generated worlds,
19 were admitted and **all 19 carried the identical map**, with 6 rejected for ambiguity and 35 for
missing rows. The criterion does real work and never touches a label.

**C2 — the registry names and the feature vocabulary are shared authored vocabulary.** They are
imported from the producer module rather than restated, which prevents drift, but it does not make
them transferred content. M110 cannot claim a lineage would discover this vocabulary.

**C3 — the consumer family is project-authored.** It is not independently maintained, so **G4 does not
advance** to independent transfer. This is cross-family transfer inside one project's authorship.

**C4 — the candidate-space step widens and then searches.** Resolving on the candidate-space axis
performs a widen followed by an operator search, where the operator axis performs only the search.
M109 declared this asymmetry and it is inherited unchanged: widening is a no-op unless the search it
unlocks finds something the narrower space did not, so the reach change is the single operator
addition both arms are allowed. It remains an asymmetry and it remains declared.

**C5 — the lemma technique is shared with the producer.** Both laboratories close an axis by a
monotonicity argument. The lemma is the instrument, not the domain; the objects it closes here are
4-valued chain maps over five JSON documents, not Boolean truth tables.

**C6 — `MIN`/`MAX` are the chain analogue of `AND`/`OR`.** A reviewer may read the consumer's lattice
fragment as the Boolean one relabelled. The reply is the row-5 geometry: no relabelling of the
producer's world produces a reachable row 5, because prefix truncation forbids it at every width.
That the analogy holds for the *held* operators while the *information boundary* differs is precisely
what isolates the variable under test.

## Objections a hostile reviewer should still press

**O1 — "the rules are an eight-row lookup table; of course they carry."** Partly right, and it is why
row 5 matters. If the map were trivially correct everywhere, the cascades would help there too. They
do not: they fire on an unpinned row and are wrong. The transfer is real *and* bounded, and the bound
is derivable from the producer's own census before any consumer world runs.

**O2 — "M2 searches 257 candidates where M0 searches 36."** True, on the row-3 demand, because
widening the candidate space is the acquisition being tested. The node budget is equal and the
deeper-bound control shows more nodes do not help `M0`; the candidate space is a component, not a
budget. P23 discloses that the host can flip it directly.

**O3 — "the conservation control is weak."** Row 1 is a single row where all three arms succeed. It
shows nothing is lost, not that nothing could be. A stronger conservation measure over the full
row-1 population is a fair successor request.

**O4 — "one canonical demand per row per world."** The census counts thousands of row-1 and row-3
targets and only single digits at rows 5 and 7. The canonical demand is the lexicographically least
determined target at the base state, fixed before the arms run, but the milestone measures one demand
per row per world rather than the whole row. Six worlds is the population, not the sample size within
a row.

**O5 — "is this recursive self-improvement?"** No. Two rules of three nodes each, restored from a
frozen file, over three authored features, in a five-document world with fixed budgets and a fixed
evaluator.
