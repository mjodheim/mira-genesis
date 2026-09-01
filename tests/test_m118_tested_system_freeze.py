"""Nothing that can change what a completion means may be left unbound."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from metamorphosis import m118_chronology as chronology
from metamorphosis.m116_chronology import ChronologyError

ROOT = Path(__file__).resolve().parents[1]


def test_the_interpreting_closure_is_fully_bound():
    stock = chronology.inventory(ROOT)
    assert stock["unbound_interpretation_modules"] == []
    assert stock["closure_is_fully_bound"] is True


def test_the_closure_is_computed_from_source_not_asserted():
    """It must reach further than the roots themselves, or it is not a closure."""
    closure = chronology.interpretation_closure(ROOT)
    assert len(closure) > len(chronology.INTERPRETATION_ROOTS)
    assert "metamorphosis/m113_evaluator.py" in closure
    assert "metamorphosis/carrier_host.py" in closure


def test_m118s_own_interpreting_modules_are_roots_and_bound():
    for module in ("metamorphosis/m118_route.py", "metamorphosis/m118_chronology.py"):
        assert module in chronology.INTERPRETATION_ROOTS, module
        assert module in chronology.TESTED_SYSTEM_PATHS, module


def test_every_deliberate_exclusion_carries_a_reason():
    for path, reason in chronology.UNBOUND_BY_DESIGN.items():
        assert isinstance(reason, str) and len(reason) > 20, path


def test_the_readiness_gate_and_freeze_builder_are_excluded_with_reasons():
    for path in ("scripts/audit_m118_readiness.py", "scripts/build_m118_freeze.py"):
        assert path in chronology.UNBOUND_BY_DESIGN, path


def test_a_freeze_refuses_while_anything_is_unbound(monkeypatch):
    monkeypatch.setattr(chronology, "TESTED_SYSTEM_PATHS", ("metamorphosis/m118_route.py",))
    monkeypatch.setattr(chronology, "UNBOUND_BY_DESIGN", {})
    with pytest.raises(ChronologyError, match="leave interpreting modules unbound"):
        chronology.build_freeze(ROOT)


def test_the_freeze_binds_every_tested_system_path():
    record = chronology.build_freeze(ROOT)
    assert set(record["tested_system_digests"]) == set(chronology.TESTED_SYSTEM_PATHS)
    assert record["frozen_before_generation"] is True
    assert record["no_scientific_completion_existed_at_freeze"] is True


def test_the_freeze_validates_against_an_unchanged_tree():
    chronology.validate_freeze(chronology.build_freeze(ROOT), ROOT)


def test_a_changed_tested_system_module_invalidates_the_freeze():
    record = chronology.build_freeze(ROOT)
    target = "metamorphosis/m118_route.py"
    record["tested_system_digests"][target] = "0" * 64
    record["freeze_commitment_sha256"] = chronology.sha256_hex(
        chronology.canonical_bytes(
            {k: v for k, v in record.items() if k != "freeze_commitment_sha256"}))
    with pytest.raises(ChronologyError, match="changed after the freeze"):
        chronology.validate_freeze(record, ROOT)


def test_a_tampered_commitment_is_refused():
    record = chronology.build_freeze(ROOT)
    record["freeze_commitment_sha256"] = "0" * 64
    with pytest.raises(ChronologyError, match="does not match its contents"):
        chronology.validate_freeze(record, ROOT)


def test_every_phase_after_the_generation_rechecks_the_freeze():
    assert chronology.DOWNSTREAM_PHASES == ("admission", "sealing", "reveal", "scoring")
    with pytest.raises(ChronologyError, match="unknown downstream phase"):
        chronology.assert_frozen_system_unchanged(ROOT, phase="whenever")


def test_a_phase_requires_the_freeze_committed_at_head(tmp_path):
    import subprocess
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    with pytest.raises(ChronologyError):
        chronology.assert_frozen_system_unchanged(tmp_path, phase="scoring")
