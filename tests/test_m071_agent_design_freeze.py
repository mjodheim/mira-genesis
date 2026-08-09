from __future__ import annotations

import json
from pathlib import Path

import pytest

import check_m071_agent_design_freeze as freeze


def test_exact_m071_agent_and_bridge_commits_are_immutable() -> None:
    result = freeze.verify_freeze()
    assert result == {
        "status": "agent_and_bridge_frozen_before_external_task_selection",
        "exact_agent_design_commit": "0820ebc3a638e8ae0e06fceed7addbdb71bafbb7",
        "exact_harbor_bridge_commit": "132476a5db532812a0cd223d02f8eba9ad88e346",
        "design_commitment_sha256": (
            "2e76a1b8b390bee0ee55095a6f3f61366176e7a4ac0791add9d6d37fca5c30a2"
        ),
        "frozen_blob_count": 17,
    }


def test_m071_design_freeze_rejects_commitment_tampering(tmp_path: Path) -> None:
    value = json.loads(freeze.DEFAULT_FREEZE.read_text(encoding="utf-8"))
    value["design_commitment_sha256"] = "0" * 64
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="commitment mismatch"):
        freeze.verify_freeze(path)


def test_m071_freeze_contains_no_selected_target_or_result() -> None:
    value = json.loads(freeze.DEFAULT_FREEZE.read_text(encoding="utf-8"))
    assert value["benchmark_revision_pinned"] is False
    assert value["benchmark_task_identifier_selected"] is False
    assert value["benchmark_task_content_inspected"] is False
    assert value["benchmark_task_executed"] is False
    assert value["scientific_result_exists"] is False
