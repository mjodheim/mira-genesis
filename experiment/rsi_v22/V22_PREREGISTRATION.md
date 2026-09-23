# Genesis RSI V22 — retained-evaluator Brewstead replication

Status: **DRAFT FOR CALIBRATION; no V22 proposer output may be generated until the calibration workflow is green and the final freeze record is committed.**

## Purpose

V22 is a clean prospective replication of the V21 cross-stack search-policy transfer experiment. It is not a reconstruction of the missing V21 evaluator. Its purpose is to make the L4 decision independently reproducible by retaining the exact task mutations, reserved evaluator tests, utility implementation, search policies, host identity, and success rule before any proposer sees a task.

## Frozen host candidate

- Repository: `mjodheim/mjodheim-brewstead`
- Commit: `720b27c8bc80de16c04953e13d5f9e8425beea8c`
- Production language/stack: Java / Spring Boot

## Task selection rule

Exactly three tasks are selected before proposer observation. Each must:

1. modify exactly one production service source file;
2. represent a user-visible or domain-visible semantic defect;
3. be expressible by a minimal reversible mutation of the frozen host;
4. pass the relevant existing public service test(s) when defected;
5. fail exactly one retained reserved JUnit objective test when defected;
6. pass that reserved objective on the unmodified frozen host;
7. use no network, database, clock-sensitive external service, or nondeterministic provider in the reserved objective;
8. target a different production service from the other two tasks.

Selected tasks:

| task id | allowed production source | public symptom |
|---|---|---|
| `brewstead-game-state-estate-max-fields` | `src/main/java/be/mjodheim/brewstead/service/GameStateService.java` | Estate metadata must report the field capacity from the field schedule, not the hive capacity. |
| `brewstead-progression-merchant-coin-bonus` | `src/main/java/be/mjodheim/brewstead/service/ProgressionService.java` | The MARCHAND specialization must add its 10% NPC-order coin bonus while other specializations keep the base reward. |
| `brewstead-catalog-crop-ingredient-name` | `src/main/java/be/mjodheim/brewstead/service/CatalogService.java` | Crop catalog entries must expose the linked ingredient's name rather than repeating the crop name. |

## Information boundary

The proposer receives the defected parent archive, public tests, public symptom, task manifest, proposer protocol, and output verifier only. It does not receive:

- reserved evaluator JUnit source;
- evaluator outcome;
- another task/slot output;
- G1/G2 selection outcome;
- previous V22 proposer conversation;
- Mira Genesis project context, memory, web, GitHub, plugins, or connectors.

The laboratory retains evaluator source in this repository before proposer execution.

## Search policies

G1 is the frozen parent search policy identified by SHA-256:

`3354f887a93a08d9f00e9c54ccb097003f727ba77c1e1b4e9997adf676d35434`

G2 is the already-canonical V19 child generation identified by:

- generation digest: `d2e2b990581b5c72c1e642944ccd08c96ff0470b5117dd8a8820425c0028c6bd`
- source SHA-256: `69d0d725601cd32adff27379dbb25f5c7be29946f9e9c6ac4858a0634cbd5fdf`

No V22 outcome may modify either policy.

## Evaluation

A proposal receives `quality_milli = 1000` iff all of the following hold:

- output contract passes;
- patch applies to the exact selected parent;
- only the allowed production source is changed;
- the relevant frozen public guard passes;
- the retained reserved objective for that task passes.

Otherwise it receives `quality_milli = 0`. Mechanical-invalid proposer output is retried only as an output-format retry and is not a represented search observation.

The defect root has quality 0 after calibration. The unmodified host oracle must have quality 1000.

## Represented search cost

One represented request means one search-policy request for one parent node. If an isolated proposer invocation is retried only because its returned files fail the mechanical output contract, that retry is laboratory transport recovery and does not create another search node. A valid evaluated proposal does create a node.

For each task the policies begin from the same defect root and receive exactly the same evaluated observations until their parent selections diverge. No policy receives an observation produced only for the other policy after divergence.

## Utility

Per-task process utility is the lexicographic tuple:

`(best_quality_milli, -represented_requests, -rounds)`

Global utility is the lexicographic tuple:

`(tasks_solved_without_regression, sum_best_quality_milli, -total_represented_requests, -total_rounds)`

Lexicographic comparison is authoritative. There are no hidden scalar weights.

## L4 replication success rule

V22 is positive iff all are true:

1. G2 solves all 3/3 reserved tasks without public regression;
2. G2 has strictly higher per-task process utility than G1 on at least 2/3 tasks;
3. G2 has strictly higher global utility than G1;
4. every calibration predicate is green before the first proposer output;
5. evaluator, utility, policy identities, task mutations, host identity, and reveal boundary remain unchanged after freeze.

A failure or archival defect is reported, not repaired after observation.
