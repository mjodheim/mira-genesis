# M071 fresh external-task selection protocol

**RULE FROZEN BEFORE ELIGIBLE INVENTORY ENUMERATION.**

M071 retains the Terminal-Bench 2 revision independently verified at remote `main`,
`2fd12b88aafdd04a52c298e3940bcb189f9766d6`. Keeping this tree fixed isolates the agent transport
correction from benchmark drift.

The two closed M070 identifiers are excluded before ranking:

- `llm-inference-batching-scheduler`;
- `rstan-to-pystan`.

They are disclosed regression history, not candidates for a second scientific threshold.

After the M071 design freeze commit `de85e31`, one 32-byte salt was drawn with the operating
system's cryptographic random generator. The draw occurred before the eligible identifier inventory
was enumerated. For each remaining tracked `task.toml`, the selector computes
`SHA-256(salt || UTF-8(identifier))`, sorts `(digest, identifier)` pairs and selects the first two.
No replacement is permitted.

The selector reads only Git tree paths and identifiers. It does not open task configuration,
instructions, environments, solutions or verifier tests. A synthetic Git fixture tests exclusion,
determinism and ordering without touching the real benchmark inventory.

This commit contains a rule, not a selected pair or result. The real selector may run only after
this protocol and its implementation are committed.
