"""Structural insufficiency measurement for M094.

This replaces the substring-matching diagnostic in `m094_component_discovery.py`,
whose four defects are measured in `experiments/M094/DESIGN_AUDIT.md`.

The measurement rests on one separation, which is what makes it a measurement
rather than a name lookup:

    demand is counted OUTSIDE the component; supply is checked INSIDE it.

A component is insufficient for a capability when its callers repeatedly perform
an operation by hand that the component could expose, and the component does not
expose it. Because the component's own source is excluded from the demand count,
implementing the capability can only ever *decrease* insufficiency. The inverted
detector of the inherited implementation — where writing `events_by_kind` raised
the score for "missing query method", since `event.kind` appears in the method
body — is structurally impossible here.

Nothing in this module names a component, a path or a class. Every input is an
AST property. Which component wins is therefore a fact about the repository, not
a constant written by a person.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Sequence

DIAGNOSIS_SCHEMA = "m094-structural-diagnosis-v1"


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("ascii")).hexdigest()


# ── Capability shapes ────────────────────────────────────────────────


@dataclass(frozen=True)
class FilterByAttribute:
    """Selecting the members of an exposed collection by one attribute.

    The shape is generic: it mentions no collection name and no attribute name.
    Both are recovered from the source being measured.
    """

    name: str = "filter_collection_by_attribute"

    def demand_sites(self, tree: ast.AST, collections: frozenset[str]) -> list[tuple[str, str]]:
        """Find hand-written filters over one of *collections*.

        Returns (collection_name, attribute_name) for each site, e.g. a
        comprehension of the form ``x for x in obj.events if x.kind == k``.
        """

        found: list[tuple[str, str]] = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
                continue
            for generator in node.generators:
                collection = _iterated_attribute(generator.iter)
                if collection is None or collection not in collections:
                    continue
                bound = generator.target
                if not isinstance(bound, ast.Name):
                    continue
                for condition in generator.ifs:
                    attribute = _compared_attribute_of(condition, bound.id)
                    if attribute is not None:
                        found.append((collection, attribute))
        return found

    def is_supplied_by(
        self, class_node: ast.ClassDef, collection: str, attribute: str
    ) -> bool:
        """Does *class_node* already define a method performing this filter?"""

        for node in class_node.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name.startswith("_"):
                continue
            for inner in ast.walk(node):
                if not isinstance(inner, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
                    continue
                for generator in inner.generators:
                    iterated = _iterated_attribute(generator.iter)
                    if iterated not in {collection, f"_{collection}"}:
                        continue
                    bound = generator.target
                    if not isinstance(bound, ast.Name):
                        continue
                    if any(
                        _compared_attribute_of(cond, bound.id) == attribute
                        for cond in generator.ifs
                    ):
                        return True
        return False


CAPABILITY_SHAPES: tuple[FilterByAttribute, ...] = (FilterByAttribute(),)


# ── AST helpers ──────────────────────────────────────────────────────


def _iterated_attribute(node: ast.expr) -> str | None:
    """Return the attribute name in ``obj.attr`` / ``self._attr``, else None."""

    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        return None
    return None


def _compared_attribute_of(condition: ast.expr, bound_name: str) -> str | None:
    """For ``x.kind == v`` with *bound_name* ``x``, return ``"kind"``."""

    if not isinstance(condition, ast.Compare):
        return None
    left = condition.left
    if (
        isinstance(left, ast.Attribute)
        and isinstance(left.value, ast.Name)
        and left.value.id == bound_name
    ):
        return left.attr
    return None


def _module_name(repo_root: Path, component_path: str) -> str:
    return component_path.replace("/", ".").removesuffix(".py")


def _reaches_component(tree: ast.AST, module: str, exported: frozenset[str]) -> bool:
    """Can this source reach the component, directly or via a package re-export?

    Demand is only attributable to a component if the caller can actually reach
    it. Without this gate, any class exposing a collection of the same name would
    contribute demand to every other one — the measurement would be keyed to an
    attribute spelling rather than to the component.

    Three reaches count: importing the module itself; importing a name from it;
    and importing one of the names it defines from an ancestor package that
    re-exports it, which is how `from mira_core import MemoryLedger` reaches
    `mira_core/memory.py`.
    """

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name == module or alias.name.startswith(f"{module}.")
                   for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            if node.module == module:
                return True
            if not node.module:
                continue
            if module.startswith(f"{node.module}."):
                tail = module[len(node.module) + 1:]
                # `from mira_core import memory`
                if any(alias.name == tail for alias in node.names):
                    return True
                # `from mira_core import MemoryLedger`, re-exported by the package
                if any(alias.name in exported for alias in node.names):
                    return True
    return False


def _top_level_names(tree: ast.AST) -> frozenset[str]:
    """Public classes and functions a module defines, for re-export resolution."""

    names = {
        node.name
        for node in getattr(tree, "body", [])
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    }
    return frozenset(names)


def _exposed_collections(class_node: ast.ClassDef) -> frozenset[str]:
    """Public names on *class_node* that yield a sequence.

    A property or method returning ``tuple(...)``/``list(...)`` counts, as does a
    private backing attribute assigned a list in ``__init__``.
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


# ── Measurement ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class Insufficiency:
    """One unmet capability on one component, with its evidence."""

    component_path: str
    class_name: str
    capability: str
    collection: str
    attribute: str
    demand_sites: tuple[str, ...]   # files outside the component that filter by hand
    supplied: bool

    @property
    def demand(self) -> int:
        return len(self.demand_sites)

    @property
    def is_unmet(self) -> bool:
        return self.demand > 0 and not self.supplied

    def to_dict(self) -> dict:
        return {
            "component": self.component_path,
            "class": self.class_name,
            "capability": self.capability,
            "collection": self.collection,
            "attribute": self.attribute,
            "demand": self.demand,
            "demand_sites": sorted(self.demand_sites),
            "supplied": self.supplied,
            "unmet": self.is_unmet,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


def _python_sources(repo_root: Path, exclude: Path) -> Iterator[tuple[Path, ast.AST]]:
    """Walk the repository's own Python sources, pruning environment trees.

    Pruning happens during descent rather than after it: a virtualenv checked out
    from another platform can contain broken symlinks that raise on `scandir`.
    """

    skipped_dirs = {
        ".git", ".claude", ".pytest_cache", "__pycache__",
        "build", "dist", "archives", "node_modules",
    }
    exclude = exclude.resolve()

    for parent, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = sorted(
            name for name in dirnames
            if name not in skipped_dirs
            and not name.startswith(".venv")
            and not name.endswith(".egg-info")
        )
        for filename in sorted(filenames):
            if not filename.endswith(".py"):
                continue
            path = Path(parent) / filename
            if path.resolve() == exclude:
                continue
            try:
                yield path, ast.parse(path.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError, OSError):
                continue


def measure_component(repo_root: Path, component_path: str) -> tuple[Insufficiency, ...]:
    """Measure every unmet capability shape on one component."""

    source_path = repo_root / component_path
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    results: list[Insufficiency] = []

    for class_node in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
        collections = _exposed_collections(class_node)
        if not collections:
            continue

        for shape in CAPABILITY_SHAPES:
            # Demand is counted strictly outside the component.
            sites: dict[tuple[str, str], set[str]] = {}
            module = _module_name(repo_root, component_path)
            exported = _top_level_names(tree)
            for path, other_tree in _python_sources(repo_root, source_path):
                if not _reaches_component(other_tree, module, exported):
                    continue
                for collection, attribute in shape.demand_sites(other_tree, collections):
                    key = (collection, attribute)
                    sites.setdefault(key, set()).add(
                        path.relative_to(repo_root).as_posix()
                    )

            for (collection, attribute), files in sorted(sites.items()):
                results.append(Insufficiency(
                    component_path=component_path,
                    class_name=class_node.name,
                    capability=shape.name,
                    collection=collection,
                    attribute=attribute,
                    demand_sites=tuple(sorted(files)),
                    supplied=shape.is_supplied_by(class_node, collection, attribute),
                ))

    return tuple(results)


@dataclass(frozen=True)
class Diagnosis:
    """The selected component, and why it beat the alternatives."""

    selected: str | None
    unmet: tuple[Insufficiency, ...]
    considered: tuple[Insufficiency, ...]

    def to_dict(self) -> dict:
        return {
            "schema": DIAGNOSIS_SCHEMA,
            "selected": self.selected,
            "unmet": [i.to_dict() for i in self.unmet],
            "considered": [i.to_dict() for i in self.considered],
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


def diagnose(repo_root: Path, components: Sequence[str]) -> Diagnosis:
    """Select the component with the greatest unmet demand.

    Ties break on (demand, component path) so the rule is total and reproducible.
    A component with no unmet capability is never selected; if none has one, the
    diagnosis is empty rather than arbitrary.
    """

    considered: list[Insufficiency] = []
    for path in components:
        considered.extend(measure_component(repo_root, path))

    unmet = tuple(sorted(
        (i for i in considered if i.is_unmet),
        key=lambda i: (-i.demand, i.component_path, i.collection, i.attribute),
    ))

    return Diagnosis(
        selected=unmet[0].component_path if unmet else None,
        unmet=unmet,
        considered=tuple(considered),
    )
