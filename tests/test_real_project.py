from __future__ import annotations

import json
from pathlib import Path
import sys
import time

import pytest

from genesis import real_project


def _write_host(root: Path) -> None:
    (root / "src").mkdir(parents=True)
    (root / "src" / "base.txt").write_text("baseline\n", encoding="utf-8")
    (root / "src" / "feature.txt").write_text("disabled\n", encoding="utf-8")
    (root / ".env").write_text("SECRET=not-for-candidates\n", encoding="utf-8")


def _manifest(root: Path) -> dict:
    _, tree_digest = real_project.tree_inventory(root, ignored_directory_names=[".git", "bin", "obj"])
    base_digest = real_project._sha256_file(root / "src" / "base.txt")
    feature_digest = real_project._sha256_file(root / "src" / "feature.txt")
    mandatory = (
        "from pathlib import Path; import sys; "
        "r=Path(sys.argv[1]); "
        "sys.exit(0 if (r/'src/base.txt').read_text() == 'baseline\\n' else 7)"
    )
    objective = (
        "from pathlib import Path; import sys; "
        "r=Path(sys.argv[1]); v=(r/'src/feature.txt').read_text(); "
        "(r/'src/runtime-side-effect.txt').write_text('bad\\n') if v == 'side-effect\\n' else None; "
        "sys.exit(0 if v in {'enabled\\n','side-effect\\n'} else 9)"
    )
    return {
        "schema": real_project.MANIFEST_SCHEMA,
        "host_name": "real-project-gate-test-host",
        "expected_host_tree_digest": tree_digest,
        "host_identity": {"kind": "test-tree", "value": tree_digest},
        "genesis_identity": {"kind": "test", "value": "current"},
        "writable_prefixes": ["src"],
        "forbidden_prefixes": [".env"],
        "authority_paths": ["src/evaluator.py"],
        "ignored_directory_names": [".git", "bin", "obj"],
        "ignored_globs": [],
        "evaluation_budget_seconds": 300,
        "inherit_environment_keys": ["PATH", "HOME"],
        "environment": {},
        "evaluation_commands": [
            {
                "name": "mandatory-regression",
                "role": "mandatory",
                "argv": [sys.executable, "-c", mandatory, "{workspace}"],
                "timeout_seconds": 10,
            },
            {
                "name": "new-capability-contract",
                "role": "objective",
                "argv": [sys.executable, "-c", objective, "{workspace}"],
                "timeout_seconds": 10,
            },
        ],
        "candidates": [
            {
                "id": "outside-boundary",
                "mutations": [
                    {
                        "path": ".env",
                        "expected_sha256": real_project._sha256_file(root / ".env"),
                        "content_utf8": "SECRET=changed\n",
                    }
                ],
            },
            {
                "id": "break-regression",
                "mutations": [
                    {
                        "path": "src/base.txt",
                        "expected_sha256": base_digest,
                        "content_utf8": "broken\n",
                    },
                    {
                        "path": "src/feature.txt",
                        "expected_sha256": feature_digest,
                        "content_utf8": "enabled\n",
                    },
                ],
            },
            {
                "id": "runtime-side-effect",
                "mutations": [
                    {
                        "path": "src/feature.txt",
                        "expected_sha256": feature_digest,
                        "content_utf8": "side-effect\n",
                    }
                ],
            },
            {
                "id": "measured-winner",
                "mutations": [
                    {
                        "path": "src/feature.txt",
                        "expected_sha256": feature_digest,
                        "content_utf8": "enabled\n",
                    }
                ],
            },
        ],
    }


def test_gate_measures_complete_image_rejects_bad_arms_and_replays_winner(tmp_path: Path) -> None:
    host = tmp_path / "host"
    host.mkdir()
    _write_host(host)
    manifest = _manifest(host)
    original_env = (host / ".env").read_bytes()
    original_base = (host / "src" / "base.txt").read_bytes()
    original_feature = (host / "src" / "feature.txt").read_bytes()

    output = tmp_path / "out"
    report = real_project.run_gate(host, manifest, output_directory=output)

    assert report["passed"] is True
    assert report["selected_candidate_id"] == "measured-winner"
    assert len(report["candidates"]) == 4
    assert report["checks"] and all(report["checks"].values())
    assert report["winner_replay"]["semantic_matches"] is True
    assert report["baseline_objective_pass_count"] == 0

    by_id = {item["id"]: item for item in report["candidates"]}
    assert by_id["outside-boundary"]["construction_refused"] is True
    assert "writable prefix" in by_id["outside-boundary"]["construction_reason"]
    assert by_id["break-regression"]["mandatory_pass"] is False
    assert by_id["runtime-side-effect"]["objective_pass_count"] == 1
    assert by_id["runtime-side-effect"]["tracked_source_stable"] is False
    assert by_id["measured-winner"]["mandatory_pass"] is True
    assert by_id["measured-winner"]["objective_pass_count"] == 1
    assert by_id["measured-winner"]["tracked_source_stable"] is True
    assert by_id["measured-winner"]["accepted"] is True

    assert (host / ".env").read_bytes() == original_env
    assert (host / "src" / "base.txt").read_bytes() == original_base
    assert (host / "src" / "feature.txt").read_bytes() == original_feature
    assert not (host / "src" / "runtime-side-effect.txt").exists()

    persisted = json.loads((output / "report.json").read_text(encoding="utf-8"))
    assert persisted["report_digest"] == report["report_digest"]
    patch = (output / "winner.patch").read_text(encoding="utf-8")
    assert "src/feature.txt" in patch
    assert "+enabled" in patch


def test_report_preserves_detailed_command_evidence(tmp_path: Path) -> None:
    host = tmp_path / "host"
    host.mkdir()
    _write_host(host)
    report = real_project.run_gate(host, _manifest(host))

    command = report["baseline"]["commands"][0]
    assert command["name"] == "mandatory-regression"
    assert isinstance(command["elapsed_ms"], int)
    assert len(command["stdout_sha256"]) == 64
    assert len(command["stderr_sha256"]) == 64
    assert isinstance(command["stdout_length"], int)
    assert isinstance(command["stderr_length"], int)
    assert "argv" in command
    assert "cwd" in command

    winner = next(item for item in report["candidates"] if item["id"] == "measured-winner")
    assert "elapsed_ms" in winner["evaluation"]["commands"][0]


def test_tree_inventory_refuses_nonignored_symlink(tmp_path: Path) -> None:
    host = tmp_path / "host"
    host.mkdir()
    _write_host(host)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    link = host / "src" / "external-link.txt"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available on this platform")

    with pytest.raises(real_project.RealProjectError, match="symbolic link"):
        real_project.tree_inventory(host, ignored_directory_names=[".git", "bin", "obj"])


def test_gate_refuses_wrong_bound_host_snapshot(tmp_path: Path) -> None:
    host = tmp_path / "host"
    host.mkdir()
    _write_host(host)
    manifest = _manifest(host)
    manifest["expected_host_tree_digest"] = "0" * 64

    with pytest.raises(real_project.RealProjectError, match="host snapshot identity mismatch"):
        real_project.run_gate(host, manifest)


def test_manifest_requires_argv_not_shell_string(tmp_path: Path) -> None:
    host = tmp_path / "host"
    host.mkdir()
    _write_host(host)
    manifest = _manifest(host)
    manifest["evaluation_commands"][0]["argv"] = "python -c pass"

    with pytest.raises(real_project.RealProjectError, match="argv array"):
        real_project.validate_manifest(manifest)


def test_manifest_requires_explicit_forbidden_prefixes(tmp_path: Path) -> None:
    host = tmp_path / "host"
    host.mkdir()
    _write_host(host)
    manifest = _manifest(host)
    manifest["forbidden_prefixes"] = []

    with pytest.raises(real_project.RealProjectError, match="forbidden_prefix"):
        real_project.validate_manifest(manifest)


def test_manifest_refuses_writable_prefix_under_excluded_prefix(tmp_path: Path) -> None:
    host = tmp_path / "host"
    host.mkdir()
    _write_host(host)
    manifest = _manifest(host)
    manifest["writable_prefixes"] = ["src", "src/evaluator.py"]

    with pytest.raises(real_project.RealProjectError, match="lies at or under excluded prefix"):
        real_project.validate_manifest(manifest)

    nested = _manifest(host)
    nested["writable_prefixes"] = ["src"]
    nested["forbidden_prefixes"] = [".env", "src"]
    with pytest.raises(real_project.RealProjectError, match="lies at or under excluded prefix"):
        real_project.validate_manifest(nested)


def test_manifest_requires_bound_run_identities(tmp_path: Path) -> None:
    host = tmp_path / "host"
    host.mkdir()
    _write_host(host)

    missing = _manifest(host)
    missing["genesis_identity"] = {}
    with pytest.raises(real_project.RealProjectError, match="non-empty genesis_identity"):
        real_project.validate_manifest(missing)

    partial = _manifest(host)
    partial["host_identity"] = {"kind": "test-tree"}
    with pytest.raises(real_project.RealProjectError, match="host_identity requires a non-empty 'value'"):
        real_project.validate_manifest(partial)


def test_manifest_requires_budget_admitting_one_evaluation_pass(tmp_path: Path) -> None:
    host = tmp_path / "host"
    host.mkdir()
    _write_host(host)

    absent = _manifest(host)
    del absent["evaluation_budget_seconds"]
    with pytest.raises(real_project.RealProjectError, match="evaluation_budget_seconds in"):
        real_project.validate_manifest(absent)

    too_small = _manifest(host)
    too_small["evaluation_budget_seconds"] = 5
    with pytest.raises(real_project.RealProjectError, match="one complete evaluation pass"):
        real_project.validate_manifest(too_small)


def test_budget_refuses_a_command_it_cannot_run_to_its_declared_timeout() -> None:
    budget = real_project._Budget(total_seconds=10, started=time.monotonic() - 9.5)

    budget.require("cheap command", 0.1)
    with pytest.raises(real_project.RealProjectError, match="cannot admit") as caught:
        budget.require("expensive command", 5.0)
    assert caught.value.kind == "budget"


def test_gate_fails_closed_when_the_overall_budget_cannot_cover_a_command(tmp_path: Path) -> None:
    host = tmp_path / "host"
    host.mkdir()
    _write_host(host)
    manifest = _manifest(host)
    slow = "import time; time.sleep(1.2)"
    manifest["evaluation_commands"] = [
        {
            "name": "slow-mandatory",
            "role": "mandatory",
            "argv": [sys.executable, "-c", slow],
            "timeout_seconds": 2,
        },
        {
            "name": "cheap-objective",
            "role": "objective",
            "argv": [sys.executable, "-c", "pass"],
            "timeout_seconds": 1,
        },
    ]
    manifest["evaluation_budget_seconds"] = 3

    with pytest.raises(real_project.RealProjectError, match="evaluation budget") as caught:
        real_project.run_gate(host, manifest)
    assert caught.value.kind == "budget"
    assert (host / "src" / "feature.txt").read_text(encoding="utf-8") == "disabled\n"


def test_gate_refuses_to_pass_without_the_required_safety_invariant_arms(tmp_path: Path) -> None:
    host = tmp_path / "host"
    host.mkdir()
    _write_host(host)
    manifest = _manifest(host)
    manifest["candidates"] = [
        item for item in manifest["candidates"] if item["id"] == "measured-winner"
    ]

    report = real_project.run_gate(host, manifest)

    assert report["selected_candidate_id"] == "measured-winner"
    assert report["checks"]["unique_strict_improving_winner"] is True
    assert report["checks"]["winner_replays_semantically"] is True
    assert report["checks"]["boundary_violating_arm_refused"] is False
    assert report["checks"]["host_check_failing_arm_rejected"] is False
    assert report["passed"] is False


def test_gate_reports_safety_invariant_and_disjointness_evidence(tmp_path: Path) -> None:
    host = tmp_path / "host"
    host.mkdir()
    _write_host(host)
    report = real_project.run_gate(host, _manifest(host))

    assert report["safety_invariant_evidence"]["boundary_refused_candidate_ids"] == ["outside-boundary"]
    assert sorted(report["safety_invariant_evidence"]["host_check_rejected_candidate_ids"]) == [
        "break-regression",
        "runtime-side-effect",
    ]
    assert report["selected_candidate_paths"] == ["src/feature.txt"]
    assert report["checks"]["winner_diff_disjoint_from_authority"] is True
    assert report["evaluation_budget_seconds"] == 300
    assert isinstance(report["evaluation_elapsed_ms"], int)

    refused = next(item for item in report["candidates"] if item["id"] == "outside-boundary")
    assert refused["construction_refusal_kind"] == "path_policy"
