"""Running a candidate, rather than reading it.

Amendment A2. The search accepted a candidate on a structural predicate that constrained
only the keys the requirement named; every other key it carried was unconstrained, wrapper
included. A method binding two required keys correctly and wrapping an unrelated ``int``
field in ``list()`` therefore passed acceptance and raised when executed. The qualification
found it on ``ContainerLimits`` — eight fields, a two-key requirement, thousands of accepted
candidates and a content-address tie-break among them.

The correction is not a tighter thing to read. It is to stop reading:

    a candidate is accepted when running it reproduces what the call sites wrote.

This module is that execution, shared by everything that needs it so there is one probe
rather than three. `m094_synthesis` uses it to confirm survivors before adoption,
`m094_lineage` uses it to sandbox whole variants, and both get the same answer because it is
the same subprocess.

Nothing here reads `experiments/`, and nothing here knows a component, a class or a method
name. It is handed a requirement and some values and reports what happened.
"""

from __future__ import annotations

import ast
import hashlib
import importlib
import inspect
import itertools
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

EXECUTION_SCHEMA = "m094-execution-v1"

#: Generic value shapes tried in order for a string field until the class accepts one. The
#: same disclosed ladder the qualification pool's generator uses: an identifier, an absolute
#: path, a content-addressed reference. General software vocabulary, not knowledge about any
#: particular class — a class that rejects all of them yields no case, and a candidate that
#: cannot be exercised is not accepted on the strength of not having been tested.
STRING_SHAPES = ("{token}", "/{token}", "{token}@sha256:{digest}")

#: How many surviving candidates the search will execute before giving up on confirming one.
#: Disclosed, and recorded in the search report when it binds, because a search that quietly
#: stopped looking is a different experiment from one that found nothing.
MAX_CONFIRMATIONS = 256

#: How many draws to attempt per case wanted. A class may enforce an invariant between fields,
#: so independently drawn values sometimes violate it; overdrawing lets the generator keep the
#: combinations that build instead of concluding the class cannot be built at all.
CASE_OVERDRAW = 8

#: Ceiling on the per-field shape search, matching the qualification pool's generator so the
#: two cannot disagree about whether a class is constructible.
MAX_SHAPE_COMBINATIONS = 256


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    ).hexdigest()


# ── inventing values a class will accept ─────────────────────────────


def _annotations(source: str, class_name: str) -> dict[str, str]:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return {
                item.target.id: ast.unparse(item.annotation)
                for item in node.body
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
            }
    return {}


def _scalar(annotation: str, field: str, index: int, seed: str) -> Any:
    stem = hashlib.sha256(f"{seed}|{field}|{index}".encode("ascii")).hexdigest()
    lowered = annotation.lower()
    if "bool" in lowered:
        return bool(int(stem[:8], 16) % 2)
    if "int" in lowered:
        return int(stem[:8], 16) % 1000
    if "float" in lowered:
        return round(int(stem[:8], 16) % 10000 / 100, 2)
    if "mapping" in lowered or "dict" in lowered:
        return {"k" + stem[:4]: stem[4:12]}
    if "tuple" in lowered or "sequence" in lowered or "list" in lowered or "iterable" in lowered:
        return [stem[:8], stem[8:16]]
    return None  # a string field: the shape ladder decides


#: A case field that is itself a value object travels as a recipe rather than an object,
#: because the probe runs in a subprocess and the payload is JSON. Both sides materialise it
#: with `materialise`, so the parent verifies exactly what the child constructs.
NESTED_MARKER = "__m094_construct__"


def materialise(fields: Mapping[str, Any], module: Any) -> dict[str, Any]:
    """Turn any construction recipes in *fields* into real objects."""

    built: dict[str, Any] = {}
    for name, value in fields.items():
        if isinstance(value, dict) and NESTED_MARKER in value:
            cls = getattr(module, value[NESTED_MARKER])
            built[name] = cls(**value["arguments"])
        else:
            built[name] = value
    return built


def _class_names(source: str) -> set[str]:
    """Every class the module defines, so a nested annotation can be recognised."""

    return {
        node.name for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ClassDef)
    }


def _build_nested(module, class_name, annotations, siblings, source, index, seed, shapes):
    """Construct a value object to fill a field annotated as one.

    One level: a field whose own field is another value object is left to the string ladder,
    which will fail loudly rather than silently produce something that raises deeper in.
    """

    inner = getattr(module, class_name, None)
    if inner is None:
        return None
    inner_annotations = _annotations(source, class_name)
    try:
        signature = inspect.signature(inner)
    except (TypeError, ValueError):
        return None
    arguments: dict[str, Any] = {}
    for name, parameter in signature.parameters.items():
        if parameter.default is not inspect.Parameter.empty:
            continue
        annotation = inner_annotations.get(name, "str").strip()
        if annotation in siblings:
            return None  # deeper nesting: not this function's business
        value = _scalar(annotation, f"{class_name}.{name}", index, seed)
        if value is None:
            value = _string(STRING_SHAPES[shapes.get(name, 0)], f"{class_name}.{name}", index, seed)
        arguments[name] = value
    try:
        inner(**arguments)  # verified here; transported as a recipe
    except Exception:  # noqa: BLE001 - an unbuildable inner object yields no case
        return None
    return {NESTED_MARKER: class_name, "arguments": arguments}


def _string(shape: str, field: str, index: int, seed: str) -> str:
    stem = hashlib.sha256(f"{seed}|{field}|{index}".encode("ascii")).hexdigest()
    return shape.format(token=f"{field}-{stem[:8]}", digest=stem[:64].ljust(64, "0"))


def constructible_cases(
    root: Path,
    component_path: str,
    class_name: str,
    requirement: Sequence[tuple[str, str, str | None]],
    *,
    count: int = 6,
    seed: str = "m094-execution-cases-v1",
) -> tuple[dict[str, Any], ...]:
    """Constructor arguments the class actually accepts, verified by building it.

    Every argument without a default, plus every field the requirement reads that the
    constructor takes. String fields walk the shape ladder until the class stops raising.
    Returns an empty tuple when nothing works, which callers must treat as "this measures
    nothing" rather than as a failure of whatever they were testing.
    """

    module_name = component_path.replace("/", ".").removesuffix(".py")
    source = (root / component_path).read_text(encoding="utf-8")
    annotations = _annotations(source, class_name)
    # Classes the same module defines, so a field annotated as one of them can be built rather
    # than filled with a string. Without this, a value object nested inside another is
    # constructed as text and every method that reaches into it raises -- so a correct repair
    # is refused and the entry reads as a refutation. The same shape of defect as the
    # qualification pool's unbuildable cases, one level down.
    sibling_classes = _class_names(source)

    # The module must be imported from *this* root, not served from a previous import of the
    # same dotted name. Without the purge a second component sharing a package name is
    # silently measured against the first one's classes -- the class is simply missing and
    # the caller is told "no case constructs", which reads as a refutation of whatever it was
    # testing. Every entry the purge protects is one the qualification would have got wrong.
    package = module_name.split(".")[0]
    stale = {name: sys.modules[name] for name in list(sys.modules) if name.split(".")[0] == package}
    for name in stale:
        del sys.modules[name]
    try:
        sys.path.insert(0, str(root))
        module = importlib.import_module(module_name)
        cls = getattr(module, class_name)
        signature = inspect.signature(cls)
    except Exception:  # noqa: BLE001 - an unimportable class yields no cases
        return ()
    finally:
        if str(root) in sys.path:
            sys.path.remove(str(root))
        for name in list(sys.modules):
            if name.split(".")[0] == package:
                del sys.modules[name]
        sys.modules.update(stale)
    # `module` is kept alive deliberately: nested construction needs the classes it defines,
    # and re-importing per field would undo the purge above.

    wanted = [
        name for name, parameter in signature.parameters.items()
        if parameter.default is inspect.Parameter.empty
        and parameter.kind not in (
            inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD,
        )
    ]
    for _key, field, _wrapper in requirement:
        if field in signature.parameters and field not in wanted:
            wanted.append(field)

    strings = [
        name for name in wanted if _scalar(annotations.get(name, "str"), name, 0, seed) is None
    ]

    # Draw more candidates than are needed and keep the ones that build. A class can enforce
    # an invariant *between* fields -- `mira_core.contracts.Observation` refuses `success`
    # without `terminal` -- and values drawn independently will sometimes violate it. Treating
    # that as "this class cannot be constructed" was wrong twice over: it discarded the many
    # combinations that are fine, and it made a class unrepairable because of an unlucky draw.
    # A case that does not construct is simply not a case, which is what this module already
    # says everywhere else.
    # Shape assignments to try: every field the same shape first, then per-field combinations
    # when the space is small enough. A class can constrain two string fields differently --
    # `mira_core/container.py::ContainerSpec` wants a content-addressed `image` and an absolute
    # `working_directory`, and no uniform assignment satisfies both. The qualification pool's
    # generator has always searched combinations; this one did not, so the two disagreed about
    # whether a class could be constructed and the weaker of them gated the mechanism.
    assignments: list[dict[str, int]] = [
        {name: shape for name in strings} for shape in range(len(STRING_SHAPES))
    ]
    if strings and len(STRING_SHAPES) ** len(strings) <= MAX_SHAPE_COMBINATIONS:
        assignments += [
            dict(zip(strings, combination))
            for combination in itertools.product(
                range(len(STRING_SHAPES)), repeat=len(strings)
            )
        ]

    for shapes in assignments or [{}]:
        cases: list[dict[str, Any]] = []
        for index in range(count * CASE_OVERDRAW):
            fields: dict[str, Any] = {}
            for name in wanted:
                annotation = annotations.get(name, "str").strip()
                if annotation in sibling_classes:
                    built = _build_nested(
                        module, annotation, annotations, sibling_classes,
                        source, index, seed, shapes,
                    )
                    if built is None:
                        fields = {}
                        break
                    fields[name] = built
                    continue
                value = _scalar(annotation, name, index, seed)
                if value is None:
                    value = _string(STRING_SHAPES[shapes.get(name, 0)], name, index, seed)
                fields[name] = value
            if not fields and wanted:
                continue
            try:
                instance = cls(**materialise(fields, module))
                for _key, field, _wrapper in requirement:
                    getattr(instance, field)
            except Exception:  # noqa: BLE001 - not a case; try the next draw
                continue
            cases.append(fields)
            if len(cases) == count:
                return tuple(cases)
        if not strings:
            break
    return ()


# ── the subprocess probe ─────────────────────────────────────────────


def repo_dependencies(root: Path, component_path: str, source: str) -> tuple[str, ...]:
    """Repository modules the variant imports, transitively.

    Read from *source* rather than from disk for the component itself, because the variant
    being probed is often not what is on disk — and during a rollback proof the live file is
    deliberately damaged. An unparsable source contributes no edges, which is the right
    answer: a broken variant has no discoverable imports.
    """

    seen: set[str] = {component_path}
    queue: list[str] = []

    def edges(text: str) -> list[str]:
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return []
        found: list[str] = []
        for item in ast.walk(tree):
            modules: list[str] = []
            if isinstance(item, ast.Import):
                modules = [alias.name for alias in item.names]
            elif isinstance(item, ast.ImportFrom) and item.module:
                modules = [item.module]
            for module in modules:
                candidate = module.replace(".", "/") + ".py"
                if (root / candidate).exists():
                    found.append(candidate)
        return found

    queue.extend(edges(source))
    while queue:
        current = queue.pop()
        if current in seen:
            continue
        seen.add(current)
        queue.extend(edges((root / current).read_text(encoding="utf-8")))
    return tuple(sorted(seen - {component_path}))


#: Executed in the disposable subprocess. It receives one or more candidate sources and
#: reports, for each, which public zero-argument methods reproduce the requirement when run.
#: It is never told the method name, so a candidate cannot pass by being called `as_mapping`.
_PROBE = r'''
import importlib, json, sys, traceback

payload = json.loads(sys.stdin.read())
sys.path.insert(0, ".")

def wrap(value, wrapper):
    if wrapper == "list":
        return list(value)
    if wrapper == "tuple":
        return tuple(value)
    if isinstance(wrapper, str) and wrapper.startswith("nested:"):
        # M095. The call site wrote a mapping over the inner object's fields, so that mapping
        # is what a correct candidate must produce -- not the object. The pairs travel in the
        # wrapper, so nothing has to discover a renderer to know the expected value. An audit
        # found this wrapper empty, and the probe refusing every correct candidate because it
        # compared a mapping against a value object.
        expected = {}
        for piece in wrapper[len("nested:"):].split(";"):
            if not piece:
                continue
            key, _, field = piece.partition(":")
            expected[key] = getattr(value, field)
        return expected
    return value

requirement = [tuple(item) for item in payload["requirement"]]
cases = payload["cases"]
marker = payload["nested_marker"]
results = []


def materialise(fields, module):
    built = {}
    for name, value in fields.items():
        if isinstance(value, dict) and marker in value:
            built[name] = getattr(module, value[marker])(**value["arguments"])
        else:
            built[name] = value
    return built

for variant in payload["variants"]:
    record = {"id": variant["id"], "imported": False, "cases_total": len(cases),
              "cases_constructible": 0, "cases_satisfied": 0,
              "satisfying_methods": [], "error": None}
    try:
        with open(payload["module_file"], "w", encoding="utf-8") as handle:
            handle.write(variant["source"])
        for name in [m for m in list(sys.modules) if m.startswith(payload["package"])]:
            del sys.modules[name]
        module = importlib.import_module(payload["module"])
        cls = getattr(module, payload["class"])
        record["imported"] = True

        constructible = 0
        for case in cases:
            try:
                cls(**materialise(case, module))
                constructible += 1
            except Exception:
                pass
        record["cases_constructible"] = constructible

        names = sorted(
            n for n in dir(cls)
            if not n.startswith("_") and callable(getattr(cls, n, None))
        )
        agreeing = []
        for name in names:
            satisfied = 0
            for case in cases:
                try:
                    instance = cls(**materialise(case, module))
                except Exception:
                    continue
                try:
                    produced = getattr(instance, name)()
                except Exception:
                    break
                if not isinstance(produced, dict):
                    break
                ok = True
                for key, attribute, wrapper in requirement:
                    try:
                        expected = wrap(getattr(instance, attribute), wrapper)
                    except Exception:
                        ok = False
                        break
                    if key not in produced or produced[key] != expected:
                        ok = False
                        break
                if not ok:
                    break
                satisfied += 1
            if constructible and satisfied == constructible:
                agreeing.append(name)
        record["satisfying_methods"] = agreeing
        if agreeing:
            record["cases_satisfied"] = constructible
    except Exception:
        record["error"] = traceback.format_exc(limit=4)
    results.append(record)

print("M094_PROBE:" + json.dumps(results, sort_keys=True))
'''


def probe_variants(
    root: Path,
    component_path: str,
    variants: Sequence[tuple[str, str]],
    class_name: str,
    requirement: Sequence[tuple[str, str, str | None]],
    cases: Sequence[Mapping[str, Any]],
    *,
    timeout_seconds: int = 300,
) -> list[dict[str, Any]]:
    """Run every variant in one disposable subprocess and report what each did.

    Many variants share a process on purpose. Confirming a search's survivors one process at
    a time would cost more than the search, and the point of A2 is that execution becomes the
    acceptance rule rather than a luxury applied to the winner.
    """

    if not variants:
        return []

    module = component_path.replace("/", ".").removesuffix(".py")
    package = module.split(".")[0]
    with tempfile.TemporaryDirectory(prefix="m094-exec-") as tmp:
        sandbox = Path(tmp)
        target = sandbox / component_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(variants[0][1], encoding="utf-8")
        for parent in Path(component_path).parents:
            if str(parent) not in {".", ""}:
                (sandbox / parent / "__init__.py").write_text("", encoding="utf-8")
        for dependency in repo_dependencies(root, component_path, variants[0][1]):
            destination = sandbox / dependency
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / dependency, destination)
            for parent in Path(dependency).parents:
                if str(parent) not in {".", ""}:
                    marker = sandbox / parent / "__init__.py"
                    if not marker.exists():
                        marker.write_text("", encoding="utf-8")

        script = sandbox / "_m094_probe.py"
        script.write_text(_PROBE, encoding="utf-8")
        payload = json.dumps({
            "module": module,
            "module_file": str(target),
            "package": package,
            "class": class_name,
            "requirement": [list(item) for item in requirement],
            "cases": [dict(case) for case in cases],
            "nested_marker": NESTED_MARKER,
            "variants": [{"id": name, "source": source} for name, source in variants],
        }, sort_keys=True)

        try:
            completed = subprocess.run(
                [sys.executable, str(script)],
                cwd=sandbox, input=payload, capture_output=True, text=True,
                timeout=timeout_seconds,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
        except subprocess.TimeoutExpired:
            return [
                {"id": name, "imported": False, "cases_total": len(cases),
                 "cases_constructible": 0, "cases_satisfied": 0,
                 "satisfying_methods": [], "error": "TIMEOUT"}
                for name, _ in variants
            ]

        line = next(
            (l for l in completed.stdout.splitlines() if l.startswith("M094_PROBE:")), None
        )
        if line is None:
            return [
                {"id": name, "imported": False, "cases_total": len(cases),
                 "cases_constructible": 0, "cases_satisfied": 0, "satisfying_methods": [],
                 "error": (completed.stderr or "no probe output")[-600:]}
                for name, _ in variants
            ]
        return json.loads(line[len("M094_PROBE:"):])


def agrees(record: Mapping[str, Any]) -> bool:
    """Did this variant reproduce the requirement, on cases that actually built?"""

    return bool(
        record.get("imported")
        and int(record.get("cases_constructible", 0)) > 0
        and int(record.get("cases_satisfied", 0)) == int(record.get("cases_constructible", 0))
    )
