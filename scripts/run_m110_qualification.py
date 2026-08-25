"""M110 orchestration - restored machinery against a consumer family that never produced it.

Restores the M109 lineage arms from the frozen M109 result bytes, verifies that they reproduce the
recorded state digests exactly, and runs them against the canonical consumer population across
isolated processes.

The information boundary is enforced by capsule membership, not by convention. Every arm capsule for
a given world and demand receives byte-identical `WORLD.json` and `DEMAND.json` and differs only in
`STATE.json`; no capsule ever holds the producer's result, world or demands. All of that is measured
and recorded.

The canonical entry point refuses unless a final protocol is frozen, HEAD is exactly the freeze
commit, the worktree is clean, the bound apparatus is unchanged and no evidence exists yet.
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

from metamorphosis import m109_runtime as producer  # noqa: E402
from metamorphosis import m110_runtime as runtime  # noqa: E402

EXPERIMENT = ROOT / "experiments" / "M110"
PRODUCER_RESULT = ROOT / "experiments" / "M109" / "RESULT.json"
POPULATION_PATH = EXPERIMENT / "POPULATION.json"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
RESULT_PATH = EXPERIMENT / "RESULT.json"
CHECK_PATH = EXPERIMENT / "CHECK_REPORT.json"

CANONICAL_PYTHON = (3, 11, 16)
EXPECTED_PREDICATES = ["P%d" % index for index in range(1, 23)]
ISOLATED_PYTHON = Path(sys.executable).resolve()
DEEPER_BOUND = runtime.DEEPER_EXPRESSION_NODES
REACH_BUDGET = 2

# The rows the experiment poses. 7 and 3 lie inside the producer's reachable attribution census; 5
# lies outside it; 1 is the conservation control.
INSIDE_ROWS = (7, 3)
OUTSIDE_ROWS = (5,)
CONSERVATION_ROWS = (1,)
POSED_ROWS = INSIDE_ROWS + OUTSIDE_ROWS + CONSERVATION_ROWS
ARM_NAMES = ("M0", "M1", "M2")

RUNTIME_SOURCES = {
    "m107_runtime.py": "metamorphosis/m107_runtime.py",
    "m108_runtime.py": "metamorphosis/m108_runtime.py",
    "m109_runtime.py": "metamorphosis/m109_runtime.py",
    "m110_runtime.py": "metamorphosis/m110_runtime.py",
    "run.py": "scripts/run_m110_process.py",
}

EPHEMERAL_KEYS = {
    "pid",
    "arm_pids",
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


# ----------------------------------------------------------------------------------------
# Provenance: the arms are restored from the producer's frozen bytes, never reimplemented.
# ----------------------------------------------------------------------------------------


def restore_arms() -> dict[str, Any]:
    """Rebuild M0/M1/M2 from `experiments/M109/RESULT.json` and prove they are those states."""
    raw = PRODUCER_RESULT.read_bytes()
    result = json.loads(raw.decode("ascii"))
    evidence = result["scientific_evidence"]
    first = producer.decode_rule(evidence["generation_one"]["acquisition"]["adopted_rule"])
    second = producer.decode_rule(evidence["generation_two"]["acquisition"]["adopted_rule"])

    base = producer.create_state()
    generation_one = producer.create_state(
        base["operators"],
        signal_width=base["signal_width"],
        candidate_space=base["candidate_space"],
        rules=[first],
    )
    stage_one = evidence["stage_one_resolution"]
    generation_two = producer.create_state(
        base["operators"],
        signal_width=stage_one["final_signal_width"],
        candidate_space=stage_one["final_candidate_space"],
        rules=[first, second],
    )
    checks = {
        "producer_result_digest_matches": result["result_digest"] == digest(
            {k: v for k, v in result.items() if k != "result_digest"}
        ),
        "m0_state_digest_reproduced": base["state_digest"] == evidence["m0"]["state_digest"],
        "m1_state_digest_reproduced": generation_one["state_digest"]
        == evidence["generation_one"]["state_digest"],
        "m2_state_digest_reproduced": generation_two["state_digest"]
        == evidence["generation_two"]["state_digest"],
        "generation_one_selects_a_registered_component": first["selects_component_when_true"]
        in producer.COMPONENTS,
        "generation_two_selects_a_registered_component": second["selects_component_when_true"]
        in producer.COMPONENTS,
        "generations_are_distinct": first["rule_id"] != second["rule_id"],
        "cascade_is_contiguous": [first["generation"], second["generation"]] == [1, 2],
        "attribution_is_delegated_to_the_producer_module": runtime.attribute.__module__
        == "metamorphosis.m110_runtime"
        and producer.attribute.__module__ == "metamorphosis.m109_runtime",
    }
    cascades = {"M0": [], "M1": [first], "M2": [first, second]}
    arms = {name: runtime.create_state(rules=rules) for name, rules in cascades.items()}
    return {
        "schema": "m110-provenance-v1",
        "confirmed": all(checks.values()),
        "checks": checks,
        "producer_result_bytes_digest": sha256_bytes(raw),
        "producer_result_digest": result["result_digest"],
        "producer_protocol_digest": result["protocol_digest"],
        "producer_reachable_rows": list(evidence["domain"]["rows"]),
        "producer_unreachable_rows": list(evidence["domain"]["unreachable_rows"]),
        "producer_row_labels": {
            key: list(value) for key, value in evidence["domain"]["row_labels"].items()
        },
        "restored_state_digests": {
            "M0": base["state_digest"],
            "M1": generation_one["state_digest"],
            "M2": generation_two["state_digest"],
        },
        "restored_rules": {"generation_one": first, "generation_two": second},
        "arm_state_digests": {name: state["state_digest"] for name, state in arms.items()},
        "arm_generations": {name: len(state["rules"]) for name, state in arms.items()},
        "arm_adapter_projection_digests": {
            name: digest(runtime.adapter_projection(state)) for name, state in arms.items()
        },
        "_arms": arms,
    }


def verify_inputs(provenance: dict[str, Any]) -> dict[str, Any]:
    population = _read_canonical(POPULATION_PATH, "M110 canonical population")
    worlds = [runtime.decode_world(item) for item in population["worlds"]]
    arms = provenance["_arms"]
    adapters = {digest(runtime.adapter_projection(state)) for state in arms.values()}
    payload_keys = {
        name: sorted(key for key in state if key not in ("rules", "state_digest"))
        for name, state in arms.items()
    }
    differing = _fields_that_differ(arms)
    checks = {
        "population_schema": population.get("schema") == runtime.POPULATION_SCHEMA,
        "population_is_canonical_tag": population.get("tag") == "canonical",
        "population_seed_range_is_disjoint_from_development": population.get("seed_range")
        == [1000, 1999],
        "population_is_non_empty": len(worlds) > 0,
        "world_identities_are_distinct": len({item["world_digest"] for item in worlds})
        == len(worlds),
        "documents_are_the_declared_count": all(
            len(item["documents"]) == runtime.DOCUMENT_COUNT for item in worlds
        ),
        "population_holds_no_census_or_label": not any(
            key in population for key in ("row_labels", "canonical_targets", "census", "rows")
        ),
        "registry_is_the_producer_triple": tuple(runtime.COMPONENTS) == tuple(producer.COMPONENTS),
        "feature_vocabulary_is_the_producer_vocabulary": tuple(runtime.FEATURE_NAMES)
        == tuple(producer.FEATURE_NAMES),
        "arms_share_one_adapter": len(adapters) == 1,
        "arms_agree_on_field_names": len({tuple(value) for value in payload_keys.values()}) == 1,
        "arms_differ_only_in_the_rule_cascade": differing == ["rules"],
        "provenance_confirmed": bool(provenance["confirmed"]),
        "producer_census_excludes_row_five": 5 in provenance["producer_unreachable_rows"],
        "no_producer_fixture_in_the_experiment_directory": not any(
            (EXPERIMENT / name).exists()
            for name in ("DEMAND_STAGE1.json", "DEMAND_STAGE2.json", "EPISODES.json")
        ),
    }
    return {
        "schema": "m110-input-preflight-v1",
        "confirmed": all(checks.values()),
        "checks": checks,
        "population_digest": population["population_digest"],
        "world_count": len(worlds),
        "world_digests": [item["world_digest"] for item in worlds],
        "arm_fields_that_differ": differing,
    }


def _fields_that_differ(arms: dict[str, dict[str, Any]]) -> list[str]:
    keys: set[str] = set()
    for state in arms.values():
        keys |= set(state)
    differing = []
    for key in sorted(keys):
        if key == "state_digest":
            continue
        rendered = {canonical_json(state.get(key)) for state in arms.values()}
        if len(rendered) > 1:
            differing.append(key)
    return differing


# ----------------------------------------------------------------------------------------
# Capsules.
# ----------------------------------------------------------------------------------------


def _build_capsule(base: Path, name: str, payloads: dict[str, bytes]) -> Path:
    capsule = base / name
    capsule.mkdir(parents=True)
    for destination, source in RUNTIME_SOURCES.items():
        shutil.copyfile(ROOT / source, capsule / destination)
    for filename, raw in payloads.items():
        (capsule / filename).write_bytes(raw)
    return capsule


def _run(
    capsule: Path, action: str, bound: int | None = None, budget: int | None = None
) -> dict[str, Any]:
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
            "M110 capsule produced no parsable report: %s" % (completed.stderr[:400] or error)
        )
    report["returncode"] = completed.returncode
    report["capsule_members"] = sorted(item.name for item in capsule.iterdir())
    report["input_digests"] = {
        item.name: sha256_bytes(item.read_bytes())
        for item in sorted(capsule.iterdir())
        if item.name.endswith(".json")
    }
    return report


def _resolution_outcome(report: dict[str, Any]) -> dict[str, Any]:
    resolution = report.get("resolution") or {}
    construction = resolution.get("construction") or {}
    trace = resolution.get("trace") or []
    return {
        "confirmed": bool(resolution.get("confirmed")),
        "reason": resolution.get("reason"),
        "steps": resolution.get("steps"),
        "attributed_component": (trace[0]["attribution"]["component"] if trace else None),
        "attribution_mode": (trace[0]["attribution"]["mode"] if trace else None),
        "attribution_generation": (trace[0]["attribution"]["generation"] if trace else None),
        "feature_row": (trace[0]["features"]["row_index"] if trace else None),
        "executes_to_target": bool(construction.get("executes_to_target")),
        "rendered_python_agrees": bool(construction.get("rendered_python_agrees")),
        "witness_nodes": construction.get("witness_nodes"),
        "image_size": construction.get("image_size"),
        "final_interface_width": resolution.get("final_interface_width"),
        "final_candidate_space": resolution.get("final_candidate_space"),
        "trials_performed": resolution.get("trials_performed"),
    }


def _solved(outcome: dict[str, Any]) -> bool:
    return bool(
        outcome["confirmed"]
        and outcome["executes_to_target"]
        and outcome["rendered_python_agrees"]
    )


# ----------------------------------------------------------------------------------------
# The experiment.
# ----------------------------------------------------------------------------------------


def run_experiment() -> dict[str, Any]:
    provenance = restore_arms()
    preflight_report = verify_inputs(provenance)
    if not preflight_report["confirmed"] or not provenance["confirmed"]:
        raise QualificationRefused("M110 input preflight failed")

    arms = provenance.pop("_arms")
    arm_bytes = {name: runtime.encode_state(state) for name, state in arms.items()}
    population = _read_canonical(POPULATION_PATH, "M110 canonical population")
    worlds = [runtime.decode_world(item) for item in population["worlds"]]

    base = Path(tempfile.mkdtemp(prefix="m110-"))
    isolated: list[dict[str, Any]] = []
    arm_capsules: list[dict[str, Any]] = []
    per_world: list[dict[str, Any]] = []
    try:
        for index, world in enumerate(worlds):
            tag = "w%d" % index
            world_bytes = canonical_json({"world": world}).encode("ascii")

            census_run = _run(
                _build_capsule(base, tag + "-census", {"WORLD.json": world_bytes}), "census"
            )
            if not census_run.get("confirmed"):
                raise QualificationRefused("M110 consumer census failed on %s" % world["world_id"])
            census = census_run["census"]
            isolated.append(census_run)

            certificates_run = _run(
                _build_capsule(
                    base,
                    tag + "-certificates",
                    {"WORLD.json": world_bytes, "STATE.json": arm_bytes["M0"]},
                ),
                "certificates",
            )
            isolated.append(certificates_run)

            demands: dict[str, dict[str, Any]] = {}
            rows: dict[str, Any] = {}
            for row in POSED_ROWS:
                key = str(row)
                if key not in census["canonical_targets"]:
                    raise QualificationRefused(
                        "M110 canonical row %d is absent from %s" % (row, world["world_id"])
                    )
                demand = runtime.consumer_demand("row-%d" % row, census["canonical_targets"][key])
                demands[key] = demand
                demand_bytes = canonical_json({"demand": demand}).encode("ascii")

                trial_run = _run(
                    _build_capsule(
                        base,
                        "%s-trial-%d" % (tag, row),
                        {
                            "WORLD.json": world_bytes,
                            "STATE.json": arm_bytes["M0"],
                            "DEMAND.json": demand_bytes,
                        },
                    ),
                    "trial",
                )
                isolated.append(trial_run)

                outcomes: dict[str, Any] = {}
                for name in ARM_NAMES:
                    capsule = _build_capsule(
                        base,
                        "%s-row%d-%s" % (tag, row, name),
                        {
                            "WORLD.json": world_bytes,
                            "STATE.json": arm_bytes[name],
                            "DEMAND.json": demand_bytes,
                        },
                    )
                    report = _run(capsule, "resolve")
                    isolated.append(report)
                    arm_capsules.append(report)
                    outcomes[name] = _resolution_outcome(report)
                    outcomes[name]["arm_state_digest"] = report.get("arm_state_digest")
                    outcomes[name]["adapter_projection_digest"] = report.get(
                        "adapter_projection_digest"
                    )
                    outcomes[name]["input_digests"] = report["input_digests"]

                deeper: dict[str, Any] = {}
                if row in INSIDE_ROWS:
                    deeper_report = _run(
                        _build_capsule(
                            base,
                            "%s-row%d-deeper" % (tag, row),
                            {
                                "WORLD.json": world_bytes,
                                "STATE.json": arm_bytes["M0"],
                                "DEMAND.json": demand_bytes,
                            },
                        ),
                        "resolve",
                        DEEPER_BOUND,
                    )
                    isolated.append(deeper_report)
                    deeper = _resolution_outcome(deeper_report)

                rows[key] = {
                    "row": row,
                    "demand_digest": demand["demand_digest"],
                    "target": demand["target"],
                    "trial": trial_run.get("trial"),
                    "features": trial_run.get("features"),
                    "ground_truth_component": (trial_run.get("trial") or {}).get("component"),
                    "arms": outcomes,
                    "solved": {name: _solved(outcomes[name]) for name in ARM_NAMES},
                    "deeper_bound_m0": deeper,
                    "equal_inputs_across_arms": len(
                        {
                            canonical_json(
                                {
                                    key: value
                                    for key, value in outcomes[name]["input_digests"].items()
                                    if key != "STATE.json"
                                }
                            )
                            for name in ARM_NAMES
                        }
                    )
                    == 1,
                }

            # ---- causal controls, on the row the second generation owns -------------------
            row_three = canonical_json({"demand": demands["3"]}).encode("ascii")
            ablated_two = runtime.create_state(rules=arms["M2"]["rules"][:-1])
            ablated_one = runtime.create_state(rules=[])
            mutated_rule = copy.deepcopy(arms["M2"]["rules"][-1])
            mutated = runtime.create_state(
                rules=list(arms["M2"]["rules"][:-1])
                + [
                    producer.attribution_rule(
                        mutated_rule["body"],
                        [not value for value in mutated_rule["truth_table"]],
                        mutated_rule["selects_component_when_true"],
                        mutated_rule["generation"],
                    )
                ]
            )
            ablation_two = _run(
                _build_capsule(
                    base,
                    tag + "-ablate-two",
                    {
                        "WORLD.json": world_bytes,
                        "STATE.json": runtime.encode_state(ablated_two),
                        "DEMAND.json": row_three,
                    },
                ),
                "resolve",
            )
            row_seven = canonical_json({"demand": demands["7"]}).encode("ascii")
            row_five = canonical_json({"demand": demands["5"]}).encode("ascii")
            ablation_one_seven = _run(
                _build_capsule(
                    base,
                    tag + "-ablate-one-seven",
                    {
                        "WORLD.json": world_bytes,
                        "STATE.json": runtime.encode_state(ablated_one),
                        "DEMAND.json": row_seven,
                    },
                ),
                "resolve",
            )
            ablation_one_five = _run(
                _build_capsule(
                    base,
                    tag + "-ablate-one-five",
                    {
                        "WORLD.json": world_bytes,
                        "STATE.json": runtime.encode_state(ablated_one),
                        "DEMAND.json": row_five,
                    },
                ),
                "resolve",
            )
            mutation = _run(
                _build_capsule(
                    base,
                    tag + "-mutate",
                    {
                        "WORLD.json": world_bytes,
                        "STATE.json": runtime.encode_state(mutated),
                        "DEMAND.json": row_three,
                    },
                ),
                "resolve",
            )
            unregistered = _run(
                _build_capsule(
                    base,
                    tag + "-unregistered",
                    {
                        "WORLD.json": world_bytes,
                        "STATE.json": arm_bytes["M0"],
                        "DEMAND.json": row_three,
                        "RULES.json": canonical_json(
                            {"rules": [item for item in arms["M2"]["rules"]]}
                        ).encode("ascii"),
                    },
                ),
                "resolve",
            )
            corruption = _run(
                _build_capsule(base, tag + "-corrupt", {"STATE.json": arm_bytes["M2"]}),
                "corruption",
            )
            isolated += [
                ablation_two,
                ablation_one_seven,
                ablation_one_five,
                mutation,
                unregistered,
                corruption,
            ]

            reach: dict[str, Any] = {}
            for name in ARM_NAMES:
                report = _run(
                    _build_capsule(
                        base,
                        "%s-reach-%s" % (tag, name),
                        {"WORLD.json": world_bytes, "STATE.json": arm_bytes[name]},
                    ),
                    "reach_improve",
                    None,
                    REACH_BUDGET,
                )
                isolated.append(report)
                reach[name] = report["reach_improve"]
            reach_sets = {name: set(reach[name]["tables"]) for name in ARM_NAMES}

            per_world.append(
                {
                    "world_id": world["world_id"],
                    "world_digest": world["world_digest"],
                    "census": {
                        key: value for key, value in census.items() if key != "witnesses"
                    },
                    "certificates": certificates_run.get("certificates"),
                    "rows": rows,
                    "ablation": {
                        "generation_two_removed_state_digest": ablated_two["state_digest"],
                        "generation_two_removed_matches_m1": runtime.encode_state(ablated_two)
                        == arm_bytes["M1"],
                        "generation_one_removed_matches_m0": runtime.encode_state(ablated_one)
                        == arm_bytes["M0"],
                        "row_three_after_removing_generation_two": _resolution_outcome(
                            ablation_two
                        ),
                        "row_seven_after_removing_generation_one": _resolution_outcome(
                            ablation_one_seven
                        ),
                        "row_five_after_removing_generation_one": _resolution_outcome(
                            ablation_one_five
                        ),
                    },
                    "mutation": _resolution_outcome(mutation),
                    "unregistered": {
                        **_resolution_outcome(unregistered),
                        "capsule_held_the_rule_bytes": "RULES.json"
                        in unregistered["capsule_members"],
                        "state_held_no_rule": unregistered.get("generations") == 0,
                    },
                    "corruption": corruption.get("corruption"),
                    "reach_improve": {
                        name: {
                            "size": reach[name]["size"],
                            "axes": reach[name]["axes"],
                            "budget": reach[name]["budget"],
                            "digest": reach[name]["digest"],
                        }
                        for name in ARM_NAMES
                    },
                    "reach_chain": {
                        "m0_strictly_inside_m1": reach_sets["M0"] < reach_sets["M1"],
                        "m1_strictly_inside_m2": reach_sets["M1"] < reach_sets["M2"],
                        "strict_chain": reach_sets["M0"] < reach_sets["M1"] < reach_sets["M2"],
                        "gained_by_generation_one": len(reach_sets["M1"] - reach_sets["M0"]),
                        "gained_by_generation_two": len(reach_sets["M2"] - reach_sets["M1"]),
                    },
                }
            )

        evidence: dict[str, Any] = {
            "schema": "m110-evidence-v1",
            "input_preflight": preflight_report,
            "provenance": provenance,
            "population_digest": population["population_digest"],
            "posed_rows": {
                "inside_producer_census": list(INSIDE_ROWS),
                "outside_producer_census": list(OUTSIDE_ROWS),
                "conservation": list(CONSERVATION_ROWS),
            },
            "runtime": {
                "implementation": platform.python_implementation().lower(),
                "canonical_python": list(CANONICAL_PYTHON),
                "matches_canonical": tuple(sys.version_info[:3]) == CANONICAL_PYTHON,
                "deeper_bound": DEEPER_BOUND,
                "reach_budget": REACH_BUDGET,
            },
            "worlds": per_world,
            "census_agreement": _census_agreement(per_world, provenance),
            "boundary": {
                "no_capsule_held_a_producer_fixture": all(
                    not any(
                        name.startswith("DEMAND_STAGE") or name in ("EPISODES.json", "DOMAIN.json")
                        for name in item["capsule_members"]
                    )
                    for item in isolated
                ),
                "arm_capsules_differ_only_in_state": _arm_capsules_differ_only_in_state(
                    arm_capsules
                ),
                "isolated_process_count": len(isolated),
                "arm_pids": [item["runtime"]["pid"] for item in arm_capsules],
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


def _arm_capsules_differ_only_in_state(reports: list[dict[str, Any]]) -> bool:
    grouped: dict[tuple[str, ...], set[str]] = {}
    for report in reports:
        members = tuple(report["capsule_members"])
        grouped.setdefault(members, set()).add(
            canonical_json(
                {k: v for k, v in report["input_digests"].items() if k != "STATE.json"}
            )
        )
    return all(len(value) >= 1 for value in grouped.values()) and len(grouped) >= 1


def _census_agreement(per_world: list[dict[str, Any]], provenance: dict[str, Any]) -> dict[str, Any]:
    producer_labels = {
        int(key): value[0] for key, value in provenance["producer_row_labels"].items()
    }
    producer_rows = set(provenance["producer_reachable_rows"])
    shared: dict[str, list[str]] = {}
    disagreements: list[dict[str, Any]] = []
    consumer_rows: set[int] = set()
    for entry in per_world:
        for key, value in entry["census"]["row_labels"].items():
            row = int(key)
            consumer_rows.add(row)
            shared.setdefault(key, []).append(value[0] if len(value) == 1 else "|".join(value))
            if row in producer_rows and value != [producer_labels[row]]:
                disagreements.append(
                    {"world_id": entry["world_id"], "row": row,
                     "producer": producer_labels[row], "consumer": value}
                )
    return {
        "producer_reachable_rows": sorted(producer_rows),
        "consumer_reachable_rows": sorted(consumer_rows),
        "rows_only_the_consumer_reaches": sorted(consumer_rows - producer_rows),
        "rows_only_the_producer_reaches": sorted(producer_rows - consumer_rows),
        "shared_rows": sorted(consumer_rows & producer_rows),
        "labels_agree_on_every_shared_row": not disagreements,
        "disagreements": disagreements,
        "consumer_label_is_world_invariant": all(
            len(set(value)) == 1 for value in shared.values()
        ),
    }


# ----------------------------------------------------------------------------------------
# Canonical gating.
# ----------------------------------------------------------------------------------------


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        raise QualificationRefused(completed.stderr.strip() or "git command failed")
    return completed.stdout.strip()


def require_frozen() -> dict[str, Any]:
    if not PROTOCOL_PATH.exists():
        raise QualificationRefused("M110 final protocol is absent")
    protocol = _read_canonical(PROTOCOL_PATH, "M110 final protocol")
    payload = {key: value for key, value in protocol.items() if key != "protocol_digest"}
    if protocol.get("schema") != "m110-protocol-v1" or protocol.get("protocol_digest") != digest(
        payload
    ):
        raise QualificationRefused("M110 protocol schema or digest mismatch")
    if protocol.get("status") != "frozen_protocol_owner_authorized":
        raise QualificationRefused("M110 protocol is not owner-authorized")
    if protocol.get("decisive_conditions") != EXPECTED_PREDICATES:
        raise QualificationRefused("M110 decisive predicate declaration changed")
    if tuple(sys.version_info[:3]) != CANONICAL_PYTHON:
        raise QualificationRefused("M110 canonical runtime mismatch")
    bound = protocol.get("bound_files", {})
    files = bound.get("files")
    members = bound.get("member_digests")
    modes = bound.get("member_digest_modes") or {}
    if not isinstance(files, list) or not isinstance(members, dict):
        raise QualificationRefused("M110 bound-file record is invalid")
    measured = {}
    for path in files:
        raw = (ROOT / path).read_bytes()
        if modes.get(path) == "lf_normalized":
            raw = raw.replace(b"\r\n", b"\n")
        elif modes.get(path) != "raw":
            raise QualificationRefused("M110 bound-file digest mode is undeclared")
        measured[path] = sha256_bytes(raw)
    if measured != members or digest(measured) != bound.get("digest"):
        raise QualificationRefused("M110 bound apparatus changed")
    freeze_tag = protocol.get("freeze_tag")
    if not isinstance(freeze_tag, str) or _git("cat-file", "-t", freeze_tag) != "tag":
        raise QualificationRefused("M110 freeze reference is not an annotated tag")
    if _git("rev-list", "-n", "1", freeze_tag) != _git("rev-parse", "HEAD"):
        raise QualificationRefused("M110 HEAD is not the frozen tag commit")
    if _git("status", "--porcelain"):
        raise QualificationRefused("M110 canonical worktree is not clean")
    if RESULT_PATH.exists() or CHECK_PATH.exists():
        raise QualificationRefused("M110 canonical evidence path already exists")
    return protocol


def preflight() -> dict[str, Any]:
    provenance = restore_arms()
    inputs = verify_inputs(provenance)
    protocol = require_frozen()
    return {
        "schema": "m110-preflight-v1",
        "confirmed": inputs["confirmed"] and provenance["confirmed"],
        "inputs": {key: value for key, value in inputs.items() if not key.startswith("_")},
        "protocol_digest": protocol["protocol_digest"],
        "result_absent": not RESULT_PATH.exists(),
        "check_report_absent": not CHECK_PATH.exists(),
        "python": platform.python_version(),
    }


def materialize(*, authorized_by_owner: bool, understand_unique_attempt: bool) -> dict[str, Any]:
    if not authorized_by_owner or not understand_unique_attempt:
        raise QualificationRefused(
            "M110 owner authorization or unique-attempt acknowledgement absent"
        )
    protocol = require_frozen()
    evidence = run_experiment()
    result: dict[str, Any] = {
        "schema": "m110-result-v1",
        "milestone": "M110",
        "hypothesis": "H55",
        "attempt": 1,
        "protocol_digest": protocol["protocol_digest"],
        "population_digest": evidence["population_digest"],
        "producer_result_digest": evidence["provenance"]["producer_result_digest"],
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
                "schema": "m110-development-rehearsal-v1",
                "confirmed": True,
                "stable_evidence_digest": digest(stable_projection(evidence)),
                "evidence": evidence,
            }
            if arguments.out:
                Path(arguments.out).write_bytes(canonical_json(report).encode("ascii"))
                report = {
                    key: value for key, value in report.items() if key != "evidence"
                } | {"out": arguments.out}
        else:
            report = materialize(
                authorized_by_owner=arguments.owner_authorized,
                understand_unique_attempt=arguments.understand_unique_attempt,
            )
    except Exception as error:  # noqa: BLE001 - the refusal is the observation
        report = {
            "schema": "m110-qualification-refusal-v1",
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
