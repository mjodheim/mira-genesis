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


# ── Candidate classes ─────────────────────────────────────────


@dataclass(frozen=True)
class CandidateClass:
    """One class a call site might be talking about.

    Attribution asks which classes could explain a site, not how many fields it
    reads. That replaces an authored threshold with a property of the
    repository: a site explained by exactly one reachable class is evidence
    about that class, and a site explained by several is evidence about none.
    """

    component_path: str
    module: str
    exported: frozenset[str]
    class_name: str
    fields: frozenset[str]

    @property
    def identity(self) -> tuple[str, str]:
        return (self.component_path, self.class_name)


# ── How callers render an object ───────────────────────────────


def _encode_rendering(entries: Sequence[tuple[str, str, str | None]]) -> str:
    """Serialise (key, field, wrapper) triples into a comparable string.

    The wrapper is part of the observation. A caller that wrote
    ``list(goal.success_criteria)`` did not write ``goal.success_criteria``, and
    a repair that returns the second does not reproduce the first.
    """

    return ",".join(sorted(
        key + "=" + attribute + "|" + (wrapper or "")
        for key, attribute, wrapper in entries
    ))


def decode_rendering(detail: str) -> tuple[tuple[str, str, str | None], ...]:
    """Recover the (key, field, wrapper) triples encoded by `_encode_rendering`."""

    triples: list[tuple[str, str, str | None]] = []
    for piece in detail.split(","):
        if not piece:
            continue
        key, _, rest = piece.partition("=")
        attribute, _, wrapper = rest.partition("|")
        triples.append((key, attribute, wrapper or None))
    return tuple(triples)


def rendering_fields(detail: str) -> frozenset[str]:
    """The set of fields a rendering reads, ignoring keys and wrappers."""

    return frozenset(attribute for _, attribute, _ in decode_rendering(detail))


# ── Capability shapes ────────────────────────────────────────────────


@dataclass(frozen=True)
class FilterByAttribute:
    """Selecting the members of an exposed collection by one attribute.

    The shape is generic: it mentions no collection name and no attribute name.
    Both are recovered from the source being measured.
    """

    name: str = "filter_collection_by_attribute"

    #: Filtering by one attribute and filtering by another are different
    #: capabilities, so their demand is counted separately.
    merges_details: bool = False

    def applies_to(self, class_node: ast.ClassDef) -> bool:
        return bool(_exposed_collections(class_node))

    def demand_sites(
        self,
        tree: ast.AST,
        class_node: ast.ClassDef,
        rivals: Sequence[CandidateClass] = (),
    ) -> list[tuple[str, str]]:
        """Find hand-written filters over a collection this class exposes.

        ``rivals`` is unused here: a filter names the collection it iterates, so
        the site already identifies what it is talking about.

        Returns (collection_name, attribute_name) for each site, e.g. a
        comprehension of the form ``x for x in obj.events if x.kind == k``.
        """

        collections = _exposed_collections(class_node)
        if not collections:
            return []

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


@dataclass(frozen=True)
class RenderAsMapping:
    """Rebuilding a value object's fields into a mapping, at the call site.

    When several callers each write out the same fields of the same value object
    into a dict literal, the object could render itself and they do not. The
    shape mentions no class, field or method name: the field set is recovered
    from the class under measurement, and a caller is attributed to that class
    only when it is the single reachable class that could explain the site.
    """

    name: str = "render_value_object_as_mapping"

    #: Callers reading different subsets of the same object want one method, not
    #: several: a renderer covering the union satisfies every subset. Their
    #: demand is therefore pooled rather than split.
    merges_details: bool = True

    def applies_to(self, class_node: ast.ClassDef) -> bool:
        return bool(_declared_fields(class_node))

    def demand_sites(
        self,
        tree: ast.AST,
        class_node: ast.ClassDef,
        rivals: Sequence[CandidateClass] = (),
    ) -> list[tuple[str, str]]:
        """Attribute a hand-written mapping to this class only when nothing else explains it.

        An earlier revision required the site to read at least three of the
        class's fields, so that name coincidence would not be mistaken for
        evidence. That threshold was authored, and sweeping it moved which
        component the diagnosis selected — the constant was deciding, which is
        the defect it was meant to avoid, one level up.

        The rule here asks a question the repository answers instead: of the
        classes this file can actually reach, how many could have produced this
        site? Exactly one is evidence about that class. Several is evidence
        about none, because the site does not say which. Zero is not evidence at
        all. No number appears anywhere in that.
        """

        fields = _declared_fields(class_node)
        if not fields:
            return []

        found: list[tuple[str, str]] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue

            # (key, field, wrapper) for every value that reads an object.
            read: dict[str, list[tuple[str, str, str | None]]] = {}
            for key, value in zip(node.keys, node.values):
                base, attribute, wrapper = _attribute_read(value)
                if base is None or attribute is None:
                    continue
                name = key.value if isinstance(key, ast.Constant) and isinstance(key.value, str) else attribute
                read.setdefault(base, []).append((name, attribute, wrapper))

            # A dict that reads several objects is evidence about each of them.
            # An earlier revision required the dict to read exactly one object,
            # on the reasoning that a mixed record is not a rendering of either.
            # That was too strong and it was wrong: the `action_admission` record
            # reads four fields of one decision alongside two of one action, and
            # it is precisely the evidence that neither can render itself. What
            # each object is asked for is its own slice, so each slice is judged
            # on its own.
            for entries in read.values():
                attributes = {attribute for _, attribute, _ in entries}
                if not attributes or not attributes <= fields:
                    continue

                explainers = {
                    rival.identity for rival in rivals if attributes <= rival.fields
                }
                # `rivals` carries every eligible class this file can reach,
                # including the one under measurement.
                if len(explainers) != 1:
                    continue
                if not any(name == class_node.name for _, name in explainers):
                    continue

                found.append((class_node.name, _encode_rendering(entries)))
        return found

    def is_supplied_by(
        self, class_node: ast.ClassDef, target: str, detail: str
    ) -> bool:
        """Does the class define a method that reproduces what the callers wrote?

        An earlier revision asked only whether some public method returned a
        mapping whose *keys* covered the required ones. That is cheap to
        satisfy: the field each key was bound to, and any container the caller
        wrapped it in, were both unconstrained, so hundreds of different methods
        passed and the search that produced them was not discriminating.

        The requirement here is agreement. For every ``key -> field`` the callers
        were writing by hand, the method must bind that same key to that same
        field, wrapped exactly as the callers wrapped it. A method that returns
        ``success_criteria`` bare where every caller wrote
        ``list(success_criteria)`` does not let those callers delete their line,
        so it does not supply the capability.
        """

        wanted = decode_rendering(detail)
        if not wanted:
            return False

        for node in class_node.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name.startswith("_"):
                continue
            for inner in ast.walk(node):
                if not isinstance(inner, ast.Return) or inner.value is None:
                    continue
                produced = _mapping_bindings(inner.value)
                if produced is None:
                    continue
                if all(produced.get(key) == (attribute, wrapper)
                       for key, attribute, wrapper in wanted):
                    return True
        return False


CAPABILITY_SHAPES: tuple[object, ...] = (FilterByAttribute(), RenderAsMapping())


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


def _attribute_read(node: ast.expr) -> tuple[str | None, str | None, str | None]:
    """For ``d.allowed`` return ``("d", "allowed", None)``.

    ``list(d.missing)`` returns ``("d", "missing", "list")``. The wrapper is kept
    rather than discarded because a candidate repair that returns the field bare
    where the caller wrapped it does not reproduce what the caller wrote, and
    acceptance has to be able to tell those apart.
    """

    wrapper: str | None = None
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"list", "tuple", "set", "dict", "sorted"}
        and len(node.args) == 1
    ):
        wrapper = node.func.id
        node = node.args[0]
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return node.value.id, node.attr, wrapper
    return None, None, None


def _mapping_bindings(node: ast.expr) -> dict[str, tuple[str, str | None]] | None:
    """For a returned dict literal, map each key to the (field, wrapper) it binds.

    ``{"a": self.x, "b": list(self.y)}`` gives ``{"a": ("x", None), "b": ("y", "list")}``.
    Returns None when the expression is not a dict literal at all.
    """

    if not isinstance(node, ast.Dict):
        return None

    bindings: dict[str, tuple[str, str | None]] = {}
    for key, value in zip(node.keys, node.values):
        if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
            continue
        wrapper: str | None = None
        expr = value
        if (
            isinstance(expr, ast.Call)
            and isinstance(expr.func, ast.Name)
            and expr.func.id in {"list", "tuple", "set", "dict", "sorted"}
            and len(expr.args) == 1
        ):
            wrapper = expr.func.id
            expr = expr.args[0]
        if isinstance(expr, ast.Attribute) and isinstance(expr.value, ast.Name):
            bindings[key.value] = (expr.attr, wrapper)
    return bindings


def _mapping_keys(node: ast.expr) -> frozenset[str] | None:
    """String keys of a returned dict literal or ``dict(a=..., b=...)`` call."""

    if isinstance(node, ast.Dict):
        keys = {
            key.value for key in node.keys
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        }
        return frozenset(keys)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dict":
        return frozenset(kw.arg for kw in node.keywords if kw.arg)
    return None


def _declared_fields(class_node: ast.ClassDef) -> frozenset[str]:
    """Field names a class declares, whether as annotations or in ``__init__``."""

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
            elif not node.name.startswith("_"):
                # A read-only property is a field as far as callers are concerned.
                if any(
                    isinstance(decorator, ast.Name) and decorator.id == "property"
                    for decorator in node.decorator_list
                ):
                    names.add(node.name)
    return frozenset(name for name in names if not name.startswith("_"))


def _module_name(repo_root: Path, component_path: str) -> str:
    return component_path.replace("/", ".").removesuffix(".py")


def _reaches_component_cached(
    path: Path, tree: ast.AST, module: str, exported: frozenset[str]
) -> bool:
    """`_reaches_component`, remembered per (file identity, module, exported names).

    The predicate is a pure function of the file's syntax tree and the component's module
    name and exported names, so caching it changes no measurement. It was the dominant
    remaining cost: 2446 calls per diagnosis, each an `ast.walk` of a whole file.
    """

    try:
        stat = path.stat()
        key = (str(path), stat.st_size, stat.st_mtime_ns, module, exported)
    except OSError:
        return _reaches_component(tree, module, exported)
    cached = _REACH_CACHE.get(key)
    if cached is None:
        cached = _reaches_component(tree, module, exported)
        _REACH_CACHE[key] = cached
    return cached


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
    target: str      # what the shape keys on, e.g. a collection or a class
    detail: str      # the specific of that shape, e.g. an attribute or field set
    demand_sites: tuple[str, ...]   # files outside the component doing it by hand
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
            "target": self.target,
            "detail": self.detail,
            "demand": self.demand,
            "demand_sites": sorted(self.demand_sites),
            "supplied": self.supplied,
            "unmet": self.is_unmet,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


#: Parsed repository sources, keyed by tree identity rather than by path alone.
#:
#: `measure_component` walks every source once per eligible component, so a three-component
#: diagnosis parsed all 644 files three times: 1935 `ast.parse` calls, and the dominant cost
#: of the whole M094 loop. The cache key carries each file's size and modification time, so
#: an edited file is re-parsed and a stale entry cannot be served. Caching a pure function of
#: the file's bytes changes no measurement -- `docs/REPOSITORY_AUDIT_2026_08_18.md` records
#: the diagnosis digest before and after, and it is the same.
_PARSE_CACHE: dict[tuple[str, int, int], ast.AST] = {}

#: Whether one source can reach one component. Called once per (reaching file, candidate
#: class), which is where the remaining time went after the parse cache. Keyed on the file's
#: identity and on the exported names, so a component that gains or loses a public name is
#: measured again rather than remembered.
_REACH_CACHE: dict[tuple[str, int, int, str, frozenset[str]], bool] = {}


def _parse_cached(path: Path) -> ast.AST | None:
    """Parse *path* once per (path, size, mtime). Returns None if it cannot be read."""

    try:
        stat = path.stat()
        key = (str(path), stat.st_size, stat.st_mtime_ns)
    except OSError:
        return None
    cached = _PARSE_CACHE.get(key)
    if cached is not None:
        return cached
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return None
    _PARSE_CACHE[key] = tree
    return tree


def clear_caches() -> None:
    """Drop the parse and reachability caches.

    Only needed by a caller that rewrites a source and re-measures within the same process
    faster than the filesystem's modification-time resolution can distinguish. The arm
    runners do exactly that, so the entry point is public rather than an internal detail.
    """

    _PARSE_CACHE.clear()
    _REACH_CACHE.clear()


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
            tree = _parse_cached(path)
            if tree is not None:
                yield path, tree


def _pool_by_target(
    sites: dict[tuple[str, str], set[str]]
) -> dict[tuple[str, str], set[str]]:
    """Pool demand for one target, but only across renderings that agree.

    Callers reading different subsets of the same object want one method, and a
    renderer covering the union satisfies all of them -- so those pool.

    Callers that bind the *same key differently* do not. If one writes
    ``list(x.missing)`` and another writes ``x.missing``, no single method
    reproduces both, and unioning them would manufacture a requirement nothing
    can satisfy: the component would read as permanently insufficient for a
    reason no repair could ever address. Those stay separate requirements, each
    with its own demand, and the larger one is simply the more demanded.
    """

    pooled: dict[str, list[tuple[dict[str, tuple[str, str | None]], set[str]]]] = {}

    for (target, detail), paths in sorted(sites.items()):
        rendering = {key: (attribute, wrapper)
                     for key, attribute, wrapper in decode_rendering(detail)}
        groups = pooled.setdefault(target, [])
        for existing, existing_paths in groups:
            if all(existing.get(key, binding) == binding
                   for key, binding in rendering.items()):
                existing.update(rendering)
                existing_paths.update(paths)
                break
        else:
            groups.append((dict(rendering), set(paths)))

    result: dict[tuple[str, str], set[str]] = {}
    for target in sorted(pooled):
        for rendering, paths in pooled[target]:
            detail = _encode_rendering(
                [(key, attribute, wrapper)
                 for key, (attribute, wrapper) in rendering.items()]
            )
            result[(target, detail)] = paths
    return result


def candidate_classes(
    repo_root: Path, components: Sequence[str]
) -> tuple[CandidateClass, ...]:
    """Every class that could explain a call site, across all eligible components.

    Attribution is decided by how many of these a site fits, so the set has to be
    assembled before any one component is measured.
    """

    candidates: list[CandidateClass] = []
    for component_path in components:
        tree = ast.parse((repo_root / component_path).read_text(encoding="utf-8"))
        module = _module_name(repo_root, component_path)
        exported = _top_level_names(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                candidates.append(CandidateClass(
                    component_path=component_path,
                    module=module,
                    exported=exported,
                    class_name=node.name,
                    fields=_declared_fields(node),
                ))
    return tuple(candidates)


def measure_component(
    repo_root: Path,
    component_path: str,
    candidates: Sequence[CandidateClass] | None = None,
) -> tuple[Insufficiency, ...]:
    """Measure every unmet capability shape on one component.

    ``candidates`` is the set of classes a call site might otherwise be talking
    about. It defaults to this component's own classes, which is right when a
    component is measured alone; `diagnose` supplies the whole eligible set so
    that a site two components could equally explain is credited to neither.
    """

    source_path = repo_root / component_path
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    results: list[Insufficiency] = []

    module = _module_name(repo_root, component_path)
    exported = _top_level_names(tree)

    if candidates is None:
        candidates = candidate_classes(repo_root, [component_path])

    # Parse the reaching sources once, rather than once per class and shape.
    reaching_paths: list[tuple[Path, str, ast.AST]] = [
        (path, path.relative_to(repo_root).as_posix(), other_tree)
        for path, other_tree in _python_sources(repo_root, source_path)
        if _reaches_component_cached(path, other_tree, module, exported)
    ]
    reaching: list[tuple[str, ast.AST]] = [
        (relative, other_tree) for _path, relative, other_tree in reaching_paths
    ]

    # Which rival classes each reaching file can also see. A class it cannot
    # reach is not an alternative explanation for anything written there.
    rivals_by_file: dict[str, tuple[CandidateClass, ...]] = {
        relative: tuple(
            candidate for candidate in candidates
            if _reaches_component_cached(
                path, other_tree, candidate.module, candidate.exported
            )
        )
        for path, relative, other_tree in reaching_paths
    }

    for class_node in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
        for shape in CAPABILITY_SHAPES:
            if not shape.applies_to(class_node):
                continue

            # Demand is counted strictly outside the component.
            sites: dict[tuple[str, str], set[str]] = {}
            for relative, other_tree in reaching:
                for target, detail in shape.demand_sites(
                    other_tree, class_node, rivals_by_file[relative]
                ):
                    sites.setdefault((target, detail), set()).add(relative)

            if getattr(shape, "merges_details", False):
                sites = _pool_by_target(sites)

            for (target, detail), files in sorted(sites.items()):
                results.append(Insufficiency(
                    component_path=component_path,
                    class_name=class_node.name,
                    capability=shape.name,
                    target=target,
                    detail=detail,
                    demand_sites=tuple(sorted(files)),
                    supplied=shape.is_supplied_by(class_node, target, detail),
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

    The ordering key is ``(-demand, component_path, capability, target, detail)``, so
    the rule is total and reproducible. A component with no unmet capability is never
    selected; if none has one, the diagnosis is empty rather than arbitrary.

    An earlier version of this docstring said ties break on "(demand, component path)",
    which omitted the terms that actually decide. ``target`` is the class name, so when
    two classes tie on demand -- as ``Goal`` and ``Observation`` currently do in
    ``mira_core/contracts.py`` -- the class that gets repaired is chosen by alphabetical
    order on its identifier, not by measurement. The component-level selection is
    invariant under renaming; the class-level selection is not. This is disclosed in
    ``docs/REPOSITORY_AUDIT_2026_08_18.md`` and is left unchanged here: altering the key
    would move the adopted mechanism digest, and with it the qualification draw, which is
    a decision for the project owner to record before the run rather than a cleanup.
    """

    candidates = candidate_classes(repo_root, components)

    considered: list[Insufficiency] = []
    for path in components:
        considered.extend(measure_component(repo_root, path, candidates))

    unmet = tuple(sorted(
        (i for i in considered if i.is_unmet),
        key=lambda i: (-i.demand, i.component_path, i.capability, i.target, i.detail),
    ))

    return Diagnosis(
        selected=unmet[0].component_path if unmet else None,
        unmet=unmet,
        considered=tuple(considered),
    )
