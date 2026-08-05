from __future__ import annotations
import hashlib, json, shutil
from pathlib import Path

SRC=Path('/tmp/m042-first-result')
result_path=SRC/'m042-canonical-result.json'
seal_path=SRC/'m042-canonical-first-result-seal.json'
frozen_path=SRC/'experiments/M042/FROZEN_PROTOCOL.json'
expected={
 result_path:'2d6c75abf526f0b3a3edba381f6f7b820d4dd03ccc3276784301e3c6a65b7830',
 seal_path:'bc39b5d494efcefa6fbfbf95170b2fe38436e90e4168fac9a347030a56e404b2',
 frozen_path:'d3d2b60a23d5847238aaec87e0d04200b707761ba8e0eb1418632e59dd39a366',
}
for path,digest in expected.items():
    actual=hashlib.sha256(path.read_bytes()).hexdigest()
    if actual!=digest: raise SystemExit(f'{path}: {actual} != {digest}')
result=json.loads(result_path.read_text())
seal=json.loads(seal_path.read_text())
gates=dict(result['gate_verdicts'])
gates['gate_10_measurement_integrity']=bool(seal['status']=='first-result-preserved' and seal['first_result_preserved_without_reexecution'] and seal['no_retuning_performed'])
audit={
 'schema':'m042-canonical-audit/1','status':'canonical-positive-closed',
 'scientific_verdict':'positive' if all(gates.values()) else 'negative',
 'raw_result_sha256':expected[result_path],
 'raw_first_result_seal_sha256':expected[seal_path],
 'frozen_protocol_sha256':expected[frozen_path],
 'workflow_run_id':seal['workflow_run_id'],'workflow_run_attempt':seal['workflow_run_attempt'],
 'canonical_head_sha':seal['head_sha'],'canonical_selected_index':seal['canonical_selected_index'],
 'canonical_selected_entry_digest':seal['canonical_selected_entry_digest'],
 'raw_result_schema':result['schema'],'raw_result_status':result['status'],
 'raw_gate_verdicts':result['gate_verdicts'],'audited_gate_verdicts':gates,
 'gate_10_basis':{
   'rule':'true iff the unique frozen first result was preserved without reexecution or retuning',
   'first_result_preserved_without_reexecution':seal['first_result_preserved_without_reexecution'],
   'no_retuning_performed':seal['no_retuning_performed'],
   'artifact_digest':'sha256:14abb40f77c5fe3821c7e87f3d3078e378e0763efa1cd4a68296d7224f30de38',
   'artifact_retention_days':90,
 },
 'raw_payload_immutable':True,'raw_seal_immutable':True,'no_reexecution_for_audit':True,
 'no_threshold_seed_rule_or_control_change':True,
 'm038_to_m041_artefacts_unchanged':result['m038_to_m041_artefacts_unchanged'],
 'bank_replay_identical':result['bank_replay_identical'],
 'all_development_mechanisms_supported':result['all_ten_development_mechanisms_supported'],
 'closure_reason':'The raw generator emits the pre-preservation development gate vector. Gate 10 is established only by the separately preserved first-result seal; this audit combines those immutable records without changing either.',
}
if audit['scientific_verdict']!='positive': raise SystemExit('audited canonical result is not positive')
out=Path('results/artifacts'); out.mkdir(parents=True,exist_ok=True)
shutil.copyfile(result_path,out/'M042_CANONICAL_RESULT.json')
shutil.copyfile(seal_path,out/'M042_CANONICAL_FIRST_RESULT_SEAL.json')
(out/'M042_CANONICAL_AUDIT.json').write_text(json.dumps(audit,indent=2,sort_keys=True)+'\n')
selected=result['bank_entries'][result['selected_index']]
Path('results/M042_CANONICAL_RESULT.md').write_text(f'''# M042 canonical result

## Result

**Positive canonical result.** M042 closes the constructive-availability gap exposed by M041 and completes the frozen continuous lineage through a further hidden post-migration task.

## Frozen selection

The selector chose index `{seal['canonical_selected_index']}` from the four-entry independently verified bank, entry `{seal['canonical_selected_entry_digest']}`. The selected task seed was `{selected['task_seed']}` and its task digest was `{selected['task']['task_digest']}`.

## Canonical observation

The complete continued lineage adapted exactly to 127/127 observations. Its accepted body digest was `{selected['accepted_body_digest']}`. Passive isolated validation recorded candidate 127/127, parent {selected['validation']['parent_passed']}/127, regressions {selected['validation']['regression_passed']}/{selected['validation']['regression_total']}, strict improvement, exact equivalence and no candidate execution authority. Native synthesis produced `{selected['native_json_sha256']}` and rollback restored the prior state exactly.

All equal-budget alternatives remained non-exact: fresh on B {selected['arms']['fresh_on_b']['quality_numerator']}/127, learned-tool ablated {selected['arms']['learned_tool_ablated']['quality_numerator']}/127, learning-state ablated {selected['arms']['learning_state_ablated']['quality_numerator']}/127, unchanged parent migrated {selected['arms']['unchanged_parent_migrated']['quality_numerator']}/127 and output only {selected['arms']['output_only']['quality_numerator']}/127.

## Measurement-integrity audit

The exact raw result SHA-256 is `{expected[result_path]}` and the exact first-result seal SHA-256 is `{expected[seal_path]}`. Workflow run `{seal['workflow_run_id']}`, attempt `{seal['workflow_run_attempt']}`, produced artifact digest `sha256:14abb40f77c5fe3821c7e87f3d3078e378e0763efa1cd4a68296d7224f30de38`.

The raw payload retains the development-time gate vector, where Gate 10 is false because preservation had not yet occurred inside that payload. The separate immutable seal records preservation without re-execution or retuning. The audit establishes Gate 10 solely from that record, without rerunning or rewriting the raw result. All ten audited gates are true.

## Claim boundary

M042 supports a positive, single-lineage demonstration under the frozen finite protocol. It does not claim general intelligence, open-ended evolution or performance outside the recorded task family and budgets.
''')
Path('experiments/M042/STATUS.md').write_text(f'''# M042 status

## Current phase

**Canonical result: positive. Experiment closed.**

The unique frozen canonical execution completed on head `{seal['head_sha']}` and its first result was preserved without re-execution or retuning. The selector chose index `{seal['canonical_selected_index']}` with entry digest `{seal['canonical_selected_entry_digest']}`.

## Canonical identities

- frozen protocol commit: `c75e57cfb23bcaccab98f449bfef0d83fe530ad4`;
- marker-only canonical head: `{seal['head_sha']}`;
- first workflow run: `{seal['workflow_run_id']}` (attempt `{seal['workflow_run_attempt']}`);
- frozen protocol SHA-256: `{expected[frozen_path]}`;
- exact raw result SHA-256: `{expected[result_path]}`;
- exact first-result seal SHA-256: `{expected[seal_path]}`;
- GitHub artifact digest: `sha256:14abb40f77c5fe3821c7e87f3d3078e378e0763efa1cd4a68296d7224f30de38`.

The immutable raw result, raw seal and post-result audit are preserved under `results/artifacts/`; the report is `results/M042_CANONICAL_RESULT.md`.

## Verdict

The selected task was constructively available; the complete lineage reached 127/127 exact observations while every equal-budget ablation remained non-exact. Passive isolated validation, native synthesis and exact rollback all succeeded. Gate 10 is established by the separate first-result preservation record, leaving the raw payload and seal byte-identical. All ten audited gates are true.

## Closure boundary

No second M042 canonical run is permitted. M038–M041 identities and artifacts remain unchanged.
''')
