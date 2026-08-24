# M104 adversarial review before protocol candidate

## Scope

M104 is allowed to correct only the experiment/checker instrument around the unchanged M103
mechanism. The red-team question is whether the successor silently repairs science, reuses exposed
qualification identities or merely self-declares that its entry point works.

## Closed falsifiers

### A1 — The direct-script import failure could recur

The checker establishes the repository root from `__file__` before importing any `scripts` module.
Its `--entrypoint-preflight` is launched as an absolute direct script from a different working
directory. The subprocess succeeds and imports the M104 runner.

### A2 — The preflight could touch qualification data

The preflight function imports and binds the runner only. Tests hash the pool before and after,
require result/report absence, and inspect the preflight function's call surface. It does not open
pool, result or report paths. This validates the broken import boundary without executing M104
qualification.

### A3 — “Fresh” could mean renamed metadata over reused cases

The freshness audit compares every demand/case/probe/world identity, context token, actionable
descriptor value and complete initial value against M103. All four intersection sets are empty. The
M104 pool uses different configuration semantics, filesystem paths/content and sixteen hidden cases;
it is a complete population with no draw.

### A4 — The wrapper could change the mechanism

M104 imports the frozen M103 runner and changes only the pool preflight function and expected pool
digest for the duration of orchestration, restoring both in `finally`. Candidate construction binds
the exact M103 mechanism/checker file members recorded by protocol `cb21a4fa…`. No M103 mechanism or
capsule source is edited.

### A5 — The new checker could change favorable predicate meanings

M104 delegates P1-P15 evaluation and stable projection to the frozen independent M103 checker. It
adds only M104 result/protocol/pool bindings, replay through the M104 namespace, and process-entry
provenance. The expected predicate census remains exactly fifteen.

### A6 — Another checker exception could disappear without evidence

With `--write`, any checker exception is exclusively materialized as a negative fail-closed report,
blocking a second invocation. A positive report is likewise exclusive-create. M104 permits one
canonical result and one canonical checker attempt.

### A7 — M103 could be silently upgraded after a positive successor

D072, the M103 result tag, the negative tag and `CHECKER_FAILURE.json` remain immutable. M104 result
schema explicitly records that M103 result bytes are not used as evidence. D073 cannot alter D072.

## Residual ceiling

Even if M104 is positive, the constructor feature vocabulary, subset bound, lower interpreter,
carrier adapters, tasks, evaluator and entire population remain project-authored. M104 removes an
instrument defect; it removes no scientific bound. The next milestone must attack one of those
bounds with a new hypothesis rather than add another same-shape carrier.

