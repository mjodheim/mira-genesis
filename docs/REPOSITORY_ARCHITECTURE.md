# Repository architecture and lifecycle

This document defines the **repository boundary**, not the scientific mechanism.  Its purpose is to
keep Mira Genesis maintainable without rewriting or cosmetically relocating evidence whose paths are
part of the reproducibility record.

## Design rule

The repository contains three legitimate layers and they must not be confused:

1. **runtime/source** — reusable Python code and tests;
2. **research/evidence** — experiment protocols, preserved results and papers;
3. **governance/provenance** — decisions, hypotheses, licensing, attribution and archival indexes.

A file is not obsolete merely because it is old.  Scientific evidence is retained when it is needed
to reproduce, audit or qualify a claim.  Conversely, executable infrastructure does not remain live
merely because it once produced useful evidence.

## Canonical zones

| Path | Role | Lifecycle |
|---|---|---|
| `mira_core/` | bounded reusable runtime primitives | mutable source; covered by normal tests |
| `metamorphosis/` | current and historically coupled lineage/research implementation | mutable only under the experiment rules that govern the affected code |
| `tests/` | repository-wide regression and integrity tests | mutable validation surface |
| `scripts/` | current runners, auditors and checkers | keep only while operational or required for replay |
| `experiments/` | experiment-local protocols, fixtures and frozen records | path-stable scientific record; never bulk-move for aesthetics |
| `results/` | canonical/preserved result material | evidence, not a scratch directory |
| `papers/` | publication material | research record |
| `docs/` | maintained explanatory and governance documentation | preferred home for new non-canonical documentation |
| `archives/` | readable retired material and retirement indexes | non-executable historical surface |
| `.github/workflows/` | **currently executable** GitHub Actions only | keep deliberately small |
| `archives/workflows/` | exact copies of retired scientific workflows | immutable/read-only in practice |

Canonical root records such as `PROJECT_STATE.*`, `DECISIONS.md`, `FAILURE_LOG.md`, licensing files
and scientific criteria remain at the root because they are heavily cited and act as stable public
entry points.  They are not moved merely to make the root visually smaller.

## Why the Python packages remain top-level

A conventional `src/` layout is normally attractive, but it is not currently a free refactor here.
Preserved and recently active research tooling refers to physical paths such as
`metamorphosis/...`, not only to Python import names.  Moving the packages while that path contract
exists would require editing scientific tooling and could blur whether a replay is exercising the
same instrument.

For that reason the current flat package roots are an **explicit compatibility boundary** rather
than accidental packaging.  `pyproject.toml` lists the packages explicitly so setuptools does not
mistake `results/`, `archives/` or `experiments/` for importable packages.

A future migration to `src/` is appropriate only after a dedicated path-reference audit proves that
no preserved/current protocol depends on working-tree package paths, or after those protocols are
replayed at their frozen commits instead of the live tree.  Do the migration once, as its own
reviewed change; do not maintain duplicate root and `src/` copies.

## Workflow lifecycle

`.github/workflows/` is an execution surface, not a museum.

Permanent repository workflows may live there indefinitely.  A milestone workflow follows this
lifecycle:

1. create/freeze it while the milestone genuinely needs executable automation;
2. perform the permitted run/rehearsal under the experiment protocol;
3. when the run is consumed, the milestone is superseded, or the experiment is abandoned, copy the
   exact workflow blob to `archives/workflows/`;
4. remove it from `.github/workflows/` in the same change;
5. record significant retirements in `archives/RETIRED_CODE.md`.

The archive preserves the recipe while removal from `.github/workflows/` makes the recipe
non-executable by default.

`python scripts/audit_repository_layout.py --check` enforces this boundary.  A new milestone
workflow must be explicitly named in `ACTIVE_MILESTONE_WORKFLOWS` for as long as it is intentionally
live.

## Results and generated output

Use the following rule:

- temporary/local output -> ignored local workspace (for example `results/local/` where already
  established by the project);
- development output that can be regenerated -> do not commit unless a protocol explicitly requires
  preservation;
- canonical/qualified evidence -> commit under the experiment/result structure with its provenance;
- CI convenience artifacts -> GitHub Actions artifact storage unless the scientific record requires
  them in Git.

Never bulk-delete `results/` based on age or file size.  Classify by evidentiary role first.

## Retirement instead of accumulation

When code or infrastructure is genuinely dead:

1. verify no live source/test/runner depends on it;
2. verify the scientific record remains reconstructible from Git or a preserved artifact;
3. remove it from the working tree rather than creating another permanent copy;
4. add an entry to `archives/RETIRED_CODE.md` when the retirement is scientifically or operationally
   significant.

Git history is the primary archive for retired source.  `archives/` is used when a readable copy has
ongoing documentary value (notably sealed workflow recipes), not as a duplicate of the whole Git
history.

## Repository audit

Run:

```bash
python scripts/audit_repository_layout.py
```

The report includes:

- exact tracked-file count and tracked byte size;
- file/byte distribution by top-level zone;
- active and archived workflow counts;
- the largest tracked files;
- duplicate-content groups larger than 4 KiB;
- structural hygiene defects.

For automation:

```bash
python scripts/audit_repository_layout.py --json --check
```

The normal test suite also exercises the hygiene rules through
`tests/test_repository_layout.py`.

## Current cleanup boundary (2026-08-23)

The repository regularization performed on 23 August 2026 deliberately does **not** rewrite frozen
experiment/result paths.  It retires obsolete executable workflows, removes an unsupported stale
container entry point, documents the current zones and adds an executable hygiene audit.  This is a
structural cleanup, not a scientific result and not a modification of any preserved verdict.
