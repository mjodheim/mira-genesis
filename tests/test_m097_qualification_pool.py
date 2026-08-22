from __future__ import annotations

import ast
import json
from pathlib import Path

from scripts.author_m097_qualification_pool import (
    OUTPUT,
    audit,
    build_pool,
    digest,
    load_pool,
)

ROOT = Path(__file__).resolve().parents[1]


def test_committed_pool_is_all_four_frozen_authored_worlds() -> None:
    pool = load_pool()
    assert pool == build_pool(status="frozen")
    assert pool["population_size"] == 4
    assert len(pool["entries"]) == 4
    assert len({entry["id"] for entry in pool["entries"]}) == 4


def test_pool_and_entries_are_content_addressed() -> None:
    pool = load_pool()
    assert pool["pool_digest"] == digest(
        {key: value for key, value in pool.items() if key != "pool_digest"}
    )
    for entry in pool["entries"]:
        assert entry["entry_digest"] == digest(
            {key: value for key, value in entry.items() if key != "entry_digest"}
        )


def test_preflight_recovers_every_demand_without_acquiring_or_searching() -> None:
    report = audit(load_pool())
    assert report["passed"] is True
    assert report["entries_checked"] == 4
    assert report["acquisition_was_run"] is False
    assert report["extended_search_was_run"] is False


def test_pool_author_cannot_call_acquisition_registration_or_search() -> None:
    path = ROOT / "scripts" / "author_m097_qualification_pool.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden = {"acquire", "register", "search", "confirm_search", "run_experiment"}
    called = {
        node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, (ast.Attribute, ast.Name))
    }
    assert forbidden.isdisjoint(called)


def test_mechanism_and_validator_cannot_reach_qualification_pool() -> None:
    for name in (
        "m097_language.py", "m097_acquisition.py", "m097_validator.py", "m097_execution.py"
    ):
        source = (ROOT / "metamorphosis" / name).read_text(encoding="utf-8")
        assert "QUALIFICATION_POOL" not in source
        assert "author_m097_qualification_pool" not in source


def test_pool_is_portable_result_free_json() -> None:
    raw = OUTPUT.read_bytes()
    assert b"\r\n" not in raw
    value = json.loads(raw)
    forbidden = {"adopted", "execution_confirmed", "verdict", "extension"}
    assert forbidden.isdisjoint(value)
    assert all(forbidden.isdisjoint(entry) for entry in value["entries"])
