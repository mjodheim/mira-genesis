"""Lineage-extensible transformation operators for Genesis v2 DEVELOPMENT work.

Genesis v1 can evolve a search policy, but the *kinds* of policy mutation remain host-written in
``genesis.policy_mutations``. This module introduces the deliberately smaller lower substrate that
Genesis v2 needs in order to attack that ceiling without giving mutable code access to the trust
root, evaluator, budget or isolation boundary.

A transformation operator is canonical data: a canonically ordered program of micro-steps interpreted
by fixed apparatus. A transformation language is also canonical data and names which operators the
lineage currently holds. Extending the language adds a new operator definition while preserving an
explicit parent-language digest. The lower micro-step kernel is still host-written DEVELOPMENT
apparatus; therefore this module is a substrate for open-metamorphosis experiments, not evidence that
the v2 objective has been reached.

The canonical order removes representation aliases from the lower language: two independent edits do
not become two candidate operators merely because their textual order was swapped. Acquired operators
may themselves become lower-language primitives through ``invoke_held_operator``. That invocation is
by content digest, must resolve inside the current language, and is recursively flattened to the same
fixed primitive kernel before execution. A missing or cyclic dependency fails closed.

No ``eval``, ``exec``, generated import or arbitrary attribute mutation is used. Operators can only
edit the bounded fields already present in a generated search policy.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from genesis import policies
from genesis.probe import resolve_registry
from genesis.trust_root import digest_of

STEP_SCHEMA = "genesis-transformation-micro-step-v1"
OPERATOR_SCHEMA = "genesis-transformation-operator-v1"
LANGUAGE_SCHEMA = "genesis-transformation-language-v1"

MICRO_STEP_KINDS = (
    "append_policy_operation",
    "increase_policy_depth",
    "increase_candidate_limit",
    "invoke_held_operator",
)
_STEP_RANK = {name: index for index, name in enumerate(MICRO_STEP_KINDS)}


class TransformationLanguageError(RuntimeError):
    """Raised when a v2 transformation program exceeds its admitted lower-language boundary."""


def create_step(
    kind: str,
    *,
    operation: str = "",
    amount: int = 1,
    operator_digest: str = "",
) -> dict[str, Any]:
    kind = str(kind)
    operation = str(operation)
    amount = int(amount)
    operator_digest = str(operator_digest)
    if kind not in MICRO_STEP_KINDS:
        raise TransformationLanguageError("unrecognised transformation micro-step %r" % kind)
    if kind == "append_policy_operation":
        if not operation:
            raise TransformationLanguageError("append_policy_operation names no operation")
        if amount != 1:
            raise TransformationLanguageError("append_policy_operation does not use a numeric amount")
        if operator_digest:
            raise TransformationLanguageError("append_policy_operation may not invoke an operator")
    elif kind == "invoke_held_operator":
        if operation:
            raise TransformationLanguageError("invoke_held_operator may not carry a body operation")
        if amount != 1:
            raise TransformationLanguageError("invoke_held_operator does not use a numeric amount")
        if not operator_digest:
            raise TransformationLanguageError("invoke_held_operator names no held operator digest")
    else:
        if operation:
            raise TransformationLanguageError("%s may not carry an operation name" % kind)
        if operator_digest:
            raise TransformationLanguageError("%s may not invoke an operator" % kind)
        if amount <= 0:
            raise TransformationLanguageError("transformation micro-step amount must be positive")
        if kind == "increase_policy_depth" and amount != 1:
            raise TransformationLanguageError("policy depth may increase by exactly one per micro-step")
    payload = {
        "schema": STEP_SCHEMA,
        "kind": kind,
        "operation": operation,
        "amount": amount,
        "operator_digest": operator_digest,
    }
    return {**payload, "step_digest": digest_of(payload)}


def validate_step(record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping) or record.get("schema") != STEP_SCHEMA:
        raise TransformationLanguageError("transformation micro-step uses an unrecognised schema")
    rebuilt = create_step(
        str(record.get("kind") or ""),
        operation=str(record.get("operation") or ""),
        amount=int(record.get("amount", 1)),
        operator_digest=str(record.get("operator_digest") or ""),
    )
    if rebuilt != dict(record):
        raise TransformationLanguageError("transformation micro-step does not reproduce its digest")
    return rebuilt


def step_sort_key(step: Mapping[str, Any]) -> tuple[int, str, int, str, str]:
    value = validate_step(step)
    return (
        _STEP_RANK[value["kind"]],
        str(value["operation"]),
        int(value["amount"]),
        str(value["operator_digest"]),
        str(value["step_digest"]),
    )


def create_operator(name: str, steps: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    name = str(name)
    if not name:
        raise TransformationLanguageError("transformation operator has no name")
    program = [validate_step(step) for step in steps]
    if not program:
        raise TransformationLanguageError("transformation operator contains no micro-step")
    if program != sorted(program, key=step_sort_key):
        raise TransformationLanguageError(
            "transformation operator micro-steps are not in canonical lower-language order"
        )
    payload = {
        "schema": OPERATOR_SCHEMA,
        "name": name,
        "steps": program,
    }
    return {**payload, "operator_digest": digest_of(payload)}


def validate_operator(record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping) or record.get("schema") != OPERATOR_SCHEMA:
        raise TransformationLanguageError("transformation operator uses an unrecognised schema")
    rebuilt = create_operator(str(record.get("name") or ""), list(record.get("steps") or []))
    if rebuilt != dict(record):
        raise TransformationLanguageError("transformation operator does not reconstruct from its fields")
    return rebuilt


def operator_program_digest(operator: Mapping[str, Any]) -> str:
    value = validate_operator(operator)
    return digest_of({"step_digests": [step["step_digest"] for step in value["steps"]]})


def _assert_invocation_graph(operators: Sequence[Mapping[str, Any]]) -> None:
    by_digest = {item["operator_digest"]: item for item in operators}
    edges: dict[str, tuple[str, ...]] = {}
    for operator in operators:
        refs = tuple(
            step["operator_digest"]
            for step in operator["steps"]
            if step["kind"] == "invoke_held_operator"
        )
        for ref in refs:
            if ref not in by_digest:
                raise TransformationLanguageError(
                    "transformation operator invokes an operator not held by this language"
                )
            if ref == operator["operator_digest"]:
                raise TransformationLanguageError("transformation operator invokes itself")
        edges[operator["operator_digest"]] = refs

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(digest: str) -> None:
        if digest in visited:
            return
        if digest in visiting:
            raise TransformationLanguageError("transformation-operator invocation graph is cyclic")
        visiting.add(digest)
        for dependency in edges.get(digest, ()):
            visit(dependency)
        visiting.remove(digest)
        visited.add(digest)

    for digest in edges:
        visit(digest)


def create_language(
    operators: Sequence[Mapping[str, Any]],
    *,
    max_operator_steps: int,
    parent_language_digest: str = "",
) -> dict[str, Any]:
    values = [validate_operator(item) for item in operators]
    if not values:
        raise TransformationLanguageError("transformation language contains no operator")
    bound = int(max_operator_steps)
    if bound <= 0:
        raise TransformationLanguageError("transformation language needs a positive operator-step bound")
    names = [item["name"] for item in values]
    if len(set(names)) != len(names):
        raise TransformationLanguageError("transformation language contains a duplicate operator name")
    digests = [item["operator_digest"] for item in values]
    if len(set(digests)) != len(digests):
        raise TransformationLanguageError("transformation language contains a duplicate operator")
    programs = [operator_program_digest(item) for item in values]
    if len(set(programs)) != len(programs):
        raise TransformationLanguageError(
            "transformation language contains two names for the same operator program"
        )
    too_long = [item["name"] for item in values if len(item["steps"]) > bound]
    if too_long:
        raise TransformationLanguageError(
            "transformation operator exceeds the admitted step bound: %s" % ", ".join(too_long)
        )
    _assert_invocation_graph(values)
    payload = {
        "schema": LANGUAGE_SCHEMA,
        "operators": values,
        "max_operator_steps": bound,
        "parent_language_digest": str(parent_language_digest),
    }
    return {**payload, "language_digest": digest_of(payload)}


def validate_language(record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping) or record.get("schema") != LANGUAGE_SCHEMA:
        raise TransformationLanguageError("transformation language uses an unrecognised schema")
    rebuilt = create_language(
        list(record.get("operators") or []),
        max_operator_steps=int(record.get("max_operator_steps", 0)),
        parent_language_digest=str(record.get("parent_language_digest") or ""),
    )
    if rebuilt != dict(record):
        raise TransformationLanguageError("transformation language does not reconstruct from its fields")
    return rebuilt


def extend_language(
    language: Mapping[str, Any], operator: Mapping[str, Any]
) -> dict[str, Any]:
    """Return a one-operator descendant of a lineage-held transformation language."""
    prior = validate_language(language)
    addition = validate_operator(operator)
    if addition["name"] in {item["name"] for item in prior["operators"]}:
        raise TransformationLanguageError("language extension reuses an existing operator name")
    if addition["operator_digest"] in {
        item["operator_digest"] for item in prior["operators"]
    }:
        raise TransformationLanguageError("language extension re-adds an existing operator")
    if operator_program_digest(addition) in {
        operator_program_digest(item) for item in prior["operators"]
    }:
        raise TransformationLanguageError("language extension aliases an existing operator program")
    if len(addition["steps"]) > int(prior["max_operator_steps"]):
        raise TransformationLanguageError("language extension exceeds its admitted operator-step bound")
    return create_language(
        [*prior["operators"], addition],
        max_operator_steps=prior["max_operator_steps"],
        parent_language_digest=prior["language_digest"],
    )


def operator_named(language: Mapping[str, Any], name: str) -> dict[str, Any]:
    current = validate_language(language)
    matches = [item for item in current["operators"] if item["name"] == str(name)]
    if len(matches) != 1:
        raise TransformationLanguageError("transformation language has no unique operator %r" % name)
    return dict(matches[0])


def operator_by_digest(language: Mapping[str, Any], operator_digest: str) -> dict[str, Any]:
    current = validate_language(language)
    matches = [
        item for item in current["operators"] if item["operator_digest"] == str(operator_digest)
    ]
    if len(matches) != 1:
        raise TransformationLanguageError(
            "transformation language has no unique operator digest %r" % operator_digest
        )
    return dict(matches[0])


def _flatten_operator_steps(
    current: Mapping[str, Any], operator: Mapping[str, Any], stack: tuple[str, ...] = ()
) -> tuple[dict[str, Any], ...]:
    value = validate_operator(operator)
    digest = value["operator_digest"]
    if digest in stack:
        raise TransformationLanguageError("transformation-operator invocation is cyclic")
    primitive: list[dict[str, Any]] = []
    for raw_step in value["steps"]:
        step = validate_step(raw_step)
        if step["kind"] != "invoke_held_operator":
            primitive.append(step)
            continue
        target = operator_by_digest(current, step["operator_digest"])
        primitive.extend(_flatten_operator_steps(current, target, (*stack, digest)))
    return tuple(sorted(primitive, key=step_sort_key))


def apply_operator(
    policy: Mapping[str, Any], language: Mapping[str, Any], operator_name: str
) -> dict[str, Any]:
    """Interpret one lineage-held operator against a canonical generated-search policy.

    The final policy is a direct descendant of the input policy even when the operator program edits
    more than one structural field. Invoked acquired operators are expanded recursively to the same
    fixed primitive kernel, so reusing an acquired operator gives later generations a real dependency
    rather than a certificate-only label.
    """
    prior = policies.validate(policy)
    current = validate_language(language)
    operator = operator_named(current, operator_name)

    operation_names = list(prior["operation_names"])
    max_length = int(prior["max_length"])
    max_candidates = int(prior["max_candidates"])
    changed = False

    for step in _flatten_operator_steps(current, operator):
        if step["kind"] == "append_policy_operation":
            registry = resolve_registry(prior["registry_reference"])
            operation = step["operation"]
            if operation not in registry:
                raise TransformationLanguageError(
                    "operator asks to add operation %r outside the admitted registry" % operation
                )
            if operation in operation_names:
                raise TransformationLanguageError("operator adds an operation the policy already holds")
            operation_names.append(operation)
            changed = True
        elif step["kind"] == "increase_policy_depth":
            if max_length >= int(prior["ceiling_length"]):
                raise TransformationLanguageError("operator asks beyond the admitted policy depth ceiling")
            max_length += 1
            changed = True
        elif step["kind"] == "increase_candidate_limit":
            amount = int(step["amount"])
            if amount > max_candidates:
                raise TransformationLanguageError(
                    "one candidate-limit micro-step may not grow the current cap by more than 2x"
                )
            max_candidates += amount
            changed = True
        else:  # pragma: no cover - invocation is flattened and validation closes all other paths
            raise TransformationLanguageError("unsupported transformation micro-step")

    if not changed:
        raise TransformationLanguageError("transformation operator produced no structural change")

    return policies.create(
        registry_reference=prior["registry_reference"],
        operation_names=operation_names,
        max_length=max_length,
        ceiling_length=prior["ceiling_length"],
        max_candidates=max_candidates,
        input_field=prior["input_field"],
        parent_policy_digest=prior["policy_digest"],
    )
