"""Generic, composable transformation synthesis for M094 (P6).

Satisfies P6 from experiments/M094/PROTOCOL.json:

    "the repair is assembled from composable operations and is
    not a template body"

Every operation's apply() function reads the target class's AST to discover
its structure (fields, collections, attributes) and generates source code
from that discovered structure. No operation contains a component name,
class name, or path as a literal in its generation logic — everything is
read from the AST.

This is NOT a template because the generated code depends on what the AST
actually contains, not on what an author wrote down. The method body for
a to_dict() renderer, for example, is built by first reading the class's
declared fields from its AST node, then constructing the dict literal
from those field names. If the class has three fields the method returns
three entries; if it has five it returns five — without any authored
string saying what those fields are.

Contrast with m094_transform.py which carries one authored template
(suggest_query_method) containing the complete method body, a component-
specific branch on "MemoryLedger", and a fixed method name shape.
"""

from __future__ import annotations

import ast
import hashlib
import json
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

SYNTHESIS_SCHEMA = "m094-synthesis-v1"


# ── Canonical helpers ────────────────────────────────────────────────


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("ascii")).hexdigest()


# ── AST helpers (no component names) ──────────────────────────────────


def _declared_field_names(class_node: ast.ClassDef) -> list[str]:
    """Return declared field names for a class, reading from the AST only.

    Handles:
    - Type annotations (dataclass-like):: ``x: int``
    - Class-level assignments: ``x = 0``
    - ``__init__`` body assignments to self: ``self.x = value``
    - Read-only ``@property`` methods
    """
    names: set[str] = set()
    for node in class_node.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == "__init__":
                for inner in ast.walk(node):
                    if isinstance(inner, ast.Assign):
                        for target in inner.targets:
                            if isinstance(target, ast.Attribute):
                                names.add(target.attr)
            elif not node.name.startswith("_") and any(
                isinstance(d, ast.Name) and d.id == "property"
                for d in node.decorator_list
            ):
                names.add(node.name)
    return sorted(name for name in names if not name.startswith("_"))


def _exposed_collection_names(class_node: ast.ClassDef) -> frozenset[str]:
    """Public collection-like attribute names exposed by the class.

    A property or method returning ``tuple(...)`` / ``list(...)`` counts,
    as does a private backing attribute assigned a list in ``__init__``.
    """
    names: set[str] = set()
    for node in class_node.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.args.args and len(node.args.args) == 1:
                for inner in ast.walk(node):
                    if (
                        isinstance(inner, ast.Return)
                        and isinstance(inner.value, ast.Call)
                        and isinstance(inner.value.func, ast.Name)
                        and inner.value.func.id in {"tuple", "list"}
                    ):
                        names.add(node.name.lstrip("_"))
            if node.name == "__init__":
                for inner in ast.walk(node):
                    if isinstance(inner, ast.Assign) and isinstance(inner.value, ast.List):
                        for target in inner.targets:
                            if isinstance(target, ast.Attribute):
                                names.add(target.attr.lstrip("_"))
    return frozenset(names)


def _find_class_node(tree: ast.AST, class_name: str) -> ast.ClassDef | None:
    """Walk the AST and return the class definition node for *class_name*."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    return None


def _class_body_insert_line(class_node: ast.ClassDef) -> int:
    """Return the line number (1-indexed) after the last class body member."""
    last = class_node.body[-1]
    return last.end_lineno or last.lineno


def _insert_method_into_source(source: str, method_source: str, class_name: str) -> str:
    """Insert a method after the last body member of the named class.

    Uses line-level string manipulation (not ``ast.unparse``) so import
    order, comments, and formatting are preserved exactly.
    """
    tree = ast.parse(source)
    class_node = _find_class_node(tree, class_name)
    if class_node is None:
        raise ValueError(f"class {class_name} not found in source")

    insert_line = _class_body_insert_line(class_node)
    lines = source.splitlines(keepends=True)

    # Indent the method source to class level (4 spaces)
    indented = textwrap.indent(method_source.strip(), "    ").splitlines(keepends=True)
    if not indented[-1].endswith("\n"):
        indented[-1] += "\n"

    # Prepend a blank line for readability
    indented = ["\n"] + indented

    for i, line in enumerate(indented):
        lines.insert(insert_line + i, line)

    return "".join(lines)


# ── Capability-specific generators (AST-driven, never authored) ───────


def _is_container_annotation(node: ast.expr | None) -> bool:
    """Check if a type annotation suggests a container type.

    Reads the AST annotation only — no string matching on component identity.
    Returns True for ``tuple``, ``list``, ``set``, ``frozenset``, ``dict``,
    ``Iterable``, ``Sequence``, and their subscripted forms.
    """
    if node is None:
        return False
    # Bare name: tuple, list, set, frozenset, dict, Iterable, Sequence
    if isinstance(node, ast.Name):
        return node.id in {
            "tuple", "list", "set", "frozenset", "dict",
            "Iterable", "Sequence", "Collection",
            "Mapping", "MutableMapping",
        }
    # Subscripted: tuple[str, ...], list[int], Optional[list[str]]
    if isinstance(node, ast.Subscript):
        if isinstance(node.value, ast.Name):
            return node.value.id in {
                "tuple", "list", "set", "frozenset", "dict",
                "Iterable", "Sequence", "Collection",
                "Mapping", "MutableMapping",
            }
        # Handle Optional[...] — unwrap and recurse
        if isinstance(node.value, ast.Name) and node.value.id == "Optional":
            return _is_container_annotation(node.slice)
    return False


def _field_value_expr(field_name: str, annotation: ast.expr | None) -> str:
    """Generate the expression for a field in a dict literal.

    Container types (tuple, list, set) are wrapped in ``list()`` for
    JSON-safe serialisation. Simple types (str, int, bool, etc.) are
    returned as ``self.<field>`` directly.
    """
    if _is_container_annotation(annotation):
        return f"list(self.{field_name})"
    return f"self.{field_name}"


# ── Public types ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class SynthesisOperation:
    """A single atomic operation that can be applied to a source file.

    The ``apply`` function reads the AST of the target file to discover
    structure (fields, collections) and generates replacement source
    from that discovered structure. No component identity is embedded in
    the operation — every component-specific string comes from the AST.
    """

    #: Path of the file to edit, relative to the repository root.
    file: str

    #: Name of the class being modified.
    class_name: str

    #: Human-readable description (for logging / search, not for routing).
    description: str

    #: Source → modified-source transformation. Reads the AST internally.
    apply: Callable[[str], str]

    #: Content-addressed digest identifying this specific operation.
    digest: str

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "class": self.class_name,
            "description": self.description,
            "digest": self.digest,
        }


# ── Main synthesis entry point ────────────────────────────────────────


def suggest_operations(
    repo_root: Path,
    component_path: str,
    class_name: str,
    capability: str,
    target: str,
    detail: str,
    max_length: int | None = None,
) -> list[SynthesisOperation]:
    """Given a diagnostic result, generate candidate operations.

    The operations are derived from the component's AST, not from a
    template. No operation contains a component name, class name, or
    path as a literal in its generation logic — everything is read from
    the AST.

    Parameters
    ----------
    repo_root:
        Root of the repository being diagnosed.
    component_path:
        Relative path to the component's source file (e.g.
        ``"mira_core/safety.py"``).
    class_name:
        Name of the class to modify.
    capability:
        Capability being repaired (e.g. ``"render_value_object_as_mapping"``
        or ``"filter_collection_by_attribute"``).
    target:
        Shape-specific target. For ``RenderAsMapping`` this is the class
        name; for ``FilterByAttribute`` this is the collection name.
    detail:
        Shape-specific detail. For ``RenderAsMapping`` this is the
        attribute subset read by callers; for ``FilterByAttribute`` this
        is the attribute name.
    max_length:
        Composition bound. ``None`` uses the declared
        ``m094_composition.MAX_COMPOSITION_LENGTH``. It exists so the protocol's
        ``more_budget_same_operations`` arm can raise the bound over the same
        operation set; a control that cannot be run cannot fail.

    Returns
    -------
    list[SynthesisOperation]
        Zero or more candidate operations. Most callers will get exactly
        one per capability, but the interface is a list for future
        composition (multiple operations, alternative approaches).
    """
    source_path = repo_root / component_path
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    class_node = _find_class_node(tree, class_name)
    if class_node is None:
        return []

    from metamorphosis import m094_composition as composition
    from metamorphosis import m094_execution as execution
    from metamorphosis.m094_diagnosis import CAPABILITY_SHAPES, decode_rendering

    shape = next((s for s in CAPABILITY_SHAPES if s.name == capability), None)
    if shape is None:
        return []

    fields = _declared_field_names(class_node)
    collections = sorted(_exposed_collection_names(class_node))

    def accepts(modified: str) -> bool:
        """Judge a candidate by the requirement, not against a written-down answer.

        This is the same predicate the diagnosis uses to decide whether a
        component supplies a capability. A candidate is accepted when the
        insufficiency stops being unmet, so nothing here knows what the winning
        method looks like.
        """

        try:
            modified_tree = ast.parse(modified)
        except SyntaxError:
            return False
        node = _find_class_node(modified_tree, class_name)
        return node is not None and shape.is_supplied_by(node, target, detail)

    search_kwargs = {} if max_length is None else {"max_length": max_length}
    def confirms(ordered):
        """Amendment A2: run the survivors and keep the ones that reproduce the requirement.

        The structural predicate above says a candidate *reads* correctly. This says it
        *behaves* correctly, on values the class actually accepts, in a fresh interpreter
        that is never told which method is supposed to work. A candidate binding the
        required keys and wrapping an unrelated integer field in `list()` satisfied the
        first and raises under the second; the qualification found exactly that.
        """

        cases = execution.constructible_cases(
            repo_root, component_path, class_name, decode_rendering(detail),
        )
        if not cases:
            # No value the class accepts could be invented, so nothing can be executed. The
            # candidates are returned unconfirmed rather than silently adopted, and the
            # report records that nothing was executed.
            return [], 0, False

        budget = execution.MAX_CONFIRMATIONS
        window = ordered[:budget]
        variants = [
            (str(index), composition.insert_into_class(source, class_name, item.source) or "")
            for index, item in enumerate(window)
        ]
        records = execution.probe_variants(
            repo_root, component_path, variants, class_name,
            decode_rendering(detail), cases,
        )
        by_id = {record["id"]: record for record in records}
        accepted = [
            item for index, item in enumerate(window)
            if execution.agrees(by_id.get(str(index), {}))
        ]
        return accepted, len(window), len(ordered) > budget

    report = composition.search(
        source=source,
        class_name=class_name,
        capability=capability,
        fields=fields,
        detail=detail,
        collections=collections,
        accepts=accepts,
        confirms=confirms,
        **search_kwargs,
    )

    if report.adopted is None:
        return []

    adopted = report.adopted

    def _apply(src: str, _ms=adopted.source, _cn=class_name) -> str:
        placed = composition.insert_into_class(src, _cn, _ms)
        if placed is None:
            raise ValueError("the adopted method could not be placed in " + _cn)
        return placed

    operations = [SynthesisOperation(
        file=component_path,
        class_name=class_name,
        description=(
            "assembled " + str(len(adopted.composition)) + " operations for "
            + class_name + "; " + str(report.examined) + " examined, "
            + str(report.refused_total()) + " refused, "
            + str(report.executed) + " executed, "
            + str(report.confirmed_by_execution) + " confirmed"
        ),
        apply=_apply,
        digest=adopted.digest(),
    )]

    return operations