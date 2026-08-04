# M041 status

## Current phase

Positive consumed integration result preserved. The exact mechanism is eligible for a freeze
candidate after complete Python 3.11/3.13 CI passes on the preserved pre-freeze state.

No frozen M041 protocol, sealed seed, marker-only arming commit or canonical result exists.

## Preserved base

M040 remains the immutable source of truth for cumulative post-migration plasticity. Its
canonical artefact, protocol identity, arming head, sealed seed and result remain unchanged.

M023 remains the source of truth for the earlier bounded-source disposable subprocess pattern.
M041 reuses its resource-limit discipline for a different candidate class: passive canonical
DFA data evaluated by a fixed trusted runner.

## Implemented mechanism

M041 now provides:

- deterministic passive-DFA candidate, case and workspace identities;
- a fresh temporary subprocess for every validation;
- explicit CPU, memory, filesystem, process, descriptor, wall-time, output and structural
  limits;
- independent schema, observation, regression, strict-improvement and exact-equivalence
  checks;
- a fail-closed release gate that validates before adoption;
- stale-parent, digest-tamper, non-equivalence and resource-bound controls;
- a default-disabled pre-adoption hook that leaves the M040 result surface unchanged;
- seed-only replay with byte-identical isolated validation results.

## Consumed development result

Workflow run `30934716341` reproduced the exact M040 development result, then ran M041 with the
isolated validator enabled.

- focused M041 tests: 21 passed;
- repository integrity: passed;
- unchanged M040 result digest:
  `0b1b82a742e341fdc304fe2ea4dbeb53000ff129bce32d0571ec4bf6e9373e2d`;
- M041 result digest:
  `cff9d270d317ebad7d2f54f58950511decd24156c8c20e013d7880ac5ec063ca`;
- exact result SHA-256:
  `5e885371cb0efb5e4ef3f969c1abced0f7b21a20479379899b85bd94ce6013a6`;
- first/replay workspace digest:
  `9de0a02c09f6d6487316243d0a519bdd72218a5d5e656654c24691ecf18c4735`;
- Gates 1–9: supported in development;
- Gate 10: deliberately false until a unique canonical M041 run exists.

The exact artefact is `results/artifacts/M041_DEVELOPMENT_RESULT.json`; the report is
`results/M041_DEVELOPMENT_RESULT.md`.

## Pre-freeze gate

Before a sealed block may exist, this exact functional state must pass:

- complete Python 3.11 suite;
- complete Python 3.13 suite;
- repository integrity;
- permanent M041 focused controls;
- all historical repository guardrails.

After that validation, the protocol, mechanism identities, budgets, gate definitions, sealed
seed derivation and first-run workflow may be frozen without deriving or observing the M041
canonical task.
