from __future__ import annotations

from scripts import check_m105_result as checker
from scripts import run_m105_qualification as qualification


def test_development_rehearsal_satisfies_all_predicates_with_stable_replay() -> None:
    first = qualification.run_experiment()
    second = qualification.run_experiment()
    assert qualification.stable_projection(first) == qualification.stable_projection(second)
    conditions = checker.evaluate_conditions(first, replay_confirmed=True)
    assert conditions == {f"P{index}": True for index in range(1, 17)}


def test_canonical_entrypoint_refuses_before_final_freeze() -> None:
    if qualification.PROTOCOL_PATH.exists():
        protocol = qualification.require_frozen()
        assert protocol["status"] == "frozen_protocol_owner_authorized"
        return
    try:
        qualification.require_frozen()
    except qualification.QualificationRefused as error:
        assert "final protocol is absent" in str(error)
    else:  # pragma: no cover - an absent protocol must always refuse
        raise AssertionError("M105 unexpectedly has a final protocol before freeze")
