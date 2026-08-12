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
- **External review of PR #134 found four P1 defects, all confirmed and all corrected before
  merge.** The instrument was not weakened to accommodate them; three of the four made it
  stronger.
  1. The leak scanner matched this contract's own payload schema document — see below.
  2. `assess_blind_bank_readiness` validated each sealed-stage artifact in isolation and never
     required them to describe the **same run**. An attestation from one generator run could be
     paired with a payload from another, the commitment made to name a third generator identity,
     and the ledger written to agree, with every document passing. `sealed_run_binding_problems`
     now compares every identity that must causally survive from the frozen spec through the
     container run into the commitment and the ledger.
  3. A ledger holding one `materialized` entry belonging to **another** frozen spec satisfied this
     milestone's generation stage, because the check asked only whether the current spec had
     materialized more than once, and zero is not more than one. A ledger is now one milestone's
     record: every entry must bind the frozen spec and exactly one must be a materialization.
  4. The matched-pair contract was declarative. Two independent task objects were compared on a
     shared image digest and a capability-set difference, so a pair could still differ in its
     instruction, initial state, permitted interfaces, terminal predicate or evaluator and be
     counted as evidence about a capability. **The representation changed** rather than the check
     growing: a pair now stores its shared half once and the twins are derived. No bank existed,
     which is why this was the right moment.
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
| A pair really is matched | the pair stores its goal, instruction, environment, initial state, permitted interfaces, required capabilities, terminal predicate and evaluator **once**, so the twins cannot disagree on them; `materialize_twin` derives each twin and `assert_matched_pair_delta` rejects any divergence beyond the withheld capability |
| Impossibility is caused by an absent capability | machine-checkable certificate: the capability must be required by the shared goal, absent from the environment and from every permitted interface, and sufficient — nothing else the goal needs may be missing |
| The sealed artifacts describe one run | `sealed_run_binding_problems` compares attested output against sealed payload, frozen generator identity against the commitment, and pinned image reference, image digest, runtime name and runtime version against what actually ran |
| The ledger belongs to this milestone | with a frozen spec commitment supplied, every entry must bind it and exactly one must be a materialization; a foreign entry cannot satisfy this spec's generation stage |
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
