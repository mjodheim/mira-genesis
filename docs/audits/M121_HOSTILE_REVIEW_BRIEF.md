# M121/H66 apparatus — hostile review brief (v2 finding and v3 successor)

**For an independent reviewer. Prepared by the agent that wrote the apparatus, which is why it is a
brief and not a review.**

This document asks for a review; it does not perform one. The apparatus at
`metamorphosis/m121_long_horizon_v2.py` and its runner, checker and tests were written by one agent
in one sitting. That agent then went looking for variance and found a blocking defect in its own
work, recorded at `experiments/M121/V2_IMPLEMENTATION_NOTES.md`. Finding one defect is not evidence
that it found the others.

Requested output shape, following `M125_DESIGN_CORRIGENDUM_HATI_2026-09-06.md`: numbered blocking
corrections with severity, an explicit required-test delta, and a disposition. `NO-GO` is an
expected outcome here, not a failure of the review.

## Do not defer to the author

The apparatus author will read your report and act on it. Two consequences:

- do not soften a finding because the code looks careful; it was careful and still could not fail;
- do not accept the four recorded departures as settled. They are exactly where discretion was
  exercised, and jointly they are what broke falsifiability.

## Finding zero, already recorded — verify it, then go past it

Every metric the checker's negative conditions consult is constant across 200 independently drawn
salts and all four horizons. The instrument returns `positive` for every input it can receive.

Reproduce with:

```sh
python - <<'PY'
import secrets
from metamorphosis.m121_long_horizon_v2 import HORIZONS, run_horizon
seen = {}
for _ in range(200):
    salt = secrets.token_bytes(32)
    for h in HORIZONS:
        arms = run_horizon(salt, h)["arms"]
        for name, arm in arms.items():
            for metric in ("operational_detections_before_harm",
                           "quiescent_detections_before_harm",
                           "silent_divergent_outputs", "residual_corruption"):
                seen.setdefault((name, metric, h), set()).add(arm[metric])
print(sorted(k for k, v in seen.items() if len(v) > 1) or "NOTHING VARIES")
PY
```

Questions this raises that the author did not answer:

1. Is any negative condition in `check_m121_v2_result.py` reachable by **any** input the apparatus
   can produce, or only by editing the apparatus? A condition reachable only by editing the
   instrument is a self-test, not a scientific condition.
2. Does the canonical chronology — freeze, then draw, then materialize one schedule, never reroll —
   protect against a threat that can materialize here? If not, say so plainly: the ceremony would
   otherwise lend a vacuous result the appearance of rigour.
3. The four horizons produce identical numbers. What is the horizon varying, and should the
   experiment claim horizon robustness at all?

## The attack surface, in the order the author considers it most dangerous

### A. The four departures from the design candidate

Recorded in `V2_IMPLEMENTATION_NOTES.md`. Each was justified as removing an instrument-reason for
failure. Attack each as having removed a scientific one:

1. **whole-plane guarded read** — the candidate says "the next guarded operation"; the
   implementation checks every non-quarantined record every episode. Does this inflate the
   operational positive control past what any real body would do?
2. **incremental redundancy** — clearly correct as a fix, but does it make quiescent detection
   *guaranteed* rather than measured? A monitor that cannot miss is not being tested.
3. **replay on recovery** — does this make `full` structurally incapable of ending with residual
   corruption or a silent divergence, and therefore incapable of failing conditions 5 and 6?
4. **distinct targets per class** — the candidate resolves collisions on the episode only. Did
   extending it to targets remove the interference the experiment wanted to observe?

### B. An undeclared fifth design decision

`run_arm` implements **output suppression**: an arm that has detected corruption it cannot repair
declines to emit a settlement output. This is not in the design candidate. It is load-bearing — it
is what makes `no_checkpoint` show the same pre-harm detection counts as `full`, which the checker's
ninth negative condition requires.

The notes present it as "a design consequence worth stating plainly". Assess whether it is instead a
fifth departure that should have been declared as one, and whether it is the right semantics at all:
is declining to emit genuinely "preventing harm", or is it an arm scoring itself well for doing
nothing?

### C. The ground-truth boundary

`Evaluator` holds the fault-free trajectory. `tests/test_m121_v2_harness.py` enumerates
lineage-visible surfaces and asserts no expectation value appears in their serialization. Attack the
enumeration rather than the assertion: is any surface missing from it — exception text, the schedule,
checkpoint payloads, the cost record added later by `evaluation_cost.py`?

### D. The checker's independence

`check_m121_v2_result.py` reimplements the schedule generator instead of importing it, and
reimplements the deterministic cost derivation for the same reason. But it imports `run_arm` from the
apparatus to replay. A defect inside `run_arm` therefore reproduces perfectly. Is that acceptable, or
does the replay need its own reimplementation?

### E. Arithmetic and boundary conditions

- `eligible_episodes` excludes the first two and last two episodes of each quartile and every
  boundary episode. At horizon 32 a quartile is 8 episodes and only three candidates remain. Is the
  generator's rejection loop reachable to exhaustion for any salt?
- `_tag_for` and `_guard_for` are affine over a Mersenne modulus. Can a fault produce a collision
  that leaves an invariant satisfied?
- `deferred_slot_rotation` falls back to `value + 1` when a rotation is a fixed point. Is that
  fallback reachable, and does it change the fault's class?

### F. The cost record

`evaluation_cost.py` was added after the apparatus and the M121 record now carries a cost section
attached *after* `record_sha256`. Confirm that nothing verdict-bearing depends on an
environment-dependent value, and that the deterministic half is genuinely recomputable without
consulting the record.

## What is explicitly not being asked

You are being asked for a **pre-freeze self-audit**, which is what this project calls an internal
adversarial review. It is not, and must not be recorded as, the external adversarial audit the
generality decision rule requires — that requires an adversary the project does not choose. Nothing
in your report can advance a generality gate, and a `GO` disposition would authorize implementation
work only, never a canonical salt.

## The v3 successor, and the harder question it raises

After the finding above, a v3 apparatus was written to restore falsifiability:
`metamorphosis/m121_long_horizon_v3.py`, with `tests/test_m121_v3_harness.py` and
`experiments/M121/V3_DESIGN_FINDINGS.md`. v2 is not edited. v3 inherits v2's body, fault grammar and
replay by import, keeps all four v2 corrections, and adds three sources of variance: coprime
boundary and settlement cadences, a bounded monitor budget, and a matched `random_audit` control.

Falsifiability is restored and measured — and v3 then **cannot pass** under the design candidate's
clause set: 0 of 300 development salts. Attack all of the following.

### G. Is the "no good regime" conclusion sound?

The central claim is a pass-rate curve over `MONITOR_SLOTS_PER_BOUNDARY`: unbounded (8/8) passes
every clause by construction and reduces to v2; every bounded setting essentially always fails, best
9% at 6/8.

**This is a one-dimensional slice, and the author says so.** `BOUNDARY_PERIOD`,
`SETTLEMENT_PERIOD`, `DEFERRED_SLOTS`, the eight-fault budget and the injection-window rule were all
held fixed. A regime that is both falsifiable and fairly passable may exist elsewhere — a slower
settlement cadence would give a bounded audit more chances per output without making detection
certain. Is the conclusion overstated? If a better regime exists, say where, and say on what grounds
it should be chosen other than "it passes".

### H. Three clauses that are hypothesis questions, not bugs

The author deliberately did not resolve these. They are the substance of the review.

1. **Clause 5, zero residual corruption.** It presupposes an audit that eventually sees everything in
   time; a bounded audit does not provide that. Three successive apparatus changes failed to make it
   satisfiable — a closing full sweep, recovery from that sweep, and checkpoints permitted only after
   a completed audit cycle. Is the clause wrong, or is a bounded audit the wrong mechanism to claim
   retention for?
2. **Clause 9, checkpoint removal changes recovery but not detection.** v3 falsifies this: a rollback
   in `full` undoes corruption the monitor had not yet reached, so that fault is never detected while
   `no_checkpoint` keeps and later detects it. Recovery and detection are coupled once recovery can
   erase. Should the clause compare *resolved* faults (detected or erased) instead, or is the
   coupling itself the result worth reporting?
3. **Clause 11, the structured audit beats a matched random audit.** Added in v3; the measured
   distributions are near-identical. Is `random_audit` a fair matched control — its slots are drawn
   from the salt, the structured cursor from the boundary index — or does the comparison have a
   defect that manufactures the tie? If it is fair, the round-robin structure buys nothing at this
   budget, which is a substantive negative result and should be reported as one.

### I. The regression the tests caught mid-work

v3's suite asserts that verdict-bearing metrics **vary**, not merely that behaviour is correct. It
caught a fresh instance of v2's defect during v3's own construction: the closing repair was marking
still-undetected faults as *erased*, making `unrecovered_silent_divergent_outputs` constant at zero.
Fixed and recorded.

Assume there are more. In particular check the `erased_undetected` bookkeeping: is "a rollback undid
it before it mattered" always true, or can a fault be erased after it has already influenced an
emitted output?

## Current state

- no canonical salt exists for either version;
- no scientific observation exists;
- both apparatus sources are deliberately unfrozen;
- P-025 resolves publication governance only;
- `tests/test_m121_v2_harness.py` passes 76 tests and `tests/test_m121_v3_harness.py` passes 29,
  which the findings above show is not the reassurance it appears to be.
