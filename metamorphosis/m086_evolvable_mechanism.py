"""The mechanism that turns evidence into candidate transformations, made mutable.

M047 froze that mechanism in two pieces: `diagnose_limiting_module`, whose `ModuleDiagnosis.sufficient`
is true only when exactly one module is at fault, and `_candidate_sources`, an authored if/elif chain
dispatching on that single module. When the evidence implicates two modules the diagnosis is `None`,
the engine returns `INSUFFICIENT_DIAGNOSIS`, and **no candidate is generated at all**. That is a limit
of the hypothesis representation, not of the budget, and M047's protocol records it terminating on a
compound task for exactly this reason.

Here the pair becomes a serialized artifact — a schema plus a rule set — executed by a fixed
interpreter. The interpreter stands to the rule set as a CPU stands to a program: what the lineage
rewrites is the schema and the rules, and the next cycle really executes the rewritten version.

`m0_mechanism()` is differentially equivalent to M047's frozen pair, and a regression proves it over
the same evidence. Without that, this module would be a new mechanism we happened to write rather than
the one the repository actually froze.

Nothing here calls a model or opens a network. The evaluator, the sandbox, the task bank and this
interpreter are outside the mutable body.
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field, replace
from typing import Mapping, Sequence

from metamorphosis.m047_runtime_sandbox import CaseExecution
from metamorphosis.m047_software_body import (
    SoftwareBody,
    SoftwareCase,
    module_metadata,
    render_interpretation,
    render_selection,
    render_tool_module,
)

PROTOCOL_SCHEMA = "m086-evolvable-improvement-mechanism-protocol-v1"
GENERATOR_VERSION = 1

SCHEMA_SINGLE = "single_module"
SCHEMA_MULTI = "multi_module"

# Authored exactly as M046's transformation language and M047's templates are authored. What is not
# authored is which of these a limitation calls for, or how they combine.
META_PRIMITIVES = ("widen_hypothesis", "compose_expansions", "parameterize_constant", "relax_guard")

ALIAS_TARGETS = ("add", "max", "mean", "mul")
TOOL_EXPRESSIONS = ("midpoint", "mean", "sum", "maximum", "minimum")

ARMS = ("evolvable_meta", "fixed_meta", "meta_acquisition_ablated", "task_only_mutable")


class MechanismError(RuntimeError):
    """Raised when a mechanism, hypothesis or arm contract is violated."""


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def _clean(message: str | None) -> str:
    if message is None:
        return ""
    return message.strip().strip("'").strip('"')


# --------------------------------------------------------------------------------------------
# The hypothesis the mechanism is allowed to state
# --------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Hypothesis:
    """What the mechanism believes is wrong.

    Under the single-module schema at most one module may appear, which is M047's contract. Under the
    widened schema the same evidence can name several, which is the whole point of the experiment.
    """

    modules: tuple[str, ...]
    reason: str
    evidence_case_ids: tuple[str, ...]
    unknown_tokens: tuple[str, ...] = ()
    missing_operations: tuple[str, ...] = ()

    @property
    def sufficient(self) -> bool:
        return bool(self.modules)

    def to_dict(self) -> dict[str, object]:
        return {
            "modules": list(self.modules),
            "reason": self.reason,
            "evidence_case_ids": list(self.evidence_case_ids),
            "unknown_tokens": list(self.unknown_tokens),
            "missing_operations": list(self.missing_operations),
            "sufficient": self.sufficient,
        }


@dataclass(frozen=True)
class Rule:
    """A guarded expansion from a hypothesis to candidate module sources."""

    rule_id: str
    module: str
    requires: str
    options: tuple[str, ...]
    parameterized: bool = False
    relaxed: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id, "module": self.module, "requires": self.requires,
            "options": list(self.options), "parameterized": self.parameterized,
            "relaxed": self.relaxed,
        }


@dataclass(frozen=True)
class Mechanism:
    """The improvement mechanism as data. This is the artifact the lineage may rewrite."""

    schema: str
    rules: tuple[Rule, ...]
    composes: bool = False
    provenance: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "rules": [rule.to_dict() for rule in self.rules],
            "composes": self.composes,
            "provenance": list(self.provenance),
        }

    def digest(self) -> str:
        return hashlib.sha256(_canonical(self.to_dict())).hexdigest()

    def rule_for(self, module: str) -> Rule | None:
        return next((rule for rule in self.rules if rule.module == module), None)


def m0_mechanism() -> Mechanism:
    """The mechanism M047 froze, expressed as data.

    Every option list here is transcribed from `_candidate_sources`. A differential regression drives
    this and M047's own functions over the same evidence and requires identical results.
    """

    return Mechanism(
        schema=SCHEMA_SINGLE,
        rules=(
            Rule("interpreter_add_alias", "interpretation", "unknown_token", ALIAS_TARGETS),
            Rule("planner", "planning", "none", ("one_level", "recursive_postorder")),
            Rule("synthesize_tool", "selection", "missing_operation", TOOL_EXPRESSIONS),
            Rule("critic", "critique", "none", ("round_one", "round_two", "round_three")),
            Rule("allocator", "allocation", "none", ("fixed_five", "plan_length", "double_plan_length")),
        ),
        composes=False,
        provenance=(),
    )


# --------------------------------------------------------------------------------------------
# The fixed interpreter
# --------------------------------------------------------------------------------------------

def diagnose(mechanism: Mechanism, executions: Sequence[CaseExecution]) -> Hypothesis:
    """Run the mechanism's hypothesis schema over failure evidence.

    Under `single_module` this reproduces `diagnose_limiting_module` exactly, including its refusal to
    speak when more than one stage or more than one token is implicated. Under `multi_module` the same
    evidence yields every module it implicates.
    """

    failures = [execution for execution in executions if not execution.passed]
    if not failures:
        return Hypothesis((), "public cases already pass", ())

    evidence = tuple(failure.case_id for failure in failures)
    stages = {failure.error_stage for failure in failures if not failure.ok}
    tokens: set[str] = set()
    missing: set[str] = set()
    for failure in failures:
        message = _clean(failure.error_message)
        if message.startswith("unknown_operator:"):
            tokens.add(message.split(":", 1)[1])
        if "route_missing:" in message:
            missing.add(message.split("route_missing:", 1)[1].strip("'\""))

    if mechanism.schema == SCHEMA_SINGLE:
        if stages == {"interpretation"} and len(tokens) == 1:
            return Hypothesis(
                ("interpretation",),
                "unknown lexical operator blocks otherwise parseable requests",
                evidence, unknown_tokens=tuple(sorted(tokens)),
            )
        if stages == {"planning"}:
            return Hypothesis(
                ("planning",),
                "the interpreter produced structured input but the planner rejected nesting",
                evidence,
            )
        if stages == {"execution"}:
            messages = {_clean(failure.error_message) for failure in failures}
            if messages == {"budget_exceeded"}:
                return Hypothesis(
                    ("allocation",),
                    "the produced plan exceeds the allocator's explicit execution budget",
                    evidence,
                )
            if len(missing) == 1:
                return Hypothesis(
                    ("selection",),
                    "the planner emitted an operation with no selected executable tool",
                    evidence, missing_operations=tuple(sorted(missing)),
                )
        if not stages and _critique_matches(failures):
            return Hypothesis(
                ("critique",),
                "execution is numerically correct but final result normalization is insufficient",
                evidence,
            )
        return Hypothesis((), "public evidence does not isolate one safely patchable module", evidence)

    if mechanism.schema != SCHEMA_MULTI:
        raise MechanismError(f"unknown hypothesis schema {mechanism.schema!r}")

    modules: list[str] = []
    if tokens:
        modules.append("interpretation")
    if missing:
        modules.append("selection")
    if "planning" in stages and not tokens:
        modules.append("planning")
    if not stages and _critique_matches(failures):
        modules.append("critique")
    if not modules:
        return Hypothesis((), "widened evidence still implicates no patchable module", evidence)
    return Hypothesis(
        tuple(sorted(set(modules))),
        "widened evidence implicates every module the failures point at",
        evidence,
        unknown_tokens=tuple(sorted(tokens)),
        missing_operations=tuple(sorted(missing)),
    )


def _critique_matches(failures: Sequence[CaseExecution]) -> bool:
    for failure in failures:
        raw_value: object | None = None
        for item in failure.trace:
            if item.get("stage") == "execution":
                value = item.get("value")
                if isinstance(value, Mapping):
                    raw_value = value.get("value")
        if (
            not isinstance(raw_value, float)
            or not isinstance(failure.expected, (int, float))
            or round(raw_value, 2) != failure.expected
        ):
            return False
    return True


def _alias_replacements(parent: SoftwareBody, token: str, canonical: str) -> dict[str, str]:
    metadata = module_metadata(parent.source("interpretation"))
    aliases = metadata.get("aliases")
    if not isinstance(aliases, Mapping):
        raise MechanismError("interpretation source lacks aliases metadata")
    updated = {str(key): str(value) for key, value in aliases.items()}
    updated[token] = canonical
    return {"interpretation": render_interpretation(updated)}


def _tool_replacements(parent: SoftwareBody, operation: str, expression: str) -> dict[str, str]:
    metadata = module_metadata(parent.source("selection"))
    routes = metadata.get("routes")
    if not isinstance(routes, Mapping):
        raise MechanismError("selection source lacks routes metadata")
    updated = {str(key): str(value) for key, value in routes.items()}
    updated[operation] = operation
    return {
        "selection": render_selection(updated),
        f"tool_{operation}": render_tool_module(operation, expression),
    }


def _module_expansions(
    mechanism: Mechanism, parent: SoftwareBody, hypothesis: Hypothesis, module: str,
) -> list[tuple[str, dict[str, str]]]:
    """Every replacement set one rule offers for one implicated module."""

    rule = mechanism.rule_for(module)
    if rule is None:
        return []
    produced: list[tuple[str, dict[str, str]]] = []

    if module == "interpretation":
        tokens = hypothesis.unknown_tokens or ((),)
        for token in hypothesis.unknown_tokens:
            options = (
                (_canonical_for(token),) if rule.parameterized else rule.options
            )
            for canonical in options:
                produced.append((
                    f"{rule.rule_id}:{token}:{canonical}",
                    _alias_replacements(parent, token, canonical),
                ))
        if not hypothesis.unknown_tokens and rule.relaxed:
            for canonical in rule.options:
                produced.append((f"{rule.rule_id}:*:{canonical}", {}))
        return produced

    if module == "selection":
        for operation in hypothesis.missing_operations:
            options = (
                (_expression_for(operation),) if rule.parameterized else rule.options
            )
            for expression in options:
                produced.append((
                    f"{rule.rule_id}:{operation}:{expression}",
                    _tool_replacements(parent, operation, expression),
                ))
        return produced

    from metamorphosis.m047_software_body import (
        render_allocation,
        render_critique,
        render_planning,
    )

    renderers = {
        "planning": (render_planning, "planning"),
        "critique": (render_critique, "critique"),
        "allocation": (render_allocation, "allocation"),
    }
    if module not in renderers:
        return []
    render, name = renderers[module]
    for option in rule.options:
        produced.append((f"{rule.rule_id}:{option}", {name: render(option)}))
    return produced


def _canonical_for(token: str) -> str:
    """`parameterize_constant` for aliases: read the target from the token instead of a fixed list."""

    return token if token in ALIAS_TARGETS else "mean"


def _expression_for(operation: str) -> str:
    """`parameterize_constant` for tools: read the expression from the operation instead of a list."""

    table = {"max": "maximum", "low": "minimum", "min": "minimum", "tot": "sum", "mean": "mean"}
    return table.get(operation, "mean")


def generate(
    mechanism: Mechanism, parent: SoftwareBody, hypothesis: Hypothesis,
) -> tuple[tuple[str, dict[str, str]], ...]:
    """Every candidate replacement set the mechanism can emit for this hypothesis.

    This is the mechanism's *constructive image*, and the experiment enumerates it directly rather
    than inferring it from a score.
    """

    if not hypothesis.sufficient:
        return ()
    per_module = {
        module: _module_expansions(mechanism, parent, hypothesis, module)
        for module in hypothesis.modules
    }
    if not mechanism.composes:
        flat: list[tuple[str, dict[str, str]]] = []
        for module in hypothesis.modules:
            flat.extend(per_module[module])
        return tuple(flat)

    # Composition: one candidate carries the expansions of every implicated module at once. This is
    # the shape M047's dispatch cannot express, because it returns for a single module.
    combined: list[tuple[str, dict[str, str]]] = []
    ordered = [per_module[module] for module in hypothesis.modules if per_module[module]]
    if not ordered:
        return ()

    def cross(index: int, label: list[str], merged: dict[str, str]) -> None:
        if index == len(ordered):
            combined.append(("+".join(label), dict(merged)))
            return
        for name, replacements in ordered[index]:
            conflict = any(
                key in merged and merged[key] != value for key, value in replacements.items()
            )
            if conflict:
                continue
            merged_next = dict(merged)
            merged_next.update(replacements)
            cross(index + 1, label + [name], merged_next)

    cross(0, [], {})
    return tuple(combined)


# --------------------------------------------------------------------------------------------
# Meta-primitives: bounded operations over a mechanism
# --------------------------------------------------------------------------------------------

def apply_meta_primitive(mechanism: Mechanism, primitive: str) -> Mechanism:
    if primitive == "widen_hypothesis":
        return replace(
            mechanism, schema=SCHEMA_MULTI,
            provenance=mechanism.provenance + (primitive,),
        )
    if primitive == "compose_expansions":
        return replace(
            mechanism, composes=True, provenance=mechanism.provenance + (primitive,),
        )
    if primitive == "parameterize_constant":
        return replace(
            mechanism,
            rules=tuple(replace(rule, parameterized=True) for rule in mechanism.rules),
            provenance=mechanism.provenance + (primitive,),
        )
    if primitive == "relax_guard":
        return replace(
            mechanism,
            rules=tuple(replace(rule, relaxed=True) for rule in mechanism.rules),
            provenance=mechanism.provenance + (primitive,),
        )
    raise MechanismError(f"unknown meta-primitive {primitive!r}")


def candidate_meta_transformations() -> tuple[tuple[str, ...], ...]:
    """Every bounded combination the lineage may try, in a deterministic order.

    Singles before pairs, alphabetical within a size. Nothing here knows which one works; the order is
    a search order, not a ranking, and the lineage finds out by running them.
    """

    singles = tuple((primitive,) for primitive in sorted(META_PRIMITIVES))
    pairs = tuple(
        (first, second)
        for index, first in enumerate(sorted(META_PRIMITIVES))
        for second in sorted(META_PRIMITIVES)[index + 1:]
    )
    return singles + pairs


def build_mechanism(base: Mechanism, primitives: Sequence[str]) -> Mechanism:
    mechanism = base
    for primitive in primitives:
        mechanism = apply_meta_primitive(mechanism, primitive)
    return mechanism
