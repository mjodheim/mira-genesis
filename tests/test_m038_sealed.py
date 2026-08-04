from __future__ import annotations

import json
from pathlib import Path

import pytest

from check_m038_canonical_guard import (
    ARM_MESSAGE,
    ARM_PATH,
    GuardError,
    inspect_arm,
)
from metamorphosis.m038_sealed import head_nonce, sealed_spec


HEAD_A = "a" * 40
HEAD_B = "b" * 40
PARENT = "c" * 40
PROTOCOL = "d" * 64


def marker_payload(parent: str = PARENT, protocol: str = PROTOCOL):
    return {
        "schema": "m038-canonical-arm/1",
        "frozen_parent_sha": parent,
        "protocol_sha256": protocol,
        "first_run_only": True,
        "reruns_are_reproductions_only": True,
    }


def write_marker(tmp_path: Path, payload=None) -> Path:
    path = tmp_path / "experiments" / "M038" / "CANONICAL_ARMED.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(payload or marker_payload()), encoding="utf-8")
    return path


def test_the_sealed_spec_is_deterministic_from_head_parent_and_protocol():
    first = sealed_spec(HEAD_A, frozen_parent_sha=PARENT, protocol_sha256=PROTOCOL)
    second = sealed_spec(HEAD_A, frozen_parent_sha=PARENT, protocol_sha256=PROTOCOL)

    assert first == second
    assert first.task_seed == second.task_seed
    assert first.digest() == second.digest()
    assert first.master_nonce == head_nonce(HEAD_A, PROTOCOL)


def test_a_different_arming_head_reveals_a_different_task_seed():
    first = sealed_spec(HEAD_A, frozen_parent_sha=PARENT, protocol_sha256=PROTOCOL)
    second = sealed_spec(HEAD_B, frozen_parent_sha=PARENT, protocol_sha256=PROTOCOL)

    assert first.master_nonce != second.master_nonce
    assert first.task_seed != second.task_seed
    assert first.digest() != second.digest()


def test_the_seed_cannot_be_derived_from_an_abbreviated_or_malformed_head():
    for head in ("a" * 39, "A" * 40, "not-a-sha", ""):
        with pytest.raises(ValueError, match="40-character lowercase"):
            sealed_spec(head, frozen_parent_sha=PARENT, protocol_sha256=PROTOCOL)


def test_the_protocol_digest_is_part_of_the_nonce():
    other_protocol = "e" * 64
    assert head_nonce(HEAD_A, PROTOCOL) != head_nonce(HEAD_A, other_protocol)


def test_the_arming_head_must_be_a_child_not_the_frozen_parent():
    with pytest.raises(ValueError, match="child"):
        sealed_spec(PARENT, frozen_parent_sha=PARENT, protocol_sha256=PROTOCOL)


def test_an_ordinary_commit_does_not_open_the_block(tmp_path, monkeypatch):
    marker = write_marker(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = inspect_arm(
        head_sha=HEAD_A,
        parent_sha=PARENT,
        commit_message="docs: record a result",
        changed_files=("results/M038.md",),
        marker_path=marker.relative_to(tmp_path),
    )

    assert result is None


def test_the_exact_marker_only_commit_is_accepted(tmp_path, monkeypatch):
    marker = write_marker(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = inspect_arm(
        head_sha=HEAD_A,
        parent_sha=PARENT,
        commit_message=ARM_MESSAGE,
        changed_files=(str(marker.relative_to(tmp_path)).replace("\\", "/"),),
        marker_path=marker.relative_to(tmp_path),
    )

    assert result == marker_payload()


def test_a_marker_only_commit_with_the_wrong_message_fails_loudly(tmp_path, monkeypatch):
    marker = write_marker(tmp_path)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(GuardError, match="exact arming message"):
        inspect_arm(
            head_sha=HEAD_A,
            parent_sha=PARENT,
            commit_message="almost canonical",
            changed_files=(str(marker.relative_to(tmp_path)).replace("\\", "/"),),
            marker_path=marker.relative_to(tmp_path),
        )


def test_the_marker_must_name_the_actual_parent(tmp_path, monkeypatch):
    marker = write_marker(tmp_path, marker_payload(parent=HEAD_B))
    monkeypatch.chdir(tmp_path)

    with pytest.raises(GuardError, match="actual parent"):
        inspect_arm(
            head_sha=HEAD_A,
            parent_sha=PARENT,
            commit_message=ARM_MESSAGE,
            changed_files=(str(marker.relative_to(tmp_path)).replace("\\", "/"),),
            marker_path=marker.relative_to(tmp_path),
        )


def test_the_marker_schema_is_closed(tmp_path, monkeypatch):
    payload = marker_payload()
    payload["extra"] = True
    marker = write_marker(tmp_path, payload)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(GuardError, match="closed schema"):
        inspect_arm(
            head_sha=HEAD_A,
            parent_sha=PARENT,
            commit_message=ARM_MESSAGE,
            changed_files=(str(marker.relative_to(tmp_path)).replace("\\", "/"),),
            marker_path=marker.relative_to(tmp_path),
        )


def test_the_consumed_canonical_marker_pins_the_first_run_identities():
    data = json.loads(ARM_PATH.read_text(encoding="utf-8"))

    assert data == {
        "schema": "m038-canonical-arm/1",
        "frozen_parent_sha": "aaf86bb63d6e2d27e9965f5dcc5871c0cd79fd69",
        "protocol_sha256": "f717740c24d5028dd660c066477e8690c9a7559f43e03cb57c4b875c1f3ee326",
        "first_run_only": True,
        "reruns_are_reproductions_only": True,
    }
