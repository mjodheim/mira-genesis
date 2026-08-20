"""Author M094's qualification pool, by measurement rather than by invention.

The protocol commits to a pool of candidate requirements existing at the freeze.
This script produces it, and it produces it the same way the milestone produces
everything else: by running the structural diagnosis and recording what it finds.
Nothing here chooses a requirement by hand.

Two boundaries make the pool a qualification rather than a second development set:

* **cross-component.** Every entry is drawn from a component *outside* the
  development eligible set, so a mechanism specialised to the component it was
  developed against fails.
* **not reachable by the lineage.** The pool lives in `experiments/M094/` and no
  module under `metamorphosis/m094_*` reads it. `tests/test_m094_qualification_pool.py`
  asserts that, so the boundary is checked rather than promised.

Experimenter blindness is **not** claimed, exactly as M091 did not claim it. The
pool is authored by someone who has seen the development result. What is claimed
is that the lineage cannot reach it before adoption, and that the draw is a
deterministic function of the adopted mechanism's digest, so anyone can reproduce
which entries were drawn.

    python -m scripts.author_m094_qualification_pool
"""

from __future__ import annotations

import ast
import enum
import hashlib
import importlib
import inspect
import itertools
import json
from pathlib import Path

from metamorphosis.m094_diagnosis import decode_rendering, diagnose

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "experiments" / "M094" / "QUALIFICATION_POOL.json"

#: The development set. Nothing here may appear in the pool.
DEVELOPMENT_COMPONENTS = (
    "mira_core/memory.py",
    "mira_core/safety.py",
    "mira_core/contracts.py",
)

#: Hidden cases generated per requirement, per the protocol.
HIDDEN_CASES_PER_REQUIREMENT = 5

#: Seed for hidden-case generation. Fixed and disclosed, so the cases are
#: reproducible by anyone from the committed pool. Bumped for amendment A1 so the
#: regenerated cases are visibly not the superseded ones.
CASE_SEED = "m094-qualification-hidden-cases-v2"

#: Generic value shapes, tried in this fixed order for every string field until the class
#: accepts the combination. Amendment A1: the superseded generator invented one value per
#: field and never constructed the object, so seven of nine entries carried cases that raise.
#:
#: These are shapes common to software in general -- an identifier, an absolute path, a
#: content-addressed reference -- not knowledge about any class in `mira_core`. A class whose
#: constructor rejects all of them is excluded rather than accommodated.
STRING_SHAPES = (
    "{token}",
    "/{token}",
    "{token}@sha256:{digest}",
)

#: Ceiling on the shape search, so generation stays bounded on a class with many string
#: fields. Above this, only uniform shape assignments are tried.
MAX_SHAPE_COMBINATIONS = 256


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("ascii")).hexdigest()


def _candidate_components() -> list[str]:
    """Every `mira_core` module that is not part of the development set."""

    return [
        relative
        for relative in (
            path.relative_to(REPO_ROOT).as_posix()
            for path in sorted((REPO_ROOT / "mira_core").glob("*.py"))
            if path.name != "__init__.py"
        )
        if relative not in DEVELOPMENT_COMPONENTS
    ]


def _field_annotations(component: str, class_name: str) -> dict[str, str]:
    """Declared annotations, so hidden cases can carry type-plausible values."""

    tree = ast.parse((REPO_ROOT / component).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return {
                item.target.id: ast.unparse(item.annotation)
                for item in node.body
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
            }
    return {}


def _value_for(annotation: str, field: str, index: int) -> object:
    """A deterministic, type-plausible value for one field in one hidden case."""

    stem = hashlib.sha256(
        (CASE_SEED + "|" + field + "|" + str(index)).encode("ascii")
    ).hexdigest()[:8]

    lowered = annotation.lower()
    if "int" in lowered and "print" not in lowered:
        return int(stem, 16) % 1000
    if "float" in lowered:
        return round(int(stem, 16) % 10000 / 100, 2)
    if "bool" in lowered:
        return bool(int(stem, 16) % 2)
    if "mapping" in lowered or "dict" in lowered:
        return {"k" + stem[:4]: stem[4:]}
    if "tuple" in lowered or "sequence" in lowered or "list" in lowered:
        return [stem[:4], stem[4:]]
    return field + "-" + stem


def _load_class(component: str, class_name: str):
    """Import the real class, because a case is only a case if it constructs one."""

    module_name = component.replace("/", ".").removesuffix(".py")
    return getattr(importlib.import_module(module_name), class_name)


def _string_value(shape: str, field: str, index: int) -> str:
    stem = hashlib.sha256(
        (CASE_SEED + "|" + field + "|" + str(index)).encode("ascii")
    ).hexdigest()
    return shape.format(token=field + "-" + stem[:8], digest=stem[:64].ljust(64, "0"))


def _case_fields(
    cls, annotations: dict[str, str], rendering, index: int, shapes: dict[str, int],
) -> dict[str, object]:
    """One case: every required constructor argument, plus every field the requirement reads.

    Amendment A1. The superseded generator supplied only the requirement's fields, so a class
    with any other required argument could never be built from its own committed cases.
    """

    signature = inspect.signature(cls)
    wanted: list[str] = [
        name for name, parameter in signature.parameters.items()
        if parameter.default is inspect.Parameter.empty
        and parameter.kind not in (
            inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD,
        )
    ]
    for _key, field, _wrapper in rendering:
        if field in signature.parameters and field not in wanted:
            wanted.append(field)

    fields: dict[str, object] = {}
    for name in wanted:
        annotation = annotations.get(name, "str")
        value = _value_for(annotation, name, index)
        if isinstance(value, str):
            value = _string_value(STRING_SHAPES[shapes.get(name, 0)], name, index)
        fields[name] = value
    return fields


def _string_fields(cls, annotations: dict[str, str], rendering) -> list[str]:
    signature = inspect.signature(cls)
    names = [
        name for name, parameter in signature.parameters.items()
        if parameter.default is inspect.Parameter.empty
    ]
    names += [
        field for _k, field, _w in rendering
        if field in signature.parameters and field not in names
    ]
    return [
        name for name in names
        if isinstance(_value_for(annotations.get(name, "str"), name, 0), str)
    ]


def _hidden_cases(component: str, class_name: str, rendering) -> tuple[list[dict], str | None]:
    """Field assignments the repair must render correctly — every one of which constructs.

    Returns ``(cases, exclusion_reason)``. A reason means the entry does not belong in a
    qualification: an entry whose cases cannot build their class measures nothing, and scoring
    it either way would be the instrument reporting on itself.
    """

    try:
        cls = _load_class(component, class_name)
    except Exception as exc:  # noqa: BLE001 - any import failure disqualifies the entry
        return [], f"the class could not be imported: {type(exc).__name__}"

    if isinstance(cls, type) and issubclass(cls, enum.Enum):
        # An enumeration has members, not constructor fields. A requirement naming them is a
        # mis-attributed call site rather than a renderable value object.
        return [], "the class is an Enum, so it has no constructor fields to render"

    annotations = _field_annotations(component, class_name)
    strings = _string_fields(cls, annotations, rendering)

    # Try shape assignments in a fixed order until the class accepts one, uniformly first.
    assignments: list[dict[str, int]] = [
        {name: shape for name in strings} for shape in range(len(STRING_SHAPES))
    ]
    if strings and len(STRING_SHAPES) ** len(strings) <= MAX_SHAPE_COMBINATIONS:
        assignments += [
            dict(zip(strings, combination))
            for combination in itertools.product(range(len(STRING_SHAPES)), repeat=len(strings))
        ]

    last_error = "no value shape was accepted"
    for shapes in assignments or [{}]:
        cases: list[dict] = []
        try:
            for index in range(HIDDEN_CASES_PER_REQUIREMENT):
                fields = _case_fields(cls, annotations, rendering, index, shapes)
                instance = cls(**fields)
                # Every field the requirement reads must be readable on the instance, or the
                # requirement is not something any method could satisfy.
                for _key, field, _wrapper in rendering:
                    getattr(instance, field)
                cases.append({"index": index, "fields": fields})
        except Exception as exc:  # noqa: BLE001 - try the next shape assignment
            last_error = f"{type(exc).__name__}: {exc}"[:160]
            continue
        if len(cases) == HIDDEN_CASES_PER_REQUIREMENT:
            return cases, None

    return [], f"no generated case constructs the class ({last_error})"


def build_pool() -> dict:
    components = _candidate_components()
    result = diagnose(REPO_ROOT, components)

    entries = []
    excluded = []
    for insufficiency in result.unmet:
        assert insufficiency.component_path not in DEVELOPMENT_COMPONENTS, (
            "a development component leaked into the qualification pool: "
            + insufficiency.component_path
        )
        rendering = decode_rendering(insufficiency.detail)
        cases, exclusion = _hidden_cases(
            insufficiency.component_path, insufficiency.class_name, rendering
        )
        if exclusion is not None:
            # Recorded in the pool, not dropped silently. Which entries a qualification could
            # not include is part of what the qualification is worth.
            excluded.append({
                "component": insufficiency.component_path,
                "class": insufficiency.class_name,
                "requirement": [
                    {"key": key, "field": field, "wrapper": wrapper}
                    for key, field, wrapper in rendering
                ],
                "reason": exclusion,
            })
            continue
        entry = {
            "component": insufficiency.component_path,
            "class": insufficiency.class_name,
            "capability": insufficiency.capability,
            "requirement": [
                {"key": key, "field": field, "wrapper": wrapper}
                for key, field, wrapper in rendering
            ],
            "demand": insufficiency.demand,
            "demand_sites": list(insufficiency.demand_sites),
            "hidden_cases": cases,
        }
        entry["entry_digest"] = _digest(
            {k: v for k, v in entry.items() if k != "entry_digest"}
        )
        entries.append(entry)

    entries.sort(key=lambda e: e["entry_digest"])

    pool = {
        "schema": "m094-qualification-pool-v2",
        "milestone": "M094",
        "authored_at_freeze": True,
        "amendment": "A1",
        "amendment_reason": (
            "The pool frozen on 18 August 2026 carried hidden cases that were synthesised "
            "from a seed and never executed: they supplied only the fields the requirement "
            "mentioned, not the arguments the constructor required, so seven of its nine "
            "entries raised on construction. The draw for the adopted mechanism selected two "
            "of the broken entries, so a run would have reported a failed qualification that "
            "was an artifact of the instrument. Corrected before any qualification or result "
            "existed, in the open and with its arithmetic, as the standard recorded for M076 "
            "requires. The superseded pool is preserved at "
            "experiments/M094/QUALIFICATION_POOL_SUPERSEDED_A1.json."
        ),
        "every_case_is_verified_by_construction": True,
        "entries_excluded_because_they_measure_nothing": excluded,
        "experimenter_blindness_is_not_claimed": (
            "The pool is authored by someone who has seen the development result. "
            "What is claimed is that the lineage cannot reach it before adoption, and "
            "that the draw is a deterministic function of the adopted mechanism's "
            "digest, so anyone can reproduce which entries were drawn."
        ),
        "development_components_excluded": list(DEVELOPMENT_COMPONENTS),
        "candidate_components_surveyed": components,
        "hidden_cases_per_requirement": HIDDEN_CASES_PER_REQUIREMENT,
        "hidden_case_seed": CASE_SEED,
        "draw_rule": (
            "Order entries by sha256(entry_digest + adopted mechanism digest) and take "
            "the first two whose components differ. The mechanism digest does not exist "
            "until adoption, so the draw cannot be known at this freeze."
        ),
        "entries_drawn_per_qualification": 2,
        "not_importable_by_the_lineage": True,
        "entries": entries,
    }
    pool["pool_digest"] = _digest({k: v for k, v in pool.items() if k != "pool_digest"})
    return pool


def draw(pool: dict, mechanism_digest: str) -> list[dict]:
    """Apply the committed draw rule. Reproducible by anyone, after adoption."""

    ordered = sorted(
        pool["entries"],
        key=lambda e: hashlib.sha256(
            (e["entry_digest"] + mechanism_digest).encode("ascii")
        ).hexdigest(),
    )
    drawn: list[dict] = []
    for entry in ordered:
        if any(existing["component"] == entry["component"] for existing in drawn):
            continue
        drawn.append(entry)
        if len(drawn) == pool["entries_drawn_per_qualification"]:
            break
    return drawn


def main() -> int:
    pool = build_pool()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(_canonical_json(pool) + "\n", encoding="utf-8", newline="\n")

    print("qualification pool written to " + str(OUTPUT.relative_to(REPO_ROOT)))
    print("pool digest " + pool["pool_digest"])
    print()
    excluded = pool["entries_excluded_because_they_measure_nothing"]
    if excluded:
        print()
        print(str(len(excluded)) + " candidate(s) excluded because no case constructs them:")
        for item in excluded:
            print("  " + item["component"] + " / " + item["class"] + " -- " + item["reason"])
    print()
    print(str(len(pool["entries"])) + " candidate requirements, none from the development set:")
    for entry in pool["entries"]:
        keys = ", ".join(item["key"] for item in entry["requirement"])
        print(
            "  " + entry["component"] + " / " + entry["class"]
            + "  demand=" + str(entry["demand"])
            + "  -> " + keys[:60]
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
