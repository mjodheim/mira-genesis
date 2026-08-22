"""M096's qualification population is finite, fresh and preflight-only before freeze."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from scripts.author_m096_qualification_pool import (
    OUTPUT,
    audit,
    build_pool,
    digest,
    load_pool,
)

ROOT = Path(__file__).resolve().parents[1]


def test_committed_pool_is_the_frozen_authored_cartesian_product() -> None:
    pool = load_pool()
    assert pool == build_pool(status="frozen")
    assert pool["population_size"] == 12
    assert len(pool["structures"]) == 4
    assert len(pool["arrangements"]) == 3
    assert {
        (entry["structure"], entry["arrangement"]) for entry in pool["entries"]
    } == {
        (structure["id"], arrangement["id"])
        for structure in pool["structures"]
        for arrangement in pool["arrangements"]
    }


def test_pool_and_every_entry_are_content_addressed() -> None:
    pool = load_pool()
    assert pool["pool_digest"] == digest(
        {key: value for key, value in pool.items() if key != "pool_digest"}
    )
    for entry in pool["entries"]:
        assert entry["entry_digest"] == digest(
            {key: value for key, value in entry.items() if key != "entry_digest"}
        )


def test_every_world_passes_s0_preflight_without_running_the_chain() -> None:
    report = audit(load_pool())
    assert report["chain_was_run"] is False
    assert report["entries_checked"] == 12
    assert report["passed"] is True
    assert all(row["control_b_from_s0_reached"] is False for row in report["entries"])


def test_preflight_source_cannot_call_either_chain_runner() -> None:
    path = ROOT / "scripts" / "author_m096_qualification_pool.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "run" not in called
    assert "run_existing" not in called


def test_m096_mechanism_does_not_import_or_name_qualification_material() -> None:
    path = ROOT / "metamorphosis" / "m096_contracts.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name for alias in node.names]
            if isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
            assert all("qualification" not in name.lower() for name in names)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert "QUALIFICATION_POOL" not in node.value


def test_pool_is_portable_json_and_contains_no_result_fields() -> None:
    raw = OUTPUT.read_bytes()
    assert b"\r\n" not in raw
    pool = json.loads(raw)
    forbidden = {"enabling_demonstrated", "a_reached", "b_reached", "verdict"}
    assert forbidden.isdisjoint(pool)
    assert all(forbidden.isdisjoint(entry) for entry in pool["entries"])
