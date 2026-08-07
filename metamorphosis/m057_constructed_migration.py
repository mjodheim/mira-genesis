"""M057: the lineage constructs its own migration path.

M056 handed the lineage a compiler. `m056_wasm_compiler._body_for` mapped every declared tool to
a WebAssembly instruction sequence, authored in advance, and the result stated the limit twice:
the lineage carried its capabilities across a substrate boundary but did not perform the
crossing.

M057 removes the map. The target instruction set is exposed as opaque handles; nothing tells the
lineage which one is addition and which is maximum. It observes its own accepted tools in the
substrate it currently runs in, probes the handles, and composes a body for each tool out of
what it measured.

This is M013e one level up — *"exact migration after discovery of an opaque finite substrate"* —
asked of a real runtime rather than of deterministic automata.
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
from metamorphosis.m057_opaque_substrate import (
    HANDLES, MAX_EXPRESSION_SIZE, SYNTHESIS_BUDGET, M057Error, atoms_for, emit_tool,
    expression_space_size, load_expression, probe_module,
)


def _digest(domain: bytes, value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(domain + payload).hexdigest()


RESPONSE_SCHEMA = "m057-node-response-v1"

#: Shared input pairs used to probe every handle. Declared before the run.
PROBE_PAIRS: tuple[tuple[float, float], ...] = ((6.0, 3.0), (2.0, 5.0), (-4.0, 7.0), (3.0, 3.0))

#: Argument lists on which the lineage observes each of its own tools. Chosen to separate the
#: tools from one another, not to point at any particular composition.
OBSERVATION_ARGUMENTS: dict[int, tuple[tuple[float, ...], ...]] = {
    2: ((1.0, 2.0), (6.0, 3.0), (-4.0, 7.0), (5.0, 5.0), (0.0, -8.0)),
    3: ((1.0, 2.0, 4.0), (6.0, 3.0, 9.0), (-4.0, 7.0, 0.0), (5.0, -5.0, 10.0), (2.0, 2.0, 2.0)),
}

#: A domain the synthesis never sees, used only to validate what it produced.
HIDDEN_ARGUMENTS: dict[int, tuple[tuple[float, ...], ...]] = {
    2: ((9.0, -1.0), (-7.0, -7.0), (12.0, 4.0)),
    3: ((9.0, 1.0, 2.0), (-3.0, -3.0, -3.0), (100.0, 0.0, 50.0)),
}


@dataclass(frozen=True)
class M057Protocol:
    max_expression_size: int = MAX_EXPRESSION_SIZE
    synthesis_budget: int = SYNTHESIS_BUDGET
    node_timeout_seconds: float = 120.0
    schema: str = "m057-constructed-migration-protocol-v1"

    def __post_init__(self) -> None:
        if self.max_expression_size != 7:
            raise M057Error("M057 fixes the maximum expression size at seven nodes")
        if self.synthesis_budget != 200_000:
            raise M057Error("M057 synthesis budget is frozen")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "max_expression_size": self.max_expression_size,
            "synthesis_budget": self.synthesis_budget,
            "handles": list(HANDLES),
            "probe_pairs": [list(pair) for pair in PROBE_PAIRS],
        }

    def digest(self) -> str:
        return _digest(b"m057-constructed-migration-protocol-v1\0", self.to_dict())


M057_PROTOCOL = M057Protocol()


def _runtime_script() -> Path:
    return Path(__file__).resolve().with_name("m057_wasm_runtime.mjs")


def _node_call(mode: str, request: Mapping[str, object], protocol: M057Protocol) -> Mapping[str, object]:
    payload = json.dumps(request, sort_keys=True, separators=(",", ":")).encode("utf-8")
    try:
        completed = subprocess.run(
            ["node", str(_runtime_script()), mode],
            input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=protocol.node_timeout_seconds, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise M057Error(f"Node runtime unavailable or timed out: {type(exc).__name__}") from exc
    try:
        response = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise M057Error("Node runtime returned malformed output") from exc
    if completed.returncode != 0 or not isinstance(response, Mapping) or response.get("fatal_error"):
        detail = response.get("fatal_error") if isinstance(response, Mapping) else completed.stderr.decode("utf-8", "replace")
        raise M057Error(f"Node runtime failed: {detail}")
    if response.get("schema") != RESPONSE_SCHEMA or response.get("mode") != mode:
        raise M057Error("Node runtime response identity mismatch")
    result = response.get("result")
    if not isinstance(result, Mapping):
        raise M057Error("Node runtime result is not an object")
    return result


def probe_handles(protocol: M057Protocol = M057_PROTOCOL) -> Mapping[str, object]:
    """Run every opaque handle on the shared pairs. This is the only way to learn what they do."""
    return _node_call("probe", {
        "probe_wasm": base64.b64encode(probe_module()).decode("ascii"),
        "pairs": [list(pair) for pair in PROBE_PAIRS],
    }, protocol)


def observe_own_tools(
    body: Mapping[str, object], arities: Mapping[str, int], protocol: M057Protocol = M057_PROTOCOL,
) -> Mapping[str, object]:
    """The lineage watching its own tools run. The synthesis targets come from here."""
    samples = {
        name: [list(args) for args in OBSERVATION_ARGUMENTS[arity]] for name, arity in arities.items()
    }
    return _node_call("observe", {"body": body, "samples": samples}, protocol)


def synthesize_body(
    observations: Sequence[Mapping[str, object]], arity: int, *,
    allow_composition: bool = True, protocol: M057Protocol = M057_PROTOCOL,
) -> Mapping[str, object]:
    return _node_call("synthesize", {
        "probe_wasm": base64.b64encode(probe_module()).decode("ascii"),
        "observations": [dict(item) for item in observations],
        "arity": arity,
        "max_size": protocol.max_expression_size,
        "budget": protocol.synthesis_budget,
        "allow_composition": allow_composition,
    }, protocol)


def execute_with_synthesized_tools(
    body: Mapping[str, object], tool_modules: Mapping[str, bytes], cases: Sequence[object],
    protocol: M057Protocol = M057_PROTOCOL,
) -> Mapping[str, object]:
    return _node_call("execute", {
        "body": body,
        "tool_modules": {name: base64.b64encode(module).decode("ascii") for name, module in tool_modules.items()},
        "cases": _m048._case_dicts(cases),
    }, protocol)


def _observations_for(name: str, arity: int, observed: Sequence[float]) -> list[dict[str, object]]:
    return [
        {"args": list(args), "expected": value}
        for args, value in zip(OBSERVATION_ARGUMENTS[arity], observed)
    ]


def _hidden_for(name: str, arity: int, observed_hidden: Sequence[float]) -> list[dict[str, object]]:
    return [
        {"args": list(args), "expected": value}
        for args, value in zip(HIDDEN_ARGUMENTS[arity], observed_hidden)
    ]


@dataclass
class M057Manifest:
    mapping: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return dict(self.mapping)

    def digest(self) -> str:
        return _digest(b"m057-constructed-migration-manifest-v1\0", self.mapping)


def run_m057_constructed_migration(protocol: M057Protocol = M057_PROTOCOL) -> M057Manifest:
    """One lineage discovering a substrate and building its own way into it."""
    lineage = reconstruct_m048_version_eight()
    tools = {tool.tool_name: tool for tool in declared_tools(lineage.body())}
    arities = {name: tool.arity for name, tool in tools.items()}

    probed = probe_handles(protocol)
    if probed["import_count"] != 0:
        raise M057Error("the probe module declares imports")
    if sorted(probed["handles"]) != sorted(HANDLES):
        raise M057Error("the substrate did not expose the declared handles")

    observed = observe_own_tools(lineage.body(), arities, protocol)
    hidden_samples = {name: [list(a) for a in HIDDEN_ARGUMENTS[arity]] for name, arity in arities.items()}
    observed_hidden = _node_call("observe", {"body": lineage.body(), "samples": hidden_samples}, protocol)

    syntheses: dict[str, Mapping[str, object]] = {}
    tool_modules: dict[str, bytes] = {}
    emitted: dict[str, dict[str, object]] = {}
    composed_tools: list[str] = []
    for name in sorted(tools):
        arity = arities[name]
        result = synthesize_body(_observations_for(name, arity, observed["observations"][name]), arity, protocol=protocol)
        if result["status"] != "synthesized":
            raise M057Error(f"the lineage did not synthesize a body for {name}: {result['status']}")
        syntheses[name] = result
        expression = load_expression(result["expression"])
        module, record = emit_tool(name, expression, arity)
        tool_modules[name] = module
        emitted[name] = record
        if int(result["expression_size"]) > 3:
            composed_tools.append(name)

    if not composed_tools:
        raise M057Error("no tool required composition; discovery was not distinguished from labelling")

    # Validate every synthesized body on a domain the synthesis never saw.
    hidden_verified = _verify_hidden(tool_modules, arities, observed_hidden["observations"], protocol)
    if not all(hidden_verified.values()):
        raise M057Error("a synthesized body failed on the hidden domain")

    migrated = execute_with_synthesized_tools(lineage.body(), tool_modules, lineage.retained, protocol)
    if not migrated["all_passed"]:
        raise M057Error("a capability was lost on the constructed migration path")

    # Ablation one: handles taken in the order the substrate exposes them, without probing.
    unprobed = _ablation_declaration_order(lineage, arities, observed["observations"], protocol)
    # Ablation two: probing kept, composition denied.
    without_composition = {
        name: synthesize_body(
            _observations_for(name, arities[name], observed["observations"][name]),
            arities[name], allow_composition=False, protocol=protocol,
        )["status"]
        for name in composed_tools
    }

    mapping = {
        "schema": "m057-constructed-migration-manifest-v1",
        "status": "development_pending_qualification",
        "protocol_digest": protocol.digest(),
        "inherited_version": lineage.version(),
        "inherited_retained_case_count": len(lineage.retained),
        "handle_count": len(HANDLES),
        "handles_carry_semantic_names": False,
        "probe_pairs": len(PROBE_PAIRS),
        "probe_import_count": int(probed["import_count"]),
        "handle_observations": {name: list(values) for name, values in sorted(probed["observations"].items())},
        "admissible_space_by_arity": {
            str(arity): expression_space_size(protocol.max_expression_size, len(atoms_for(arity)))
            for arity in sorted(set(arities.values()))
        },
        "synthesis_budget": protocol.synthesis_budget,
        "synthesised_tools": sorted(tools),
        "expression_sizes": {name: int(syntheses[name]["expression_size"]) for name in sorted(tools)},
        "expressions": {name: emitted[name]["expression"] for name in sorted(tools)},
        "candidates_constructed": {name: int(syntheses[name]["candidates_constructed"]) for name in sorted(tools)},
        "behaviour_classes": {name: int(syntheses[name]["behaviour_classes"]) for name in sorted(tools)},
        "tools_requiring_composition": sorted(composed_tools),
        "hidden_domain_verified": hidden_verified,
        "migrated_all_retained_passed": bool(migrated["all_passed"]),
        "migrated_import_count": int(migrated["import_count"]),
        "ablation_declaration_order_passed": unprobed,
        "ablation_composition_denied": without_composition,
        "arbitrary_code_generation": False,
        "network_authority": False,
        "repository_authority": False,
        "credential_authority": False,
        "deployment_authority": False,
        "canonical": False,
    }
    return M057Manifest(mapping)


def _verify_hidden(
    tool_modules: Mapping[str, bytes], arities: Mapping[str, int],
    expected: Mapping[str, Sequence[float]], protocol: M057Protocol,
) -> dict[str, bool]:
    """Run each synthesized module on arguments the synthesis never saw."""
    result = _node_call("verify", {
        "tool_modules": {
            name: base64.b64encode(module).decode("ascii") for name, module in sorted(tool_modules.items())
        },
        "checks": {
            name: _hidden_for(name, arities[name], expected[name]) for name in sorted(tool_modules)
        },
    }, protocol)
    return {name: bool(value) for name, value in sorted(result["verified"].items())}


def _ablation_declaration_order(
    lineage, arities: Mapping[str, int], observed: Mapping[str, Sequence[float]],
    protocol: M057Protocol,
) -> bool:
    """Assign handles in the order the substrate exposes them, with no probing at all."""
    from metamorphosis.m057_opaque_substrate import Expr

    modules: dict[str, bytes] = {}
    for index, name in enumerate(sorted(arities)):
        arity = arities[name]
        handle = HANDLES[index % len(HANDLES)]
        expression = Expr(handle=handle, left=Expr(atom="p0"), right=Expr(atom="p1" if arity > 1 else "k"))
        modules[name], _record = emit_tool(name, expression, arity)
    execution = execute_with_synthesized_tools(lineage.body(), modules, lineage.retained, protocol)
    return bool(execution["all_passed"])


__all__ = [
    "HIDDEN_ARGUMENTS", "M057Manifest", "M057Protocol", "M057_PROTOCOL", "OBSERVATION_ARGUMENTS",
    "PROBE_PAIRS", "execute_with_synthesized_tools", "observe_own_tools", "probe_handles",
    "run_m057_constructed_migration", "synthesize_body",
]
