"""M107 interpreter-extension tests.

The phase check is bound to the artefacts on disk from the start: M105's equivalent test asserted a
pre-result invariant unconditionally and turned both CI jobs red the moment its result was sealed.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from metamorphosis import m107_runtime as runtime
from scripts import audit_m107_boundaries
from scripts import author_m107_demands as author
from scripts import check_m107_result as checker
from scripts import run_m107_qualification as qualification

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "M107"
_PHASE_CHECK = "canonical_evidence_absent_before_attempt"


def _canonical_evidence_exists() -> bool:
    return (EXPERIMENT / "RESULT.json").exists() or (EXPERIMENT / "CHECK_REPORT.json").exists()


def test_the_substrate_is_genuinely_incomplete() -> None:
    base = runtime.initial_operators()
    assert sorted(item["name"] for item in base) == ["AND", "OR"]
    image = runtime.complete_image(base)
    assert len(image) == 4
    # Stable at the closure fixed point: the bound records the closure, not a search budget.
    assert len(runtime.complete_image(base, 13)) == 4


def test_non_monotone_targets_are_excluded_by_a_lemma_not_a_budget() -> None:
    base = runtime.initial_operators()
    for target in (author.TARGET_PRIMARY, author.TARGET_SECOND):
        certificate = runtime.insufficiency_certificate(base, tuple(target))
        assert certificate["confirmed"] is True
        assert certificate["target_in_image"] is False
        assert certificate["excluded_by_monotonicity_lemma"] is True
        assert certificate["budget_independent"] is True


def test_the_interpreter_holds_no_operator_semantics() -> None:
    """An expression naming an operator absent from the state must not evaluate."""
    base = runtime.operator_map(runtime.initial_operators())
    node = runtime.apply_node("ABSENT", [runtime.signal_node(0)])
    try:
        runtime.execute_expression(base, node, (True, False))
    except ValueError as error:
        assert "not in the state table" in str(error)
    else:  # pragma: no cover - the interpreter must never invent semantics
        raise AssertionError("M107 interpreter evaluated an operator it does not hold")


def test_one_demand_underdetermines_and_two_determine_the_extension() -> None:
    demands = json.loads((EXPERIMENT / "DEMANDS.json").read_text("ascii"))
    s0 = runtime.create_state()

    single = runtime.acquire_operator(s0, [demands["primary"]], register_result=False)
    assert single["confirmed"] is False
    assert single["reason"] == "extension_underdetermined_by_observations"
    assert single["surviving_reach_classes"] >= 2

    joint = runtime.acquire_operator(
        s0, [demands["joint"]["first"], demands["joint"]["second"]], register_result=True
    )
    assert joint["confirmed"] is True
    assert joint["surviving_reach_classes"] == 1
    assert joint["operator_space_size"] == 20
    assert joint["operator_space_exhausted"] is True


def test_the_acquired_extension_enlarges_reach_and_ablation_removes_it() -> None:
    demands = json.loads((EXPERIMENT / "DEMANDS.json").read_text("ascii"))
    s0 = runtime.create_state()
    joint = runtime.acquire_operator(
        s0, [demands["joint"]["first"], demands["joint"]["second"]], register_result=True
    )
    s1 = joint["next_state"]
    assert len(runtime.complete_image(s1["operators"])) == 16

    for target in demands["targets"]:
        assert runtime.construct(s1, target)["constructible"] is True
        assert runtime.construct(s0, target)["constructible"] is False

    decoded = runtime.decode_state(s1)
    kept = [item for item in decoded["operators"] if not item["name"].startswith("ACQUIRED_")]
    ablated = runtime._next_state(decoded, kept, decoded["definitions"])
    for target in demands["targets"]:
        assert runtime.construct(ablated, target)["constructible"] is False
    # Byte-exact rollback.
    assert runtime.encode_state(ablated) == runtime.encode_state(s0)


def test_the_extension_survives_serialization() -> None:
    demands = json.loads((EXPERIMENT / "DEMANDS.json").read_text("ascii"))
    joint = runtime.acquire_operator(
        runtime.create_state(),
        [demands["joint"]["first"], demands["joint"]["second"]],
        register_result=True,
    )
    revived = runtime.decode_state(runtime.encode_state(joint["next_state"]))
    assert revived["state_digest"] == joint["next_state"]["state_digest"]
    for target in demands["targets"]:
        assert runtime.construct(revived, target)["constructible"] is True


def test_the_demand_fixture_matches_its_authoring_script() -> None:
    expected = runtime.canonical_json(author.build()).encode("ascii")
    assert (EXPERIMENT / "DEMANDS.json").read_bytes() == expected


def test_input_preflight_binds_the_substrate() -> None:
    report = qualification.verify_inputs()
    assert report["confirmed"] is True, [k for k, v in report["checks"].items() if not v]


def test_adversarial_boundary_audit_still_holds() -> None:
    report = audit_m107_boundaries.audit()
    checks = report["checks"]
    substantive = {key: value for key, value in checks.items() if key != _PHASE_CHECK}
    assert all(substantive.values()), [k for k, v in substantive.items() if not v]
    assert report["base_image_size"] == 4
    assert report["extended_image_size"] == 16
    if _canonical_evidence_exists():
        assert checks[_PHASE_CHECK] is False
    else:
        assert checks[_PHASE_CHECK] is True


def test_the_checker_replay_import_resolves_as_a_direct_script() -> None:
    """The exact defect that lost M103 and M105."""
    source = (ROOT / "scripts" / "check_m107_result.py").read_text(encoding="utf-8")
    assert "from scripts import run_m107_qualification" in source
    assert "_ROOT = Path(__file__).resolve().parents[1]" in source
    completed = subprocess.run(
        [sys.executable, "-c",
         "import runpy,sys;sys.argv=['check_m107_result.py'];"
         "runpy.run_path(r'%s', run_name='not_main')" % (ROOT / "scripts" / "check_m107_result.py")],
        capture_output=True, text=True, cwd=ROOT / "scripts",
    )
    assert completed.returncode == 0, completed.stderr


def test_predicate_semantics_import_nothing() -> None:
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(checker.evaluate_conditions))
    assert not any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(tree))


def test_canonical_entrypoint_is_gated_by_the_final_freeze() -> None:
    content_refusals = (
        "final protocol is absent",
        "schema or digest mismatch",
        "is not owner-authorized",
        "decisive predicate declaration changed",
        "bound apparatus changed",
    )
    if not qualification.PROTOCOL_PATH.exists():
        try:
            qualification.require_frozen()
        except qualification.QualificationRefused as error:
            assert "final protocol is absent" in str(error)
        else:  # pragma: no cover
            raise AssertionError("M107 unexpectedly has a final protocol before freeze")
        return
    try:
        armed = qualification.require_frozen()
    except qualification.QualificationRefused as error:
        assert not any(reason in str(error) for reason in content_refusals), str(error)
    else:
        assert armed["status"] == "frozen_protocol_owner_authorized"
