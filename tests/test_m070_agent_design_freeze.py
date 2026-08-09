from __future__ import annotations

import json
from pathlib import Path

import pytest

import check_m070_agent_design_freeze as freeze


def test_exact_m070_agent_design_commit_and_blobs_are_immutable() -> None:
    result = freeze.verify_freeze()
    assert result == {
        "status": "agent_design_frozen_before_external_task_selection",
        "exact_agent_design_commit": "41ebe791605f55e7a44df8f0939d730139cf219a",
        "design_commitment_sha256": (
            "14f6c17ea9c88a4e967b317e167e45d76f4700f5a5d91c4f017edb0add179a46"
        ),
        "frozen_blob_count": 9,
    }


def test_m070_design_freeze_rejects_commitment_tampering(tmp_path: Path) -> None:
    value = json.loads(freeze.DEFAULT_FREEZE.read_text(encoding="utf-8"))
    value["design_commitment_sha256"] = "0" * 64
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="commitment mismatch"):
        freeze.verify_freeze(path)


def test_m070_design_freeze_contains_no_selected_target_or_result() -> None:
    value = json.loads(freeze.DEFAULT_FREEZE.read_text(encoding="utf-8"))
    assert value["benchmark_revision_pinned"] is False
    assert value["benchmark_task_identifier_selected"] is False
    assert value["benchmark_task_content_inspected"] is False
    assert value["benchmark_task_executed"] is False
    assert value["scientific_result_exists"] is False
