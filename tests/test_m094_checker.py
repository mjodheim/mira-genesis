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


@pytest.mark.parametrize("pid", ["P7", "P8", "P9", "P10", "P11"])
def test_run_dependent_conditions_are_uncomputed_without_a_run(report: dict, pid: str) -> None:
    """No qualification exists, so these are neither satisfied nor refuted."""

    condition = _condition(report, pid)
    assert condition["computed"] is False, f"{pid} claims to be decided: {condition['evidence']}"
    assert condition["passed"] is False
    assert "not computable before a qualification run" in condition["evidence"]


def test_p7_does_not_pass_because_nothing_was_qualified(report: dict) -> None:
    """The inversion that mattered most: absence of evidence read as success."""

    condition = _condition(report, "P7")
    assert not (condition["computed"] and condition["passed"])


def test_p7_fails_loudly_if_a_result_appears_under_a_draft(
    protocol: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import check_m094_result as checker

    monkeypatch.setattr(checker, "EXPERIMENT", tmp_path)
    (tmp_path / "RESULT.json").write_text("{}", encoding="utf-8")

    result = checker.check_p7(protocol)
    assert result.computed is True and result.passed is False
    assert "RESULT.json" in result.evidence


# ── P3 measures the diagnosis, not its own fixture ───────────────────


def test_p3_passes_now_that_its_fixture_imports_what_it_measures(report: dict) -> None:
    """The reported P3 failure was a package-name mismatch in the checker."""

    condition = _condition(report, "P3")
    assert condition["computed"] is True
    assert condition["passed"] is True, condition["evidence"]


# ── P6 asserts what its docstring promises ───────────────────────────


def test_p6_detects_a_literal_method_body() -> None:
    bodies = _operations_carrying_a_literal_body()
    assert bodies, "the literal-body detector found nothing; P6 would pass vacuously"


def test_p6_fails_while_the_repair_shape_is_authored(report: dict) -> None:
    condition = _condition(report, "P6")
    assert condition["computed"] is True
    assert condition["passed"] is False
    assert "finished method body" in condition["evidence"]


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


def test_verdict_is_negative_for_real_failures_only(report: dict) -> None:
    assert report["schema"] == "m094-checker-v2"
    assert report["verdict"] == "negative"
    # P6 alone now: the repair shape is still an authored template.
    assert set(report["failed_conditions"]) == {"P6"}
    assert set(report["uncomputed_conditions"]) == {"P7", "P8", "P9", "P10", "P11"}
    assert report["passed"] + report["failed"] + report["uncomputed"] == 12


def test_uncomputed_conditions_can_never_produce_a_positive(report: dict) -> None:
    assert not (report["uncomputed"] > 0 and report["verdict"] == "positive")


def test_the_committed_report_matches_a_fresh_computation(report: dict) -> None:
    committed = json.loads((EXPERIMENT / "CHECK_REPORT.json").read_text(encoding="utf-8"))
    assert committed["verdict"] == report["verdict"]
    assert committed["failed_conditions"] == report["failed_conditions"]
    assert committed["uncomputed_conditions"] == report["uncomputed_conditions"]
