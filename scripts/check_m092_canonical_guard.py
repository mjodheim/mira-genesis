"""Guard the unique M092 canonical criterion-search arming commit.

The canonical target search stays closed unless the pull-request head *adds* exactly the arming
marker as the sole commit above the pull-request base, carries the exact arming message, names its
real parent commit and binds every decisive pre-search transport and selection artifact by SHA-256.
Ordinary development commits return ``armed=false``; a marker-only malformed claim fails loudly.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Mapping

ROOT = Path(__file__).resolve().parents[1]
ARM_RELATIVE = Path("experiments/M092/CANONICAL_SEARCH_ARMED.json")
ARM_MESSAGE = "m092(canonical): arm first immutable criterion search"
ARM_SCHEMA = "m092-canonical-search-arm/1"
PROGRAM_LIMIT = 2_000_000

BOUND_FILES: Mapping[str, Path] = {
    "protocol_sha256": Path("experiments/M092/PROTOCOL.json"),
    "target_theorem_sha256": Path("experiments/M092/TARGET_THEOREM.json"),
    "criterion_runner_sha256": Path("scripts/run_m092_criterion_search.py"),
    "criterion_freeze_sha256": Path("scripts/check_m092_criterion_freeze.py"),
    "criterion_engine_sha256": Path("metamorphosis/m092_criterion_search.py"),
    "resume_validator_sha256": Path("metamorphosis/m092_resume_validation.py"),
    "search_enumerator_sha256": Path("metamorphosis/m092_search_enumerator.py"),
    "certificate_policy_search_sha256": Path("metamorphosis/m092_certificate_policy_search.py"),
    "certificate_generator_sha256": Path("metamorphosis/m092_certificate_generator.py"),
    "proof_search_sha256": Path("metamorphosis/m092_proof_search.py"),
    "candidate_validation_sha256": Path("metamorphosis/m092_candidate_validation.py"),
    "certificate_verifier_sha256": Path("metamorphosis/m092_certificate_verifier.py"),
    "kernel_sha256": Path("metamorphosis/m092_kernel.py"),
    "runtime_sha256": Path("metamorphosis/m092_runtime.py"),
    "canonical_guard_sha256": Path("scripts/check_m092_canonical_guard.py"),
    "canonical_workflow_sha256": Path(".github/workflows/m092-canonical-search.yml"),
    "canonical_packager_sha256": Path("scripts/package_m092_canonical_search.py"),
    "canonical_segment_packager_sha256": Path("scripts/package_m092_canonical_segment.py"),
}

_SHA = re.compile(r"\A[0-9a-f]{40}\Z")
_DIGEST = re.compile(r"\A[0-9a-f]{64}\Z")


class GuardError(ValueError):
    """The head resembles an arming commit but violates the frozen arming contract."""


def _posix(path: str | Path) -> str:
    return str(path).replace("\\", "/")


def _canonical_status(entry: str) -> str:
    parts = entry.split("\t")
    if len(parts) != 2:
        return entry.replace("\\", "/")
    return f"{parts[0]}\t{_posix(parts[1])}"


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        raise GuardError(f"bound file is absent: {_posix(path)}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_output(path: Path | None, *, armed: bool, reason: str) -> None:
    if path is None:
        return
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"armed={'true' if armed else 'false'}\n")
        handle.write(f"reason={reason}\n")


def inspect_arm(
    *,
    head_sha: str,
    parent_sha: str,
    base_sha: str,
    commit_message: str,
    changed_files: tuple[str, ...],
    changed_statuses: tuple[str, ...] = (),
    root: Path = ROOT,
) -> dict[str, object] | None:
    """Return the marker only for a one-commit, newly-added, marker-only arming PR."""

    canonical_files = tuple(sorted(_posix(path) for path in changed_files if path))
    if canonical_files != (_posix(ARM_RELATIVE),):
        return None

    canonical_statuses = tuple(sorted(_canonical_status(item) for item in changed_statuses if item))
    expected_addition = (f"A\t{_posix(ARM_RELATIVE)}",)
    if canonical_statuses != expected_addition:
        raise GuardError("the canonical arming marker must be newly added, not modified or renamed")
    if commit_message.strip() != ARM_MESSAGE:
        raise GuardError("the marker-only commit does not carry the exact arming message")
    for label, value in (("head", head_sha), ("parent", parent_sha), ("base", base_sha)):
        if not _SHA.fullmatch(value):
            raise GuardError(f"{label} SHA must be full lowercase 40-hex")
    if parent_sha != base_sha:
        raise GuardError("the arming commit parent must equal the pull-request base SHA")

    marker_path = root / ARM_RELATIVE
    if not marker_path.is_file():
        raise GuardError("the canonical arming marker is absent")
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise GuardError("the canonical arming marker is not valid JSON") from error
    if not isinstance(marker, dict):
        raise GuardError("the canonical arming marker must be a JSON object")

    expected_fields = {
        "schema",
        "frozen_parent_sha",
        *BOUND_FILES.keys(),
        "program_limit",
        "first_run_only",
        "reruns_are_reproductions_only",
        "qualification_forbidden",
    }
    if set(marker) != expected_fields:
        raise GuardError("the canonical arming marker fields differ from the closed schema")
    if marker.get("schema") != ARM_SCHEMA:
        raise GuardError("unknown M092 canonical arming marker schema")
    if marker.get("frozen_parent_sha") != parent_sha:
        raise GuardError("the marker does not name the actual parent commit")
    if marker.get("program_limit") != PROGRAM_LIMIT or isinstance(marker.get("program_limit"), bool):
        raise GuardError("the marker changes the frozen canonical program limit")
    for field in ("first_run_only", "reruns_are_reproductions_only", "qualification_forbidden"):
        if marker.get(field) is not True:
            raise GuardError(f"{field} must be true")

    for field, relative_path in BOUND_FILES.items():
        supplied = marker.get(field)
        if not isinstance(supplied, str) or _DIGEST.fullmatch(supplied) is None:
            raise GuardError(f"{field} is not canonical lowercase SHA-256")
        actual = _sha256_file(root / relative_path)
        if supplied != actual:
            raise GuardError(
                f"{field} differs from {_posix(relative_path)}: supplied={supplied}, actual={actual}"
            )

    return marker


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--parent-sha", required=True)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--commit-message", required=True)
    parser.add_argument("--changed-file", action="append", default=[])
    parser.add_argument("--changed-status", action="append", default=[])
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()

    try:
        marker = inspect_arm(
            head_sha=args.head_sha,
            parent_sha=args.parent_sha,
            base_sha=args.base_sha,
            commit_message=args.commit_message,
            changed_files=tuple(args.changed_file),
            changed_statuses=tuple(args.changed_status),
        )
    except GuardError as error:
        _write_output(args.github_output, armed=False, reason="invalid-arm")
        print(f"M092 canonical guard failure: {error}")
        return 1

    if marker is None:
        _write_output(args.github_output, armed=False, reason="not-arm-commit")
        print("M092 canonical search remains closed: the head is not the marker-only arming commit")
        return 0

    _write_output(args.github_output, armed=True, reason="valid-first-arm")
    print(json.dumps(marker, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
