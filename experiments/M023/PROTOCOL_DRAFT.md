# M023 — Disposable candidate-workspace protocol draft

**Status: DEVELOPMENT ONLY. Not frozen or canonical.**

## Question

Can a self-rewrite candidate be evaluated independently from the process that proposed
it, under explicit resource limits and regression gates, before it changes the active
body?

## Workspace

Every evaluation creates a new temporary directory containing exactly three files:

- `candidate.py` — validated bounded policy source;
- `cases.json` — evaluator-owned arguments and expected values;
- `runner.py` — a fixed evaluator whose digest contributes to the workspace identity.

The directory is deleted after the subprocess exits. The candidate source remains under
M020's bounded-language rules: no imports, calls, attributes, loops, reflection,
filesystem access or network access.

## Process boundary

The runner uses an isolated Python invocation and a minimal environment. On POSIX hosts,
the child receives limits for:

- CPU seconds;
- address-space memory;
- output file size;
- process count;
- open file descriptors;
- wall-clock duration;
- captured output size.

These limits are defence in depth. They do not turn arbitrary Python into safe code and
do not replace future container or micro-VM isolation.

## Independent adoption gate

The gate receives the active versioned body and an M020 rewrite result. It independently
evaluates:

1. the current body on development cases;
2. the candidate on the same development cases;
3. the candidate on a separate regression suite.

Adoption requires all of the following:

- the rewrite descends from the current body digest;
- both candidate subprocess evaluations complete normally;
- candidate development score is strictly above the independently measured baseline;
- every regression case passes;
- M020's versioned body accepts and archives the exact parent.

A selected candidate that fails any independent gate is not adopted.

## Development gates

- a valid candidate completes in the subprocess and returns exact scores;
- runtime faults are reported without terminating the host evaluator;
- workspace identities are deterministic and change with evidence;
- a verified two-edit M020 rewrite passes independent development and regression gates;
- an improving candidate that breaks a regression is rejected;
- a stale rewrite cannot overwrite a newer body;
- resource-limit configurations reject non-positive values.

## Remaining isolation work

M023 does not yet provide kernel-level network namespaces, syscall filtering, read-only
mounts, container image pinning or multi-language builds. Those capabilities require a
later execution substrate while retaining this exact evidence and rollback model.
