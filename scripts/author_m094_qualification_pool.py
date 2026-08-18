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
import hashlib
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
#: reproducible by anyone from the committed pool.
CASE_SEED = "m094-qualification-hidden-cases-v1"


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


def _hidden_cases(component: str, class_name: str, rendering) -> list[dict]:
    """Field assignments the repair must render correctly, one per case."""

    annotations = _field_annotations(component, class_name)
    cases: list[dict] = []
    for index in range(HIDDEN_CASES_PER_REQUIREMENT):
        assignment = {
            field: _value_for(annotations.get(field, "str"), field, index)
            for _key, field, _wrapper in rendering
        }
        cases.append({"index": index, "fields": assignment})
    return cases


def build_pool() -> dict:
    components = _candidate_components()
    result = diagnose(REPO_ROOT, components)

    entries = []
    for insufficiency in result.unmet:
        assert insufficiency.component_path not in DEVELOPMENT_COMPONENTS, (
            "a development component leaked into the qualification pool: "
            + insufficiency.component_path
        )
        rendering = decode_rendering(insufficiency.detail)
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
            "hidden_cases": _hidden_cases(
                insufficiency.component_path, insufficiency.class_name, rendering
            ),
        }
        entry["entry_digest"] = _digest(
            {k: v for k, v in entry.items() if k != "entry_digest"}
        )
        entries.append(entry)

    entries.sort(key=lambda e: e["entry_digest"])

    pool = {
        "schema": "m094-qualification-pool-v1",
        "milestone": "M094",
        "authored_at_freeze": True,
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
