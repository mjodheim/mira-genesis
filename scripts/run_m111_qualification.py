"""M111 orchestration - a lineage that spends an experiment where its observation runs out.

Restores the M109 lineage from the frozen M109 result bytes, including its **terminal** state, which
already holds the non-monotone operator the lineage adopted for itself when generation 2 widened its
candidate space. All four restored states are verified against the digests M109 recorded.

Every arm receives byte-identical world and demand inputs and the same probe budget; the arms differ
in the lineage state they carry and in nothing else. No capsule holds a producer result, a producer
demand or an episodes fixture: the lineage records its own episodes, in a capsule holding only the
world.
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

from metamorphosis import m107_runtime as expr  # noqa: E402
from metamorphosis import m109_runtime as machinery  # noqa: E402
from metamorphosis import m110_runtime as consumer  # noqa: E402
from metamorphosis import m111_runtime as runtime  # noqa: E402

EXPERIMENT = ROOT / "experiments" / "M111"
PRODUCER_RESULT = ROOT / "experiments" / "M109" / "RESULT.json"
CONSUMER_RESULT = ROOT / "experiments" / "M110" / "RESULT.json"
POPULATION_PATH = EXPERIMENT / "POPULATION.json"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
RESULT_PATH = EXPERIMENT / "RESULT.json"
CHECK_PATH = EXPERIMENT / "CHECK_REPORT.json"

CANONICAL_PYTHON = (3, 11, 16)
EXPECTED_PREDICATES = ["P%d" % index for index in range(1, 25)]
ISOLATED_PYTHON = Path(sys.executable).resolve()
AMBIGUOUS_ROW = 3
WITNESS_ROW = 7
CONTRAST_ROW = 1
STATIC_ARMS = ("M0", "M1", "M2", "always_signal")
DETERMINED_FIRST = ("determined_then_A", "determined_then_B")

RUNTIME_SOURCES = {
    "m107_runtime.py": "metamorphosis/m107_runtime.py",
    "m108_runtime.py": "metamorphosis/m108_runtime.py",
    "m109_runtime.py": "metamorphosis/m109_runtime.py",
    "m110_runtime.py": "metamorphosis/m110_runtime.py",
    "m111_runtime.py": "metamorphosis/m111_runtime.py",
    "run.py": "scripts/run_m111_process.py",
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
# Provenance: four restored states, each verified against what M109 recorded.
# ----------------------------------------------------------------------------------------


def restore_lineage() -> dict[str, Any]:
    raw = PRODUCER_RESULT.read_bytes()
    result = json.loads(raw.decode("ascii"))
    evidence = result["scientific_evidence"]
    first = machinery.decode_rule(evidence["generation_one"]["acquisition"]["adopted_rule"])
    second = machinery.decode_rule(evidence["generation_two"]["acquisition"]["adopted_rule"])
    terminal = evidence["stage_two_resolution"]

    # The operator the lineage adopted for itself when generation 2 widened its candidate space. Its
    # name is the only thing M109 recorded, so it is recovered from the authored space by that name
    # and the reconstruction is proved by the terminal state digest rather than asserted.
    acquired_name = terminal["construction"]["witness"]["children"][0]["operator"]
    matches = [
        item
        for item in expr.operator_space()
        if "ACQUIRED_%s" % item["operator_id"][-8:] == acquired_name
    ]
    acquired = (
        expr.operator_definition(acquired_name, matches[0]["arity"], matches[0]["truth_table"])
        if len(matches) == 1
        else None
    )

    base = machinery.create_state()
    generation_one = machinery.create_state(
        base["operators"], signal_width=base["signal_width"],
        candidate_space=base["candidate_space"], rules=[first],
    )
    stage_one = evidence["stage_one_resolution"]
    generation_two = machinery.create_state(
        base["operators"], signal_width=stage_one["final_signal_width"],
        candidate_space=stage_one["final_candidate_space"], rules=[first, second],
    )
    end_state = (
        machinery.create_state(
            base["operators"] + [acquired],
            signal_width=terminal["final_signal_width"],
            candidate_space=terminal["final_candidate_space"],
            rules=[first, second],
        )
        if acquired is not None
        else None
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
        "acquired_operator_recovered_uniquely": len(matches) == 1,
        "terminal_state_digest_reproduced": end_state is not None
        and end_state["state_digest"] == terminal["final_state_digest"],
        "acquired_operator_is_non_monotone": acquired is not None
        and not expr._operator_is_monotone(acquired),
        "terminal_candidate_space_is_complete": terminal["final_candidate_space"]
        == machinery.COMPLETE_SPACE,
    }
    consumer_raw = CONSUMER_RESULT.read_bytes()
    return {
        "schema": "m111-provenance-v1",
        "confirmed": all(checks.values()),
        "checks": checks,
        "producer_result_bytes_digest": sha256_bytes(raw),
        "producer_result_digest": result["result_digest"],
        "consumer_result_bytes_digest": sha256_bytes(consumer_raw),
        "consumer_result_digest": json.loads(consumer_raw.decode("ascii"))["result_digest"],
        "restored_state_digests": {
            "M0": base["state_digest"],
            "M1": generation_one["state_digest"],
            "M2_at_adoption": generation_two["state_digest"],
            "M2_terminal": end_state["state_digest"] if end_state else None,
        },
        "acquired_operator": acquired,
        "restored_rules": {"generation_one": first, "generation_two": second},
        "_states": {
            "M0": base,
            "M1": machinery.create_state(
                base["operators"], signal_width=stage_one["final_signal_width"],
                candidate_space=base["candidate_space"], rules=[first],
            ),
            "M2": end_state,
        },
        "_rules": [first, second],
    }


def _always_signal_rule() -> dict[str, Any]:
    """An authored fixed strategy: blame the signal interface, always. A control, not a lineage."""
    return machinery.attribution_rule(
        {"node": "SIGNAL", "index": 0},
        [True] * (2 ** runtime.FEATURE_COUNT),
        runtime.COMPONENT_SIGNALS,
        1,
    )


def build_arms(provenance: dict[str, Any]) -> dict[str, dict[str, Any]]:
    states = provenance["_states"]
    first, second = provenance["_rules"]
    fixed = _always_signal_rule()
    arms = {
        "M0": runtime.create_state(states["M0"], consumer.create_state(rules=[])),
        "M1": runtime.create_state(states["M1"], consumer.create_state(rules=[first])),
        "M2": runtime.create_state(states["M2"], consumer.create_state(rules=[first, second])),
        "always_signal": runtime.create_state(
            machinery.create_state(
                machinery.create_state()["operators"], rules=[fixed]
            ),
            consumer.create_state(rules=[fixed]),
        ),
    }
    return arms


def verify_inputs(
    provenance: dict[str, Any], population_path: Path = POPULATION_PATH
) -> dict[str, Any]:
    population = _read_canonical(population_path, "M111 population")
    ambiguous = [consumer.decode_world(item) for item in population["ambiguous_worlds"]]
    witness = [consumer.decode_world(item) for item in population["witness_worlds"]]
    worlds = ambiguous + witness
    arms = build_arms(provenance)
    adapters = {digest(runtime.adapter_projection(state)) for state in arms.values()}
    checks = {
        "population_schema": population.get("schema") == "m111-two-stratum-population-v1",
        "population_is_canonical_tag": population.get("tag") == "canonical",
        "population_seed_range_is_disjoint": population.get("seed_range") == [3000, 3999],
        "both_strata_are_non_empty": len(ambiguous) > 0 and len(witness) > 0,
        "strata_are_disjoint": not (
            {item["world_digest"] for item in ambiguous}
            & {item["world_digest"] for item in witness}
        ),
        "world_identities_are_distinct": len({item["world_digest"] for item in worlds})
        == len(worlds),
        "population_holds_no_census_pair_or_label": not any(
            key in population for key in ("row_labels", "canonical_targets", "census", "pair", "episodes")
        ),
        "registry_extends_the_producer_triple": tuple(runtime.COMPONENTS)
        == tuple(machinery.COMPONENTS) + (runtime.COMPONENT_DIAGNOSTIC,),
        "feature_vocabulary_is_the_producer_vocabulary": tuple(runtime.FEATURE_NAMES)
        == tuple(machinery.FEATURE_NAMES),
        "arms_share_one_adapter": len(adapters) == 1,
        "provenance_confirmed": bool(provenance["confirmed"]),
        "no_episodes_fixture_exists": not (EXPERIMENT / "EPISODES.json").exists(),
        "no_producer_fixture_in_the_experiment_directory": not any(
            (EXPERIMENT / name).exists()
            for name in ("DEMAND_STAGE1.json", "DEMAND_STAGE2.json", "DOMAIN.json")
        ),
        "probe_budget_is_one": all(
            state["probe_budget"] == 1 for state in arms.values()
        ),
    }
    return {
        "schema": "m111-input-preflight-v1",
        "confirmed": all(checks.values()),
        "checks": checks,
        "population_digest": population["population_digest"],
        "world_count": len(worlds),
        "ambiguous_world_count": len(ambiguous),
        "witness_world_count": len(witness),
        "world_digests": [item["world_digest"] for item in worlds],
        "arm_state_digests": {name: state["state_digest"] for name, state in arms.items()},
        "arm_adapter_digests": sorted(adapters),
    }


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


def _run(capsule: Path, action: str, **options: Any) -> dict[str, Any]:
    command = [str(ISOLATED_PYTHON), "-I", "-S", str(capsule / "run.py"), "--action", action]
    for key, value in options.items():
        if value is not None:
            command += ["--" + key.replace("_", "-"), str(value)]
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
            "M111 capsule produced no parsable report: %s" % (completed.stderr[:400] or error)
        )
    report["returncode"] = completed.returncode
    report["capsule_members"] = sorted(item.name for item in capsule.iterdir())
    report["input_digests"] = {
        item.name: sha256_bytes(item.read_bytes())
        for item in sorted(capsule.iterdir())
        if item.name.endswith(".json")
    }
    return report


def _sequence_summary(report: dict[str, Any]) -> dict[str, Any]:
    sequence = report.get("sequence") or {}
    return {
        "resolved_count": sequence.get("resolved_count"),
        "all_resolved": sequence.get("all_resolved"),
        "probes_spent": sequence.get("probes_spent"),
        "starting_probe_budget": sequence.get("starting_probe_budget"),
        "remaining_probe_budget": sequence.get("remaining_probe_budget"),
        "outcomes": [
            {
                "confirmed": item["confirmed"],
                "feature_row": item["feature_row"],
                "policy_fired": item["policy_fired"],
                "probes_spent": item["probes_spent"],
                "decided_by": item["decided_by"],
                "attributed_component": item["attributed_component"],
                "executes_to_target": item["executes_to_target"],
            }
            for item in sequence.get("outcomes", [])
        ],
    }


def run_experiment(population_path: Path = POPULATION_PATH) -> dict[str, Any]:
    provenance = restore_lineage()
    preflight_report = verify_inputs(provenance, population_path)
    rehearsal = population_path != POPULATION_PATH
    if not provenance["confirmed"]:
        raise QualificationRefused("M111 provenance preflight failed")
    if not preflight_report["confirmed"] and not rehearsal:
        raise QualificationRefused("M111 input preflight failed")

    arms = build_arms(provenance)
    arm_bytes = {name: runtime.encode_state(state) for name, state in arms.items()}
    population = _read_canonical(population_path, "M111 population")
    ambiguous_worlds = [
        consumer.decode_world(item) for item in population["ambiguous_worlds"]
    ]
    witness_worlds = [consumer.decode_world(item) for item in population["witness_worlds"]]

    base = Path(tempfile.mkdtemp(prefix="m111-"))
    isolated: list[dict[str, Any]] = []
    try:
        # ---- phase one: the lineage meets every world and records what it finds -------------
        pooled: list[dict[str, Any]] = []
        surveyed: list[dict[str, Any]] = []
        for stratum, worlds in (("ambiguous", ambiguous_worlds), ("witness", witness_worlds)):
            for index, world in enumerate(worlds):
                tag = "%s%d" % (stratum[0], index)
                world_bytes = canonical_json({"world": world}).encode("ascii")

                census_run = _run(
                    _build_capsule(base, tag + "-census", {"WORLD.json": world_bytes}), "census"
                )
                if not census_run.get("confirmed"):
                    raise QualificationRefused("M111 census failed on %s" % world["world_id"])
                census = census_run["census"]
                isolated.append(census_run)

                pair_run = _run(
                    _build_capsule(base, tag + "-pair", {"WORLD.json": world_bytes}), "pair"
                )
                isolated.append(pair_run)
                pair = pair_run.get("pair")
                if stratum == "ambiguous" and not pair:
                    raise QualificationRefused(
                        "M111 ambiguous world %s exhibits no pair" % world["world_id"]
                    )

                targets: list[list[int]] = []
                if pair:
                    targets += [pair["targets"][name] for name in pair["components"]]
                targets += [
                    census["canonical_targets"][str(row)]
                    for row in sorted(int(key) for key in census["canonical_targets"])
                ]
                episodes_run = _run(
                    _build_capsule(
                        base,
                        tag + "-episodes",
                        {
                            "WORLD.json": world_bytes,
                            "TARGETS.json": canonical_json({"targets": targets}).encode("ascii"),
                        },
                    ),
                    "episodes",
                )
                if not episodes_run.get("confirmed"):
                    raise QualificationRefused("M111 episode recording failed")
                isolated.append(episodes_run)
                pooled += episodes_run["episodes"]

                surveyed.append(
                    {
                        "stratum": stratum,
                        "world_id": world["world_id"],
                        "world_digest": world["world_digest"],
                        "world_bytes": world_bytes,
                        "census": {k: v for k, v in census.items() if k != "witnesses"},
                        "base_survey": pair_run.get("survey"),
                        "ambiguous_pair": pair,
                        "episodes_fixture_present": episodes_run.get("episodes_fixture_present"),
                        "episode_count": len(episodes_run["episodes"]),
                    }
                )

        record_bytes = canonical_json({"episodes": pooled}).encode("ascii")
        pooled_survey = runtime.undetermined_rows(pooled)

        # ---- phase two: one policy, from the whole record -----------------------------------
        expressibility: dict[str, Any] = {}
        for name in ("M2", "M1"):
            report = _run(
                _build_capsule(
                    base, "expressibility-" + name, {"STATE.json": arm_bytes[name]}
                ),
                "expressibility",
            )
            isolated.append(report)
            expressibility[name] = {
                **report.get("expressibility", {}),
                "policy_rule_space": report.get("policy_rule_space"),
            }

        acquire_run = _run(
            _build_capsule(
                base, "acquire", {"STATE.json": arm_bytes["M2"], "RECORD.json": record_bytes}
            ),
            "acquire",
        )
        isolated.append(acquire_run)
        if not acquire_run.get("confirmed") or "next_state" not in acquire_run:
            raise QualificationRefused("M111 generation three did not adopt a policy")
        g3 = runtime.decode_state(acquire_run["next_state"])
        g3_bytes = runtime.encode_state(g3)

        ablated_run = _run(
            _build_capsule(
                base, "acquire-ablated",
                {"STATE.json": arm_bytes["M1"], "RECORD.json": record_bytes},
            ),
            "acquire_refuse_only",
        )
        isolated.append(ablated_run)

        ablated_state = runtime.create_state(
            g3["machinery_state"], g3["consumer_state"],
            policy=None, probe_budget=g3["probe_budget"],
        )
        mutated_policy = copy.deepcopy(g3["policy"])
        mutated_state = runtime.create_state(
            g3["machinery_state"], g3["consumer_state"],
            policy=runtime.diagnostic_policy(
                mutated_policy["body"],
                [not value for value in mutated_policy["truth_table"]],
                mutated_policy["generation"],
            ),
            probe_budget=g3["probe_budget"],
        )

        # ---- phase three: competence, on the ambiguous worlds --------------------------------
        per_world: list[dict[str, Any]] = []
        for entry in surveyed:
            if entry["stratum"] != "ambiguous":
                per_world.append({k: v for k, v in entry.items() if k != "world_bytes"})
                continue
            tag = "c%d" % len(per_world)
            world_bytes = entry["world_bytes"]
            pair = entry["ambiguous_pair"]
            census = entry["census"]
            demand_a = consumer.consumer_demand("A", pair["targets"][pair["components"][0]])
            demand_b = consumer.consumer_demand("B", pair["targets"][pair["components"][1]])
            determined = consumer.consumer_demand(
                "determined", census["canonical_targets"][str(CONTRAST_ROW)]
            )
            sequences = {
                "determined_then_A": [determined, demand_a],
                "determined_then_B": [determined, demand_b],
                "A_then_determined": [demand_a, determined],
                "B_then_determined": [demand_b, determined],
            }
            sequence_bytes = {
                name: canonical_json({"demands": items}).encode("ascii")
                for name, items in sequences.items()
            }

            static: dict[str, Any] = {}
            for name in STATIC_ARMS:
                static[name] = {}
                for seq in DETERMINED_FIRST:
                    report = _run(
                        _build_capsule(
                            base, "%s-static-%s-%s" % (tag, name, seq),
                            {"WORLD.json": world_bytes, "STATE.json": arm_bytes[name],
                             "DEMANDS.json": sequence_bytes[seq]},
                        ),
                        "sequence",
                    )
                    isolated.append(report)
                    static[name][seq] = _sequence_summary(report)

            diagnostic: dict[str, Any] = {}
            for force in ("policy", "never", "always"):
                diagnostic[force] = {}
                for order in ("candidates_first", "signals_first"):
                    diagnostic[force][order] = {}
                    for seq in sequences:
                        report = _run(
                            _build_capsule(
                                base, "%s-g3-%s-%s-%s" % (tag, force, order, seq),
                                {"WORLD.json": world_bytes, "STATE.json": g3_bytes,
                                 "DEMANDS.json": sequence_bytes[seq]},
                            ),
                            "sequence", probe_order=order, force_probe=force,
                        )
                        isolated.append(report)
                        diagnostic[force][order][seq] = _sequence_summary(report)

            rollback_run = _run(
                _build_capsule(
                    base, tag + "-rollback",
                    {"WORLD.json": world_bytes, "STATE.json": g3_bytes,
                     "DEMANDS.json": canonical_json(
                         {"demands": [demand_a, demand_b]}
                     ).encode("ascii")},
                ),
                "probe_rollback",
            )
            ablation = _run(
                _build_capsule(
                    base, tag + "-ablate-three",
                    {"WORLD.json": world_bytes,
                     "STATE.json": runtime.encode_state(ablated_state),
                     "DEMANDS.json": sequence_bytes["determined_then_B"]},
                ),
                "sequence",
            )
            mutation = _run(
                _build_capsule(
                    base, tag + "-mutation",
                    {"WORLD.json": world_bytes,
                     "STATE.json": runtime.encode_state(mutated_state),
                     "DEMANDS.json": sequence_bytes["determined_then_B"]},
                ),
                "sequence",
            )
            corruption = _run(
                _build_capsule(base, tag + "-corrupt", {"STATE.json": g3_bytes}), "corruption"
            )
            isolated += [rollback_run, ablation, mutation, corruption]

            per_world.append(
                {
                    **{k: v for k, v in entry.items() if k != "world_bytes"},
                    "demands": {
                        "A": {"target": demand_a["target"], "digest": demand_a["demand_digest"]},
                        "B": {"target": demand_b["target"], "digest": demand_b["demand_digest"]},
                        "determined": {
                            "target": determined["target"],
                            "digest": determined["demand_digest"],
                        },
                    },
                    "static_arms": static,
                    "diagnostic": diagnostic,
                    "probe_rollback": rollback_run.get("probe_rollback"),
                    "ablation": {
                        "generation_three_removed": _sequence_summary(ablation),
                        "removal_returns_to_m2_byte_exactly": runtime.encode_state(ablated_state)
                        == arm_bytes["M2"],
                        "ablated_state_digest": ablated_state["state_digest"],
                    },
                    "mutation": _sequence_summary(mutation),
                    "corruption": corruption.get("corruption"),
                }
            )

        evidence: dict[str, Any] = {
            "schema": "m111-evidence-v1",
            "input_preflight": preflight_report,
            "provenance": {
                key: value for key, value in provenance.items() if not key.startswith("_")
            },
            "population_digest": population["population_digest"],
            "runtime": {
                "implementation": platform.python_implementation().lower(),
                "canonical_python": list(CANONICAL_PYTHON),
                "matches_canonical": tuple(sys.version_info[:3]) == CANONICAL_PYTHON,
                "ambiguous_row": AMBIGUOUS_ROW,
                "witness_row": WITNESS_ROW,
                "contrast_row": CONTRAST_ROW,
            },
            "pooled_record": {
                "episode_count": len(pooled),
                "worlds_contributing": len(surveyed),
                "row_components": pooled_survey["row_components"],
                "undetermined": pooled_survey["undetermined"],
                "determined": pooled_survey["determined"],
                "record_digest": sha256_bytes(record_bytes),
                "no_episodes_fixture_in_any_capsule": all(
                    item.get("episodes_fixture_present") is False for item in surveyed
                ),
            },
            "expressibility": expressibility,
            "generation_three": {
                "acquisition": acquire_run.get("acquisition"),
                "state_digest": g3["state_digest"],
                "policy_fires_on": (acquire_run.get("acquisition") or {}).get("policy_fires_on"),
                "one_policy_for_the_whole_population": True,
            },
            "ablated_acquisition": ablated_run.get("acquisition"),
            "worlds": per_world,
            "boundary": {
                "no_capsule_held_a_producer_fixture": all(
                    not any(
                        name.startswith("DEMAND_STAGE")
                        or name in ("EPISODES.json", "DOMAIN.json", "RESULT.json")
                        for name in item["capsule_members"]
                    )
                    for item in isolated
                ),
                "isolated_process_count": len(isolated),
                "arm_pids": [item["runtime"]["pid"] for item in isolated],
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
        raise QualificationRefused("M111 final protocol is absent")
    protocol = _read_canonical(PROTOCOL_PATH, "M111 final protocol")
    payload = {key: value for key, value in protocol.items() if key != "protocol_digest"}
    if protocol.get("schema") != "m111-protocol-v1" or protocol.get("protocol_digest") != digest(
        payload
    ):
        raise QualificationRefused("M111 protocol schema or digest mismatch")
    if protocol.get("status") != "frozen_protocol_owner_authorized":
        raise QualificationRefused("M111 protocol is not owner-authorized")
    if protocol.get("decisive_conditions") != EXPECTED_PREDICATES:
        raise QualificationRefused("M111 decisive predicate declaration changed")
    if tuple(sys.version_info[:3]) != CANONICAL_PYTHON:
        raise QualificationRefused("M111 canonical runtime mismatch")
    bound = protocol.get("bound_files", {})
    files = bound.get("files")
    members = bound.get("member_digests")
    modes = bound.get("member_digest_modes") or {}
    if not isinstance(files, list) or not isinstance(members, dict):
        raise QualificationRefused("M111 bound-file record is invalid")
    measured = {}
    for path in files:
        raw = (ROOT / path).read_bytes()
        if modes.get(path) == "lf_normalized":
            raw = raw.replace(b"\r\n", b"\n")
        elif modes.get(path) != "raw":
            raise QualificationRefused("M111 bound-file digest mode is undeclared")
        measured[path] = sha256_bytes(raw)
    if measured != members or digest(measured) != bound.get("digest"):
        raise QualificationRefused("M111 bound apparatus changed")
    freeze_tag = protocol.get("freeze_tag")
    if not isinstance(freeze_tag, str) or _git("cat-file", "-t", freeze_tag) != "tag":
        raise QualificationRefused("M111 freeze reference is not an annotated tag")
    if _git("rev-list", "-n", "1", freeze_tag) != _git("rev-parse", "HEAD"):
        raise QualificationRefused("M111 HEAD is not the frozen tag commit")
    if _git("status", "--porcelain"):
        raise QualificationRefused("M111 canonical worktree is not clean")
    if RESULT_PATH.exists() or CHECK_PATH.exists():
        raise QualificationRefused("M111 canonical evidence path already exists")
    return protocol


def preflight() -> dict[str, Any]:
    provenance = restore_lineage()
    inputs = verify_inputs(provenance)
    protocol = require_frozen()
    return {
        "schema": "m111-preflight-v1",
        "confirmed": inputs["confirmed"] and provenance["confirmed"],
        "inputs": inputs,
        "protocol_digest": protocol["protocol_digest"],
        "result_absent": not RESULT_PATH.exists(),
        "check_report_absent": not CHECK_PATH.exists(),
        "python": platform.python_version(),
    }


def materialize(*, authorized_by_owner: bool, understand_unique_attempt: bool) -> dict[str, Any]:
    if not authorized_by_owner or not understand_unique_attempt:
        raise QualificationRefused(
            "M111 owner authorization or unique-attempt acknowledgement absent"
        )
    protocol = require_frozen()
    evidence = run_experiment()
    result: dict[str, Any] = {
        "schema": "m111-result-v1",
        "milestone": "M111",
        "hypothesis": "H56",
        "attempt": 1,
        "protocol_digest": protocol["protocol_digest"],
        "population_digest": evidence["population_digest"],
        "producer_result_digest": evidence["provenance"]["producer_result_digest"],
        "consumer_result_digest": evidence["provenance"]["consumer_result_digest"],
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
    development.add_argument("--population", default=None)
    canonical = subparsers.add_parser("canonical")
    canonical.add_argument("--owner-authorized", action="store_true")
    canonical.add_argument("--understand-unique-attempt", action="store_true")
    arguments = parser.parse_args()
    try:
        if arguments.command == "preflight":
            report = preflight()
        elif arguments.command == "development":
            evidence = run_experiment(
                Path(arguments.population) if arguments.population else POPULATION_PATH
            )
            report = {
                "schema": "m111-development-rehearsal-v1",
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
            "schema": "m111-qualification-refusal-v1",
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
