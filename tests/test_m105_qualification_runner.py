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


# require_frozen refuses everywhere except the exact freeze commit, on a clean worktree, on the
# canonical runtime -- that is the point of it. A checkout may therefore legitimately fail the
# environment gates (CI tests a merge ref, on two interpreters, often without fetching tags). What
# must never happen is a refusal about the frozen protocol's own content.
_CONTENT_REFUSALS = (
    "final protocol is absent",
    "schema or digest mismatch",
    "is not owner-authorized",
    "decisive predicate declaration changed",
    "pool binding mismatch",
    "bound apparatus changed",
)


def test_canonical_entrypoint_is_gated_by_the_final_freeze() -> None:
    if not qualification.PROTOCOL_PATH.exists():
        try:
            qualification.require_frozen()
        except qualification.QualificationRefused as error:
            assert "final protocol is absent" in str(error)
        else:  # pragma: no cover - an absent protocol must always refuse
            raise AssertionError("M105 unexpectedly has a final protocol before freeze")
        return

    protocol = qualification._read_canonical(
        qualification.PROTOCOL_PATH, "M105 final protocol"
    )
    payload = {key: item for key, item in protocol.items() if key != "protocol_digest"}
    assert protocol["schema"] == "m105-protocol-v1"
    assert protocol["protocol_digest"] == qualification.digest(payload)
    assert protocol["status"] == "frozen_protocol_owner_authorized"
    assert protocol["decisive_conditions"] == qualification.EXPECTED_PREDICATES
    assert protocol["canonical_run_allowed"] is True

    try:
        armed = qualification.require_frozen()
    except qualification.QualificationRefused as error:
        # An environment gate refused. That is correct behaviour off the freeze commit; it must
        # never be the protocol's content that is wrong.
        assert not any(reason in str(error) for reason in _CONTENT_REFUSALS), str(error)
    else:
        assert armed["protocol_digest"] == protocol["protocol_digest"]
        assert (
            qualification._git("rev-list", "-n", "1", protocol["freeze_tag"])
            == qualification._git("rev-parse", "HEAD")
        )
