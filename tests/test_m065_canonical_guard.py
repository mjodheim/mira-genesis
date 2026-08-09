from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from metamorphosis.m065_qualified_completion import M065_PROTOCOL, M065_PROTOCOL_SHA256
from check_m065_canonical_guard import ARM_MESSAGE, GuardError, inspect_arm
from check_m065_frozen_protocol import FrozenProtocolError, validate_frozen_protocol
from reproduce_m065_canonical import main as reproduce_main


HEAD = "a" * 40
PARENT = "b" * 40


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    committed = tmp_path / "generator.py"
    committed.write_text("VALUE = 1\n", encoding="utf-8")
    frozen = tmp_path / "FROZEN_PROTOCOL.json"
    frozen.write_text(
        json.dumps(
            {
                "schema": "m065-frozen-protocol/1",
                "protocol": M065_PROTOCOL,
                "protocol_sha256": M065_PROTOCOL_SHA256,
                "task_bank_commitment": M065_PROTOCOL["task_bank_commitment"],
                "task_bank_entry_count": 4,
                "file_sha256": {
                    str(committed): hashlib.sha256(
                        committed.read_bytes().replace(b"\r\n", b"\n")
                    ).hexdigest()
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    marker = tmp_path / "CANONICAL_ARMED.json"
    marker.write_text(
        json.dumps(
            {
                "schema": "m065-canonical-arm/1",
                "frozen_parent_sha": PARENT,
                "protocol_sha256": M065_PROTOCOL_SHA256,
                "frozen_protocol_file_sha256": hashlib.sha256(
                    frozen.read_bytes().replace(b"\r\n", b"\n")
                ).hexdigest(),
                "task_bank_commitment": M065_PROTOCOL["task_bank_commitment"],
                "first_run_only": True,
                "reruns_are_reproductions_only": True,
                "independent_reproduction_required": True,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return marker, frozen


def _inspect(marker: Path, frozen: Path, *, history: int = 1):
    return inspect_arm(
        head_sha=HEAD,
        parent_sha=PARENT,
        commit_message=ARM_MESSAGE,
        changed_files=(str(marker),),
        marker_history_count=history,
        marker_path=marker,
        frozen_protocol_path=frozen,
    )


def test_first_history_marker_only_commit_arms(tmp_path: Path) -> None:
    marker, frozen = _fixture(tmp_path)
    assert _inspect(marker, frozen)["frozen_parent_sha"] == PARENT


def test_updated_deleted_or_readded_marker_is_rejected(tmp_path: Path) -> None:
    marker, frozen = _fixture(tmp_path)
    with pytest.raises(GuardError, match="first and only"):
        _inspect(marker, frozen, history=2)


def test_wrong_parent_is_rejected(tmp_path: Path) -> None:
    marker, frozen = _fixture(tmp_path)
    data = json.loads(marker.read_text(encoding="utf-8"))
    data["frozen_parent_sha"] = "c" * 40
    marker.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(GuardError, match="actual immutable parent"):
        _inspect(marker, frozen)


def test_frozen_protocol_drift_is_rejected(tmp_path: Path) -> None:
    marker, frozen = _fixture(tmp_path)
    frozen.write_text('{"schema":"tampered"}\n', encoding="utf-8")
    data = json.loads(marker.read_text(encoding="utf-8"))
    data["frozen_protocol_file_sha256"] = hashlib.sha256(
        frozen.read_bytes().replace(b"\r\n", b"\n")
    ).hexdigest()
    marker.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(GuardError, match="failed verification"):
        _inspect(marker, frozen)


def test_repository_frozen_protocol_matches_all_committed_sources() -> None:
    value = validate_frozen_protocol()
    assert value["protocol_sha256"] == M065_PROTOCOL_SHA256


def test_portable_hash_rejects_real_source_drift(tmp_path: Path) -> None:
    _marker, frozen = _fixture(tmp_path)
    data = json.loads(frozen.read_text(encoding="utf-8"))
    source = Path(next(iter(data["file_sha256"])))
    source.write_text("VALUE = 2\n", encoding="utf-8")
    with pytest.raises(FrozenProtocolError, match="source drifted"):
        validate_frozen_protocol(frozen)


def test_workflow_never_recreates_first_result_on_rerun() -> None:
    source = Path(".github/workflows/m065-canonical.yml").read_text(encoding="utf-8")
    assert "github.run_attempt == 1" in source
    assert "marker-history-count" in source
    assert "fetch-depth: 0" in source


def test_reproduction_entrypoint_is_importable() -> None:
    assert callable(reproduce_main)
