# M013e — Reproduction and evidence

## Canonical evidence

- evaluated SHA: `e309169b4edf8a508ec60990e68ba079fd032f2c`
- protocol SHA-256: `e29f024e3cc04ebd18ebd9484d499bdfbf1d98a3fbe0beb9c0ec318c8c394c5f`
- GitHub Actions run: `30637689966`
- run number / attempt: `1 / 1`
- artifact ID: `8796036463`
- artifact name: `m013e-sealed-evidence-30637689966`
- artifact ZIP SHA-256: `47888734b6c88ef5811e086bac71bbcfd8e6c14f676824eb5d6597475c7742c6`

Canonical files in the artifact:

- `M013e_full.json`: `a39a498e563e720ab5e8f16b858540a927bf9fff96f2084e9cff3bb7f57f80f3`
- `summary.json`: `478a84268e2a4552567e236149a799c75109dbf7a78f9ae057340c36b0c27100`
- `REPORT.md`: `90ed4516ebe4e7c482cd96b9e112cc3b6cdb3357af5e43c027b39d6520cd3bf8`

## Published nonce

```text
dec6efb1a8f4c44448689eebab15ceb8bea46c89dcf6df860a3dc7c086ea3d54
```

SHA-256:

```text
fedfc69a7be6acfe7184be9840911147ea94d57ae6c8011ac8440a2a13149ab6
```

## Reproduction command

```bash
git checkout e309169b4edf8a508ec60990e68ba079fd032f2c
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip pytest numpy
export PYTHONPATH=.:scripts
export GITHUB_ACTIONS=true
python scripts/run_m013e_evaluation.py \
  --canonical \
  --git-commit e309169b4edf8a508ec60990e68ba079fd032f2c \
  --github-run-id 30637689966 \
  --github-run-attempt 1 \
  --event-action opened \
  --master-nonce dec6efb1a8f4c44448689eebab15ceb8bea46c89dcf6df860a3dc7c086ea3d54 \
  --output-dir reproduced/M013e
```

Run the isolation audit separately:

```bash
python scripts/audit_m013e_isolation.py
pytest -q tests/test_m013e.py
```

## Comparison rule

The deterministic scientific content must match the canonical result exactly. Two fields are excluded from byte-level cross-machine comparison:

- `elapsed_seconds`, because wall-clock performance varies by machine and load;
- `environment`, because Python, operating-system and runner metadata may differ.

The complete canonical JSON SHA-256 is an integrity checksum for the archived run, not a requirement that another computer reproduce identical timing metadata. The independent replay matched all remaining scientific fields exactly.

## Long-term preservation

The concise canonical decision record is stored in `summary.json`. The complete result can be regenerated from the immutable SHA, published nonce and command above after the GitHub Actions artifact expires.
