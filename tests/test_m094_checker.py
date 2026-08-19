"""The checker must be able to be satisfied, and must not decide what it cannot see.

`scripts/check_m094_result.py` arrived with defects that made its verdict
unreliable in both directions. The checks below are written against each one, so
that a regression reintroduces a red test rather than a plausible-looking report:

* two conditions demanded that control arms be ceiling arms, while a third
  demanded the ceiling set be exactly one arm, so no protocol could satisfy all
  three at once;
* P11 failed unless the protocol *permitted* rerolls, which the discipline
  forbids;
* P7 passed precisely because no qualification existed, and would have flipped
  to FAIL once one did;
* P3's fixture imported a different package than the one it measured;
* P6 omitted the one assertion its own docstring promised.

The full report costs about a minute, dominated by P5's threshold sweep over the
whole repository, so it is computed once for the module and asserted against.
Individual checks are called directly only where a mutated protocol is needed.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from check_m094_result import (
    PROTOCOL_PATH,
    _operations_carrying_a_literal_body,
    check_p7,
    check_p11,
    compute_report,
)

EXPERIMENT = Path("experiments/M094").resolve()


@pytest.fixture(scope="module")
def protocol() -> dict:
    return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def report(protocol: dict) -> dict:
    return compute_report(protocol)


def _condition(report: dict, name: str) -> dict:
    return report["conditions"][name]


# ── The checker must be satisfiable at all ───────────────────────────


def test_no_two_conditions_make_contradictory_demands_on_the_arms(report: dict) -> None:
    """P1 fixes the ceiling set; P9 and P10 must not demand membership in it.

    An earlier revision required `more_budget_same_operations` and
    `random_component_selection` to be ceiling arms while P1 required the ceiling
    set to be exactly `{authored_target_component}`. No protocol could pass all
    three, so the checker was unsatisfiable by construction.
    """

    assert _condition(report, "P1")["passed"] is True

    for pid in ("P9", "P10"):
        evidence = _condition(report, pid)["evidence"]
        assert "is not in ceiling arms" not in evidence
        assert "is not in the ceiling arms" not in evidence


def test_control_arms_must_not_be_ceiling_arms(protocol: dict) -> None:
    controls = {"more_budget_same_operations", "random_component_selection"}
    assert controls <= set(protocol["arms"])
    assert controls.isdisjoint(protocol["ceiling_arms"])


def test_p11_requires_rerolls_to_be_forbidden(protocol: dict) -> None:
    """The disciplined value is False; the checker must not demand True."""

    assert protocol["retry_policy"]["reroll_permitted"] is False
    assert "reroll_permitted is not true" not in check_p11(protocol).evidence

    permissive = copy.deepcopy(protocol)
    permissive["retry_policy"]["reroll_permitted"] = True
    refused = check_p11(permissive)
    assert refused.computed is True and refused.passed is False
    assert "must be false" in refused.evidence


# ── Conditions must not be decided without the evidence they need ────


@pytest.fixture
def no_run_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """The checker pointed at an experiment directory that holds no run.

    These properties used to be asserted against the real `experiments/M094/`, which held no
    run because M094 had not been performed. It has been performed now, so the real directory
    is the wrong place to look for them -- but the properties themselves still matter, and a
    staged directory is where they belong. Deleting them because the world moved on would
    throw away the guard against the defect the audit found.
    """

    import check_m094_result as checker

    experiment = tmp_path / "M094"
    experiment.mkdir()
    for name in ("PROTOCOL.json", "QUALIFICATION_POOL.json", "DESIGN_AUDIT.json",
                 "DESIGN_AUDIT.md"):
        (experiment / name).write_bytes((EXPERIMENT / name).read_bytes())
    monkeypatch.setattr(checker, "EXPERIMENT", experiment)
    monkeypatch.setattr(checker, "PROTOCOL_PATH", experiment / "PROTOCOL.json")
    monkeypatch.setattr(checker, "DESIGN_AUDIT_PATH", experiment / "DESIGN_AUDIT.json")
    monkeypatch.setattr(checker, "DESIGN_AUDIT_MD", experiment / "DESIGN_AUDIT.md")
    protocol = json.loads((experiment / "PROTOCOL.json").read_text(encoding="utf-8"))
    return checker.compute_report(protocol)


@pytest.mark.parametrize("pid", ["P7", "P8", "P9", "P10", "P11"])
def test_run_dependent_conditions_are_uncomputed_without_a_run(
    no_run_report: dict, pid: str
) -> None:
    """With no run, these are neither satisfied nor refuted. Absence is not evidence."""

    condition = _condition(no_run_report, pid)
    assert condition["computed"] is False, f"{pid} claims to be decided: {condition['evidence']}"
    assert condition["passed"] is False


def test_p7_does_not_pass_because_nothing_was_qualified(no_run_report: dict) -> None:
    """The inversion that mattered most: absence of evidence read as success."""

    condition = _condition(no_run_report, "P7")
    assert not (condition["computed"] and condition["passed"])


def test_a_run_that_exists_is_read_rather_than_ignored(report: dict) -> None:
    """The converse of the no-run case, whenever the real directory holds a run.

    Skipped between the withdrawal of attempt 1 and attempt 2, when there legitimately is
    none. What must never happen is a run present and conditions still uncomputed.
    """

    if not (EXPERIMENT / "RESULT.json").exists():
        pytest.skip("no current attempt: the preserved one is withdrawn")

    for pid, condition in report["conditions"].items():
        assert condition["computed"] is True, f"{pid} is uncomputed with a run preserved"


def test_p7_fails_loudly_if_a_result_has_nothing_behind_it(
    protocol: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A result artifact with no qualification in it must fail, loudly and computed.

    This test previously asserted that P7 fails *because* a RESULT.json exists at all, and
    checked for the string "RESULT.json" in the evidence. That polarity is the blocker
    `docs/REPOSITORY_AUDIT_2026_08_18.md` recorded: it made a positive verdict unreachable,
    because performing the experiment failed the condition named for the experiment
    succeeding. The property worth keeping is the one asserted here -- a result the checker
    cannot substantiate is a computed failure and not an `uncomputed` shrug -- and it is now
    checked by what the condition concludes rather than by how it words it.
    """

    import check_m094_result as checker

    monkeypatch.setattr(checker, "EXPERIMENT", tmp_path)
    (tmp_path / "RESULT.json").write_text("{}", encoding="utf-8")

    result = checker.check_p7(protocol)
    assert result.computed is True, "an unsubstantiated result must not read as uncomputed"
    assert result.passed is False
    assert result.evidence


def test_p7_fails_when_qualification_data_exists_with_no_run(
    protocol: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The leak the old polarity was reaching for, stated precisely.

    Qualification data appearing *without* a run that produced it is the real violation: it
    means the held-out material exists ahead of the thing that was supposed to draw it.
    """

    import check_m094_result as checker

    monkeypatch.setattr(checker, "EXPERIMENT", tmp_path)
    (tmp_path / "QUALIFICATION.json").write_text("{}", encoding="utf-8")

    result = checker.check_p7(protocol)
    assert result.computed is True and result.passed is False
    assert "QUALIFICATION.json" in result.evidence


# ── P3 measures the diagnosis, not its own fixture ───────────────────


def test_p3_passes_now_that_its_fixture_imports_what_it_measures(report: dict) -> None:
    """The reported P3 failure was a package-name mismatch in the checker."""

    condition = _condition(report, "P3")
    assert condition["computed"] is True
    assert condition["passed"] is True, condition["evidence"]


# ── P6 asserts what its docstring promises ───────────────────────────


def test_p6_detector_still_catches_a_literal_method_body(tmp_path: Path) -> None:
    """P6 must not pass merely because the detector stopped detecting.

    The templates are gone from the real modules, so the instrument is exercised
    against a synthetic one that has one. It also scans every `m094_*.py` module
    rather than a single file, since a template moved to a new module would
    otherwise slip past — the failure mode this audit keeps finding.
    """

    template = "def to_dict(self) -> dict:\n    return {}"
    (tmp_path / "m094_pretend.py").write_text(
        "TEMPLATE = " + repr(template) + "\n", encoding="utf-8"
    )
    assert _operations_carrying_a_literal_body(tmp_path) != set()


def test_no_m094_module_carries_a_literal_method_body() -> None:
    assert _operations_carrying_a_literal_body() == set()


def test_p6_passes_now_that_the_repair_is_assembled(report: dict) -> None:
    """The repair is composed from operations, none of which is a method."""

    condition = _condition(report, "P6")
    assert condition["computed"] is True
    assert condition["passed"] is True, condition["evidence"]


# ── P5 keeps reporting the disclosed instability ─────────────────────


def test_p5_passes_now_that_no_constant_can_decide(report: dict) -> None:
    """Defect 5 is repaired: there is no sweepable knob left.

    `RenderAsMapping.min_fields` was authored and its declared value 3 was the
    outlier that selected `mira_core/safety.py`; 2, 4 and 5 all selected
    `mira_core/contracts.py`, which is what the threshold-free rule selects too.
    """

    condition = _condition(report, "P5")
    assert condition["computed"] is True and condition["passed"] is True, condition["evidence"]
    assert condition["detail"]["numeric_constants_in_capability_shapes"] == {}
    assert condition["detail"]["selected"] == "mira_core/contracts.py"


# ── The verdict rule ─────────────────────────────────────────────────


def test_the_verdict_is_incomplete_while_no_run_exists(no_run_report: dict) -> None:
    """Preserved from before the run, and still the property that matters most.

    A checker that reports `positive` on a milestone nobody performed is worthless. The real
    directory now holds a run, so this is asserted where the condition it describes still
    holds.
    """

    assert no_run_report["verdict"] == "incomplete"
    assert no_run_report["failed"] == 0
    assert no_run_report["uncomputed_conditions"] == ["P7", "P8", "P9", "P10", "P11"]


def test_uncomputed_conditions_can_never_produce_a_positive(report: dict) -> None:
    assert not (report["uncomputed"] > 0 and report["verdict"] == "positive")


def test_the_tallies_account_for_every_condition(report: dict) -> None:
    """Carried over from the pre-run verdict test, which the run made obsolete."""

    assert report["schema"] == "m094-checker-v2"
    assert report["passed"] + report["failed"] + report["uncomputed"] == 12
    assert report["total_conditions"] == 12


def test_the_committed_report_matches_a_fresh_computation(report: dict) -> None:
    committed = json.loads((EXPERIMENT / "CHECK_REPORT.json").read_text(encoding="utf-8"))
    assert committed["verdict"] == report["verdict"]
    assert committed["failed_conditions"] == report["failed_conditions"]
    assert committed["uncomputed_conditions"] == report["uncomputed_conditions"]
