# Reproducibility

## Reproducing the working tree

1. Python 3.11 or later.
2. `pip install -e ".[dev]"`.
3. `pytest -q` — the whole suite must pass.
4. `python scripts/check_repository_integrity.py` — importability, absence of orphan
   modules, and consistency of the declared dependencies.

For the current adaptive-embodiment frontier:

```bash
python scripts/check_m068_frozen_protocol.py
python scripts/run_m068_development.py
python scripts/run_mira_core_demo.py
```

The freeze check verifies the LF-normalised target bytes and live opaque attestation. The M068
runner emits the deterministic development manifest; the Mira Core demo exercises the reusable
least-privilege agent loop independently of the scientific result.

These four steps are exactly what `.github/workflows/ci.yml` runs on every pull request,
on Python 3.11 and 3.13.

## Reproducing a canonical result

Every canonical result is identified in `results/<ID>.md` by:

- the evaluated commit SHA, immutable;
- the SHA-256 of the frozen protocol;
- the GitHub Actions run id and attempt number;
- the SHA-256 of the evidence artifact.

Reproduction starts from the published nonce, at the evaluated commit:

```bash
git checkout <evaluated SHA>
```

```bash
python scripts/run_<ID>_evaluation.py --help
```

The exact CI recipe of every consumed sealed evaluation is kept in
`archives/workflows/`. Those workflows are deliberately made non-executable: the rule
"one canonical run, never replayed" forbids re-running them.

## Reproducing the measure failures

The catalogue in `MEASURES.md` replays on demand, each case with its ground truth:

```bash
python scripts/reproduce_measure_failures.py
```

## What a future result must contain

Every new result must carry the seed, the Git commit, the protocol hash, and a decision
trace portable bit for bit. M014b showed that a consolidation hash embedding
floating-point scores is not reproducible across environments: decisions and hashes must
rest on integers or canonical rationals.

Development benchmarks deliberately exclude elapsed time from their result files. It
depends on the machine and the core count, and would make the artifact non-comparable
byte for byte; the reproduction audit of M014b already excluded it.

## Scope

The scripts in `scripts/` correspond to experiments **M012b and later**. No M001–M011
code exists in this repository; see `archives/README.md`.
