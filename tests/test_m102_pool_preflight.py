from __future__ import annotations

import ast
from pathlib import Path

from scripts import author_m102_qualification_pool as author


ROOT = Path(__file__).resolve().parents[1]


def test_committed_m102_pool_matches_source_only_authorship() -> None:
    committed = author.load_pool()
    rebuilt = author.build_pool(status="frozen")
    assert committed == rebuilt
    report = author.audit(committed)
    assert report["passed"] is True
    assert report["entries_checked"] == 13
    assert report["raw_sqlite_models_inspected"] == 64
    assert report["scientific_verdict"] is False
    assert report["acquisition_was_run"] is False
    assert report["hidden_success_was_scored"] is False


def test_pool_author_has_no_m102_mechanism_import_or_execution_call() -> None:
    path = ROOT / "scripts/author_m102_qualification_pool.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not imported & {
        "metamorphosis",
        "m102_runtime",
        "m102_executor",
        "check_m102_definitions",
        "run_m102_qualification",
    }
    forbidden_calls = {
        "acquire_policy",
        "register_events",
        "acquire_c",
        "execute_c_world",
        "execute_record",
        "execute_sqlite",
        "mutate_policy_to_flat",
        "mutate_c_duplicate_effect",
    }
    observed_calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not observed_calls & forbidden_calls


def test_pool_contains_no_development_descriptor_digest() -> None:
    pool = author.load_pool()
    observed: set[str] = set()
    for entry in pool["entries"]:
        world = entry["world"]
        for event in world.get("events", []) + world.get("incoming_events", []):
            observed.add(author.digest(event["descriptor"]))
    assert not observed & author.DEVELOPMENT_DESCRIPTOR_DIGESTS
