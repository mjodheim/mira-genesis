# M074 — development apparatus qualification

**STATUS: LOCALLY QUALIFIED DEVELOPMENT APPARATUS. NOT FROZEN. NOT A SCIENTIFIC RESULT.**

Date: 2026-08-10. Docker client/server: 29.6.2 on the local Linux engine.

## Scope

This qualification establishes that the proposed refusal-calibration apparatus behaves as declared
on real containers. It does not evaluate a foundation model or support a refusal-capability claim.
The preserved dry run uses a deterministic label-blind scripted policy and spends zero model tokens.

## Real environment

Both images were already present locally and were addressed by repository digest:

- `alpine@sha256:d9e853e87e55526f6b2917df91a2115c36dd7c696a35be12163d44e6e2a4b6bc`;
- `python@sha256:6d43704baacd1bfbe7c295d7f13079d5d8104ed33568873133f8fc69980419df`.

Every episode used a fresh persistent no-network container with read-only root, bounded tmpfs
workspace, all Linux capabilities dropped, `no-new-privileges`, bounded CPU/memory/PIDs and agent
UID/GID 65534. The harness materialized fixtures, then the same live container was probed, acted in
and externally evaluated before removal.

## Development failure found and corrected

The first live probe run rejected the Python-absent task as `UNLABELLED`: BusyBox `command -v`
returned `127`, while the draft probe had declared only `1` as evidence of absence. This is the
intended fail-closed behavior; the unexpected code was not silently converted into `ABSENT`.

The probe contract was corrected before any freeze or scientific model call to declare the observed
BusyBox code explicitly. The next complete probe run labelled all six tasks without a bank defect.

## Preserved records

`DEVELOPMENT_PROBE_BANK.json`:

- raw file SHA-256: `51a82ca7a8ecec1a2ce43d55de87a3871c358e6bb3f427682ec98756e1ad0827`;
- 3 feasible and 3 capability-impossible live labels;
- zero bank defects;
- exact probe, task and environment bindings retained per row.

`DEVELOPMENT_DRYRUN.json`:

- raw file SHA-256: `2abbf79444e37c38b1f2fb6c17ef764c281d98579c54dbfd2511211914ee114f`;
- 12 fresh real-container episodes: 6 tasks × 2 arms;
- 6/6 feasible arm episodes passed external final-state evaluation;
- 0/6 capability-impossible arm episodes passed external final-state evaluation;
- `A-terminal-refusal`: true-refusal rate 1.0, false-refusal rate 0.0, margin 1.0,
  zero wasted steps;
- `B-nonterminal-refusal`: true-refusal rate 0.0, false-refusal rate 0.0, margin 0.0,
  12 wasted steps;
- zero apparatus defects and zero model tokens;
- calibration digest `71fc5f5d5f68db97557325a56254c22325dfe2fba5db9229259a1ef85c7cbbc3`.

The two arms enforce identical authority admission and hash-chained audit. Only refusal termination
differs. The removed raw/audit arm duplicated a contrast already answered by M072 and produced the
same refusal outcome as the nonterminal arm, so retaining it would add a confound rather than a
measurement.

## Permanent verification

`python scripts/check_m074_development.py` reconstructs all six certificates and labels from the
current task contracts, verifies exact task/environment bindings and complete 12-episode coverage,
recomputes both calibration reports and reproduces the calibration digest without Docker.

The exact final focused campaign passes 65 tests, including mutation checks for environment-binding
drift, selective episode removal and malformed certificate inputs. Immediately before the final
input-type guards, the complete local Python 3.14.6 suite passed **1,320 tests with two expected
skips in 2,321.91 seconds**; the affected final tests and repository integrity then passed again.

Exact apparatus commit `27a2e1f` passed first GitHub CI run `31377768229`: **1,322 passed and one
skipped on Python 3.11 in 1,238.57 seconds, and 1,322 passed and one skipped on Python 3.13 in
1,255.09 seconds**, plus repository integrity. Attribution run `31377768244` passed. No workflow
rerun was used.

## Decision boundary

The apparatus is ready for protocol design, not scientific execution. Before any model sees a task,
M074 still needs an exact-code freeze, numeric threshold, model/prompt/budget commitment, ordered
single-attempt execution protocol and independent exact-commit qualification. See
`DRAFT_REFUSAL_CALIBRATION_DESIGN.md`.
