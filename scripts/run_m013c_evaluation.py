from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis.core import DFA, exact_equivalence, random_minimal_dfa
from metamorphosis.opaque_machine_lab import make_negative_machine, make_positive_machine
from metamorphosis.unknown_substrate import (
    DiscoveredOpcode,
    DiscoveredSubstrate,
    OpaqueNativeBody,
    UnknownSubstrateMigrator,
    fixed_role_baseline,
    opaque_body_to_dfa,
    random_semantics_baseline,
)

PASSPORT_SEEDS = [14211, 14217, 14229, 14241, 14249, 14259, 14267, 14291, 14309, 14313, 14327, 14331]
MACHINE_SEEDS = [14411, 14423, 14437]
SEARCH_SEEDS = [107, 127, 149]
NEGATIVE_INDICES = list(range(12))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hidden_words(seed: int, count: int = 20_000) -> list[tuple[int, ...]]:
    rng = random.Random(seed)
    return [tuple(rng.randrange(2) for _ in range(rng.randint(0, 128))) for _ in range(count)]


def batch_accepts(dfa: DFA, words: list[tuple[int, ...]]) -> np.ndarray:
    transitions = np.asarray(dfa.transitions, dtype=np.int64)
    accepting = np.asarray(dfa.accepting, dtype=np.bool_)
    out = np.zeros(len(words), dtype=np.bool_)
    by_length: dict[int, list[tuple[int, tuple[int, ...]]]] = {}
    for index, word in enumerate(words):
        by_length.setdefault(len(word), []).append((index, word))
    for length, items in by_length.items():
        states = np.full(len(items), dfa.initial, dtype=np.int64)
        if length:
            tokens = np.asarray([word for _, word in items], dtype=np.int64)
            for step in range(length):
                states = transitions[states, tokens[:, step]]
        values = accepting[states]
        for (index, _), value in zip(items, values.tolist()):
            out[index] = value
    return out


class HiddenSuite:
    def __init__(self, target: DFA, words: list[tuple[int, ...]]) -> None:
        self.words = words
        self.expected = batch_accepts(target, words)

    def accuracy(self, candidate: DFA) -> float:
        return float((self.expected == batch_accepts(candidate, self.words)).mean())


def oracle_substrate(machine) -> DiscoveredSubstrate:
    snapshot = machine._audit_snapshot()
    operations = tuple(
        DiscoveredOpcode(
            opcode=opcode,
            arity=int(data["arity"]),
            cost=int(data["cost"]),
            table=tuple(int(x) for x in data["table"]),
            stable=data["instability"] == "stable",
        )
        for opcode, data in sorted(snapshot.items())
    )
    unstable = tuple(op.opcode for op in operations if not op.stable)
    operations = tuple(
        DiscoveredOpcode(op.opcode, op.arity, op.cost, op.table if op.stable else None, op.stable)
        for op in operations
    )
    return DiscoveredSubstrate(operations, 0, unstable)


def semantic_audit(cert, machine) -> tuple[bool, dict[str, bool]]:
    discovered = {op.opcode: op for op in cert.substrate.opcodes}
    per_opcode: dict[str, bool] = {}
    for opcode in cert.used_opcodes:
        op = discovered.get(opcode)
        per_opcode[opcode] = bool(
            op is not None
            and op.stable
            and op.table == tuple(machine._audit_truth_table(opcode))
            and machine._audit_stability(opcode) == "stable"
        )
    return all(per_opcode.values()), per_opcode


def evaluate_certificate(cert, passport: DFA, machine, suite: HiddenSuite | None) -> dict:
    record = {
        "status": cert.status,
        "reason": cert.reason,
        "probe_calls": cert.probe_calls,
        "candidate_evaluations": cert.candidate_evaluations,
        "native_components": cert.native_components,
        "serialized_bytes": cert.serialized_bytes,
        "elapsed_seconds": cert.elapsed_seconds,
        "used_opcodes": list(cert.used_opcodes),
        "trace": dict(cert.trace),
        "exact": False,
        "hidden_accuracy": 0.0,
        "serialization_round_trip": False,
        "semantic_exact_used": False,
        "semantic_audit": {},
        "body_sha256": None,
    }
    if cert.body is None:
        return record
    raw = cert.body.to_json()
    record["body_sha256"] = sha256_bytes(raw.encode("utf-8"))
    restored = OpaqueNativeBody.from_json(raw)
    candidate = opaque_body_to_dfa(restored, machine)
    record["exact"] = exact_equivalence(passport, candidate)[0]
    record["hidden_accuracy"] = suite.accuracy(candidate) if suite is not None else float(record["exact"])
    record["serialization_round_trip"] = restored == cert.body
    semantic_exact, audit = semantic_audit(cert, machine)
    record["semantic_exact_used"] = semantic_exact
    record["semantic_audit"] = audit
    return record


def median(values) -> float:
    return float(statistics.median(values)) if values else 0.0


def source_audit() -> dict:
    source = (ROOT / "metamorphosis" / "unknown_substrate.py").read_text(encoding="utf-8")
    forbidden = [
        "_audit_truth_table",
        "_audit_snapshot",
        "_audit_stability",
        "14411",
        "14423",
        "14437",
        "14500",
        "heterogeneous_organs",
        "compile_symbolic",
        "compile_graph",
        "compile_matrix",
        "compile_cellular",
    ]
    hits = [token for token in forbidden if token in source]
    return {"passed": not hits, "forbidden_hits": hits}


def run(git_commit: str, output: Path) -> dict:
    protocol_path = ROOT / "experiments" / "M013c" / "protocol.yaml"
    protocol_hash = sha256_bytes(protocol_path.read_bytes())
    passports = {seed: random_minimal_dfa(random.Random(seed), 3, 8) for seed in PASSPORT_SEEDS}
    suites = {seed: HiddenSuite(passports[seed], hidden_words(seed + 1_400_000)) for seed in PASSPORT_SEEDS}
    migrator = UnknownSubstrateMigrator()
    trace_base = {"git_commit": git_commit, "protocol_sha256": protocol_hash}

    main_runs = []
    oracle_runs = []
    for passport_seed in PASSPORT_SEEDS:
        passport = passports[passport_seed]
        for machine_seed in MACHINE_SEEDS:
            for search_seed in SEARCH_SEEDS:
                trace = {
                    **trace_base,
                    "passport_seed": passport_seed,
                    "machine_seed": machine_seed,
                    "search_seed": search_seed,
                }
                machine = make_positive_machine(machine_seed)
                cert = migrator.migrate(passport, machine, search_seed, trace)
                main_runs.append({**trace, **evaluate_certificate(cert, passport, machine, suites[passport_seed])})

                oracle_machine = make_positive_machine(machine_seed)
                oracle_cert = migrator.migrate(
                    passport,
                    oracle_machine,
                    search_seed,
                    trace,
                    supplied_substrate=oracle_substrate(oracle_machine),
                )
                oracle_runs.append({**trace, **evaluate_certificate(oracle_cert, passport, oracle_machine, None)})

    no_probe_runs = []
    random_runs = []
    for passport_seed in PASSPORT_SEEDS:
        passport = passports[passport_seed]
        for machine_seed in MACHINE_SEEDS:
            trace = {
                **trace_base,
                "passport_seed": passport_seed,
                "machine_seed": machine_seed,
                "search_seed": SEARCH_SEEDS[0],
            }
            fixed_machine = make_positive_machine(machine_seed)
            fixed_cert = migrator.migrate(
                passport,
                fixed_machine,
                SEARCH_SEEDS[0],
                trace,
                supplied_substrate=fixed_role_baseline(fixed_machine.describe()),
            )
            no_probe_runs.append({**trace, **evaluate_certificate(fixed_cert, passport, fixed_machine, None)})

            random_machine = make_positive_machine(machine_seed)
            random_cert = migrator.migrate(
                passport,
                random_machine,
                SEARCH_SEEDS[0],
                trace,
                supplied_substrate=random_semantics_baseline(
                    random_machine.describe(), passport_seed ^ machine_seed
                ),
            )
            random_runs.append({**trace, **evaluate_certificate(random_cert, passport, random_machine, None)})

    negative_runs = []
    negative_passport = passports[PASSPORT_SEEDS[0]]
    for index in NEGATIVE_INDICES:
        machine = make_negative_machine(index)
        trace = {
            **trace_base,
            "negative_machine_seed": 14500 + index,
            "passport_seed": PASSPORT_SEEDS[0],
            "search_seed": SEARCH_SEEDS[0],
        }
        cert = migrator.migrate(negative_passport, machine, SEARCH_SEEDS[0], trace)
        record = {**trace, **evaluate_certificate(cert, negative_passport, machine, None)}
        record["false_success"] = bool(record["status"] == "success" and record["exact"])
        negative_runs.append(record)

    principal = []
    for passport_seed in PASSPORT_SEEDS:
        for machine_seed in MACHINE_SEEDS:
            group = [
                row for row in main_runs
                if row["passport_seed"] == passport_seed and row["machine_seed"] == machine_seed
            ]
            exact = all(
                row["status"] == "success"
                and row["exact"]
                and row["hidden_accuracy"] == 1.0
                and row["serialization_round_trip"]
                and row["semantic_exact_used"]
                for row in group
            )
            principal.append({"passport_seed": passport_seed, "machine_seed": machine_seed, "exact": exact})

    oracle_principal = []
    for passport_seed in PASSPORT_SEEDS:
        for machine_seed in MACHINE_SEEDS:
            group = [
                row for row in oracle_runs
                if row["passport_seed"] == passport_seed and row["machine_seed"] == machine_seed
            ]
            oracle_principal.append({
                "passport_seed": passport_seed,
                "machine_seed": machine_seed,
                "exact": all(row["status"] == "success" and row["exact"] for row in group),
            })

    exact_migrations = sum(row["exact"] for row in principal)
    oracle_exact = sum(row["exact"] for row in oracle_principal)
    per_machine = {
        str(machine_seed): sum(
            row["exact"] for row in principal if row["machine_seed"] == machine_seed
        )
        for machine_seed in MACHINE_SEEDS
    }
    no_probe_exact = sum(row["status"] == "success" and row["exact"] for row in no_probe_runs)
    random_exact = sum(row["status"] == "success" and row["exact"] for row in random_runs)
    correct_abstentions = sum(row["status"] == "abstained" for row in negative_runs)
    false_successes = sum(row["false_success"] for row in negative_runs)
    audit = source_audit()

    criteria = {
        "exact_migrations_at_least_32_of_36": exact_migrations >= 32,
        "at_least_10_of_12_per_machine": all(value >= 10 for value in per_machine.values()),
        "exact_identification_of_all_used_stable_truth_tables": all(
            row["semantic_exact_used"] for row in main_runs if row["status"] == "success"
        ),
        "no_success_exceeds_120_probes": all(
            row["probe_calls"] <= 120 for row in main_runs if row["status"] == "success"
        ),
        "exact_equivalence_and_perfect_hidden_accuracy_for_all_successes": all(
            row["exact"] and row["hidden_accuracy"] == 1.0
            for row in main_runs if row["status"] == "success"
        ),
        "no_probe_baseline_at_most_8_of_36": no_probe_exact <= 8,
        "within_two_exact_migrations_of_oracle_ceiling": exact_migrations >= oracle_exact - 2,
        "correct_abstentions_at_least_10_of_12": correct_abstentions >= 10,
        "zero_false_success_on_negative_controls": false_successes == 0,
        "complete_seed_commit_protocol_traceability": bool(git_commit)
        and audit["passed"]
        and all(
            row["git_commit"] == git_commit and row["protocol_sha256"] == protocol_hash
            for row in main_runs
        ),
    }

    result = {
        "experiment": "M013c",
        "status": "VALIDATED" if all(criteria.values()) else "FAILED",
        "git_commit": git_commit,
        "protocol_sha256": protocol_hash,
        "passport_seeds": PASSPORT_SEEDS,
        "machine_seeds": MACHINE_SEEDS,
        "search_seeds": SEARCH_SEEDS,
        "main_runs": main_runs,
        "oracle_runs": oracle_runs,
        "no_probe_runs": no_probe_runs,
        "random_semantics_runs": random_runs,
        "negative_controls": negative_runs,
        "principal_migrations": principal,
        "oracle_principal_migrations": oracle_principal,
        "aggregates": {
            "exact_migrations": exact_migrations,
            "oracle_exact_migrations": oracle_exact,
            "per_machine_exact": per_machine,
            "no_probe_exact": no_probe_exact,
            "random_semantics_exact": random_exact,
            "correct_abstentions": correct_abstentions,
            "false_successes": false_successes,
            "median_probe_calls": median([row["probe_calls"] for row in main_runs]),
            "max_probe_calls": max(row["probe_calls"] for row in main_runs),
            "median_candidate_evaluations": median([row["candidate_evaluations"] for row in main_runs]),
            "max_native_components": max(row["native_components"] for row in main_runs),
            "source_audit": audit,
        },
        "acceptance_criteria": criteria,
        "all_criteria_passed": all(criteria.values()),
        "interpretation_limit": "Opaque finite Boolean opcode discovery; not general adaptation to continuous or physical substrates.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    output.with_suffix(".md").write_text(report(result), encoding="utf-8")
    return result


def report(result: dict) -> str:
    a = result["aggregates"]
    lines = [
        "# Mira Genesis — Metamorphosis 013c",
        "",
        f"Scientific status: **{result['status']}**.",
        "",
        "## Results",
        "",
        f"- exact principal migrations: **{a['exact_migrations']}/36**;",
        f"- oracle ceiling: **{a['oracle_exact_migrations']}/36**;",
        f"- per machine: `{a['per_machine_exact']}`;",
        f"- median substrate probes: **{a['median_probe_calls']:.1f}** / 120;",
        f"- maximum substrate probes: **{a['max_probe_calls']}** / 120;",
        f"- median candidate evaluations: **{a['median_candidate_evaluations']:.1f}**;",
        f"- no-probe baseline: **{a['no_probe_exact']}/36**;",
        f"- random-semantics baseline: **{a['random_semantics_exact']}/36**;",
        f"- correct negative abstentions: **{a['correct_abstentions']}/12**;",
        f"- false negative-control successes: **{a['false_successes']}**;",
        f"- maximum native components: **{a['max_native_components']}** / 320.",
        "",
        "## Pre-registered criteria",
        "",
    ]
    lines.extend(
        f"- {'PASS' if passed else 'FAIL'} — `{name}`"
        for name, passed in result["acceptance_criteria"].items()
    )
    lines += [
        "",
        "## Interpretation",
        "",
        "Genesis received an inherited finite passport and a machine exposing only opaque opcode identifiers, arities, costs, probes and execution. It inferred stable truth tables, synthesized a native opcode body, and the evaluator reconstructed the competence solely through native execution.",
        "",
        "The result remains bounded to finite Boolean operations. Portable learning dynamics and memory are not tested here and remain the objective of M014 and M015.",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--git-commit", required=True)
    parser.add_argument("--output", default=str(ROOT / "results" / "M013c.json"))
    args = parser.parse_args()
    result = run(args.git_commit, Path(args.output))
    print(report(result))


if __name__ == "__main__":
    main()
