"""Generated executable bodies as inert canonical data.

Every body this runtime has run so far was an importable symbol the host installed before the lineage
started. `World.artifacts` names them, `Transform.body` selects one, and the demonstration's
"improved descendants" existed at admission. That is selection from a host-authored catalogue, and
the objective asks for something else: a lineage that **modifies its body**, which means a body that
was not there before.

The obvious way to get one — generate Python source and import it — would hand back every authority
the runtime has spent this whole review closing. `eval`, `exec`, a dynamic import or a
candidate-controlled deserialiser all put lineage-produced code in the evaluator's interpreter before
anything has been isolated.

So a generated body here is **data**: a small expression graph in canonical JSON, executed by a fixed
interpreter that lives on the far side of the sandbox boundary. The program changes; the interpreter
does not. That is the same reason bytecode is a program even though nobody rewrites the VM per
program, and it is what lets identity be exact rather than symbolic — the canonical bytes *are* the
body, so `binds_exact_executed_bytes` is true here for the first time in this runtime.

The grammar is deliberately tiny:

    input(field)              read one named field of the task
    constant(value)           an inert literal
    call(operation, args...)  apply one operation from the admitted registry

A node may only reference nodes before it, so a program is acyclic by construction rather than by a
check that could be wrong. The operation registry is the same bounded alphabet the probe apparatus
composes over: **the host supplies the alphabet, the lineage writes the sentence.**

What this does not do: there is no recursion, no branching and no state. A body that needs those is
outside this grammar, and the honest reading of that is that the grammar is a first bounded step, not
that programs of this shape are all a lineage could want.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

PROGRAM_SCHEMA = "genesis-program-v1"

#: What a node may be. Anything else is refused rather than interpreted generously.
NODE_KINDS = ("input", "constant", "call")


class ProgramError(RuntimeError):
    """Raised when a program is not a program, or asks for something the grammar does not have."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _clean_nodes(nodes: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Validate every node against the grammar, and against the nodes before it.

    Validation happens here, once, on canonical data — not in the interpreter, which runs inside the
    sandbox where a refusal is an `error` row rather than a legible complaint.
    """
    if not nodes:
        raise ProgramError("a program with no nodes computes nothing")
    cleaned: list[dict[str, Any]] = []
    for index, node in enumerate(nodes):
        if not isinstance(node, Mapping):
            raise ProgramError("node %d is not a record" % index)
        kind = node.get("op")
        if kind not in NODE_KINDS:
            raise ProgramError("node %d has no recognised operation kind: %r" % (index, kind))
        if kind == "input":
            field = node.get("field")
            if not isinstance(field, str) or not field:
                raise ProgramError("node %d reads no named task field" % index)
            cleaned.append({"op": "input", "field": field})
        elif kind == "constant":
            value = node.get("value")
            if not isinstance(value, (bool, int, float, str)) and value is not None:
                raise ProgramError("node %d holds a constant this grammar cannot carry" % index)
            cleaned.append({"op": "constant", "value": value})
        else:
            operation = node.get("operation")
            if not isinstance(operation, str) or not operation:
                raise ProgramError("node %d calls no named operation" % index)
            arguments = list(node.get("args") or [])
            for argument in arguments:
                if not isinstance(argument, int) or isinstance(argument, bool):
                    raise ProgramError("node %d takes an argument that is not a node index" % index)
                if not 0 <= argument < index:
                    # Forward and self references are what a cycle is made of. Refusing them here
                    # means acyclicity is a property of the grammar rather than of a later check.
                    raise ProgramError(
                        "node %d references node %d, which does not come before it; a program may "
                        "only build on what it has already computed" % (index, argument)
                    )
            cleaned.append({"op": "call", "operation": operation, "args": arguments})
    return cleaned


def program(
    *,
    nodes: Sequence[Mapping[str, Any]],
    root: int,
    registry_reference: str,
    inputs: Sequence[str] = ("input",),
    declared_dependencies: Sequence[str] = (),
) -> dict[str, Any]:
    """Build one canonical program. The returned value is the body; nothing else is."""
    cleaned = _clean_nodes(nodes)
    if not isinstance(root, int) or isinstance(root, bool) or not 0 <= root < len(cleaned):
        raise ProgramError("the program's root is not one of its nodes")
    declared_inputs = [str(name) for name in inputs]
    for index, node in enumerate(cleaned):
        if node["op"] == "input" and node["field"] not in declared_inputs:
            raise ProgramError(
                "node %d reads %r, which this program did not declare as an input" % (index, node["field"])
            )
    if not str(registry_reference):
        raise ProgramError("a program names the operation registry it composes over")
    payload = {
        "schema": PROGRAM_SCHEMA,
        "inputs": declared_inputs,
        "nodes": cleaned,
        "root": int(root),
        "registry_reference": str(registry_reference),
        "declared_dependencies": sorted(str(name) for name in declared_dependencies),
    }
    return payload


def operations_used(value: Mapping[str, Any]) -> list[str]:
    """Which registry operations this program calls, as a set, read off the program itself."""
    return sorted({node["operation"] for node in value["nodes"] if node["op"] == "call"})


def calls_in_order(value: Mapping[str, Any]) -> list[str]:
    """The calls this program makes, in the order it makes them.

    `operations_used` collapses to a set, which is the right answer to "what does this reach for"
    and the wrong one for "which program is this": `increment` twice and `increment` once share a
    set, and so do `increment` then `double` and `double` then `increment`. A search record that
    cannot tell two evaluated candidates apart is a weak record, and these records are what a later
    policy would have to reason over.
    """
    return [node["operation"] for node in value["nodes"] if node["op"] == "call"]


def evaluate(value: Mapping[str, Any], task: Mapping[str, Any], registry: Mapping[str, Any]) -> Any:
    """Run one program over one task. Called inside the sandbox, after limits exist.

    Deliberately not defensive about the grammar: `program()` validated the shape before the artifact
    was ever admitted, and re-litigating that here would put the check on the wrong side of the
    boundary. What it does refuse is an operation the admitted registry does not contain, because
    that depends on the world rather than on the program.
    """
    computed: list[Any] = []
    for node in value["nodes"]:
        kind = node["op"]
        if kind == "input":
            if node["field"] not in task:
                raise ProgramError("this task carries no field %r" % node["field"])
            computed.append(task[node["field"]])
        elif kind == "constant":
            computed.append(node["value"])
        else:
            operation = registry.get(node["operation"])
            if operation is None:
                raise ProgramError(
                    "this program calls %r, which the admitted registry does not have"
                    % node["operation"]
                )
            computed.append(operation(*[computed[index] for index in node["args"]]))
    return computed[value["root"]]


class ProgramBody:
    """The body a program is. Constructed in the child, after isolation exists."""

    def __init__(self, value: Mapping[str, Any]) -> None:
        self.program = dict(value)

    def attempt(self, task: Mapping[str, Any]) -> Any:
        from genesis.probe import resolve_registry

        registry = resolve_registry(self.program["registry_reference"])
        return evaluate(self.program, task, registry)


@dataclass(frozen=True)
class ProgramArtifact:
    """A generated body, identified by the exact bytes that are it.

    This is the first artifact in this runtime whose identity binds what actually executes rather
    than an importable symbol plus its module's source. There is nothing behind the digest to drift:
    change one byte of the program and it is a different program, because the program is the bytes.
    """

    value: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", json.loads(canonical_bytes(dict(self.value)).decode()))
        if self.value.get("schema") != PROGRAM_SCHEMA:
            raise ProgramError("this is not a canonical program")

    def __call__(self) -> ProgramBody:
        return ProgramBody(self.value)

    def exact_artifact_bytes(self) -> bytes:
        """What `trust_root.artifact_digest_of` binds: the program, byte for byte."""
        return canonical_bytes(self.value)

    def artifact_kind(self) -> str:
        return PROGRAM_SCHEMA

    def operations(self) -> list[str]:
        return operations_used(self.value)

    def calls(self) -> list[str]:
        return calls_in_order(self.value)


def program_artifact(value: Mapping[str, Any]) -> ProgramArtifact:
    return ProgramArtifact(value=value)


def enumerate_programs(
    operations: Sequence[str],
    *,
    registry_reference: str,
    max_nodes: int = 3,
    field: str = "input",
):
    """Every straight-line program over these operations, shortest first.

    Deterministic and exhaustive, because the point of the first bounded search is that the runtime
    *constructs* the candidates — not that it constructs them cleverly. Shortest-first means the
    budget buys the simple explanations before the elaborate ones, which is the same ordering the
    probe search already uses and for the same reason.

    The chains are unary compositions of the admitted alphabet. That is a small space on purpose: a
    caller can reason about how large it is before spending a lineage's budget on it, which is not
    true of a generator whose reach is a function of its own cleverness.
    """
    from itertools import product

    alphabet = list(dict.fromkeys(str(name) for name in operations))
    depth = max(0, int(max_nodes) - 1)
    for length in range(1, depth + 1):
        for chain in product(alphabet, repeat=length):
            nodes: list[dict[str, Any]] = [{"op": "input", "field": field}]
            for step, operation in enumerate(chain):
                nodes.append({"op": "call", "operation": operation, "args": [step]})
            yield program(
                nodes=nodes,
                root=len(nodes) - 1,
                registry_reference=registry_reference,
                inputs=(field,),
            )
