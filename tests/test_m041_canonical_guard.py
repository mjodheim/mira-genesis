from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_m041_canonical_guard.py"
_SPEC = importlib.util.spec_from_file_location("m041_canonical_guard_script", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_GUARD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_GUARD)

ARM_MESSAGE = _GUARD.ARM_MESSAGE
GuardError = _GUARD.GuardError
inspect_arm = _GUARD.inspect_arm

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


def test_the_marker_comparison_does_not_depend_on_the_host_separator(tmp_path):
    """Both sides of the comparison are normalised, not only the marker path.

    Git reports forward slashes everywhere, but a caller holding a host path does not.
    Normalising one side left the comparison unsatisfiable on Windows, and the guard then
    returned None — declining to arm without saying so — for every case in this file.
    """
    path = marker(tmp_path / "CANONICAL_ARMED.json")

    for spelling in (str(path), str(path).replace("/", "\\"), str(path).replace("\\", "/")):
        value = inspect_arm(
            head_sha=HEAD,
            parent_sha=PARENT,
            commit_message=ARM_MESSAGE,
            changed_files=(spelling,),
            marker_path=path,
        )
        assert value is not None, spelling
        assert value["protocol_sha256"] == PROTOCOL


def test_normalisation_does_not_widen_what_can_arm(tmp_path):
    """Rewriting separators must not let a different file stand in for the marker."""
    path = marker(tmp_path / "CANONICAL_ARMED.json")

    for other in ("README.md", str(tmp_path / "OTHER.json"), str(path) + ".bak"):
        assert inspect_arm(
            head_sha=HEAD,
            parent_sha=PARENT,
            commit_message=ARM_MESSAGE,
            changed_files=(other,),
            marker_path=path,
        ) is None


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
