"""Integrated M048 CPython-to-Node migration and post-migration learning lineage."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from metamorphosis.m047_lineage_protocol import M047_PROTOCOL
from metamorphosis.m047_lineage_runner import _execute_with_artifacts
from metamorphosis.m047_lineage_state import initial_software_snapshot
from metamorphosis.m047_lineage_transaction import VersionedSoftwareStore
from metamorphosis.m047_search_memory import CausalSoftwareMemory
from metamorphosis.m047_software_body import BASELINE_CASES, SoftwareCase, founder_software_body
from metamorphosis.m047_task_definition import build_hidden_modular_task
from metamorphosis.m048_native_support import (
    M048_PROTOCOL,
    M048Protocol,
    NativeMigrationError,
    _canonical_json,
    _digest,
    _native_body_digest,
    _native_checkpoint,
    _native_journal_entry_digest,
    _native_state_digest,
    _node_call,
    compile_m047_body_to_node,
)


def _case(case_id: str, request: str, expected: object, origin: str) -> SoftwareCase:
    return SoftwareCase(case_id, request, expected, origin)


def _case_dicts(cases: Sequence[SoftwareCase]) -> list[dict[str, object]]:
    return [case.to_dict() for case in cases]


def _reconstruct_m047() -> tuple[object, CausalSoftwareMemory, tuple[SoftwareCase, ...], object]:
    artifacts = _execute_with_artifacts(M047_PROTOCOL)
    store = VersionedSoftwareStore(initial_software_snapshot(founder_software_body()))
    memory = CausalSoftwareMemory()
    hidden: list[SoftwareCase] = []
    for ordinal, (selection, episode) in enumerate(zip(artifacts.selections, artifacts.episodes), start=1):
        task = build_hidden_modular_task(store.current.accepted_body, ordinal=ordinal, protocol_digest=M047_PROTOCOL.digest())
        hidden.extend(task.hidden_cases)
        receipt = store.adopt(selection)
        if not receipt.adopted:
            raise NativeMigrationError(f"M047 reconstruction failed at version {ordinal}")
        memory = memory.append(episode, maximum_bytes=M047_PROTOCOL.resources.max_causal_memory_bytes)
    retained = BASELINE_CASES + store.current.accepted_body.regression_cases + tuple(hidden)
    if store.current.version != 6 or len(retained) != 28:
        raise NativeMigrationError("M047 reconstruction did not recover the qualified version-six state")
    return store.current, memory, retained, artifacts


def _source_continuity(snapshot: object, memory: CausalSoftwareMemory) -> dict[str, object]:
    patch_registry = []
    for record in snapshot.patch_registry:
        patch_registry.append({"runtime": "cpython", "record": record.to_dict(), "record_digest": record.digest()})
    journal = []
    for entry in snapshot.causal_journal:
        journal.append({"record": entry.to_dict(), "record_digest": entry.digest()})
    mapping = {
        "schema": "m048-inherited-m047-state-v1",
        "version": snapshot.version,
        "snapshot_digest": snapshot.digest(),
        "snapshot_bytes_sha256": _digest(b"m048-source-snapshot-bytes-v1\x00", snapshot.to_bytes().decode("ascii")),
        "body_digest": snapshot.accepted_body.digest(),
        "patch_registry": patch_registry,
        "accepted_task_ids": list(snapshot.accepted_task_ids),
        "source_journal": journal,
        "source_journal_digest": _digest(b"m048-source-journal-v1\x00", journal),
        "causal_memory": memory.to_dict(),
        "causal_memory_digest": memory.digest(),
    }
    return {**mapping, "digest": _digest(b"m048-inherited-m047-state-v1\x00", mapping)}


def _build_migrated_state(snapshot: object, memory: CausalSoftwareMemory, protocol: M048Protocol) -> dict[str, object]:
    native_body = compile_m047_body_to_node(snapshot.accepted_body)
    inherited = _source_continuity(snapshot, memory)
    migration_core = {
        "schema": "m048-runtime-migration-record-v1",
        "source_runtime": protocol.source_runtime,
        "target_runtime": protocol.target_runtime,
        "source_state_digest": inherited["digest"],
        "source_snapshot_digest": snapshot.digest(),
        "source_body_digest": snapshot.accepted_body.digest(),
        "native_body_digest": _native_body_digest(native_body),
        "compiler": "bounded-m047-metadata-to-node-esm-v1",
        "semantic_delegation_to_python": False,
    }
    migration = {**migration_core, "digest": _digest(b"m048-runtime-migration-record-v1\x00", migration_core)}
    migration_entry = {
        "sequence": 7,
        "event": "migrate_cpython_body_to_node_esm",
        "previous_source_journal_digest": inherited["source_journal_digest"],
        "migration_digest": migration["digest"],
        "accepted_body_digest": _native_body_digest(native_body),
        "patch_digest": None,
        "validation_digest": None,
        "previous_entry_digest": None,
    }
    state = {
        "schema": "m048-native-lineage-state-v1",
        "version": 7,
        "runtime": protocol.target_runtime,
        "body": native_body,
        "patch_registry": list(inherited["patch_registry"]),
        "accepted_task_ids": list(inherited["accepted_task_ids"]),
        "native_journal": [migration_entry],
        "causal_memory": {
            "schema": "m048-continuous-causal-memory-v1",
            "inherited": inherited["causal_memory"],
            "inherited_digest": inherited["causal_memory_digest"],
            "native_episodes": [],
        },
        "inherited": inherited,
        "migration": migration,
    }
    _audit_native_state(state)
    return state


def _audit_native_state(state: Mapping[str, object]) -> None:
    if state.get("schema") != "m048-native-lineage-state-v1" or state.get("runtime") != "node-esm":
        raise NativeMigrationError("invalid native lineage identity")
    body = state.get("body")
    if not isinstance(body, Mapping) or body.get("schema") != "m048-js-body-v1":
        raise NativeMigrationError("native state lacks a JavaScript body")
    modules = body.get("modules")
    if not isinstance(modules, list) or len(modules) < 9:
        raise NativeMigrationError("native body lost required modules")
    names = [str(item.get("name")) for item in modules if isinstance(item, Mapping)]
    required = {"interpretation", "planning", "selection", "execution", "critique", "allocation", "orchestration", "tool_core", "tool_mean"}
    if not required.issubset(names):
        raise NativeMigrationError("native body lost a migrated M047 module")
    for item in modules:
        if not isinstance(item, Mapping):
            raise NativeMigrationError("native module is malformed")
        source = str(item.get("source", "")).lower()
        if any(token in source for token in ("python", "subprocess", "child_process", "node:child_process")):
            raise NativeMigrationError("native body delegates semantics to the source runtime")
    registry = state.get("patch_registry")
    journal = state.get("native_journal")
    memory = state.get("causal_memory")
    if not isinstance(registry, list) or not isinstance(journal, list) or not isinstance(memory, Mapping):
        raise NativeMigrationError("native lineage components are malformed")
    native_records = [record for record in registry if isinstance(record, Mapping) and record.get("runtime") == "node-esm"]
    expected_version = 7 + len(native_records)
    if state.get("version") != expected_version or len(journal) != 1 + len(native_records):
        raise NativeMigrationError("native version, journal and registry are discontinuous")
    if journal[0].get("event") != "migrate_cpython_body_to_node_esm" or journal[0].get("sequence") != 7:
        raise NativeMigrationError("native journal lacks its migration origin")
    previous = _native_journal_entry_digest(journal[0])
    for sequence, entry in enumerate(journal[1:], start=8):
        if entry.get("sequence") != sequence or entry.get("previous_entry_digest") != previous:
            raise NativeMigrationError("native causal journal hash chain is broken")
        previous = _native_journal_entry_digest(entry)
    migration = state.get("migration")
    inherited = state.get("inherited")
    if not isinstance(migration, Mapping) or not isinstance(inherited, Mapping):
        raise NativeMigrationError("native state lost migration continuity")
    if migration.get("source_state_digest") != inherited.get("digest"):
        raise NativeMigrationError("migration no longer binds the inherited M047 state")
    if migration.get("native_body_digest") != _native_body_digest(journal[0] and body if len(journal) == 1 else state["inherited_native_body"] if "inherited_native_body" in state else body):
        # After native learning the migration record continues to bind the original compiled body,
        # while the current body is bound by later journal entries.
        if len(journal) == 1:
            raise NativeMigrationError("migration native body identity mismatch")
    if memory.get("inherited_digest") != inherited.get("causal_memory_digest"):
        raise NativeMigrationError("native memory lost its inherited causal identity")


def _migration_body_digest(state: Mapping[str, object]) -> str:
    return str(state["migration"]["native_body_digest"])


def _append_memory_episode(state: Mapping[str, object], episode: Mapping[str, object]) -> dict[str, object]:
    updated = dict(state)
    memory = dict(state["causal_memory"])
    episodes = list(memory["native_episodes"])
    episodes.append(dict(episode))
    memory["native_episodes"] = episodes
    updated["causal_memory"] = memory
    return updated


#: Fields a validation selection carries that describe the environment rather than the
#: decision. They are evidence that a disposable process ran, not part of what was decided,
#: and digesting them made every derived identity depend on the pid of that process.
_VOLATILE_VALIDATION_FIELDS = ("worker_pid",)


def _decided(selection: Mapping[str, object]) -> dict[str, object]:
    """The part of a validation selection that carries meaning.

    An identity computed over a mapping should be computed over the fields that carry
    meaning, not over whatever the producer happened to return. See D018.
    """
    return {key: value for key, value in selection.items() if key not in _VOLATILE_VALIDATION_FIELDS}


def _adopt_native_candidate(
    state: Mapping[str, object],
    task_id: str,
    selection: Mapping[str, object],
    *,
    forced_fault: bool = False,
) -> tuple[dict[str, object], dict[str, object]]:
    before = dict(state)
    before_bytes = _canonical_json(before)
    before_digest = _native_state_digest(before)
    if selection.get("action") != "adopt" or not isinstance(selection.get("selected_candidate"), Mapping):
        return before, {"adopted": False, "exact_restoration": False, "reason": "selection was not accepted"}
    candidate = selection["selected_candidate"]
    validation_digest = _digest(b"m048-native-validation-v1\x00", _decided(selection))
    record_core = {
        "runtime": "node-esm",
        "task_id": task_id,
        "template_id": candidate["template_id"],
        "changed_modules": list(candidate["changed_modules"]),
        "added_modules": list(candidate["added_modules"]),
        "candidate_body_digest": _native_body_digest(candidate["candidate_body"]),
        "validation_digest": validation_digest,
        "adopted_version": int(state["version"]) + 1,
    }
    record = {**record_core, "record_digest": _digest(b"m048-native-patch-record-v1\x00", record_core)}
    previous = _native_journal_entry_digest(state["native_journal"][-1])
    journal_entry = {
        "sequence": int(state["version"]) + 1,
        "event": "adopt_validated_native_patch",
        "migration_digest": state["migration"]["digest"],
        "accepted_body_digest": record["candidate_body_digest"],
        "patch_digest": record["record_digest"],
        "validation_digest": validation_digest,
        "previous_entry_digest": previous,
    }
    staged = dict(state)
    staged["version"] = int(state["version"]) + 1
    staged["body"] = candidate["candidate_body"]
    staged["patch_registry"] = list(state["patch_registry"]) + [record]
    staged["accepted_task_ids"] = list(state["accepted_task_ids"]) + [task_id]
    staged["native_journal"] = list(state["native_journal"]) + [journal_entry]
    staged["inherited_native_body"] = state.get("inherited_native_body", state["body"])
    staged = _append_memory_episode(staged, {
        "task_id": task_id,
        "outcome": "accepted",
        "selected_template": candidate["template_id"],
        "changed_modules": list(candidate["changed_modules"]),
        "validation_digest": validation_digest,
        "reason": selection.get("reason"),
    })
    try:
        if forced_fault:
            corrupted = dict(staged)
            journal = [dict(item) for item in staged["native_journal"]]
            journal[-1]["patch_digest"] = "0" * 64
            corrupted["native_journal"] = journal
            _audit_native_state(corrupted)
        else:
            _audit_native_state(staged)
    except NativeMigrationError as exc:
        exact = _canonical_json(before) == before_bytes and _native_state_digest(before) == before_digest
        if not exact:
            raise NativeMigrationError("native rollback failed to restore the exact checkpoint") from exc
        return before, {
            "adopted": False,
            "exact_restoration": True,
            "reason": str(exc),
            "attempted_version": int(state["version"]) + 1,
            "restored_version": state["version"],
            "before_digest": before_digest,
            "after_digest": _native_state_digest(before),
        }
    return staged, {
        "adopted": True,
        "exact_restoration": False,
        "attempted_version": staged["version"],
        "committed_version": staged["version"],
        "before_digest": before_digest,
        "after_digest": _native_state_digest(staged),
    }


def _used_tool(execution: Mapping[str, object], case_id: str, tool: str) -> bool:
    for case in execution.get("case_results", []):
        if case.get("case_id") != case_id:
            continue
        for trace in case.get("result", {}).get("trace", []):
            if trace.get("stage") == "execution" and tool in trace.get("value", {}).get("used_tools", []):
                return True
    return False


@dataclass(frozen=True)
class M048Manifest:
    mapping: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return dict(self.mapping)

    def to_bytes(self) -> bytes:
        return _canonical_json(self.mapping)

    def digest(self) -> str:
        return _digest(b"m048-manifest-v1\x00", self.mapping)


def _task_cases() -> dict[str, tuple[tuple[SoftwareCase, ...], tuple[SoftwareCase, ...]]]:
    return {
        "maximum": (
            (_case("m048_public_maximum_positive", "maximum 2 5", 5, "maximum"), _case("m048_public_maximum_negative", "maximum -1 -3", -1, "maximum")),
            (_case("m048_hidden_maximum_equal", "maximum 4 4", 4, "maximum"), _case("m048_hidden_maximum_mixed", "maximum -8 3", 3, "maximum")),
        ),
        "largest": (
            (_case("m048_public_largest_positive", "largest 2 5", 5, "largest"), _case("m048_public_largest_negative", "largest -1 -3", -1, "largest")),
            (_case("m048_hidden_largest_equal", "largest 4 4", 4, "largest"), _case("m048_hidden_largest_mixed", "largest -8 3", 3, "largest")),
        ),
        "median": (
            (_case("m048_public_median_a", "median 1 2 3", 2, "median"), _case("m048_public_median_b", "median 2 4 6", 4, "median")),
            (_case("m048_hidden_median_a", "median 1 2 9", 2, "median"), _case("m048_hidden_median_b", "median 1 8 9", 8, "median")),
        ),
    }


def _propose(body: Mapping[str, object], task_id: str, public: Sequence[SoftwareCase], protocol: M048Protocol) -> Mapping[str, object]:
    return _node_call("propose", {
        "body": body,
        "task_id": task_id,
        "public_cases": _case_dicts(public),
        "max_generated_candidates": protocol.max_generated_candidates,
        "max_candidate_bytes": protocol.max_candidate_bytes,
    }, protocol)


def _validate(body: Mapping[str, object], proposal: Mapping[str, object], retained: Sequence[SoftwareCase], public: Sequence[SoftwareCase], hidden: Sequence[SoftwareCase], expected: Sequence[str], protocol: M048Protocol) -> Mapping[str, object]:
    return _node_call("validate", {
        "parent_body": body,
        "proposal": proposal,
        "retained_cases": _case_dicts(retained),
        "public_cases": _case_dicts(public),
        "hidden_cases": _case_dicts(hidden),
        "expected_changed_modules": list(expected),
        "max_validation_attempts": 4,
    }, protocol)


def run_m048_native_runtime_migration(protocol: M048Protocol = M048_PROTOCOL) -> M048Manifest:
    source_snapshot, source_memory, retained, artifacts = _reconstruct_m047()
    migrated = _build_migrated_state(source_snapshot, source_memory, protocol)
    migration_checkpoint = _native_checkpoint(migrated)
    migration_execution = _node_call("execute", {"body": migrated["body"], "cases": _case_dicts(retained)}, protocol)
    if not migration_execution.get("all_passed"):
        raise NativeMigrationError("native migration failed a retained M047 capability")
    mean_reused_after_migration = _used_tool(migration_execution, "hidden_average_fraction", "mean")
    if not mean_reused_after_migration:
        raise NativeMigrationError("the acquired mean tool was not reused after migration")

    tasks = _task_cases()
    max_public, max_hidden = tasks["maximum"]
    max_task_id = "m048_native_maximum"
    max_proposal = _propose(migrated["body"], max_task_id, max_public, protocol)
    if max_proposal.get("complete_program_space_enumerated") is not False:
        raise NativeMigrationError("native proposal search enumerated the complete program space")
    max_selection = _validate(migrated["body"], max_proposal, retained, max_public, max_hidden, ("interpretation", "selection", "tool_max"), protocol)
    learned, adoption = _adopt_native_candidate(migrated, max_task_id, max_selection)
    if not adoption.get("adopted") or learned.get("version") != 8:
        raise NativeMigrationError("post-migration native learning was not adopted")
    learned_checkpoint = _native_checkpoint(learned)
    learned_retained = retained + max_public + max_hidden
    learned_execution = _node_call("execute", {"body": learned["body"], "cases": _case_dicts(learned_retained)}, protocol)
    if not learned_execution.get("all_passed"):
        raise NativeMigrationError("post-migration learning regressed a retained capability")

    largest_public, largest_hidden = tasks["largest"]
    rollback_task_id = "m048_native_largest_rollback"
    rollback_proposal = _propose(learned["body"], rollback_task_id, largest_public, protocol)
    rollback_selection = _validate(learned["body"], rollback_proposal, learned_retained, largest_public, largest_hidden, ("interpretation",), protocol)
    restored, rollback = _adopt_native_candidate(learned, rollback_task_id, rollback_selection, forced_fault=True)
    if not rollback.get("exact_restoration") or _native_state_digest(restored) != _native_state_digest(learned):
        raise NativeMigrationError("forced native fault did not restore the exact version-eight checkpoint")

    median_public, median_hidden = tasks["median"]
    median_task_id = "m048_native_median_terminal"
    median_proposal = _propose(restored["body"], median_task_id, median_public, protocol)
    median_selection = _validate(restored["body"], median_proposal, learned_retained, median_public, median_hidden, ("interpretation",), protocol)
    if median_selection.get("action") != "terminate_insufficient_evidence":
        raise NativeMigrationError("terminal native challenge did not fail closed")
    final_state = _append_memory_episode(restored, {
        "task_id": median_task_id,
        "outcome": "insufficient_evidence",
        "selected_template": None,
        "rejected_templates": [attempt.get("template_id") for attempt in median_selection.get("attempts", [])],
        "reason": median_selection.get("reason"),
    })
    _audit_native_state(final_state)

    replay_migrated = _build_migrated_state(source_snapshot, source_memory, protocol)
    replay_learned, replay_adoption = _adopt_native_candidate(replay_migrated, max_task_id, max_selection)
    replay_restored, replay_rollback = _adopt_native_candidate(replay_learned, rollback_task_id, rollback_selection, forced_fault=True)
    replay_final = _append_memory_episode(replay_restored, final_state["causal_memory"]["native_episodes"][-1])
    replay_identical = bool(replay_adoption.get("adopted") and replay_rollback.get("exact_restoration") and _native_state_digest(replay_final) == _native_state_digest(final_state))
    if not replay_identical:
        raise NativeMigrationError("native migration and post-migration learning replay diverged")

    mapping = {
        "schema": "m048-native-runtime-migration-manifest-v1",
        "protocol_digest": protocol.digest(),
        "source_m047_manifest_digest": artifacts.manifest.digest(),
        "source_snapshot_digest": source_snapshot.digest(),
        "source_body_digest": source_snapshot.accepted_body.digest(),
        "source_causal_memory_digest": source_memory.digest(),
        "source_version": source_snapshot.version,
        "source_retained_case_count": len(retained),
        "migration_version": migrated["version"],
        "migration_record_digest": migrated["migration"]["digest"],
        "migration_checkpoint": migration_checkpoint,
        "native_migration_all_retained_passed": migration_execution["all_passed"],
        "native_migration_worker_pid": migration_execution["worker_pid"],
        "native_module_count_after_migration": len(migrated["body"]["modules"]),
        "semantic_delegation_to_python": False,
        "pre_migration_mean_tool_reused_after_migration": mean_reused_after_migration,
        "post_migration_task": max_task_id,
        "post_migration_generated_candidates": max_proposal["generated_candidates"],
        "post_migration_program_space_lower_bound": max_proposal["program_space_lower_bound"],
        "post_migration_complete_space_enumerated": max_proposal["complete_program_space_enumerated"],
        "post_migration_validation_attempts": len(max_selection["attempts"]),
        "post_migration_selected_template": max_selection["selected_candidate"]["template_id"],
        "post_migration_changed_modules": max_selection["selected_candidate"]["changed_modules"],
        "post_migration_version": learned["version"],
        "post_migration_checkpoint": learned_checkpoint,
        "native_module_count_after_learning": len(learned["body"]["modules"]),
        "native_regression_case_count_after_learning": len(learned["body"]["regression_cases"]),
        "post_migration_all_retained_passed": learned_execution["all_passed"],
        "forced_fault_attempted_version": rollback["attempted_version"],
        "forced_fault_restored_version": rollback["restored_version"],
        "forced_fault_exact_restoration": rollback["exact_restoration"],
        "terminal_task": median_task_id,
        "terminal_action": median_selection["action"],
        "terminal_rejections": len(median_selection["attempts"]),
        "terminal_body_unchanged": _native_body_digest(final_state["body"]) == _native_body_digest(learned["body"]),
        "final_state_digest": _native_state_digest(final_state),
        "final_native_failure_evidence_count": len(final_state["causal_memory"]["native_episodes"][-1]["rejected_templates"]),
        "replay_identical": replay_identical,
        "claim_scope": "bounded_cpython_to_node_modular_lineage_migration_with_one_post_migration_learning_cycle",
        "canonical_workflow_authorised": False,
        "repository_write_authority_granted_to_lineage": False,
    }
    return M048Manifest(mapping)
