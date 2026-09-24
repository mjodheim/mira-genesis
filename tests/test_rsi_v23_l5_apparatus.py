"""Structural regressions for the prospective V23 L5 apparatus.

These tests deliberately do not execute the four scientific meta-search arms.
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V23 = ROOT / "experiment" / "rsi_v23"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


family = _load("test_v23_l5_family", V23 / "l5_policy_family.py")
dev = _load("test_v23_l5_dev", V23 / "l5_meta_development.py")
search = _load("test_v23_l5_search", V23 / "l5_meta_search.py")
holdout_gen = _load("test_v23_l5_holdout_gen", V23 / "holdout" / "candidate_generator.py")
run_task = _load("test_v23_l5_run_task", V23 / "holdout" / "run_task.py")


def test_l5_root_is_exact_frozen_g2():
    source = family.root_source()
    assert hashlib.sha256(source.encode()).hexdigest() == family.ROOT_SHA256
    assert family.render_source(family.ROOT_PARAMS) == source


def test_l5_policy_family_is_finite_content_addressed_and_depth_bounded():
    rows = family.universe(2)
    assert rows
    assert rows[0]["mutation_depth"] == 0
    assert max(row["mutation_depth"] for row in rows) <= 2
    assert len({row["params_digest"] for row in rows}) == len(rows)
    assert len({row["source_sha256"] for row in rows}) == len(rows)
    assert family.params_digest(family.ROOT_PARAMS) in {
        row["params_digest"] for row in rows
    }


def test_l5_development_population_is_the_frozen_factorial():
    episodes = dev.development_episodes()
    assert len(episodes) == 12
    assert {row["q1"] for row in episodes} == {650, 730, 810}
    assert {row["gain_location"] for row in episodes} == {"deep", "root"}
    assert {row["profile_generation"] for row in episodes} == {0, 1}
    assert len({row["episode_id"] for row in episodes}) == 12


def test_l5_equal_external_meta_budgets_are_fixed():
    assert search.META_REQUEST_BUDGET == 9
    assert search.META_ROUND_BUDGET == 8
    assert search.META_MAX_PARALLELISM == 2
    assert search.META_MUTATION_DEPTH == 2


def test_l5_ablation_is_exact_g2_except_for_the_l4_validated_early_stop():
    g2 = family.root_source()
    ablated = search.g2_ablation_source()
    assert ablated != g2
    assert "if best >= 780:" in g2
    assert "if best >= 780:" not in ablated
    assert "return (10, 6, 3, 5, 5, 4, 8, 1, 8, 3)" in ablated
    block = """    if best >= 780:
        return []

"""
    expected = g2.replace(block, "")
    assert ablated == expected


def test_l5_holdout_generator_has_four_two_locus_tasks_and_no_reserved_evaluator_dependency():
    assert set(holdout_gen.TASKS) == {
        "brewtrack-brewmath-precision",
        "brewtrack-recipemath-units-water",
        "brewstead-effect-rounding",
        "brewstead-brew-lifecycle-thresholds",
    }
    for spec in holdout_gen.TASKS.values():
        assert len(spec["loci"]) == 2
        assert spec["path"]
    assert "evaluator" not in holdout_gen.manifest()["schema"].lower()


def test_l5_holdout_external_caps_match_preregistration():
    assert run_task.MAX_REQUESTS == 9
    assert run_task.MAX_ROUNDS == 8
    assert run_task.MAX_PARALLELISM == 2
