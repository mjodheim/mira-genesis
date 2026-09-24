"""Structural regressions for the prospective V24 L5 apparatus.

These tests deliberately do not execute the four scientific meta-search arms.
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V23 = ROOT / "experiment" / "rsi_v23"
V24 = ROOT / "experiment" / "rsi_v24"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


family = _load("test_v24_family", V23 / "l5_policy_family.py")
bridge = _load("test_v24_bridge", V24 / "semantic_quality_bridge.py")
search = _load("test_v24_search", V24 / "l5_meta_search.py")


def test_v24_root_remains_exact_frozen_g2():
    source = family.root_source()
    assert hashlib.sha256(source.encode()).hexdigest() == family.ROOT_SHA256


def test_v24_semantic_bridge_matches_exact_g2_threshold_regions():
    rows = bridge.bridged_universe()
    root_utility = bridge.root_utility()
    assert rows

    for row in rows:
        utility = tuple(row["development_utility"])
        quality = int(row["quality_milli"])
        if utility < root_utility:
            assert 0 <= quality <= bridge.PROMISING_MAX
        elif utility == root_utility:
            assert quality == bridge.NEUTRAL_QUALITY
        else:
            assert bridge.STRONG_THRESHOLD <= quality <= bridge.MAX_QUALITY


def test_v24_semantic_bridge_preserves_strict_order_inside_each_side_of_root():
    mapping = bridge.utility_quality_map()
    root = bridge.root_utility()

    worse = sorted(value for value in mapping if value < root)
    better = sorted(value for value in mapping if value > root)

    assert all(mapping[a] < mapping[b] for a, b in zip(worse, worse[1:]))
    assert all(mapping[a] < mapping[b] for a, b in zip(better, better[1:]))


def test_v24_exact_g2_strong_stop_boundary_is_not_rewritten():
    g2 = family.root_source()
    assert "if best >= 780:" in g2
    assert bridge.STRONG_THRESHOLD == 780
    assert bridge.PROMISING_MAX == 710
    assert bridge.NEUTRAL_QUALITY == 750


def test_v24_ablation_is_exact_g2_except_for_the_l4_validated_early_stop():
    g2 = family.root_source()
    ablated = search.g2_ablation_source()
    block = """    if best >= 780:
        return []

"""
    assert ablated == g2.replace(block, "")


def test_v24_equal_external_meta_budgets_remain_v23_sized():
    assert search.META_REQUEST_BUDGET == 9
    assert search.META_ROUND_BUDGET == 8
    assert search.META_MAX_PARALLELISM == 2
    assert search.META_MUTATION_DEPTH == 2
