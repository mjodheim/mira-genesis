"""M109 orchestration - two successive machinery generations over a self-determined blame record.

Runs the H54 chronology across isolated processes and materializes the evidence P1-P18 are computed
from. The canonical entry point refuses unless a final protocol is frozen, HEAD is exactly the freeze
commit, the worktree is clean, the bound apparatus is unchanged and no evidence exists yet.

The curriculum boundary is enforced by capsule membership, not by convention: a stage-one capsule
holds the first staged demand and never the second, a stage-two capsule holds the second and never
the first, and a producer capsule holds neither. All three directions are measured and recorded.
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

from metamorphosis import m109_runtime as runtime  # noqa: E402

EXPERIMENT = ROOT / "experiments" / "M109"
STAGE1_PATH = EXPERIMENT / "DEMAND_STAGE1.json"
STAGE2_PATH = EXPERIMENT / "DEMAND_STAGE2.json"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
RESULT_PATH = EXPERIMENT / "RESULT.json"
CHECK_PATH = EXPERIMENT / "CHECK_REPORT.json"

CANONICAL_PYTHON = (3, 11, 16)
EXPECTED_PREDICATES = ["P%d" % index for index in range(1, 19)]
ISOLATED_PYTHON = Path(sys.executable).resolve()
DEEPER_BOUND = 13
REACH_BUDGET = 2

RUNTIME_SOURCES = {
    "m107_runtime.py": "metamorphosis/m107_runtime.py",
    "m108_runtime.py": "metamorphosis/m108_runtime.py",
    "m109_runtime.py": "metamorphosis/m109_runtime.py",
    "run.py": "scripts/run_m109_process.py",
}

EPHEMERAL_KEYS = {
    # M098 was negative because its frozen stable projection retained consumer PIDs. The derived
    # booleans carry the claim; the raw identifiers are pure process accident and must never enter a
    # replayed projection.
    "pid",
    "producer_pids",
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


def verify_inputs() -> dict[str, Any]:
    stage1 = _read_canonical(STAGE1_PATH, "M109 stage-one fixture")
    stage2 = _read_canonical(STAGE2_PATH, "M109 stage-two fixture")
    first = runtime.demand_target(stage1["demand"])
    second = runtime.demand_target(stage2["demand"])
    base = runtime.create_state()
    world = runtime.WORLD_SIGNAL_WIDTH
    checks = {
        "stage_one_schema": stage1.get("schema") == "m109-staged-demand-v1",
        "stage_two_schema": stage2.get("schema") == "m109-staged-demand-v1",
        "stages_are_ordered": stage1.get("stage") == 1
        and stage2.get("stage") == 2
        and stage2.get("revealed_after_stage") == 1,
        "registry_is_the_declared_triple": tuple(runtime.COMPONENTS)
        == (
            runtime.COMPONENT_OPERATORS,
            runtime.COMPONENT_SIGNALS,
            runtime.COMPONENT_CANDIDATES,
        ),
        "base_operators_are_the_monotone_fragment": sorted(
            item["name"] for item in base["operators"]
        )
        == ["AND", "OR"],
        "base_candidate_space_is_monotone": base["candidate_space"] == runtime.MONOTONE_SPACE,
        "base_holds_no_rule": not base["rules"],
        "stage_one_needs_the_unread_signal": runtime.depends_on_signal(first, world - 1),
        "stage_one_is_monotone": runtime.is_monotone(first, world),
        "stage_two_is_non_monotone": not runtime.is_monotone(second, world),
        "stages_are_distinct": first != second,
        "no_episode_fixture_exists": not (EXPERIMENT / "EPISODES.json").exists(),
    }
    return {
        "schema": "m109-input-preflight-v1",
        "confirmed": all(checks.values()),
        "checks": checks,
        "stage_one_digest": stage1.get("stage_digest"),
        "stage_two_digest": stage2.get("stage_digest"),
    }


def _build_capsule(base: Path, name: str, payloads: dict[str, bytes]) -> Path:
    capsule = base / name
    capsule.mkdir(parents=True)
    for destination, source in RUNTIME_SOURCES.items():
        shutil.copyfile(ROOT / source, capsule / destination)
    for filename, raw in payloads.items():
        (capsule / filename).write_bytes(raw)
    return capsule


def _run(capsule: Path, action: str, bound: int | None = None, budget: int | None = None) -> dict[str, Any]:
    command = [str(ISOLATED_PYTHON), "-I", "-S", str(capsule / "run.py"), "--action", action]
    if bound is not None:
        command += ["--bound", str(bound)]
    if budget is not None:
        command += ["--budget", str(budget)]
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
            "M109 capsule produced no parsable report: %s" % (completed.stderr[:400] or error)
        )
    report["returncode"] = completed.returncode
    report["capsule_members"] = sorted(item.name for item in capsule.iterdir())
    return report


def run_experiment() -> dict[str, Any]:
    preflight_report = verify_inputs()
    if not preflight_report["confirmed"]:
        raise QualificationRefused("M109 input preflight failed")

    stage1 = _read_canonical(STAGE1_PATH, "M109 stage-one fixture")
    stage2 = _read_canonical(STAGE2_PATH, "M109 stage-two fixture")
    stage1_bytes = canonical_json(stage1).encode("ascii")
    stage2_bytes = canonical_json(stage2).encode("ascii")

    s0 = runtime.create_state()
    s0_bytes = runtime.encode_state(s0)

    base = Path(tempfile.mkdtemp(prefix="m109-"))
    try:
        # ---- structural facts about the world, before any demand is posed ----------------
        domain_run = _run(_build_capsule(base, "domain", {}), "domain")
        if not domain_run.get("confirmed"):
            raise QualificationRefused("M109 attribution domain census failed")
        domain = domain_run["domain"]
        domain_bytes = canonical_json({"domain": domain}).encode("ascii")
        closure = _run(_build_capsule(base, "closure", {"STATE.json": s0_bytes}), "closure")
        image_m0 = _run(_build_capsule(base, "image-m0", {"STATE.json": s0_bytes}), "image")

        # ---- stage one: these capsules see the first demand and never the second ---------
        baseline = _run(
            _build_capsule(base, "baseline", {"STATE.json": s0_bytes, "DEMAND_STAGE1.json": stage1_bytes}),
            "resolve",
        )
        baseline_deeper = _run(
            _build_capsule(
                base, "baseline-deeper", {"STATE.json": s0_bytes, "DEMAND_STAGE1.json": stage1_bytes}
            ),
            "resolve",
            DEEPER_BOUND,
        )
        learn1 = _run(
            _build_capsule(base, "learn-1", {"STATE.json": s0_bytes, "DEMAND_STAGE1.json": stage1_bytes}),
            "episode",
        )
        if not learn1.get("confirmed"):
            raise QualificationRefused("M109 stage-one learning phase failed")
        episode1 = learn1["episode"]

        # ---- producer one: holds the trial record and the domain, and no demand at all ---
        episodes1_bytes = canonical_json({"episodes": [episode1]}).encode("ascii")
        producer1 = _run(
            _build_capsule(
                base,
                "producer-1",
                {"STATE.json": s0_bytes, "EPISODES.json": episodes1_bytes, "DOMAIN.json": domain_bytes},
            ),
            "acquire",
        )
        if not producer1.get("confirmed") or "next_state" not in producer1:
            raise QualificationRefused("M109 generation one did not adopt a rule")
        m1 = runtime.decode_state(producer1["next_state"])
        m1_bytes = runtime.encode_state(m1)

        stage1_resolved = _run(
            _build_capsule(base, "stage-1", {"STATE.json": m1_bytes, "DEMAND_STAGE1.json": stage1_bytes}),
            "resolve",
        )
        resolution1 = stage1_resolved.get("resolution") or {}
        if not resolution1.get("confirmed"):
            raise QualificationRefused("M109 stage one was never resolved; stage two stays sealed")

        # The first producer is gone. Stage two exists only because stage one was resolved.
        m1_after = runtime.create_state(
            m1["operators"],
            signal_width=resolution1["final_signal_width"],
            candidate_space=resolution1["final_candidate_space"],
            rules=m1["rules"],
        )
        m1_after_bytes = runtime.encode_state(m1_after)

        # ---- stage two: these capsules see the second demand and never the first --------
        stage2_unresolved = _run(
            _build_capsule(
                base, "stage-2-before", {"STATE.json": m1_after_bytes, "DEMAND_STAGE2.json": stage2_bytes}
            ),
            "resolve",
        )
        learn2 = _run(
            _build_capsule(
                base, "learn-2", {"STATE.json": m1_after_bytes, "DEMAND_STAGE2.json": stage2_bytes}
            ),
            "episode",
        )
        if not learn2.get("confirmed"):
            raise QualificationRefused("M109 stage-two learning phase failed")
        episode2 = learn2["episode"]

        episodes2_bytes = canonical_json({"episodes": [episode1, episode2]}).encode("ascii")
        producer2 = _run(
            _build_capsule(
                base,
                "producer-2",
                {
                    "STATE.json": m1_after_bytes,
                    "EPISODES.json": episodes2_bytes,
                    "DOMAIN.json": domain_bytes,
                },
            ),
            "acquire",
        )
        if not producer2.get("confirmed") or "next_state" not in producer2:
            raise QualificationRefused("M109 generation two did not adopt a rule")
        m2 = runtime.decode_state(producer2["next_state"])
        m2_bytes = runtime.encode_state(m2)

        stage2_resolved = _run(
            _build_capsule(base, "stage-2", {"STATE.json": m2_bytes, "DEMAND_STAGE2.json": stage2_bytes}),
            "resolve",
        )

        # ---- controls -------------------------------------------------------------------
        handed_bytes = canonical_json({"episodes": [episode2]}).encode("ascii")
        handed = _run(
            _build_capsule(
                base,
                "handed",
                {"STATE.json": s0_bytes, "EPISODES.json": handed_bytes, "DOMAIN.json": domain_bytes},
            ),
            "acquire_refuse_only",
        )
        conflated = _run(
            _build_capsule(
                base,
                "conflated",
                {"STATE.json": s0_bytes, "EPISODES.json": episodes2_bytes, "DOMAIN.json": domain_bytes},
            ),
            "acquire_refuse_only",
        )
        nothing_left = _run(
            _build_capsule(
                base,
                "nothing-left",
                {"STATE.json": m1_bytes, "EPISODES.json": episodes1_bytes, "DOMAIN.json": domain_bytes},
            ),
            "acquire_refuse_only",
        )

        ablated = runtime.create_state(
            m2["operators"],
            signal_width=m2["signal_width"],
            candidate_space=m2["candidate_space"],
            rules=m2["rules"][:-1],
        )
        ablation = _run(
            _build_capsule(
                base,
                "ablation",
                {"STATE.json": runtime.encode_state(ablated), "DEMAND_STAGE2.json": stage2_bytes},
            ),
            "resolve",
        )
        mutated_rule = copy.deepcopy(m2["rules"][-1])
        mutated = runtime.create_state(
            m2["operators"],
            signal_width=m2["signal_width"],
            candidate_space=m2["candidate_space"],
            rules=list(m2["rules"][:-1])
            + [
                runtime.attribution_rule(
                    mutated_rule["body"],
                    [not value for value in mutated_rule["truth_table"]],
                    mutated_rule["selects_component_when_true"],
                    mutated_rule["generation"],
                )
            ],
        )
        mutation = _run(
            _build_capsule(
                base,
                "mutation",
                {"STATE.json": runtime.encode_state(mutated), "DEMAND_STAGE2.json": stage2_bytes},
            ),
            "resolve",
        )
        corruption = _run(_build_capsule(base, "corruption", {"STATE.json": m2_bytes}), "corruption")

        reach = {}
        for label, payload in (("m0", s0_bytes), ("m1", m1_bytes), ("m2", m2_bytes)):
            reach[label] = _run(
                _build_capsule(base, "reach-" + label, {"STATE.json": payload}),
                "reach_improve",
                None,
                REACH_BUDGET,
            )

        producers = [producer1, producer2]
        stage_one_capsules = [baseline, baseline_deeper, learn1, stage1_resolved]
        stage_two_capsules = [stage2_unresolved, learn2, stage2_resolved, ablation, mutation]
        isolated = [
            domain_run,
            closure,
            image_m0,
            *stage_one_capsules,
            *producers,
            *stage_two_capsules,
            handed,
            conflated,
            nothing_left,
            corruption,
            *reach.values(),
        ]

        reach_sets = {label: set(item["reach_improve"]["tables"]) for label, item in reach.items()}
        evidence: dict[str, Any] = {
            "schema": "m109-evidence-v1",
            "input_preflight": preflight_report,
            "stage_one_digest": stage1["stage_digest"],
            "stage_two_digest": stage2["stage_digest"],
            "targets": {
                "stage_one": [bool(v) for v in runtime.demand_target(stage1["demand"])],
                "stage_two": [bool(v) for v in runtime.demand_target(stage2["demand"])],
            },
            "runtime": {
                "implementation": platform.python_implementation().lower(),
                "canonical_python": list(CANONICAL_PYTHON),
                "matches_canonical": tuple(sys.version_info[:3]) == CANONICAL_PYTHON,
            },
            "domain": domain,
            "closure": closure.get("closure"),
            "m0": {
                "operators": sorted(item["name"] for item in s0["operators"]),
                "signal_width": s0["signal_width"],
                "candidate_space": s0["candidate_space"],
                "generations": len(s0["rules"]),
                "state_digest": s0["state_digest"],
            },
            "image_m0": image_m0.get("image"),
            "baseline": {"bound": baseline.get("bound"), "resolution": baseline.get("resolution")},
            "baseline_deeper": {
                "bound": baseline_deeper.get("bound"),
                "resolution": baseline_deeper.get("resolution"),
            },
            "generation_one": {
                "episode": episode1,
                "acquisition": producer1.get("acquisition"),
                "state_digest": m1["state_digest"],
                "generations": len(m1["rules"]),
            },
            "stage_one_resolution": resolution1,
            "stage_two_before_generation_two": stage2_unresolved.get("resolution"),
            "generation_two": {
                "episode": episode2,
                "acquisition": producer2.get("acquisition"),
                "state_digest": m2["state_digest"],
                "generations": len(m2["rules"]),
            },
            "stage_two_resolution": stage2_resolved.get("resolution"),
            "handed_counterfactual": handed.get("acquisition"),
            "conflated_record": conflated.get("acquisition"),
            "exhausted_record": nothing_left.get("acquisition"),
            "ablation": ablation.get("resolution"),
            "mutation": mutation.get("resolution"),
            "corruption": corruption.get("corruption"),
            "rollback": {
                # Ablating generation two must return the lineage byte-exactly to the state it held
                # immediately before that acquisition -- which is M1 *after* stage one widened its
                # interface, not M1 as it was adopted.
                "ablated_matches_state_before_generation_two": runtime.encode_state(ablated)
                == m1_after_bytes,
                "state_before_generation_two_digest": m1_after["state_digest"],
                "ablated_digest": ablated["state_digest"],
                "ablated_generation_count": len(ablated["rules"]),
            },
            "reach_improve": {
                label: {
                    "size": item["reach_improve"]["size"],
                    "axes": item["reach_improve"]["axes"],
                    "budget": item["reach_improve"]["budget"],
                }
                for label, item in reach.items()
            },
            "reach_chain": {
                "m0_strictly_inside_m1": reach_sets["m0"] < reach_sets["m1"],
                "m1_strictly_inside_m2": reach_sets["m1"] < reach_sets["m2"],
                "strict_chain": reach_sets["m0"] < reach_sets["m1"] < reach_sets["m2"],
                "gained_by_generation_one": len(reach_sets["m1"] - reach_sets["m0"]),
                "gained_by_generation_two": len(reach_sets["m2"] - reach_sets["m1"]),
            },
            "curriculum_boundary": {
                "producer_capsules_hold_no_demand": all(
                    "DEMAND_STAGE1.json" not in item["capsule_members"]
                    and "DEMAND_STAGE2.json" not in item["capsule_members"]
                    for item in producers
                ),
                "stage_one_capsules_hold_only_the_first_demand": all(
                    "DEMAND_STAGE1.json" in item["capsule_members"]
                    and "DEMAND_STAGE2.json" not in item["capsule_members"]
                    for item in stage_one_capsules
                ),
                "stage_two_capsules_hold_only_the_second_demand": all(
                    "DEMAND_STAGE2.json" in item["capsule_members"]
                    and "DEMAND_STAGE1.json" not in item["capsule_members"]
                    for item in stage_two_capsules
                ),
            },
            "trial_provenance": {
                "labels_are_lineage_determined": all(
                    item["trial"]["label_source"] == "lineage_component_trial"
                    for item in (episode1, episode2)
                ),
                "no_trial_at_resolution_time": all(
                    (item.get("resolution") or {}).get("trials_performed") == 0
                    for item in (baseline, stage1_resolved, stage2_unresolved, stage2_resolved)
                ),
            },
            "process_boundary": {
                "producer_pids": [item["runtime"]["pid"] for item in producers],
                "later_pids": [item["runtime"]["pid"] for item in stage_two_capsules],
                "producer_pids_absent_from_later": not (
                    {item["runtime"]["pid"] for item in producers}
                    & {item["runtime"]["pid"] for item in stage_two_capsules}
                ),
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
        raise QualificationRefused("M109 final protocol is absent")
    protocol = _read_canonical(PROTOCOL_PATH, "M109 final protocol")
    payload = {key: value for key, value in protocol.items() if key != "protocol_digest"}
    if protocol.get("schema") != "m109-protocol-v1" or protocol.get("protocol_digest") != digest(
        payload
    ):
        raise QualificationRefused("M109 protocol schema or digest mismatch")
    if protocol.get("status") != "frozen_protocol_owner_authorized":
        raise QualificationRefused("M109 protocol is not owner-authorized")
    if protocol.get("decisive_conditions") != EXPECTED_PREDICATES:
        raise QualificationRefused("M109 decisive predicate declaration changed")
    if tuple(sys.version_info[:3]) != CANONICAL_PYTHON:
        raise QualificationRefused("M109 canonical runtime mismatch")
    bound = protocol.get("bound_files", {})
    files = bound.get("files")
    members = bound.get("member_digests")
    modes = bound.get("member_digest_modes") or {}
    if not isinstance(files, list) or not isinstance(members, dict):
        raise QualificationRefused("M109 bound-file record is invalid")
    measured = {}
    for path in files:
        raw = (ROOT / path).read_bytes()
        if modes.get(path) == "lf_normalized":
            raw = raw.replace(b"\r\n", b"\n")
        elif modes.get(path) != "raw":
            raise QualificationRefused("M109 bound-file digest mode is undeclared")
        measured[path] = sha256_bytes(raw)
    if measured != members or digest(measured) != bound.get("digest"):
        raise QualificationRefused("M109 bound apparatus changed")
    freeze_tag = protocol.get("freeze_tag")
    if not isinstance(freeze_tag, str) or _git("cat-file", "-t", freeze_tag) != "tag":
        raise QualificationRefused("M109 freeze reference is not an annotated tag")
    if _git("rev-list", "-n", "1", freeze_tag) != _git("rev-parse", "HEAD"):
        raise QualificationRefused("M109 HEAD is not the frozen tag commit")
    if _git("status", "--porcelain"):
        raise QualificationRefused("M109 canonical worktree is not clean")
    if RESULT_PATH.exists() or CHECK_PATH.exists():
        raise QualificationRefused("M109 canonical evidence path already exists")
    return protocol


def preflight() -> dict[str, Any]:
    inputs = verify_inputs()
    protocol = require_frozen()
    return {
        "schema": "m109-preflight-v1",
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
            "M109 owner authorization or unique-attempt acknowledgement absent"
        )
    protocol = require_frozen()
    evidence = run_experiment()
    result: dict[str, Any] = {
        "schema": "m109-result-v1",
        "milestone": "M109",
        "hypothesis": "H54",
        "attempt": 1,
        "protocol_digest": protocol["protocol_digest"],
        "stage_one_digest": evidence["stage_one_digest"],
        "stage_two_digest": evidence["stage_two_digest"],
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
                "schema": "m109-development-rehearsal-v1",
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
            "schema": "m109-qualification-refusal-v1",
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
