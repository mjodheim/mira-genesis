# M051 — bounded variable-length primitive composition

**Status: IN DEVELOPMENT.**

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

## Authority boundary

The experiment has no network, repository, credential, deployment or production authority. It cannot create arbitrary code, discover an unknown runtime or alter the frozen grammar.

## Qualification rule

M051 may be described as passed in development only after the complete Python 3.11 and Python 3.13 test matrix and repository-integrity job pass on the exact PR head. Every failed qualification remains part of the append-only record and must not be rerun away.

## Claim boundary

M051 is a bounded noncanonical experiment over one closed grammar and fixed probe families. It does not establish unrestricted compiler synthesis, arbitrary program induction, open-ended evolution, general intelligence, consciousness or production safety. M042 remains the only positive canonical continuous-lineage completion.
