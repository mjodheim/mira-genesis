"""M095's qualification population is finite, reproducible and unreachable by the lineage."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from scripts.author_m095_qualification_pool import (
    OUTPUT,
    audit,
    build_pool,
    digest,
    load_pool,
)

ROOT = Path(__file__).resolve().parents[1]


def test_the_committed_pool_is_the_authored_cartesian_product() -> None:
    pool = load_pool()
    assert pool == build_pool()
    assert pool["population_size"] == 9
    assert len(pool["structures"]) == 3
    assert len(pool["arrangements"]) == 3
    pairs = {(entry["structure"], entry["arrangement"]) for entry in pool["entries"]}
    assert pairs == {
        (structure["id"], arrangement["id"])
        for structure in pool["structures"]
        for arrangement in pool["arrangements"]
    }


def test_every_entry_and_the_pool_are_content_addressed() -> None:
    pool = load_pool()
    assert pool["pool_digest"] == digest(
        {key: value for key, value in pool.items() if key != "pool_digest"}
    )
    for entry in pool["entries"]:
        assert entry["entry_digest"] == digest(
            {key: value for key, value in entry.items() if key != "entry_digest"}
        )


def test_every_world_passes_the_s0_preflight_without_running_the_chain() -> None:
    report = audit(load_pool())
    assert report["chain_was_run"] is False
    assert report["entries_checked"] == 9
    assert report["passed"] is True
    assert all(row["control_b_from_s0_reached"] is False for row in report["entries"])


def test_the_preflight_code_cannot_call_the_chain_runner() -> None:
    path = ROOT / "scripts" / "author_m095_qualification_pool.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "run_existing" not in called
    # ``arms.run`` would also acquire a development result before the freeze.
    assert not any(
        isinstance(node, ast.ImportFrom) and node.module == "metamorphosis.m095_arms"
        for node in ast.walk(tree)
    )


def test_the_lineage_cannot_reach_the_qualification_population() -> None:
    forbidden = ("QUALIFICATION_POOL", "qualification_pool")
    for path in sorted((ROOT / "metamorphosis").glob("m095_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [alias.name for alias in node.names]
                if isinstance(node, ast.ImportFrom) and node.module:
                    names.append(node.module)
                assert all("qualification" not in name.lower() for name in names)
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert all(item not in node.value for item in forbidden)


def test_pool_bytes_are_portable_json() -> None:
    raw = OUTPUT.read_bytes()
    assert b"\r\n" not in raw
    json.loads(raw)
