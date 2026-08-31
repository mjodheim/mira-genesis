"""Chronology and leakage tests: the tested system freezes before any H61 completion exists.

M115 froze the tested system after sealing. That stopped adaptation to carrier *content*, which
stayed sealed, but not adaptation to what the completion implies -- token counts, byte lengths,
carrier counts, refusal counts and a violation location are all correlated with the bank. M116
moves the freeze ahead of the qualifying request, so at the moment a scientific completion first
exists there is nothing left to adapt.

These tests make that chronology mechanical rather than procedural.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from metamorphosis import m116_admission as admission
from metamorphosis import m116_chronology as chronology
from metamorphosis import m116_materialization as materialization
from metamorphosis import m116_telemetry as telemetry

ROOT = Path(__file__).resolve().parents[1]


def _freeze(root: Path, **overrides):
    record = chronology.build_freeze(
        plan_commitment_sha256="a" * 64,
        spec_commitment_sha256="b" * 64,
        request_body_sha256="c" * 64,
        bank_nonce_sha256="d" * 64,
        frozen_at="2026-09-01T00:00:00Z",
        frozen_at_commit="0" * 40,
        root=root,
    )
    record.update(overrides)
    return record


@pytest.fixture()
def tree(tmp_path: Path) -> Path:
    """A minimal git working tree carrying every bound member plus the roots, by copy."""
    import subprocess

    for relative in set(chronology.TESTED_SYSTEM_PATHS) | set(chronology.INTERPRETATION_ROOTS):
        source = ROOT / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    (tmp_path / "experiments" / "M116").mkdir(parents=True, exist_ok=True)
    for command in (["git", "init", "-q"],
                    ["git", "config", "user.name", "Test"],
                    ["git", "config", "user.email", "test@example.invalid"],
                    ["git", "add", "-A"],
                    ["git", "commit", "-q", "-m", "tree"]):
        subprocess.run(command, cwd=tmp_path, check=True, capture_output=True)
    return tmp_path


def _commit_freeze(root: Path, record) -> None:
    """Write the freeze and commit it, as the real chronology requires."""
    import subprocess

    (root / chronology.FREEZE_PATH).write_text(json.dumps(record), encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", "freeze"], cwd=root, check=True,
                   capture_output=True)


# ---------------------------------------------------------------------------------------------
# The delivery gate
# ---------------------------------------------------------------------------------------------

def test_qualifying_delivery_refuses_when_the_freeze_is_absent(tree: Path):
    with pytest.raises(chronology.ChronologyError, match="before the tested system is frozen"):
        chronology.assert_qualifying_delivery_permitted(tree)


def test_qualifying_delivery_is_permitted_once_the_freeze_exists(tree: Path):
    _commit_freeze(tree, _freeze(tree))
    permission = chronology.assert_qualifying_delivery_permitted(tree)
    assert permission["permitted"] is True
    assert permission["freeze_precedes_scientific_generation"] is True
    assert permission["freeze_is_committed_at_head"] is True


def test_an_uncommitted_freeze_does_not_authorize_delivery(tree: Path):
    """A file written moments before the request is not a freeze; a commit is what makes it one."""
    (tree / chronology.FREEZE_PATH).write_text(json.dumps(_freeze(tree)), encoding="utf-8")
    with pytest.raises(chronology.ChronologyError, match="not committed at HEAD"):
        chronology.assert_qualifying_delivery_permitted(tree)


def test_a_freeze_edited_after_being_committed_does_not_authorize_delivery(tree: Path):
    _commit_freeze(tree, _freeze(tree))
    record = _freeze(tree)
    record["frozen_at"] = "2099-01-01T00:00:00Z"
    (tree / chronology.FREEZE_PATH).write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(chronology.ChronologyError, match="differs from the committed one"):
        chronology.assert_qualifying_delivery_permitted(tree)


def test_the_gate_accepts_no_caller_supplied_freeze_record():
    """The runner must not be able to build a freeze and hand it straight to the gate.

    An earlier form took `freeze=`, which let a caller satisfy every digest check by freezing
    moments before generating -- bypassing the chronology the freeze exists to establish.
    """
    import inspect

    parameters = inspect.signature(chronology.assert_qualifying_delivery_permitted).parameters
    assert set(parameters) == {"root"}


def test_qualifying_delivery_refuses_if_a_frozen_member_changed(tree: Path):
    _commit_freeze(tree, _freeze(tree))
    victim = tree / "metamorphosis" / "m113_evaluator.py"
    victim.write_bytes(victim.read_bytes() + b"\n# adapted after the freeze\n")
    with pytest.raises(chronology.ChronologyError, match="changed after it was frozen"):
        chronology.assert_qualifying_delivery_permitted(tree)


def test_qualifying_delivery_refuses_if_the_machinery_under_test_changed(tree: Path):
    """The M107-M111 lineage is the thing being tested; it must not move after the freeze."""
    _commit_freeze(tree, _freeze(tree))
    victim = tree / "metamorphosis" / "m109_runtime.py"
    victim.write_bytes(victim.read_bytes() + b"\n# tuned to the unseen bank\n")
    with pytest.raises(chronology.ChronologyError, match="changed after it was frozen"):
        chronology.assert_qualifying_delivery_permitted(tree)


def test_a_tampered_freeze_commitment_is_refused(tree: Path):
    record = _freeze(tree)
    record["tested_system_digests"]["metamorphosis/carrier_host.py"] = "0" * 64
    with pytest.raises(chronology.ChronologyError, match="commitment digest drifted"):
        chronology.validate_freeze(record, root=tree)


def test_the_freeze_must_cover_the_inventory_exactly(tree: Path):
    record = _freeze(tree)
    del record["tested_system_digests"]["metamorphosis/carrier_host.py"]
    record["freeze_commitment_sha256"] = chronology.freeze_commitment(record)
    with pytest.raises(chronology.ChronologyError, match="does not cover the inventory exactly"):
        chronology.validate_freeze(record, root=tree)


# ---------------------------------------------------------------------------------------------
# Nothing derived from a completion may exist before the freeze
# ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "artifact",
    ["DELIVERY_LEDGER.json", "TELEMETRY.json", "ADMISSION_RECORD.json",
     "GENERATION_RESPONSE.json", "SEALED_BANK.json.gpg", "PUBLIC_BANK_COMMITMENT.json",
     "REVEAL_AUTHORIZATION.json", "RESULT.json"],
)
def test_no_completion_derived_artifact_may_predate_the_freeze(tree: Path, artifact: str):
    (tree / "experiments" / "M116" / artifact).write_text("{}", encoding="utf-8")
    with pytest.raises(chronology.ChronologyError, match="already exist"):
        chronology.build_freeze(
            plan_commitment_sha256="a" * 64, spec_commitment_sha256="b" * 64,
            request_body_sha256="c" * 64, bank_nonce_sha256="d" * 64,
            frozen_at="2026-09-01T00:00:00Z", frozen_at_commit="0" * 40, root=tree,
        )


def test_delivery_is_refused_once_a_completion_derived_artifact_appears(tree: Path):
    _commit_freeze(tree, _freeze(tree))
    (tree / "experiments" / "M116" / "TELEMETRY.json").write_text("{}", encoding="utf-8")
    with pytest.raises(chronology.ChronologyError, match="already exist"):
        chronology.assert_qualifying_delivery_permitted(tree)


def test_the_repository_carries_no_h61_completion_derived_artifact_today():
    for relative in chronology.POST_FREEZE_ONLY_ARTIFACTS:
        assert not (ROOT / relative).exists(), "%s must not exist before H61" % relative


# ---------------------------------------------------------------------------------------------
# The inventory is mechanical, not prose
# ---------------------------------------------------------------------------------------------

def test_every_module_that_can_interpret_a_completion_is_bound():
    assert chronology.unbound_interpretation_modules(ROOT) == []


def test_the_closure_is_computed_from_source_not_declared():
    closure = chronology.interpretation_closure(ROOT)
    # Reached only transitively: nothing names these in the roots list.
    assert "metamorphosis/m109_runtime.py" in closure
    assert "metamorphosis/carrier_host.py" in closure
    assert "metamorphosis/m113_carrier_devkit.py" in closure


def test_an_unbound_interpretation_module_is_reported(monkeypatch):
    trimmed = tuple(p for p in chronology.TESTED_SYSTEM_PATHS
                    if p != "metamorphosis/m113_evaluator.py")
    monkeypatch.setattr(chronology, "TESTED_SYSTEM_PATHS", trimmed)
    assert "metamorphosis/m113_evaluator.py" in chronology.unbound_interpretation_modules(ROOT)


def test_a_freeze_cannot_be_built_while_a_module_is_unbound(tmp_path, monkeypatch):
    trimmed = tuple(p for p in chronology.TESTED_SYSTEM_PATHS
                    if p != "metamorphosis/m113_evaluator.py")
    monkeypatch.setattr(chronology, "TESTED_SYSTEM_PATHS", trimmed)
    with pytest.raises(chronology.ChronologyError, match="not bound"):
        chronology.build_freeze(
            plan_commitment_sha256="a" * 64, spec_commitment_sha256="b" * 64,
            request_body_sha256="c" * 64, bank_nonce_sha256="d" * 64,
            frozen_at="2026-09-01T00:00:00Z", frozen_at_commit="0" * 40, root=ROOT,
        )


def test_the_unbound_by_design_set_is_development_only():
    for relative, reason in chronology.UNBOUND_BY_DESIGN.items():
        assert (ROOT / relative).is_file()
        assert "DEVELOPMENT" in reason or "frozen M115 schema" in reason
        assert relative not in chronology.TESTED_SYSTEM_PATHS


# ---------------------------------------------------------------------------------------------
# Telemetry and admission cannot authorize anything
# ---------------------------------------------------------------------------------------------

def _executed_telemetry(**overrides):
    record = telemetry.extract(
        status=200,
        body={"choices": [{"finish_reason": "stop", "message": {"content": "x"}}],
              "usage": {"completion_tokens": 41203,
                        "completion_tokens_details": {"reasoning_tokens": 0}},
              "model": "deepseek/deepseek-v4-flash-0731", "provider": "Alibaba"},
        response_bytes=1000, headers={"x-generation-id": "gen-abc"},
        identity_attestation={"router_attestation": {"checks": {
            "selected_checkpoint_exact": True, "direct_strategy": True,
            "no_fallback_attested": True, "one_selected_endpoint": True,
            "one_router_attempt": True, "no_pipeline_intervention": True}}},
        requested_model="deepseek/deepseek-v4-flash-0731", requested_provider="Alibaba")
    record.update(overrides)
    return record


def test_telemetry_cannot_authorize_a_system_modification():
    """Telemetry is data. The freeze path cannot consult it, so it can grant no permission.

    The chronology module names the telemetry and admission modules as bound members of the
    inventory -- that is the point of the inventory -- but it must not *import* them, because a
    freeze that could read a completion-derived value is a freeze that could be argued with.
    """
    import ast

    tree = ast.parse((ROOT / "metamorphosis" / "m116_chronology.py").read_text("utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
            imported.update("%s.%s" % (node.module, a.name) for a in node.names)
    assert not any("m116_telemetry" in name for name in imported)
    assert not any("m116_admission" in name for name in imported)
    assert not any("m116_materialization" in name for name in imported)

    # And no freeze entry point takes telemetry, admission or a completion as an argument.
    for function in (chronology.validate_freeze, chronology.build_freeze,
                     chronology.assert_qualifying_delivery_permitted):
        names = set(function.__code__.co_varnames)
        assert not (names & {"telemetry", "admission", "completion", "record_telemetry"})


def test_admission_cannot_authorize_a_redraw():
    decision = materialization.decide(_executed_telemetry(), None)
    assert decision["content_dependent_redraw_permitted"] is False
    assert decision["physical_retry_permitted"] is False


def test_the_content_correlated_quantities_exist_only_after_the_freeze(tree: Path):
    """Every quantity the owner flagged is produced by code that runs after step 5."""
    _commit_freeze(tree, _freeze(tree))
    chronology.assert_qualifying_delivery_permitted(tree)  # step 5 complete, step 6 not yet

    flagged = ("completion_tokens", "content_bytes", "response_bytes", "finish_reason")
    for name in flagged:
        assert name in telemetry.ALLOWED_FIELDS
    for name in ("records_emitted", "carriers_enveloped", "carriers_accepted",
                 "carriers_refused", "distinct_structural_signatures",
                 "violation_location", "violation_keyword"):
        assert name in admission.ADMISSION_FIELDS

    # None of them appears in any artifact that may exist before the freeze.
    freeze_text = (tree / chronology.FREEZE_PATH).read_text("utf-8")
    for name in flagged:
        assert name not in freeze_text
