# M081 — first result

**POSITIVE QUALIFIED DEVELOPMENT RESULT — TRACK A, MODEL-FREE, REAL CONTAINERS.**

Date: 2026-08-11. No external model, no external task, no third-party attestation. Docker server
reachable; both images digest-pinned and local.

## Outcome

| Arm | shell | service | State reached | Claimed | Over-report |
|---|---:|---:|---:|---:|---:|
| shared_interface | **5 / 5** | **5 / 5** | 10 | 12 | 2 |
| crossed_drivers | **0** | **0** | 0 | 12 | 12 |
| self_report_scored | 6 | 6 | 10 | 12 | **2** |

One unchanged agent emitting four abstract actions completed every completable task in both
environments, judged from a fresh state read issued after the action sequence.

## The two arms that make this mean something

**`crossed_drivers` completes nothing.** Actions are sent through the other environment's driver
while state is read from the environment under test. Without this arm, "the same interface worked in
both" would also be true of a single environment wearing two labels. Zero completions is what shows
the shell container and the HTTP service are genuinely distinct systems.

**`self_report_scored` over-reports by two, one per environment.** The shell writes to a missing
read-only path through a script ending in `; true`, exactly as real deployment scripts swallow
errors, and returns success. The service accepts a `PUT` to a sealed name with `204` and discards it,
as a real service can accept a write it later drops. Both lie. The state read catches both.

That is G6's rule — never score from self-report — **measured** rather than asserted. Scored by
claim, the interface looks 12/12. Scored by environment state, it is 10/12, and the two missing tasks
are precisely the two lies.

## The environments are real

The shell environment is a POSIX shell in an Alpine container with networking disabled, a read-only
root and a tmpfs work directory. The service environment is a real Python HTTP server process in its
own container, reached over a published loopback port. Neither is modelled in the harness; the
harness learns their state only by executing a fresh read.

If Docker were unavailable the experiment would be **inconclusive**, not negative, and the runner
says so and exits rather than recording a failure.

## Amendment A1

The first freeze was **self-contradictory**: it required all six tasks per environment to complete
while specifying that one of the six writes to a target the environment silently discards. That task
is uncompletable by construction, so no agent could meet the threshold.

A1 resolves it in the **strengthening** direction. The five completable tasks must all succeed, and
the sealed task must now be *observed to fail* under environment-state scoring while the agent claims
success. It carries a positive requirement instead of being counted as an ordinary pass. Applied
before materialization and recorded in `PROTOCOL.json` with its reason and direction.

## Recorded construction fixes

1. The crossed arm originally swapped both the driver and the environment being read, so it crossed
   nothing and completed all twelve tasks. It now sends actions through the wrong driver while
   reading the right environment.
2. The sealed task originally expected nothing, so the silent discard scored as a pass and the
   self-report arm never diverged. It now expects its resource to exist.

## Preserved evidence

- Protocol frozen before the harness: commit `7ac5ad4`; salt
  `42f58959b59b2f4c2fd3c4a318709cdf2f37887916e8f1f33c774e8dbcd76a7c`.
- Harness and amendment: commit `54b90c5`.
- Bank commitment `5261974e2eb37424816205f8a5c37979df055fbdfa30113d411d65d78ef9ccbd`.
- First result, attempt 1, no retry:
  `cc9a6e89a023ee3c9f1b5e3f5f1f8a015f57af00d53c1f1611b3b4550bb41bdc`.

`python scripts/check_m081_result.py` replays the bank, re-verifies the sealed-task construction, the
one-interface boundary and the digest pinning, and re-derives every arm against live containers when
Docker is reachable. It reported `failures: []` with `live_rederivation: performed`.

Local regressions: 17 pass without Docker, 20 with `MIRA_RUN_DOCKER_TESTS=1`. The three
container-backed tests skip in CI under the repository's existing opt-in, so CI does not exercise the
live half — a reader should treat the live evidence as local, reproducible on demand, not CI-attested.

## What this supports

Two G6 clauses: one unchanged interface driving two materially different real isolated environments,
and completion judged from environment state rather than self-report.

## What this does not support

G6 remains **open**, and the untouched clauses are the larger ones. There is **no browser**, **no
desktop VM**, no physical simulator or device, and no external suite. A container shell and an HTTP
service are two real environments, not the three G6 names. The tasks are project-authored; closure
additionally requires uncontaminated private tasks frozen after the agent design plus independent
reproduction. No Genesis Gate 2 evidence and no AGI claim.
