"""Independent verifier for persisted M041 completion artefacts."""

from __future__ import annotations

import hashlib
import re
from typing import Mapping, Sequence

from .m012b_dfa import DFA, exact_equivalence
from .m039_engine import dfa_digest
from .m040_engine import OBSERVATIONS
from .m040_result_verify import verify_m040_result
from .m041_isolated_validation import (
    _case_digest,
    _case_rows,
    dfa_candidate_digest,
)

_SHA256 = re.compile(r"\A[0-9a-f]{64}\Z")
_EXPECTED_GATES = {
    "gate_1_autonomous_diagnosis",
    "gate_2_internal_tool_ownership",
    "gate_3_self_rewrite",
    "gate_4_isolated_validation",
    "gate_5_held_out_improvement",
    "gate_6_adoption_and_rollback",
    "gate_7_trans_substrate_metamorphosis",
    "gate_8_post_migration_plasticity",
    "gate_9_repeated_improvement_cycles",
    "gate_10_measurement_integrity",
}


class M041ResultVerificationError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise M041ResultVerificationError(message)


def _mapping(value: object, name: str) -> Mapping[str, object]:
    _require(isinstance(value, Mapping), f"{name} must be a mapping")
    return value  # type: ignore[return-value]


def _sequence(value: object, name: str) -> Sequence[object]:
    _require(
        isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)),
        f"{name} must be a sequence",
    )
    return value  # type: ignore[return-value]


def _sha(value: object, name: str) -> str:
    text = str(value)
    _require(bool(_SHA256.match(text)), f"{name} is not canonical SHA-256 hexadecimal")
    return text


def _dfa(value: object, name: str) -> DFA:
    try:
        return DFA.from_dict(_mapping(value, name))
    except (KeyError, TypeError, ValueError) as error:
        raise M041ResultVerificationError(f"{name} is not a valid DFA") from error


def _validation_is_perfect(validation: Mapping[str, object]) -> None:
    _require(str(validation["status"]) == "completed", "isolated validation did not complete")
    for field in (
        "schema_valid",
        "candidate_digest_matches",
        "case_digest_matches",
        "task_passed",
        "regressions_passed",
        "strict_improvement",
        "exact",
        "passive_candidate_data",
    ):
        _require(bool(validation[field]), f"isolated validation field {field} is false")
    _require(validation["candidate_execution_authority"] is False, "candidate received execution authority")
    _require(validation["timed_out"] is False, "isolated validation timed out")
    _require(int(validation["return_code"]) == 0, "isolated validation subprocess failed")
    _require(int(validation["candidate_passed"]) == int(validation["task_total"]), "candidate missed hidden cases")
    _require(int(validation["candidate_passed"]) > int(validation["parent_passed"]), "candidate did not strictly improve")
    _require(int(validation["regression_passed"]) == int(validation["regression_total"]), "critical regression failed")
    _require(not _sequence(validation["task_failures"], "task failures"), "task failures are present")
    _require(not _sequence(validation["regression_failures"], "regression failures"), "regression failures are present")
    _require(validation["equivalence_witness"] is None, "exact candidate carries an equivalence witness")
    for field in ("candidate_digest", "parent_digest", "target_digest", "case_digest", "workspace_digest"):
        _sha(validation[field], field)


def verify_m041_result(
    payload: Mapping[str, object],
    *,
    raw_bytes: bytes | None = None,
    expected_sha256: str | None = None,
) -> None:
    """Raise unless a persisted result supports all ten bounded Genesis gates."""

    if expected_sha256 is not None:
        _sha(expected_sha256, "expected artefact digest")
        _require(raw_bytes is not None, "raw bytes are required for external digest verification")
        _require(hashlib.sha256(raw_bytes).hexdigest() == expected_sha256, "external artefact digest mismatch")

    _require(str(payload["schema"]) == "m041-canonical-scientific-result/1", "unsupported M041 schema")
    base = _mapping(payload["base_result"], "M040-style base result")
    verify_m040_result(base)

    gates = _mapping(payload["gate_verdicts"], "gate verdicts")
    _require(set(gates) == _EXPECTED_GATES, "M041 gate set differs from the frozen protocol")
    _require(all(value is True for value in gates.values()), "at least one Genesis gate is false")
    _require(bool(payload["all_ten_gates_supported"]), "combined ten-gate field is false")
    _require(bool(payload["canonical_completion_claim_supported"]), "completion claim field is false")
    _require(bool(payload["isolated_replay_byte_identical"]), "isolated replay is not byte-identical")

    validations = _sequence(payload["isolated_validations"], "isolated validations")
    _require(int(payload["isolated_validation_count"]) == 2, "M041 must retain first and replay validation")
    _require(len(validations) == 2, "M041 validation record count differs from the protocol")
    first = _mapping(validations[0], "first isolated validation")
    replay = _mapping(validations[1], "replay isolated validation")
    _validation_is_perfect(first)
    _validation_is_perfect(replay)
    _require(first == replay, "isolated validation changed during seed-only replay")

    inputs = _mapping(payload["validator_inputs"], "validator inputs")
    parent = _dfa(inputs["parent_dfa"], "validator parent")
    candidate = _dfa(inputs["candidate_dfa"], "validator candidate")
    target = _dfa(inputs["target_dfa"], "validator target")
    observations_raw = _sequence(inputs["observations"], "validator observations")
    _require(len(observations_raw) == len(OBSERVATIONS) == 127, "validator observation count changed")
    observations: dict[tuple[int, ...], bool] = {}
    for row in observations_raw:
        value = _mapping(row, "validator observation")
        word = tuple(int(symbol) for symbol in _sequence(value["word"], "observation word"))
        observations[word] = bool(value["expected"])
    _require(tuple(sorted(observations)) == tuple(sorted(OBSERVATIONS)), "validator observation words changed")
    _require(all(observations[word] == target.accepts(word) for word in OBSERVATIONS), "validator observations disagree with target")

    exact, witness = exact_equivalence(candidate, target)
    _require(exact and witness is None, "persisted candidate is not exactly equivalent to target")
    parent_exact, _ = exact_equivalence(parent, target)
    _require(not parent_exact, "persisted parent is already equivalent to target")

    arms = _mapping(base["arms"], "base arms")
    full = _mapping(arms["complete_migrated_lineage"], "complete migrated arm")
    _require(dfa_digest(candidate) == str(full["accepted_body_digest"]), "validator candidate differs from adopted base candidate")
    task = _mapping(base["task"], "base task")
    _require(dfa_digest(target) == str(task["target_digest"]), "validator target differs from hidden task")

    candidate_digest = dfa_candidate_digest(candidate)
    parent_digest = dfa_candidate_digest(parent)
    target_digest = dfa_candidate_digest(target)
    regressions = {
        word: expected
        for word, expected in observations.items()
        if parent.accepts(word) == expected
    }
    cases = _case_rows(observations)
    regression_rows = _case_rows(regressions)
    case_digest = _case_digest(cases, regression_rows)
    _require(first["candidate_digest"] == candidate_digest, "candidate digest mismatch")
    _require(first["parent_digest"] == parent_digest, "parent digest mismatch")
    _require(first["target_digest"] == target_digest, "target digest mismatch")
    _require(candidate_digest == target_digest, "candidate and target passive-data digests differ")
    _require(first["case_digest"] == case_digest, "case digest mismatch")
    _require(int(first["candidate_passed"]) == sum(candidate.accepts(word) == expected for word, expected in observations.items()), "candidate score mismatch")
    _require(int(first["parent_passed"]) == sum(parent.accepts(word) == expected for word, expected in observations.items()), "parent score mismatch")
    _require(int(first["regression_total"]) == len(regressions), "regression count mismatch")

    limits = _mapping(first["limits"], "isolated limits")
    expected_limits = {
        "cpu_seconds": 2,
        "memory_bytes": 134_217_728,
        "file_size_bytes": 2_097_152,
        "process_count": 1,
        "open_files": 32,
        "wall_seconds": 5,
        "output_bytes": 131_072,
        "maximum_states": 64,
        "maximum_observations": 4_096,
        "maximum_input_bytes": 4_194_304,
    }
    _require(dict(limits) == expected_limits, "isolated resource limits differ from the protocol")
