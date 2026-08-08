"""M064 integrated real-substrate post-migration completion experiment.

M064 continues the qualified M047 -> M048 CPython-to-Node lineage.  It does
not replace either experiment: it adds the four-arm comparison and the three
post-migration learning cycles which the repository's final frontier requires.

The constructor sees public cases only.  A separate passive validator sees
the retained and hidden cases, validates every public survivor (D021), and
returns a decision without owning the versioned adoption mechanism.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import inspect
import json
import math
import subprocess
import tempfile
from typing import Iterable, Mapping, Sequence

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

# Import the strengthened public facade first.  It installs the qualified M048
# compiler/checkpoint compatibility and, critically, the journal-to-registry
# integrity audit before exposing the integrated lineage internals.
import metamorphosis.m048_runtime_migration as m048


_support = m048._support
_lineage = m048._lineage


class M064Error(RuntimeError):
    """Raised when an M064 scientific or execution invariant is violated."""


def _canonical_json(value: object) -> bytes:
    return _support._canonical_json(value)


def _digest(domain: bytes, value: object) -> str:
    return _support._digest(domain, value)


def _case(case_id: str, token: str, left: int, right: int, expected: float) -> SoftwareCase:
    return SoftwareCase(case_id, f"{token} {left} {right}", expected, token)


def _round_two(value: float) -> int | float:
    """Match the positive-number branch of M048's Node critic exactly."""
    if value < 0:
        raise M064Error("the frozen M064 bank uses non-negative outputs only")
    rounded = math.floor((value + float.fromhex("0x1.0000000000000p-52")) * 100.0 + 0.5) / 100.0
    return int(rounded) if rounded.is_integer() else rounded


def _task_value(family: str, left: int, right: int) -> int | float:
    high = max(left, right)
    crest = (high + left + right) / 3.0
    if family == "crest":
        value = crest
    elif family == "lift":
        value = crest + high
    elif family == "weave":
        value = (crest + high) * crest
    else:
        raise M064Error(f"unknown frozen task family: {family}")
    return _round_two(value)


@dataclass(frozen=True)
class M064Task:
    task_id: str
    token: str
    family: str
    public_pairs: tuple[tuple[int, int], ...]
    hidden_pairs: tuple[tuple[int, int], ...]
    required_prior_tools: tuple[str, ...]

    def public_cases(self) -> tuple[SoftwareCase, ...]:
        return tuple(
            _case(
                f"{self.task_id}_public_{index}",
                self.token,
                left,
                right,
                _task_value(self.family, left, right),
            )
            for index, (left, right) in enumerate(self.public_pairs, start=1)
        )

    def hidden_cases(self) -> tuple[SoftwareCase, ...]:
        return tuple(
            _case(
                f"{self.task_id}_hidden_{index}",
                self.token,
                left,
                right,
                _task_value(self.family, left, right),
            )
            for index, (left, right) in enumerate(self.hidden_pairs, start=1)
        )

    def commitment(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "token": self.token,
            "family": self.family,
            "public_cases": [case.to_dict() for case in self.public_cases()],
            "hidden_cases": [case.to_dict() for case in self.hidden_cases()],
            "required_prior_tools": list(self.required_prior_tools),
        }


def _bank_entry(index: int, offset: int) -> tuple[M064Task, ...]:
    pools = (
        (
            ((1, 5), (7, 2), (4, 9), (8, 3), (2, 6), (11, 4)),
            ((3, 10), (12, 5), (6, 8), (9, 1), (5, 13), (14, 7)),
        ),
        (
            ((2, 7), (9, 4), (3, 8), (10, 2), (5, 12), (13, 6)),
            ((4, 11), (15, 8), (6, 10), (12, 1), (7, 14), (16, 9)),
        ),
        (
            ((1, 8), (10, 3), (4, 12), (13, 5), (6, 11), (15, 2)),
            ((3, 13), (14, 4), (7, 16), (17, 6), (8, 12), (18, 5)),
        ),
    )
    tokens = (f"crest{offset}", f"lift{offset}", f"weave{offset}")
    families = ("crest", "lift", "weave")
    required = ((), (tokens[0],), (tokens[0], tokens[1]))
    return tuple(
        M064Task(
            task_id=f"m064_bank_{index}_cycle_{cycle}",
            token=tokens[cycle - 1],
            family=families[cycle - 1],
            public_pairs=tuple(
                (left + offset, right + offset)
                for left, right in pools[cycle - 1][0]
            ),
            hidden_pairs=tuple(
                (left + offset, right + offset)
                for left, right in pools[cycle - 1][1]
            ),
            required_prior_tools=required[cycle - 1],
        )
        for cycle in range(1, 4)
    )


M064_TASK_BANK: tuple[tuple[M064Task, ...], ...] = tuple(
    _bank_entry(index, offset) for index, offset in enumerate((0, 2, 5, 9))
)


def _task_bank_commitment() -> str:
    return _digest(
        b"m064-task-bank-v1\x00",
        [[task.commitment() for task in entry] for entry in M064_TASK_BANK],
    )


@dataclass(frozen=True)
class M064Protocol:
    source_runtime: str = "cpython"
    intermediate_runtime: str = "node-esm"
    target_runtime: str = "webassembly"
    arms: tuple[str, ...] = (
        "complete_continued_lineage",
        "fresh_on_b",
        "unchanged_parent_migrated",
        "learned_state_ablated",
    )
    accepted_post_migration_cycles: int = 3
    candidate_budget_per_arm_cycle: int = 8_192
    max_candidate_bytes: int = 262_144
    node_timeout_seconds: float = 30.0
    task_bank_entries: int = 4
    public_cases_per_cycle: int = 6
    hidden_cases_per_cycle: int = 6
    expression_node_limit: int = 7
    extensions: tuple[str, ...] = ()
    task_bank_commitment: str = _task_bank_commitment()
    schema: str = "m064-real-substrate-completion-protocol-v1"

    def __post_init__(self) -> None:
        if (
            self.source_runtime != "cpython"
            or self.intermediate_runtime != "node-esm"
            or self.target_runtime != "webassembly"
        ):
            raise M064Error("M064 fixes the qualified CPython -> Node ESM -> WebAssembly path")
        if self.accepted_post_migration_cycles != 3 or len(self.arms) != 4:
            raise M064Error("M064 fixes three cycles and four adversarial arms")
        if self.candidate_budget_per_arm_cycle != 8_192:
            raise M064Error("M064 fixes an equal 8,192-expression budget")
        if self.task_bank_entries != len(M064_TASK_BANK):
            raise M064Error("M064 task-bank size drifted")
        if self.public_cases_per_cycle != 6 or self.hidden_cases_per_cycle != 6:
            raise M064Error("M064 case-count commitment drifted")
        if self.expression_node_limit != 7 or self.extensions != ():
            raise M064Error("M064 construction grammar drifted")
        if self.task_bank_commitment != _task_bank_commitment():
            raise M064Error("M064 task-bank commitment mismatch")
        if self.node_timeout_seconds != m048.M048_PROTOCOL.node_timeout_seconds:
            raise M064Error("M064 must retain the qualified Node timeout")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "source_runtime": self.source_runtime,
            "intermediate_runtime": self.intermediate_runtime,
            "target_runtime": self.target_runtime,
            "arms": list(self.arms),
            "accepted_post_migration_cycles": self.accepted_post_migration_cycles,
            "candidate_budget_per_arm_cycle": self.candidate_budget_per_arm_cycle,
            "max_candidate_bytes": self.max_candidate_bytes,
            "node_timeout_seconds": self.node_timeout_seconds,
            "task_bank_entries": self.task_bank_entries,
            "public_cases_per_cycle": self.public_cases_per_cycle,
            "hidden_cases_per_cycle": self.hidden_cases_per_cycle,
            "expression_node_limit": self.expression_node_limit,
            "extensions": list(self.extensions),
            "task_bank_commitment": self.task_bank_commitment,
            "canonical_selection_rule": "sha256(protocol_digest || marker_parent_sha) mod bank_size",
            "public_survivor_rule": "validate_entire_class_before_digest_selection",
        }

    def digest(self) -> str:
        return _digest(b"m064-protocol-v1\x00", self.to_dict())


M064_PROTOCOL = M064Protocol()


def select_task_bank(marker_parent_sha: str, protocol: M064Protocol = M064_PROTOCOL) -> int:
    if len(marker_parent_sha) != 40 or any(char not in "0123456789abcdef" for char in marker_parent_sha):
        raise M064Error("canonical marker parent must be a lower-case forty-character Git SHA")
    value = hashlib.sha256(
        b"m064-canonical-bank-selection-v1\x00"
        + bytes.fromhex(protocol.digest())
        + bytes.fromhex(marker_parent_sha)
    ).digest()
    return int.from_bytes(value, "big") % protocol.task_bank_entries


def _module_map(body: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    modules = body.get("modules")
    if not isinstance(modules, list):
        raise M064Error("native body modules are malformed")
    result: dict[str, Mapping[str, object]] = {}
    for item in modules:
        if not isinstance(item, Mapping) or not isinstance(item.get("name"), str):
            raise M064Error("native module is malformed")
        result[str(item["name"])] = item
    return result


def _body_bytes(body: Mapping[str, object]) -> int:
    return len(_canonical_json(body))


def _isolated_node_call(
    mode: str,
    request: Mapping[str, object],
    protocol: M064Protocol,
) -> Mapping[str, object]:
    """Run the qualified Node evaluator with M064's explicit process bounds."""
    with tempfile.TemporaryDirectory(prefix="m064-node-cwd-") as directory:
        try:
            completed = subprocess.run(
                [
                    "node",
                    "--max-old-space-size=128",
                    str(_support._node_script()),
                    mode,
                ],
                input=_canonical_json(request),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=directory,
                timeout=protocol.node_timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise M064Error(
                f"isolated Node runtime unavailable or timed out: {type(exc).__name__}"
            ) from exc
    try:
        response = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise M064Error("isolated Node runtime returned malformed output") from exc
    if completed.returncode != 0 or not isinstance(response, Mapping) or response.get("fatal_error"):
        detail = (
            response.get("fatal_error")
            if isinstance(response, Mapping)
            else completed.stderr.decode("utf-8", "replace")
        )
        raise M064Error(f"isolated Node runtime failed: {detail}")
    if response.get("schema") != "m048-node-response-v1" or response.get("mode") != mode:
        raise M064Error("isolated Node response identity mismatch")
    result = response.get("result")
    if not isinstance(result, Mapping):
        raise M064Error("isolated Node result is not an object")
    return result


def _render_interpretation(aliases: Mapping[str, str], arities: Mapping[str, int]) -> str:
    aliases_value = dict(sorted((str(key), str(value)) for key, value in aliases.items()))
    arities_value = dict(sorted((str(key), int(value)) for key, value in arities.items()))
    return _support._js_header(
        "interpretation",
        {"kind": "m064_recursive_prefix_parser", "aliases": aliases_value, "arities": arities_value},
    ) + (
        f"export const ALIASES={json.dumps(aliases_value, sort_keys=True, separators=(',', ':'))};\n"
        f"export const ARITIES={json.dumps(arities_value, sort_keys=True, separators=(',', ':'))};\n"
        "function number(token){const value=Number(token);return Number.isFinite(value)?value:null;}\n"
        "function parse(tokens,index){if(index>=tokens.length)throw new Error('unexpected_end');"
        "const token=tokens[index].toLowerCase();const value=number(token);"
        "if(value!==null)return [{kind:'number',value},index+1];const canonical=ALIASES[token];"
        "if(!canonical)throw new Error('unknown_operator:'+token);const arity=ARITIES[canonical];"
        "if(!Number.isInteger(arity))throw new Error('arity_missing:'+canonical);const args=[];let cursor=index+1;"
        "for(let i=0;i<arity;i++){const parsed=parse(tokens,cursor);args.push(parsed[0]);cursor=parsed[1];}"
        "return [{kind:'call',op:canonical,args},cursor];}\n"
        "export function interpret(text){const tokens=text.trim().split(/\\s+/).filter(Boolean);"
        "if(!tokens.length)throw new Error('empty_request');const [node,cursor]=parse(tokens,0);"
        "if(cursor!==tokens.length)throw new Error('trailing_tokens');return node;}\n"
    )


def _render_selection(routes: Mapping[str, str]) -> str:
    routes_value = dict(sorted((str(key), str(value)) for key, value in routes.items()))
    return _support._js_header(
        "selection", {"kind": "m064_route_table", "routes": routes_value}
    ) + (
        f"export const ROUTES={json.dumps(routes_value, sort_keys=True, separators=(',', ':'))};\n"
        "export function select(step){const route=ROUTES[step.op];"
        "if(!route)throw new Error('route_missing:'+step.op);return route;}\n"
    )


def _render_registry_execution() -> str:
    return _support._js_header("execution", {"kind": "m064_registry_aware_stack_executor"}) + (
        "export function execute(plan,select,tools,budget){const steps=plan.steps;"
        "if(steps.length>budget)throw new Error('budget_exceeded');const results=[];const used_tools=[];"
        "for(const step of steps){const route=select(step);if(!(route in tools))throw new Error('tool_missing:'+route);"
        "const args=step.args.map(argument=>('literal' in argument)?argument.literal:results[argument.ref]);"
        "results.push(tools[route](args,tools));used_tools.push(route);}"
        "return {value:results[plan.root],used_tools};}\n"
    )


def _render_planning(strategy: str) -> str:
    if strategy == "recursive_postorder":
        return _support._render_planning(strategy)
    if strategy == "root_only":
        body = (
            "export function plan(ir){if(ir.kind!=='call')throw new Error('root_must_be_call');"
            "const args=ir.args.map(argument=>{if(argument.kind!=='number')throw new Error('nested_arguments_unsupported');"
            "return {literal:argument.value};});return {steps:[{op:ir.op,args}],root:0};}\n"
        )
    elif strategy == "one_level":
        body = (
            "function child(node,steps){if(node.kind==='number')return {literal:node.value};"
            "const args=node.args.map(argument=>{if(argument.kind!=='number')throw new Error('planner_depth_exceeded');"
            "return {literal:argument.value};});const index=steps.length;steps.push({op:node.op,args});return {ref:index};}\n"
            "export function plan(ir){if(ir.kind!=='call')throw new Error('root_must_be_call');const steps=[];"
            "const args=ir.args.map(argument=>child(argument,steps));const root=steps.length;"
            "steps.push({op:ir.op,args});return {steps,root};}\n"
        )
    else:
        raise M064Error(f"unsupported M047 planner strategy: {strategy}")
    return _support._js_header("planning", {"kind": "planner", "strategy": strategy}) + body


def _render_critique(policy: str) -> str:
    if policy == "identity":
        expression = "value"
    elif policy in {"round_one", "round_two", "round_three"}:
        factor = {"round_one": 10, "round_two": 100, "round_three": 1000}[policy]
        expression = f"Math.round((value+Number.EPSILON)*{factor})/{factor}"
    else:
        raise M064Error(f"unsupported M047 critique policy: {policy}")
    return _support._js_header("critique", {"kind": "result_critic", "policy": policy}) + (
        f"export function critique(value){{return (typeof value==='number'&&!Number.isInteger(value))?{expression}:value;}}\n"
    )


def _render_allocation(policy: str) -> str:
    expressions = {
        "fixed_one": "1",
        "fixed_four": "4",
        "fixed_five": "5",
        "plan_length": "Math.max(1,plan.steps.length)",
        "double_plan_length": "Math.max(1,plan.steps.length*2)",
    }
    if policy not in expressions:
        raise M064Error(f"unsupported M047 allocation policy: {policy}")
    return _support._js_header("allocation", {"kind": "resource_allocator", "policy": policy}) + (
        f"export function allocate(ir,plan){{return {expressions[policy]};}}\n"
    )


def _compile_control_body(body: SoftwareBody, protocol: M064Protocol) -> dict[str, object]:
    modules: list[dict[str, object]] = []
    default_arities = {"add": 2, "max": 2, "mean": 3, "mul": 2}
    for module in body.modules:
        meta = module_metadata(module.source)
        name = module.name
        if name == "interpretation":
            aliases = {str(key): str(value) for key, value in dict(meta["aliases"]).items()}
            source = _render_interpretation(aliases, default_arities)
            native_meta = {"kind": "m064_recursive_prefix_parser", "aliases": dict(sorted(aliases.items())), "arities": default_arities}
        elif name == "planning":
            strategy = str(meta["strategy"])
            source = _render_planning(strategy)
            native_meta = {"kind": "planner", "strategy": strategy}
        elif name == "selection":
            routes = {str(key): str(value) for key, value in dict(meta["routes"]).items()}
            source = _render_selection(routes)
            native_meta = {"kind": "m064_route_table", "routes": dict(sorted(routes.items()))}
        elif name == "execution":
            source = _support._render_execution()
            native_meta = {"kind": "stack_executor"}
        elif name == "critique":
            policy = str(meta["policy"])
            source = _render_critique(policy)
            native_meta = {"kind": "result_critic", "policy": policy}
        elif name == "allocation":
            policy = str(meta["policy"])
            source = _render_allocation(policy)
            native_meta = {"kind": "resource_allocator", "policy": policy}
        elif name == "orchestration":
            source = _support._render_orchestration()
            native_meta = {"kind": "pipeline_orchestrator"}
        elif name == "tool_core":
            source = _support._render_tool_core()
            native_meta = {"kind": "tool_module", "tools": ["add", "mul"]}
        elif name == "tool_mean":
            source = _support._render_mean_tool()
            native_meta = {"kind": "synthesized_tool", "tool_name": "mean", "expression_id": "mean"}
        else:
            raise M064Error(f"unsupported control-body module: {name}")
        if any(token in source.lower() for token in ("python", "subprocess", "child_process")):
            raise M064Error("control-body compiler emitted a delegation token")
        modules.append({"name": name, "source": source, "meta": native_meta})
    native = {
        "schema": "m048-js-body-v1",
        "modules": sorted(modules, key=lambda item: str(item["name"])),
        "regression_cases": [case.to_dict() for case in body.regression_cases],
    }
    if _body_bytes(native) > protocol.max_candidate_bytes:
        raise M064Error("compiled control body exceeds the frozen size bound")
    return native


@lru_cache(maxsize=1)
def _qualified_source_artifacts() -> object:
    return _execute_with_artifacts(M047_PROTOCOL)


def _source_snapshots() -> dict[str, object]:
    artifacts = _qualified_source_artifacts()
    store = VersionedSoftwareStore(initial_software_snapshot(founder_software_body()))
    memory = CausalSoftwareMemory()
    hidden: list[SoftwareCase] = []
    snapshots: dict[int, object] = {0: store.current}
    memories: dict[int, CausalSoftwareMemory] = {0: memory}
    retained: dict[int, tuple[SoftwareCase, ...]] = {0: BASELINE_CASES}
    for ordinal, (selection, episode) in enumerate(zip(artifacts.selections, artifacts.episodes), start=1):
        task = build_hidden_modular_task(
            store.current.accepted_body,
            ordinal=ordinal,
            protocol_digest=M047_PROTOCOL.digest(),
        )
        hidden.extend(task.hidden_cases)
        receipt = store.adopt(selection)
        if not receipt.adopted:
            raise M064Error(f"M047 reconstruction failed at version {ordinal}")
        memory = memory.append(episode, maximum_bytes=M047_PROTOCOL.resources.max_causal_memory_bytes)
        snapshots[ordinal] = store.current
        memories[ordinal] = memory
        retained[ordinal] = BASELINE_CASES + store.current.accepted_body.regression_cases + tuple(hidden)
    if snapshots[6].version != 6 or len(retained[6]) != 28:
        raise M064Error("M064 did not recover the qualified M047 source lineage")
    return {
        "artifacts": artifacts,
        "snapshots": snapshots,
        "memories": memories,
        "retained": retained,
    }


Expression = dict[str, object]


def _arg(index: int) -> Expression:
    return {"kind": "arg", "index": index}


def _call(tool: str, *arguments: Expression) -> Expression:
    return {"kind": "call", "tool": tool, "args": [dict(argument) for argument in arguments]}


def _expression_key(expression: Mapping[str, object]) -> str:
    return _canonical_json(expression).decode("ascii")


def _expression_nodes(expression: Mapping[str, object]) -> int:
    if expression.get("kind") == "arg":
        return 1
    arguments = expression.get("args")
    if not isinstance(arguments, list):
        raise M064Error("expression call lacks arguments")
    return 1 + sum(_expression_nodes(argument) for argument in arguments if isinstance(argument, Mapping))


def _expression_tools(expression: Mapping[str, object]) -> tuple[str, ...]:
    found: set[str] = set()
    if expression.get("kind") == "call":
        found.add(str(expression["tool"]))
        for argument in expression.get("args", []):
            if isinstance(argument, Mapping):
                found.update(_expression_tools(argument))
    return tuple(sorted(found))


def _primitive(name: str, values: Sequence[float]) -> float:
    if name == "add":
        return values[0] + values[1]
    if name == "mul":
        return values[0] * values[1]
    if name == "mean":
        return sum(values) / len(values)
    if name == "max":
        return max(values)
    if name == "min":
        return min(values)
    raise M064Error(f"unknown primitive semantics: {name}")


def _evaluate_expression(
    expression: Mapping[str, object],
    arguments: Sequence[float],
    tools: Mapping[str, Mapping[str, object]],
    *,
    depth: int = 0,
) -> float:
    if depth > 16:
        raise M064Error("tool expansion exceeded the frozen recursion guard")
    if expression.get("kind") == "arg":
        index = int(expression["index"])
        return float(arguments[index])
    if expression.get("kind") != "call":
        raise M064Error("unknown expression node")
    tool = str(expression["tool"])
    spec = tools.get(tool)
    if spec is None:
        raise M064Error(f"expression references an unowned tool: {tool}")
    raw_children = expression.get("args")
    if not isinstance(raw_children, list) or len(raw_children) != int(spec["arity"]):
        raise M064Error("expression arity mismatch")
    values = [
        _evaluate_expression(child, arguments, tools, depth=depth + 1)
        for child in raw_children
        if isinstance(child, Mapping)
    ]
    if spec["kind"] == "primitive":
        return _primitive(str(spec["primitive"]), values)
    nested = spec.get("expression")
    if spec["kind"] != "constructed" or not isinstance(nested, Mapping):
        raise M064Error("tool registry entry is malformed")
    return _evaluate_expression(nested, values, tools, depth=depth + 1)


def _body_tool_specs(
    body: Mapping[str, object],
    *,
    ablate_inherited_learning: bool,
    extensions: Sequence[str],
) -> dict[str, dict[str, object]]:
    specs: dict[str, dict[str, object]] = {
        "add": {"kind": "primitive", "primitive": "add", "arity": 2, "origin": "founder"},
        "mul": {"kind": "primitive", "primitive": "mul", "arity": 2, "origin": "founder"},
    }
    modules = _module_map(body)
    if "tool_mean" in modules and not ablate_inherited_learning:
        specs["mean"] = {"kind": "primitive", "primitive": "mean", "arity": 3, "origin": "m047_learned"}
    for name, item in modules.items():
        if not name.startswith("tool_") or name in {"tool_core", "tool_mean"}:
            continue
        meta = item.get("meta")
        if not isinstance(meta, Mapping):
            continue
        tool_name = str(meta.get("tool_name", ""))
        if meta.get("kind") == "m064_primitive_extension":
            specs[tool_name] = {
                "kind": "primitive",
                "primitive": str(meta["primitive"]),
                "arity": int(meta["arity"]),
                "origin": "m064_extension",
            }
        elif meta.get("kind") == "m064_constructed_tool":
            expression = meta.get("expression_ast")
            if not isinstance(expression, Mapping):
                raise M064Error("constructed native tool lost its expression AST")
            specs[tool_name] = {
                "kind": "constructed",
                "expression": dict(expression),
                "arity": int(meta["arity"]),
                "origin": str(meta["task_id"]),
            }
    for extension in extensions:
        specs.setdefault(
            extension,
            {"kind": "primitive", "primitive": extension, "arity": 2, "origin": "m064_bounded_extension"},
        )
    return specs


def _enumerate_expression_candidates(
    tools: Mapping[str, Mapping[str, object]],
    node_limit: int,
    candidate_budget: int,
) -> tuple[Expression, ...]:
    """Construct bounded expressions from owned tools; no complete programs are catalogued."""
    atoms = (_arg(0), _arg(1))
    binary = tuple(sorted(name for name, spec in tools.items() if int(spec["arity"]) == 2))
    ternary = tuple(sorted(name for name, spec in tools.items() if int(spec["arity"]) == 3))
    components: list[Expression] = [dict(atom) for atom in atoms]
    for tool in binary:
        for left in atoms:
            for right in atoms:
                components.append(_call(tool, left, right))
    generated: dict[str, Expression] = {}
    for tool in binary:
        for left in components:
            for right in components:
                expression = _call(tool, left, right)
                if _expression_nodes(expression) <= node_limit:
                    generated.setdefault(_expression_key(expression), expression)
    composites = tuple(component for component in components if component.get("kind") == "call")
    for tool in ternary:
        for first in atoms:
            for second in atoms:
                for third in atoms:
                    expression = _call(tool, first, second, third)
                    generated.setdefault(_expression_key(expression), expression)
        for position in range(3):
            for composite in composites:
                for first in atoms:
                    for second in atoms:
                        arguments = [dict(first), dict(second)]
                        arguments.insert(position, dict(composite))
                        expression = _call(tool, *arguments)
                        if _expression_nodes(expression) <= node_limit:
                            generated.setdefault(_expression_key(expression), expression)
    ordered = tuple(generated[key] for key in sorted(generated))
    if len(ordered) > candidate_budget:
        return ordered[:candidate_budget]
    return ordered


def _render_expression(expression: Mapping[str, object]) -> str:
    if expression.get("kind") == "arg":
        return f"args[{int(expression['index'])}]"
    tool = str(expression["tool"])
    children = expression.get("args")
    if not isinstance(children, list):
        raise M064Error("cannot render malformed expression")
    rendered = ",".join(_render_expression(child) for child in children if isinstance(child, Mapping))
    return f"tools[{json.dumps(tool)}]([{rendered}],tools)"


def _render_primitive_tool(name: str) -> str:
    if name == "max":
        expression = "Math.max(...args)"
    elif name == "min":
        expression = "Math.min(...args)"
    else:
        raise M064Error(f"unsupported bounded extension: {name}")
    return _support._js_header(
        f"tool_{name}",
        {"kind": "m064_primitive_extension", "tool_name": name, "primitive": name, "arity": 2},
    ) + f"export function {name}(args,tools){{return {expression};}}\nexport const TOOLS={{{name}}};\n"


def _render_constructed_tool(task_id: str, name: str, expression: Mapping[str, object]) -> str:
    meta = {
        "kind": "m064_constructed_tool",
        "task_id": task_id,
        "tool_name": name,
        "arity": 2,
        "expression_ast": expression,
        "referenced_tools": list(_expression_tools(expression)),
    }
    return _support._js_header(f"tool_{name}", meta) + (
        f"export function {name}(args,tools){{return {_render_expression(expression)};}}\n"
        f"export const TOOLS={{{name}}};\n"
    )


def _replace_modules(
    body: Mapping[str, object],
    replacements: Mapping[str, Mapping[str, object]],
    added_cases: Sequence[SoftwareCase],
) -> dict[str, object]:
    modules = dict(_module_map(body))
    modules.update(replacements)
    regression = [dict(item) for item in body.get("regression_cases", []) if isinstance(item, Mapping)]
    existing = {str(item["case_id"]) for item in regression}
    for case in added_cases:
        if case.case_id not in existing:
            regression.append(case.to_dict())
            existing.add(case.case_id)
    return {
        "schema": "m048-js-body-v1",
        "modules": [dict(modules[name]) for name in sorted(modules)],
        "regression_cases": regression,
    }


def _changed_modules(parent: Mapping[str, object], candidate: Mapping[str, object]) -> list[str]:
    before = _module_map(parent)
    after = _module_map(candidate)
    return sorted(
        name
        for name in set(before) | set(after)
        if name not in before
        or name not in after
        or before[name].get("source") != after[name].get("source")
    )


def _materialize_candidate(
    body: Mapping[str, object],
    task_id: str,
    token: str,
    public_cases: Sequence[SoftwareCase],
    expression: Mapping[str, object],
    tools: Mapping[str, Mapping[str, object]],
    protocol: M064Protocol,
) -> dict[str, object]:
    modules = _module_map(body)
    interpretation_meta = modules["interpretation"].get("meta")
    selection_meta = modules["selection"].get("meta")
    if not isinstance(interpretation_meta, Mapping) or not isinstance(selection_meta, Mapping):
        raise M064Error("native parser or selector metadata is malformed")
    aliases = {str(key): str(value) for key, value in dict(interpretation_meta["aliases"]).items()}
    routes = {str(key): str(value) for key, value in dict(selection_meta["routes"]).items()}
    aliases[token] = token
    routes[token] = token
    arities = {name: int(spec["arity"]) for name, spec in tools.items()}
    arities[token] = 2
    replacements: dict[str, dict[str, object]] = {
        "interpretation": {
            "name": "interpretation",
            "source": _render_interpretation(aliases, arities),
            "meta": {"kind": "m064_recursive_prefix_parser", "aliases": dict(sorted(aliases.items())), "arities": dict(sorted(arities.items()))},
        },
        "selection": {
            "name": "selection",
            "source": _render_selection(routes),
            "meta": {"kind": "m064_route_table", "routes": dict(sorted(routes.items()))},
        },
        f"tool_{token}": {
            "name": f"tool_{token}",
            "source": _render_constructed_tool(task_id, token, expression),
            "meta": {
                "kind": "m064_constructed_tool",
                "task_id": task_id,
                "tool_name": token,
                "arity": 2,
                "expression_ast": dict(expression),
                "referenced_tools": list(_expression_tools(expression)),
            },
        },
    }
    if modules["execution"].get("meta", {}).get("kind") != "m064_registry_aware_stack_executor":
        replacements["execution"] = {
            "name": "execution",
            "source": _render_registry_execution(),
            "meta": {"kind": "m064_registry_aware_stack_executor"},
        }
    referenced = set(_expression_tools(expression))
    for extension in protocol.extensions:
        if extension in referenced and f"tool_{extension}" not in modules:
            replacements[f"tool_{extension}"] = {
                "name": f"tool_{extension}",
                "source": _render_primitive_tool(extension),
                "meta": {"kind": "m064_primitive_extension", "tool_name": extension, "primitive": extension, "arity": 2},
            }
    candidate_body = _replace_modules(body, replacements, public_cases)
    if _body_bytes(candidate_body) > protocol.max_candidate_bytes:
        raise M064Error("constructed native candidate exceeds the size bound")
    changed = _changed_modules(body, candidate_body)
    expression_digest = _digest(b"m064-expression-v1\x00", expression)
    return {
        "template_id": f"m064_constructed_{expression_digest[:20]}",
        "expression_digest": expression_digest,
        "expression_ast": dict(expression),
        "referenced_tools": list(_expression_tools(expression)),
        "changed_modules": changed,
        "added_modules": [name for name in changed if name not in modules],
        "candidate_body": candidate_body,
    }


def _parse_binary_case(case: SoftwareCase, token: str) -> tuple[float, float]:
    parts = case.request.split()
    if len(parts) != 3 or parts[0] != token:
        raise M064Error("M064 task cases must be binary prefix requests")
    return float(parts[1]), float(parts[2])


def _propose_constructed_tools(
    body: Mapping[str, object],
    tool_registry: Mapping[str, Mapping[str, object]],
    task_id: str,
    public_cases: Sequence[SoftwareCase],
    protocol: M064Protocol,
) -> dict[str, object]:
    """Propose from public evidence only; hidden evidence is absent by construction."""
    tokens = {case.request.split()[0] for case in public_cases}
    if len(tokens) != 1:
        raise M064Error("public cases do not identify one unknown task token")
    token = next(iter(tokens))
    incumbent = _isolated_node_call(
        "execute",
        {"body": body, "cases": [case.to_dict() for case in public_cases]},
        protocol,
    )
    failures = [item for item in incumbent.get("case_results", []) if not item.get("passed")]
    diagnosed = bool(failures) and all(
        item.get("result", {}).get("error_stage") == "interpretation"
        and item.get("result", {}).get("error_message") == f"unknown_operator:{token}"
        for item in failures
    )
    if not diagnosed:
        return {
            "schema": "m064-public-proposal-v1",
            "task_id": task_id,
            "token": token,
            "diagnosis": None,
            "incumbent_public_passes": sum(
                1 for item in incumbent.get("case_results", []) if item.get("passed")
            ),
            "candidate_budget": protocol.candidate_budget_per_arm_cycle,
            "expressions_constructed": 0,
            "complete_program_space_enumerated": False,
            "public_survivor_count": 0,
            "public_survivors": [],
            "constructor_registry_digest": _digest(b"m064-tool-specs-v1\x00", tool_registry),
        }
    expressions = _enumerate_expression_candidates(
        tool_registry,
        protocol.expression_node_limit,
        protocol.candidate_budget_per_arm_cycle,
    )
    survivors: list[dict[str, object]] = []
    for expression in expressions:
        passed = True
        for case in public_cases:
            arguments = _parse_binary_case(case, token)
            observed = _round_two(_evaluate_expression(expression, arguments, tool_registry))
            if observed != case.expected:
                passed = False
                break
        if not passed:
            continue
        candidate = _materialize_candidate(
            body, task_id, token, public_cases, expression, tool_registry, protocol
        )
        native_public = _isolated_node_call(
            "execute",
            {"body": candidate["candidate_body"], "cases": [case.to_dict() for case in public_cases]},
            protocol,
        )
        if native_public.get("all_passed"):
            survivors.append(candidate)
    return {
        "schema": "m064-public-proposal-v1",
        "task_id": task_id,
        "token": token,
        "diagnosis": {
            "stage": "interpretation",
            "limitation": f"unknown_operator:{token}",
            "predicted_recovery": "extend parser, route table and owned tool registry",
            "emitted_before_hidden_validation": True,
        },
        "incumbent_public_passes": sum(1 for item in incumbent.get("case_results", []) if item.get("passed")),
        "candidate_budget": protocol.candidate_budget_per_arm_cycle,
        "expressions_constructed": len(expressions),
        "complete_program_space_enumerated": False,
        "public_survivor_count": len(survivors),
        "public_survivors": survivors,
        "constructor_registry_digest": _digest(b"m064-tool-specs-v1\x00", tool_registry),
    }


def _candidate_safety_audit(
    parent: Mapping[str, object],
    candidate: Mapping[str, object],
    token: str,
    protocol: M064Protocol,
) -> tuple[bool, str]:
    body = candidate.get("candidate_body")
    if not isinstance(body, Mapping):
        return False, "candidate_body_missing"
    changed = _changed_modules(parent, body)
    if changed != list(candidate.get("changed_modules", [])):
        return False, "changed_module_trace_mismatch"
    allowed = {"interpretation", "selection", "execution", f"tool_{token}"} | {
        f"tool_{name}" for name in protocol.extensions
    }
    if not set(changed).issubset(allowed) or f"tool_{token}" not in changed:
        return False, "mutation_scope_violation"
    if _body_bytes(body) > protocol.max_candidate_bytes:
        return False, "candidate_size_violation"
    for module in _module_map(body).values():
        source = str(module.get("source", "")).lower()
        if any(
            value in source
            for value in (
                "python",
                "subprocess",
                "child_process",
                "node:",
                "import ",
                "import(",
                "require(",
                "fetch(",
                "process.",
                "websocket",
                "xmlhttprequest",
            )
        ):
            return False, "semantic_delegation_token"
    modules = _module_map(body)
    for name in changed:
        item = modules[name]
        meta = item.get("meta")
        if not isinstance(meta, Mapping):
            return False, "generated_module_metadata_missing"
        if name == "interpretation":
            expected = _render_interpretation(meta.get("aliases", {}), meta.get("arities", {}))
        elif name == "selection":
            expected = _render_selection(meta.get("routes", {}))
        elif name == "execution":
            expected = _render_registry_execution()
        elif name == f"tool_{token}":
            expression = meta.get("expression_ast")
            if not isinstance(expression, Mapping):
                return False, "generated_expression_metadata_missing"
            expected = _render_constructed_tool(str(meta.get("task_id")), token, expression)
        elif name in {f"tool_{extension}" for extension in protocol.extensions}:
            expected = _render_primitive_tool(str(meta.get("tool_name")))
        else:
            return False, "unexpected_generated_module"
        if item.get("source") != expected:
            return False, "generated_source_trace_mismatch"
    return True, "passed"


def _independent_validate_public_class(
    parent_body: Mapping[str, object],
    proposal: Mapping[str, object],
    retained_cases: Sequence[SoftwareCase],
    public_cases: Sequence[SoftwareCase],
    hidden_cases: Sequence[SoftwareCase],
    protocol: M064Protocol,
) -> dict[str, object]:
    """Passively validate every public survivor; this function cannot adopt."""
    complete = tuple(retained_cases) + tuple(public_cases) + tuple(hidden_cases)
    retained_ids = {case.case_id for case in retained_cases}
    public_ids = {case.case_id for case in public_cases}
    hidden_ids = {case.case_id for case in hidden_cases}
    attempts: list[dict[str, object]] = []
    candidates = proposal.get("public_survivors")
    if not isinstance(candidates, list) or not candidates:
        return {
            "action": "terminate_insufficient_public_evidence",
            "reason": "no expression in the bounded public construction class survived",
            "selected_candidate": None,
            "attempts": attempts,
            "entire_public_class_validated": True,
        }
    token = str(proposal["token"])
    all_admitted = True
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            raise M064Error("proposal contains a malformed candidate")
        safe, safety_reason = _candidate_safety_audit(parent_body, candidate, token, protocol)
        if safe:
            execution = _isolated_node_call(
                "execute",
                {"body": candidate["candidate_body"], "cases": [case.to_dict() for case in complete]},
                protocol,
            )
            results = execution.get("case_results", [])
            retained_passed = sum(1 for item in results if item.get("case_id") in retained_ids and item.get("passed"))
            public_passed = sum(1 for item in results if item.get("case_id") in public_ids and item.get("passed"))
            hidden_passed = sum(1 for item in results if item.get("case_id") in hidden_ids and item.get("passed"))
        else:
            retained_passed = public_passed = hidden_passed = 0
        admitted = bool(
            safe
            and retained_passed == len(retained_ids)
            and public_passed == len(public_ids)
            and hidden_passed == len(hidden_ids)
        )
        all_admitted = all_admitted and admitted
        attempts.append(
            {
                "template_id": candidate["template_id"],
                "candidate_body_digest": _support._native_body_digest(candidate["candidate_body"]),
                "safety_reason": safety_reason,
                "retained_passed": retained_passed,
                "retained_total": len(retained_ids),
                "public_passed": public_passed,
                "public_total": len(public_ids),
                "hidden_passed": hidden_passed,
                "hidden_total": len(hidden_ids),
                "admitted": admitted,
            }
        )
    if not all_admitted:
        return {
            "action": "terminate_ambiguous_public_equivalence_class",
            "reason": "at least one public survivor disagreed with independent admission evidence",
            "selected_candidate": None,
            "attempts": attempts,
            "entire_public_class_validated": True,
        }
    selected = min(
        candidates,
        key=lambda item: _support._native_body_digest(item["candidate_body"]),
    )
    return {
        "action": "adopt",
        "reason": "every public survivor passed retained, public and hidden native admission",
        "selected_candidate": selected,
        "attempts": attempts,
        "entire_public_class_validated": True,
        "public_equivalence_class_size": len(candidates),
        "canonicalisation_after_admission": True,
    }


def _constructor_registry() -> dict[str, object]:
    constructor_source = inspect.getsource(_enumerate_expression_candidates)
    evaluator_source = inspect.getsource(_evaluate_expression)
    renderer_source = inspect.getsource(_render_expression)
    mapping = {
        "schema": "m064-serialised-construction-registry-v1",
        "constructor": {
            "name": "bounded_expression_constructor",
            "implementation_source": constructor_source,
            "implementation_sha256": hashlib.sha256(constructor_source.encode("utf-8")).hexdigest(),
        },
        "evaluator": {
            "name": "recursive_owned_tool_evaluator",
            "implementation_source": evaluator_source,
            "implementation_sha256": hashlib.sha256(evaluator_source.encode("utf-8")).hexdigest(),
        },
        "renderer": {
            "name": "node_registry_call_renderer",
            "implementation_source": renderer_source,
            "implementation_sha256": hashlib.sha256(renderer_source.encode("utf-8")).hexdigest(),
        },
    }
    return {**mapping, "digest": _digest(b"m064-construction-registry-v1\x00", mapping)}


@dataclass(frozen=True)
class M064Manifest:
    mapping: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return dict(self.mapping)

    def to_bytes(self) -> bytes:
        return _canonical_json(self.mapping)

    def digest(self) -> str:
        return _digest(b"m064-manifest-v1\x00", self.mapping)


def _execute_cases(body: Mapping[str, object], cases: Sequence[SoftwareCase]) -> Mapping[str, object]:
    return _isolated_node_call(
        "execute",
        {"body": body, "cases": [case.to_dict() for case in cases]},
        M064_PROTOCOL,
    )


def _migration_precedes_task_selection(
    event_trace: Sequence[Mapping[str, object]],
    required_arms: Sequence[str],
) -> bool:
    migrations = {
        str(event.get("arm")): int(event["sequence"])
        for event in event_trace
        if event.get("event") == "arm_migrated" and "sequence" in event
    }
    selections = [
        int(event["sequence"])
        for event in event_trace
        if event.get("event") == "task_bank_selected" and "sequence" in event
    ]
    return bool(
        set(migrations) == set(required_arms)
        and len(selections) == 1
        and max(migrations.values()) < selections[0]
    )


def _strict_quality_advantage(
    quality: Mapping[str, Mapping[str, object]],
    complete_name: str,
) -> bool:
    complete = int(quality[complete_name]["hidden_passes"])
    return bool(
        quality[complete_name].get("exact")
        and all(
            complete > int(result["hidden_passes"])
            for name, result in quality.items()
            if name != complete_name
        )
    )


def _body_contains_delegation(body: Mapping[str, object]) -> bool:
    forbidden = (
        "python",
        "subprocess",
        "child_process",
        "node:",
        "import ",
        "import(",
        "require(",
        "fetch(",
        "process.",
        "websocket",
        "xmlhttprequest",
    )
    return any(
        token in str(module.get("source", "")).lower()
        for module in _module_map(body).values()
        for token in forbidden
    )


def _arm_record(
    name: str,
    body: Mapping[str, object],
    retained: Sequence[SoftwareCase],
    *,
    state: Mapping[str, object] | None,
    ablate_inherited_learning: bool,
    provenance: Mapping[str, object],
) -> dict[str, object]:
    migration_execution = _execute_cases(body, retained)
    if not migration_execution.get("all_passed"):
        raise M064Error(f"arm {name} failed its predeclared pre-task capabilities")
    return {
        "name": name,
        "body": body,
        "state": state,
        "retained": tuple(retained),
        "ablate_inherited_learning": ablate_inherited_learning,
        "provenance": dict(provenance),
        "migration_body_digest": _support._native_body_digest(body),
        "migration_retained_passed": len(retained),
        "cycles": [],
    }


def _build_arms(protocol: M064Protocol) -> tuple[dict[str, dict[str, object]], Mapping[str, object]]:
    source = _source_snapshots()
    snapshots = source["snapshots"]
    memories = source["memories"]
    retained = source["retained"]
    complete_state = _lineage._build_migrated_state(snapshots[6], memories[6], m048.M048_PROTOCOL)
    registry = _constructor_registry()
    complete_state = {**complete_state, "m064_constructor_registry": registry}
    _lineage._audit_native_state(complete_state)
    ablated_state = json.loads(json.dumps(complete_state))
    parent_body = _compile_control_body(snapshots[2].accepted_body, protocol)
    fresh_body = _compile_control_body(founder_software_body(), protocol)
    arms = {
        "complete_continued_lineage": _arm_record(
            "complete_continued_lineage",
            complete_state["body"],
            retained[6],
            state=complete_state,
            ablate_inherited_learning=False,
            provenance={"source_version": 6, "continuous_m048_state": True},
        ),
        "fresh_on_b": _arm_record(
            "fresh_on_b",
            fresh_body,
            BASELINE_CASES,
            state=None,
            ablate_inherited_learning=True,
            provenance={"source_version": 0, "continuous_m048_state": False, "native_founder": True},
        ),
        "unchanged_parent_migrated": _arm_record(
            "unchanged_parent_migrated",
            parent_body,
            retained[2],
            state=None,
            ablate_inherited_learning=True,
            provenance={"source_version": 2, "continuous_m048_state": False, "pre_mean_parent": True},
        ),
        "learned_state_ablated": _arm_record(
            "learned_state_ablated",
            ablated_state["body"],
            retained[6],
            state=ablated_state,
            ablate_inherited_learning=True,
            provenance={"source_version": 6, "continuous_m048_state": True, "mean_available_to_execution": True, "mean_withheld_from_constructor": True},
        ),
    }
    if tuple(arms) != protocol.arms:
        raise M064Error("four-arm order drifted from the protocol")
    return arms, source


def _run_selected_bank(
    bank_index: int,
    protocol: M064Protocol,
    *,
    selection_mode: str,
) -> M064Manifest:
    if not 0 <= bank_index < protocol.task_bank_entries:
        raise M064Error("task-bank index is outside the frozen bank")
    arms, source = _build_arms(protocol)
    # The bank is selected only after all four bodies have crossed into Node.
    event_trace: list[dict[str, object]] = [
        {"sequence": index, "event": "arm_migrated", "arm": arm_name}
        for index, arm_name in enumerate(protocol.arms, start=1)
    ]
    event_trace.append(
        {
            "sequence": len(event_trace) + 1,
            "event": "task_bank_selected",
            "selection_mode": selection_mode,
            "bank_index": bank_index,
        }
    )
    migration_before_selection = _migration_precedes_task_selection(
        event_trace, protocol.arms
    )
    if not migration_before_selection:
        raise M064Error("task bank was selected before every arm migrated")
    tasks = M064_TASK_BANK[bank_index]
    forced_rollback: dict[str, object] | None = None
    admitted_selections: list[Mapping[str, object]] = []
    all_hidden: list[SoftwareCase] = []
    for cycle_number, task in enumerate(tasks, start=1):
        public = task.public_cases()
        hidden = task.hidden_cases()
        all_hidden.extend(hidden)
        for arm_name in protocol.arms:
            arm = arms[arm_name]
            body = arm["body"]
            if not isinstance(body, Mapping):
                raise M064Error("arm body is malformed")
            tool_specs = _body_tool_specs(
                body,
                ablate_inherited_learning=bool(arm["ablate_inherited_learning"]),
                extensions=protocol.extensions,
            )
            proposal = _propose_constructed_tools(
                body, tool_specs, task.task_id, public, protocol
            )
            if not isinstance(proposal.get("diagnosis"), Mapping):
                raise M064Error(f"arm {arm_name} did not diagnose the public failure before search")
            selection = _independent_validate_public_class(
                body,
                proposal,
                arm["retained"],
                public,
                hidden,
                protocol,
            )
            adopted = False
            rollback_receipt: Mapping[str, object] | None = None
            if arm_name == "complete_continued_lineage":
                if selection.get("action") != "adopt":
                    raise M064Error(f"complete lineage failed closed in cycle {cycle_number}: {selection.get('reason')}")
                selected = selection.get("selected_candidate")
                if not isinstance(selected, Mapping):
                    raise M064Error("admitted selection lacks a candidate")
                references = set(selected.get("referenced_tools", []))
                if not set(task.required_prior_tools).issubset(references):
                    raise M064Error("a later accepted cycle did not reuse its required earlier tool")
                state = arm["state"]
                if not isinstance(state, Mapping):
                    raise M064Error("complete arm lost its versioned native state")
                if cycle_number == 1:
                    restored, rollback_receipt = _lineage._adopt_native_candidate(
                        state,
                        f"{task.task_id}_forced_fault",
                        selection,
                        forced_fault=True,
                    )
                    restored_execution = _execute_cases(restored["body"], arm["retained"])
                    if not rollback_receipt.get("exact_restoration") or not restored_execution.get("all_passed"):
                        raise M064Error("forced native fault failed exact code-and-behaviour restoration")
                    forced_rollback = {
                        **dict(rollback_receipt),
                        "restored_behaviour_passed": True,
                        "restored_body_digest": _support._native_body_digest(restored["body"]),
                    }
                    state = restored
                updated, receipt = _lineage._adopt_native_candidate(
                    state, task.task_id, selection
                )
                if not receipt.get("adopted"):
                    raise M064Error("independently admitted native candidate was not adopted")
                arm["state"] = updated
                arm["body"] = updated["body"]
                arm["retained"] = tuple(arm["retained"]) + public + hidden
                adopted = True
                admitted_selections.append(selection)
            elif selection.get("action") == "adopt":
                raise M064Error(f"control arm {arm_name} unexpectedly solved cycle {cycle_number}")
            current_hidden = _execute_cases(arm["body"], hidden)
            hidden_passes = sum(1 for item in current_hidden.get("case_results", []) if item.get("passed"))
            arm["cycles"].append(
                {
                    "cycle": cycle_number,
                    "task_id": task.task_id,
                    "proposal_digest": _digest(b"m064-proposal-v1\x00", proposal),
                    "diagnosis": proposal["diagnosis"],
                    "expressions_constructed": proposal["expressions_constructed"],
                    "public_survivors": proposal["public_survivor_count"],
                    "selection_action": selection["action"],
                    "entire_public_class_validated": selection["entire_public_class_validated"],
                    "validation_attempts": len(selection["attempts"]),
                    "adopted": adopted,
                    "hidden_passes_after_cycle": hidden_passes,
                    "hidden_total": len(hidden),
                    "selected_template": (
                        selection["selected_candidate"]["template_id"]
                        if isinstance(selection.get("selected_candidate"), Mapping)
                        else None
                    ),
                    "selected_referenced_tools": (
                        selection["selected_candidate"]["referenced_tools"]
                        if isinstance(selection.get("selected_candidate"), Mapping)
                        else []
                    ),
                    "rollback_receipt": dict(rollback_receipt) if rollback_receipt else None,
                }
            )
    if forced_rollback is None:
        raise M064Error("the predeclared forced rollback did not execute")
    complete = arms["complete_continued_lineage"]
    complete_state = complete["state"]
    if not isinstance(complete_state, Mapping) or complete_state.get("version") != 10:
        raise M064Error("complete lineage did not reach exactly three accepted native cycles")
    final_retained_execution = _execute_cases(complete["body"], complete["retained"])
    if not final_retained_execution.get("all_passed"):
        raise M064Error("complete final lineage regressed a retained capability")
    final_retained_passed = sum(
        1 for item in final_retained_execution.get("case_results", []) if item.get("passed")
    )
    quality: dict[str, dict[str, object]] = {}
    for name, arm in arms.items():
        execution = _execute_cases(arm["body"], all_hidden)
        passes = sum(1 for item in execution.get("case_results", []) if item.get("passed"))
        quality[name] = {"hidden_passes": passes, "hidden_total": len(all_hidden), "exact": passes == len(all_hidden)}
    strict_advantage = _strict_quality_advantage(
        quality, "complete_continued_lineage"
    )
    if not strict_advantage:
        raise M064Error("complete lineage lacks strict held-out quality advantage")

    # Replay starts again from the exact migrated version-seven state and applies
    # only the independently admitted selections.  The selected tasks and hidden
    # evidence do not participate in replay.
    snapshots = source["snapshots"]
    memories = source["memories"]
    replay = _lineage._build_migrated_state(snapshots[6], memories[6], m048.M048_PROTOCOL)
    replay = {**replay, "m064_constructor_registry": _constructor_registry()}
    replay_restored, replay_rollback = _lineage._adopt_native_candidate(
        replay,
        f"{tasks[0].task_id}_forced_fault",
        admitted_selections[0],
        forced_fault=True,
    )
    if not replay_rollback.get("exact_restoration"):
        raise M064Error("replay forced rollback diverged")
    replay = replay_restored
    for task, selection in zip(tasks, admitted_selections):
        replay, receipt = _lineage._adopt_native_candidate(replay, task.task_id, selection)
        if not receipt.get("adopted"):
            raise M064Error("deterministic adoption replay failed")
    replay_identical = _support._native_state_digest(replay) == _support._native_state_digest(complete_state)
    if not replay_identical:
        raise M064Error("complete real-substrate lineage did not replay identically")

    arm_results: dict[str, object] = {}
    for name, arm in arms.items():
        cycles = arm["cycles"]
        native_process_invocations = 2 + sum(
            2 + int(cycle["public_survivors"]) + int(cycle["validation_attempts"])
            for cycle in cycles
        )
        if name == "complete_continued_lineage":
            native_process_invocations += 2  # rollback behaviour and final retained suite
        arm_results[name] = {
            "provenance": arm["provenance"],
            "migration_body_digest": arm["migration_body_digest"],
            "migration_retained_passed": arm["migration_retained_passed"],
            "equal_candidate_budget_per_cycle": protocol.candidate_budget_per_arm_cycle,
            "cycles": cycles,
            "accepted_cycles": sum(1 for cycle in cycles if cycle["adopted"]),
            "final_body_digest": _support._native_body_digest(arm["body"]),
            "held_out_quality": quality[name],
            "cost_accounting": {
                "expressions_constructed": sum(int(cycle["expressions_constructed"]) for cycle in cycles),
                "public_candidate_processes": sum(int(cycle["public_survivors"]) for cycle in cycles),
                "independent_validation_processes": sum(int(cycle["validation_attempts"]) for cycle in cycles),
                "native_process_invocations": native_process_invocations,
                "accepted_rewrites": sum(1 for cycle in cycles if cycle["adopted"]),
            },
        }
    constructor_parameters = inspect.signature(_propose_constructed_tools).parameters
    validator_source = inspect.getsource(_independent_validate_public_class)
    constructor_receives_hidden = any("hidden" in name for name in constructor_parameters)
    validator_owns_adoption = any(
        token in validator_source
        for token in ("_adopt_native_candidate", "patch_registry", "native_journal")
    )
    semantic_delegation = any(
        _body_contains_delegation(arm["body"]) for arm in arms.values()
    )
    mapping = {
        "schema": "m064-real-substrate-completion-manifest-v1",
        "protocol_digest": protocol.digest(),
        "task_bank_commitment": protocol.task_bank_commitment,
        "selected_bank_index": bank_index,
        "selection_mode": selection_mode,
        "selected_task_commitments": [task.commitment() for task in tasks],
        "source_m047_manifest_digest": source["artifacts"].manifest.digest(),
        "source_version": 6,
        "migration_version": 7,
        "source_runtime": protocol.source_runtime,
        "target_runtime": protocol.target_runtime,
        "constructor_registry": _constructor_registry(),
        "constructor_receives_hidden_cases": constructor_receives_hidden,
        "validator_owns_adoption": validator_owns_adoption,
        "semantic_delegation_to_python": semantic_delegation,
        "event_trace": event_trace,
        "all_arms_migrated_before_task_selection": migration_before_selection,
        "execution_limits": {
            "wall_timeout_seconds": protocol.node_timeout_seconds,
            "node_old_space_megabytes": 128,
            "filesystem": "disposable_working_directory_and_body_directory",
            "network_and_syscalls": "unavailable_to_exact_rendered_candidate_grammar",
            "expression_node_limit": protocol.expression_node_limit,
            "candidate_budget_per_arm_cycle": protocol.candidate_budget_per_arm_cycle,
        },
        "arm_results": arm_results,
        "forced_rollback": forced_rollback,
        "complete_final_version": complete_state["version"],
        "complete_original_retained_cases": 28,
        "complete_final_retained_cases": len(complete["retained"]),
        "complete_final_retained_passed": final_retained_passed,
        "strict_held_out_advantage": strict_advantage,
        "replay_identical": replay_identical,
        "claim_scope": "bounded_real_node_substrate_four_arm_three_cycle_post_migration_completion_candidate",
        "canonical_workflow_authorised": False,
        "repository_write_authority_granted_to_lineage": False,
    }
    return M064Manifest(mapping)


def run_m064_development(
    bank_index: int = 0,
    protocol: M064Protocol = M064_PROTOCOL,
) -> M064Manifest:
    """Run the authoritative whole-WebAssembly development experiment."""
    from metamorphosis.m064_whole_wasm_completion import run_m064_development as run

    return run(bank_index, protocol)


def run_m064_canonical(
    marker_parent_sha: str,
    protocol: M064Protocol = M064_PROTOCOL,
) -> M064Manifest:
    """Run the authoritative marker-selected whole-WebAssembly experiment."""
    from metamorphosis.m064_whole_wasm_completion import run_m064_canonical as run

    return run(marker_parent_sha, protocol)


__all__ = [
    "M064Error",
    "M064Manifest",
    "M064Protocol",
    "M064_PROTOCOL",
    "M064_TASK_BANK",
    "run_m064_canonical",
    "run_m064_development",
    "select_task_bank",
]
