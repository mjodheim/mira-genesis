from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
import sys
from pathlib import Path
from typing import Callable

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis.core import DFA, exact_equivalence, random_minimal_dfa
from metamorphosis.morphogenesis import (
    GATE_GRAPH_CATALOG,
    QUANTIZED_RECURRENT_CATALOG,
    REGISTER_CATALOG,
    AutonomousMorphogenesisEngine,
    BirthCertificate,
    NativeBody,
    learn_cube_heritage,
    native_body_to_dfa,
)

EVALUATION_SEEDS = [12011, 12023, 12037, 12041, 12049, 12071, 12073, 12097, 12101, 12109, 12113, 12119]
SEARCH_SEEDS = [7, 19, 43]
DEVELOPMENT_SEEDS = list(range(11001, 11013))
CATALOGS = [REGISTER_CATALOG, GATE_GRAPH_CATALOG, QUANTIZED_RECURRENT_CATALOG]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def batch_accepts(dfa: DFA, words: list[tuple[int, ...]]) -> np.ndarray:
    transitions = np.asarray(dfa.transitions, dtype=np.int64)
    accepting = np.asarray(dfa.accepting, dtype=np.bool_)
    out = np.zeros(len(words), dtype=np.bool_)
    groups: dict[int, list[tuple[int, tuple[int, ...]]]] = {}
    for index, word in enumerate(words):
        groups.setdefault(len(word), []).append((index, word))
    for length, items in groups.items():
        state = np.full(len(items), dfa.initial, dtype=np.int64)
        if length:
            tokens = np.asarray([word for _, word in items], dtype=np.int64)
            for t in range(length):
                state = transitions[state, tokens[:, t]]
        values = accepting[state]
        for (index, _), value in zip(items, values.tolist()):
            out[index] = value
    return out


def hidden_words(seed: int, count: int = 20_000) -> list[tuple[int, ...]]:
    rng = random.Random(seed)
    return [tuple(rng.randrange(2) for _ in range(rng.randint(0, 128))) for _ in range(count)]


class HiddenSuite:
    def __init__(self, target: DFA, words: list[tuple[int, ...]]) -> None:
        self.words = words
        self.expected = batch_accepts(target, words)

    def accuracy(self, candidate: DFA) -> float:
        return float((self.expected == batch_accepts(candidate, self.words)).mean())


def cert_dict(cert: BirthCertificate, target: DFA, suite: HiddenSuite | None, full_external: bool = True) -> dict:
    data = {
        "status": cert.status,
        "reason": cert.reason,
        "behavioural_queries": cert.behavioural_queries,
        "candidate_evaluations": cert.candidate_evaluations,
        "native_components": cert.native_components,
        "serialized_bytes": cert.serialized_bytes,
        "elapsed_seconds": cert.elapsed_seconds,
        "discovery_rounds": cert.discovery_rounds,
        "counterexamples": cert.counterexamples,
        "inheritance_used": cert.inheritance_used,
        "trace": dict(cert.trace),
        "discovered_states": cert.discovered_dfa.n_states if cert.discovered_dfa else None,
        "discovery_exact": False,
        "native_exact": False,
        "hidden_accuracy": 0.0,
        "serialization_round_trip": False,
        "body_sha256": None,
    }
    if cert.discovered_dfa is not None:
        data["discovery_exact"] = exact_equivalence(target, cert.discovered_dfa)[0]
    if cert.body is not None:
        raw = cert.body.to_json()
        data["body_sha256"] = sha256_bytes(raw.encode("utf-8"))
        restored = NativeBody.from_json(raw)
        native_dfa = native_body_to_dfa(restored)
        data["native_exact"] = exact_equivalence(target, native_dfa)[0]
        if full_external and suite is not None:
            data["hidden_accuracy"] = suite.accuracy(native_dfa)
            data["serialization_round_trip"] = restored == cert.body
        else:
            data["hidden_accuracy"] = 1.0 if data["native_exact"] else 0.0
            data["serialization_round_trip"] = restored == cert.body
    return data


def inconsistent_oracle(trigger: tuple[int, ...]) -> Callable[[tuple[int, ...]], bool]:
    calls: dict[tuple[int, ...], int] = {}
    def oracle(word: tuple[int, ...]) -> bool:
        calls[word] = calls.get(word, 0) + 1
        base = (sum(word) % 2) == 1
        if word == trigger:
            return base if calls[word] % 2 else not base
        return base
    return oracle


def median(values):
    return float(statistics.median(values)) if values else 0.0


def source_audit() -> dict:
    source = (ROOT / "metamorphosis" / "morphogenesis.py").read_text(encoding="utf-8")
    forbidden = [
        "heterogeneous_organs",
        "compile_symbolic",
        "compile_graph",
        "compile_matrix",
        "compile_cellular",
        "M010",
    ]
    hits = [token for token in forbidden if token in source]
    return {"passed": not hits, "forbidden_hits": hits}


def run(git_commit: str, output: Path) -> dict:
    protocol_path = ROOT / "experiments" / "M012" / "protocol.yaml"
    protocol_hash = sha256_bytes(protocol_path.read_bytes())
    development = [random_minimal_dfa(random.Random(seed), 3, 8) for seed in DEVELOPMENT_SEEDS]
    heritage = learn_cube_heritage(
        development,
        {"development_seeds": DEVELOPMENT_SEEDS, "protocol_sha256": protocol_hash},
    )
    heritage_raw = heritage.to_json()
    heritage_path = output.parent / "m012_heritage.json"
    heritage_path.write_text(heritage_raw, encoding="utf-8")

    targets = {seed: random_minimal_dfa(random.Random(seed), 3, 8) for seed in EVALUATION_SEEDS}
    hidden = {seed: HiddenSuite(targets[seed], hidden_words(seed + 900_000)) for seed in EVALUATION_SEEDS}
    trace_base = {
        "git_commit": git_commit,
        "protocol_sha256": protocol_hash,
        "heritage_sha256": sha256_bytes(heritage_raw.encode("utf-8")),
    }

    main_runs = []
    b1_runs = []
    b2_runs = []
    for target_seed in EVALUATION_SEEDS:
        target = targets[target_seed]
        for catalog in CATALOGS:
            for search_seed in SEARCH_SEEDS:
                trace = {**trace_base, "target_seed": target_seed, "search_seed": search_seed, "catalog": catalog.name}
                main = AutonomousMorphogenesisEngine(catalog, heritage, search_seed).birth(target.accepts, trace)
                main_runs.append({**trace, **cert_dict(main, target, hidden[target_seed], True)})
                b1 = AutonomousMorphogenesisEngine(catalog, None, search_seed, random_search=True).birth(target.accepts, trace)
                b1_runs.append({**trace, **cert_dict(b1, target, None, False)})
                b2 = AutonomousMorphogenesisEngine(catalog, None, search_seed).birth(target.accepts, trace)
                b2_runs.append({**trace, **cert_dict(b2, target, None, False)})

    probes = [(), (0,), (1,), (0, 1), (1, 0), (1, 1, 0)]
    negative_runs = []
    for catalog_index, catalog in enumerate(CATALOGS):
        for local_index in range(4):
            trigger = probes[(catalog_index * 2 + local_index) % len(probes)]
            trace = {**trace_base, "negative_control": catalog_index * 4 + local_index, "catalog": catalog.name, "trigger": list(trigger)}
            cert = AutonomousMorphogenesisEngine(catalog, heritage, SEARCH_SEEDS[0]).birth(inconsistent_oracle(trigger), trace)
            negative_runs.append({
                **trace,
                "status": cert.status,
                "reason": cert.reason,
                "behavioural_queries": cert.behavioural_queries,
                "false_success": cert.body is not None,
            })

    principal = []
    for target_seed in EVALUATION_SEEDS:
        for catalog in CATALOGS:
            group = [r for r in main_runs if r["target_seed"] == target_seed and r["catalog"] == catalog.name]
            exact = all(r["status"] == "success" and r["native_exact"] and r["hidden_accuracy"] == 1.0 for r in group)
            principal.append({"target_seed": target_seed, "catalog": catalog.name, "exact": exact})

    exact_births = sum(p["exact"] for p in principal)
    per_catalog = {catalog.name: sum(p["exact"] for p in principal if p["catalog"] == catalog.name) for catalog in CATALOGS}
    main_evals = [r["candidate_evaluations"] for r in main_runs if r["status"] == "success"]
    b1_evals = [r["candidate_evaluations"] if r["status"] == "success" else 50_000 for r in b1_runs]
    b2_evals = [r["candidate_evaluations"] if r["status"] == "success" else 50_000 for r in b2_runs]
    main_successes = sum(r["status"] == "success" and r["native_exact"] for r in main_runs)
    b2_successes = sum(r["status"] == "success" and r["native_exact"] for r in b2_runs)
    correct_abstentions = sum(r["status"] == "abstained" and not r["false_success"] for r in negative_runs)
    false_successes = sum(r["false_success"] for r in negative_runs)
    audit = source_audit()

    criteria = {
        "exact_births_at_least_32_of_36": exact_births >= 32,
        "at_least_10_of_12_per_substrate": all(v >= 10 for v in per_catalog.values()),
        "perfect_hidden_accuracy_for_claimed_successes": all(r["hidden_accuracy"] == 1.0 for r in main_runs if r["status"] == "success"),
        "no_specialized_compiler_dependency": audit["passed"],
        "median_candidate_evaluations_at_least_5x_better_than_random": median(b1_evals) >= 5 * median(main_evals),
        "inheritance_improves_success_or_reduces_evaluations_by_30_percent": main_successes > b2_successes or median(main_evals) <= 0.7 * median(b2_evals),
        "correct_abstentions_at_least_10_of_12": correct_abstentions >= 10,
        "zero_false_success_on_impossible_controls": false_successes == 0,
        "serialization_round_trip_for_all_successes": all(r["serialization_round_trip"] for r in main_runs if r["status"] == "success"),
        "complete_seed_commit_and_protocol_hash_traceability": bool(git_commit) and all(r["git_commit"] == git_commit and r["protocol_sha256"] == protocol_hash for r in main_runs),
    }

    result = {
        "experiment": "M012",
        "status": "VALIDATED" if all(criteria.values()) else "FAILED",
        "git_commit": git_commit,
        "protocol_sha256": protocol_hash,
        "heritage_sha256": trace_base["heritage_sha256"],
        "development_seeds": DEVELOPMENT_SEEDS,
        "evaluation_seeds": EVALUATION_SEEDS,
        "search_seeds": SEARCH_SEEDS,
        "main_runs": main_runs,
        "baseline_random_runs": b1_runs,
        "baseline_no_heritage_runs": b2_runs,
        "negative_controls": negative_runs,
        "principal_births": principal,
        "aggregates": {
            "exact_births": exact_births,
            "per_catalog_exact_births": per_catalog,
            "main_successful_executions": main_successes,
            "b2_successful_executions": b2_successes,
            "median_main_candidate_evaluations": median(main_evals),
            "median_random_candidate_evaluations": median(b1_evals),
            "median_no_heritage_candidate_evaluations": median(b2_evals),
            "random_reduction_factor": median(b1_evals) / max(1.0, median(main_evals)),
            "inheritance_reduction_fraction": 1.0 - median(main_evals) / max(1.0, median(b2_evals)),
            "median_behavioural_queries": median([r["behavioural_queries"] for r in main_runs]),
            "max_native_components": max(r["native_components"] for r in main_runs),
            "correct_abstentions": correct_abstentions,
            "false_successes": false_successes,
            "source_audit": audit,
        },
        "acceptance_criteria": criteria,
        "all_criteria_passed": all(criteria.values()),
        "interpretation_limit": "Finite deterministic regular-language morphogenesis with human-declared Boolean primitives; not arbitrary substrate adaptation or AGI.",
    }
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    output.with_suffix(".md").write_text(report(result), encoding="utf-8")
    return result


def report(result: dict) -> str:
    a = result["aggregates"]
    lines = [
        "# Mira Genesis — Metamorphosis 012",
        "",
        f"Scientific status: **{result['status']}**.",
        "",
        "## Core results",
        "",
        f"- exact principal births: **{a['exact_births']}/36**;",
        f"- per catalogue: `{a['per_catalog_exact_births']}`;",
        f"- median behavioural queries: **{a['median_behavioural_queries']:.1f}** / 10,000;",
        f"- median candidate evaluations: **{a['median_main_candidate_evaluations']:.1f}**;",
        f"- random baseline median: **{a['median_random_candidate_evaluations']:.1f}** ({a['random_reduction_factor']:.2f}x);",
        f"- no-heritage median: **{a['median_no_heritage_candidate_evaluations']:.1f}** ({100*a['inheritance_reduction_fraction']:.1f}% reduction);",
        f"- maximum native components: **{a['max_native_components']}** / 256;",
        f"- negative controls correctly rejected: **{a['correct_abstentions']}/12**;",
        f"- false success certificates: **{a['false_successes']}**.",
        "",
        "## Pre-registered criteria",
        "",
    ]
    lines.extend(f"- {'PASS' if passed else 'FAIL'} — `{name}`" for name, passed in result["acceptance_criteria"].items())
    lines += [
        "",
        "## Interpretation",
        "",
        "The target DFA was never supplied to the morphogenesis engine. Behavioural states were reconstructed by active membership queries, then a single catalogue-driven Boolean synthesizer produced inspectable native bodies. The inherited artefact contains reusable cubes learned on development contracts and no evaluation transition table.",
        "",
        "This remains a bounded result on deterministic regular languages with human-declared Boolean primitives. It does not yet show discovery of an unknown substrate, portable memory, or portable learning dynamics.",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--git-commit", required=True)
    parser.add_argument("--output", default=str(ROOT / "results" / "M012.json"))
    args = parser.parse_args()
    result = run(args.git_commit, Path(args.output))
    print(report(result))


if __name__ == "__main__":
    main()
