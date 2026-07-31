from __future__ import annotations

import hashlib
import json
from pathlib import Path
import random
import statistics
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis.m012b_dfa import DFA, exact_equivalence
from metamorphosis.m012b_primitives import Primitive
from metamorphosis.m013e_engine import MigrationCertificate
from metamorphosis.m013e_lab import OpaqueBooleanMachine
from metamorphosis.m013e_runtime import (
    DiscoveredOpcode,
    DiscoveredSubstrate,
    OpaqueNativeBody,
    opaque_body_to_dfa,
    unique_component_count,
)

TARGET_COUNT = 12
MACHINE_COUNT = 3
SEARCH_REPETITIONS = 3
HIDDEN_WORDS_PER_SUCCESS = 10_000


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hidden_words(seed: int, count: int = HIDDEN_WORDS_PER_SUCCESS) -> list[tuple[int, ...]]:
    rng = random.Random(seed)
    return [tuple(rng.randrange(2) for _ in range(rng.randint(0, 128))) for _ in range(count)]


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


def evaluate_certificate(
    certificate: MigrationCertificate,
    passport: DFA,
    machine: OpaqueBooleanMachine,
    suite: HiddenSuite | None,
    audit_semantics: bool,
) -> dict[str, object]:
    record: dict[str, object] = {
        "status": certificate.status,
        "reason": certificate.reason,
        "probe_calls": certificate.probe_calls,
        "candidate_evaluations": certificate.candidate_evaluations,
        "native_components": certificate.native_components,
        "serialized_bytes": certificate.serialized_bytes,
        "elapsed_seconds": certificate.elapsed_seconds,
        "used_opcodes": list(certificate.used_opcodes),
        "trace": dict(certificate.trace),
        "exact": False,
        "hidden_accuracy": 0.0,
        "serialization_round_trip": False,
        "semantic_exact_used": False,
        "semantic_audit": {},
        "body_sha256": None,
    }
    if certificate.body is None:
        return record
    raw = certificate.body.to_json()
    record["body_sha256"] = sha256_bytes(raw.encode("utf-8"))
    try:
        restored = OpaqueNativeBody.from_json(raw)
        candidate = opaque_body_to_dfa(restored, machine)
    except (ValueError, RecursionError) as exc:
        record["evaluation_error"] = f"{type(exc).__name__}:{exc}"
        return record
    record["exact"] = exact_equivalence(passport, candidate)[0]
    record["hidden_accuracy"] = suite.accuracy(candidate) if suite is not None else float(record["exact"])
    record["serialization_round_trip"] = restored == certificate.body
    record["native_components_external"] = unique_component_count(certificate.body)
    if audit_semantics:
        exact, details = semantic_audit(certificate, machine)
        record["semantic_exact_used"] = exact
        record["semantic_audit"] = details
    return record


def oracle_substrate(machine: OpaqueBooleanMachine) -> DiscoveredSubstrate:
    snapshot = machine._audit_snapshot()
    operations = tuple(
        DiscoveredOpcode(
            opcode=opcode,
            arity=int(data["arity"]),
            cost=int(data["cost"]),
            table=tuple(int(value) for value in data["table"]) if data["instability"] == "stable" else None,
            stable=data["instability"] == "stable",
        )
        for opcode, data in sorted(snapshot.items())
    )
    return DiscoveredSubstrate(
        operations,
        0,
        tuple(opcode.opcode for opcode in operations if not opcode.stable),
    )


def source_isolation_audit() -> dict[str, object]:
    public_paths = [
        ROOT / "metamorphosis" / "m013e_engine.py",
        ROOT / "metamorphosis" / "m013e_runtime.py",
    ]
    public_source = "\n".join(path.read_text(encoding="utf-8") for path in public_paths)
    tests_source = (ROOT / "tests" / "test_m013e.py").read_text(encoding="utf-8")
    workflow_source = (ROOT / ".github" / "workflows" / "m013e-sealed-evaluation.yml").read_text(encoding="utf-8")
    public_forbidden = [
        "_audit_truth_table",
        "_audit_snapshot",
        "_audit_stability",
        "make_positive_machine",
        "make_negative_machine",
        "master_nonce",
        "sealed_spec",
    ]
    test_forbidden = [
        "sealed_spec",
        "runtime_nonce",
        "run_m013e_evaluation",
        "master_nonce",
        "results/M013e",
    ]
    public_hits = [token for token in public_forbidden if token in public_source]
    test_hits = [token for token in test_forbidden if token in tests_source]
    requirements = {
        "pull_request_opened_only": "types: [opened]" in workflow_source,
        "artifact_upload": "actions/upload-artifact@v4" in workflow_source,
        "canonical_flag": "--canonical" in workflow_source,
    }
    runner_source = (ROOT / "scripts" / "m013e_eval_run.py").read_text(encoding="utf-8")
    return {
        "passed": not public_hits and not test_hits and all(requirements.values()),
        "public_forbidden_hits": public_hits,
        "test_forbidden_hits": test_hits,
        "workflow_requirements": requirements,
        "runtime_nonce_calls_in_runner": runner_source.count("runtime_nonce()"),
    }


def median(values: list[float | int]) -> float:
    return float(statistics.median(values)) if values else 0.0


def report(result: dict[str, object]) -> str:
    aggregate = result["aggregates"]
    criteria = result["acceptance_criteria"]
    assert isinstance(aggregate, dict)
    assert isinstance(criteria, dict)
    lines = [
        "# Mira Genesis — Metamorphosis 013e",
        "",
        f"Scientific status: **{result['status']}**.",
        "",
        "## Sealed unknown-substrate evaluation",
        "",
        "Inherited finite competences and opaque machines were generated from a fresh runtime nonce during the first PR-opened workflow run. Genesis received no task oracle or opcode map during migration.",
        "",
        "## Results",
        "",
        f"- exact principal migrations: **{aggregate['exact_principal_migrations']}/36**;",
        f"- exact executions: **{aggregate['exact_executions']}/108**;",
        f"- per machine: `{aggregate['per_machine_exact']}`;",
        f"- oracle ceiling: **{aggregate['oracle_ceiling_exact']}/36**;",
        f"- median probes: **{aggregate['median_probe_calls']:.1f}** / 120;",
        f"- maximum probes: **{aggregate['max_probe_calls']}** / 120;",
        f"- no-probe baseline: **{aggregate['no_probe_exact']}/36**;",
        f"- random-semantics baseline: **{aggregate['random_semantics_exact']}/36**;",
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
        "A success supports bounded discovery of stable Boolean opcode semantics and exact migration of an inherited finite competence to a runtime-sealed opaque machine. It does not establish adaptation to arbitrary continuous physics, memory transfer, or general plasticity.",
    ])
    return "\n".join(lines) + "\n"
