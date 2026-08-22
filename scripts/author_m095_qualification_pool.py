"""Author and audit M095's finite structural qualification population.

M095 cannot draw a natural demand from ``mira_core`` without planting the demand it
then claims to discover.  The disclosed alternative is an exhaustive finite population:
three structural families crossed with three demand arrangements.  No salt or draw can
turn an inconvenient entry into an easier one; all nine entries are qualification data.

This module may build and inspect S0, including exhausting the negative B-from-S0
control required by amendment A1.  It deliberately never calls ``m095_chain.run`` or
``run_existing``.  The enabling outcome is first acquired only after the protocol is
frozen and the qualification runner is explicitly armed.

Run ``python -m scripts.author_m095_qualification_pool`` to print the candidate pool and
its construction audit.  It writes nothing.
"""

from __future__ import annotations

import ast
import hashlib
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

from metamorphosis import m095_chain as chain
from metamorphosis import m095_world as world

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "experiments" / "M095" / "QUALIFICATION_POOL.json"
POOL_SCHEMA = "m095-qualification-pool-v1"


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


@dataclass(frozen=True)
class Structure:
    id: str
    inner_class: str
    outer_class: str
    nested_field: str
    inner_fields: tuple[tuple[str, str, str], ...]
    outer_fields: tuple[tuple[str, str], ...]
    inner_rendered: tuple[str, ...]
    outer_rendered: tuple[str, ...]
    axes: tuple[str, ...]


STRUCTURES = (
    Structure(
        id="renamed_minimal",
        inner_class="Coordinate",
        outer_class="Envelope",
        nested_field="coordinate",
        inner_fields=(("x", "str", "x_axis"), ("y", "str", "y_axis")),
        outer_fields=(("label", "str"),),
        inner_rendered=("x", "y"),
        outer_rendered=("label",),
        axes=("renamed classes", "renamed fields", "re-keyed inner mapping"),
    ),
    Structure(
        id="larger_arity",
        inner_class="Vector",
        outer_class="Frame",
        nested_field="vector",
        inner_fields=(
            ("horizontal", "int", "x"),
            ("vertical", "int", "y"),
            ("depth", "int", "z"),
        ),
        outer_fields=(("frame_id", "str"), ("sequence", "int")),
        inner_rendered=("horizontal", "vertical", "depth"),
        outer_rendered=("frame_id", "sequence"),
        axes=("three-field inner", "two scalar outer fields", "integer values"),
    ),
    Structure(
        id="unrelated_and_collection",
        inner_class="Marker",
        outer_class="Batch",
        nested_field="marker",
        inner_fields=(
            ("code", "str", "code"),
            ("confidence", "float", "confidence"),
            ("active", "bool", "active"),
        ),
        outer_fields=(("batch_id", "str"), ("tags", "list[str]"), ("ignored", "int")),
        inner_rendered=("code", "confidence"),
        outer_rendered=("batch_id", "tags"),
        axes=(
            "declared fields omitted from the demand",
            "collection-valued outer field",
            "mixed scalar types",
        ),
    ),
)


ARRANGEMENTS = (
    {
        "id": "ranking_unaided",
        "inner_call_sites": 3,
        "outer_call_sites": 2,
        "expected_relation": True,
        "expected_descent": False,
    },
    {
        "id": "failed_search_descent",
        "inner_call_sites": 1,
        "outer_call_sites": 3,
        "expected_relation": True,
        "expected_descent": True,
    },
    {
        "id": "no_visible_enabler",
        "inner_call_sites": 0,
        "outer_call_sites": 2,
        "expected_relation": False,
        "expected_descent": False,
    },
)


def _structure_dict(spec: Structure) -> dict[str, object]:
    return {
        "id": spec.id,
        "inner_class": spec.inner_class,
        "outer_class": spec.outer_class,
        "nested_field": spec.nested_field,
        "inner_fields": [
            {"field": field, "annotation": annotation, "key": key}
            for field, annotation, key in spec.inner_fields
        ],
        "outer_fields": [
            {"field": field, "annotation": annotation}
            for field, annotation in spec.outer_fields
        ],
        "inner_rendered": list(spec.inner_rendered),
        "outer_rendered": list(spec.outer_rendered),
        "variation_axes": list(spec.axes),
    }


def build_pool() -> dict[str, object]:
    structures = [_structure_dict(spec) for spec in STRUCTURES]
    arrangements = [dict(item) for item in ARRANGEMENTS]
    entries = []
    for structure in structures:
        for arrangement in arrangements:
            entry = {
                "id": f"{structure['id']}--{arrangement['id']}",
                "structure": structure["id"],
                "arrangement": arrangement["id"],
                "inner_call_sites": arrangement["inner_call_sites"],
                "outer_call_sites": arrangement["outer_call_sites"],
                "expected_relation": arrangement["expected_relation"],
                "expected_descent": arrangement["expected_descent"],
            }
            entry["entry_digest"] = digest(entry)
            entries.append(entry)
    pool: dict[str, object] = {
        "schema": POOL_SCHEMA,
        "milestone": "M095",
        "status": "frozen",
        "construction": "exhaustive Cartesian product; no draw, salt, exclusion or reroll",
        "experimenter_blindness_claimed": False,
        "lineage_reachability_claimed": False,
        "development_world_excluded": True,
        "structures": structures,
        "arrangements": arrangements,
        "entries": entries,
        "population_size": len(entries),
        "preflight_boundary": (
            "S0 construction, measured demand, absence of renderers and exhaustive B-from-S0 "
            "control only; the chain and enabling verdict are forbidden before freeze"
        ),
    }
    pool["pool_digest"] = digest(pool)
    return pool


def load_pool(path: Path = OUTPUT) -> dict[str, object]:
    pool = json.loads(path.read_text(encoding="utf-8"))
    recorded = pool.pop("pool_digest", None)
    recomputed = digest(pool)
    pool["pool_digest"] = recorded
    if recorded != recomputed:
        raise ValueError(f"pool digest mismatch: recorded {recorded}, recomputed {recomputed}")
    return pool


def structure_for(pool: dict[str, object], structure_id: str) -> dict[str, object]:
    return next(
        item for item in pool["structures"]
        if isinstance(item, dict) and item.get("id") == structure_id
    )


def _mapping_lines(
    variable: str,
    fields: list[dict[str, str]],
    rendered: list[str],
    *,
    indent: str,
) -> list[str]:
    by_name = {item["field"]: item for item in fields}
    lines = []
    for name in rendered:
        field = by_name[name]
        key = field.get("key", name)
        value = f"{variable}.{name}"
        if "list[" in field["annotation"]:
            value = f"list({value})"
        lines.append(f'{indent}"{key}": {value},')
    return lines


def build_world(root: Path, pool: dict[str, object], entry: dict[str, object]) -> Path:
    """Materialise one S0 exactly from its committed structural recipe."""

    spec = structure_for(pool, str(entry["structure"]))
    inner = str(spec["inner_class"])
    outer = str(spec["outer_class"])
    nested = str(spec["nested_field"])
    inner_fields = list(spec["inner_fields"])
    outer_fields = list(spec["outer_fields"])

    class_lines = [
        '"""Qualification world; no class renders itself at S0."""',
        "",
        "from dataclasses import dataclass",
        "",
        "",
        "@dataclass(frozen=True)",
        f"class {inner}:",
    ]
    class_lines += [f"    {item['field']}: {item['annotation']}" for item in inner_fields]
    class_lines += ["", "", "@dataclass(frozen=True)", f"class {outer}:"]
    class_lines += [f"    {item['field']}: {item['annotation']}" for item in outer_fields]
    class_lines.append(f"    {nested}: {inner}")

    package = root / "pkg"
    package.mkdir(parents=True, exist_ok=True)
    (package / "__init__.py").write_text("", encoding="utf-8", newline="\n")
    (root / world.COMPONENT).write_text(
        "\n".join(class_lines) + "\n", encoding="utf-8", newline="\n"
    )

    inner_mapping = _mapping_lines(
        "value", inner_fields, list(spec["inner_rendered"]), indent="        "
    )
    for index in range(int(entry["inner_call_sites"])):
        source = [
            f"from pkg.values import {inner}",
            "",
            "",
            f"def emit_{index}(value: {inner}) -> dict:",
            "    return {",
            *inner_mapping,
            "    }",
            "",
        ]
        (root / f"inner_caller_{index}.py").write_text(
            "\n".join(source), encoding="utf-8", newline="\n"
        )

    outer_mapping = _mapping_lines(
        "value", outer_fields, list(spec["outer_rendered"]), indent="        "
    )
    nested_mapping = _mapping_lines(
        f"value.{nested}", inner_fields, list(spec["inner_rendered"]), indent="            "
    )
    nested_key = nested
    for index in range(int(entry["outer_call_sites"])):
        source = [
            f"from pkg.values import {outer}",
            "",
            "",
            f"def report_{index}(value: {outer}) -> dict:",
            "    return {",
            *outer_mapping,
            f'        "{nested_key}": {{',
            *nested_mapping,
            "        },",
            "    }",
            "",
        ]
        (root / f"outer_caller_{index}.py").write_text(
            "\n".join(source), encoding="utf-8", newline="\n"
        )
    return root


def preflight_entry(pool: dict[str, object], entry: dict[str, object], root: Path) -> dict:
    """Verify construction and S0 controls, without ever running the chain."""

    build_world(root, pool, entry)
    files = sorted(root.rglob("*.py"))
    for path in files:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    facts = world.WorldFacts.of(root)
    diagnosis = chain.measure(root)
    nested = next((item for item in diagnosis.unmet if item.capability == chain.NESTED), None)
    control = chain.control_from_s0(root) if nested is not None else None
    inner_plain = [
        item for item in diagnosis.unmet
        if item.target == facts.inner_class
        and item.capability == "render_value_object_as_mapping"
    ]
    failures = []
    if facts.inner_call_sites != entry["inner_call_sites"]:
        failures.append("measured inner demand differs from the recipe")
    if facts.outer_call_sites != entry["outer_call_sites"]:
        failures.append("measured outer demand differs from the recipe")
    if not facts.nothing_renders_itself_at_s0:
        failures.append("a class already renders itself at S0")
    if nested is None:
        failures.append("the nested requirement is absent at S0")
    if int(entry["inner_call_sites"]) > 0 and not inner_plain:
        failures.append("the positive world exposes no inner insufficiency")
    if int(entry["inner_call_sites"]) == 0 and inner_plain:
        failures.append("the negative world unexpectedly exposes an inner insufficiency")
    if control is not None and control.reached:
        failures.append("B is reachable from S0")
    if (control is not None and int(entry["inner_call_sites"]) > 0
            and not control.nested_offered):
        failures.append("the demand-bearing S0 control was not offered the nested operation")
    if (control is not None and int(entry["inner_call_sites"]) == 0
            and control.nested_offered):
        failures.append("the demand-free world unexpectedly manufactured a nested operation")
    return {
        "entry": entry["id"],
        "files_parsed": len(files),
        "facts": facts.to_dict(),
        "nested_requirement_present": nested is not None,
        "inner_requirement_present": bool(inner_plain),
        "control_b_from_s0_reached": control.reached if control else None,
        "control_examined": control.examined if control else None,
        "control_nested_operations_offered": list(control.nested_offered) if control else [],
        "passed": not failures,
        "failures": failures,
    }


def audit(pool: dict[str, object]) -> dict[str, object]:
    rows = []
    with tempfile.TemporaryDirectory(prefix="m095-pool-audit-") as temporary:
        base = Path(temporary)
        for entry in pool["entries"]:
            rows.append(preflight_entry(pool, entry, base / str(entry["id"])))
    return {
        "schema": "m095-qualification-pool-audit-v1",
        "pool_digest": pool["pool_digest"],
        "entries_checked": len(rows),
        "chain_was_run": False,
        "passed": bool(rows) and all(row["passed"] for row in rows),
        "entries": rows,
    }


def main() -> int:
    pool = build_pool()
    report = audit(pool)
    print(json.dumps({"pool": pool, "audit": report}, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
