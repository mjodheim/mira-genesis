from __future__ import annotations

import json
from pathlib import Path

import pytest

from check_m040_canonical_guard import ARM_MESSAGE, GuardError, inspect_arm
from metamorphosis.m040_sealed import head_nonce, sealed_spec

HEAD_A = "a" * 40
HEAD_B = "b" * 40
PARENT = "c" * 40
PROTOCOL = "d" * 64


def marker_payload(parent: str = PARENT, protocol: str = PROTOCOL):
    return {
        "schema": "m040-canonical-arm/1",
        "frozen_parent_sha": parent,
        "protocol_sha256": protocol,
        "first_run_only": True,
        "reruns_are_reproductions_only": True,
    }


def write_marker(tmp_path: Path, payload=None) -> Path:
    path = tmp_path / "experiments" / "M040" / "CANONICAL_ARMED.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(payload or marker_payload()), encoding="utf-8")
    return path


def test_sealed_spec_is_deterministic_and_bound_to_head_parent_and_protocol():
    first = sealed_spec(HEAD_A, frozen_parent_sha=PARENT, protocol_sha256=PROTOCOL)
    second = sealed_spec(HEAD_A, frozen_parent_sha=PARENT, protocol_sha256=PROTOCOL)
    assert first == second
    assert first.master_nonce == head_nonce(HEAD_A, PROTOCOL)
    assert first.digest() == second.digest()


def test_different_arming_head_or_protocol_reveals_a_different_task():
    first = sealed_spec(HEAD_A, frozen_parent_sha=PARENT, protocol_sha256=PROTOCOL)
    other_head = sealed_spec(HEAD_B, frozen_parent_sha=PARENT, protocol_sha256=PROTOCOL)
    other_protocol = sealed_spec(
        HEAD_A,
        frozen_parent_sha=PARENT,
        protocol_sha256="e" * 64,
    )
    assert first.task_seed != other_head.task_seed
    assert first.task_seed != other_protocol.task_seed
    assert first.digest() != other_head.digest()
    assert first.digest() != other_protocol.digest()


def test_noncanonical_or_abbreviated_identifiers_are_rejected():
    for head in ("a" * 39, "A" * 40, "not-a-sha", ""):
        with pytest.raises(ValueError, match="40-character lowercase"):
            sealed_spec(head, frozen_parent_sha=PARENT, protocol_sha256=PROTOCOL)
    with pytest.raises(ValueError, match="64 lowercase"):
        sealed_spec(HEAD_A, frozen_parent_sha=PARENT, protocol_sha256="D" * 64)


def test_arming_head_must_be_a_child_not_the_parent():
    with pytest.raises(ValueError, match="child"):
        sealed_spec(PARENT, frozen_parent_sha=PARENT, protocol_sha256=PROTOCOL)


def test_ordinary_commit_never_opens_the_block(tmp_path, monkeypatch):
    marker = write_marker(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert inspect_arm(
        head_sha=HEAD_A,
        parent_sha=PARENT,
        commit_message="docs: record result",
        changed_files=("results/M040.md",),
        marker_path=marker.relative_to(tmp_path),
    ) is None


def test_exact_marker_only_commit_is_accepted(tmp_path, monkeypatch):
    marker = write_marker(tmp_path)
    monkeypatch.chdir(tmp_path)
    relative = str(marker.relative_to(tmp_path))
    assert inspect_arm(
        head_sha=HEAD_A,
        parent_sha=PARENT,
        commit_message=ARM_MESSAGE,
        changed_files=(relative,),
        marker_path=marker.relative_to(tmp_path),
    ) == marker_payload()


def test_the_marker_comparison_does_not_depend_on_the_host_separator(tmp_path, monkeypatch):
    """Both sides of the comparison are normalised, not only the marker path.

    Git emits forward slashes everywhere, but a caller holding a host path does not. While
    only one side was normalised, the tests in this file supplied an already-normalised
    path and so compensated for the defect instead of exposing it.
    """
    marker = write_marker(tmp_path)
    monkeypatch.chdir(tmp_path)
    relative = str(marker.relative_to(tmp_path))

    for spelling in (relative, relative.replace("/", "\\"), relative.replace("\\", "/")):
        assert inspect_arm(
            head_sha=HEAD_A,
            parent_sha=PARENT,
            commit_message=ARM_MESSAGE,
            changed_files=(spelling,),
            marker_path=marker.relative_to(tmp_path),
        ) == marker_payload(), spelling


def test_normalisation_does_not_widen_what_can_arm(tmp_path, monkeypatch):
    """Rewriting separators must not let a different file stand in for the marker."""
    marker = write_marker(tmp_path)
    monkeypatch.chdir(tmp_path)
    relative = str(marker.relative_to(tmp_path))

    for other in ("results/M040.md", relative + ".bak", "x/" + relative):
        assert inspect_arm(
            head_sha=HEAD_A,
            parent_sha=PARENT,
            commit_message=ARM_MESSAGE,
            changed_files=(other,),
            marker_path=marker.relative_to(tmp_path),
        ) is None, other


def test_wrong_message_parent_or_schema_fails_loudly(tmp_path, monkeypatch):
    marker = write_marker(tmp_path)
    monkeypatch.chdir(tmp_path)
    relative = str(marker.relative_to(tmp_path))

    with pytest.raises(GuardError, match="exact arming message"):
        inspect_arm(
            head_sha=HEAD_A,
            parent_sha=PARENT,
            commit_message="almost",
            changed_files=(relative,),
            marker_path=marker.relative_to(tmp_path),
        )

    marker.write_text(json.dumps(marker_payload(parent=HEAD_B)), encoding="utf-8")
    with pytest.raises(GuardError, match="actual parent"):
        inspect_arm(
            head_sha=HEAD_A,
            parent_sha=PARENT,
            commit_message=ARM_MESSAGE,
            changed_files=(relative,),
            marker_path=marker.relative_to(tmp_path),
        )

    invalid = marker_payload()
    invalid["extra"] = True
    marker.write_text(json.dumps(invalid), encoding="utf-8")
    with pytest.raises(GuardError, match="closed schema"):
        inspect_arm(
            head_sha=HEAD_A,
            parent_sha=PARENT,
            commit_message=ARM_MESSAGE,
            changed_files=(relative,),
            marker_path=marker.relative_to(tmp_path),
        )
