# RSI V23 / L5 — causal recursive meta-improvement preregistration

Status: **PROSPECTIVE APPARATUS SPECIFICATION — no L5 meta-search arm may be executed until the
final V23 freeze record binds the exact holdout tasks, evaluators, candidate generator, apparatus
hashes and this document.**

Date: 2026-09-24.

## Scientific question

L4 established that the acquired G2 search policy transfers to fresh real-project repair processes
and reaches the same quality as G1 with lower represented search cost.

L5 asks the recursive question:

> Does the already-acquired G2 improvement materially improve the process that discovers its own
> successor G3, and does that successor then outperform G2 on a fresh population that did not select
> it?

The causal chain under test is:

`G2 acquired search mechanism -> better meta-search -> frozen G3 -> fresh cross-stack gain`.

## Frozen parent identities

- G1 source SHA-256:
  `3354f887a93a08d9f00e9c54ccb097003f727ba77c1e1b4e9997adf676d35434`
- G2 source SHA-256:
  `69d0d725601cd32adff27379dbb25f5c7be29946f9e9c6ac4858a0634cbd5fdf`
- L4 final adjudication schema:
  `mira-genesis-rsi-v22-final-adjudication-v1`
- L4 observed global utility:
  - G1 = `(3, 3000, -9, -6)`
  - G2 = `(3, 3000, -3, -3)`

The L5 equal meta-search represented-request budget is therefore fixed at **9 per arm**, the complete
represented-request cost of the L4 G1 comparator. This value is derived from the already-adjudicated
L4 cost scale and was not selected from an L5 outcome.

## Meta-search arms

All four arms search the same descendant tree rooted at exact G2 and use the same candidate evaluator,
candidate mutation family and public meta-development population.

- **A / G2-meta** — exact frozen G2 controls parent selection and stopping.
- **B / G1-meta** — exact frozen G1 controls the same G2-rooted descendant tree.
- **C / G2-ablation** — exact G2 selection logic except:
  1. the acquired `best >= 780` early-stop block is absent;
  2. stall-round metadata is reverted from 3 to predecessor value 1.
- **D / no-meta** — deterministic lexicographic breadth-first parent expansion.

External caps, identical for every arm:

- represented candidate evaluations: **9**
- rounds: **8**
- maximum parallelism: **2**
- candidate mutation depth from G2: **2**

Internal controller limits may only reduce these external caps.

## Editable object and finite descendant grammar

The candidate root is byte-exact G2. Descendants may alter only six integer controls already present
in G2:

| axis | admitted values | G2 root |
|---|---|---:|
| stop quality | 700, 740, 780, 820, 860, 900 | 780 |
| promising-quality maximum | 630, 670, 710, 750, 790 | 710 |
| deep minimum lineage depth | 1, 2, 3 | 2 |
| parallelism | 1, 2 | 1 |
| maximum rounds | 6, 7, 8, 9, 10 | 8 |
| stall rounds | 1, 2, 3, 4 | 3 |

One edge moves exactly one axis to an adjacent admitted value. Candidate identity is content-addressed.
No arbitrary Python generation, new branch logic, task literal or holdout identity may enter G3.

## Public meta-development population

G3 construction uses exactly **12 synthetic public search landscapes**, the complete Cartesian product:

- first revealed child quality: `{650, 730, 810}`;
- location of the unique quality-1000 continuation: `{root, deep}`;
- first child evolver-profile generation flag: `{0, 1}`.

The landscapes are generated mechanically by `l5_meta_development.py`; there is no manually chosen
subset after arm observation.

Per development episode the candidate search policy is externally capped at 6 represented requests,
6 rounds and parallelism 2.

Candidate development utility is lexicographic:

`(episodes_solved_at_1000, accepted_episodes, sum_best_quality_milli, -requests, -rounds)`.

The complete finite depth-2 candidate universe is evaluated before arm traversal. Candidate
`quality_milli` exposed to the meta-controller is an order-preserving 0..1000 tier rank of that
frozen development utility across the complete universe. Equal utilities receive the same tier.

The decisive L5 claim never uses this development score directly; it only constructs and freezes
successor identities.

## G3 selection

For each arm, after its frozen meta-search budget stops, the selected successor is the revealed
candidate with lexicographically maximal development utility; source SHA-256 breaks only exact
utility ties deterministically.

No human may choose among revealed candidates.

The A/G2-meta successor is named **G3** only if it is a strict development improvement over root G2.

Before any fresh holdout execution, the exact G3 source bytes and the B/C/D selected successor
identities are committed.

## L4 retention gate

Before fresh L5 holdout evaluation, G3 must replay the preserved L4 represented discovery histories
without lower per-task or global process utility than exact G2.

Tolerance: **zero**.

Failure of this retention gate is a valid L5 negative and the fresh holdout is not consumed.

## Fresh L5 cross-stack holdout

Exactly four real-project tasks are frozen before the meta-search is executed.

### Host A — BrewTrack / C# .NET

Repository: `mjodheim/BrewTrack`
commit: `1727fc0158c6dbd741bfb0b6d85e8fe70f1a40f3`

Allowed production files:

1. `Domain/BrewMath.cs`
2. `Domain/RecipeMath.cs`

### Host B — Brewstead / Java Spring

Repository: `mjodheim/mjodheim-brewstead`
commit: `84f6c2462b810a83870974068db1e12d7f1e3720`

Allowed production files:

3. `src/main/java/be/mjodheim/brewstead/service/EffectService.java`
4. `src/main/java/be/mjodheim/brewstead/service/BrewService.java`

Task construction rule, fixed before G3:

- each root contains exactly two prospectively injected semantic defects in the one allowed file;
- each task has four retained reserved objective assertions, two per defect family;
- the untouched frozen host passes 4/4;
- the defect root passes 0/4;
- existing public project tests remain the public regression guard;
- the repair candidate generator is deterministic, finite and laboratory-owned;
- candidate generation exposes no reserved assertion, hidden outcome or holdout result to a policy;
- no task is included or removed after observing G2, G3 or any meta-search arm on that task.

Reserved task quality is:

- public guard failure: **0**
- public guard pass: **250 × number of four reserved assertions passed**

Thus possible retained quality is exactly `0, 250, 500, 750, 1000`.

## Fresh holdout search utility

For one holdout task:

`(best_quality_milli, -represented_requests, -rounds)`

Global four-task utility:

`(tasks_at_1000, sum_best_quality_milli, -total_represented_requests, -total_rounds)`

All comparisons are lexicographic. No scalar weights are hidden.

## Positive L5 predicates

V23/L5 is positive only if all hold:

1. A/G2-meta mechanically selects and freezes a G3 that strictly improves on G2 on public
   meta-development utility.
2. G3 passes the zero-tolerance L4 retention gate.
3. On the fresh four-task holdout, G3 global utility is strictly greater than exact G2.
4. On the same holdout and equal external budget, G3 global utility is strictly greater than the
   successor selected by B/G1-meta.
5. A/G2-meta meta-process utility is strictly greater than C/G2-ablation meta-process utility.
6. all four holdout task/evaluator/host identities remain byte-identical to the final pre-search
   freeze.
7. no holdout result enters G3 construction, candidate ranking or mutation.
8. negative attempts and all four meta arms are retained.

D/no-meta is a preregistered descriptive control. A strict A>D meta-process win strengthens the result
but is not required for the primary L5 predicate.

## Failure interpretations

- A finds no development successor better than G2: clean negative on recursive successor discovery.
- G3 loses L4 retention: clean recursive-regression negative; do not expose fresh holdout.
- G3 > G2 fresh but B finds an equally good or better successor: useful policy evolution, not causal
  recursive attribution.
- A and C have equal meta-process utility: acquired G2 mechanism is not causally established.
- A wins development but G3 does not beat G2 fresh: meta-overfit negative.
- any post-observation task/evaluator/budget change: invalid attempt, not a scientific negative.

## Freeze boundary

Before any call to `l5_meta_search.run_all()`, the final V23 freeze must bind:

- this preregistration;
- exact L4 adjudication bytes;
- exact G1/G2 and C-ablation source identities;
- policy guard and sandbox;
- finite mutation-family implementation;
- 12-landscape generator/evaluator;
- meta-search engine;
- exact four holdout defect patches;
- exact four retained evaluator sources;
- exact holdout candidate-generator implementation;
- host commit identities;
- task manifests;
- utility/adjudicator implementation;
- test suite and calibration record.

Until that freeze exists and calibration is green, **running the four L5 meta-search arms is forbidden**.
