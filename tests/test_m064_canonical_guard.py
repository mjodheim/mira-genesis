from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from metamorphosis.m064_real_substrate_completion import M064_PROTOCOL
from check_m064_canonical_guard import ARM_MESSAGE, ARM_SCHEMA, GuardError, inspect_arm
from run_m064_canonical import canonical_bytes
import reproduce_m064_canonical as reproduction_entrypoint


HEAD = "a" * 40
PARENT = "b" * 40


def _files(tmp_path: Path) -> tuple[Path, Path]:
    committed = tmp_path / "committed.py"
    committed.write_text("VALUE = 1\n", encoding="utf-8")
    frozen = tmp_path / "FROZEN_PROTOCOL.json"
    frozen.write_text(
        json.dumps(
            {
                "schema": "m064-frozen-protocol/1",
                "protocol": M064_PROTOCOL.to_dict(),
                "protocol_sha256": M064_PROTOCOL.digest(),
                "task_bank_commitment": M064_PROTOCOL.task_bank_commitment,
                "task_bank_entry_count": 4,
                "file_sha256": {
                    str(committed): hashlib.sha256(
                        committed.read_bytes().replace(b"\r\n", b"\n")
                    ).hexdigest()
                },
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    marker = tmp_path / "CANONICAL_ARMED.json"
    marker.write_text(
        json.dumps(
            {
                "schema": ARM_SCHEMA,
                "frozen_parent_sha": PARENT,
                "protocol_sha256": M064_PROTOCOL.digest(),
                "frozen_protocol_file_sha256": hashlib.sha256(frozen.read_bytes()).hexdigest(),
                "task_bank_commitment": M064_PROTOCOL.task_bank_commitment,
                "first_run_only": True,
                "reruns_are_reproductions_only": True,
                "independent_reproduction_required": True,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return marker, frozen


def test_non_marker_commit_keeps_canonical_block_closed(tmp_path: Path) -> None:
    marker, frozen = _files(tmp_path)
    assert inspect_arm(
        head_sha=HEAD,
        parent_sha=PARENT,
        commit_message="ordinary change",
        changed_files=("README.md",),
        marker_path=marker,
        frozen_protocol_path=frozen,
    ) is None


def test_exact_marker_only_commit_arms_once(tmp_path: Path) -> None:
    marker, frozen = _files(tmp_path)
    result = inspect_arm(
        head_sha=HEAD,
        parent_sha=PARENT,
        commit_message=ARM_MESSAGE,
        changed_files=(str(marker),),
        marker_path=marker,
        frozen_protocol_path=frozen,
    )
    assert result is not None
    assert result["frozen_parent_sha"] == PARENT
    assert result["independent_reproduction_required"] is True


def test_marker_shape_rejects_wrong_message_or_parent(tmp_path: Path) -> None:
    marker, frozen = _files(tmp_path)
    with pytest.raises(GuardError):
        inspect_arm(
            head_sha=HEAD,
            parent_sha=PARENT,
            commit_message="wrong",
            changed_files=(str(marker),),
            marker_path=marker,
            frozen_protocol_path=frozen,
        )
    data = json.loads(marker.read_text(encoding="utf-8"))
    data["frozen_parent_sha"] = "c" * 40
    marker.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(GuardError):
        inspect_arm(
            head_sha=HEAD,
            parent_sha=PARENT,
            commit_message=ARM_MESSAGE,
            changed_files=(str(marker),),
            marker_path=marker,
            frozen_protocol_path=frozen,
        )


def test_marker_binds_exact_frozen_protocol_bytes(tmp_path: Path) -> None:
    marker, frozen = _files(tmp_path)
    frozen.write_text('{"schema":"tampered"}\n', encoding="utf-8")
    with pytest.raises(GuardError, match="does not bind"):
        inspect_arm(
            head_sha=HEAD,
            parent_sha=PARENT,
            commit_message=ARM_MESSAGE,
            changed_files=(str(marker),),
            marker_path=marker,
            frozen_protocol_path=frozen,
        )


def test_marker_rejects_protocol_or_bank_drift(tmp_path: Path) -> None:
    marker, frozen = _files(tmp_path)
    data = json.loads(marker.read_text(encoding="utf-8"))
    data["protocol_sha256"] = "0" * 64
    marker.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(GuardError, match="protocol digest"):
        inspect_arm(
            head_sha=HEAD,
            parent_sha=PARENT,
            commit_message=ARM_MESSAGE,
            changed_files=(str(marker),),
            marker_path=marker,
            frozen_protocol_path=frozen,
        )


def test_canonical_json_bytes_are_stable() -> None:
    left = canonical_bytes({"b": 2, "a": 1})
    right = canonical_bytes({"a": 1, "b": 2})
    assert left == right == b'{\n  "a": 1,\n  "b": 2\n}\n'


def test_independent_reproduction_entrypoint_is_live() -> None:
    assert callable(reproduction_entrypoint.main)
