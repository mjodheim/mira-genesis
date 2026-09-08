# GPT-5.6 Genesis runtime hostile review — round 2, 8 September 2026

Target: post-hardening head derived from `45dce283` (short identifier only; this note is engineering review, not a scientific record).

The first hardening pass materially closes the persistence, evaluator-binding, retention, task-identity, journal-copying, provenance and proposer-authority counterexamples encoded in PR #276. This round therefore does not reopen those findings. It tests what remains after the fixes.

## R2-1 — causal ablation is still caller-authored

The hardening rejects an ablation whose `depends_on` names an acquisition the lineage never held. That closes the exact first counterexample, but not the stronger property. If the lineage *does* hold an acquisition named `real_prior`, the proposer may still supply any deliberately weak `ablated_body_factory`, label it as `depends_on="real_prior"`, and obtain a measured loss. Nothing reconstructs the candidate with exactly that acquisition removed.

Expected repair shape: the runtime derives the ablated artifact structurally from a content-addressed candidate plus a content-addressed acquisition, or records `established: false` when it cannot prove that relation. Text identity is insufficient.

## R2-2 — migration translator receives the canonical departing record by mutable reference

`migrate()` decodes the current state into `departing`, then calls `translate(departing, ...)`, then constructs the arrival and runs `carried_intact(departing, arrived)`. A translator can mutate the supplied `departing` mapping before the arrival and the comparison are computed. The loss is then present in both sides of the comparison and disappears from `carried_intact`.

Expected repair shape: retain an immutable/canonical departure value for comparison and give the translator a deep, read-only copy or declarative context. Never compare against a value untrusted translation code was allowed to mutate.

## R2-3 — the sandbox task-set guard is reachable through the candidate's frame

The candidate executes inside `_child`. Python code can inspect the caller frame and obtain the mutable `rows` list from `_child`'s locals. A hostile body can append a row for a task it was never given. Therefore the final task-set guard is not merely an unreachable assertion about how `_child` itself constructs rows.

Expected repair shape: keep and test the guard, and ideally isolate candidate execution from mutable parent-frame bookkeeping rather than relying on the candidate not to inspect its caller.

## R2-4 — the probe state-mutation guard is reachable through a hostile Mapping collaborator

`diagnose_by_experiment()` accepts `component_operations: Mapping[...]` and calls `.get()` after serialising `state`. A Mapping implementation can mutate the referenced state as a side effect of `.get()`. The before/after guard is therefore reachable and should have a direct hostile test if the API continues to accept arbitrary Mapping implementations.

## Mutation-score interpretation

The `sandbox.py` subprocess survivor is environment-sensitive. `RLIMIT_NPROC` can independently block process creation for an unprivileged process, masking removal of the Python audit-hook guard. In a root container, `setrlimit(RLIMIT_NPROC, (0, 0))` may succeed while `/bin/true` still launches. Therefore 70/6 versus 71/5 on identical source can be a platform-dependent mutation result rather than a counting error. Mutation reports should record platform/uid and whether the independent RLIMIT control actually blocks a subprocess.

The missing-operation guard in `probe.py` is only observationally equivalent through the current sandbox outcome path: removing it changes the direct exception from `ProbeError` to `TypeError`. If that direct exception is intended API behavior, test it and kill the mutant. If it is not part of the contract, the documentation should scope the equivalence claim to sandbox-observed outcomes rather than calling the mutant globally equivalent.
