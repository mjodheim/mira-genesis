# M012b — Reproduction and evidence

## Canonical evidence

- evaluated SHA: `c60ddc28e3bea8c7c71d615dace4263f5cf3d187`
- protocol SHA-256: `b949b9d4fc61cd118af075985d1d4218c37ce7f970f28bd3598d1f38dadbd651`
- GitHub Actions run: `30635291887`
- run number / attempt: `1 / 1`
- artifact ID: `8795038626`
- artifact name: `m012b-sealed-evidence-30635291887`
- artifact ZIP SHA-256: `b8c4bc1b6302f03b088ca03b557a8ec3b17359d777aad9b9c4e7eb1190042adb`

Canonical files in the artifact:

- `M012b_full.json`: `e3c821829cf911fd65537c3aa06464dd4abe05f56df4d846fac1a8ce058c10a1`
- `summary.json`: `793a9c3a2a904547af08824c8f6f1ed189aee811e1975d2a45ded61d056a688b`
- `REPORT.md`: `e4ac73926a2689594713c9ad2d58850ce20a6656c8f065666eff05830fb03797`

## Published nonce

```text
b68a5827ba5bbd8789cf5a37d96ad618367e217381f1cbd5d9bab76ae203a30e
```

SHA-256:

```text
6b7d28657434b128194c127257eba1dfeafafc0d1ef2ed05ddf2cd8d2b2f7cbc
```

## Reproduction command

```bash
git checkout c60ddc28e3bea8c7c71d615dace4263f5cf3d187
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip pytest numpy
export PYTHONPATH=.:scripts
export GITHUB_ACTIONS=true
python scripts/run_m012b_evaluation.py \
  --canonical \
  --git-commit c60ddc28e3bea8c7c71d615dace4263f5cf3d187 \
  --github-run-id 30635291887 \
  --github-run-attempt 1 \
  --event-action opened \
  --master-nonce b68a5827ba5bbd8789cf5a37d96ad618367e217381f1cbd5d9bab76ae203a30e \
  --output-dir reproduced/M012b
```

Run the isolation audit separately:

```bash
python scripts/audit_m012b_isolation.py
pytest -q tests/test_m012b.py
```

## Comparison rule

The deterministic scientific content must match the canonical result exactly. Two fields are excluded from byte-level cross-machine comparison:

- `elapsed_seconds`, because wall-clock performance varies by machine and load;
- `environment`, because Python, operating-system and runner metadata may differ.

The complete canonical JSON SHA-256 is an integrity checksum for the archived run, not a requirement that a different computer reproduce identical timing metadata. The independent replay performed after the canonical run matched all remaining scientific fields exactly.

## Long-term preservation

The concise canonical decision record is stored in `summary.json`. The complete result can be regenerated from the immutable SHA, published nonce and command above even after the original GitHub Actions artifact expires.
