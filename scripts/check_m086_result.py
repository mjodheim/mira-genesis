"""Independently re-verify the preserved M086 result.

Checked unconditionally: the protocol bytes match, the bank replays, M0 is differentially equivalent
to M047's frozen mechanism, the starting mechanism's constructive image for the holdout is empty, the
evaluator and holdout are unreachable from the mutable mechanism, the frozen threshold recomputes from
the preserved arms, and the preserved digests recompute. The arms are re-derived live, because the
whole experiment runs in seconds.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m047_runtime_sandbox import run_body_in_sandbox  # noqa: E402
from metamorphosis.m047_search_diagnosis import diagnose_limiting_module  # noqa: E402
from metamorphosis.m047_search_templates import _candidate_sources  # noqa: E402
from metamorphosis.m047_software_body import SoftwareCase  # noqa: E402
from metamorphosis.m047_software_tools import founder_software_body  # noqa: E402
from metamorphosis.m086_evolvable_mechanism import (  # noqa: E402
    ARMS,
    META_PRIMITIVES,
    diagnose,
    generate,
    m0_mechanism,
)
from metamorphosis.m086_meta_lineage import (  # noqa: E402
    bank_commitment,
    enumerate_m0_image_on_holdout,
    evaluate,
    run_arm,
    starting_body,
)

BASE = ROOT / "experiments/M086"
MECHANISM = ROOT / "metamorphosis/m086_evolvable_mechanism.py"
LINEAGE = ROOT / "metamorphosis/m086_meta_lineage.py"
PROTOCOL_PATH = BASE / "PROTOCOL.json"
BANK_PATH = BASE / "BANK_COMMITMENT.json"
RESULT_PATH = BASE / "RESULT.json"

DIFFERENTIAL_PROBES = (
    ("unknown token", (SoftwareCase("p1", "plus 4 5", 9, "t"),)),
    ("missing route", (SoftwareCase("p2", "mean 1 2 3", 2.0, "t"),)),
    ("two stages", (
        SoftwareCase("p3", "plus 4 5", 9, "t"), SoftwareCase("p4", "mean 1 2 3", 2.0, "t"),
    )),
    ("two tokens", (
        SoftwareCase("p5", "plus 4 5", 9, "t"), SoftwareCase("p6", "times 3 4", 12, "t"),
    )),
    ("already passing", (SoftwareCase("p7", "add 2 3", 5, "t"),)),
)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def _fail(failures: list[str], condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def _differential_equivalence(failures: list[str]) -> int:
    """M0 must answer exactly as M047's frozen pair, or this experiment is about a new mechanism."""

    mechanism = m0_mechanism()
    checked = 0
    for body_label, body in (("starting", starting_body()), ("founder", founder_software_body())):
        for label, cases in DIFFERENTIAL_PROBES:
            executed = run_body_in_sandbox(body, cases, timeout_seconds=60.0)
            old = diagnose_limiting_module(executed.cases)
            new = diagnose(mechanism, executed.cases)
            old_modules = (old.module,) if old.module else ()
            _fail(
                failures, old_modules == new.modules,
                f"M0 diagnosis differs from M047 on {body_label}/{label}: "
                f"{old_modules} against {new.modules}",
            )
            old_sets = sorted(
                tuple(sorted(replacements.items()))
                for _, replacements in (_candidate_sources(body, old) if old.sufficient else ())
            )
            new_sets = sorted(
                tuple(sorted(replacements.items()))
                for _, replacements in generate(mechanism, body, new)
            )
            _fail(
                failures, old_sets == new_sets,
                f"M0 candidates differ from M047 on {body_label}/{label}: "
                f"{len(old_sets)} against {len(new_sets)}",
            )
            checked += 1
    return checked


def _leak_boundary(failures: list[str]) -> None:
    """The mutable mechanism must not be able to see the evaluator or the holdout.

    M069 is the recorded precedent: its candidate code executed in the process holding hidden cases
    and could return them through an admitted output path, and its positive qualification was
    withdrawn for it.
    """

    mechanism_source = MECHANISM.read_text(encoding="utf-8")
    tree = ast.parse(mechanism_source)
    imported = {
        node.module for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    _fail(
        failures, "metamorphosis.m086_meta_lineage" not in imported,
        "the mechanism module imports the lineage module, which holds the hidden cases",
    )
    for marker in ("HOLDOUT_HIDDEN", "HOLDOUT_PUBLIC", "solves(", "evaluate("):
        _fail(
            failures, marker not in mechanism_source,
            f"the mechanism module references {marker}, which is evaluator-side",
        )

    lineage_source = LINEAGE.read_text(encoding="utf-8")
    lineage_tree = ast.parse(lineage_source)

    def _function(name: str) -> ast.FunctionDef | None:
        return next(
            (
                node for node in ast.walk(lineage_tree)
                if isinstance(node, ast.FunctionDef) and node.name == name
            ),
            None,
        )

    # The meta-search may validate a disposable descendant against the limitation it is trying to
    # fix — the protocol requires exactly that. What it may never touch is the holdout, in either
    # its public or its hidden half.
    for name in ("meta_search", "run_cycle"):
        function = _function(name)
        if function is None:
            continue
        body = ast.unparse(function)
        for forbidden in ("HOLDOUT_HIDDEN", "HOLDOUT_PUBLIC"):
            _fail(
                failures, forbidden not in body,
                f"{name} names {forbidden}, so the holdout is not sealed from the search",
            )

    # The mechanism itself never evaluates anything, in either module.
    for name in ("generate", "diagnose"):
        function = _function(name)
        if function is None:
            continue
        body = ast.unparse(function)
        for forbidden in ("HOLDOUT_HIDDEN", "HOLDOUT_PUBLIC", "solves(", "run_body_in_sandbox"):
            _fail(
                failures, forbidden not in body,
                f"{name} can reach {forbidden}, so the mechanism can score itself",
            )

    # And the only cases the meta-search is ever handed are the development ones.
    run = _function("run_arm")
    if run is not None:
        calls = [
            node for node in ast.walk(run)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "meta_search"
        ]
        _fail(failures, bool(calls), "run_arm never calls meta_search")
        for call in calls:
            arguments = {ast.unparse(argument) for argument in call.args}
            _fail(
                failures, "DEVELOPMENT_PUBLIC" in arguments,
                "meta_search is called with cases other than the development limitation",
            )
            _fail(
                failures, not any("HOLDOUT" in argument for argument in arguments),
                "meta_search is called with holdout cases",
            )


def main() -> int:
    failures: list[str] = []
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    bound = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    preserved = json.loads(RESULT_PATH.read_text(encoding="utf-8"))

    _fail(
        failures,
        hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest() == preserved["protocol_commitment"],
        "protocol bytes no longer match the recorded commitment",
    )
    _fail(
        failures, bank_commitment() == bound["bank_digest"],
        "the replayed bank does not match the bound digest",
    )
    _fail(
        failures, starting_body().digest() == bound["starting_body_digest"],
        "the starting body changed after the bank was bound",
    )
    _fail(
        failures, m0_mechanism().digest() == bound["m0_mechanism_digest"],
        "the starting mechanism changed after the bank was bound",
    )
    _fail(
        failures, sorted(bound["meta_primitives"]) == sorted(META_PRIMITIVES),
        "the meta-primitive set changed after the bank was bound",
    )

    probes = _differential_equivalence(failures)
    _leak_boundary(failures)

    image = enumerate_m0_image_on_holdout()
    _fail(
        failures, image["candidate_count"] == 0,
        f"the starting mechanism can emit {image['candidate_count']} candidates for the holdout, "
        "so the control's failure is not structural",
    )
    _fail(
        failures,
        preserved["m0_constructive_image_on_holdout"]["candidate_count"] == image["candidate_count"],
        "the preserved constructive image does not re-derive",
    )

    arms = {arm: run_arm(arm).to_dict() for arm in ARMS}
    for arm in ARMS:
        for key in (
            "development_solved", "holdout_hidden_solved", "meta_transformations_adopted",
        ):
            _fail(
                failures, arms[arm][key] == preserved["arms"][arm][key],
                f"{arm}.{key} does not reproduce: {arms[arm][key]} against "
                f"{preserved['arms'][arm][key]}",
            )

    verdict = evaluate(arms, image)
    _fail(
        failures, (preserved["verdict"] == "positive") == verdict.positive,
        "the recomputed verdict disagrees with the preserved verdict",
    )
    _fail(
        failures, list(verdict.reasons) == preserved["failed_conditions"],
        "the recomputed failure list disagrees with the preserved one",
    )

    boundary = preserved["claim_boundary"]
    for key in (
        "agi_evidence", "open_ended_evolution", "arbitrary_self_improvement",
        "general_autonomy", "advances_any_generality_gate", "replaces_m085",
        "is_an_independent_reproduction",
    ):
        _fail(failures, boundary[key] is False, f"claim boundary weakened on {key}")

    _fail(
        failures,
        hashlib.sha256(_canonical({
            key: value for key, value in preserved.items() if key != "result_sha256"
        })).hexdigest() == preserved["result_sha256"],
        "preserved result digest does not recompute",
    )

    print(json.dumps({
        "schema": "m086-meta-lineage-check-v1",
        "bank_commitment": bound["bank_commitment"],
        "result_sha256": preserved["result_sha256"],
        "verdict": preserved["verdict"],
        "differential_probes_against_m047": probes,
        "m0_candidates_for_the_holdout": image["candidate_count"],
        "failures": failures,
        "ok": not failures,
    }, indent=2, sort_keys=True))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
