# M051 — bounded variable-length primitive composition

**Status: PASSED IN DEVELOPMENT.**

## Objective

Advance one bounded step beyond M050 by allowing a migration strategy to contain zero, one or two ordered input transformations before one reduction and one empty-input policy.

## Frozen grammar and budget

- transformations: `absolute`, `unique`, `nonnegative`;
- transformation depth: `0..2`;
- repeated transformations: forbidden;
- reductions: `maximum`, `minimum`, `sum`, `mean_floor`;
- empty policies: `zero`, `reject`;
- total candidates: exactly `80`;
- arbitrary source generation: forbidden;
- grammar widening after hidden evidence: forbidden.

The proposer receives public probes only. It succeeds only when exactly one candidate survives. A separate validator owns hidden probes and has no adoption authority.

## Permanent episodes

1. a positive episode requiring the ordered chain `absolute -> unique`, followed by `sum` and `zero`;
2. an ambiguous public episode that must terminate with `insufficient_evidence`;
3. a contradictory public episode with no survivor;
4. independent hidden acceptance and rejection;
5. tamper rejection and deterministic replay.

## Qualification history

The first qualification run, CI `418` on commit `ff30ff1f71a11b0d2e09c8c3ab15e082725a33e6`, completed successfully without a failed job or rerun:

- 830 tests passed on Python 3.11 with Node.js 20.20.2;
- 830 tests passed on Python 3.13 with Node.js 20.20.2;
- repository integrity passed, including clean imports, orphan-module detection and dependency matching.

No negative qualification result was produced before this positive result. This absence is recorded only as history and is not evidence of general correctness.

## Authority boundary

The experiment has no network, repository, credential, deployment or production authority. It cannot create arbitrary code, discover an unknown runtime or alter the frozen grammar.

## Cleaning decision

No source, test, protocol, workflow or artifact was removed during qualification. The repository-integrity audit found no orphan module or dependency mismatch. Node.js 20 was deliberately retained because its exact runtime identity is part of the already qualified M048–M051 evidence; replacing it during this closure would change the experimental substrate rather than constitute safe cleanup.

## Claim boundary

M051 is a bounded noncanonical experiment over one closed grammar and fixed probe families. It does not establish unrestricted compiler synthesis, arbitrary program induction, open-ended evolution, general intelligence, consciousness or production safety. M042 remains the only positive canonical continuous-lineage completion.
