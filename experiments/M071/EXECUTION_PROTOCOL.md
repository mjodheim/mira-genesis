# M071 external execution protocol

**FROZEN BEFORE ANY SELECTED TASK OR FLOOR CONTROL IS EXECUTED.**

Canonical JSON SHA-256:
`31d3c7bd968cb3fc381b8c3272b599695f3294c8537a1d8d805fc0ef334e0555`.

## Falsifiable claim

The composed system frozen by M071 must earn official reward `1.0` on at least one of
`sqlite-with-gcov` or `custom-memory-heap-crash`. Both trials must be valid and externally scored;
both `nop` controls must score `0.0`. A valid lower reward, policy failure, refusal, step exhaustion
or rejected submission is negative evidence.

This is public development evidence about the named composed system. It is not evidence that Mira
owns the external model's proposed transformations, does not satisfy Genesis Gate 2, and cannot
establish AGI or safe deployment.

## Immutable execution order

One process at a time, with zero Harbor retries:

1. SQLite `nop` floor;
2. SQLite M071;
3. custom-memory `nop` floor;
4. custom-memory M071.

There is one attempt for each cell, no replacement and no reordering. An infrastructure retry is
permitted only before any model decision and before any verifier reward, with identical inputs and
a recorded incident. A scientifically valid attempt is never retried.

The agent has at most 16 decisions, 120 seconds per command, 180 seconds per model call and 65,536
visible output characters. Harbor's task-owned agent timeouts are 900 seconds for SQLite and 1,800
seconds for custom-memory. The official external verifier alone determines reward.

## Environment and contamination boundary

Both original image tags were resolved and replaced by their repository digests. The only other
task-package change is `[agent].network_mode = "no-network"`. The original public environment and
verifier policies remain otherwise unchanged.

Instructions and environment sources were opened only after commit `b403920` bound the pair.
Reference solutions and verifier tests have not been opened by the operator and must never enter
the model context. Agent setup performs no action before Harbor applies the no-network phase.

## Attribution

Any reward belongs to the named combination of `gpt-5.6-sol`, policy
`m071-governed-model-policy-v1`, the frozen UTF-8/process-tree transport, Harbor container body and
external evaluator. `nop` is an empty-action floor, not an ablation of Mira governance. The direct
Mira-layer evidence in this experiment is limited to frozen authority, isolation, transport,
failure and audit invariants.
