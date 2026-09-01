# M118 readiness attempt 01 — instrument abort, no verdict

**This is not a readiness verdict.** The gate aborted on its own budget arithmetic before it could
evaluate the token-capacity stress. **No `READINESS_RESULT.json` was written**, so no verdict about
the fixed route exists and none may be inferred from this directory.

| | |
|---|---|
| Frozen plan | `dabff81037af3f0bd048cc10c7ed6bf80476eb76e5ec8ea69141ecdc7786884b` (readiness revision 1) |
| Outcome | **instrument abort** — `ReadinessError: the frozen request budget is exhausted` |
| Verdict about the route | **none** |
| Readiness result written | **no** |
| Qualifying scientific invocations | **0** |

## The defect

Revision 1 fixed `MAX_REQUESTS = 12` while granting `MAX_RETRIES = 2` on each of **eleven**
mandatory requests — ten capability probes plus the stress.

**The contradiction is visible in the constants alone.** Eleven mandatory requests with up to two
retries each can consume thirty-three; a budget of twelve leaves one request of slack. Two retried
probes exhaust it, and the stress — the last and most important measurement — is refused before it
is ever sent.

This is the same species of defect as M117 attempt 02, where the token-capacity stress requested
more tokens than the eligibility rule guaranteed. Both were derivable from the frozen constants
without any observation, and both should have been caught before freezing.

## What can and cannot be said about the run

The gate reached the stress with at least twelve requests already spent. Ten probes account for ten,
so **at least two additional requests were sent**.

The only control-flow path that spends a request without returning is the retry branch, which is
entered only on an explicit HTTP 429 carrying no completion and no evidence of model execution.
**It therefore follows that at least two pre-generation 429 responses occurred.** That is an
inference from the control flow, stated as such — it is not a recorded observation, because
revision 1 recorded nothing.

**Nothing can be said about whether the route enforces its schema features, or whether it would pass
the stress.** Those measurements were either taken and discarded, or never taken.

## The second defect: the abort lost its own evidence

Revision 1 persisted nothing until the very end, so an abort discarded every observation it had
already paid for. The record could not say what the route had done, only that the gate stopped.

That is M115's failure mode returning, and an abort is precisely when the evidence matters most.

## What readiness revision 2 changes

Both fixes are derivable a priori and neither touches what the gate requires of the route.

1. **The budget is derived from the retry rule rather than chosen**:
   `MAX_REQUESTS = MANDATORY_REQUESTS * (MAX_RETRIES + 1)` = 33. The plan now refuses to freeze a
   budget that cannot accommodate the retries it grants, so this contradiction cannot recur.
2. **The ledger is persisted incrementally**, after every probe and on every abort path, naming the
   phase the run died in. An abort now preserves what it measured.

**No requirement was relaxed.** The identity, feature, stress, completion-token and reasoning
requirements are unchanged; the stress bar remains 32,000 completion tokens. No provider or model
changed — there is one route and no substitution path.

## Why re-running is not "rerunning until it passes"

The precommitted failure rule forbids rerunning until the gate passes. **That rule governs a gate
that produced a verdict.** This run produced none: it never evaluated the route, and there is no
result to overturn or improve upon.

Re-running under a corrected apparatus is the same treatment M117 gave attempts 01, 02 and 04 —
each superseded before producing a verdict, each preserved, none reinterpreted as a result.

## Claim boundary

Attempt 01 measured nothing that survives. It is **not evidence for or against H63**, says nothing
about the fixed route's readiness, and leaves G1–G10 unchanged.
