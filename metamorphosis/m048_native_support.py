"""M048 genuine Python-to-Node modular-lineage migration experiment."""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence

from metamorphosis.m047_lineage_protocol import M047_PROTOCOL
from metamorphosis.m047_lineage_runner import _execute_with_artifacts
from metamorphosis.m047_lineage_state import initial_software_snapshot
from metamorphosis.m047_lineage_transaction import VersionedSoftwareStore
from metamorphosis.m047_search_memory import CausalSoftwareMemory
from metamorphosis.m047_software_body import (
    BASELINE_CASES,
    SoftwareBody,
    SoftwareCase,
    founder_software_body,
    module_metadata,
)
from metamorphosis.m047_task_definition import build_hidden_modular_task


class NativeMigrationError(RuntimeError):
    """Raised when M048 cannot establish trustworthy native continuity."""


def _normalize_json_number(value: object) -> object:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, list):
        return [_normalize_json_number(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize_json_number(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _normalize_json_number(item) for key, item in value.items()}
    return value

def _canonical_json(value: object) -> bytes:
    return json.dumps(_normalize_json_number(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _digest(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + _canonical_json(value)).hexdigest()


def _js_header(name: str, meta: Mapping[str, object]) -> str:
    return "// M048_META " + json.dumps({"module": name, **dict(meta)}, sort_keys=True, separators=(",", ":")) + "\n"


def _render_interpretation(aliases: Mapping[str, str]) -> str:
    aliases_json = json.dumps(dict(sorted(aliases.items())), sort_keys=True, separators=(",", ":"))
    arities_json = json.dumps({"add": 2, "max": 2, "mean": 3, "mul": 2}, sort_keys=True, separators=(",", ":"))
    return _js_header("interpretation", {"kind": "recursive_prefix_parser", "aliases": dict(sorted(aliases.items()))}) + (
        f"export const ALIASES = {aliases_json};\n"
        f"export const ARITIES = {arities_json};\n"
        "function number(token){const value=Number(token);return Number.isFinite(value)?value:null;}\n"
        "function parse(tokens,index){if(index>=tokens.length)throw new Error('unexpected_end');"
        "const token=tokens[index].toLowerCase();const value=number(token);"
        "if(value!==null)return [{kind:'number',value},index+1];const canonical=ALIASES[token];"
        "if(!canonical)throw new Error('unknown_operator:'+token);const args=[];let cursor=index+1;"
        "for(let i=0;i<ARITIES[canonical];i++){const parsed=parse(tokens,cursor);args.push(parsed[0]);cursor=parsed[1];}"
        "return [{kind:'call',op:canonical,args},cursor];}\n"
        "export function interpret(text){const tokens=text.trim().split(/\\s+/).filter(Boolean);"
        "if(!tokens.length)throw new Error('empty_request');const [node,cursor]=parse(tokens,0);"
        "if(cursor!==tokens.length)throw new Error('trailing_tokens');return node;}\n"
    )


def _render_planning(strategy: str) -> str:
    if strategy != "recursive_postorder":
        raise NativeMigrationError(f"M048 compiler does not support final planner strategy {strategy!r}")
    return _js_header("planning", {"kind": "planner", "strategy": strategy}) + (
        "function emit(node,steps){if(node.kind==='number')return {literal:node.value};"
        "const args=node.args.map(argument=>emit(argument,steps));const index=steps.length;"
        "steps.push({op:node.op,args});return {ref:index};}\n"
        "export function plan(ir){if(ir.kind!=='call')throw new Error('root_must_be_call');"
        "const steps=[];const root=emit(ir,steps);return {steps,root:root.ref};}\n"
    )


def _render_selection(routes: Mapping[str, str]) -> str:
    routes_json = json.dumps(dict(sorted(routes.items())), sort_keys=True, separators=(",", ":"))
    return _js_header("selection", {"kind": "route_table", "routes": dict(sorted(routes.items()))}) + (
        f"export const ROUTES={routes_json};\n"
        "export function select(step){const route=ROUTES[step.op];"
        "if(!route)throw new Error('route_missing:'+step.op);return route;}\n"
    )


def _render_execution() -> str:
    return _js_header("execution", {"kind": "stack_executor"}) + (
        "export function execute(plan,select,tools,budget){const steps=plan.steps;"
        "if(steps.length>budget)throw new Error('budget_exceeded');const results=[];const used_tools=[];"
        "for(const step of steps){const route=select(step);if(!(route in tools))throw new Error('tool_missing:'+route);"
        "const args=step.args.map(argument=>('literal' in argument)?argument.literal:results[argument.ref]);"
        "results.push(tools[route](args));used_tools.push(route);}return {value:results[plan.root],used_tools};}\n"
    )


def _render_critique(policy: str) -> str:
    if policy != "round_two":
        raise NativeMigrationError(f"M048 compiler does not support final critique policy {policy!r}")
    return _js_header("critique", {"kind": "result_critic", "policy": policy}) + (
        "export function critique(value){if(typeof value==='number'&&!Number.isInteger(value))"
        "return Math.round((value+Number.EPSILON)*100)/100;return value;}\n"
    )


def _render_allocation(policy: str) -> str:
    if policy != "double_plan_length":
        raise NativeMigrationError(f"M048 compiler does not support final allocation policy {policy!r}")
    return _js_header("allocation", {"kind": "resource_allocator", "policy": policy}) + (
        "export function allocate(ir,plan){return Math.max(1,plan.steps.length*2);}\n"
    )


def _render_orchestration() -> str:
    return _js_header("orchestration", {"kind": "pipeline_orchestrator"}) + (
        "function failure(stage,error,trace){return {ok:false,output:null,error_stage:stage,"
        "error_type:error.name,error_message:error.message,trace};}\n"
        "export function run(request,modules,tools){const trace=[];let ir,plan,budget,executed;"
        "try{ir=modules.interpretation.interpret(request);trace.push({stage:'interpretation',value:ir});}"
        "catch(error){return failure('interpretation',error,trace);}"
        "try{plan=modules.planning.plan(ir);trace.push({stage:'planning',value:plan});}"
        "catch(error){return failure('planning',error,trace);}"
        "try{budget=modules.allocation.allocate(ir,plan);trace.push({stage:'allocation',value:budget});}"
        "catch(error){return failure('allocation',error,trace);}"
        "try{executed=modules.execution.execute(plan,modules.selection.select,tools,budget);"
        "trace.push({stage:'execution',value:executed});}catch(error){return failure('execution',error,trace);}"
        "try{const output=modules.critique.critique(executed.value);trace.push({stage:'critique',value:output});"
        "return {ok:true,output,error_stage:null,error_type:null,error_message:null,trace};}"
        "catch(error){return failure('critique',error,trace);}}\n"
    )


def _render_tool_core() -> str:
    return _js_header("tool_core", {"kind": "tool_module", "tools": ["add", "mul"]}) + (
        "export function add(args){return args[0]+args[1];}\n"
        "export function mul(args){return args[0]*args[1];}\n"
        "export const TOOLS={add,mul};\n"
    )


def _render_mean_tool() -> str:
    return _js_header("tool_mean", {"kind": "synthesized_tool", "tool_name": "mean", "expression_id": "mean"}) + (
        "export function mean(args){if(!args.length)throw new Error('tool_requires_arguments');"
        "return args.reduce((a,b)=>a+b,0)/args.length;}\nexport const TOOLS={mean};\n"
    )


@dataclass(frozen=True)
class M048Protocol:
    source_runtime: str = "cpython"
    target_runtime: str = "node-esm"
    accepted_post_migration_cycles: int = 1
    max_generated_candidates: int = 8
    max_candidate_bytes: int = 131_072
    node_timeout_seconds: float = 30.0
    forced_fault_task: str = "largest_alias_rollback"
    terminal_task: str = "median_insufficient_evidence"
    schema: str = "m048-native-runtime-migration-protocol-v1"

    def __post_init__(self) -> None:
        if self.source_runtime != "cpython" or self.target_runtime != "node-esm":
            raise NativeMigrationError("M048 fixes CPython to Node ESM migration")
        if self.accepted_post_migration_cycles != 1:
            raise NativeMigrationError("M048 fixes one accepted post-migration learning cycle")
        if self.max_generated_candidates != 8 or self.max_candidate_bytes != 131_072:
            raise NativeMigrationError("M048 candidate bounds are frozen")
        if self.node_timeout_seconds != 30.0:
            raise NativeMigrationError("M048 Node timeout is frozen")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "source_runtime": self.source_runtime,
            "target_runtime": self.target_runtime,
            "accepted_post_migration_cycles": self.accepted_post_migration_cycles,
            "max_generated_candidates": self.max_generated_candidates,
            "max_candidate_bytes": self.max_candidate_bytes,
            "node_timeout_seconds": self.node_timeout_seconds,
            "forced_fault_task": self.forced_fault_task,
            "terminal_task": self.terminal_task,
        }

    def digest(self) -> str:
        return _digest(b"m048-protocol-v1\x00", self.to_dict())


M048_PROTOCOL = M048Protocol()


def _node_script() -> Path:
    return Path(__file__).with_name("m048_node_runtime.mjs")


def _node_call(mode: str, request: Mapping[str, object], protocol: M048Protocol) -> Mapping[str, object]:
    try:
        completed = subprocess.run(
            ["node", str(_node_script()), mode],
            input=_canonical_json(request),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=protocol.node_timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise NativeMigrationError(f"Node runtime unavailable or timed out: {type(exc).__name__}") from exc
    try:
        response = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NativeMigrationError("Node runtime returned malformed output") from exc
    if completed.returncode != 0 or not isinstance(response, Mapping) or response.get("fatal_error"):
        detail = response.get("fatal_error") if isinstance(response, Mapping) else completed.stderr.decode("utf-8", "replace")
        raise NativeMigrationError(f"Node runtime failed: {detail}")
    if response.get("schema") != "m048-node-response-v1" or response.get("mode") != mode:
        raise NativeMigrationError("Node runtime response identity mismatch")
    result = response.get("result")
    if not isinstance(result, Mapping):
        raise NativeMigrationError("Node runtime result is not an object")
    return result


def _compile_module(name: str, metadata: Mapping[str, object]) -> tuple[str, dict[str, object]]:
    if name == "interpretation":
        aliases = metadata.get("aliases")
        if not isinstance(aliases, Mapping):
            raise NativeMigrationError("M047 interpreter metadata missing aliases")
        normalized = {str(k): str(v) for k, v in aliases.items()}
        return _render_interpretation(normalized), {"kind": "recursive_prefix_parser", "aliases": dict(sorted(normalized.items()))}
    if name == "planning":
        strategy = str(metadata.get("strategy"))
        return _render_planning(strategy), {"kind": "planner", "strategy": strategy}
    if name == "selection":
        routes = metadata.get("routes")
        if not isinstance(routes, Mapping):
            raise NativeMigrationError("M047 selection metadata missing routes")
        normalized = {str(k): str(v) for k, v in routes.items()}
        return _render_selection(normalized), {"kind": "route_table", "routes": dict(sorted(normalized.items()))}
    if name == "execution":
        return _render_execution(), {"kind": "stack_executor"}
    if name == "critique":
        policy = str(metadata.get("policy"))
        return _render_critique(policy), {"kind": "result_critic", "policy": policy}
    if name == "allocation":
        policy = str(metadata.get("policy"))
        return _render_allocation(policy), {"kind": "resource_allocator", "policy": policy}
    if name == "orchestration":
        return _render_orchestration(), {"kind": "pipeline_orchestrator"}
    if name == "tool_core":
        return _render_tool_core(), {"kind": "tool_module", "tools": ["add", "mul"]}
    if name == "tool_mean":
        return _render_mean_tool(), {"kind": "synthesized_tool", "tool_name": "mean", "expression_id": "mean"}
    raise NativeMigrationError(f"unsupported M047 module for native compilation: {name}")


def compile_m047_body_to_node(body: SoftwareBody) -> dict[str, object]:
    modules: list[dict[str, object]] = []
    for module in body.modules:
        metadata = module_metadata(module.source)
        source, native_meta = _compile_module(module.name, metadata)
        if "python" in source.lower() or "subprocess" in source.lower() or "child_process" in source.lower():
            raise NativeMigrationError("native module contains a forbidden delegation token")
        modules.append({"name": module.name, "source": source, "meta": native_meta})
    native = {
        "schema": "m048-js-body-v1",
        "modules": sorted(modules, key=lambda item: str(item["name"])),
        "regression_cases": [case.to_dict() for case in body.regression_cases],
    }
    if len(_canonical_json(native)) > M048_PROTOCOL.max_candidate_bytes:
        raise NativeMigrationError("compiled native body exceeds the fixed size bound")
    return native


def _native_body_digest(body: Mapping[str, object]) -> str:
    return _digest(b"m048-js-body-v1\x00", body)


def _native_state_digest(state: Mapping[str, object]) -> str:
    return _digest(b"m048-native-state-v1\x00", state)


def _native_journal_entry_digest(entry: Mapping[str, object]) -> str:
    return _digest(b"m048-native-journal-entry-v1\x00", entry)


def _native_checkpoint(state: Mapping[str, object]) -> dict[str, object]:
    mapping = {
        "schema": "m048-native-checkpoint-v1",
        "version": state["version"],
        "body_digest": _native_body_digest(state["body"]),
        "patch_registry_digest": _digest(b"m048-native-patch-registry-v1\x00", state["patch_registry"]),
        "journal_digest": _digest(b"m048-native-journal-v1\x00", state["causal_journal"]),
        "memory_digest": _digest(b"m048-native-memory-v1\x00", state["causal_memory"]),
        "migration_digest": state["migration"]["digest"],
    }
    return {**mapping, "combined_digest": _digest(b"m048-native-checkpoint-v1\x00", mapping)}
