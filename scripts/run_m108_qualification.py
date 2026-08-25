"""M108 orchestration - endogenous modification of the acquisition machinery.

Runs the H53 chronology across isolated processes and materializes the evidence P1-P16 are computed
from. The canonical entry point refuses unless a final protocol is frozen, HEAD is exactly the
freeze commit, the worktree is clean, the bound apparatus is unchanged and no evidence exists yet.

The information boundary is enforced by capsule membership, not by convention: the producer stage
receives the attribution episodes and never the later demand, and every later stage receives the
demand and never the episodes. Both directions are measured and recorded.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m107_runtime as m107  # noqa: E402
from metamorphosis import m108_runtime as runtime  # noqa: E402

EXPERIMENT = ROOT / "experiments" / "M108"
EPISODES_PATH = EXPERIMENT / "EPISODES.json"
DEMAND_PATH = EXPERIMENT / "DEMAND.json"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
RESULT_PATH = EXPERIMENT / "RESULT.json"
CHECK_PATH = EXPERIMENT / "CHECK_REPORT.json"

CANONICAL_PYTHON = (3, 11, 16)
EXPECTED_PREDICATES = ["P%d" % index for index in range(1, 17)]
ISOLATED_PYTHON = Path(sys.executable).resolve()
DEEPER_BOUND = 13

RUNTIME_SOURCES = {
    "m107_runtime.py": "metamorphosis/m107_runtime.py",
    "m108_runtime.py": "metamorphosis/m108_runtime.py",
    "run.py": "scripts/run_m108_process.py",
}

EPHEMERAL_KEYS = {
    # M098 was negative because its frozen stable projection retained consumer PIDs. The derived
    # boolean producer_pid_absent_from_later is stable and carries the claim; the raw identifiers
    # are pure process accident and must never enter a replayed projection.
    "pid",
    "producer_pid",
    "later_pids",
    "search_path",
    "python_executable",
    "elapsed_seconds",
    "stderr",
    "returncode",
    "capsule_only_path",
    "python_version",
}


class QualificationRefused(RuntimeError):
    """Raised when the canonical boundary is not satisfied."""


def canonical_json(value: Any) -> str:
    return runtime.canonical_json(value)


def digest(value: Any) -> str:
    return runtime.digest(value)


def sha256_bytes(raw: bytes) -> str:
    return runtime.sha256_bytes(raw)


def stable_projection(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: stable_projection(item)
            for key, item in sorted(value.items())
            if key not in EPHEMERAL_KEYS
        }
    if isinstance(value, list):
        return [stable_projection(item) for item in value]
    return value


def _read_canonical(path: Path, label: str) -> dict[str, Any]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("ascii"))
    if canonical_json(value).encode("ascii") != raw:
        raise QualificationRefused("%s is not canonical" % label)
    return value


def _episodes() -> dict[str, Any]:
    return _read_canonical(EPISODES_PATH, "M108 episodes fixture")


def _demand_fixture() -> dict[str, Any]:
    return _read_canonical(DEMAND_PATH, "M108 demand fixture")


def verify_inputs() -> dict[str, Any]:
    episodes = _episodes()
    fixture = _demand_fixture()
    target = runtime.demand_target(fixture["demand"])
    domain = runtime.attribution_domain()
    covered = {
        runtime.episode_feature_row(runtime.decode_episode(item))
        for item in episodes["episodes"]
    }
    subset = set(episodes["underdetermined_subset"])
    partial = {
        runtime.episode_feature_row(runtime.decode_episode(item))
        for item in episodes["episodes"]
        if item["episode_id"] in subset
    }
    m0_operators = [m107.decode_operator(item) for item in episodes["m0_operators"]]
    checks = {
        "episodes_schema": episodes.get("schema") == "m108-episodes-v1",
        "demand_schema": fixture.get("schema") == "m108-later-demand-v1",
        "registry_is_the_declared_pair": tuple(runtime.COMPONENTS)
        == (runtime.COMPONENT_OPERATORS, runtime.COMPONENT_SIGNALS),
        "m0_holds_the_m107_acquisition": any(
            item["name"].startswith("ACQUIRED_") for item in m0_operators
        ),
        "m0_operator_table_is_saturated_at_base_width": len(
            runtime.expression_image(m0_operators, runtime.BASE_SIGNAL_WIDTH)
        )
        == 2 ** (2 ** runtime.BASE_SIGNAL_WIDTH),
        "episodes_cover_the_attribution_domain": sorted(covered) == domain["rows"],
        "underdetermined_subset_leaves_a_row_uncovered": sorted(partial) != domain["rows"],
        "target_depends_on_the_unreadable_signal": runtime.depends_on_signal(
            target, runtime.WORLD_SIGNAL_WIDTH - 1
        ),
        "target_is_non_monotone": not runtime.is_monotone(target, runtime.WORLD_SIGNAL_WIDTH),
        "no_episode_carries_the_later_demand": all(
            runtime.demand_target(item["demand"]) != target for item in episodes["episodes"]
        ),
        "episode_blame_labels_are_in_the_registry": all(
            item["blamed_component"] in runtime.COMPONENTS for item in episodes["episodes"]
        ),
        "predecessor_fixture_is_not_bound_here": episodes["predecessor"]["bound_by_this_protocol"]
        is False,
    }
    return {
        "schema": "m108-input-preflight-v1",
        "confirmed": all(checks.values()),
        "checks": checks,
        "episodes_digest": episodes.get("episodes_digest"),
        "demand_fixture_digest": fixture.get("demand_fixture_digest"),
    }


def _build_capsule(base: Path, name: str, payloads: dict[str, bytes]) -> Path:
    capsule = base / name
    capsule.mkdir(parents=True)
    for destination, source in RUNTIME_SOURCES.items():
        shutil.copyfile(ROOT / source, capsule / destination)
    for filename, raw in payloads.items():
        (capsule / filename).write_bytes(raw)
    return capsule


def _capsule_members(capsule: Path) -> list[str]:
    return sorted(item.name for item in capsule.iterdir())


def _run(capsule: Path, action: str, bound: int | None = None) -> dict[str, Any]:
    command = [str(ISOLATED_PYTHON), "-I", "-S", str(capsule / "run.py"), "--action", action]
    if bound is not None:
        command += ["--bound", str(bound)]
    completed = subprocess.run(
        command,
        cwd=str(capsule),
        capture_output=True,
        text=True,
        env={"PATH": os.environ.get("PATH", ""), "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")},
    )
    try:
        report = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise QualificationRefused(
            "M108 capsule produced no parsable report: %s" % (completed.stderr[:400] or error)
        )
    report["returncode"] = completed.returncode
    report["capsule_members"] = _capsule_members(capsule)
    return report


def run_experiment() -> dict[str, Any]:
    preflight_report = verify_inputs()
    if not preflight_report["confirmed"]:
        raise QualificationRefused("M108 input preflight failed")

    episodes = _episodes()
    demand_fixture = _demand_fixture()
    target = runtime.demand_target(demand_fixture["demand"])
    episodes_bytes = canonical_json(episodes).encode("ascii")
    demand_bytes = canonical_json(demand_fixture).encode("ascii")

    m0 = runtime.create_state(episodes["m0_operators"], signal_width=runtime.BASE_SIGNAL_WIDTH)
    monotone = runtime.create_state(
        m107.initial_operators(), signal_width=runtime.BASE_SIGNAL_WIDTH
    )
    m0_bytes = runtime.encode_state(m0)
    monotone_bytes = runtime.encode_state(monotone)

    base = Path(tempfile.mkdtemp(prefix="m108-"))
    try:
        # ---- structural facts about the world, before any acquisition ------------------
        domain = _run(_build_capsule(base, "domain", {}), "domain")
        equivalence = _run(
            _build_capsule(base, "equivalence", {"STATE.json": m0_bytes}), "equivalence"
        )
        image_s0 = _run(_build_capsule(base, "image-s0", {"STATE.json": m0_bytes}), "image")

        # ---- the producer: sees the episodes, never the later demand -------------------
        partial_capsule = _build_capsule(
            base, "partial", {"STATE.json": m0_bytes, "EPISODES.json": episodes_bytes}
        )
        partial = _run(partial_capsule, "acquire_refuse_only")

        producer_capsule = _build_capsule(
            base, "producer", {"STATE.json": m0_bytes, "EPISODES.json": episodes_bytes}
        )
        producer = _run(producer_capsule, "acquire")
        if not producer.get("confirmed") or "next_state" not in producer:
            raise QualificationRefused("M108 producer did not adopt an attribution rule")

        control_capsule = _build_capsule(
            base, "monotone-control", {"STATE.json": monotone_bytes, "EPISODES.json": episodes_bytes}
        )
        monotone_control = _run(control_capsule, "acquire")

        # The producer process is gone. Everything after this point sees only serialized state.
        producer_pid = producer["runtime"]["pid"]
        s1 = runtime.decode_state(producer["next_state"])
        s1_bytes = runtime.encode_state(s1)

        ablated = runtime.create_state(
            s1["operators"], signal_width=s1["signal_width"], attribution=None
        )
        mutated_rule = copy.deepcopy(s1["attribution"])
        mutated = runtime.create_state(
            s1["operators"],
            signal_width=s1["signal_width"],
            attribution=runtime.attribution_rule(
                mutated_rule["body"], [not value for value in mutated_rule["truth_table"]]
            ),
        )

        # ---- later stages: see the demand, never the episodes --------------------------
        later: list[dict[str, Any]] = []
        image_s1 = _run(_build_capsule(base, "image-s1", {"STATE.json": s1_bytes}), "image")
        later.append(image_s1)
        exclusion = _run(
            _build_capsule(
                base, "exclusion", {"STATE.json": m0_bytes, "DEMAND.json": demand_bytes}
            ),
            "exclusion",
        )
        later.append(exclusion)
        consumer = _run(
            _build_capsule(base, "consumer", {"STATE.json": s1_bytes, "DEMAND.json": demand_bytes}),
            "resolve",
        )
        later.append(consumer)
        baseline = _run(
            _build_capsule(base, "baseline", {"STATE.json": m0_bytes, "DEMAND.json": demand_bytes}),
            "resolve",
        )
        later.append(baseline)
        baseline_deeper = _run(
            _build_capsule(
                base, "baseline-deeper", {"STATE.json": m0_bytes, "DEMAND.json": demand_bytes}
            ),
            "resolve",
            DEEPER_BOUND,
        )
        later.append(baseline_deeper)
        ablation = _run(
            _build_capsule(
                base,
                "ablation",
                {"STATE.json": runtime.encode_state(ablated), "DEMAND.json": demand_bytes},
            ),
            "resolve",
        )
        later.append(ablation)
        mutation = _run(
            _build_capsule(
                base,
                "mutation",
                {"STATE.json": runtime.encode_state(mutated), "DEMAND.json": demand_bytes},
            ),
            "resolve",
        )
        later.append(mutation)
        corruption = _run(
            _build_capsule(base, "corruption", {"STATE.json": s1_bytes}), "corruption"
        )
        later.append(corruption)

        producers = [partial, producer, monotone_control]
        isolated = [domain, equivalence, image_s0, *producers, *later]
        evidence: dict[str, Any] = {
            "schema": "m108-evidence-v1",
            "input_preflight": preflight_report,
            "episodes_digest": episodes["episodes_digest"],
            "demand_fixture_digest": demand_fixture["demand_fixture_digest"],
            "target": [bool(value) for value in target],
            "runtime": {
                "implementation": platform.python_implementation().lower(),
                "canonical_python": list(CANONICAL_PYTHON),
                "matches_canonical": tuple(sys.version_info[:3]) == CANONICAL_PYTHON,
            },
            "domain": domain.get("domain"),
            "equivalence": equivalence.get("equivalence"),
            "s0": {
                "operators": sorted(item["name"] for item in m0["operators"]),
                "signal_width": m0["signal_width"],
                "attribution_mode": runtime.attribute(m0, {"row_index": 0})["mode"],
                "state_digest": m0["state_digest"],
            },
            "image_s0": image_s0.get("image"),
            "image_s1": image_s1.get("image"),
            "partial_acquisition": partial.get("acquisition"),
            "partial_episode_rows": partial.get("episode_feature_rows"),
            "producer": {
                "acquisition": {
                    key: value
                    for key, value in (producer.get("acquisition") or {}).items()
                },
                "episode_rows": producer.get("episode_feature_rows"),
                "s1_state_digest": s1["state_digest"],
                "s1_attribution_mode": runtime.attribute(s1, {"row_index": 0})["mode"],
            },
            "monotone_control": monotone_control.get("acquisition"),
            "exclusion": {
                "structural": exclusion.get("structural"),
                "monotone": exclusion.get("monotone"),
                "reachable_once_both_generations_hold": exclusion.get(
                    "target_reachable_once_both_generations_hold"
                ),
            },
            "consumer": consumer.get("resolution"),
            "baseline": {
                "bound": baseline.get("bound"),
                "resolution": baseline.get("resolution"),
            },
            "baseline_deeper": {
                "bound": baseline_deeper.get("bound"),
                "resolution": baseline_deeper.get("resolution"),
            },
            "ablation": ablation.get("resolution"),
            "mutation": mutation.get("resolution"),
            "corruption": corruption.get("corruption"),
            "rollback": {
                "byte_exact": runtime.encode_state(ablated) == m0_bytes,
                "s0_digest": m0["state_digest"],
                "ablated_digest": ablated["state_digest"],
            },
            "information_boundary": {
                "producer_has_demand_file": "DEMAND.json" in producer["capsule_members"],
                "producer_has_episodes_file": "EPISODES.json" in producer["capsule_members"],
                "later_stages_have_episodes_file": any(
                    "EPISODES.json" in item["capsule_members"] for item in later
                ),
                "later_stages_have_demand_file": all(
                    "DEMAND.json" in item["capsule_members"]
                    for item in (exclusion, consumer, baseline, baseline_deeper, ablation, mutation)
                ),
            },
            "process_boundary": {
                "producer_pid": producer_pid,
                "later_pids": [item["runtime"]["pid"] for item in later],
                "producer_pid_absent_from_later": producer_pid
                not in {item["runtime"]["pid"] for item in later},
                "isolated_process_count": len(isolated),
                "all_processes_isolated": all(
                    item["runtime"]["capsule_only_path"]
                    and not item["runtime"]["imported_project_modules"]
                    for item in isolated
                ),
                "all_processes_zero_external_calls": all(
                    item["runtime"]["model_calls"] == 0
                    and item["runtime"]["network_calls"] == 0
                    and item["runtime"]["remote_execution_calls"] == 0
                    for item in isolated
                ),
            },
        }
        return evidence
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        raise QualificationRefused(completed.stderr.strip() or "git command failed")
    return completed.stdout.strip()


def require_frozen() -> dict[str, Any]:
    if not PROTOCOL_PATH.exists():
        raise QualificationRefused("M108 final protocol is absent")
    protocol = _read_canonical(PROTOCOL_PATH, "M108 final protocol")
    payload = {key: value for key, value in protocol.items() if key != "protocol_digest"}
    if protocol.get("schema") != "m108-protocol-v1" or protocol.get("protocol_digest") != digest(
        payload
    ):
        raise QualificationRefused("M108 protocol schema or digest mismatch")
    if protocol.get("status") != "frozen_protocol_owner_authorized":
        raise QualificationRefused("M108 protocol is not owner-authorized")
    if protocol.get("decisive_conditions") != EXPECTED_PREDICATES:
        raise QualificationRefused("M108 decisive predicate declaration changed")
    if tuple(sys.version_info[:3]) != CANONICAL_PYTHON:
        raise QualificationRefused("M108 canonical runtime mismatch")
    bound = protocol.get("bound_files", {})
    files = bound.get("files")
    members = bound.get("member_digests")
    if not isinstance(files, list) or not isinstance(members, dict):
        raise QualificationRefused("M108 bound-file record is invalid")
    # Text members are bound by LF-normalized content and JSON evidence by raw bytes; the mode is
    # recorded per member so a third party recomputes exactly what was frozen. See
    # scripts/build_m108_protocol.py for why M108 cannot pin bytes the way M107 did.
    modes = bound.get("member_digest_modes") or {}
    measured = {}
    for path in files:
        raw = (ROOT / path).read_bytes()
        if modes.get(path) == "lf_normalized":
            raw = raw.replace(b"\r\n", b"\n")
        elif modes.get(path) != "raw":
            raise QualificationRefused("M108 bound-file digest mode is undeclared")
        measured[path] = sha256_bytes(raw)
    if measured != members or digest(measured) != bound.get("digest"):
        raise QualificationRefused("M108 bound apparatus changed")
    freeze_tag = protocol.get("freeze_tag")
    if not isinstance(freeze_tag, str) or _git("cat-file", "-t", freeze_tag) != "tag":
        raise QualificationRefused("M108 freeze reference is not an annotated tag")
    if _git("rev-list", "-n", "1", freeze_tag) != _git("rev-parse", "HEAD"):
        raise QualificationRefused("M108 HEAD is not the frozen tag commit")
    if _git("status", "--porcelain"):
        raise QualificationRefused("M108 canonical worktree is not clean")
    if RESULT_PATH.exists() or CHECK_PATH.exists():
        raise QualificationRefused("M108 canonical evidence path already exists")
    return protocol


def preflight() -> dict[str, Any]:
    inputs = verify_inputs()
    protocol = require_frozen()
    return {
        "schema": "m108-preflight-v1",
        "confirmed": inputs["confirmed"],
        "inputs": inputs,
        "protocol_digest": protocol["protocol_digest"],
        "result_absent": not RESULT_PATH.exists(),
        "check_report_absent": not CHECK_PATH.exists(),
        "python": platform.python_version(),
    }


def materialize(*, authorized_by_owner: bool, understand_unique_attempt: bool) -> dict[str, Any]:
    if not authorized_by_owner or not understand_unique_attempt:
        raise QualificationRefused(
            "M108 owner authorization or unique-attempt acknowledgement absent"
        )
    protocol = require_frozen()
    evidence = run_experiment()
    result: dict[str, Any] = {
        "schema": "m108-result-v1",
        "milestone": "M108",
        "hypothesis": "H53",
        "attempt": 1,
        "protocol_digest": protocol["protocol_digest"],
        "episodes_digest": evidence["episodes_digest"],
        "demand_fixture_digest": evidence["demand_fixture_digest"],
        "scientific_evidence": evidence,
        "stable_evidence_digest": digest(stable_projection(evidence)),
        "model_calls": 0,
        "network_calls": 0,
        "remote_execution_calls": 0,
    }
    result["result_digest"] = digest(result)
    with RESULT_PATH.open("xb") as handle:
        handle.write(canonical_json(result).encode("ascii"))
    return {
        "materialized": True,
        "path": str(RESULT_PATH),
        "result_digest": result["result_digest"],
        "stable_evidence_digest": result["stable_evidence_digest"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("preflight")
    development = subparsers.add_parser("development")
    development.add_argument("--out")
    canonical = subparsers.add_parser("canonical")
    canonical.add_argument("--owner-authorized", action="store_true")
    canonical.add_argument("--understand-unique-attempt", action="store_true")
    arguments = parser.parse_args()
    try:
        if arguments.command == "preflight":
            report = preflight()
        elif arguments.command == "development":
            evidence = run_experiment()
            report = {
                "schema": "m108-development-rehearsal-v1",
                "confirmed": True,
                "stable_evidence_digest": digest(stable_projection(evidence)),
                "evidence": evidence,
            }
            if arguments.out:
                Path(arguments.out).write_bytes(canonical_json(report).encode("ascii"))
        else:
            report = materialize(
                authorized_by_owner=arguments.owner_authorized,
                understand_unique_attempt=arguments.understand_unique_attempt,
            )
    except Exception as error:  # noqa: BLE001 - the refusal is the observation
        report = {
            "schema": "m108-qualification-refusal-v1",
            "confirmed": False,
            "failed_closed": True,
            "error": "%s: %s" % (type(error).__name__, error),
        }
        print(json.dumps(report, sort_keys=True))
        return 3
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
