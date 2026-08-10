# M077 — first result

**NEGATIVE RESULT ON THE PREREGISTERED DISSOCIATION. TWO POSITIVE SUB-RESULTS PRESERVED.**

Date: 2026-08-10. Track A, model-free. No external model, no network, no external task, no
third-party attestation. Horizons are **episode counts**, never human-equivalent time.

## Outcome

| Arm | h32 | h128 | h512 | h2048 |
|---|---|---|---|---|
| full | 4/4 · 1.00 | 4/4 · 1.00 | 8/8 · 1.00 | **32/32 · 1.00** |
| no_checkpoint | 4/4 · **0.00** | 4/4 · **0.00** | 8/8 · **0.00** | 32/32 · **0.00** |
| no_constraint_monitor | 4/4 · 1.00 | 4/4 · 1.00 | 8/8 · 1.00 | 31/32 · 1.00 |
| idle_floor | 0/4 | 0/4 | 0/8 | 0/32 |

Cells are `faults detected / faults injected · restoration rate on detected`.

**The hypothesis is refuted.** `no_constraint_monitor` was required to lose detection at every
horizon. It loses one fault out of 32 at the longest horizon and nothing at the other three.

## Why it failed, and why that is the finding

Faults were split into an operational class that makes a legitimate operation impossible — journal
truncation, capacity overflow — and a silent class that only a boundary audit should catch: slot
type corruption and a staled checkpoint reference.

That split does not survive a long shift. A silently corrupted pool keeps being written to, and the
corruption reaches an operation that cannot complete. The body then raises on its own, without any
boundary audit. Removing the constraint monitor therefore delays detection instead of removing it.

**In this body the boundary monitor is redundant with operational failure.** That is a real
statement about the design, and it is more useful than a pass would have been: it says a periodic
invariant audit buys latency, not coverage, whenever every corruption eventually touches a guarded
operation. A monitor earns its place only against corruptions that can stay quiescent forever.

## The two positive sub-results

They are preserved because they are real, and reported as sub-results because the preregistered
claim was the conjunction.

- **Retention does not degrade with horizon.** The full arm holds all four invariants, detects and
  recovers every injected fault, requires zero interventions and ends with zero residual violations
  at 32, 128, 512 and 2048 episodes. Perfect at the shortest horizon and still perfect at the
  longest, with fault count scaling as `max(4, horizon // 64)`.
- **Checkpoint recovery is causally isolated.** `no_checkpoint` drops the restoration rate to
  exactly 0.00 at every horizon while its detection count stays numerically identical to the full
  arm. One mechanism removed, exactly one capability lost.

The `idle_floor` arm completes zero work and still ends with residual violations, so a
zero-violation score cannot be earned by doing nothing.

## Recorded instrument corrections

Both were applied before schedule materialization and are stored in `RESULT.json`.

1. Detection was counted per event, which let detections exceed injected faults: an unrepaired fault
   re-triggers on every later episode. Accounting is now per unique fault.
2. The outstanding-fault tracker was a single slot, which could not represent faults landing on
   adjacent episodes. At horizon 2048 two pairs land one episode apart, and the earlier fault was
   silently dropped, costing the full arm a spurious miss while `residual_violations` was zero.

The first correction moved the failure from one arm to another. A third iteration would have been
tuning until the remaining arm complied, and was not performed. The negative stands.

## Preserved evidence

- Protocol frozen before the harness: commit `31b2778`; salt
  `c24a8c49ebd2357c34299ec706f93ce323d4aba383281f8680cc4db722d12e03`.
- Harness and recorded corrections: commit `720bad4`.
- Schedule commitment `80e92af496798417117b5b173aa852aefb1ec1351474ea3f138c2c800e8a9d13`.
- First result, attempt 1, no retry:
  `93ecd2d082e9b58e2913355f86b4b5a576cd72a63fe1b9fff232477c15d983d9`.

`python scripts/check_m077_result.py` rebuilds every schedule from the salt, re-derives all four
arms and fails closed if the preserved negative ever silently becomes positive. It reported
`failures: []`.

## Claim boundary

G7 remains **open**. A negative does not advance a gate, and the two sub-results are bounded
mechanism evidence inside one project-authored in-memory body. Nothing here is a human-equivalent
task horizon, real-environment autonomy, Genesis Gate 2 or Gate 3 evidence, or AGI evidence. A
successor must not reuse this schedule or relabel the same body as new evidence.
