"""M107 orchestration - endogenous extension of the lower interpreter.

Runs the H52 chronology across isolated processes and materializes the evidence P1-P16 are computed
from. The canonical entry point refuses unless a final protocol is frozen, HEAD is exactly the
freeze commit, the worktree is clean, the bound apparatus is unchanged and no evidence exists yet.
"""

from __future__ import annotations

import argparse
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

from metamorphosis import m107_runtime as runtime  # noqa: E402

EXPERIMENT = ROOT / "experiments" / "M107"
DEMANDS_PATH = EXPERIMENT / "DEMANDS.json"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
RESULT_PATH = EXPERIMENT / "RESULT.json"
CHECK_PATH = EXPERIMENT / "CHECK_REPORT.json"

CANONICAL_PYTHON = (3, 11, 16)
EXPECTED_PREDICATES = ["P%d" % index for index in range(1, 17)]
ISOLATED_PYTHON = Path(sys.executable).resolve()

RUNTIME_SOURCES = {
    "m107_runtime.py": "metamorphosis/m107_runtime.py",
    "run.py": "scripts/run_m107_process.py",
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


def _demands() -> dict[str, Any]:
    return _read_canonical(DEMANDS_PATH, "M107 demands fixture")


def verify_inputs() -> dict[str, Any]:
    demands = _demands()
    targets = [tuple(bool(bit) for bit in row) for row in demands["targets"]]
    base = runtime.initial_operators()
    image = runtime.complete_image(base)
    checks = {
        "demands_schema": demands.get("schema") == "m107-demands-v1",
        "two_targets": len(targets) == 2,
        "targets_distinct": len(set(targets)) == 2,
        "targets_outside_base_image": all(target not in image for target in targets),
        "base_image_is_four": len(image) == 4,
        "base_operators_are_the_monotone_fragment": sorted(
            item["name"] for item in base
        ) == ["AND", "OR"],
        "observations_cover_every_row": all(
            {tuple(row["signals"]) for row in demand["observations"]}
            == {tuple(item) for item in runtime.SIGNAL_ROWS}
            for demand in (
                demands["primary"],
                demands["joint"]["first"],
                demands["joint"]["second"],
            )
        ),
        "operator_space_is_generic": len(runtime.operator_space()) == 20,
    }
    return {
        "schema": "m107-input-preflight-v1",
        "confirmed": all(checks.values()),
        "checks": checks,
        "demands_digest": demands.get("demands_digest"),
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
            "M107 capsule produced no parsable report: %s" % (completed.stderr[:400] or error)
        )
    report["returncode"] = completed.returncode
    report["capsule_members"] = _capsule_members(capsule)
    return report


def run_experiment() -> dict[str, Any]:
    preflight = verify_inputs()
    if not preflight["confirmed"]:
        raise QualificationRefused("M107 input preflight failed")

    demands = _demands()
    targets = [list(row) for row in demands["targets"]]
    s0 = runtime.create_state()
    s0_raw = runtime.encode_state(s0)

    with tempfile.TemporaryDirectory(prefix="m107-qualification-") as temporary:
        base = Path(temporary)

        certificate_capsule = _build_capsule(
            base, "certificate",
            {"STATE.json": s0_raw, "TARGETS.json": canonical_json({"targets": targets}).encode("ascii")},
        )
        certificates = _run(certificate_capsule, "certificate")

        image_capsule = _build_capsule(base, "image_s0", {"STATE.json": s0_raw})
        image_s0 = _run(image_capsule, "image")

        # P4 - one demanded behaviour must leave the extension underdetermined.
        primary_capsule = _build_capsule(
            base, "primary_only",
            {"STATE.json": s0_raw,
             "DEMAND.json": canonical_json([demands["primary"]]).encode("ascii")},
        )
        primary_only = _run(primary_capsule, "acquire_refuse_only")

        # P5-P6 - the joint demand determines exactly one reach class.
        producer_capsule = _build_capsule(
            base, "producer",
            {"STATE.json": s0_raw,
             "DEMAND.json": canonical_json(
                 [demands["joint"]["first"], demands["joint"]["second"]]
             ).encode("ascii")},
        )
        producer = _run(producer_capsule, "acquire")
        acquisition = producer.get("acquisition") or {}
        s1 = acquisition.get("next_state")
        if not s1:
            s1_raw = b""
        else:
            s1_raw = runtime.encode_state(s1)

        consumer = {}
        image_s1 = {}
        ablation = {}
        rollback = {}
        mutation = {}
        corruption = {}
        if s1_raw:
            # P8-P9 - the producer is gone; a fresh process receives only the serialized state.
            consumer_capsule = _build_capsule(
                base, "consumer",
                {"STATE.json": s1_raw,
                 "TARGETS.json": canonical_json({"targets": targets}).encode("ascii")},
            )
            consumer = _run(consumer_capsule, "construct")

            image_capsule_s1 = _build_capsule(base, "image_s1", {"STATE.json": s1_raw})
            image_s1 = _run(image_capsule_s1, "image")

            # P10 - ablation returns the reach to exactly the base image.
            decoded = runtime.decode_state(s1)
            kept = [item for item in decoded["operators"] if not item["name"].startswith("ACQUIRED_")]
            ablated_raw = runtime.encode_state(
                runtime._next_state(decoded, kept, decoded["definitions"])
            )
            ablation_capsule = _build_capsule(
                base, "ablated",
                {"STATE.json": ablated_raw,
                 "TARGETS.json": canonical_json({"targets": targets}).encode("ascii")},
            )
            ablation = _run(ablation_capsule, "construct")

            # P14 - byte-exact rollback.
            rollback = {
                "s0_digest": s0["state_digest"],
                "ablated_digest": runtime.decode_state(ablated_raw)["state_digest"],
                "byte_exact": ablated_raw == s0_raw,
            }

            # P13 - mutation of the acquired table changes reach as predicted.
            adopted = acquisition["adopted_operator"]
            flipped = [not bit for bit in adopted["truth_table"]]
            mutated_operator = runtime.operator_definition(
                adopted["name"], adopted["arity"], flipped
            )
            mutated_state = runtime._next_state(
                decoded, kept + [mutated_operator], decoded["definitions"]
            )
            mutation_capsule = _build_capsule(
                base, "mutated",
                {"STATE.json": runtime.encode_state(mutated_state),
                 "TARGETS.json": canonical_json({"targets": targets}).encode("ascii")},
            )
            mutation = _run(mutation_capsule, "construct")
            mutation["adopted_truth_table"] = list(adopted["truth_table"])
            mutation["mutated_truth_table"] = list(flipped)

            # P13 - corruption must fail closed.
            corrupt = json.loads(s1_raw.decode("ascii"))
            corrupt["state_digest"] = "0" * 64
            corruption_capsule = _build_capsule(
                base, "corrupted",
                {"STATE.json": canonical_json(corrupt).encode("ascii"),
                 "TARGETS.json": canonical_json({"targets": targets}).encode("ascii")},
            )
            corruption = _run(corruption_capsule, "construct")

        # P11-P12 - fresh controls with the same observations and an exhaustive search.
        fresh_capsule = _build_capsule(
            base, "fresh",
            {"STATE.json": s0_raw,
             "TARGETS.json": canonical_json({"targets": targets}).encode("ascii")},
        )
        fresh = _run(fresh_capsule, "construct")
        fresh_deeper = _run(fresh_capsule, "construct", bound=runtime.MAX_EXPRESSION_NODES + 4)

    process_records = [
        certificates, image_s0, primary_only, producer, consumer, image_s1,
        ablation, mutation, corruption, fresh, fresh_deeper,
    ]
    isolated = [item for item in process_records if item and item.get("runtime", {}).get("schema")
                == "m107-isolated-process-v1"]

    evidence: dict[str, Any] = {
        "schema": "m107-scientific-evidence-v1",
        "input_preflight": preflight,
        "demands_digest": demands["demands_digest"],
        "targets": targets,
        "runtime": {
            "python_version": platform.python_version(),
            "implementation": platform.python_implementation().lower(),
        },
        "s0": {
            "state_digest": s0["state_digest"],
            "operators": sorted(item["name"] for item in s0["operators"]),
            "raw_sha256": sha256_bytes(s0_raw),
        },
        "certificates": certificates,
        "image_s0": image_s0,
        "primary_only": primary_only,
        "producer": producer,
        "consumer": consumer,
        "image_s1": image_s1,
        "ablation": ablation,
        "mutation": mutation,
        "corruption": corruption,
        "fresh": fresh,
        "fresh_deeper": fresh_deeper,
        "process_boundary": {
            "producer_pid": producer.get("runtime", {}).get("pid"),
            "later_pids": [
                (consumer.get("runtime") or {}).get("pid"),
                (ablation.get("runtime") or {}).get("pid"),
                (fresh.get("runtime") or {}).get("pid"),
            ],
            "producer_pid_absent_from_later": producer.get("runtime", {}).get("pid")
            not in [
                (consumer.get("runtime") or {}).get("pid"),
                (ablation.get("runtime") or {}).get("pid"),
                (fresh.get("runtime") or {}).get("pid"),
            ],
            "all_processes_isolated": bool(isolated)
            and all(
                item["runtime"].get("isolated_mode") is True
                and item["runtime"].get("imported_project_modules") == []
                for item in isolated
            ),
            "all_processes_zero_external_calls": bool(isolated)
            and all(
                item["runtime"].get("model_calls") == 0
                and item["runtime"].get("network_calls") == 0
                and item["runtime"].get("remote_execution_calls") == 0
                for item in isolated
            ),
            "isolated_process_count": len(isolated),
        },
        "information_boundary": {
            "producer_capsule_members": producer.get("capsule_members"),
            "producer_has_targets_file": "TARGETS.json" in (producer.get("capsule_members") or []),
            "consumer_has_demand_file": "DEMAND.json" in (consumer.get("capsule_members") or []),
        },
        "rollback": rollback,
    }
    return evidence


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        raise QualificationRefused(completed.stderr.strip() or "git command failed")
    return completed.stdout.strip()


def require_frozen() -> dict[str, Any]:
    if not PROTOCOL_PATH.exists():
        raise QualificationRefused("M107 final protocol is absent")
    protocol = _read_canonical(PROTOCOL_PATH, "M107 final protocol")
    payload = {key: value for key, value in protocol.items() if key != "protocol_digest"}
    if protocol.get("schema") != "m107-protocol-v1" or protocol.get("protocol_digest") != digest(payload):
        raise QualificationRefused("M107 protocol schema or digest mismatch")
    if protocol.get("status") != "frozen_protocol_owner_authorized":
        raise QualificationRefused("M107 protocol is not owner-authorized")
    if protocol.get("decisive_conditions") != EXPECTED_PREDICATES:
        raise QualificationRefused("M107 decisive predicate declaration changed")
    if tuple(sys.version_info[:3]) != CANONICAL_PYTHON:
        raise QualificationRefused("M107 canonical runtime mismatch")
    bound = protocol.get("bound_files", {})
    files = bound.get("files")
    members = bound.get("member_digests")
    if not isinstance(files, list) or not isinstance(members, dict):
        raise QualificationRefused("M107 bound-file record is invalid")
    measured = {path: sha256_bytes((ROOT / path).read_bytes()) for path in files}
    if measured != members or digest(measured) != bound.get("digest"):
        raise QualificationRefused("M107 bound apparatus changed")
    freeze_tag = protocol.get("freeze_tag")
    if not isinstance(freeze_tag, str) or _git("cat-file", "-t", freeze_tag) != "tag":
        raise QualificationRefused("M107 freeze reference is not an annotated tag")
    if _git("rev-list", "-n", "1", freeze_tag) != _git("rev-parse", "HEAD"):
        raise QualificationRefused("M107 HEAD is not the frozen tag commit")
    if _git("status", "--porcelain"):
        raise QualificationRefused("M107 canonical worktree is not clean")
    if RESULT_PATH.exists() or CHECK_PATH.exists():
        raise QualificationRefused("M107 canonical evidence path already exists")
    return protocol


def preflight() -> dict[str, Any]:
    inputs = verify_inputs()
    protocol = require_frozen()
    return {
        "schema": "m107-preflight-v1",
        "confirmed": inputs["confirmed"],
        "inputs": inputs,
        "protocol_digest": protocol["protocol_digest"],
        "result_absent": not RESULT_PATH.exists(),
        "check_report_absent": not CHECK_PATH.exists(),
        "python": platform.python_version(),
    }


def materialize(*, authorized_by_owner: bool, understand_unique_attempt: bool) -> dict[str, Any]:
    if not authorized_by_owner or not understand_unique_attempt:
        raise QualificationRefused("M107 owner authorization or unique-attempt acknowledgement absent")
    protocol = require_frozen()
    evidence = run_experiment()
    result: dict[str, Any] = {
        "schema": "m107-result-v1",
        "milestone": "M107",
        "hypothesis": "H52",
        "attempt": 1,
        "protocol_digest": protocol["protocol_digest"],
        "demands_digest": evidence["demands_digest"],
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
                "schema": "m107-development-rehearsal-v1",
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
            "schema": "m107-qualification-refusal-v1",
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
