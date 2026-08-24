"""Fail-closed static/dynamic audit of M103 information and authority boundaries."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis import m103_runtime as runtime  # noqa: E402
from scripts import author_m103_development_fixture as fixture_author  # noqa: E402
from scripts import author_m103_predecessor_conservation as conservation_author  # noqa: E402
from scripts import author_m103_qualification_pool as pool_author  # noqa: E402


RUNTIME = ROOT / "metamorphosis" / "m103_runtime.py"
PROCESS = ROOT / "scripts" / "run_m103_process.py"
FIXTURE = ROOT / "experiments" / "M103" / "DEVELOPMENT_FIXTURE.json"
POOL = ROOT / "experiments" / "M103" / "QUALIFICATION_POOL.json"
PREDECESSOR_CONSERVATION = (
    ROOT / "experiments" / "M103" / "PREDECESSOR_CONSERVATION.json"
)
RESULT = ROOT / "experiments" / "M103" / "RESULT.json"
CHECK_REPORT = ROOT / "experiments" / "M103" / "CHECK_REPORT.json"

M102_U2_RAW_SHA256 = "3bad4d5400e8d9a11b15ba596336925823ffb4064a5bbe38f93f64b7384a198d"
M102_U2_STATE_DIGEST = "fbf7b0232aa8adf4e67513719c63f19f28c1b7e8b86437af1135ff18335d3a0e"
VALIDATED_S_PRIME_FEATURES = {
    "OBSERVE_CONTEXT",
    "PARTITION_EQUAL",
    "SYNTHESIZE_PARTITIONS",
    "EMIT_GUARDED",
}


def _m102_u2_bytes() -> bytes:
    result = json.loads((ROOT / "experiments" / "M102" / "RESULT.json").read_text(encoding="utf-8"))
    state = result["scientific_evidence"]["states"]["U2"]["state"]
    return runtime.canonical_json(state).encode("ascii")


def audit() -> dict[str, Any]:
    runtime_source = RUNTIME.read_text(encoding="utf-8")
    process_source = PROCESS.read_text(encoding="utf-8")
    runtime_tree = ast.parse(runtime_source)
    process_tree = ast.parse(process_source)
    imports = sorted(
        {
            alias.name.split(".")[0]
            for tree in (runtime_tree, process_tree)
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        | {
            (node.module or "").split(".")[0]
            for tree in (runtime_tree, process_tree)
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
    )
    forbidden_imports = sorted(
        set(imports)
        & {
            "httpx",
            "requests",
            "socket",
            "subprocess",
            "urllib",
            "mira_core",
            "scripts",
        }
    )
    forbidden_source_terms = sorted(
        term
        for term in (
            "QUALIFICATION_POOL",
            "experiments/M103",
            "RESULT.json",
            "CHECK_REPORT.json",
            "github",
        )
        if term in runtime_source or term in process_source
    )

    fixture = json.loads(FIXTURE.read_text(encoding="ascii"))
    deterministic_fixture = fixture_author.build_fixture()
    fixture_exact = fixture == deterministic_fixture
    pool = json.loads(POOL.read_text(encoding="ascii"))
    pool_exact = pool == pool_author.build_pool()
    conservation_fixture = json.loads(PREDECESSOR_CONSERVATION.read_text(encoding="ascii"))
    conservation_exact = conservation_fixture == conservation_author.build_fixture()
    predecessor = _m102_u2_bytes()
    v0 = runtime.create_state(predecessor)
    acquisition = runtime.acquire_constructor(v0, fixture["producer"], register_result=True)
    if acquisition["confirmed"] is not True:
        raise RuntimeError("M103 boundary audit could not acquire S-prime on DEVELOPMENT")
    v1 = acquisition["next_state"]
    s_prime = v1["constructor"]
    s_prime_text = runtime.canonical_json(s_prime).lower()
    leaked_identities = sorted(
        term
        for term in (
            "north",
            "south",
            "amber",
            "violet",
            "outcome",
            "configuration",
            "configparser",
            "filesystem",
            "path",
            "file",
            "production",
            "release",
        )
        if term in s_prime_text
    )
    m102_state = json.loads(predecessor.decode("ascii"))
    exact_winning_literals: list[list[str]] = []
    for node in ast.walk(runtime_tree):
        if not isinstance(node, (ast.List, ast.Set, ast.Tuple)):
            continue
        values = [
            item.value
            for item in node.elts
            if isinstance(item, ast.Constant) and isinstance(item.value, str)
        ]
        if len(values) == len(node.elts) and set(values) == VALIDATED_S_PRIME_FEATURES:
            exact_winning_literals.append(sorted(values))
    feature_ablation_attempts = {
        feature: runtime.construct_hypothesis(
            runtime.constructor_definition(
                runtime.S_PRIME_ORIGIN,
                [item for item in s_prime["features"] if item != feature],
            ),
            fixture["producer"],
        )
        for feature in s_prime["features"]
    }
    pool_text = runtime.canonical_json(pool).lower()
    checks = {
        "m102_u2_raw_sha256_exact": runtime.sha256_bytes(predecessor) == M102_U2_RAW_SHA256,
        "m102_u2_state_digest_exact": m102_state["state_digest"] == M102_U2_STATE_DIGEST,
        "development_fixture_deterministic": fixture_exact,
        "development_fixture_marks_nonqualification": fixture.get("qualification") is False,
        "qualification_pool_deterministic": pool_exact,
        "predecessor_conservation_fixture_deterministic": conservation_exact,
        "qualification_pool_excludes_development_identities": not any(
            term in pool_text for term in ("north", "south", "amber", "violet", '"outcome"')
        ),
        "runtime_has_no_forbidden_import": not forbidden_imports,
        "runtime_has_no_pool_result_checker_path": not forbidden_source_terms,
        "producer_runtime_contains_no_accepted_feature_subset": "REQUIRED_FEATURES"
        not in runtime_source
        and not exact_winning_literals,
        "s_prime_contains_no_producer_or_consumer_identity": not leaked_identities,
        "s_prime_is_exact_required_generic_feature_set": set(s_prime["features"])
        == VALIDATED_S_PRIME_FEATURES,
        "s_prime_built_from_complete_feature_census": acquisition["assembled"]
        == sum(
            1
            for size in range(1, runtime.MAX_ACQUIRED_FEATURES + 1)
            for _features in __import__("itertools").combinations(runtime.FEATURE_TOKENS, size)
        ),
        "every_adopted_feature_is_operationally_necessary": set(feature_ablation_attempts)
        == set(s_prime["features"])
        and all(
            attempt["confirmed"] is False and attempt["reason"] == "no_candidate"
            for attempt in feature_ablation_attempts.values()
        ),
        "s0_failed_before_s_prime": acquisition["s0_attempt"]["confirmed"] is False,
        "s0_closure_budget_independent": acquisition["s0_closure"]["budget_independent"] is True,
        "m102_bytes_conserved_in_v1": v1["m102_ascii"].encode("ascii") == predecessor,
        "canonical_result_absent": not RESULT.exists(),
        "canonical_check_report_absent": not CHECK_REPORT.exists(),
    }
    report: dict[str, Any] = {
        "schema": "m103-boundary-audit-v1",
        "confirmed": all(checks.values()),
        "checks": checks,
        "imports": imports,
        "forbidden_imports": forbidden_imports,
        "forbidden_source_terms": forbidden_source_terms,
        "s_prime": s_prime,
        "leaked_identities": leaked_identities,
        "exact_winning_literals_in_runtime": exact_winning_literals,
        "feature_ablation_attempts": feature_ablation_attempts,
        "development_fixture_digest": fixture["fixture_digest"],
        "development_fixture_raw_sha256": runtime.sha256_bytes(FIXTURE.read_bytes()),
        "qualification_pool_digest": pool["pool_digest"],
        "qualification_pool_raw_sha256": runtime.sha256_bytes(POOL.read_bytes()),
        "predecessor_conservation_fixture_digest": conservation_fixture["fixture_digest"],
        "predecessor_conservation_fixture_raw_sha256": runtime.sha256_bytes(
            PREDECESSOR_CONSERVATION.read_bytes()
        ),
        "result_exists": RESULT.exists(),
        "check_report_exists": CHECK_REPORT.exists(),
    }
    report["report_digest"] = runtime.digest(report)
    return report


def main() -> int:
    report = audit()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["confirmed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
