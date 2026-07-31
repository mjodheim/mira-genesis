from __future__ import annotations

import hashlib
import json
from pathlib import Path
import random
import statistics
import sys
from typing import Mapping

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis.m012b_dfa import DFA, exact_equivalence
from metamorphosis.m013e_engine import MigrationCertificate, UnknownSubstrateMigrator
from metamorphosis.m013e_lab import OpaqueBooleanMachine
from metamorphosis.m013e_runtime import OpaqueNativeBody, opaque_body_to_dfa
from metamorphosis.m014b_engine import PortablePlasticityCertificate

TARGET_COUNT = 12
MACHINE_COUNT = 3
HIDDEN_WORDS_PER_BODY = 20_000


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def median(values: list[int | float]) -> float:
    return float(statistics.median(values)) if values else 0.0


def hidden_words(seed: int, count: int = HIDDEN_WORDS_PER_BODY) -> list[tuple[int, ...]]:
    rng = random.Random(seed)
    return [
        tuple(rng.randrange(2) for _ in range(rng.randint(0, 128)))
        for _ in range(count)
    ]


def batch_accepts(dfa: DFA, words: list[tuple[int, ...]]) -> np.ndarray:
    transitions = np.asarray(dfa.transitions, dtype=np.int64)
    accepting = np.asarray(dfa.accepting, dtype=np.bool_)
    output = np.zeros(len(words), dtype=np.bool_)
    groups: dict[int, list[tuple[int, tuple[int, ...]]]] = {}
    for index, word in enumerate(words):
        groups.setdefault(len(word), []).append((index, word))
    for length, items in groups.items():
        states = np.full(len(items), dfa.initial, dtype=np.int64)
        if length:
            tokens = np.asarray([word for _, word in items], dtype=np.int64)
            for step in range(length):
                states = transitions[states, tokens[:, step]]
        values = accepting[states]
        for (index, _), value in zip(items, values.tolist()):
            output[index] = value
    return output


class HiddenSuite:
    def __init__(self, target: DFA, words: list[tuple[int, ...]]) -> None:
        self.words = words
        self.expected = batch_accepts(target, words)

    def accuracy(self, candidate: DFA) -> float:
        return float((batch_accepts(candidate, self.words) == self.expected).mean())


def semantic_audit(
    certificate: MigrationCertificate,
    machine: OpaqueBooleanMachine,
) -> tuple[bool, dict[str, bool]]:
    discovered = {opcode.opcode: opcode for opcode in certificate.substrate.opcodes}
    details: dict[str, bool] = {}
    for opcode_id in certificate.used_opcodes:
        opcode = discovered.get(opcode_id)
        details[opcode_id] = bool(
            opcode is not None
            and opcode.stable
            and opcode.table == tuple(machine._audit_truth_table(opcode_id))
            and machine._audit_stability(opcode_id) == "stable"
        )
    return all(details.values()), details


def _body_record(
    body: OpaqueNativeBody | None,
    expected: DFA,
    machine: OpaqueBooleanMachine,
    suite: HiddenSuite | None,
) -> dict[str, object]:
    record: dict[str, object] = {
        "present": body is not None,
        "sha256": None,
        "serialization_round_trip": False,
        "exact": False,
        "hidden_accuracy": 0.0,
    }
    if body is None:
        return record
    raw = body.to_json()
    record["sha256"] = sha256_bytes(raw.encode("utf-8"))
    try:
        restored = OpaqueNativeBody.from_json(raw)
        candidate = opaque_body_to_dfa(restored, machine)
    except (ValueError, RecursionError) as exc:
        record["evaluation_error"] = f"{type(exc).__name__}:{exc}"
        return record
    record["serialization_round_trip"] = restored == body
    record["exact"] = exact_equivalence(expected, candidate)[0]
    record["hidden_accuracy"] = suite.accuracy(candidate) if suite is not None else float(record["exact"])
    return record


def evaluate_chain(
    certificate: PortablePlasticityCertificate,
    base: DFA,
    target: DFA,
    machine: OpaqueBooleanMachine,
    old_suite: HiddenSuite | None,
    new_suite: HiddenSuite | None,
) -> dict[str, object]:
    old_record = _body_record(certificate.old_body, base, machine, old_suite)
    new_record = _body_record(certificate.new_body, target, machine, new_suite)
    old_semantic_exact, old_semantic_details = semantic_audit(certificate.old_migration, machine)
    new_semantic_exact = False
    new_semantic_details: dict[str, bool] = {}
    if certificate.new_migration is not None:
        new_semantic_exact, new_semantic_details = semantic_audit(certificate.new_migration, machine)
    updated_passport_exact = bool(
        certificate.updated_passport is not None
        and exact_equivalence(certificate.updated_passport, target)[0]
    )
    success = bool(
        certificate.status == "success"
        and old_record["exact"] is True
        and new_record["exact"] is True
        and old_record["hidden_accuracy"] == 1.0
        and new_record["hidden_accuracy"] == 1.0
        and old_record["serialization_round_trip"] is True
        and new_record["serialization_round_trip"] is True
        and certificate.old_body_bit_exact
        and certificate.plasticity_round_trip_exact
        and updated_passport_exact
        and old_semantic_exact
        and new_semantic_exact
        and certificate.consolidation_record_sha256 is not None
    )
    return {
        "status": certificate.status,
        "reason": certificate.reason,
        "success": success,
        "old_body": old_record,
        "new_body": new_record,
        "updated_passport_exact": updated_passport_exact,
        "old_body_bit_exact": certificate.old_body_bit_exact,
        "old_body_sha256_before": certificate.old_body_sha256_before,
        "old_body_sha256_after": certificate.old_body_sha256_after,
        "plasticity_round_trip_exact": certificate.plasticity_round_trip_exact,
        "plasticity_passport_sha256": certificate.plasticity_passport_sha256,
        "consolidation_record_sha256": certificate.consolidation_record_sha256,
        "identification_calls": certificate.inference.raw_oracle_calls if certificate.inference else 0,
        "identification_unique_queries": certificate.inference.unique_queries if certificate.inference else 0,
        "confirmation_calls": certificate.confirmation.raw_oracle_calls if certificate.confirmation else 0,
        "total_update_calls": certificate.total_update_oracle_calls,
        "initial_candidates": certificate.inference.initial_candidates if certificate.inference else 0,
        "remaining_candidates": certificate.inference.remaining_candidates if certificate.inference else 0,
        "selected_schema": (
            certificate.inference.selected_hypothesis.kind
            if certificate.inference and certificate.inference.selected_hypothesis
            else None
        ),
        "old_probe_calls": certificate.old_migration.probe_calls,
        "old_candidate_evaluations": certificate.old_migration.candidate_evaluations,
        "new_candidate_evaluations": (
            certificate.new_migration.candidate_evaluations
            if certificate.new_migration is not None
            else 0
        ),
        "old_semantic_exact_used": old_semantic_exact,
        "new_semantic_exact_used": new_semantic_exact,
        "old_semantic_audit": old_semantic_details,
        "new_semantic_audit": new_semantic_details,
    }


def migrate_with_retries(
    migrator: UnknownSubstrateMigrator,
    passport: DFA,
    machine: OpaqueBooleanMachine,
    seed: int,
    trace: Mapping[str, object],
    *,
    supplied_substrate=None,
) -> MigrationCertificate:
    attempts = (seed, seed ^ 0x9E37_79B9, seed ^ 0xC2B2_AE35)
    last: MigrationCertificate | None = None
    for index, attempt_seed in enumerate(attempts):
        attempt_trace = dict(trace)
        attempt_trace["oracle_morphogenesis_attempt"] = index
        certificate = migrator.migrate(
            passport,
            machine,
            attempt_seed,
            attempt_trace,
            supplied_substrate=supplied_substrate,
        )
        last = certificate
        if certificate.status == "success" and certificate.body is not None:
            return certificate
    assert last is not None
    return last


def evaluate_oracle_ceiling(
    base: DFA,
    target: DFA,
    machine: OpaqueBooleanMachine,
    search_seed: int,
    trace: Mapping[str, object],
) -> dict[str, object]:
    migrator = UnknownSubstrateMigrator(native_component_budget=360)
    old_certificate = migrate_with_retries(migrator, base, machine, search_seed, trace)
    if old_certificate.status != "success" or old_certificate.body is None:
        return {"success": False, "reason": "oracle_old_body_failed"}
    new_certificate = migrate_with_retries(
        migrator,
        target,
        machine,
        search_seed ^ 0x5EED_14B0,
        trace,
        supplied_substrate=old_certificate.substrate,
    )
    old = _body_record(old_certificate.body, base, machine, None)
    new = _body_record(new_certificate.body, target, machine, None)
    return {
        "success": bool(
            old_certificate.status == "success"
            and new_certificate.status == "success"
            and old["exact"] is True
            and new["exact"] is True
            and old["serialization_round_trip"] is True
            and new["serialization_round_trip"] is True
        ),
        "reason": "oracle_transformation_ceiling",
        "old": old,
        "new": new,
    }


def source_isolation_audit() -> dict[str, object]:
    public_paths = [
        ROOT / "metamorphosis" / "m014b_policy.py",
        ROOT / "metamorphosis" / "m014b_confirmation.py",
        ROOT / "metamorphosis" / "m014b_engine.py",
    ]
    public_source = "\n".join(path.read_text(encoding="utf-8") for path in public_paths)
    tests_source = (ROOT / "tests" / "test_m014b.py").read_text(encoding="utf-8")
    workflow_source = (ROOT / ".github" / "workflows" / "m014b-sealed-evaluation.yml").read_text(encoding="utf-8")
    runner_source = (ROOT / "scripts" / "m014b_eval_run.py").read_text(encoding="utf-8")
    public_forbidden = [
        "_audit_target",
        "_audit_truth_table",
        "_audit_snapshot",
        "make_positive_update",
        "make_three_edit_target",
        "make_state_adding_target",
        "make_nondeterministic_oracle",
        "runtime_nonce",
        "sealed_spec",
        "master_nonce",
    ]
    test_forbidden = [
        "sealed_spec",
        "runtime_nonce",
        "run_m014b_evaluation",
        "master_nonce",
        "results/M014b",
    ]
    public_hits = [token for token in public_forbidden if token in public_source]
    test_hits = [token for token in test_forbidden if token in tests_source]
    requirements = {
        "pull_request_opened_only": "types: [opened]" in workflow_source,
        "immutable_head_checkout": "github.event.pull_request.head.sha" in workflow_source,
        "canonical_branch_guard": "research/m014b-sealed-portable-plasticity" in workflow_source,
        "artifact_upload": "actions/upload-artifact@v4" in workflow_source,
        "canonical_flag": "--canonical" in workflow_source,
        "tests_before_evaluation": workflow_source.index("pytest -q tests/test_m014b.py") < workflow_source.index("Run canonical sealed evaluation"),
        "audit_before_evaluation": workflow_source.index("audit_m014b_isolation.py") < workflow_source.index("Run canonical sealed evaluation"),
    }
    return {
        "passed": not public_hits and not test_hits and all(requirements.values()),
        "public_forbidden_hits": public_hits,
        "test_forbidden_hits": test_hits,
        "workflow_requirements": requirements,
        "runtime_nonce_calls_in_runner": runner_source.count("runtime_nonce()"),
    }


def report(result: dict[str, object]) -> str:
    aggregate = result["aggregates"]
    criteria = result["acceptance_criteria"]
    assert isinstance(aggregate, dict)
    assert isinstance(criteria, dict)
    lines = [
        "# Mira Genesis — Metamorphosis 014b",
        "",
        f"Scientific status: **{result['status']}**.",
        "",
        "## Sealed portable-plasticity evaluation",
        "",
        "A serialized plasticity passport learned only from development demonstrations was carried with an inherited finite competence to runtime-sealed opaque Boolean machines. Genesis received only behavioral query access to each new task modification.",
        "",
        "## Results",
        "",
        f"- exact portable-plasticity chains: **{aggregate['exact_principal_chains']}/36**;",
        f"- per machine: `{aggregate['per_machine_exact']}`;",
        f"- oracle transformation ceiling: **{aggregate['oracle_ceiling_exact']}/36**;",
        f"- median identification calls: **{aggregate['median_active_identification_calls']:.1f}**;",
        f"- median independent confirmation calls: **{aggregate['median_active_confirmation_calls']:.1f}**;",
        f"- median total update calls: **{aggregate['median_active_total_update_calls']:.1f}**;",
        f"- maximum total update calls: **{aggregate['max_active_total_update_calls']}**;",
        f"- random-policy median identification calls: **{aggregate['median_random_identification_calls']:.1f}**;",
        f"- no-learned-passport median identification calls: **{aggregate['median_generic_identification_calls']:.1f}**;",
        f"- scratch L* median membership queries: **{aggregate['median_scratch_membership_queries']:.1f}**;",
        f"- negative abstentions: **{aggregate['correct_negative_abstentions']}/12**;",
        f"- false negative successes: **{aggregate['false_negative_successes']}**.",
        "",
        "## Pre-registered criteria",
        "",
    ]
    lines.extend(f"- {'PASS' if passed else 'FAIL'} — `{name}`" for name, passed in criteria.items())
    lines.extend([
        "",
        "## Interpretation",
        "",
        "A success supports portable plasticity only inside a finite language of local DFA edits on runtime-sealed opaque Boolean substrates. It does not establish general learning, autobiographical continuity, continuous-physics adaptation or open-ended self-improvement.",
    ])
    return "\n".join(lines) + "\n"
