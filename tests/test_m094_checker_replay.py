"""Can the M094 checker ever return `positive`, and can each condition still fail?

The audit found that it could not. `verdict_rule` says "positive only when every condition
is computed and true", but P7 and P12 *failed* the moment a `RESULT.json` appeared and P8
through P11 returned `uncomputed` unconditionally, so before a run the verdict was
`incomplete` and after one it became `negative`. A checker whose best case is unreachable
certifies nothing.

These tests drive the checker against a synthetic preserved run in a temporary experiment
directory. Two properties matter, and the second is the one that keeps the first honest:

1. a complete, well-formed run reaches `positive`;
2. corrupting any single run-dependent condition's evidence turns it negative.

Nothing here writes into the real `experiments/M094/`.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_m094_result as checker  # noqa: E402

REAL_EXPERIMENT = REPO_ROOT / "experiments" / "M094"


def _requirement() -> list[list[object]]:
    return [
        ["goal_id", "goal_id", None],
        ["instruction", "instruction", None],
        ["success_criteria", "success_criteria", None],
    ]


def _synthetic_run(mechanism: str, entries: list[dict]) -> dict:
    """A preserved run of the shape `scripts/run_m094_experiment.py` writes."""

    validation = {
        "validator_id": "m094-behavioural-validator",
        "accepted": True,
        "reasons": [],
        "cases_total": 8,
        "cases_satisfied": 8,
        "methods_tried": 1,
        "receipt": "r" * 64,
    }
    development = {
        "arm": "endogenous_diagnosis_and_synthesis",
        "selected_component": "mira_core/contracts.py",
        "class": "Goal",
        "capability": "render_value_object_as_mapping",
        "requirement": _requirement(),
        "mechanism_digest": mechanism,
    }
    return {
        "schema": "m094-result-v1",
        "milestone": "M094",
        "track": "A",
        "attempt": 1,
        "model_calls": 0,
        "network_calls": 0,
        "mechanism_digest": mechanism,
        "arms": {
            "endogenous_diagnosis_and_synthesis": {
                "arm": "endogenous_diagnosis_and_synthesis",
                "closed": True,
                "development": development,
                "validation": validation,
            },
            "more_budget_same_operations": {
                "arm": "more_budget_same_operations",
                "closed": True,
                "development": dict(development, arm="more_budget_same_operations"),
            },
            "random_component_selection": {
                "arm": "random_component_selection",
                "closed": False,
                "development": {
                    "arm": "random_component_selection",
                    "notes": {"component_override": "mira_core/safety.py"},
                },
            },
        },
        "rollback": {
            "fault": "truncate_the_adopted_method",
            "digest_domain": "bytes",
            "fault_struck_the_live_file": True,
            "adopted_supplied_the_capability": True,
            "damage_was_behavioural": True,
            "restoration_is_byte_exact": True,
            "restoration_matches_the_preserved_original_bytes": True,
            "restored_matches_the_original_behaviour": True,
            "store_version_after_restore": 0,
        },
        "qualification": {
            "salt_is_the_adopted_mechanism_digest": True,
            "drawn_after_adoption": True,
            "mechanism_digest": mechanism,
            "entries": entries,
        },
    }


@pytest.fixture
def staged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Point the checker at a temporary experiment directory holding a real draw.

    The pool is the committed one, so the draw the checker recomputes is the real draw. The
    mechanism digest is the one the current mechanism actually produces, read from the
    committed check report's own inputs rather than invented, so the recomputation is a
    genuine check and not a tautology.
    """

    experiment = tmp_path / "M094"
    experiment.mkdir()
    for name in ("PROTOCOL.json", "QUALIFICATION_POOL.json", "DESIGN_AUDIT.json",
                 "DESIGN_AUDIT.md"):
        (experiment / name).write_bytes((REAL_EXPERIMENT / name).read_bytes())

    monkeypatch.setattr(checker, "EXPERIMENT", experiment)
    monkeypatch.setattr(checker, "PROTOCOL_PATH", experiment / "PROTOCOL.json")
    monkeypatch.setattr(checker, "RESULT_PATH", experiment / "RESULT.json")
    monkeypatch.setattr(checker, "QUALIFICATION_PATH", experiment / "QUALIFICATION.json")
    monkeypatch.setattr(checker, "DESIGN_AUDIT_PATH", experiment / "DESIGN_AUDIT.json")
    monkeypatch.setattr(checker, "DESIGN_AUDIT_MD", experiment / "DESIGN_AUDIT.md")

    from metamorphosis.m094_diagnosis import diagnose
    from metamorphosis.m094_synthesis import suggest_operations

    result = diagnose(REPO_ROOT, checker.COMPONENT_PATHS)
    top = result.unmet[0]
    operations = suggest_operations(
        REPO_ROOT, top.component_path, top.target, top.capability, top.target, top.detail,
    )
    mechanism = operations[0].digest

    from materialize_m094_qualification import draw

    pool = json.loads((experiment / "QUALIFICATION_POOL.json").read_text(encoding="utf-8"))
    drawn = draw(pool, mechanism)
    entries = [
        {"component": entry["component"], "class": entry["class"],
         "entry_digest": entry["entry_digest"], "outcome": "satisfied", "satisfied": True}
        for entry in drawn
    ]

    def write(run: dict) -> dict:
        (experiment / "RESULT.json").write_text(
            json.dumps(run, sort_keys=True), encoding="utf-8",
        )
        protocol = json.loads((experiment / "PROTOCOL.json").read_text(encoding="utf-8"))
        return checker.compute_report(protocol)

    return write, mechanism, entries


# ── the best case must be reachable ───────────────────────────────────


def test_a_complete_run_reaches_a_positive_verdict(staged) -> None:
    write, mechanism, entries = staged
    report = write(_synthetic_run(mechanism, entries))

    assert report["uncomputed_conditions"] == [], (
        "conditions remain uncomputed with a complete run present: "
        f"{report['uncomputed_conditions']}"
    )
    assert report["failed_conditions"] == [], report["failed_conditions"]
    assert report["verdict"] == "positive"
    assert report["passed"] == report["total_conditions"] == 12


def test_every_condition_is_computed_once_a_run_exists(staged) -> None:
    write, mechanism, entries = staged
    report = write(_synthetic_run(mechanism, entries))
    for pid, condition in report["conditions"].items():
        assert condition["computed"] is True, f"{pid} is still uncomputed"


# ── and every run-dependent condition must still be able to fail ──────


def test_p7_fails_when_the_recorded_draw_is_not_the_draw_the_salt_produces(staged) -> None:
    write, mechanism, entries = staged
    run = _synthetic_run(mechanism, entries)
    run["qualification"]["entries"] = [
        dict(entry, entry_digest="0" * 64) for entry in entries
    ]
    report = write(run)
    assert "P7" in report["failed_conditions"]
    assert "not the draw" in report["conditions"]["P7"]["evidence"]


def test_p7_fails_when_a_drawn_requirement_was_missed(staged) -> None:
    write, mechanism, entries = staged
    run = _synthetic_run(mechanism, entries)
    run["qualification"]["entries"] = [
        dict(entries[0], outcome="refuted", satisfied=False), entries[1],
    ]
    report = write(run)
    assert "P7" in report["failed_conditions"]


def test_p7_is_uncomputed_when_a_drawn_entry_is_unrunnable(staged) -> None:
    """An instrument defect must not read as a refutation.

    Seven of the nine frozen pool entries carry hidden cases that raise on construction. If
    an unrunnable entry scored as a failure, the pool would refute H39 on its own.
    """

    write, mechanism, entries = staged
    run = _synthetic_run(mechanism, entries)
    run["qualification"]["entries"] = [
        dict(entries[0], outcome="unrunnable", satisfied=None), entries[1],
    ]
    report = write(run)
    assert report["conditions"]["P7"]["computed"] is False
    assert "P7" not in report["failed_conditions"]
    assert report["verdict"] == "incomplete"


def test_p7_fails_when_the_draw_is_not_cross_component(staged) -> None:
    write, mechanism, entries = staged
    run = _synthetic_run(mechanism, entries)
    run["qualification"]["entries"] = [entries[0], dict(entries[1],
                                                        component=entries[0]["component"])]
    report = write(run)
    assert "P7" in report["failed_conditions"]


def test_p8_fails_when_the_validator_refused(staged) -> None:
    write, mechanism, entries = staged
    run = _synthetic_run(mechanism, entries)
    arm = run["arms"]["endogenous_diagnosis_and_synthesis"]
    arm["validation"] = dict(arm["validation"], accepted=False, reasons=["refused"])
    report = write(run)
    assert "P8" in report["failed_conditions"]


def test_p8_fails_when_the_validation_carries_no_receipt(staged) -> None:
    write, mechanism, entries = staged
    run = _synthetic_run(mechanism, entries)
    arm = run["arms"]["endogenous_diagnosis_and_synthesis"]
    arm["validation"] = dict(arm["validation"], receipt="")
    report = write(run)
    assert "P8" in report["failed_conditions"]


def test_p9_fails_when_more_budget_reached_a_different_mechanism(staged) -> None:
    write, mechanism, entries = staged
    run = _synthetic_run(mechanism, entries)
    budget = run["arms"]["more_budget_same_operations"]
    budget["development"] = dict(budget["development"], mechanism_digest="f" * 64)
    report = write(run)
    assert "P9" in report["failed_conditions"]


def test_p10_fails_when_the_random_arm_closed_the_requirement(staged) -> None:
    write, mechanism, entries = staged
    run = _synthetic_run(mechanism, entries)
    run["arms"]["random_component_selection"]["closed"] = True
    report = write(run)
    assert "P10" in report["failed_conditions"]


def test_p10_fails_when_the_random_arm_imposed_no_component(staged) -> None:
    """Otherwise the arm could be the endogenous path wearing another name."""

    write, mechanism, entries = staged
    run = _synthetic_run(mechanism, entries)
    run["arms"]["random_component_selection"]["development"] = {"notes": {}}
    report = write(run)
    assert "P10" in report["failed_conditions"]


@pytest.mark.parametrize("key", [
    "fault_struck_the_live_file",
    "damage_was_behavioural",
    "restoration_is_byte_exact",
    "restored_matches_the_original_behaviour",
])
def test_p11_fails_on_each_missing_rollback_property(staged, key: str) -> None:
    write, mechanism, entries = staged
    run = _synthetic_run(mechanism, entries)
    run["rollback"][key] = False
    report = write(run)
    assert "P11" in report["failed_conditions"], key


def test_p11_fails_when_the_store_did_not_return_to_version_zero(staged) -> None:
    write, mechanism, entries = staged
    run = _synthetic_run(mechanism, entries)
    run["rollback"]["store_version_after_restore"] = 1
    report = write(run)
    assert "P11" in report["failed_conditions"]


def test_p12_fails_when_the_run_records_a_model_call(staged) -> None:
    write, mechanism, entries = staged
    run = _synthetic_run(mechanism, entries)
    run["model_calls"] = 1
    report = write(run)
    assert "P12" in report["failed_conditions"]


def test_p12_fails_when_the_run_is_not_track_a(staged) -> None:
    write, mechanism, entries = staged
    run = _synthetic_run(mechanism, entries)
    run["track"] = "B"
    report = write(run)
    assert "P12" in report["failed_conditions"]


def test_p12_fails_when_a_withdrawn_run_is_not_declared(staged, tmp_path: Path) -> None:
    """Superseded runs are preserved and disclosed; preserved-but-undisclosed is a violation."""

    write, mechanism, entries = staged
    (tmp_path / "M094" / "WITHDRAWN_RESULT_ATTEMPT_1.json").write_text("{}", encoding="utf-8")
    run = _synthetic_run(mechanism, entries)
    run.pop("prior_attempts", None)
    report = write(run)
    assert "P12" in report["failed_conditions"]


# ── and the pre-run state must be unchanged ───────────────────────────


def test_without_a_run_the_verdict_is_incomplete_not_negative(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A staged directory holding no run: five conditions await one.

    This read the real experiment directory until the canonical run of 19 August 2026 put a
    result in it. The property is about what the checker does with *no* run, so it is asserted
    against a directory that has none rather than deleted for having become false.
    """

    experiment = tmp_path / "M094"
    experiment.mkdir()
    for name in ("PROTOCOL.json", "QUALIFICATION_POOL.json", "DESIGN_AUDIT.json",
                 "DESIGN_AUDIT.md"):
        (experiment / name).write_bytes((REAL_EXPERIMENT / name).read_bytes())
    monkeypatch.setattr(checker, "EXPERIMENT", experiment)
    monkeypatch.setattr(checker, "DESIGN_AUDIT_PATH", experiment / "DESIGN_AUDIT.json")
    monkeypatch.setattr(checker, "DESIGN_AUDIT_MD", experiment / "DESIGN_AUDIT.md")

    protocol = json.loads((experiment / "PROTOCOL.json").read_text(encoding="utf-8"))
    report = checker.compute_report(protocol)
    assert report["verdict"] == "incomplete"
    assert report["failed"] == 0
    assert report["uncomputed_conditions"] == ["P7", "P8", "P9", "P10", "P11"]


def test_the_preserved_run_reaches_a_positive_verdict() -> None:
    """And the real directory, whenever it holds a run.

    Attempt 1 was withdrawn on 19 August 2026 over the P11 byte-exactness defect, so between
    that withdrawal and attempt 2 there is legitimately no run to read. The test skips rather
    than asserts in that window: a green run of the suite must not depend on which side of a
    withdrawal the repository is on.
    """

    if not (REAL_EXPERIMENT / "RESULT.json").exists():
        pytest.skip("no current attempt: the preserved one is withdrawn")

    protocol = json.loads((REAL_EXPERIMENT / "PROTOCOL.json").read_text(encoding="utf-8"))
    report = checker.compute_report(protocol)
    assert report["uncomputed_conditions"] == []
    assert report["failed_conditions"] == []
    assert report["verdict"] == "positive"


def test_a_withdrawn_attempt_is_preserved_and_declared() -> None:
    """Superseded runs are preserved and disclosed, and the attempt number derives from them."""

    withdrawn = sorted(REAL_EXPERIMENT.glob("WITHDRAWN_RESULT_ATTEMPT_*.json"))
    if not withdrawn:
        pytest.skip("no attempt has been withdrawn")

    for path in withdrawn:
        record = json.loads(path.read_text(encoding="utf-8"))
        assert record["is_rehearsal"] is False
        assert record["source_commit"], f"{path.name} records no commit"
        assert record["model_calls"] == 0 and record["network_calls"] == 0

    disclosure = (REAL_EXPERIMENT / "POST_VERDICT_DISCLOSURE.md").read_text(encoding="utf-8")
    assert "restoration_is_byte_exact" in disclosure, (
        "a withdrawn attempt must be disclosed, not merely preserved"
    )
