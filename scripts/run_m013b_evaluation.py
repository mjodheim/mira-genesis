from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis.core import exact_equivalence, random_minimal_dfa
from metamorphosis.opaque_machine_lab import make_negative_machine, make_positive_machine
from metamorphosis.unknown_substrate import (
    OpaqueNativeBody,
    UnknownSubstrateMigrator,
    discover_substrate,
    fixed_role_baseline,
    opaque_body_to_dfa,
    random_semantics_baseline,
)

PASSPORTS = [12011,12023,12037,12041,12049,12071,12073,12097,12101,12109,12113,12119]
MACHINES = [13011,13023,13037]
SEARCH = [17,31,59]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hidden_words(seed: int, count: int = 20_000):
    rng = random.Random(seed)
    return [tuple(rng.randrange(2) for _ in range(rng.randint(0,128))) for _ in range(count)]


def hidden_accuracy(left, right, words) -> float:
    return sum(left.accepts(word) == right.accepts(word) for word in words) / len(words)


def evaluate(git_commit: str, output: Path) -> dict:
    protocol = ROOT / "experiments/M013b/protocol.yaml"
    protocol_hash = digest(protocol)
    passports = {seed: random_minimal_dfa(random.Random(seed), 3, 8) for seed in PASSPORTS}
    main, no_probe, random_semantics, oracle = [], [], [], []

    for passport_seed, passport in passports.items():
        words = hidden_words(passport_seed + 913_000)
        for machine_seed in MACHINES:
            for search_seed in SEARCH:
                trace = {
                    "passport_seed": passport_seed,
                    "machine_seed": machine_seed,
                    "search_seed": search_seed,
                    "git_commit": git_commit,
                    "protocol_sha256": protocol_hash,
                }
                machine = make_positive_machine(machine_seed)
                cert = UnknownSubstrateMigrator().migrate(passport, machine, search_seed, trace)
                exact = roundtrip = used_tables_exact = False
                accuracy = 0.0
                if cert.body is not None:
                    restored = OpaqueNativeBody.from_json(cert.body.to_json())
                    candidate = opaque_body_to_dfa(restored, machine)
                    exact = exact_equivalence(passport, candidate)[0]
                    accuracy = hidden_accuracy(passport, candidate, words)
                    roundtrip = restored == cert.body
                    inferred = {op.opcode: op.table for op in cert.substrate.stable_opcodes}
                    audit = machine._audit_snapshot()
                    used_tables_exact = all(inferred[op] == tuple(audit[op]["table"]) for op in cert.used_opcodes)
                main.append({
                    **trace,
                    "status": cert.status,
                    "reason": cert.reason,
                    "probe_calls": cert.probe_calls,
                    "candidate_evaluations": cert.candidate_evaluations,
                    "native_components": cert.native_components,
                    "serialized_bytes": cert.serialized_bytes,
                    "exact": exact,
                    "hidden_accuracy": accuracy,
                    "serialization_round_trip": roundtrip,
                    "used_truth_tables_exact": used_tables_exact,
                })

                for bucket, supplied in (
                    (no_probe, fixed_role_baseline(make_positive_machine(machine_seed).describe())),
                    (random_semantics, random_semantics_baseline(make_positive_machine(machine_seed).describe(), search_seed)),
                    (oracle, discover_substrate(make_positive_machine(machine_seed))),
                ):
                    baseline_machine = make_positive_machine(machine_seed)
                    baseline = UnknownSubstrateMigrator().migrate(
                        passport, baseline_machine, search_seed, supplied_substrate=supplied
                    )
                    success = False
                    if baseline.body is not None:
                        try:
                            success = exact_equivalence(
                                passport, opaque_body_to_dfa(baseline.body, baseline_machine)
                            )[0]
                        except Exception:
                            success = False
                    bucket.append({**trace, "success": success})

    principal = []
    oracle_principal = []
    for passport_seed in PASSPORTS:
        for machine_seed in MACHINES:
            group = [r for r in main if r["passport_seed"] == passport_seed and r["machine_seed"] == machine_seed]
            principal.append({
                "passport_seed": passport_seed,
                "machine_seed": machine_seed,
                "exact": all(r["status"] == "success" and r["exact"] and r["hidden_accuracy"] == 1.0 and r["serialization_round_trip"] for r in group),
            })
            oracle_group = [r for r in oracle if r["passport_seed"] == passport_seed and r["machine_seed"] == machine_seed]
            oracle_principal.append(all(r["success"] for r in oracle_group))

    negatives = []
    fixed_passport = passports[PASSPORTS[0]]
    for index in range(12):
        cert = UnknownSubstrateMigrator().migrate(fixed_passport, make_negative_machine(index), 17)
        negatives.append({
            "index": index,
            "status": cert.status,
            "reason": cert.reason,
            "false_success": cert.body is not None,
            "probe_calls": cert.probe_calls,
        })

    exact = sum(item["exact"] for item in principal)
    per_machine = {seed: sum(item["exact"] for item in principal if item["machine_seed"] == seed) for seed in MACHINES}
    no_probe_successes = sum(item["success"] for item in no_probe)
    oracle_migrations = sum(oracle_principal)
    abstentions = sum(item["status"] == "abstained" and not item["false_success"] for item in negatives)
    false_successes = sum(item["false_success"] for item in negatives)

    criteria = {
        "exact_migrations_at_least_32_of_36": exact >= 32,
        "at_least_10_of_12_per_machine": all(value >= 10 for value in per_machine.values()),
        "exact_identification_of_all_used_stable_truth_tables": all(r["used_truth_tables_exact"] for r in main if r["status"] == "success"),
        "no_success_exceeds_120_probes": all(r["probe_calls"] <= 120 for r in main if r["status"] == "success"),
        "exact_equivalence_and_perfect_hidden_accuracy_for_all_successes": all(r["exact"] and r["hidden_accuracy"] == 1.0 for r in main if r["status"] == "success"),
        "no_probe_baseline_at_most_8_of_36": no_probe_successes <= 8,
        "within_two_exact_migrations_of_oracle_ceiling": exact >= oracle_migrations - 2,
        "correct_abstentions_at_least_10_of_12": abstentions >= 10,
        "zero_false_success_on_negative_controls": false_successes == 0,
        "complete_seed_commit_protocol_traceability": bool(git_commit) and all(r["git_commit"] == git_commit and r["protocol_sha256"] == protocol_hash for r in main),
    }
    result = {
        "experiment": "M013b",
        "status": "VALIDATED" if all(criteria.values()) else "FAILED",
        "git_commit": git_commit,
        "protocol_sha256": protocol_hash,
        "aggregates": {
            "exact_migrations": exact,
            "per_machine": per_machine,
            "median_probe_calls": statistics.median(r["probe_calls"] for r in main),
            "median_candidate_evaluations": statistics.median(r["candidate_evaluations"] for r in main),
            "no_probe_successes": no_probe_successes,
            "random_semantics_successes": sum(r["success"] for r in random_semantics),
            "oracle_principal_migrations": oracle_migrations,
            "correct_abstentions": abstentions,
            "false_successes": false_successes,
        },
        "criteria": criteria,
        "principal_migrations": principal,
        "main_runs": main,
        "negative_controls": negatives,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    report = ROOT / "results/M013b.md"
    report.write_text(
        "# Mira Genesis — Metamorphosis 013b\n\n"
        f"Scientific status: **{result['status']}**.\n\n"
        f"- exact migrations: **{exact}/36**;\n"
        f"- per machine: `{per_machine}`;\n"
        f"- median probes: **{result['aggregates']['median_probe_calls']}** / 120;\n"
        f"- oracle principal migrations: **{oracle_migrations}/36**;\n"
        f"- negative abstentions: **{abstentions}/12**;\n"
        f"- false successes: **{false_successes}**.\n\n"
        "## Pre-registered criteria\n\n" +
        "\n".join(f"- {'PASS' if value else 'FAIL'} — `{name}`" for name, value in criteria.items()) +
        "\n\n## Limit\n\nBounded Boolean opcode discovery only; no analogue, continuous, or open-ended hardware semantics.\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": result["status"], "aggregates": result["aggregates"], "criteria": criteria}, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--git-commit", required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "results/M013b.json")
    args = parser.parse_args()
    result = evaluate(args.git_commit, args.output)
    raise SystemExit(0 if result["status"] == "VALIDATED" else 1)
