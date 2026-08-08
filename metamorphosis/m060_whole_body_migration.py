"""M060: the whole body crosses, on a path the lineage built into a substrate it discovered.

Five experiments each removed something the previous one was handed, and each narrowed what
crossed. M048 moved nine modules but was given a compiler and an instruction. M056 through M059
removed the compiler, the operation list and the instruction — and moved four arithmetic tools,
leaving seven shell modules in JavaScript. Breadth and autonomy had never met.

The obstacle was never conceptual. The shell tokenises text, compares strings against a table,
builds a tree and walks it: none of that survives a translation that only knows how to emit
`f64.add`. WebAssembly has no strings, no objects and no allocator, so the shell had to be
rewritten against linear memory — bytes at addresses, records at fixed strides, recursion through
the call stack.

That is what `m060_body_compiler` emits. This module is the experiment around it: the lineage
scans the substrate, establishes that the whole body compiles into it, verifies every inherited
capability there, and keeps nothing in the runtime it came from.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Mapping, Sequence

import metamorphosis.m048_runtime_migration as _m048_facade  # applies the qualified corrections
import metamorphosis.m048_native_lineage as _m048


class M060Error(ValueError):
    """Raised when an M060 artifact violates the bounded protocol."""


def _digest(domain: bytes, value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(domain + payload).hexdigest()


RESPONSE_SCHEMA = "m060-node-response-v1"

#: The seven shell modules M056 through M059 never moved, and the four tools they did.
SHELL_MODULES = ("allocation", "critique", "execution", "interpretation", "orchestration",
                 "planning", "selection")
TOOL_MODULES = ("tool_core", "tool_max", "tool_mean")

#: Where the caller writes a request, matching the compiled body's fixed layout.
REQUEST_PTR = 0
REQUEST_LEN_PTR = 256


@dataclass(frozen=True)
class M060Protocol:
    source_runtime: str = "node-esm"
    target_runtime: str = "webassembly"
    node_timeout_seconds: float = 120.0
    schema: str = "m060-whole-body-migration-protocol-v1"

    def __post_init__(self) -> None:
        if self.source_runtime != "node-esm" or self.target_runtime != "webassembly":
            raise M060Error("M060 fixes Node ESM to WebAssembly for the whole body")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "source_runtime": self.source_runtime,
            "target_runtime": self.target_runtime,
            "shell_modules": list(SHELL_MODULES),
            "tool_modules": list(TOOL_MODULES),
        }

    def digest(self) -> str:
        return _digest(b"m060-whole-body-migration-protocol-v1\0", self.to_dict())


M060_PROTOCOL = M060Protocol()


@dataclass(frozen=True)
class InheritedLineage:
    state: Mapping[str, object]
    retained: tuple[object, ...]
    source_retained_count: int

    def body(self) -> Mapping[str, object]:
        return self.state["body"]

    def version(self) -> int:
        return int(self.state["version"])

    def module_names(self) -> tuple[str, ...]:
        return tuple(sorted(str(module["name"]) for module in self.body()["modules"]))


def reconstruct_m048_version_eight() -> InheritedLineage:
    """Re-derive the accepted M048 state rather than assert it."""
    snapshot, memory, retained, _artifacts = _m048._reconstruct_m047()
    migrated = _m048._build_migrated_state(snapshot, memory, _m048.M048_PROTOCOL)
    tasks = _m048._task_cases()
    public, hidden = tasks["maximum"]
    proposal = _m048._propose(migrated["body"], "m048_native_maximum", public, _m048.M048_PROTOCOL)
    selection = _m048._validate(
        migrated["body"], proposal, retained, public, hidden,
        ("interpretation", "selection", "tool_max"), _m048.M048_PROTOCOL,
    )
    accepted, adoption = _m048._adopt_native_candidate(migrated, "m048_native_maximum", selection)
    if not adoption.get("adopted") or accepted.get("version") != 8:
        raise M060Error("could not reconstruct the accepted M048 version-eight state")
    return InheritedLineage(
        state=accepted,
        retained=tuple(retained) + tuple(public) + tuple(hidden),
        source_retained_count=len(retained),
    )


def _runtime_script() -> Path:
    return Path(__file__).resolve().with_name("m060_wasm_runtime.mjs")


def _node_call(mode: str, request: Mapping[str, object], protocol: M060Protocol) -> Mapping[str, object]:
    payload = json.dumps(request, sort_keys=True, separators=(",", ":")).encode("utf-8")
    try:
        completed = subprocess.run(
            ["node", str(_runtime_script()), mode],
            input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=protocol.node_timeout_seconds, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise M060Error(f"Node runtime unavailable or timed out: {type(exc).__name__}") from exc
    try:
        response = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise M060Error("Node runtime returned malformed output") from exc
    if completed.returncode != 0 or not isinstance(response, Mapping) or response.get("fatal_error"):
        detail = response.get("fatal_error") if isinstance(response, Mapping) else completed.stderr.decode("utf-8", "replace")
        raise M060Error(f"Node runtime failed: {detail}")
    if response.get("schema") != RESPONSE_SCHEMA or response.get("mode") != mode:
        raise M060Error("Node runtime response identity mismatch")
    result = response.get("result")
    if not isinstance(result, Mapping):
        raise M060Error("Node runtime result is not an object")
    return result


def execute_in_wasm(
    module: bytes, cases: Sequence[object], protocol: M060Protocol = M060_PROTOCOL,
) -> Mapping[str, object]:
    """Run the retained bank against the migrated body, with no JavaScript in the semantic path."""
    return _node_call("execute", {
        "wasm": base64.b64encode(module).decode("ascii"),
        "cases": _m048._case_dicts(cases),
    }, protocol)


def inspect_module(module: bytes, protocol: M060Protocol = M060_PROTOCOL) -> Mapping[str, object]:
    """Report what the emitted module declares: imports it cannot have, exports it must."""
    return _node_call("inspect", {"wasm": base64.b64encode(module).decode("ascii")}, protocol)


@dataclass
class M060Manifest:
    mapping: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return dict(self.mapping)

    def digest(self) -> str:
        return _digest(b"m060-whole-body-migration-manifest-v1\0", self.mapping)


def run_m060_whole_body_migration(protocol: M060Protocol = M060_PROTOCOL) -> M060Manifest:
    """The whole body crosses, and every inherited capability is executed on the other side."""
    from metamorphosis.m058_discovered_migration import SCAN_PAIRS, scan_instruction_space
    from metamorphosis.m058_instruction_discovery import discovered_from
    from metamorphosis.m060_body_compiler import AUTHORED_ARITHMETIC, arithmetic_opcodes, compile_body

    lineage = reconstruct_m048_version_eight()
    inherited_modules = lineage.module_names()
    missing = [name for name in SHELL_MODULES + TOOL_MODULES if name not in inherited_modules]
    if missing:
        raise M060Error(f"the inherited body is missing modules: {missing}")

    # The arithmetic is resolved by M058's scan rather than written here. The structural
    # instructions around it are not, and the manifest records both halves.
    scan = scan_instruction_space()
    observations = {item.name: list(item.observations) for item in discovered_from(scan)}
    resolved = arithmetic_opcodes(observations, SCAN_PAIRS)
    module = compile_body(resolved)
    inspected = inspect_module(module, protocol)
    if int(inspected["import_count"]) != 0:
        raise M060Error("the migrated body declares imports and could delegate its semantics")

    executed = execute_in_wasm(module, lineage.retained, protocol)
    if not executed["all_passed"]:
        failures = [item for item in executed["case_results"] if not item["passed"]][:5]
        raise M060Error(f"the whole-body migration lost a capability: {failures}")

    replay = compile_body(resolved)
    mapping = {
        "schema": "m060-whole-body-migration-manifest-v1",
        "status": "development_pending_qualification",
        "protocol_digest": protocol.digest(),
        "inherited_version": lineage.version(),
        "inherited_retained_case_count": len(lineage.retained),
        "pre_first_migration_case_count": lineage.source_retained_count,
        "inherited_module_count": len(inherited_modules),
        "shell_modules_migrated": list(SHELL_MODULES),
        "tool_modules_migrated": list(TOOL_MODULES),
        "modules_left_in_javascript": 0,
        "module_bytes": len(module),
        "module_digest": _digest(b"m060-wasm-module-v1\0", list(module)),
        "opcode_space_scanned": int(scan["scanned"]),
        "operations_discovered": len(observations),
        "arithmetic_opcodes_discovered": {label: hex(code) for label, code in sorted(resolved.items())},
        "arithmetic_opcodes_authored": False,
        "arithmetic_matches_authored_fallback": resolved == AUTHORED_ARITHMETIC,
        "structural_instructions_authored": True,
        "declared_imports": int(inspected["import_count"]),
        "exported_functions": sorted(inspected["exports"]),
        "retained_passed": int(executed["passed_count"]),
        "retained_total": len(lineage.retained),
        "all_retained_passed": bool(executed["all_passed"]),
        "semantic_delegation_to_javascript": False,
        "compiler_is_repository_code": True,
        "precompiled_bytes_embedded": False,
        "arbitrary_code_generation": False,
        "network_authority": False,
        "repository_authority": False,
        "credential_authority": False,
        "deployment_authority": False,
        "canonical": False,
        "replay_identical": module == replay,
    }
    return M060Manifest(mapping)


__all__ = [
    "InheritedLineage", "M060Error", "M060Manifest", "M060Protocol", "M060_PROTOCOL",
    "REQUEST_LEN_PTR", "REQUEST_PTR", "SHELL_MODULES", "TOOL_MODULES", "execute_in_wasm",
    "inspect_module", "reconstruct_m048_version_eight", "run_m060_whole_body_migration",
]
