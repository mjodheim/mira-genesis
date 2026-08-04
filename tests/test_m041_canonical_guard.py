from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.check_m041_canonical_guard import (
    ARM_MESSAGE,
    GuardError,
    inspect_arm,
)

HEAD = "1" * 40
PARENT = "2" * 40
PROTOCOL = "3" * 64


def marker(path: Path, **changes) -> Path:
    value = {
        "schema": "m041-canonical-arm/1",
        "frozen_parent_sha": PARENT,
        "protocol_sha256": PROTOCOL,
        "first_run_only": True,
        "reruns_are_reproductions_only": True,
    }
    value.update(changes)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_exact_marker_only_commit_arms(tmp_path):
    path = marker(tmp_path / "CANONICAL_ARMED.json")

    value = inspect_arm(
        head_sha=HEAD,
        parent_sha=PARENT,
        commit_message=ARM_MESSAGE,
        changed_files=(str(path),),
        marker_path=path,
    )

    assert value is not None
    assert value["protocol_sha256"] == PROTOCOL


def test_ordinary_commit_keeps_the_block_closed(tmp_path):
    path = marker(tmp_path / "CANONICAL_ARMED.json")

    assert inspect_arm(
        head_sha=HEAD,
        parent_sha=PARENT,
        commit_message="docs: ordinary work",
        changed_files=("README.md",),
        marker_path=path,
    ) is None


def test_marker_plus_another_file_cannot_arm(tmp_path):
    path = marker(tmp_path / "CANONICAL_ARMED.json")

    assert inspect_arm(
        head_sha=HEAD,
        parent_sha=PARENT,
        commit_message=ARM_MESSAGE,
        changed_files=(str(path), "README.md"),
        marker_path=path,
    ) is None


@pytest.mark.parametrize(
    "changes,parent,message",
    [
        ({"schema": "wrong"}, PARENT, ARM_MESSAGE),
        ({"frozen_parent_sha": "4" * 40}, PARENT, ARM_MESSAGE),
        ({"protocol_sha256": "x" * 64}, PARENT, ARM_MESSAGE),
        ({"first_run_only": False}, PARENT, ARM_MESSAGE),
        ({"reruns_are_reproductions_only": False}, PARENT, ARM_MESSAGE),
        ({"extra": True}, PARENT, ARM_MESSAGE),
        ({}, "4" * 40, ARM_MESSAGE),
        ({}, PARENT, "wrong message"),
    ],
)
def test_malformed_marker_only_claim_fails(tmp_path, changes, parent, message):
    path = marker(tmp_path / "CANONICAL_ARMED.json", **changes)

    with pytest.raises(GuardError):
        inspect_arm(
            head_sha=HEAD,
            parent_sha=parent,
            commit_message=message,
            changed_files=(str(path),),
            marker_path=path,
        )
