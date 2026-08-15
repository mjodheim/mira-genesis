"""Fail-closed tests for the unique M092 canonical-search arming boundary."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import check_m092_canonical_guard as guard

HEAD = "a" * 40
PARENT = "b" * 40


def _install_bound_files(root: Path) -> None:
    for index, relative in enumerate(guard.BOUND_FILES.values(), start=1):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"frozen transport file {index}\n", encoding="utf-8")


def _marker(root: Path, *, parent: str = PARENT) -> dict[str, object]:
    marker: dict[str, object] = {
        "schema": guard.ARM_SCHEMA,
        "frozen_parent_sha": parent,
        "program_limit": guard.PROGRAM_LIMIT,
        "first_run_only": True,
        "reruns_are_reproductions_only": True,
        "qualification_forbidden": True,
    }
    for field, relative in guard.BOUND_FILES.items():
        marker[field] = hashlib.sha256((root / relative).read_bytes()).hexdigest()
    return marker


def _write_marker(root: Path, marker: dict[str, object]) -> None:
    path = root / guard.ARM_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(marker, sort_keys=True), encoding="utf-8")


def _inspect(root: Path, *, changed_files: tuple[str, ...] | None = None) -> dict[str, object] | None:
    return guard.inspect_arm(
        head_sha=HEAD,
        parent_sha=PARENT,
        commit_message=guard.ARM_MESSAGE,
        changed_files=changed_files or (guard.ARM_RELATIVE.as_posix(),),
        root=root,
    )


def test_exact_marker_only_arm_is_accepted(tmp_path: Path) -> None:
    _install_bound_files(tmp_path)
    expected = _marker(tmp_path)
    _write_marker(tmp_path, expected)

    assert _inspect(tmp_path) == expected


def test_non_marker_commit_keeps_search_closed_without_reading_marker(tmp_path: Path) -> None:
    assert _inspect(tmp_path, changed_files=("README.md",)) is None


def test_cross_platform_changed_path_is_normalized(tmp_path: Path) -> None:
    _install_bound_files(tmp_path)
    expected = _marker(tmp_path)
    _write_marker(tmp_path, expected)

    windows_path = guard.ARM_RELATIVE.as_posix().replace("/", "\\")
    assert _inspect(tmp_path, changed_files=(windows_path,)) == expected


def test_marker_plus_any_other_file_cannot_arm(tmp_path: Path) -> None:
    _install_bound_files(tmp_path)
    _write_marker(tmp_path, _marker(tmp_path))

    assert _inspect(
        tmp_path,
        changed_files=(guard.ARM_RELATIVE.as_posix(), "scripts/run_m092_criterion_search.py"),
    ) is None


def test_marker_only_commit_requires_exact_message(tmp_path: Path) -> None:
    _install_bound_files(tmp_path)
    _write_marker(tmp_path, _marker(tmp_path))

    with pytest.raises(guard.GuardError, match="exact arming message"):
        guard.inspect_arm(
            head_sha=HEAD,
            parent_sha=PARENT,
            commit_message=guard.ARM_MESSAGE + " amended",
            changed_files=(guard.ARM_RELATIVE.as_posix(),),
            root=tmp_path,
        )


def test_marker_must_bind_actual_parent(tmp_path: Path) -> None:
    _install_bound_files(tmp_path)
    _write_marker(tmp_path, _marker(tmp_path, parent="c" * 40))

    with pytest.raises(guard.GuardError, match="actual parent"):
        _inspect(tmp_path)


def test_rehashed_marker_cannot_hide_bound_file_drift(tmp_path: Path) -> None:
    _install_bound_files(tmp_path)
    marker = _marker(tmp_path)
    _write_marker(tmp_path, marker)

    changed = tmp_path / guard.BOUND_FILES["criterion_engine_sha256"]
    changed.write_text("different selection semantics\n", encoding="utf-8")

    with pytest.raises(guard.GuardError, match="criterion_engine_sha256 differs"):
        _inspect(tmp_path)


def test_program_limit_cannot_be_reduced_or_expanded(tmp_path: Path) -> None:
    _install_bound_files(tmp_path)
    marker = _marker(tmp_path)
    marker["program_limit"] = guard.PROGRAM_LIMIT - 1
    _write_marker(tmp_path, marker)

    with pytest.raises(guard.GuardError, match="program limit"):
        _inspect(tmp_path)


def test_first_run_and_qualification_flags_are_fail_closed(tmp_path: Path) -> None:
    _install_bound_files(tmp_path)
    for field in ("first_run_only", "reruns_are_reproductions_only", "qualification_forbidden"):
        marker = _marker(tmp_path)
        marker[field] = False
        _write_marker(tmp_path, marker)
        with pytest.raises(guard.GuardError, match=field):
            _inspect(tmp_path)


def test_marker_only_shape_without_marker_is_an_error(tmp_path: Path) -> None:
    _install_bound_files(tmp_path)
    with pytest.raises(guard.GuardError, match="marker is absent"):
        _inspect(tmp_path)
