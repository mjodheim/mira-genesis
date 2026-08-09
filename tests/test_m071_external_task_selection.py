from __future__ import annotations

import json
from pathlib import Path
import subprocess

import select_m071_external_tasks as selection


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ("git", *args), cwd=repo, capture_output=True, text=True, check=True,
    )
    return completed.stdout.strip()


def test_selector_excludes_m070_pair_and_is_deterministic(tmp_path: Path) -> None:
    repo = tmp_path / "benchmark"
    repo.mkdir()
    _git(repo, "init", "--quiet")
    for identifier in (
        "fresh-alpha", "rstan-to-pystan", "fresh-beta",
        "llm-inference-batching-scheduler", "fresh-gamma",
    ):
        task = repo / "tasks" / identifier / "task.toml"
        task.parent.mkdir(parents=True)
        task.write_text("version = '1'\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(
        repo, "-c", "user.name=Mira test", "-c", "user.email=mira@example.invalid",
        "commit", "--quiet", "-m", "fixture",
    )
    commit = _git(repo, "rev-parse", "HEAD")
    protocol = json.loads(selection.PROTOCOL.read_text(encoding="utf-8"))
    protocol["benchmark_revision"] = commit
    protocol["selection_salt_hex"] = "00" * 32
    protocol_path = tmp_path / "protocol.json"
    protocol_path.write_text(json.dumps(protocol), encoding="utf-8")

    first = selection.select(repo, protocol_path)
    second = selection.select(repo, protocol_path)
    assert first == second
    assert first["all_identifier_count"] == 5
    assert first["eligible_inventory_count"] == 3
    assert first["excluded_identifiers"] == [
        "llm-inference-batching-scheduler", "rstan-to-pystan",
    ]
    selected = [record[1] for record in first["selected"]]
    assert len(selected) == 2
    assert not set(selected) & set(first["excluded_identifiers"])
    assert first["fresh_task_content_inspected_before_selection"] is False
    assert first["scientific_result_exists"] is False


def test_real_protocol_contains_no_selection_or_result() -> None:
    protocol = json.loads(selection.PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["agent_design_freeze_commit"] == (
        "de85e31b95520d0ff90e451d192d106cf56589a8"
    )
    assert protocol["eligible_identifier_inventory_enumerated"] is False
    assert protocol["fresh_task_identifier_selected"] is False
    assert protocol["fresh_task_content_inspected"] is False
    assert protocol["fresh_task_executed"] is False
    assert protocol["selected_identifiers"] == []
    assert protocol["replacement_permitted"] is False
    assert protocol["excluded_identifiers"] == [
        "llm-inference-batching-scheduler", "rstan-to-pystan",
    ]


def test_committed_selection_binds_fresh_pair_without_task_content() -> None:
    artifact = json.loads(
        (selection.ROOT / "experiments" / "M071" / "TASK_SELECTION.json").read_text(
            encoding="utf-8"
        )
    )
    assert artifact["selection_protocol_commit"] == (
        "fa5d8962bce1659831f98938a194a226883d347c"
    )
    assert artifact["inventory_sha256"] == (
        "c21c3e62adfc08a80e33aa6506efa6e6bbd40e81a88c5a1bbb91603849d251c9"
    )
    assert [record[1] for record in artifact["selected"]] == [
        "sqlite-with-gcov", "custom-memory-heap-crash",
    ]
    protocol = json.loads(selection.PROTOCOL.read_text(encoding="utf-8"))
    salt = bytes.fromhex(protocol["selection_salt_hex"])
    for digest, identifier in artifact["selected"]:
        assert __import__("hashlib").sha256(
            salt + identifier.encode("utf-8")
        ).hexdigest() == digest
    assert not {
        record[1] for record in artifact["selected"]
    } & set(artifact["excluded_identifiers"])
    assert artifact["fresh_task_content_inspected_before_selection"] is False
    assert artifact["fresh_task_executed"] is False
    assert artifact["scientific_result_exists"] is False
