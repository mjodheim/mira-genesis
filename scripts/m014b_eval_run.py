from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import sys

from metamorphosis.m014b_sealed import runtime_nonce, sealed_spec
from m014b_eval_cases import (
    build_assets,
    run_baselines,
    run_main_and_oracle,
    run_negative_controls,
)
from m014b_eval_decision import decide
from m014b_eval_support import ROOT, report, sha256_bytes


def run(
    *,
    git_commit: str,
    output_dir: Path,
    canonical: bool,
    master_nonce_hex: str | None,
    github_run_id: str,
    github_run_attempt: int,
    event_action: str,
) -> dict[str, object]:
    protocol_path = ROOT / "experiments" / "M014b" / "protocol.yaml"
    protocol_hash = sha256_bytes(protocol_path.read_bytes())

    if canonical:
        if os.environ.get("GITHUB_ACTIONS") != "true":
            raise RuntimeError("canonical evaluation must run inside GitHub Actions")
        if github_run_attempt != 1 or event_action != "opened":
            raise RuntimeError("canonical M014b must be the first PR-opened workflow attempt")
    if master_nonce_hex is None:
        master_nonce_hex = runtime_nonce()

    spec = sealed_spec(master_nonce_hex)
    (
        plasticity,
        plasticity_json,
        generic_json,
        bases,
        targets,
        old_suites,
        new_suites,
    ) = build_assets(spec)
    trace_base: dict[str, object] = {
        "git_commit": git_commit,
        "protocol_sha256": protocol_hash,
        "github_run_id": github_run_id,
        "github_run_attempt": github_run_attempt,
        "event_action": event_action,
        "master_nonce_sha256": sha256_bytes(bytes.fromhex(master_nonce_hex)),
        "plasticity_passport_sha256": plasticity.sha256(),
        "development_provenance_sha256": plasticity.development_provenance_sha256,
    }

    main_runs, oracle_runs = run_main_and_oracle(
        spec,
        trace_base,
        plasticity_json,
        bases,
        targets,
        old_suites,
        new_suites,
    )
    random_runs, generic_runs, scratch_runs = run_baselines(
        spec,
        trace_base,
        plasticity_json,
        generic_json,
        bases,
        targets,
    )
    negative_runs = run_negative_controls(spec, trace_base, plasticity_json)
    aggregates, criteria = decide(
        main_runs=main_runs,
        oracle_runs=oracle_runs,
        random_runs=random_runs,
        generic_runs=generic_runs,
        scratch_runs=scratch_runs,
        negative_runs=negative_runs,
        plasticity=plasticity,
        plasticity_json=plasticity_json,
        git_commit=git_commit,
        protocol_hash=protocol_hash,
        github_run_id=github_run_id,
        github_run_attempt=github_run_attempt,
        event_action=event_action,
        canonical=canonical,
    )

    status = ("VALIDATED" if all(criteria.values()) else "FAILED") if canonical else "DEVELOPMENT_ONLY"
    result: dict[str, object] = {
        "experiment": "M014b",
        "status": status,
        "canonical": canonical,
        "git_commit": git_commit,
        "protocol_sha256": protocol_hash,
        "github_run_id": github_run_id,
        "github_run_attempt": github_run_attempt,
        "event_action": event_action,
        "master_nonce": master_nonce_hex,
        "master_nonce_sha256": trace_base["master_nonce_sha256"],
        "base_passport_seeds": spec.base_passport_seeds,
        "machine_seeds": spec.machine_seeds,
        "machine_families": spec.machine_families,
        "update_seeds": spec.update_seeds,
        "search_seeds": spec.search_seeds,
        "hidden_old_seeds": spec.hidden_old_seeds,
        "hidden_new_seeds": spec.hidden_new_seeds,
        "negative_base_seeds": spec.negative_base_seeds,
        "negative_update_seeds": spec.negative_update_seeds,
        "negative_kinds": spec.negative_kinds,
        "plasticity_passport": json.loads(plasticity_json),
        "environment": {"python": sys.version, "platform": platform.platform()},
        "main_runs": main_runs,
        "oracle_ceiling_runs": oracle_runs,
        "random_policy_runs": random_runs,
        "generic_no_passport_runs": generic_runs,
        "scratch_lstar_runs": scratch_runs,
        "negative_controls": negative_runs,
        "aggregates": aggregates,
        "acceptance_criteria": criteria,
        "all_criteria_passed": all(criteria.values()),
        "interpretation_limit": "Finite local DFA-edit plasticity on runtime-sealed opaque Boolean substrates; not general learning, autobiographical memory, continuous physics or open-ended self-improvement.",
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    full_path = output_dir / "M014b_full.json"
    summary_path = output_dir / "summary.json"
    report_path = output_dir / "REPORT.md"
    full_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    summary_keys = (
        "experiment", "status", "canonical", "git_commit", "protocol_sha256",
        "github_run_id", "github_run_attempt", "event_action", "master_nonce",
        "master_nonce_sha256", "base_passport_seeds", "machine_seeds",
        "machine_families", "update_seeds", "search_seeds", "hidden_old_seeds",
        "hidden_new_seeds", "negative_base_seeds", "negative_update_seeds",
        "negative_kinds", "aggregates", "acceptance_criteria",
        "all_criteria_passed", "interpretation_limit",
    )
    summary = {key: result[key] for key in summary_keys}
    summary["plasticity_passport_sha256"] = plasticity.sha256()
    summary["development_provenance_sha256"] = plasticity.development_provenance_sha256
    summary["full_result_sha256"] = sha256_bytes(full_path.read_bytes())
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report_path.write_text(report(result), encoding="utf-8")
    return result
