"""A repair substrate for M094: operations below the repair, and a search over them.

`experiments/M094/DESIGN_AUDIT.md` Defect 4 records the inherited transformation
set -- one template holding the finished method body -- and the milder form that
replaced it in `m094_synthesis.py`: an f-string of a method with its identifiers
filled in from the AST. P6 asks for something else, and the difference is not
cosmetic:

    a repair assembled from composable operations does not appear anywhere
    as a block of source text.

So nothing here emits source. Each operation contributes **one decision** to a
method under construction -- a name, a field, a container, a guard, the shape of
the return -- and the method is the abstract syntax tree those decisions
produce. No operation is a method, and no sequence is privileged: most
compositions are ill-formed, inert, or compute something the requirement does
not ask for, and they are refused by measurement rather than by being
unreachable.

Two things remain authored and are the expected next ceiling, exactly as M091's
assembly substrate was: the operation set itself, and the bound on composition
length. What is *not* authored is which composition survives.
"""

from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import dataclass, field, replace
from typing import Iterator, Sequence

from metamorphosis.m094_diagnosis import decode_rendering

COMPOSITION_SCHEMA = "m094-repair-composition-v1"

#: Container constructors a field may be wrapped in. `None` means "as it is".
WRAPPERS: tuple[str | None, ...] = (None, "list", "tuple")

#: Longest composition the search will assemble. Authored, and disclosed.
MAX_COMPOSITION_LENGTH = 12


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("ascii")).hexdigest()


# -- The method under construction ------------------------------------


@dataclass(frozen=True)
class MappingItem:
    key: str
    field: str
    wrapper: str | None


@dataclass(frozen=True)
class FilterSpec:
    collection: str
    attribute: str
    parameter: str


@dataclass(frozen=True)
class MethodDraft:
    """Partial state. A draft is not a method until a return shape is chosen."""

    name: str | None = None
    parameters: tuple[str, ...] = ()
    items: tuple[MappingItem, ...] = ()
    filtered: FilterSpec | None = None
    guard: str | None = None
    returns: str | None = None      # "mapping" | "filter"

    def fingerprint(self) -> str:
        """Behavioural identity, ignoring the chosen name.

        Two drafts differing only in what the method is called compute the same
        thing, and the search must not count them as separate discoveries.
        """

        return _digest({
            "parameters": list(self.parameters),
            # Key order does not change the mapping a method returns, so two
            # drafts differing only in the order they bind keys compute the same
            # thing and must not be counted as separate discoveries.
            "items": sorted([i.key, i.field, i.wrapper or ""] for i in self.items),
            "filtered": (
                [self.filtered.collection, self.filtered.attribute, self.filtered.parameter]
                if self.filtered else None
            ),
            "guard": self.guard,
            "returns": self.returns,
        })


# -- Operations -------------------------------------------------------


class Operation:
    """One decision. Returns None when it cannot apply to this draft."""

    def apply(self, draft: MethodDraft) -> MethodDraft | None:
        raise NotImplementedError

    def describe(self) -> str:
        raise NotImplementedError


@dataclass(frozen=True)
class NameMethod(Operation):
    identifier: str

    def apply(self, draft: MethodDraft) -> MethodDraft | None:
        if draft.name is not None:
            return None
        return replace(draft, name=self.identifier)

    def describe(self) -> str:
        return "name=" + self.identifier


@dataclass(frozen=True)
class IncludeField(Operation):
    """Bind one key to one field of the object, optionally wrapped."""

    field: str
    wrapper: str | None = None
    key: str | None = None

    def apply(self, draft: MethodDraft) -> MethodDraft | None:
        key = self.key or self.field
        if any(item.key == key for item in draft.items):
            return None
        item = MappingItem(key=key, field=self.field, wrapper=self.wrapper)
        return replace(draft, items=draft.items + (item,))

    def describe(self) -> str:
        suffix = ":" + self.wrapper if self.wrapper else ""
        key = self.key or self.field
        prefix = key + "<-" if key != self.field else ""
        return "include=" + prefix + self.field + suffix


@dataclass(frozen=True)
class FilterCollection(Operation):
    """Select from a collection by comparing one attribute to a parameter."""

    collection: str
    attribute: str
    parameter: str = "value"

    def apply(self, draft: MethodDraft) -> MethodDraft | None:
        if draft.filtered is not None:
            return None
        return replace(
            draft,
            filtered=FilterSpec(self.collection, self.attribute, self.parameter),
            parameters=draft.parameters + (self.parameter,),
        )

    def describe(self) -> str:
        return "filter=" + self.collection + "." + self.attribute


@dataclass(frozen=True)
class RejectEmpty(Operation):
    """Refuse an empty argument before doing any work."""

    parameter: str

    def apply(self, draft: MethodDraft) -> MethodDraft | None:
        if draft.guard is not None or self.parameter not in draft.parameters:
            return None
        return replace(draft, guard=self.parameter)

    def describe(self) -> str:
        return "guard=" + self.parameter


@dataclass(frozen=True)
class ReturnShape(Operation):
    """Commit the draft to returning a mapping, or a selection."""

    shape: str      # "mapping" | "filter"

    def apply(self, draft: MethodDraft) -> MethodDraft | None:
        if draft.returns is not None:
            return None
        return replace(draft, returns=self.shape)

    def describe(self) -> str:
        return "return=" + self.shape


# -- Rendering: a draft becomes an AST, never a string ----------------


def _self_attribute(field: str) -> ast.expr:
    return ast.Attribute(value=ast.Name(id="self", ctx=ast.Load()), attr=field, ctx=ast.Load())


def _wrapped(expr: ast.expr, wrapper: str | None) -> ast.expr:
    if wrapper is None:
        return expr
    return ast.Call(func=ast.Name(id=wrapper, ctx=ast.Load()), args=[expr], keywords=[])


def render(draft: MethodDraft) -> ast.FunctionDef | None:
    """Build the method as a syntax tree. Returns None for an incomplete draft."""

    if draft.name is None or draft.returns is None:
        return None

    body: list[ast.stmt] = []

    if draft.guard is not None:
        body.append(ast.If(
            test=ast.UnaryOp(op=ast.Not(), operand=ast.Name(id=draft.guard, ctx=ast.Load())),
            body=[ast.Raise(
                exc=ast.Call(
                    func=ast.Name(id="ValueError", ctx=ast.Load()),
                    args=[ast.Constant(value=draft.guard + " must not be empty")],
                    keywords=[],
                ),
                cause=None,
            )],
            orelse=[],
        ))

    if draft.returns == "mapping":
        if not draft.items:
            return None
        body.append(ast.Return(value=ast.Dict(
            keys=[ast.Constant(value=item.key) for item in draft.items],
            values=[_wrapped(_self_attribute(item.field), item.wrapper) for item in draft.items],
        )))
    elif draft.returns == "filter":
        spec = draft.filtered
        if spec is None:
            return None
        body.append(ast.Return(value=ast.Call(
            func=ast.Name(id="tuple", ctx=ast.Load()),
            args=[ast.GeneratorExp(
                elt=ast.Name(id="item", ctx=ast.Load()),
                generators=[ast.comprehension(
                    target=ast.Name(id="item", ctx=ast.Store()),
                    iter=_self_attribute(spec.collection),
                    ifs=[ast.Compare(
                        left=ast.Attribute(
                            value=ast.Name(id="item", ctx=ast.Load()),
                            attr=spec.attribute,
                            ctx=ast.Load(),
                        ),
                        ops=[ast.Eq()],
                        comparators=[ast.Name(id=spec.parameter, ctx=ast.Load())],
                    )],
                    is_async=0,
                )],
            )],
            keywords=[],
        )))
    else:
        return None

    arguments = ast.arguments(
        posonlyargs=[],
        args=[ast.arg(arg="self")] + [ast.arg(arg=p) for p in draft.parameters],
        vararg=None,
        kwonlyargs=[],
        kw_defaults=[],
        kwarg=None,
        defaults=[],
    )
    return ast.FunctionDef(
        name=draft.name,
        args=arguments,
        body=body,
        decorator_list=[],
        returns=None,
        type_params=[],
    )


def unparse(function: ast.FunctionDef) -> str:
    """Turn a built method into source, at the very last moment."""

    module = ast.Module(body=[function], type_ignores=[])
    return ast.unparse(ast.fix_missing_locations(module))


# -- The operation set offered for one diagnosed insufficiency --------


def _name_candidates(capability: str, detail: str) -> tuple[str, ...]:
    """Derive method-name candidates from the diagnosis, not from a table.

    The capability name and the diagnosed identifiers are the only sources. The
    requirement does not constrain the name, so several candidates will satisfy
    it and the search breaks the tie by digest order rather than by preference.
    """

    tokens = [t for t in capability.split("_") if t]
    names: list[str] = []
    if "mapping" in tokens:
        names += ["as_mapping", "to_dict", "as_dict"]
    if "filter" in tokens:
        attribute = detail.split(",")[-1]
        names += ["filter_by_" + attribute, "by_" + attribute, "select_by_" + attribute]
    return tuple(dict.fromkeys(names))


def operations_for(
    capability: str,
    fields: Sequence[str],
    detail: str,
    collections: Sequence[str] = (),
) -> tuple[Operation, ...]:
    """Every operation available for this insufficiency.

    None of these is a repair. `IncludeField` reads one field; `ReturnShape`
    decides what the method returns at all; `NameMethod` only names it. A method
    exists once some sequence of them has supplied a name, a return shape, and
    whatever that shape needs.
    """

    operations: list[Operation] = [NameMethod(n) for n in _name_candidates(capability, detail)]
    operations.append(ReturnShape("mapping"))
    operations.append(ReturnShape("filter"))

    for field in sorted(fields):
        for wrapper in WRAPPERS:
            operations.append(IncludeField(field, wrapper))

    # Callers do not always name the key after the field behind it. A site that wrote
    # `{"destination": spec.working_directory}` demands a method binding `destination` to
    # `working_directory`, and `RenderAsMapping.is_supplied_by` has always required exactly
    # that agreement -- but every operation offered above binds a key to the field of the
    # same name, so no composition could express it and the search refused everything on
    # such a component. Acceptance demanded a binding generation could not produce.
    #
    # The keys come from `detail`, which is the diagnosis's record of what the call sites
    # wrote. They are a measurement, not a table: nothing here knows a component, and a
    # requirement whose keys match its fields adds no operation at all.
    for key, field, _wrapper in decode_rendering(detail):
        if key == field or field not in set(fields):
            continue
        for wrapper in WRAPPERS:
            operations.append(IncludeField(field, wrapper, key))

    attribute = detail.split(",")[-1]
    for collection in sorted(collections):
        operations.append(FilterCollection(collection, attribute))
    operations.append(RejectEmpty("value"))

    return tuple(operations)


# -- The search -------------------------------------------------------


@dataclass(frozen=True)
class Candidate:
    """One assembled method, and the composition that produced it."""

    draft: MethodDraft
    composition: tuple[str, ...]
    source: str

    def digest(self) -> str:
        return _digest({"composition": list(self.composition), "source": self.source})


@dataclass
class SearchReport:
    """What the search examined, refused, and adopted."""

    examined: int = 0
    distinct_behaviours: int = 0
    refused: dict[str, int] = field(default_factory=dict)
    adopted: Candidate | None = None
    survivors: int = 0
    #: Survivors that actually differ in what they compute. Several spellings of
    #: one behaviour is one discovery, not several.
    surviving_behaviours: int = 0

    def refuse(self, reason: str) -> None:
        self.refused[reason] = self.refused.get(reason, 0) + 1

    def refused_total(self) -> int:
        return sum(self.refused.values())

    def to_dict(self) -> dict:
        return {
            "schema": COMPOSITION_SCHEMA,
            "examined": self.examined,
            "distinct_behaviours": self.distinct_behaviours,
            "refused": dict(sorted(self.refused.items())),
            "refused_total": sum(self.refused.values()),
            "survivors": self.survivors,
            "surviving_behaviours": self.surviving_behaviours,
            "adopted": (
                {
                    "composition": list(self.adopted.composition),
                    "digest": self.adopted.digest(),
                }
                if self.adopted else None
            ),
        }


def _compositions(
    operations: Sequence[Operation], max_length: int
) -> Iterator[tuple[Operation, ...]]:
    """Grow compositions breadth-first, keeping only those that still apply.

    An operation that cannot apply to a draft prunes that branch, which is what
    keeps a combinatorial space finite without privileging any sequence.
    """

    frontier: list[tuple[MethodDraft, tuple[Operation, ...]]] = [(MethodDraft(), ())]
    seen: set[tuple[str, str | None]] = set()

    for _ in range(max_length):
        nxt: list[tuple[MethodDraft, tuple[Operation, ...]]] = []
        for draft, chain in frontier:
            for operation in operations:
                grown = operation.apply(draft)
                if grown is None:
                    continue
                key = (grown.fingerprint(), grown.name)
                if key in seen:
                    continue
                seen.add(key)
                nxt.append((grown, chain + (operation,)))
                yield chain + (operation,)
        if not nxt:
            break
        frontier = nxt


# -- Validation: a candidate is judged by the diagnosis, not by a target ------


def insert_into_class(source: str, class_name: str, method_source: str) -> str | None:
    """Place a built method into a class, by AST position rather than by text search."""

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    target = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            target = node
            break
    if target is None or not target.body:
        return None

    indent = " " * 4
    body = "\n".join(indent + line if line.strip() else line
                     for line in method_source.splitlines())

    last = target.body[-1]
    end = getattr(last, "end_lineno", None)
    if end is None:
        return None

    lines = source.splitlines(keepends=True)
    prefix = "".join(lines[:end])
    suffix = "".join(lines[end:])
    if not prefix.endswith("\n"):
        prefix += "\n"
    return prefix + "\n" + body + "\n" + suffix


def search(
    source: str,
    class_name: str,
    capability: str,
    fields: Sequence[str],
    detail: str,
    collections: Sequence[str],
    accepts,
    max_length: int = MAX_COMPOSITION_LENGTH,
) -> SearchReport:
    """Assemble candidates and keep the ones the requirement accepts.

    `accepts` is supplied by the caller and receives the *modified source*. It is
    the diagnosis re-run against the candidate, so acceptance means "the
    insufficiency is now met" rather than "the output matches something written
    down". Nothing here knows what the winning method looks like.
    """

    operations = operations_for(capability, fields, detail, collections)
    report = SearchReport()
    behaviours: set[str] = set()
    survivors: list[Candidate] = []

    for composition in _compositions(operations, max_length):
        draft = MethodDraft()
        for operation in composition:
            grown = operation.apply(draft)
            if grown is None:
                draft = None
                break
            draft = grown
        if draft is None:
            # Unreachable on any input `_compositions` can produce: it only yields chains
            # it has already grown successfully from an empty draft, and re-applying the
            # same chain to the same initial draft cannot fail. Kept as a guard because
            # `search` is a public entry point and a caller may pass compositions from
            # elsewhere; measured never to fire on the M094 target at any budget.
            report.examined += 1
            report.refuse("composition_does_not_apply")
            continue

        report.examined += 1

        function = render(draft)
        if function is None:
            report.refuse("incomplete_draft_is_not_a_method")
            continue

        behaviours.add(draft.fingerprint())

        try:
            method_source = unparse(function)
        except (ValueError, TypeError, AttributeError):
            report.refuse("unrenderable")
            continue

        modified = insert_into_class(source, class_name, method_source)
        if modified is None:
            report.refuse("could_not_be_placed_in_the_class")
            continue

        try:
            ast.parse(modified)
        except SyntaxError:
            report.refuse("modified_source_does_not_parse")
            continue

        if not accepts(modified):
            report.refuse("requirement_not_satisfied")
            continue

        survivors.append(Candidate(draft=draft, composition=tuple(
            operation.describe() for operation in composition
        ), source=method_source))

    report.distinct_behaviours = len(behaviours)
    report.survivors = len(survivors)
    report.surviving_behaviours = len({c.draft.fingerprint() for c in survivors})

    if survivors:
        # The requirement does not constrain which survivor is taken, so the tie
        # is broken by content address rather than by preference.
        report.adopted = min(survivors, key=lambda c: c.digest())

    return report
