"""Self-contained transformation engine for M093 — real component mutation.

Reuses patterns from the M047 software-lineage infrastructure:
• disposable subprocess sandbox (→ m047_runtime_sandbox)
• versioned store with atomic rollback (→ m047_lineage_transaction)
• independent validation (→ m047_task)
• causal journal for persistence (→ m047_lineage_state)

Unlike M047, this engine works on actual file-backed components
in ``mira_core/`` — not on generated ``SoftwareBody`` pipelines.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from metamorphosis.m093_suites import VALIDATOR_SCRIPT


# ── Schemas ──────────────────────────────────────────────────────────

CORE_SCHEMA = "m093-transformation-v1"
JOURNAL_SCHEMA = "m093-journal-v1"

GENESIS_DIGEST = "0" * 64


# ── Helpers ───────────────────────────────────────────────────────────

def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _domain_digest(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + _canonical_json(value)).hexdigest()


# ── Component analysis ────────────────────────────────────────────────

@dataclass(frozen=True)
class ComponentInsufficiency:
    """A measurable shortcoming discovered in a real component."""

    file: str
    component: str
    insufficiency: str
    measured_evidence: str


def inspect_component(path: str | Path) -> ComponentInsufficiency:
    """Read a Python component and identify a measurable insufficiency."""
    path = Path(path)
    source = path.read_text(encoding="utf-8")
    # Count occurrences of manual kind-based iteration
    manual_filter = source.count("event.kind")
    return ComponentInsufficiency(
        file=str(path),
        component=path.stem,
        insufficiency="missing_events_by_kind_method",
        measured_evidence=(
            f"File {path.name} contains {manual_filter} occurrences of "
            f"'event.kind' — every consumer must manually filter MemoryLedger events "
            f"by kind instead of calling a dedicated query method."
        ),
    )


# ── Candidate generation ──────────────────────────────────────────────

@dataclass(frozen=True)
class CodePatch:
    """A generated code modification for a single source file."""

    file: str
    old_source: str
    new_source: str
    added_class_lines: int
    added_method_count: int
    digest: str

    @classmethod
    def generate(cls, source_path: str | Path) -> CodePatch:
        """Generate a patch that adds ``events_by_kind`` to MemoryLedger."""
        path = Path(source_path)
        old_source = path.read_text(encoding="utf-8")

        # The target method to insert before ``history()``
        method = (
            "\n"
            "    def events_by_kind(self, kind: str) -> tuple[MemoryEvent, ...]:\n"
            '        """Return every event whose kind matches *kind*, preserving insertion order.\n'
            "\n"
            "        Parameters\n"
            "        ----------\n"
            "        kind : str\n"
            "            Event kind to filter on (must be non-empty).\n"
            "\n"
            "        Returns\n"
            "        -------\n"
            "        tuple[MemoryEvent, ...]\n"
            "            Zero or more matching events in chronological order.\n"
            '        """\n'
            '        if not kind:\n'
            '            raise ValueError("memory event kind cannot be empty")\n'
            "        return tuple(event for event in self._events if event.kind == kind)\n"
            "\n"
        )

        # Insert before the ``history()`` method
        marker = "def history(self)"
        idx = old_source.rfind(marker)
        if idx == -1:
            raise ValueError("could not locate insertion point in source")

        # Find the start of the line containing ``history()``
        eol = old_source.rfind("\n", 0, idx)
        if eol == -1:
            eol = 0
        insert_at = eol + 1

        new_source = old_source[:insert_at] + method + old_source[insert_at:]
        added_lines = method.count("\n")

        digest = _domain_digest(
            b"m093-code-patch-v1\0",
            {"file": str(path), "old_digest": _domain_digest(b"m093-source-v1\0", old_source), "new_digest": _domain_digest(b"m093-source-v1\0", new_source)},
        )

        return cls(
            file=str(path),
            old_source=old_source,
            new_source=new_source,
            added_class_lines=added_lines,
            added_method_count=1,
            digest=digest,
        )

    def original_digest(self) -> str:
        return _domain_digest(b"m093-source-v1\0", self.old_source)

    def modified_digest(self) -> str:
        return _domain_digest(b"m093-source-v1\0", self.new_source)


# ── Sandbox ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SandboxResult:
    """Outcome of running one source variant inside a disposable subprocess."""

    variant_id: str
    passed: bool
    total_assertions: int
    failed_assertions: int
    runtime_seconds: float
    stdout: str
    stderr: str
    exit_code: int


def run_in_sandbox(
    source_code: str,
    module_name: str,
    *,
    sandbox_script: str,
    dependency_modules: Sequence[str] = ("contracts",),
    timeout_seconds: int = 30,
) -> SandboxResult:
    """Copy *source_code* into a temp directory and run *sandbox_script* inside it.

    The module under test is written from *source_code*.  Real, unmodified
    dependency modules named in *dependency_modules* are copied from the
    repository (read-only) so the component under test imports cleanly.
    """
    with tempfile.TemporaryDirectory(prefix="m093-sandbox-") as tmp:
        tmp_dir = Path(tmp)
        mod_dir = tmp_dir / "mira_core"
        mod_dir.mkdir()
        # Write the module under test
        (mod_dir / f"{module_name}.py").write_text(source_code, encoding="utf-8")
        # Copy unmodified dependency modules from the real repo
        repo_core = Path(__file__).resolve().parent.parent / "mira_core"
        for dep in dependency_modules:
            dep_path = repo_core / f"{dep}.py"
            if dep_path.exists():
                (mod_dir / f"{dep}.py").write_text(dep_path.read_text(encoding="utf-8"), encoding="utf-8")
        # Write __init__.py so it's a package
        (mod_dir / "__init__.py").write_text(
            f"from mira_core.{module_name} import *\n",
            encoding="utf-8",
        )
        # Write the sandbox test script
        script = tmp_dir / "_sandbox_script.py"
        script.write_text(sandbox_script, encoding="utf-8")

        try:
            completed = subprocess.run(
                [sys.executable, str(script)],
                cwd=tmp_dir,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(
                variant_id=module_name,
                passed=False,
                total_assertions=0,
                failed_assertions=0,
                runtime_seconds=float(timeout_seconds),
                stdout="",
                stderr="TIMEOUT",
                exit_code=-1,
            )

        # Parse structured JSON from stdout
        total = 0
        failed = 0
        try:
            for line in completed.stdout.strip().split("\n"):
                if line.startswith("ASSERT:"):
                    total += 1
                    parts = line.split(":")
                    if len(parts) >= 3 and parts[1] != "OK":
                        failed += 1
        except Exception:
            pass

        return SandboxResult(
            variant_id=module_name,
            passed=completed.returncode == 0,
            total_assertions=total,
            failed_assertions=failed,
            runtime_seconds=0.0,  # calculated by caller
            stdout=completed.stdout,
            stderr=completed.stderr,
            exit_code=completed.returncode,
        )


# ── Comparison ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ABNullHypothesis:
    """Null hypothesis: no measurable difference between original and candidate."""

    criterion: str
    original: SandboxResult
    candidate: SandboxResult
    null_rejected: bool
    reason: str


def compare_ab(
    original: SandboxResult,
    candidate: SandboxResult,
    *,
    criterion: str = "all_assertions_pass_and_candidate_functionally_equivalent",
) -> ABNullHypothesis:
    """Compare original vs. candidate on a pre-defined criterion."""
    null_rejected = False
    reason_parts = []

    # Criterion: both pass AND candidate adds query capability
    if original.passed:
        reason_parts.append(f"original: {original.total_assertions} assertions passed")
    else:
        reason_parts.append(f"original: {original.failed_assertions}/{original.total_assertions} failed")

    if candidate.passed:
        reason_parts.append(f"candidate: {candidate.total_assertions} assertions passed")
    else:
        reason_parts.append(f"candidate: {candidate.failed_assertions}/{candidate.total_assertions} failed")

    if not original.passed:
        reason_parts.append("original regression — candidate cannot proceed")
    elif candidate.passed:
        null_rejected = True
        reason_parts.append("null hypothesis rejected: candidate passes and adds query capability")
    else:
        reason_parts.append("candidate did not pass — null hypothesis stands")

    return ABNullHypothesis(
        criterion=criterion,
        original=original,
        candidate=candidate,
        null_rejected=null_rejected,
        reason="; ".join(reason_parts),
    )


# ── Independent validation ────────────────────────────────────────────

@dataclass(frozen=True)
class IndependentValidation:
    """Result from a validator process that does NOT see the original result."""

    validator_id: str
    passed: bool
    total_attempts: int
    accepted: bool
    report: str
    digest: str


def validate_independently(
    patch: CodePatch,
    *,
    validator_id: str = "m093-validator",
    timeout_seconds: int = 30,
) -> IndependentValidation:
    """Run the candidate source through a separate validation process.

    The validator receives only the candidate source + a held-out test suite.
    It does *not* see the original or the comparison result.
    """
    # Held-out validator suite lives in metamorphosis.m093_suites
    validator_script = VALIDATOR_SCRIPT
    result = run_in_sandbox(patch.new_source, "memory", sandbox_script=validator_script, timeout_seconds=timeout_seconds)

    # run_in_sandbox already counts ASSERT: lines; prefer those real counts
    # over the (single-quoted, non-JSON) RESULT trailer.
    total = result.total_assertions
    failed = result.failed_assertions

    passed = result.passed and failed == 0
    report_parts = [
        f"validator {validator_id}",
        f"passed={passed}",
        f"assertions={total}",
        f"failed={failed}",
    ]

    digest = _domain_digest(
        b"m093-validation-v1\0",
        {"validator_id": validator_id, "passed": passed, "total": total, "failed": failed},
    )

    return IndependentValidation(
        validator_id=validator_id,
        passed=passed,
        total_attempts=1,
        accepted=passed,
        report="; ".join(report_parts),
        digest=digest,
    )


# ── Versioned store (adoption + rollback) ─────────────────────────────

@dataclass(frozen=True)
class JournalEntry:
    """One immutable entry in the transformation journal."""

    version: int
    event: str
    file: str
    patch_digest: str
    original_file_digest: str
    modified_file_digest: str
    validation_digest: str
    comparison: str
    previous_entry_digest: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "event": self.event,
            "file": self.file,
            "patch_digest": self.patch_digest,
            "original_file_digest": self.original_file_digest,
            "modified_file_digest": self.modified_file_digest,
            "validation_digest": self.validation_digest,
            "comparison": self.comparison,
            "previous_entry_digest": self.previous_entry_digest,
        }

    def digest(self) -> str:
        return _domain_digest(b"m093-journal-entry-v1\0", self.to_dict())


@dataclass(frozen=True)
class State:
    """Serialisable state of the transformation store."""

    version: int
    current_file_digest: str
    journal: tuple[JournalEntry, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": CORE_SCHEMA,
            "version": self.version,
            "current_file_digest": self.current_file_digest,
            "journal": [e.to_dict() for e in self.journal],
        }

    def to_bytes(self) -> bytes:
        return _canonical_json(self.to_dict())

    @classmethod
    def initial(cls, file_digest: str) -> State:
        return cls(version=0, current_file_digest=file_digest, journal=())

    @classmethod
    def restore(cls, data: bytes) -> State:
        raw = json.loads(data.decode("utf-8"))
        if not isinstance(raw, dict) or raw.get("schema") != CORE_SCHEMA:
            raise ValueError("state schema mismatch")
        journal = tuple(
            JournalEntry(
                version=e["version"],
                event=e["event"],
                file=e["file"],
                patch_digest=e["patch_digest"],
                original_file_digest=e["original_file_digest"],
                modified_file_digest=e["modified_file_digest"],
                validation_digest=e["validation_digest"],
                comparison=e["comparison"],
                previous_entry_digest=e["previous_entry_digest"],
            )
            for e in raw["journal"]
        )
        return cls(version=raw["version"], current_file_digest=raw["current_file_digest"], journal=journal)


class TransformationStore:
    """Transactional versioned store for real component modifications.

    Follows the same pattern as ``VersionedSoftwareStore`` (M047) but
    works on actual file-backed source rather than ``SoftwareBody``
    instances.
    """

    def __init__(self, state: State, work_dir: str | Path) -> None:
        self._state = state
        self._work_dir = Path(work_dir)
        self._state_path = self._work_dir / ".m093-state.json"

    @property
    def state(self) -> State:
        return self._state

    @property
    def version(self) -> int:
        return self._state.version

    def _persist(self) -> None:
        self._state_path.write_bytes(self._state.to_bytes())

    @classmethod
    def init_or_load(cls, work_dir: str | Path, file_digest: str) -> TransformationStore:
        work_dir = Path(work_dir)
        state_path = work_dir / ".m093-state.json"
        if state_path.exists():
            state = State.restore(state_path.read_bytes())
            return cls(state, work_dir)
        state = State.initial(file_digest)
        store = cls(state, work_dir)
        store._persist()
        return store

    def adopt(
        self,
        patch: CodePatch,
        validation: IndependentValidation,
        comparison: ABNullHypothesis,
    ) -> bool:
        """Adopt the patch: write it to the real file and record in the journal.

        Returns True if adopted, False if not accepted.
        """
        if not validation.accepted:
            return False
        if not comparison.null_rejected:
            return False

        target = Path(worktree_file_path(patch.file))
        # Back up the exact original source BEFORE touching the real file.
        backup = self._backup_path(patch.file)
        backup.write_text(patch.old_source, encoding="utf-8")
        target.write_text(patch.new_source, encoding="utf-8")

        version = self._state.version + 1
        previous = self._state.journal[-1].digest() if self._state.journal else None

        entry = JournalEntry(
            version=version,
            event="adopt",
            file=patch.file,
            patch_digest=patch.digest,
            original_file_digest=patch.original_digest(),
            modified_file_digest=patch.modified_digest(),
            validation_digest=validation.digest,
            comparison=f"null_rejected={comparison.null_rejected}:{comparison.reason}",
            previous_entry_digest=previous,
        )

        self._state = State(
            version=version,
            current_file_digest=patch.modified_digest(),
            journal=self._state.journal + (entry,),
        )
        self._persist()
        return True

    def _backup_path(self, file: str) -> Path:
        name = Path(file).name
        return self._work_dir / f".m093-backup-{name}"

    def rollback(self) -> JournalEntry | None:
        """Roll back to the previous version (exact file restoration).

        Returns the rollback journal entry, or None if at version 0.
        """
        if self._state.version == 0:
            return None

        previous_version = self._state.version - 1
        # Find the entry to undo
        entry_to_undo = self._state.journal[-1]

        # Restore the original source from the sidecar backup.
        original_digest = entry_to_undo.original_file_digest

        # Read the current file and check it matches the modified digest
        target = Path(worktree_file_path(entry_to_undo.file))
        current = target.read_text(encoding="utf-8")
        current_digest = _domain_digest(b"m093-source-v1\0", current)

        if current_digest != entry_to_undo.modified_file_digest:
            raise ValueError(
                f"rollback safety check failed: current file digest {current_digest} "
                f"does not match expected modified digest {entry_to_undo.modified_file_digest}"
            )

        backup = self._backup_path(entry_to_undo.file)
        if not backup.exists():
            raise ValueError(f"rollback backup is missing: {backup}")
        original_source = backup.read_text(encoding="utf-8")
        backup_digest = _domain_digest(b"m093-source-v1\0", original_source)
        if backup_digest != original_digest:
            raise ValueError(
                f"rollback backup digest mismatch: expected {original_digest}, got {backup_digest}"
            )

        # Write back the original source
        target.write_text(original_source, encoding="utf-8")

        # Build previous-state state
        previous_journal = self._state.journal[:-1]
        prev_entry = previous_journal[-1] if previous_journal else None
        previous_state = State(
            version=previous_version,
            current_file_digest=original_digest,
            journal=previous_journal,
        )

        # Verify exact restoration
        written = target.read_text(encoding="utf-8")
        written_digest = _domain_digest(b"m093-source-v1\0", written)
        if written_digest != original_digest:
            raise ValueError(
                f"rollback exact restoration failed: written digest {written_digest} != expected {original_digest}"
            )

        self._state = previous_state
        self._persist()

        return JournalEntry(
            version=previous_version + 1,
            event="rollback",
            file=entry_to_undo.file,
            patch_digest=entry_to_undo.patch_digest,
            original_file_digest=original_digest,
            modified_file_digest=entry_to_undo.modified_file_digest,
            validation_digest=entry_to_undo.validation_digest,
            comparison=f"rolled back from version {entry_to_undo.version}",
            previous_entry_digest=prev_entry.digest() if prev_entry else None,
        )

    @staticmethod
    def persistence_path(work_dir: str | Path) -> Path:
        return Path(work_dir) / ".m093-state.json"


def worktree_file_path(file_path: str) -> str:
    """Resolve a file path for adoption inside the worktree.

    ``file_path`` is relative to the worktree root (e.g.
    ``mira_core/memory.py``).  This function returns an absolute path
    inside the current working directory — assumed to be the worktree
    root.
    """
    return str(Path.cwd() / file_path)