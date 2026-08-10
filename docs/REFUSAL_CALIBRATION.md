# Refusal calibration for agentic tasks

## The problem

An agent that cannot tell "I have not solved this yet" from "this cannot be solved here" burns its
entire budget on tasks it was never going to finish. That cost is real and everyone pays it, but
nothing measures it, because the material to measure it does not exist.

Agent benchmarks are built from solvable tasks. An unsolvable task looks like a broken task, so it
is removed during cleaning. No major agentic suite ships a labelled unsolvable stratum, and without
one no false-refusal rate can be computed. The incentives keep it that way: on a capability
leaderboard, refusing can only lose points, so an agent that stops cleanly scores like an agent
that is merely incapable.

`mira_core.calibration` supplies the missing halves: a mechanical certificate that a required
capability is **absent from the environment the agent actually receives**, and the calibration
measures over such labels.

## What a certificate claims

A certificate says a declared capability was absent when probed. It never says no solution exists —
that is undecidable for general software tasks, and this module has no vocabulary for it. Labels
are `CAPABILITY_IMPOSSIBLE`, never "impossible". A task that is merely hard is **feasible**, and
refusing it counts against the agent.

Three rules keep the labels honest:

- only return codes declared as absence before execution produce `ABSENT`; every unexpected failure
  and every probe that could not run is `INCONCLUSIVE`;
- certificates bind both the exact probe contract and a SHA-256 of the environment configuration;
- a task declaring a capability it never probed is rejected outright;
- every arm must contain exactly one episode for every labelled task, preventing selective scoring;
- a rate with an empty denominator is `None`, never `0.0`.

That last rule matters more than it looks. Reporting an undefined rate as zero invents evidence,
and it is the most common way a calibration table lies.

## Using it

```python
from mira_core import (
    CapabilityProbe, EpisodeOutcome, EpisodeRecord, TaskLabel,
    certify, measure_calibration,
)

compiler = CapabilityProbe(
    "c_compiler", ("cc", "--version"), absent_returncodes=(127,),
)

# Run the probe inside the same container the agent gets, then certify what it returned.
absent = certify(
    compiler,
    returncode=127,
    environment_id="task-image-a1b2",
    environment_sha256="0" * 64,  # SHA-256 of the exact environment configuration
)
label = TaskLabel("build-from-source", ("c_compiler",), (absent,))

report = measure_calibration(
    [EpisodeRecord("build-from-source", "governed", EpisodeOutcome.REFUSED, steps=7)],
    {"build-from-source": label},
    "governed",
)
report.true_refusal_rate   # 1.0 — refused a task no agent could complete
report.wasted_steps        # 0  — nothing burned
```

`verdict(report, required_margin=...)` applies a threshold. The parameter has no default: a margin
chosen after seeing the report is not a threshold, and the API refuses to pretend otherwise.

## What to measure

| Measure | Question |
|---|---|
| `true_refusal_rate` | Does it stop when the capability is certified absent? |
| `false_refusal_rate` | Does it stop on tasks that were fine? |
| `calibration_margin` | The difference — the only number worth reporting alone |
| `wasted_steps` | Budget burned on impossible tasks that ended without a refusal |

A high true-refusal rate on its own means nothing: an agent that refuses everything scores 1.0. The
margin is the claim. `wasted_steps` is the number that translates directly into money.

## Limits

This measures refusal calibration. It does not measure capability, and a well-calibrated agent may
be a weak one. Labels are only as good as the probes, and a probe that tests the wrong thing
produces a confidently wrong label. Related work on selective prediction and abstention in question
answering is adjacent prior art and should be cited by anyone publishing with this: what is
different here is that impossibility is a property of the environment and must be discovered by
acting, not judged from a prompt.
