# M121/H66 v2 apparatus — hostile review brief

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

## Current state

- no canonical salt exists;
- no scientific observation exists;
- the apparatus source is deliberately unfrozen;
- P-025 resolves publication governance only;
- `python -m pytest tests/test_m121_v2_harness.py` passes 76 tests, which the finding above shows is
  not the reassurance it appears to be.
