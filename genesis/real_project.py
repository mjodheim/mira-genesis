"""Bounded evaluator for applying Genesis selection discipline to a real software project.

The host owns the snapshot, candidate image and evaluator manifest.  Genesis owns the
mechanical accounting: every candidate starts from a fresh disposable copy, mutations
are restricted to admitted project-relative paths, evaluator commands are argv arrays
owned by the manifest, and acceptance is derived from process outcomes rather than
candidate self-report.

This is DEVELOPMENT integration apparatus.  It is intentionally not a general patch
synthesizer and it never writes an accepted candidate back to the host source tree.
"""
from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tempfile
import time
from typing import Any, Iterable, Mapping, Sequence
import difflib

from genesis.trust_root import digest_of

MANIFEST_SCHEMA = "genesis-real-project-manifest-v1"
REPORT_SCHEMA = "genesis-real-project-gate-report-v1"
CANDIDATE_SCHEMA = "genesis-real-project-candidate-v1"


class RealProjectError(RuntimeError):
    """Raised when the immutable host/evaluator contract is malformed or violated."""


@dataclass(frozen=True)
class CommandResult:
    name: str
    role: str
    argv: tuple[str, ...]
    cwd: str
    exit_code: int | None
    timed_out: bool
    elapsed_ms: int
    stdout_sha256: str
    stderr_sha256: str
    stdout_length: int
    stderr_length: int
    passed: bool
    stdout: str | None = None
    stderr: str | None = None

    def record(self) -> dict[str, Any]:
        value = {
            "name": self.name,
            "role": self.role,
            "argv": list(self.argv),
            "cwd": self.cwd,
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "elapsed_ms": self.elapsed_ms,
            "stdout_sha256": self.stdout_sha256,
            "stderr_sha256": self.stderr_sha256,
            "stdout_length": self.stdout_length,
            "stderr_length": self.stderr_length,
            "passed": self.passed,
        }
        if self.stdout is not None:
            value["stdout"] = self.stdout
        if self.stderr is not None:
            value["stderr"] = self.stderr
        return value


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def _normal_relative_path(raw: str) -> str:
    text = str(raw).replace("\\", "/").strip()
    candidate = PurePosixPath(text)
    if not text or candidate.is_absolute() or text.startswith("/"):
        raise RealProjectError("path must be a non-empty project-relative path")
    if any(part in ("", ".", "..") for part in candidate.parts):
        raise RealProjectError("path traversal or ambiguous path component is forbidden")
    return candidate.as_posix()


def _prefix_match(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix.rstrip("/") + "/")


def _is_ignored(path: str, *, directory_names: set[str], globs: Sequence[str]) -> bool:
    parts = PurePosixPath(path).parts
    if any(part in directory_names for part in parts[:-1]):
        return True
    return any(fnmatch(path, pattern) for pattern in globs)


def tree_inventory(
    root: Path,
    *,
    ignored_directory_names: Iterable[str] = (),
    ignored_globs: Sequence[str] = (),
) -> tuple[dict[str, str], str]:
    """Content-address every non-ignored file under ``root`` and return a tree digest."""
    root = root.resolve()
    if not root.is_dir():
        raise RealProjectError(f"host root does not exist or is not a directory: {root}")
    ignored_dirs = {str(item) for item in ignored_directory_names}
    files: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if _is_ignored(relative, directory_names=ignored_dirs, globs=ignored_globs):
            continue
        if path.is_symlink():
            raise RealProjectError(
                f"symbolic link is forbidden in tracked host snapshot: {relative}"
            )
        if not path.is_file():
            continue
        files[relative] = _sha256_file(path)
    return files, digest_of({"files": files})


def _validate_command(raw: Mapping[str, Any]) -> dict[str, Any]:
    name = str(raw.get("name") or "").strip()
    if not name:
        raise RealProjectError("evaluation command has no name")
    role = str(raw.get("role") or "").strip()
    if role not in {"mandatory", "objective"}:
        raise RealProjectError(f"evaluation command {name!r} has invalid role {role!r}")
    argv = raw.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item for item in argv):
        raise RealProjectError(f"evaluation command {name!r} requires a non-empty string argv array")
    timeout = int(raw.get("timeout_seconds", 0))
    if timeout < 1 or timeout > 3600:
        raise RealProjectError(f"evaluation command {name!r} timeout must be in [1, 3600]")
    cwd = str(raw.get("cwd") or ".")
    if cwd != ".":
        cwd = _normal_relative_path(cwd)
    allowed_exit_codes = raw.get("allowed_exit_codes", [0])
    if (
        not isinstance(allowed_exit_codes, list)
        or not allowed_exit_codes
        or not all(isinstance(item, int) for item in allowed_exit_codes)
    ):
        raise RealProjectError(f"evaluation command {name!r} has invalid allowed_exit_codes")
    return {
        "name": name,
        "role": role,
        "argv": list(argv),
        "timeout_seconds": timeout,
        "cwd": cwd,
        "allowed_exit_codes": list(allowed_exit_codes),
        "record_output": bool(raw.get("record_output", False)),
    }


def validate_manifest(raw: Mapping[str, Any]) -> dict[str, Any]:
    value = dict(raw)
    if value.get("schema") != MANIFEST_SCHEMA:
        raise RealProjectError(f"manifest schema must be {MANIFEST_SCHEMA!r}")

    writable = tuple(_normal_relative_path(item) for item in value.get("writable_prefixes", ()))
    if not writable:
        raise RealProjectError("manifest requires at least one writable_prefix")
    forbidden = tuple(_normal_relative_path(item) for item in value.get("forbidden_prefixes", ()))
    authority = tuple(_normal_relative_path(item) for item in value.get("authority_paths", ()))

    ignored_dirs = tuple(str(item) for item in value.get("ignored_directory_names", ()))
    if any(not item or "/" in item or "\\" in item for item in ignored_dirs):
        raise RealProjectError("ignored_directory_names must contain simple directory names")
    ignored_globs = tuple(str(item) for item in value.get("ignored_globs", ()))

    commands = tuple(_validate_command(item) for item in value.get("evaluation_commands", ()))
    if not commands:
        raise RealProjectError("manifest requires evaluation_commands")
    names = [item["name"] for item in commands]
    if len(set(names)) != len(names):
        raise RealProjectError("evaluation command names must be unique")
    if not any(item["role"] == "mandatory" for item in commands):
        raise RealProjectError("manifest requires at least one mandatory command")
    if not any(item["role"] == "objective" for item in commands):
        raise RealProjectError("manifest requires at least one objective command")

    candidates = value.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise RealProjectError("manifest requires a finite non-empty candidate list")
    ids: list[str] = []
    normalized_candidates: list[dict[str, Any]] = []
    for raw_candidate in candidates:
        if not isinstance(raw_candidate, Mapping):
            raise RealProjectError("each candidate must be an object")
        candidate_id = str(raw_candidate.get("id") or "").strip()
        if not candidate_id:
            raise RealProjectError("candidate has no id")
        ids.append(candidate_id)
        mutations = raw_candidate.get("mutations")
        if not isinstance(mutations, list) or not mutations:
            raise RealProjectError(f"candidate {candidate_id!r} has no mutations")
        normalized_mutations: list[dict[str, Any]] = []
        for mutation in mutations:
            if not isinstance(mutation, Mapping):
                raise RealProjectError(f"candidate {candidate_id!r} mutation is not an object")
            normalized_mutations.append(
                {
                    "path": str(mutation.get("path") or ""),
                    "expected_sha256": mutation.get("expected_sha256"),
                    "expected_absent": bool(mutation.get("expected_absent", False)),
                    "content_utf8": str(mutation.get("content_utf8") or ""),
                }
            )
        normalized_candidates.append(
            {
                "schema": CANDIDATE_SCHEMA,
                "id": candidate_id,
                "label": str(raw_candidate.get("label") or candidate_id),
                "mutations": normalized_mutations,
            }
        )
    if len(set(ids)) != len(ids):
        raise RealProjectError("candidate ids must be unique")

    expected_host_tree = str(value.get("expected_host_tree_digest") or "").strip()
    if not expected_host_tree:
        raise RealProjectError("manifest requires expected_host_tree_digest")

    environment = value.get("environment", {})
    if not isinstance(environment, Mapping) or not all(
        isinstance(key, str) and isinstance(item, str) for key, item in environment.items()
    ):
        raise RealProjectError("manifest environment must be a string mapping")
    inherited = value.get("inherit_environment_keys", ["PATH", "HOME"])
    if not isinstance(inherited, list) or not all(isinstance(item, str) and item for item in inherited):
        raise RealProjectError("inherit_environment_keys must be a string list")

    return {
        "schema": MANIFEST_SCHEMA,
        "host_name": str(value.get("host_name") or "external-project"),
        "expected_host_tree_digest": expected_host_tree,
        "writable_prefixes": list(writable),
        "forbidden_prefixes": list(forbidden),
        "authority_paths": list(authority),
        "ignored_directory_names": list(ignored_dirs),
        "ignored_globs": list(ignored_globs),
        "evaluation_commands": list(commands),
        "candidates": normalized_candidates,
        "inherit_environment_keys": list(inherited),
        "environment": dict(environment),
        "genesis_identity": dict(value.get("genesis_identity") or {}),
        "host_identity": dict(value.get("host_identity") or {}),
    }


def _copy_host(source: Path, destination: Path, manifest: Mapping[str, Any]) -> None:
    ignored_dirs = set(manifest["ignored_directory_names"])
    ignored_globs = tuple(manifest["ignored_globs"])

    def ignore(directory: str, names: list[str]) -> set[str]:
        base = Path(directory)
        relative_dir = base.relative_to(source).as_posix() if base != source else ""
        skipped: set[str] = set()
        for name in names:
            relative = f"{relative_dir}/{name}".strip("/")
            if name in ignored_dirs or _is_ignored(
                relative,
                directory_names=ignored_dirs,
                globs=ignored_globs,
            ):
                skipped.add(name)
        return skipped

    shutil.copytree(source, destination, ignore=ignore, symlinks=False)


def _candidate_digest(candidate: Mapping[str, Any]) -> str:
    return digest_of({
        "schema": CANDIDATE_SCHEMA,
        "id": candidate["id"],
        "mutations": candidate["mutations"],
    })


def _path_policy_problem(path: str, manifest: Mapping[str, Any]) -> str | None:
    try:
        normalized = _normal_relative_path(path)
    except RealProjectError as problem:
        return str(problem)
    if not any(_prefix_match(normalized, prefix) for prefix in manifest["writable_prefixes"]):
        return f"path {normalized!r} lies outside every writable prefix"
    if any(_prefix_match(normalized, prefix) for prefix in manifest["forbidden_prefixes"]):
        return f"path {normalized!r} lies under a forbidden prefix"
    if any(_prefix_match(normalized, prefix) for prefix in manifest["authority_paths"]):
        return f"path {normalized!r} is evaluation/authority apparatus"
    if any(part in set(manifest["ignored_directory_names"]) for part in PurePosixPath(normalized).parts):
        return f"path {normalized!r} lies in an ignored/generated directory"
    return None


def _apply_candidate(workspace: Path, candidate: Mapping[str, Any], manifest: Mapping[str, Any]) -> dict[str, Any]:
    seen: set[str] = set()
    applied: list[dict[str, Any]] = []
    for mutation in candidate["mutations"]:
        raw_path = str(mutation["path"])
        problem = _path_policy_problem(raw_path, manifest)
        if problem:
            raise RealProjectError(problem)
        relative = _normal_relative_path(raw_path)
        if relative in seen:
            raise RealProjectError(f"candidate mutates {relative!r} more than once")
        seen.add(relative)
        target = workspace / Path(relative)
        exists = target.exists()
        if mutation.get("expected_absent"):
            if exists:
                raise RealProjectError(f"candidate expected {relative!r} to be absent")
        else:
            expected = str(mutation.get("expected_sha256") or "")
            if not expected:
                raise RealProjectError(f"candidate mutation {relative!r} has no expected_sha256")
            if not exists or not target.is_file():
                raise RealProjectError(f"candidate expected existing file {relative!r}")
            actual = _sha256_file(target)
            if actual != expected:
                raise RealProjectError(
                    f"candidate base mismatch for {relative!r}: expected {expected}, got {actual}"
                )
        target.parent.mkdir(parents=True, exist_ok=True)
        old_content = target.read_text(encoding="utf-8") if exists else ""
        new_content = str(mutation["content_utf8"])
        target.write_text(new_content, encoding="utf-8")
        applied.append(
            {
                "path": relative,
                "before_sha256": _sha256_bytes(old_content.encode("utf-8")) if exists else None,
                "after_sha256": _sha256_file(target),
                "created": not exists,
            }
        )
    return {"applied": applied}


def _expanded_argv(argv: Sequence[str], workspace: Path) -> tuple[str, ...]:
    return tuple(item.replace("{workspace}", str(workspace)) for item in argv)


def _build_environment(manifest: Mapping[str, Any]) -> dict[str, str]:
    environment: dict[str, str] = {}
    for key in manifest["inherit_environment_keys"]:
        if key in os.environ:
            environment[key] = os.environ[key]
    environment.update(manifest["environment"])
    environment.setdefault("GENESIS_REAL_PROJECT_EVALUATION", "1")
    return environment


def _run_command(workspace: Path, command: Mapping[str, Any], manifest: Mapping[str, Any]) -> CommandResult:
    argv = _expanded_argv(command["argv"], workspace)
    cwd = workspace if command["cwd"] == "." else workspace / command["cwd"]
    if not cwd.is_dir():
        raise RealProjectError(f"evaluation cwd does not exist: {command['cwd']!r}")
    started = time.monotonic()
    timed_out = False
    exit_code: int | None
    stdout = b""
    stderr = b""
    try:
        finished = subprocess.run(
            argv,
            cwd=cwd,
            env=_build_environment(manifest),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=int(command["timeout_seconds"]),
            check=False,
        )
        exit_code = int(finished.returncode)
        stdout = finished.stdout or b""
        stderr = finished.stderr or b""
    except subprocess.TimeoutExpired as problem:
        timed_out = True
        exit_code = None
        stdout = problem.stdout or b""
        stderr = problem.stderr or b""
    except OSError as problem:
        exit_code = None
        stderr = str(problem).encode("utf-8", errors="replace")
    elapsed_ms = int((time.monotonic() - started) * 1000)
    passed = (not timed_out) and exit_code in set(command["allowed_exit_codes"])
    record_output = bool(command["record_output"])
    return CommandResult(
        name=command["name"],
        role=command["role"],
        argv=argv,
        cwd=command["cwd"],
        exit_code=exit_code,
        timed_out=timed_out,
        elapsed_ms=elapsed_ms,
        stdout_sha256=_sha256_bytes(stdout),
        stderr_sha256=_sha256_bytes(stderr),
        stdout_length=len(stdout),
        stderr_length=len(stderr),
        passed=passed,
        stdout=stdout.decode("utf-8", errors="replace")[-12000:] if record_output else None,
        stderr=stderr.decode("utf-8", errors="replace")[-12000:] if record_output else None,
    )


def _semantic_outcome(results: Sequence[CommandResult], *, tracked_source_stable: bool) -> dict[str, Any]:
    commands = [
        {
            "name": item.name,
            "role": item.role,
            "exit_code": item.exit_code,
            "timed_out": item.timed_out,
            "passed": item.passed,
        }
        for item in results
    ]
    mandatory_pass = all(item.passed for item in results if item.role == "mandatory")
    objective_pass_count = sum(1 for item in results if item.role == "objective" and item.passed)
    payload = {
        "commands": commands,
        "mandatory_pass": mandatory_pass,
        "objective_pass_count": objective_pass_count,
        "tracked_source_stable": tracked_source_stable,
    }
    return {
        "mandatory_pass": mandatory_pass,
        "objective_pass_count": objective_pass_count,
        "tracked_source_stable": tracked_source_stable,
        "semantic_digest": digest_of(payload),
    }


def _evaluate_workspace(workspace: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    before_files, before_digest = tree_inventory(
        workspace,
        ignored_directory_names=manifest["ignored_directory_names"],
        ignored_globs=manifest["ignored_globs"],
    )
    results = [_run_command(workspace, item, manifest) for item in manifest["evaluation_commands"]]
    after_files, after_digest = tree_inventory(
        workspace,
        ignored_directory_names=manifest["ignored_directory_names"],
        ignored_globs=manifest["ignored_globs"],
    )
    changed_by_evaluation = sorted(
        set(before_files) ^ set(after_files)
        | {path for path in set(before_files) & set(after_files) if before_files[path] != after_files[path]}
    )
    tracked_source_stable = before_digest == after_digest
    semantic = _semantic_outcome(results, tracked_source_stable=tracked_source_stable)
    return {
        "commands": [item.record() for item in results],
        "tracked_tree_before": before_digest,
        "tracked_tree_after": after_digest,
        "tracked_source_stable": tracked_source_stable,
        "changed_by_evaluation": changed_by_evaluation,
        **semantic,
    }


def _evaluate_candidate(
    source_root: Path,
    candidate: Mapping[str, Any],
    manifest: Mapping[str, Any],
    *,
    temp_root: Path,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "id": candidate["id"],
        "label": candidate["label"],
        "candidate_digest": _candidate_digest(candidate),
        "construction_refused": False,
        "construction_reason": None,
    }
    workspace = temp_root / f"candidate-{candidate['id']}"
    _copy_host(source_root, workspace, manifest)
    try:
        mutation_record = _apply_candidate(workspace, candidate, manifest)
    except RealProjectError as problem:
        record["construction_refused"] = True
        record["construction_reason"] = str(problem)
        record["accepted"] = False
        return record
    expected_files, expected_tree = tree_inventory(
        workspace,
        ignored_directory_names=manifest["ignored_directory_names"],
        ignored_globs=manifest["ignored_globs"],
    )
    evaluation = _evaluate_workspace(workspace, manifest)
    record.update(
        {
            "mutation": mutation_record,
            "expected_mutated_tree_digest": expected_tree,
            "expected_mutated_file_count": len(expected_files),
            "evaluation": evaluation,
            "mandatory_pass": evaluation["mandatory_pass"],
            "objective_pass_count": evaluation["objective_pass_count"],
            "tracked_source_stable": evaluation["tracked_source_stable"],
            "accepted": False,
        }
    )
    return record


def _render_candidate_patch(source_root: Path, candidate: Mapping[str, Any]) -> str:
    chunks: list[str] = []
    for mutation in candidate["mutations"]:
        try:
            relative = _normal_relative_path(mutation["path"])
        except RealProjectError:
            continue
        target = source_root / relative
        old = target.read_text(encoding="utf-8").splitlines(keepends=True) if target.is_file() else []
        new = str(mutation["content_utf8"]).splitlines(keepends=True)
        chunks.extend(
            difflib.unified_diff(
                old,
                new,
                fromfile=f"a/{relative}" if old else "/dev/null",
                tofile=f"b/{relative}",
            )
        )
    return "".join(chunks)


def run_gate(
    host_root: str | Path,
    raw_manifest: Mapping[str, Any],
    *,
    output_directory: str | Path | None = None,
) -> dict[str, Any]:
    """Evaluate the complete bounded candidate image and replay a unique improving winner."""
    manifest = validate_manifest(raw_manifest)
    source_root = Path(host_root).resolve()
    source_files_before, source_tree_before = tree_inventory(
        source_root,
        ignored_directory_names=manifest["ignored_directory_names"],
        ignored_globs=manifest["ignored_globs"],
    )
    if source_tree_before != manifest["expected_host_tree_digest"]:
        raise RealProjectError(
            "host snapshot identity mismatch: manifest expects %s, measured %s"
            % (manifest["expected_host_tree_digest"], source_tree_before)
        )

    manifest_digest = digest_of(manifest)
    with tempfile.TemporaryDirectory(prefix="genesis-real-project-") as temp:
        temp_root = Path(temp)
        baseline_workspace = temp_root / "baseline"
        _copy_host(source_root, baseline_workspace, manifest)
        baseline = _evaluate_workspace(baseline_workspace, manifest)
        if not baseline["mandatory_pass"]:
            raise RealProjectError("unchanged host baseline fails one or more mandatory evaluations")
        if not baseline["tracked_source_stable"]:
            raise RealProjectError("host evaluator mutates tracked source even on the baseline")

        candidate_records = [
            _evaluate_candidate(source_root, candidate, manifest, temp_root=temp_root)
            for candidate in manifest["candidates"]
        ]
        baseline_score = int(baseline["objective_pass_count"])
        eligible = [
            item
            for item in candidate_records
            if not item["construction_refused"]
            and item.get("mandatory_pass") is True
            and item.get("tracked_source_stable") is True
            and int(item.get("objective_pass_count", -1)) > baseline_score
        ]
        best_score = max((int(item["objective_pass_count"]) for item in eligible), default=None)
        winners = [] if best_score is None else [
            item for item in eligible if int(item["objective_pass_count"]) == best_score
        ]
        winner_record = winners[0] if len(winners) == 1 else None

        replay: dict[str, Any] | None = None
        winner_patch = ""
        if winner_record is not None:
            winner_candidate = next(
                item for item in manifest["candidates"] if item["id"] == winner_record["id"]
            )
            replay_workspace = temp_root / "winner-replay"
            _copy_host(source_root, replay_workspace, manifest)
            mutation = _apply_candidate(replay_workspace, winner_candidate, manifest)
            replay_eval = _evaluate_workspace(replay_workspace, manifest)
            replay = {
                "mutation": mutation,
                "evaluation": replay_eval,
                "semantic_matches": (
                    replay_eval["semantic_digest"]
                    == winner_record["evaluation"]["semantic_digest"]
                ),
            }
            if not replay["semantic_matches"]:
                winner_record = None
            else:
                winner_patch = _render_candidate_patch(source_root, winner_candidate)

    source_files_after, source_tree_after = tree_inventory(
        source_root,
        ignored_directory_names=manifest["ignored_directory_names"],
        ignored_globs=manifest["ignored_globs"],
    )
    host_unchanged = source_tree_before == source_tree_after and source_files_before == source_files_after
    selected_id = None if winner_record is None else winner_record["id"]
    for item in candidate_records:
        item["accepted"] = item["id"] == selected_id

    checks = {
        "bound_exact_host_snapshot": source_tree_before == manifest["expected_host_tree_digest"],
        "baseline_mandatory_checks_pass": baseline["mandatory_pass"] is True,
        "baseline_evaluator_does_not_mutate_source": baseline["tracked_source_stable"] is True,
        "complete_candidate_accounting": len(candidate_records) == len(manifest["candidates"]),
        "unique_strict_improving_winner": winner_record is not None,
        "winner_replays_semantically": replay is not None and replay["semantic_matches"] is True,
        "host_source_unchanged": host_unchanged,
    }
    report_payload = {
        "schema": REPORT_SCHEMA,
        "classification": "DEVELOPMENT_REAL_PROJECT_TRANSFER",
        "manifest_digest": manifest_digest,
        "host_name": manifest["host_name"],
        "host_identity": manifest["host_identity"],
        "genesis_identity": manifest["genesis_identity"],
        "host_tree_digest_before": source_tree_before,
        "host_tree_digest_after": source_tree_after,
        "baseline": baseline,
        "candidates": candidate_records,
        "baseline_objective_pass_count": baseline_score,
        "selected_candidate_id": selected_id,
        "selected_candidate_digest": None if winner_record is None else winner_record["candidate_digest"],
        "winner_replay": replay,
        "checks": checks,
        "passed": all(checks.values()),
    }
    report = {**report_payload, "report_digest": digest_of(report_payload)}

    if output_directory is not None:
        output = Path(output_directory)
        output.mkdir(parents=True, exist_ok=True)
        (output / "report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        if winner_patch:
            (output / "winner.patch").write_text(winner_patch, encoding="utf-8")
    return report
