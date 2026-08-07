"""M056: a second migration, and whether what was learned after the first one survives it.

M048 changed substrate once: the accepted M047 Python body became native Node ESM, and the
lineage then learned `tool_max` **in the new runtime**. M048's compiler was written by a human
who knew the nine M047 modules it had to translate; `tool_max` did not exist yet.

M056 asks whether a second migration carries it. If migration two transports the twenty-eight
capabilities inherited from before migration one and loses the one acquired after it, then each
hop carries only what its compiler already knew, and the lineage cannot accumulate across
substrates. That would be a negative result, and it is what makes this experiment worth running.

The target substrate is WebAssembly, executed by the already-pinned Node runtime. It is a stack
machine over linear memory with `f64` operands, no closures and no objects, so the body's
JavaScript semantics do not survive by accident. The emitted module declares **no imports**, so
it cannot call back out for its arithmetic — a property the experiment verifies rather than
promises.

M048 is qualified, so under D003 nothing here modifies it. Its reconstruction helpers are read;
its Node runtime is untouched.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Mapping, Sequence

import metamorphosis.m048_runtime_migration as _m048_facade  # applies the qualified corrections
import metamorphosis.m048_native_lineage as _m048
from metamorphosis.m056_wasm_compiler import (
    WasmCompileError, compilation_record, compile_tools_to_wasm, declared_tools, module_digest,
)


class M056Error(ValueError):
    """Raised when an M056 artifact violates the bounded protocol."""


def _digest(domain: bytes, value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(domain + payload).hexdigest()


RESPONSE_SCHEMA = "m056-node-response-v1"


@dataclass(frozen=True)
class M056Protocol:
    source_runtime: str = "node-esm"
    target_runtime: str = "webassembly"
    value_type: str = "f64"
    learned_token: str = "minimum"
    learned_tool: str = "min"
    node_timeout_seconds: float = 60.0
    schema: str = "m056-second-migration-protocol-v1"

    def __post_init__(self) -> None:
        if self.source_runtime != "node-esm" or self.target_runtime != "webassembly":
            raise M056Error("M056 fixes Node ESM to WebAssembly as its second migration")
        if self.value_type != "f64":
            raise M056Error("M056 fixes f64, which is what a JavaScript number is")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "source_runtime": self.source_runtime,
            "target_runtime": self.target_runtime,
            "value_type": self.value_type,
            "learned_token": self.learned_token,
            "learned_tool": self.learned_tool,
        }

    def digest(self) -> str:
        return _digest(b"m056-second-migration-protocol-v1\0", self.to_dict())


M056_PROTOCOL = M056Protocol()


def _runtime_script() -> Path:
    return Path(__file__).resolve().with_name("m056_wasm_runtime.mjs")


def _node_call(mode: str, request: Mapping[str, object], protocol: M056Protocol) -> Mapping[str, object]:
    payload = json.dumps(request, sort_keys=True, separators=(",", ":")).encode("utf-8")
    try:
        completed = subprocess.run(
            ["node", str(_runtime_script()), mode],
            input=payload,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=protocol.node_timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise M056Error(f"Node runtime unavailable or timed out: {type(exc).__name__}") from exc
    try:
        response = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise M056Error("Node runtime returned malformed output") from exc
    if completed.returncode != 0 or not isinstance(response, Mapping) or response.get("fatal_error"):
        detail = response.get("fatal_error") if isinstance(response, Mapping) else completed.stderr.decode("utf-8", "replace")
        raise M056Error(f"Node runtime failed: {detail}")
    if response.get("schema") != RESPONSE_SCHEMA or response.get("mode") != mode:
        raise M056Error("Node runtime response identity mismatch")
    result = response.get("result")
    if not isinstance(result, Mapping):
        raise M056Error("Node runtime result is not an object")
    return result


@dataclass(frozen=True)
class InheritedLineage:
    """The accepted M048 version-eight state and everything it must not lose."""

    state: Mapping[str, object]
    retained: tuple[object, ...]
    source_retained_count: int
    post_migration_cases: tuple[object, ...]

    def body(self) -> Mapping[str, object]:
        return self.state["body"]

    def version(self) -> int:
        return int(self.state["version"])


def reconstruct_m048_version_eight(protocol: M056Protocol = M056_PROTOCOL) -> InheritedLineage:
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
        raise M056Error("could not reconstruct the accepted M048 version-eight state")
    return InheritedLineage(
        state=accepted,
        retained=tuple(retained) + tuple(public) + tuple(hidden),
        source_retained_count=len(retained),
        post_migration_cases=tuple(public) + tuple(hidden),
    )


def _case_dicts(cases: Sequence[object]) -> list[dict[str, object]]:
    return _m048._case_dicts(cases)


def execute_on_wasm(
    body: Mapping[str, object], module: bytes, cases: Sequence[object],
    protocol: M056Protocol = M056_PROTOCOL,
) -> Mapping[str, object]:
    return _node_call("execute", {
        "body": body,
        "wasm": base64.b64encode(module).decode("ascii"),
        "cases": _case_dicts(cases),
    }, protocol)


def execute_without_wasm(
    body: Mapping[str, object], cases: Sequence[object], protocol: M056Protocol = M056_PROTOCOL,
) -> Mapping[str, object]:
    """The counter-check. If the shell still answers, the semantics never left JavaScript."""
    return _node_call("without_wasm", {"body": body, "cases": _case_dicts(cases)}, protocol)


_ALIASES = re.compile(r"(export const ALIASES=)(\{.*?\})(;)")
_ARITIES = re.compile(r"(export const ARITIES=)(\{.*?\})(;)")
_ROUTES = re.compile(r"(export const ROUTES=)(\{.*?\})(;)")


def _replace_table(source: str, pattern: re.Pattern[str], entries: Mapping[str, object]) -> str:
    match = pattern.search(source)
    if match is None:
        raise M056Error("accepted shell module does not expose its table")
    merged = {**json.loads(match.group(2)), **entries}
    ordered = json.dumps({key: merged[key] for key in sorted(merged)}, separators=(",", ":"))
    return source[: match.start(2)] + ordered + source[match.end(2) :]


def _table(source: str, pattern: re.Pattern[str]) -> dict[str, object]:
    match = pattern.search(source)
    if match is None:
        raise M056Error("accepted shell module does not expose its table")
    return json.loads(match.group(2))


def propose_post_migration_capability(
    body: Mapping[str, object], protocol: M056Protocol = M056_PROTOCOL,
) -> tuple[dict[str, object], bytes]:
    """Learn a capability in the migrated substrate.

    The emitted tool module declares itself the same way `tool_mean` and `tool_max` do, so the
    compiler reaches it by the path it already had. Nothing here names the new tool to the
    compiler.
    """
    modules = {module["name"]: dict(module) for module in body["modules"]}
    token, tool = protocol.learned_token, protocol.learned_tool
    interpretation = dict(modules["interpretation"])
    interpretation["source"] = _replace_table(
        _replace_table(interpretation["source"], _ALIASES, {token: tool}), _ARITIES, {tool: 2}
    )
    interpretation["meta"] = {
        **interpretation["meta"],
        "aliases": _table(interpretation["source"], _ALIASES),
    }
    selection = dict(modules["selection"])
    selection["source"] = _replace_table(selection["source"], _ROUTES, {tool: tool})
    selection["meta"] = {**selection["meta"], "routes": _table(selection["source"], _ROUTES)}
    tool_module = {
        "name": f"tool_{tool}",
        "source": (
            f"// M056_META {json.dumps({'kind': 'synthesized_tool', 'module': f'tool_{tool}', 'tool_name': tool, 'expression_id': token}, sort_keys=True)}\n"
            f"export function {tool}(args){{if(!args.length)throw new Error('tool_requires_arguments');return Math.min(...args);}}\n"
            f"export const TOOLS={{{tool}}};\n"
        ),
        "meta": {"kind": "synthesized_tool", "tool_name": tool, "expression_id": token},
    }
    candidate_modules = {**modules, "interpretation": interpretation, "selection": selection}
    candidate_modules[tool_module["name"]] = tool_module
    candidate_body = {
        "schema": body["schema"],
        "modules": [candidate_modules[name] for name in sorted(candidate_modules)],
        "regression_cases": list(body["regression_cases"]),
    }
    candidate_module, _tools = compile_tools_to_wasm(candidate_body)
    return candidate_body, candidate_module


def _case(case_id: str, request: str, expected: object, origin: str):
    return _m048._case(case_id, request, expected, origin)


def learning_cases() -> tuple[tuple[object, ...], tuple[object, ...]]:
    public = tuple(
        _case(f"m056_minimum_public_{index}", f"minimum {a} {b}", float(min(a, b)), "m056_minimum")
        for index, (a, b) in enumerate(((2, 5), (-1, -3), (4, 4)), start=1)
    )
    hidden = tuple(
        _case(f"m056_minimum_hidden_{index}", f"minimum {a} {b}", float(min(a, b)), "m056_minimum")
        for index, (a, b) in enumerate(((-8, 3), (7, 7)), start=1)
    )
    return public, hidden


def validate_candidate(
    candidate_body: Mapping[str, object], candidate_module: bytes, *,
    retained: Sequence[object], public: Sequence[object], hidden: Sequence[object],
    protocol: M056Protocol = M056_PROTOCOL,
) -> dict[str, object]:
    """Independent validation: inherited regression, then public, then the hidden bank."""
    regression = execute_on_wasm(candidate_body, candidate_module, retained, protocol)
    public_run = execute_on_wasm(candidate_body, candidate_module, public, protocol)
    hidden_run = execute_on_wasm(candidate_body, candidate_module, hidden, protocol)
    return {
        "inherited_regression_passed": bool(regression["all_passed"]),
        "inherited_regression_total": len(retained),
        "public_passed": bool(public_run["all_passed"]),
        "hidden_passed": bool(hidden_run["all_passed"]),
        "accepted": bool(regression["all_passed"] and public_run["all_passed"] and hidden_run["all_passed"]),
    }


def _state_digest(state: Mapping[str, object]) -> str:
    return _m048._native_state_digest(state)


def adopt(state: Mapping[str, object], candidate_body: Mapping[str, object], verdict: Mapping[str, object]) -> dict[str, object]:
    if not verdict.get("accepted"):
        raise M056Error("an unvalidated candidate cannot be adopted")
    if not verdict.get("inherited_regression_passed"):
        raise M056Error("adoption requires the inherited regression bank to pass")
    return {**state, "version": int(state["version"]) + 1, "body": candidate_body}


def corrupt_state(state: Mapping[str, object]) -> dict[str, object]:
    modules = [dict(module) for module in state["body"]["modules"]]
    if not modules:
        raise M056Error("an empty body cannot carry a post-adoption fault")
    modules[-1] = {**modules[-1], "source": modules[-1]["source"] + "\n// forced fault\n"}
    return {**state, "body": {**state["body"], "modules": modules}}


def detect_fault(state: Mapping[str, object], expected_digest: str) -> bool:
    return _state_digest(state) != expected_digest


def snapshot_state(state: Mapping[str, object]) -> str:
    return json.dumps(state, sort_keys=True, separators=(",", ":"))


def restore(snapshot: str, expected_digest: str) -> dict[str, object]:
    restored = json.loads(snapshot)
    if _state_digest(restored) != expected_digest:
        raise M056Error("restored state does not match its digest")
    return restored


@dataclass
class M056Manifest:
    mapping: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return dict(self.mapping)

    def digest(self) -> str:
        return _digest(b"m056-second-migration-manifest-v1\0", self.mapping)


def run_m056_second_migration(protocol: M056Protocol = M056_PROTOCOL) -> M056Manifest:
    """One lineage, migrated a second time, then learning again in the new substrate."""
    lineage = reconstruct_m048_version_eight(protocol)
    inherited_digest = _state_digest(lineage.state)

    module, tools = compile_tools_to_wasm(lineage.body())
    record = compilation_record(tools, module)
    if record["imports"] != 0:
        raise M056Error("the migrated module declares imports and could delegate its semantics")

    migrated = execute_on_wasm(lineage.body(), module, lineage.retained, protocol)
    if not migrated["all_passed"]:
        raise M056Error("the second migration lost an inherited capability")
    if migrated["wasm_import_count"] != 0:
        raise M056Error("the instantiated module declares imports")

    # The load-bearing check: the capability learned after the FIRST migration, in the new
    # substrate, isolated from the capabilities that predate migration one.
    post_migration = execute_on_wasm(lineage.body(), module, lineage.post_migration_cases, protocol)
    post_migration_survived = bool(post_migration["all_passed"])

    # Counter-check: removing the module must break every migrated capability.
    without = execute_without_wasm(lineage.body(), lineage.retained, protocol)
    if without["any_passed"]:
        raise M056Error("a capability survived without the wasm module; the semantics never moved")

    # Post-migration learning, in the migrated substrate.
    public, hidden = learning_cases()
    candidate_body, candidate_module = propose_post_migration_capability(lineage.body(), protocol)
    candidate_tools = declared_tools(candidate_body)
    verdict = validate_candidate(
        candidate_body, candidate_module,
        retained=lineage.retained, public=public, hidden=hidden, protocol=protocol,
    )
    if not verdict["accepted"]:
        raise M056Error("the post-migration capability failed independent validation")
    accepted = adopt(lineage.state, candidate_body, verdict)
    accepted_digest = _state_digest(accepted)
    accepted_snapshot = snapshot_state(accepted)
    if accepted["version"] != 9:
        raise M056Error("the accepted post-migration learning is not version nine")

    faulted = corrupt_state(accepted)
    fault_detected = detect_fault(faulted, accepted_digest)
    restored = restore(accepted_snapshot, accepted_digest)
    rollback_exact = (
        fault_detected
        and not detect_fault(accepted, accepted_digest)
        and _state_digest(restored) == accepted_digest
        and snapshot_state(restored) == accepted_snapshot
        and accepted_digest != inherited_digest
    )
    if not rollback_exact:
        raise M056Error("the forced post-adoption fault did not restore the exact state")

    replay_module, _replay_tools = compile_tools_to_wasm(lineage.body())
    replay_candidate_body, replay_candidate_module = propose_post_migration_capability(lineage.body(), protocol)
    replay_identical = (
        module_digest(replay_module) == record["module_digest"]
        and module_digest(replay_candidate_module) == module_digest(candidate_module)
        and replay_candidate_body == candidate_body
    )

    mapping = {
        "schema": "m056-second-migration-manifest-v1",
        "status": "development_pending_qualification",
        "protocol_digest": protocol.digest(),
        "source_runtime": protocol.source_runtime,
        "target_runtime": protocol.target_runtime,
        "value_type": protocol.value_type,
        "inherited_version": lineage.version(),
        "inherited_state_digest": inherited_digest,
        "inherited_retained_case_count": len(lineage.retained),
        "pre_first_migration_case_count": lineage.source_retained_count,
        "compilation": record,
        "migrated_all_retained_passed": bool(migrated["all_passed"]),
        "migrated_wasm_import_count": int(migrated["wasm_import_count"]),
        "migrated_wasm_exported_tools": list(migrated["wasm_exported_tools"]),
        "migrated_shell_module_count": int(migrated["shell_module_count"]),
        "post_migration_capability_survived_second_migration": post_migration_survived,
        "post_migration_case_count": len(lineage.post_migration_cases),
        "capabilities_answered_without_wasm": int(without["passed_count"]),
        "learned_token": protocol.learned_token,
        "learned_tool": protocol.learned_tool,
        "learned_in_runtime": protocol.target_runtime,
        "candidate_tool_count": len(candidate_tools),
        "candidate_module_digest": module_digest(candidate_module),
        "learning_inherited_regression_passed": verdict["inherited_regression_passed"],
        "learning_inherited_regression_total": verdict["inherited_regression_total"],
        "learning_hidden_passed": verdict["hidden_passed"],
        "accepted_version": int(accepted["version"]),
        "accepted_state_digest": accepted_digest,
        "forced_fault": "accepted_body_tampering",
        "fault_detected": fault_detected,
        "rollback_exact": rollback_exact,
        "replay_identical": replay_identical,
        "semantic_delegation_to_javascript": False,
        "arbitrary_code_generation": False,
        "network_authority": False,
        "repository_authority": False,
        "credential_authority": False,
        "deployment_authority": False,
        "canonical": False,
    }
    return M056Manifest(mapping)


__all__ = [
    "M056Error", "M056Manifest", "M056Protocol", "M056_PROTOCOL", "InheritedLineage",
    "WasmCompileError", "adopt", "corrupt_state", "detect_fault", "execute_on_wasm",
    "execute_without_wasm", "learning_cases", "propose_post_migration_capability",
    "reconstruct_m048_version_eight", "restore", "run_m056_second_migration", "snapshot_state",
    "validate_candidate",
]
