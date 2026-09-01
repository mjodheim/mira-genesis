# M118 / H63 — preregistration

**Status:** FROZEN before any H63 observation exists.
**Predecessor:** M117, closed as instrument development with its hypothesis untested.
**Qualifying scientific invocations:** 0.

## Why a new hypothesis number

H63 states the same scientific proposition H60, H61 and H62 were intended to test. The new number is
**procedural, not scientific**.

M117 disclosed that five apparatus revisions occurred inside it and that some followed real endpoint
observations. Reusing H62 would implicitly claim that M117's iteratively repaired route-selection
process was itself prospectively clean. It was not, and M117 says so.

M118 begins from a different position: **a fixed, already-calibrated route and an apparatus that will
not be modified after its prospective freeze.** H62 is not revived. M117/H62 closes as
*instrument-development completed; scientific hypothesis untested*.

## The fixed route

| | |
|---|---|
| Requested model | `deepseek/deepseek-v4-flash-0731` |
| Provider | **OpenInference** |
| Canonical checkpoint | `deepseek/deepseek-v4-flash-20260731` |

Fixed in `metamorphosis/m118_route.py` by this preregistration — not chosen at run time, not ranked,
not selected from a universe. **There is no second route in that module and no code path that could
substitute one.**

### Justification, and what it is not

This route is justified **solely by prior DEVELOPMENT calibration evidence from M117**: it was the
only candidate that qualified, on the milestone's final apparatus revision, at the earliest
qualifying position of an order frozen before that attempt's probing began. It passed all twelve
clauses and emitted 68,368 conforming completion tokens against the census-dominating stress schema
with `finish_reason: stop`.

**It was not selected using any H63 carrier outcome, because no H63 carrier exists.** Nothing about
H63 informed the choice; H63 had not begun when the calibration ran.

### After preregistration begins

- **No provider substitution.**
- **No fallback.**
- **No second route.**

If the route becomes unavailable or fails readiness, **H63 stops before scientific generation.** It
does not switch to a next-best route — there is no next-best route to switch to.

## The readiness gate

M117 observed that structured-output behaviour is **not stable run to run**: one model returned every
required feature class enforced in one attempt and none in another. A single historical calibration
therefore cannot be trusted indefinitely.

One fixed DEVELOPMENT readiness gate runs before the H63 scientific freeze, answering exactly one
question:

> Does the fixed H63 route still provide the instrument properties already established during
> calibration?

It **does not** select among providers — there is one route. It **does not** compare carrier quality.
It **does not** use the H63 qualifying input, which does not exist when it runs.

Frozen before execution, in `scripts/audit_m118_readiness.py`: the exact schemas, prompts, request
body construction, reasoning control, identity requirements, no-fallback requirements, feature
requirements, stress requirement, completion-token threshold, retry rule, stopping rule and result
classifier. The plan digest binds them and the result records it.

### What it requires

- Exact requested model, exact canonical checkpoint, exact provider.
- Direct route, routing attempt 1, exactly one selected endpoint, **no fallback**, no pipeline
  intervention.
- **Every required schema feature class enforced**, and the combined structural probe conforming.
- The **census-dominating stress schema**: HTTP 200, `finish_reason = stop`, schema-conforming
  output, **completion tokens > 32,000**.
- **Reasoning state exactly as intended**: the control sent on every request, and no reasoning tokens
  consumed. M117 calibration observed exactly this on the fixed route — 0 reasoning tokens across all
  ten probes with the control applied — so the requirement is achievable and is not a bar invented
  here.

> **Readiness apparatus revision 2.** Revision 1 (`dabff810…`) aborted on its own budget
> arithmetic before it could evaluate the stress, writing no verdict. It fixed the budget at 12
> while granting 2 retries on each of 11 mandatory requests — a contradiction visible in the
> constants alone. The budget is now *derived* from the retry rule
> (`mandatory × (retries + 1)` = 33) and the plan refuses to freeze one that cannot afford the
> retries it grants; the ledger is also persisted incrementally, so an abort preserves what it
> measured instead of discarding it. Preserved in
> [`READINESS_ATTEMPT_01_INSTRUMENT_ABORT/`](READINESS_ATTEMPT_01_INSTRUMENT_ABORT/README.md).
> **No requirement was relaxed and no route changed.**

**No content-dependent redraw.** The only surviving retry is the inherited one: an explicit
pre-generation HTTP 429 carrying no completion and no evidence of model execution.

### Feature coverage, stated honestly

The census requires **eleven** keywords; the inherited matrix carries **nine** named probes. The two
without a probe of their own are **not unassessed**: `items` is structurally present in every array
probe, and `maximum` is exercised by the integer-bounds probe, which is labelled for `minimum`. The
gate computes this mapping from the probe schemas rather than asserting it, and names any required
keyword that reaches no probe at all. **None does.**

## Readiness failure rule — precommitted

If the fixed route fails the gate, **M118/H63 stops before scientific generation.**

Do **not**: change provider; change model; weaken the stress; remove a schema requirement; rerun
until it passes; create a carrier bank.

Record: **H63 untested / instrument unavailable at execution time.** A successor milestone may later
use a newly preregistered instrument strategy.

## Readiness success rule — precommitted

If the route passes, **commit the readiness result**, then freeze the complete H63 scientific
apparatus before any qualifying generation.

**The readiness result must not be used to alter the H63 scientific proposition, carrier schema,
thresholds or tested-system machinery.** It answers whether the instrument still works. Nothing else.

## Required chronology

The repository must be able to prove this order, from committed state:

```
M117 calibration complete
  → M118/H63 preregistration
  → fixed OpenInference route
  → readiness apparatus frozen
  → readiness DEVELOPMENT run
  → readiness result committed
  → H63 plan / spec / request / nonce frozen
  → complete tested-system freeze committed
  → unique H63 qualifying generation
  → machine-only admission
  → seal, or terminal abort
  → reveal authorization
  → one reveal
  → frozen scoring
  → independent replay
```

The delivery runner **fails closed** if the required committed predecessor does not exist at HEAD.
**No in-memory freeze satisfies this.**

## Claim boundary

The readiness gate is DEVELOPMENT. It is **not evidence for H63**, sends no qualifying input, and
cannot advance a generality gate. G1–G10 are unchanged by anything in this document.
