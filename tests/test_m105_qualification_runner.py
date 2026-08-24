from __future__ import annotations

import sqlite3
import sys

from scripts import check_m105_result as checker
from scripts import run_m105_qualification as qualification


def _on_canonical_runtime() -> bool:
    return (
        tuple(sys.version_info[:3]) == qualification.CANONICAL_PYTHON
        and tuple(sqlite3.sqlite_version_info) == qualification.CANONICAL_SQLITE
    )


def test_development_rehearsal_satisfies_all_predicates_with_stable_replay() -> None:
    first = qualification.run_experiment()
    second = qualification.run_experiment()
    assert qualification.stable_projection(first) == qualification.stable_projection(second)
    conditions = checker.evaluate_conditions(first, replay_confirmed=True)

    # P2-P16 are mechanism predicates and must hold on every supported checkout.
    assert {key: conditions[key] for key in conditions if key != "P1"} == {
        f"P{index}": True for index in range(2, 17)
    }

    # P1 pins the canonical runtime, so a DEVELOPMENT rehearsal can only satisfy it on that
    # exact interpreter. Asserting it unconditionally would make CI red on the frozen commit
    # while claiming a runtime fact the rehearsal does not have. The frozen verdict rule is
    # unchanged -- a canonical attempt still needs P1-P16 all true, and require_frozen refuses
    # to run at all off the canonical pair, so P1 cannot be dodged.
    assert conditions["P1"] is _on_canonical_runtime()


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
