"""The qualification pool exists at the freeze, and the lineage cannot reach it.

The protocol commits to a pool of candidate requirements existing when it is
frozen. These checks hold that commitment to its word: the pool is present, every
entry lies outside the development set, the draw is a deterministic function of a
digest that does not exist until adoption, and no module the lineage runs reads
any of it.

Experimenter blindness is not claimed and is not tested for. What is tested is
reachability, which is the claim actually made.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from author_m094_qualification_pool import (
    DEVELOPMENT_COMPONENTS,
    HIDDEN_CASES_PER_REQUIREMENT,
    OUTPUT,
    _canonical_json,
    _digest,
    draw,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def pool() -> dict:
    return json.loads(OUTPUT.read_text(encoding="utf-8"))


# ── The pool exists, and says what it is ─────────────────────────────


def test_the_pool_exists_and_is_committed(pool: dict) -> None:
    assert OUTPUT.exists(), "the protocol commits to a pool existing at the freeze"
    assert pool["schema"] == "m094-qualification-pool-v1"
    assert pool["authored_at_freeze"] is True
    assert pool["entries"], "an empty pool would qualify nothing"


def test_the_pool_digest_matches_its_contents(pool: dict) -> None:
    recomputed = _digest({k: v for k, v in pool.items() if k != "pool_digest"})
    assert pool["pool_digest"] == recomputed


def test_the_pool_is_stored_byte_exact() -> None:
    raw = OUTPUT.read_bytes()
    assert b"\r\n" not in raw, "a digest-bearing artifact must not carry CRLF"
    json.loads(raw)


# ── Cross-component: nothing from the development set ────────────────


def test_no_entry_comes_from_the_development_set(pool: dict) -> None:
    """A mechanism specialised to the component it grew on must fail here."""

    for entry in pool["entries"]:
        assert entry["component"] not in DEVELOPMENT_COMPONENTS, entry["component"]


def test_the_pool_spans_more_than_one_component(pool: dict) -> None:
    components = {entry["component"] for entry in pool["entries"]}
    assert len(components) >= 2, "a single-component pool cannot draw cross-component"


def test_every_entry_carries_a_requirement_and_hidden_cases(pool: dict) -> None:
    for entry in pool["entries"]:
        assert entry["requirement"], entry["class"]
        assert len(entry["hidden_cases"]) == HIDDEN_CASES_PER_REQUIREMENT
        fields = {item["field"] for item in entry["requirement"]}
        for case in entry["hidden_cases"]:
            assert set(case["fields"]) == fields, "a case must assign exactly the fields read"


def test_entry_digests_are_unique_and_recomputable(pool: dict) -> None:
    digests = [entry["entry_digest"] for entry in pool["entries"]]
    assert len(digests) == len(set(digests))

    for entry in pool["entries"]:
        recomputed = _digest({k: v for k, v in entry.items() if k != "entry_digest"})
        assert entry["entry_digest"] == recomputed


# ── The draw cannot be known at the freeze ───────────────────────────


def test_the_draw_is_deterministic_in_the_mechanism_digest(pool: dict) -> None:
    first = draw(pool, "a" * 64)
    again = draw(pool, "a" * 64)
    assert [e["entry_digest"] for e in first] == [e["entry_digest"] for e in again]


def test_a_different_mechanism_draws_a_different_requirement(pool: dict) -> None:
    """The draw depends on a digest that does not exist until adoption."""

    drawn = {
        digest: tuple(e["entry_digest"] for e in draw(pool, digest))
        for digest in ("a" * 64, "b" * 64, "c" * 64, "d" * 64)
    }
    assert len(set(drawn.values())) > 1, "the draw ignores the mechanism digest"


def test_the_draw_is_cross_component(pool: dict) -> None:
    for digest in ("a" * 64, "b" * 64, "c" * 64):
        drawn = draw(pool, digest)
        assert len(drawn) == pool["entries_drawn_per_qualification"]
        assert len({e["component"] for e in drawn}) == len(drawn)


# ── The lineage cannot reach any of it ───────────────────────────────


def test_no_module_the_lineage_runs_reads_the_pool() -> None:
    """The isolation claim, checked rather than promised.

    If a diagnosis or synthesis module could read the pool, the qualification
    would be development data wearing a held-out label.
    """

    modules = sorted((REPO_ROOT / "metamorphosis").glob("m094_*.py"))
    assert modules, "no M094 modules found to check"

    forbidden = ("QUALIFICATION_POOL", "qualification_pool", "experiments/M094")

    for module_path in modules:
        source = module_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node, clean=False)
                if doc is not None:
                    docstrings.add(doc)

        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value in docstrings:
                    continue
                for needle in forbidden:
                    assert needle not in node.value, (
                        module_path.name + " references the qualification pool: " + node.value
                    )

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names]
                if isinstance(node, ast.ImportFrom) and node.module:
                    names.append(node.module)
                for name in names:
                    assert "qualification" not in name.lower(), (
                        module_path.name + " imports " + name
                    )


def test_the_pool_lives_outside_the_lineages_package() -> None:
    assert OUTPUT.parent.name == "M094"
    assert OUTPUT.parent.parent.name == "experiments"
