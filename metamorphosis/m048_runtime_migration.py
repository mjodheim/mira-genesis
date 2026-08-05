"""Public, strengthened facade for M048 native runtime migration."""
from __future__ import annotations

from typing import Mapping

import metamorphosis.m048_native_support as _support


def _render_qualified_allocation(policy: str) -> str:
    if policy not in {"plan_length", "double_plan_length"}:
        raise _support.NativeMigrationError(
            f"M048 compiler does not support final allocation policy {policy!r}"
        )
    expression = "Math.max(1,plan.steps.length)"
    if policy == "double_plan_length":
        expression = "Math.max(1,plan.steps.length*2)"
    return _support._js_header(
        "allocation", {"kind": "resource_allocator", "policy": policy}
    ) + f"export function allocate(ir,plan){{return {expression};}}\n"


def _qualified_native_checkpoint(state: Mapping[str, object]) -> dict[str, object]:
    """Checkpoint the journal key used by the accepted native state schema."""
    mapping = {
        "schema": "m048-native-checkpoint-v1",
        "version": state["version"],
        "body_digest": _support._native_body_digest(state["body"]),
        "patch_registry_digest": _support._digest(
            b"m048-native-patch-registry-v1\x00", state["patch_registry"]
        ),
        "journal_digest": _support._digest(
            b"m048-native-journal-v1\x00", state["native_journal"]
        ),
        "memory_digest": _support._digest(
            b"m048-native-memory-v1\x00", state["causal_memory"]
        ),
        "migration_digest": state["migration"]["digest"],
    }
    return {
        **mapping,
        "state_digest": _support._native_state_digest(state),
        "digest": _support._digest(b"m048-native-checkpoint-v1\x00", mapping),
    }


# Patch the compiler and checkpoint builder before importing the integrated
# lineage. These bounded compatibility corrections accept the exact M047
# allocation strategies and the journal key defined by the M048 state schema.
_support._render_allocation = _render_qualified_allocation
_support._native_checkpoint = _qualified_native_checkpoint

import metamorphosis.m048_native_lineage as _lineage  # noqa: E402

_original_audit = _lineage._audit_native_state


def _strengthened_audit(state: Mapping[str, object]) -> None:
    _original_audit(state)
    journal = state["native_journal"]
    registry = state["patch_registry"]
    native_records = [
        record
        for record in registry
        if isinstance(record, Mapping) and record.get("runtime") == "node-esm"
    ]
    if not native_records:
        return
    latest_record = native_records[-1]
    latest_entry = journal[-1]
    if latest_entry.get("patch_digest") != latest_record.get("record_digest"):
        raise _support.NativeMigrationError(
            "native journal no longer binds the latest patch record"
        )
    if latest_entry.get("validation_digest") != latest_record.get("validation_digest"):
        raise _support.NativeMigrationError(
            "native journal no longer binds independent validation"
        )
    if latest_entry.get("accepted_body_digest") != _support._native_body_digest(
        state["body"]
    ):
        raise _support.NativeMigrationError(
            "native journal no longer binds the accepted executable body"
        )
    if latest_record.get("candidate_body_digest") != _support._native_body_digest(
        state["body"]
    ):
        raise _support.NativeMigrationError(
            "native patch registry no longer binds the accepted executable body"
        )


_lineage._audit_native_state = _strengthened_audit

M048_PROTOCOL = _support.M048_PROTOCOL
M048Protocol = _support.M048Protocol
NativeMigrationError = _support.NativeMigrationError
M048Manifest = _lineage.M048Manifest
compile_m047_body_to_node = _support.compile_m047_body_to_node


def run_m048_native_runtime_migration(
    protocol: M048Protocol = M048_PROTOCOL,
) -> M048Manifest:
    """Run M048 while excluding volatile process identities from its manifest."""
    raw = _lineage.run_m048_native_runtime_migration(protocol)
    mapping = raw.to_dict()
    worker_pid = int(mapping.pop("native_migration_worker_pid"))
    mapping["native_migration_disposable_process"] = worker_pid > 0
    return M048Manifest(mapping)


__all__ = [
    "M048_PROTOCOL",
    "M048Manifest",
    "M048Protocol",
    "NativeMigrationError",
    "compile_m047_body_to_node",
    "run_m048_native_runtime_migration",
]
