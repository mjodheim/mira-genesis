from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import secrets
import statistics
import sys
from typing import Iterable

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis.m012b import (
    AutonomousMorphogenesisEngine,
    DFA,
    NativeBody,
    derive_runtime_seeds,
    evaluation_catalogs,
    exact_equivalence,
    insufficient_catalog,
    native_body_to_dfa,
    random_minimal_dfa,
    synthesize_native_body,
    unique_component_count,
)

TARGET_COUNT = 12
SEARCH_REPETITIONS = 3
HIDDEN_WORDS_PER_SUCCESS = 10_000


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hidden_words(seed: int, count: int = HIDDEN_WORDS_PER_SUCCESS) -> list[tuple[int, ...]]:
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
        actual = batch_accepts(candidate, self.words)
        return float((actual == self.expected).mean())


def evaluate_body(target: DFA, body: NativeBody, suite: HiddenSuite) -> dict[str, object]:
    raw = body.to_json()
    restored = NativeBody.from_json(raw)
    candidate = native_body_to_dfa(restored)
    exact, counterexample = exact_equivalence(target, candidate)
    accuracy = suite.accuracy(candidate)
    return {
        "exact": exact,
        "counterexample": list(counterexample) if counterexample is not None else None,
        "hidden_accuracy": accuracy,
        "serialization_round_trip": restored == body,
        "body_sha256": sha256_bytes(raw.encode("utf-8")),
        "native_components_external": unique_component_count(body),
    }


def unstable_oracle(target: DFA, trigger: tuple[int, ...]):
    calls: dict[tuple[int, ...], int] = {}

    def oracle(word: tuple[int, ...]) -> bool:
        calls[word] = calls.get(word, 0) + 1
        value = target.accepts(word)
        if word == trigger:
            return value if calls[word] % 2 else not value
        return value

    return oracle


def source_isolation_audit() -> dict[str, object]:
    engine_source = "\n".join(path.read_text(encoding="utf-8") for path in sorted((ROOT / "metamorphosis").glob("m012b*.py")))
    tests_source = (ROOT / "tests" / "test_m012b.py").read_text(encoding="utf-8")
    workflow_source = (ROOT / ".github" / "workflows" / "m012b-sealed-evaluation.yml").read_text(encoding="utf-8")

    engine_forbidden = [
        "if catalog.catalog_id",
        "if catalog_id",
        "register_logic\":",
        "nand_fabric\":",
        "nor_fabric\":",
        "__closure__",
        "inspect.getclosurevars",
    ]
    test_forbidden = [
        "derive_runtime_seeds",
        "run_m012b_evaluation",
        "token_hex(",
        "master_nonce",
        "results/M012b",
    ]
    engine_hits = [token for token in engine_forbidden if token in engine_source]
    test_hits = [token for token in test_forbidden if token in tests_source]
    workflow_requirements = {
        "pull_request_opened_only": "types: [opened]" in workflow_source,
        "artifact_upload": "actions/upload-artifact@v4" in workflow_source,
        "canonical_flag": "--canonical" in workflow_source,
    }
    return {
        "passed": not engine_hits and not test_hits and all(workflow_requirements.values()),
        "engine_forbidden_hits": engine_hits,
        "test_forbidden_hits": test_hits,
        "workflow_requirements": workflow_requirements,
        "runtime_nonce_calls_in_runner": (ROOT / "scripts" / "m012b_eval_run.py").read_text(encoding="utf-8").count("secrets." + "token_hex(32)"),
    }


def median(values: list[float | int]) -> float:
    return float(statistics.median(values)) if values else 0.0


def report(result: dict[str, object]) -> str:
    aggregate = result["aggregates"]
    assert isinstance(aggregate, dict)
    criteria = result["acceptance_criteria"]
    assert isinstance(criteria, dict)
    lines = [
        "# Mira Genesis — Metamorphosis 012b",
        "",
        f"Scientific status: **{result['status']}**.",
        "",
        "## Sealed evaluation",
        "",
        "Evaluation targets were generated from a fresh cryptographic nonce during the first GitHub Actions run opened for this pull request. No evaluation seed existed in the repository or test suite before that run.",
        "",
        "## Results",
        "",
        f"- exact principal births: **{aggregate['exact_principal_births']}/36**;",
        f"- exact executions: **{aggregate['exact_executions']}/108**;",
        f"- per catalogue: `{aggregate['per_catalog_exact']}`;",
        f"- oracle ceiling: **{aggregate['oracle_ceiling_exact']}/36**;",
        f"- median behavioural queries: **{aggregate['median_behavioural_queries']:.1f}** / 20,000;",
        f"- maximum behavioural queries: **{aggregate['max_behavioural_queries']}** / 20,000;",
        f"- maximum native components: **{aggregate['max_native_components']}** / 256;",
        f"- correct negative abstentions: **{aggregate['correct_negative_abstentions']}/12**;",
        f"- false negative successes: **{aggregate['false_negative_successes']}**.",
        "",
        "## Pre-registered criteria",
        "",
    ]
    lines.extend(
        f"- {'PASS' if passed else 'FAIL'} — `{name}`"
        for name, passed in criteria.items()
    )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "A success supports autonomous finite body construction from an opaque behavioural contract and a declarative primitive catalogue, without a catalogue-specific compiler. It does not establish unknown-substrate learning, autobiographical continuity, or open-ended intelligence.",
        ]
    )
    return "\n".join(lines) + "\n"


