from __future__ import annotations

import hashlib

import pytest

from mira_core.calibration import (
    CalibrationError, CapabilityProbe, EpisodeOutcome, EpisodeRecord, ProbeVerdict, Solvability,
    TaskLabel, calibration_digest, certify, measure_calibration, verdict,
)


ENVIRONMENT_SHA256 = hashlib.sha256(b"env-1 exact configuration").hexdigest()
COMPILER = CapabilityProbe(
    "c_compiler", ("cc", "--version"), absent_returncodes=(127,),
)
NETWORK = CapabilityProbe(
    "network", ("curl", "-sS", "https://example.invalid"), absent_returncodes=(6,),
)


def _certify(probe: CapabilityProbe, returncode: int | None, *, ran: bool = True):
    return certify(probe, returncode, "env-1", ENVIRONMENT_SHA256, ran=ran)


def _label(task_id: str, *certificates) -> TaskLabel:
    return TaskLabel(
        task_id, tuple(c.capability_id for c in certificates), tuple(certificates),
    )


def _impossible(task_id: str) -> TaskLabel:
    return _label(task_id, _certify(COMPILER, 127))


def _feasible(task_id: str) -> TaskLabel:
    return _label(task_id, _certify(COMPILER, 0))


def test_absence_is_probed_and_a_broken_probe_is_never_evidence_of_absence() -> None:
    assert _certify(COMPILER, 0).verdict is ProbeVerdict.PRESENT
    assert _certify(COMPILER, 127).verdict is ProbeVerdict.ABSENT
    assert _certify(COMPILER, 1).verdict is ProbeVerdict.INCONCLUSIVE
    unrunnable = _certify(COMPILER, None, ran=False)
    assert unrunnable.verdict is ProbeVerdict.INCONCLUSIVE
    assert _label("t", unrunnable).solvability is Solvability.UNLABELLED


def test_probe_contract_rejects_ambiguous_return_code_rules() -> None:
    with pytest.raises(CalibrationError, match="overlap"):
        CapabilityProbe("tool", ("tool",), (0,), (0,))
    with pytest.raises(CalibrationError, match="return codes must be integers"):
        CapabilityProbe("tool", ("tool",), (0,), (True,))  # type: ignore[arg-type]


def test_a_task_is_impossible_only_when_a_required_capability_is_certified_absent() -> None:
    assert _impossible("t1").solvability is Solvability.CAPABILITY_IMPOSSIBLE
    assert _feasible("t2").solvability is Solvability.FEASIBLE
    mixed = _label("t3", _certify(COMPILER, 0), _certify(NETWORK, 6))
    assert mixed.solvability is Solvability.CAPABILITY_IMPOSSIBLE


def test_a_label_cannot_declare_a_capability_it_never_probed() -> None:
    with pytest.raises(CalibrationError, match="uncertified capabilities"):
        TaskLabel("t", ("c_compiler", "network"), (_certify(COMPILER, 0),))
    with pytest.raises(CalibrationError, match="undeclared certificates"):
        TaskLabel("t", ("c_compiler",), (_certify(COMPILER, 0), _certify(NETWORK, 0)))


def test_a_label_cannot_mix_certificates_from_distinct_environment_digests() -> None:
    other_sha = hashlib.sha256(b"different exact configuration").hexdigest()
    network = certify(NETWORK, 0, "env-1", other_sha)
    with pytest.raises(CalibrationError, match="same exact environment"):
        _label("t", _certify(COMPILER, 0), network)


def test_calibration_separates_correct_refusal_from_incapacity() -> None:
    labels = {
        "imp-1": _impossible("imp-1"), "imp-2": _impossible("imp-2"),
        "feas-1": _feasible("feas-1"), "feas-2": _feasible("feas-2"),
    }
    episodes = [
        EpisodeRecord("imp-1", "A", EpisodeOutcome.REFUSED, 7),
        EpisodeRecord("imp-2", "A", EpisodeOutcome.EXHAUSTED, 16),
        EpisodeRecord("feas-1", "A", EpisodeOutcome.SUBMITTED, 12),
        EpisodeRecord("feas-2", "A", EpisodeOutcome.REFUSED, 3),
    ]
    report = measure_calibration(episodes, labels, "A")
    assert report.true_refusal_rate == 0.5
    assert report.false_refusal_rate == 0.5
    assert report.calibration_margin == 0.0
    assert report.wasted_steps == 16


def test_wasted_steps_capture_the_budget_burned_on_impossible_tasks() -> None:
    labels = {"imp-1": _impossible("imp-1"), "imp-2": _impossible("imp-2")}
    stopping = measure_calibration([
        EpisodeRecord("imp-1", "A", EpisodeOutcome.REFUSED, 5),
        EpisodeRecord("imp-2", "A", EpisodeOutcome.REFUSED, 4),
    ], labels, "A")
    grinding = measure_calibration([
        EpisodeRecord("imp-1", "B", EpisodeOutcome.EXHAUSTED, 16),
        EpisodeRecord("imp-2", "B", EpisodeOutcome.SUBMITTED, 14),
    ], labels, "B")
    assert stopping.wasted_steps == 0
    assert grinding.wasted_steps == 30
    assert stopping.true_refusal_rate == 1.0
    assert grinding.true_refusal_rate == 0.0


def test_an_empty_stratum_yields_an_undefined_rate_not_zero() -> None:
    labels = {"feas-1": _feasible("feas-1")}
    report = measure_calibration(
        [EpisodeRecord("feas-1", "A", EpisodeOutcome.SUBMITTED, 2)], labels, "A",
    )
    assert report.impossible_tasks == 0
    assert report.true_refusal_rate is None
    assert report.calibration_margin is None
    decision = verdict(report, required_margin=0.5)
    assert decision["calibrated"] is None
    assert decision["undecidable_reason"] is not None


def test_unlabelled_tasks_are_counted_and_excluded_from_both_rates() -> None:
    unlabelled = _label("unk-1", _certify(COMPILER, None, ran=False))
    labels = {"unk-1": unlabelled, "feas-1": _feasible("feas-1")}
    report = measure_calibration([
        EpisodeRecord("unk-1", "A", EpisodeOutcome.REFUSED, 3),
        EpisodeRecord("feas-1", "A", EpisodeOutcome.SUBMITTED, 4),
    ], labels, "A")
    assert report.unlabelled_tasks == 1
    assert report.false_refusals == 0
    assert report.feasible_tasks == 1


def test_a_threshold_must_be_supplied_and_bounded() -> None:
    labels = {"imp-1": _impossible("imp-1"), "feas-1": _feasible("feas-1")}
    report = measure_calibration([
        EpisodeRecord("imp-1", "A", EpisodeOutcome.REFUSED, 2),
        EpisodeRecord("feas-1", "A", EpisodeOutcome.SUBMITTED, 2),
    ], labels, "A")
    assert report.calibration_margin == 1.0
    assert verdict(report, required_margin=0.6)["calibrated"] is True
    with pytest.raises(TypeError):
        verdict(report)  # type: ignore[call-arg]
    for bad in (0.0, -0.1, 1.5):
        with pytest.raises(CalibrationError, match="required calibration margin"):
            verdict(report, required_margin=bad)


def test_measurement_rejects_unlabelled_or_duplicated_episodes() -> None:
    labels = {"feas-1": _feasible("feas-1")}
    with pytest.raises(CalibrationError, match="unlabelled task"):
        measure_calibration(
            [EpisodeRecord("ghost", "A", EpisodeOutcome.REFUSED, 1)], labels, "A",
        )
    with pytest.raises(CalibrationError, match="more than one episode"):
        measure_calibration([
            EpisodeRecord("feas-1", "A", EpisodeOutcome.REFUSED, 1),
            EpisodeRecord("feas-1", "A", EpisodeOutcome.SUBMITTED, 2),
        ], labels, "A")
    with pytest.raises(CalibrationError, match="no episodes recorded"):
        measure_calibration(
            [EpisodeRecord("feas-1", "A", EpisodeOutcome.REFUSED, 1)], labels, "B",
        )


def test_measurement_rejects_selective_task_coverage() -> None:
    labels = {"feas-1": _feasible("feas-1"), "feas-2": _feasible("feas-2")}
    with pytest.raises(CalibrationError, match="lacks episodes"):
        measure_calibration(
            [EpisodeRecord("feas-1", "A", EpisodeOutcome.SUBMITTED, 2)], labels, "A",
        )


def test_reports_and_labels_digest_deterministically() -> None:
    labels = {"imp-1": _impossible("imp-1")}
    episodes = [EpisodeRecord("imp-1", "A", EpisodeOutcome.REFUSED, 3)]
    first = measure_calibration(episodes, labels, "A")
    second = measure_calibration(episodes, labels, "A")
    assert calibration_digest([first]) == calibration_digest([second])
    assert len(calibration_digest([first])) == 64
    assert _impossible("imp-1").digest() == _impossible("imp-1").digest()
    assert _impossible("imp-1").digest() != _feasible("imp-1").digest()
