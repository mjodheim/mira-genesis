"""Verify the M092-A checkpoint against the exact pre-extension Git blobs.

The checkpoint is deliberately a second commit. Its ``source_commit`` is the clean M092-A tree
after review and before this seal exists, so the commitment is not self-referential. Verification
reads every bound blob from that commit, recomputes the semantic digests, confirms the frozen files
have not moved at ``HEAD`` or in the working tree, and proves that no M092-B protocol, substrate,
qualification, receipt or result existed in the source tree.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Mapping

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHECKPOINT = ROOT / "experiments" / "M092" / "CHECKPOINT_A.json"

CHECKPOINT_KEYS = {
    "schema",
    "milestone",
    "stage",
    "status",
    "date_frozen",
    "source_commit",
    "source_tree",
    "artifacts",
    "absent_at_source_commit",
    "semantic_commitments",
    "chronology",
    "claim_boundary",
    "checkpoint_digest",
}
ARTIFACT_KEYS = {"git_blob_sha1", "sha256", "bytes", "role", "immutable"}
REQUIRED_ARTIFACTS = {
    "experiments/M092/DESIGN_AUDIT.json",
    "experiments/M092/DESIGN_AUDIT.md",
    "experiments/M092/ISOLATION.json",
    "experiments/M092/M092A.md",
    "experiments/M092/M092A_REPORT.json",
    "experiments/M092/SUBSTRATE_A.json",
    "metamorphosis/m092_invariant.py",
    "metamorphosis/m092_kernel.py",
    "metamorphosis/m092_migration.py",
    "metamorphosis/m092_runtime.py",
    "metamorphosis/m092_substrate_state.py",
    "scripts/audit_m092_design.py",
    "scripts/run_m092a_fresh_process.py",
    "scripts/run_m092a_isolation.py",
    "scripts/run_m092a_migration.py",
    "tests/test_m092_invariant.py",
    "tests/test_m092a_substrate_migration.py",
}
MUTABLE_AFTER_FREEZE = {"experiments/M092/M092A.md"}
ABSENT_AT_SOURCE = [
    "experiments/M092/PROTOCOL.json",
    "experiments/M092/QUALIFICATION.json",
    "experiments/M092/SUBSTRATE_B.json",
    "experiments/M092/VALIDATION_RECEIPT.json",
    "experiments/M092/RESULT.json",
    "experiments/M092/REGISTER_CLAIM.json",
]
SEMANTIC_KEYS = {
    "substrate_digest",
    "language_digest",
    "kernel_manifest_digest",
    "invariant_digest",
    "registered_operations",
    "acquired_operations",
    "exhaustive_legal_comparisons",
    "exhaustive_representation_comparisons",
    "language_l0_comparisons",
    "language_l1_comparisons",
}
CHRONOLOGY_KEYS = {
    "extension_search_executed_before_checkpoint",
    "qualification_existed_at_source_commit",
    "model_calls",
    "network_calls",
}
CLAIM_KEYS = {
    "h38_supported",
    "d062_recorded",
    "self_hosting",
    "substrate_independence",
    "generality_gate",
}


class M092ACheckpointError(RuntimeError):
    """The checkpoint or one of the exact objects it binds is invalid."""


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def _git(*arguments: str, root: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *arguments], cwd=root, capture_output=True, check=check,
    )


def _git_text(*arguments: str, root: Path = ROOT) -> str:
    return _git(*arguments, root=root).stdout.decode("ascii").strip()


def _committed_blob(commit: str, path: str, root: Path) -> tuple[str, bytes]:
    object_id = _git_text("rev-parse", f"{commit}:{path}", root=root)
    return object_id, _git("cat-file", "blob", object_id, root=root).stdout


def _digest_without_self(value: Mapping[str, object]) -> str:
    payload = dict(value)
    payload.pop("checkpoint_digest", None)
    return hashlib.sha256(_canonical(payload)).hexdigest()


def verify_checkpoint(
    path: Path = DEFAULT_CHECKPOINT,
    *,
    root: Path = ROOT,
) -> dict[str, object]:
    """Return a compact verification report or fail closed with every finding."""

    value = json.loads(path.read_text(encoding="utf-8"))
    problems: list[str] = []

    if set(value) != CHECKPOINT_KEYS:
        problems.append("checkpoint fields differ from the closed schema")
    if value.get("schema") != "m092a-checkpoint-v1":
        problems.append("unexpected checkpoint schema")
    if value.get("milestone") != "M092" or value.get("stage") != "A":
        problems.append("checkpoint milestone or stage differs")
    if value.get("status") != "frozen_before_any_extension_search_or_qualification":
        problems.append("checkpoint status is not frozen at the M092-A boundary")
    if value.get("checkpoint_digest") != _digest_without_self(value):
        problems.append("checkpoint digest mismatch")

    source_commit = str(value.get("source_commit", ""))
    if len(source_commit) != 40:
        problems.append("source commit is not a full object identity")
    else:
        ancestry = _git(
            "merge-base", "--is-ancestor", source_commit, "HEAD", root=root, check=False,
        )
        if ancestry.returncode != 0:
            problems.append("source commit is not an ancestor of HEAD")
        try:
            source_tree = _git_text("rev-parse", f"{source_commit}^{{tree}}", root=root)
        except subprocess.CalledProcessError:
            problems.append("source commit cannot be resolved")
            source_tree = ""
        if source_tree != value.get("source_tree"):
            problems.append("source tree identity mismatch")

    artifacts = value.get("artifacts")
    committed: dict[str, bytes] = {}
    immutable_paths: list[str] = []
    if not isinstance(artifacts, dict) or not artifacts:
        problems.append("checkpoint has no artifact map")
        artifacts = {}
    if set(artifacts) != REQUIRED_ARTIFACTS:
        problems.append("artifact map differs from the frozen required set")
    for artifact_path, expected in artifacts.items():
        if not isinstance(artifact_path, str) or not isinstance(expected, dict):
            problems.append("malformed artifact entry")
            continue
        if set(expected) != ARTIFACT_KEYS:
            problems.append(f"artifact fields differ for {artifact_path}")
            continue
        try:
            object_id, data = _committed_blob(source_commit, artifact_path, root)
        except subprocess.CalledProcessError:
            problems.append(f"source artifact is missing: {artifact_path}")
            continue
        committed[artifact_path] = data
        if object_id != expected["git_blob_sha1"]:
            problems.append(f"Git blob identity mismatch: {artifact_path}")
        if hashlib.sha256(data).hexdigest() != expected["sha256"]:
            problems.append(f"SHA-256 mismatch: {artifact_path}")
        if len(data) != expected["bytes"]:
            problems.append(f"byte length mismatch: {artifact_path}")
        should_be_immutable = artifact_path not in MUTABLE_AFTER_FREEZE
        if expected["immutable"] is not should_be_immutable:
            problems.append(f"immutability declaration differs: {artifact_path}")
        if expected["immutable"] is True:
            immutable_paths.append(artifact_path)
            try:
                head_object = _git_text("rev-parse", f"HEAD:{artifact_path}", root=root)
            except subprocess.CalledProcessError:
                problems.append(f"immutable artifact disappeared at HEAD: {artifact_path}")
                continue
            if head_object != object_id:
                problems.append(f"immutable artifact drifted after freeze: {artifact_path}")

    if immutable_paths:
        drift = _git("diff", "--quiet", "HEAD", "--", *immutable_paths, root=root, check=False)
        if drift.returncode != 0:
            problems.append("an immutable checkpoint artifact differs in the working tree")

    if value.get("absent_at_source_commit") != ABSENT_AT_SOURCE:
        problems.append("post-checkpoint absence list differs from the frozen set")
    for absent_path in value.get("absent_at_source_commit", []):
        exists = _git(
            "cat-file", "-e", f"{source_commit}:{absent_path}", root=root, check=False,
        )
        if exists.returncode == 0:
            problems.append(f"post-checkpoint artifact already existed: {absent_path}")

    state_path = "experiments/M092/SUBSTRATE_A.json"
    report_path = "experiments/M092/M092A_REPORT.json"
    if state_path in committed and report_path in committed:
        state_bundle = json.loads(committed[state_path])
        report = json.loads(committed[report_path])
        semantics = value.get("semantic_commitments", {})
        if not isinstance(semantics, dict) or set(semantics) != SEMANTIC_KEYS:
            problems.append("semantic commitment fields differ from the closed schema")
            semantics = {}
        substrate_digest = hashlib.sha256(_canonical(state_bundle["substrate"])).hexdigest()
        language_digest = hashlib.sha256(_canonical(state_bundle["language"])).hexdigest()
        if substrate_digest != semantics.get("substrate_digest"):
            problems.append("substrate semantic digest mismatch")
        if language_digest != semantics.get("language_digest"):
            problems.append("language semantic digest mismatch")
        if state_bundle.get("expected_substrate_digest") != substrate_digest:
            problems.append("state bundle does not bind its substrate digest")
        if report.get("substrate_digest") != substrate_digest:
            problems.append("migration report binds another substrate")
        if report.get("kernel", {}).get("digest") != semantics.get("kernel_manifest_digest"):
            problems.append("kernel manifest digest mismatch")
        if report.get("invariant", {}).get("digest") != semantics.get("invariant_digest"):
            problems.append("invariant digest mismatch")
        if report.get("registered_reach", {}).get("acquired_operations") != []:
            problems.append("M092-A already contains an acquired operation")
        if report.get("registered_reach", {}).get("operations") != semantics.get(
            "registered_operations"
        ):
            problems.append("registered operation count mismatch")
        for section in (
            "exhaustive_legal_conservation",
            "exhaustive_representation_conservation",
            "language_conservation_l0",
            "language_conservation_l1",
        ):
            if report.get(section, {}).get("mismatches") != 0:
                problems.append(f"non-zero conservation mismatches in {section}")
        if report.get("authority_falsifiers", {}).get("all_behaved_as_required") is not True:
            problems.append("authority falsifiers did not all fire")
        if report.get("fresh_process", {}).get("physically_isolated", {}).get(
            "matches_expected"
        ) is not True:
            problems.append("physical-isolation reproduction did not match")

    chronology = value.get("chronology", {})
    if not isinstance(chronology, dict) or set(chronology) != CHRONOLOGY_KEYS:
        problems.append("chronology fields differ from the closed schema")
        chronology = {}
    if chronology.get("qualification_existed_at_source_commit") is not False:
        problems.append("chronology does not record qualification absence")
    if chronology.get("extension_search_executed_before_checkpoint") is not False:
        problems.append("chronology records pre-checkpoint extension search")
    if chronology.get("model_calls") != 0 or chronology.get("network_calls") != 0:
        problems.append("checkpoint chronology records a model or network call")

    claim = value.get("claim_boundary", {})
    if not isinstance(claim, dict) or set(claim) != CLAIM_KEYS:
        problems.append("claim-boundary fields differ from the closed schema")
        claim = {}
    for forbidden_claim in (
        "h38_supported",
        "d062_recorded",
        "self_hosting",
        "substrate_independence",
        "generality_gate",
    ):
        if claim.get(forbidden_claim) is not False:
            problems.append(f"checkpoint makes forbidden claim {forbidden_claim}")

    if problems:
        raise M092ACheckpointError("; ".join(problems))
    return {
        "status": "verified",
        "checkpoint_digest": value["checkpoint_digest"],
        "source_commit": source_commit,
        "source_tree": value["source_tree"],
        "artifacts_verified": len(artifacts),
        "immutable_artifacts_verified": len(immutable_paths),
        "substrate_digest": value["semantic_commitments"]["substrate_digest"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    arguments = parser.parse_args()
    try:
        report = verify_checkpoint(arguments.checkpoint)
    except (M092ACheckpointError, OSError, ValueError, json.JSONDecodeError) as error:
        print(str(error))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
