# M075-B status

**INSTRUMENT BUILT. NOTHING FROZEN, NO BANK, NO REVEAL, NO RESULT.**

- Contract: reusable across milestones, `mira-blind-bank-v1`; see
  [`docs/BLIND_BANK_GENERATION.md`](../../docs/BLIND_BANK_GENERATION.md).
- Generator: **not chosen.** Shortlist and criteria in
  [`GENERATOR_CANDIDATES.md`](GENERATOR_CANDIDATES.md).
- Frozen prompt: **not written.** Contract in
  [`GENERATOR_PROMPT_CONTRACT.md`](GENERATOR_PROMPT_CONTRACT.md).
- Phase reported by `python scripts/check_blind_bank_readiness.py`: `draft`.
- `ready_for_reveal`: `false`. `reveal_authorized`: `false`. `bank_payload_accessed`: `false`.
- Bank: absent. Generation ledger: absent. Public commitment: absent.
- Minimum bank shape enforced: 4 domains, 2 matched pairs per domain, 16 task instances — the
  same shape M075 requires of a human maintainer.
- Evidence tier this milestone can ever reach: `blind_generated_sealed_bank`.
- H21: unchanged, still not scientifically tested.
- M075: unchanged. No protocol, result, bank, hash or claim was modified.
- Issue #112: unchanged and open. Recommendation recorded in
  [`ISSUE_112_DECISION.md`](ISSUE_112_DECISION.md); no status change made.
- Gate advance: none.
- 150 focused tests. Exact instrument commit `7002e4a` passed run `31618867270`, attempt 1:
  **1,949 passed / 11 skipped** on Python 3.11 and 3.13, plus repository integrity and the new
  decisive sealed-bank boundary job; attribution run `31618864163` passed. No workflow was rerun.
- A first CI run, `31618681563`, **failed** and is preserved: the leak scanner's
  `BANK_PAYLOAD*.json` path pattern matched `docs/schemas/blind_bank_payload.schema.json`. The
  local run had missed it because the file was still untracked when the checker was first
  exercised, and the scan reads the Git index. The path patterns now skip `.schema.json`; the
  content check still reads those files, and a test pins a payload hidden under that suffix as a
  leak.

## What is enforced in code rather than promised

| Property | Enforced by |
|---|---|
| The bank is not selected on the tested system's behaviour | frozen `assembly` record; validator import graph contains no path to the agent, asserted by parsing the module |
| Impossibility is caused by an absent capability | machine-checkable certificate: the named capability must be required, absent from the environment, and the pair's only difference |
| Success is not a matter of opinion | allowlisted terminal-state evaluator kinds; `reads_agent_self_report` must be `false`; subjective tokens rejected |
| The generator saw no project context | container argv audited independently of the attestation's own booleans; mount sources resolved against the repository root; environment values checked even for allowlisted names |
| One frozen spec yields one bank | append-only ledger; two `materialized` entries under one spec commitment is a hard failure |
| Thresholds are not fitted to the bank | analysis plan frozen at F1, before generation; attainability computed and re-derived, rejecting thresholds that could never pass and ones that could never fail |
| No plaintext or key reaches this repository | path patterns, a content scan over the Git index, required `.gitignore` entries, and a sealing planner that refuses any destination inside the checkout |
| Digests are portable across checkouts | one canonical form containing no newline; every digest-bearing path registered in `.gitattributes` before the file exists |
| Reveal is a human act | signed authorization under namespace `mira-blind-bank-reveal-v1`; an unsigned authorization does not move the phase |

## Local verification

```bash
python -m pytest tests/test_blind_bank_protocol.py tests/test_blind_bank_isolation.py tests/test_blind_bank_sealing.py tests/test_m075b_blind_readiness.py -q
```

```bash
python scripts/check_blind_bank_readiness.py --assert-not-revealed
```

```bash
python scripts/check_blind_bank_leakage.py
```

```bash
python scripts/run_blind_bank_devkit.py
```

The last one drives the whole chain on a development fixture. It writes nothing into the
repository and every payload it can emit carries a schema the gate does not accept.
