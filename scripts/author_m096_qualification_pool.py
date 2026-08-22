"""Author and preflight M096's fresh structural qualification population.

The full M096 chain is deliberately absent from this module.  Before freeze it may
only construct S0, parse it, measure its demands and exhaust B-from-S0.  The four
structures below were not members of M095's observed population; all twelve Cartesian
members must run after freeze, with no draw, exclusion or reroll.
"""

from __future__ import annotations

import ast
import hashlib
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

from metamorphosis import m095_chain
from metamorphosis import m095_world as world
from metamorphosis import m096_contracts
from scripts.author_m095_qualification_pool import build_world

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "experiments" / "M096" / "QUALIFICATION_POOL.json"
POOL_SCHEMA = "m096-qualification-pool-v1"


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
        id="aliased_partial_contract",
        inner_class="Locale",
        outer_class="Dispatch",
        nested_field="locale",
        inner_fields=(
            ("primary", "str", "left"),
            ("secondary", "str", "right"),
            ("region", "str", "region"),
        ),
        outer_fields=(("dispatch_id", "str"), ("priority", "int")),
        inner_rendered=("primary", "secondary"),
        outer_rendered=("dispatch_id",),
        axes=(
            "re-keyed inner fields",
            "declared inner field omitted from the contract",
            "declared outer field omitted from the nested capability",
        ),
    ),
    Structure(
        id="sparse_text_contract",
        inner_class="Palette",
        outer_class="Presentation",
        nested_field="palette",
        inner_fields=(
            ("foreground", "str", "ink"),
            ("background", "str", "paper"),
            ("accent", "str", "accent"),
            ("locale", "str", "locale"),
            ("theme", "str", "theme"),
        ),
        outer_fields=(("title", "str"), ("edition", "str")),
        inner_rendered=("foreground", "background"),
        outer_rendered=("title", "edition"),
        axes=(
            "two demanded bindings among five declared fields",
            "two re-keyed string bindings",
            "three unrelated fields omitted",
        ),
    ),
    Structure(
        id="mixed_scalar_subset",
        inner_class="Telemetry",
        outer_class="Transmission",
        nested_field="telemetry",
        inner_fields=(
            ("temperature", "float", "temp_c"),
            ("sequence", "int", "seq"),
            ("healthy", "bool", "ok"),
            ("note", "str", "note"),
        ),
        outer_fields=(("channel", "str"), ("retry", "bool")),
        inner_rendered=("temperature", "sequence", "healthy"),
        outer_rendered=("channel",),
        axes=(
            "four declared inner fields",
            "three mixed scalar bindings",
            "all demanded keys differ from their fields",
        ),
    ),
    Structure(
        id="complete_minimal_contract",
        inner_class="Boundary",
        outer_class="Region",
        nested_field="boundary",
        inner_fields=(("start", "int", "start"), ("stop", "int", "stop")),
        outer_fields=(("region_name", "str"),),
        inner_rendered=("start", "stop"),
        outer_rendered=("region_name",),
        axes=(
            "complete rather than subset inner contract",
            "identity key bindings",
            "integer boundary values",
        ),
    ),
)


ARRANGEMENTS = (
    {
        "id": "ranking_unaided",
        "inner_call_sites": 4,
        "outer_call_sites": 2,
        "expected_relation": True,
        "expected_descent": False,
    },
    {
        "id": "failed_search_descent",
        "inner_call_sites": 1,
        "outer_call_sites": 4,
        "expected_relation": True,
        "expected_descent": True,
    },
    {
        "id": "no_visible_enabler",
        "inner_call_sites": 0,
        "outer_call_sites": 3,
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


def build_pool(*, status: str = "candidate") -> dict[str, object]:
    structures = [_structure_dict(spec) for spec in STRUCTURES]
    arrangements = [dict(item) for item in ARRANGEMENTS]
    entries: list[dict[str, object]] = []
    for structure in structures:
        for arrangement in arrangements:
            entry: dict[str, object] = {
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
        "milestone": "M096",
        "status": status,
        "construction": "exhaustive Cartesian product; no draw, salt, exclusion or reroll",
        "experimenter_blindness_claimed": False,
        "development_population": "the observed M095 qualification population",
        "qualification_population_was_not_run_during_development": True,
        "structures": structures,
        "arrangements": arrangements,
        "entries": entries,
        "population_size": len(entries),
        "preflight_boundary": (
            "S0 construction, parsing, measured demand, absence of renderers and exhaustive "
            "B-from-S0 control only; no S0-to-S1 adoption and no enabling verdict before freeze"
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


def preflight_entry(pool: dict[str, object], entry: dict[str, object], root: Path) -> dict:
    build_world(root, pool, entry)
    files = sorted(root.rglob("*.py"))
    for path in files:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    facts = world.WorldFacts.of(root)
    diagnosis = m096_contracts.measure(root)
    nested = next(
        (item for item in diagnosis.unmet if item.capability == m095_chain.NESTED), None
    )
    control = m096_contracts.control_from_s0(root) if nested is not None else None
    inner_plain = [
        item
        for item in diagnosis.unmet
        if item.target == facts.inner_class
        and item.capability == "render_value_object_as_mapping"
    ]
    failures: list[str] = []
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
    if (
        control is not None
        and int(entry["inner_call_sites"]) > 0
        and not control.nested_offered
    ):
        failures.append("the demand-bearing S0 control was not offered the nested operation")
    if (
        control is not None
        and int(entry["inner_call_sites"]) == 0
        and control.nested_offered
    ):
        failures.append("the demand-free world manufactured a nested operation")
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
    rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="m096-pool-audit-") as temporary:
        base = Path(temporary)
        for entry in pool["entries"]:
            rows.append(preflight_entry(pool, entry, base / str(entry["id"])))
    return {
        "schema": "m096-qualification-pool-audit-v1",
        "pool_digest": pool["pool_digest"],
        "entries_checked": len(rows),
        "chain_was_run": False,
        "passed": bool(rows) and all(bool(row["passed"]) for row in rows),
        "entries": rows,
    }


def main() -> int:
    pool = build_pool()
    report = audit(pool)
    print(json.dumps({"pool": pool, "audit": report}, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
