"""M058: migrate on an instruction set the lineage discovered for itself.

M057 removed the authored compiler and kept an authored list of six operations. Its result named
what remained:

    The set of available operations remains authored by a human. What the lineage discovers is
    what they do and how to build its tools from them.

M058 removes the list. The lineage is told only the shape it needs — two `f64` in, one out — and
scans the whole single-byte opcode space, asking the substrate which candidates are programs at
all. Validation answers; a byte that is not an operation refuses to compile, and the refusal is
the information.
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
from metamorphosis.m056_second_migration import reconstruct_m048_version_eight
from metamorphosis.m056_wasm_compiler import declared_tools
from metamorphosis.m058_instruction_discovery import (
    OPCODE_SPACE, DiscoveredOperation, M058Error, atoms_for, discovered_from, emit_tool,
    expression_space_size, load_expression, operations_module, scan_requests,
)


def _digest(domain: bytes, value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(domain + payload).hexdigest()


RESPONSE_SCHEMA = "m058-node-response-v1"

SCAN_PAIRS: tuple[tuple[float, float], ...] = ((6.0, 3.0), (2.0, 5.0), (-4.0, 7.0), (3.0, 3.0))
OBSERVATION_ARGUMENTS: dict[int, tuple[tuple[float, ...], ...]] = {
    2: ((1.0, 2.0), (6.0, 3.0), (-4.0, 7.0), (5.0, 5.0), (0.0, -8.0)),
    3: ((1.0, 2.0, 4.0), (6.0, 3.0, 9.0), (-4.0, 7.0, 0.0), (5.0, -5.0, 10.0), (2.0, 2.0, 2.0)),
}
HIDDEN_ARGUMENTS: dict[int, tuple[tuple[float, ...], ...]] = {
    2: ((9.0, -1.0), (-7.0, -7.0), (12.0, 4.0)),
    3: ((9.0, 1.0, 2.0), (-3.0, -3.0, -3.0), (100.0, 0.0, 50.0)),
}

#: What M057 was handed. Kept only so the result can report what discovery added.
M057_AUTHORED_OPCODES: tuple[int, ...] = (0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5)


@dataclass(frozen=True)
class M058Protocol:
    max_expression_size: int = 7
    synthesis_budget: int = 200_000
    node_timeout_seconds: float = 180.0
    schema: str = "m058-discovered-migration-protocol-v1"

    def __post_init__(self) -> None:
        if self.max_expression_size != 7:
            raise M058Error("M058 fixes the maximum expression size at seven nodes")
        if self.synthesis_budget != 200_000:
            raise M058Error("M058 synthesis budget is frozen")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "max_expression_size": self.max_expression_size,
            "synthesis_budget": self.synthesis_budget,
            "opcode_space": len(OPCODE_SPACE),
            "scan_pairs": [list(pair) for pair in SCAN_PAIRS],
        }

    def digest(self) -> str:
        return _digest(b"m058-discovered-migration-protocol-v1\0", self.to_dict())


M058_PROTOCOL = M058Protocol()


def _runtime_script() -> Path:
    return Path(__file__).resolve().with_name("m058_wasm_runtime.mjs")


def _node_call(mode: str, request: Mapping[str, object], protocol: M058Protocol) -> Mapping[str, object]:
    payload = json.dumps(request, sort_keys=True, separators=(",", ":")).encode("utf-8")
    try:
        completed = subprocess.run(
            ["node", str(_runtime_script()), mode],
            input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=protocol.node_timeout_seconds, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise M058Error(f"Node runtime unavailable or timed out: {type(exc).__name__}") from exc
    try:
        response = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise M058Error("Node runtime returned malformed output") from exc
    if completed.returncode != 0 or not isinstance(response, Mapping) or response.get("fatal_error"):
        detail = response.get("fatal_error") if isinstance(response, Mapping) else completed.stderr.decode("utf-8", "replace")
        raise M058Error(f"Node runtime failed: {detail}")
    if response.get("schema") != RESPONSE_SCHEMA or response.get("mode") != mode:
        raise M058Error("Node runtime response identity mismatch")
    result = response.get("result")
    if not isinstance(result, Mapping):
        raise M058Error("Node runtime result is not an object")
    return result


def scan_instruction_space(protocol: M058Protocol = M058_PROTOCOL) -> Mapping[str, object]:
    """Ask the substrate which of the 256 candidate bytes are operations."""
    return _node_call("scan", {
        "candidates": scan_requests(),
        "pairs": [list(pair) for pair in SCAN_PAIRS],
        "export_name": "f",
    }, protocol)


def observe_own_tools(body, arities, protocol: M058Protocol = M058_PROTOCOL) -> Mapping[str, object]:
    samples = {name: [list(a) for a in OBSERVATION_ARGUMENTS[arity]] for name, arity in arities.items()}
    return _node_call("observe", {"body": body, "samples": samples}, protocol)


def synthesize_body(
    operations: Sequence[DiscoveredOperation], observations, arity: int, *,
    allow_composition: bool = True, protocol: M058Protocol = M058_PROTOCOL,
) -> Mapping[str, object]:
    return _node_call("synthesize", {
        "operations_wasm": base64.b64encode(operations_module(operations)).decode("ascii"),
        "observations": [dict(item) for item in observations],
        "arity": arity,
        "max_size": protocol.max_expression_size,
        "budget": protocol.synthesis_budget,
        "allow_composition": allow_composition,
    }, protocol)


def execute_with_synthesized_tools(body, tool_modules, cases, protocol: M058Protocol = M058_PROTOCOL):
    return _node_call("execute", {
        "body": body,
        "tool_modules": {name: base64.b64encode(module).decode("ascii") for name, module in tool_modules.items()},
        "cases": _m048._case_dicts(cases),
    }, protocol)


def _observations_for(arity: int, observed: Sequence[float]) -> list[dict[str, object]]:
    return [{"args": list(args), "expected": value} for args, value in zip(OBSERVATION_ARGUMENTS[arity], observed)]


def _hidden_for(arity: int, observed: Sequence[float]) -> list[dict[str, object]]:
    return [{"args": list(args), "expected": value} for args, value in zip(HIDDEN_ARGUMENTS[arity], observed)]


@dataclass
class M058Manifest:
    mapping: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return dict(self.mapping)

    def digest(self) -> str:
        return _digest(b"m058-discovered-migration-manifest-v1\0", self.mapping)


def run_m058_discovered_migration(protocol: M058Protocol = M058_PROTOCOL) -> M058Manifest:
    """One lineage discovering an instruction set and migrating on it."""
    lineage = reconstruct_m048_version_eight()
    tools = {tool.tool_name: tool for tool in declared_tools(lineage.body())}
    arities = {name: tool.arity for name, tool in tools.items()}

    scan = scan_instruction_space(protocol)
    if int(scan["scanned"]) != len(OPCODE_SPACE):
        raise M058Error("the scan did not cover the declared opcode space")
    operations = discovered_from(scan)
    discovered_opcodes = {operation.opcode for operation in operations}
    if not discovered_opcodes:
        raise M058Error("the scan discovered no operation")

    observed = observe_own_tools(lineage.body(), arities, protocol)
    hidden_samples = {name: [list(a) for a in HIDDEN_ARGUMENTS[arity]] for name, arity in arities.items()}
    observed_hidden = _node_call("observe", {"body": lineage.body(), "samples": hidden_samples}, protocol)

    opcode_by_name = {operation.name: operation.opcode for operation in operations}
    syntheses: dict[str, Mapping[str, object]] = {}
    tool_modules: dict[str, bytes] = {}
    expressions: dict[str, str] = {}
    composed: list[str] = []
    for name in sorted(tools):
        arity = arities[name]
        result = synthesize_body(operations, _observations_for(arity, observed["observations"][name]), arity, protocol=protocol)
        if result["status"] != "synthesized":
            raise M058Error(f"no body was synthesized for {name}: {result['status']}")
        syntheses[name] = result
        expression = load_expression(result["expression"])
        module, record = emit_tool(name, expression, arity, opcode_by_name)
        tool_modules[name] = module
        expressions[name] = record["expression"]
        if int(result["expression_size"]) > 3:
            composed.append(name)
    if not composed:
        raise M058Error("no tool required composition; discovery was not distinguished from labelling")

    verified = _node_call("verify", {
        "tool_modules": {name: base64.b64encode(module).decode("ascii") for name, module in sorted(tool_modules.items())},
        "checks": {name: _hidden_for(arities[name], observed_hidden["observations"][name]) for name in sorted(tool_modules)},
    }, protocol)["verified"]
    if not all(verified.values()):
        raise M058Error("a synthesized body failed on the hidden domain")

    migrated = execute_with_synthesized_tools(lineage.body(), tool_modules, lineage.retained, protocol)
    if not migrated["all_passed"]:
        raise M058Error("a capability was lost on the discovered instruction set")

    without_composition = {
        name: synthesize_body(
            operations, _observations_for(arities[name], observed["observations"][name]),
            arities[name], allow_composition=False, protocol=protocol,
        )["status"]
        for name in composed
    }

    beyond_m057 = sorted(f"{opcode:#04x}" for opcode in discovered_opcodes - set(M057_AUTHORED_OPCODES))
    mapping = {
        "schema": "m058-discovered-migration-manifest-v1",
        "status": "development_pending_qualification",
        "protocol_digest": protocol.digest(),
        "inherited_version": lineage.version(),
        "inherited_retained_case_count": len(lineage.retained),
        "opcode_space_scanned": int(scan["scanned"]),
        "operations_discovered": len(operations),
        "operations_rejected": int(scan["rejected_count"]),
        "operation_names": [operation.name for operation in operations],
        "operation_observations": {operation.name: list(operation.observations) for operation in operations},
        "operations_authored_by_m057": len(M057_AUTHORED_OPCODES),
        "operations_discovery_added": beyond_m057,
        "admissible_space_by_arity": {
            str(arity): expression_space_size(protocol.max_expression_size, len(atoms_for(arity)), len(operations))
            for arity in sorted(set(arities.values()))
        },
        "synthesis_budget": protocol.synthesis_budget,
        "expression_sizes": {name: int(syntheses[name]["expression_size"]) for name in sorted(tools)},
        "expressions": {name: expressions[name] for name in sorted(tools)},
        "candidates_constructed": {name: int(syntheses[name]["candidates_constructed"]) for name in sorted(tools)},
        "behaviour_classes": {name: int(syntheses[name]["behaviour_classes"]) for name in sorted(tools)},
        "tools_requiring_composition": sorted(composed),
        "hidden_domain_verified": {name: bool(value) for name, value in sorted(verified.items())},
        "migrated_all_retained_passed": bool(migrated["all_passed"]),
        "migrated_import_count": int(migrated["import_count"]),
        "ablation_composition_denied": without_composition,
        "instruction_set_authored_by_human": False,
        "signature_shape_authored_by_human": True,
        "arbitrary_code_generation": False,
        "network_authority": False,
        "repository_authority": False,
        "credential_authority": False,
        "deployment_authority": False,
        "canonical": False,
    }
    return M058Manifest(mapping)


__all__ = [
    "HIDDEN_ARGUMENTS", "M057_AUTHORED_OPCODES", "M058Manifest", "M058Protocol", "M058_PROTOCOL",
    "OBSERVATION_ARGUMENTS", "SCAN_PAIRS", "execute_with_synthesized_tools", "observe_own_tools",
    "run_m058_discovered_migration", "scan_instruction_space", "synthesize_body",
]
