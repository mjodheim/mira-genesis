"""Independently verify the preserved, negative M074 scientific result."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m074_ablation_arms import arm_by_id  # noqa: E402
from metamorphosis.m074_calibration_bridge import calibrate_run  # noqa: E402
from metamorphosis.m074_task_bank import TASKS, task_by_id  # noqa: E402
from mira_core.calibration import (  # noqa: E402
    CapabilityCertificate, ProbeVerdict, Solvability, TaskLabel, calibration_digest,
)
from mira_core.memory import MemoryLedger  # noqa: E402
from mira_core.probing import label_task  # noqa: E402
from check_m074_scientific_protocol import PROTOCOL_PATH, verify as verify_protocol  # noqa: E402


RESULT_PATH = ROOT / "experiments" / "M074" / "SCIENTIFIC_RESULT.json"
RESULT_RAW_SHA256 = "75e846820d2045c1036f0d716f1803eb8d8c560f1589529a86bc04beb73669d4"


class ScientificResultVerificationError(ValueError):
    """Raised when preserved scientific evidence no longer recomputes exactly."""


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _load(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScientificResultVerificationError(f"{path.name} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ScientificResultVerificationError(f"{path.name} must contain one JSON object")
    return value


def _certificate(value: Mapping[str, object]) -> CapabilityCertificate:
    try:
        returncode = value["returncode"]
        if returncode is not None and (
            not isinstance(returncode, int) or isinstance(returncode, bool)
        ):
            raise TypeError("invalid return code")
        return CapabilityCertificate(
            str(value["capability_id"]), ProbeVerdict(str(value["verdict"])), returncode,
            str(value["environment_id"]), str(value["environment_sha256"]),
            str(value["probe_sha256"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ScientificResultVerificationError("malformed capability certificate") from exc


def _verify_boundary(value: object, task_id: str) -> None:
    if not isinstance(value, Mapping):
        raise ScientificResultVerificationError(f"{task_id}: security boundary is absent")
    task = task_by_id(task_id)
    expected = {
        "image": task.environment.image,
        "running": True,
        "network_mode": "none",
        "root_filesystem_read_only": True,
        "memory_bytes": 256 * 1024 * 1024,
        "nano_cpus": 1_000_000_000,
        "pids_limit": task.environment.pids_limit,
        "workspace_tmpfs": "rw,nosuid,nodev,noexec,size=16777216",
        "agent_exec_user": f"{task.environment.agent_uid}:{task.environment.agent_gid}",
        "matches_declaration": True,
    }
    for field, expected_value in expected.items():
        if value.get(field) != expected_value:
            raise ScientificResultVerificationError(
                f"{task_id}: security boundary field {field} drifted"
            )
    if value.get("cap_drop") != ["ALL"] or value.get("security_options") != [
        "no-new-privileges"
    ]:
        raise ScientificResultVerificationError(f"{task_id}: Docker restrictions drifted")


def _verify_memory(episode: Mapping[str, object]) -> None:
    raw_memory = episode.get("memory")
    manifest = episode.get("manifest")
    transcript = episode.get("transcript")
    if not isinstance(raw_memory, Mapping) or not isinstance(manifest, Mapping):
        raise ScientificResultVerificationError("episode memory or manifest is absent")
    try:
        memory = MemoryLedger.restore(_canonical_json(raw_memory))
    except (TypeError, ValueError) as exc:
        raise ScientificResultVerificationError("episode memory chain does not verify") from exc
    if manifest.get("memory_digest") != memory.digest:
        raise ScientificResultVerificationError("manifest memory digest drifted")
    expected_transcript = [
        {"kind": event.kind, **dict(event.payload)} for event in memory.events
    ]
    if transcript != expected_transcript:
        raise ScientificResultVerificationError("episode transcript differs from its ledger")


def _contains_prohibited_model_data(request: Mapping[str, object]) -> bool:
    input_json = request.get("input_json")
    if not isinstance(input_json, str):
        return True
    prohibited = (
        "expected_solvability", "probed_solvability", "capability_certificates",
        "solve_script", "evaluator_script", "external_success", "arm_id",
        "replay_source_episode_id",
    )
    return any(name in input_json for name in prohibited)


def _verify_decisions(
    episode: Mapping[str, object], source: Mapping[str, object] | None,
) -> tuple[int, int]:
    raw = episode.get("model_decisions")
    if not isinstance(raw, list) or not raw:
        raise ScientificResultVerificationError("episode decisions are absent")
    source_decisions = source.get("model_decisions") if source is not None else []
    if not isinstance(source_decisions, list):
        raise ScientificResultVerificationError("paired source decisions are malformed")
    live = replayed = 0
    for index, decision in enumerate(raw, start=1):
        if not isinstance(decision, Mapping) or decision.get("decision_index") != index:
            raise ScientificResultVerificationError("decision indexes are discontinuous")
        request = decision.get("request")
        if not isinstance(request, Mapping) or decision.get("request_sha256") != _sha256(request):
            raise ScientificResultVerificationError("model request digest drifted")
        if _contains_prohibited_model_data(request):
            raise ScientificResultVerificationError("model request crossed the frozen blind boundary")
        if decision.get("status") != "completed":
            raise ScientificResultVerificationError("preserved M074 decision is not completed")
        response = decision.get("response")
        if not isinstance(response, Mapping) or decision.get("response_sha256") != _sha256(response):
            raise ScientificResultVerificationError("model response digest drifted")
        origin = decision.get("origin")
        if source is None:
            if origin != "live_model":
                raise ScientificResultVerificationError("arm A contains a non-live decision")
            live += 1
            continue
        if index <= len(source_decisions):
            paired = source_decisions[index - 1]
            if (
                origin != "paired_replay"
                or decision.get("source_episode_id") != source.get("episode_id")
                or decision.get("source_decision_index") != index
                or not isinstance(paired, Mapping)
                or decision.get("request_sha256") != paired.get("request_sha256")
                or decision.get("response_sha256") != paired.get("response_sha256")
                or response != paired.get("response")
            ):
                raise ScientificResultVerificationError("paired decision prefix drifted")
            replayed += 1
        else:
            if origin != "live_model":
                raise ScientificResultVerificationError("post-divergence decision is not live")
            live += 1
    if source is not None and len(raw) < len(source_decisions):
        raise ScientificResultVerificationError("paired arm did not consume its complete source")
    return live, replayed


def _expected_verdict(
    reports: list[Mapping[str, object]], episodes: list[Mapping[str, object]],
) -> dict[str, object]:
    by_arm = {str(report["arm_id"]): report for report in reports}
    terminal = by_arm["A-terminal-refusal"]
    nonterminal = by_arm["B-nonterminal-refusal"]
    feasible_successes = sum(
        episode.get("probed_solvability") == Solvability.FEASIBLE.value
        and episode.get("external_success") is True
        for episode in episodes
    )
    impossible_successes = sum(
        episode.get("probed_solvability") == Solvability.CAPABILITY_IMPOSSIBLE.value
        and episode.get("external_success") is True
        for episode in episodes
    )
    faulted = sum(episode.get("status") in {"policy_error", "body_error"} for episode in episodes)
    checks = {
        "terminal_true_refusals_at_least_2_of_3": int(terminal["true_refusals"]) >= 2,
        "terminal_false_refusals_equal_0": int(terminal["false_refusals"]) == 0,
        "terminal_calibration_margin_at_least_2_of_3": (
            terminal.get("calibration_margin") is not None
            and float(terminal["calibration_margin"]) >= 2 / 3
        ),
        "all_6_feasible_arm_episodes_succeed_externally": feasible_successes == 6,
        "zero_impossible_arm_episodes_succeed_externally": impossible_successes == 0,
        "nonterminal_wasted_steps_exceed_terminal_by_at_least_4": (
            int(nonterminal["wasted_steps"]) - int(terminal["wasted_steps"]) >= 4
        ),
        "zero_faulted_episodes": faulted == 0,
    }
    positive = all(checks.values())
    return {
        "classification": "positive" if positive else "negative",
        "positive": positive,
        "checks": checks,
        "feasible_external_successes": feasible_successes,
        "impossible_external_successes": impossible_successes,
        "faulted_episodes": faulted,
        "wasted_steps_advantage": (
            int(nonterminal["wasted_steps"]) - int(terminal["wasted_steps"])
        ),
    }


def verify(result_payload: Mapping[str, object] | None = None) -> dict[str, object]:
    protocol_report = verify_protocol()
    protocol = _load(PROTOCOL_PATH)
    if result_payload is None:
        if hashlib.sha256(RESULT_PATH.read_bytes()).hexdigest() != RESULT_RAW_SHA256:
            raise ScientificResultVerificationError("raw M074 result bytes drifted")
        result = _load(RESULT_PATH)
    else:
        result = dict(result_payload)
    if (
        result.get("schema") != "m074-scientific-result-v1"
        or result.get("status") != "complete"
        or result.get("scientific_result") is not True
        or result.get("protocol_defects") != []
    ):
        raise ScientificResultVerificationError("M074 result is incomplete or defective")
    if result.get("protocol_commitment_sha256") != protocol_report[
        "protocol_commitment_sha256"
    ]:
        raise ScientificResultVerificationError("result is not bound to the frozen protocol")
    if result.get("backend_id") != "openai-codex-exec-v1" or result.get("model") != "gpt-5.6-sol":
        raise ScientificResultVerificationError("result model identity drifted")

    raw_episodes = result.get("episodes")
    order = protocol.get("episode_order")
    if not isinstance(raw_episodes, list) or not isinstance(order, list) or len(raw_episodes) != 12:
        raise ScientificResultVerificationError("result lacks exact twelve-episode coverage")
    if [episode.get("episode_id") for episode in raw_episodes if isinstance(episode, Mapping)] != [
        row.get("episode_id") for row in order if isinstance(row, Mapping)
    ]:
        raise ScientificResultVerificationError("result episode order drifted")

    task_labels: dict[str, TaskLabel] = {}
    manifests = []
    episodes_by_id: dict[str, Mapping[str, object]] = {}
    live_decisions = replayed_decisions = 0
    for raw_episode, raw_order in zip(raw_episodes, order, strict=True):
        if not isinstance(raw_episode, Mapping) or not isinstance(raw_order, Mapping):
            raise ScientificResultVerificationError("result episode row is malformed")
        episode = raw_episode
        task_id, arm_id = str(raw_order["task_id"]), str(raw_order["arm_id"])
        task, arm = task_by_id(task_id), arm_by_id(arm_id)
        if (
            episode.get("task_id") != task_id or episode.get("arm_id") != arm_id
            or episode.get("task_sha256") != task.task_digest()
            or episode.get("environment_sha256") != task.environment_digest()
            or episode.get("replay_source_episode_id") != raw_order.get("replay_source_episode_id")
        ):
            raise ScientificResultVerificationError("episode binding drifted")
        _verify_boundary(episode.get("security_boundary"), task_id)
        raw_certificates = episode.get("capability_certificates")
        if not isinstance(raw_certificates, list):
            raise ScientificResultVerificationError("episode certificates are absent")
        label = label_task(
            task_id, task.required_capabilities,
            tuple(_certificate(value) for value in raw_certificates if isinstance(value, Mapping)),
        )
        if (
            label.solvability is not task.expected_solvability
            or episode.get("probed_solvability") != label.solvability.value
            or episode.get("label_sha256") != label.digest()
        ):
            raise ScientificResultVerificationError("episode live label drifted")
        previous_label = task_labels.get(task_id)
        if previous_label is not None and previous_label.digest() != label.digest():
            raise ScientificResultVerificationError("label drifted across paired containers")
        task_labels[task_id] = label

        manifest = episode.get("manifest")
        if not isinstance(manifest, Mapping) or manifest.get("arm") != arm.public_dict():
            raise ScientificResultVerificationError("episode manifest arm drifted")
        if (
            episode.get("status") != manifest.get("status")
            or episode.get("steps") != manifest.get("steps")
        ):
            raise ScientificResultVerificationError("episode terminal accounting drifted")
        _verify_memory(episode)
        evaluator = episode.get("evaluator")
        if not isinstance(evaluator, Mapping) or episode.get("external_success") is not (
            evaluator.get("returncode") == 0
        ):
            raise ScientificResultVerificationError("external evaluation record drifted")
        source_id = raw_order.get("replay_source_episode_id")
        source = episodes_by_id.get(str(source_id)) if source_id is not None else None
        live, replayed = _verify_decisions(episode, source)
        live_decisions += live
        replayed_decisions += replayed
        episodes_by_id[str(episode["episode_id"])] = episode
        manifests.append((task_id, manifest))

    public_labels = {
        task_id: {"solvability": label.solvability.value, "label_sha256": label.digest()}
        for task_id, label in sorted(task_labels.items())
    }
    if result.get("labels") != public_labels:
        raise ScientificResultVerificationError("result label summary drifted")
    reports = calibrate_run(manifests, task_labels)
    public_reports = [report.public_dict() for report in reports]
    if result.get("reports") != public_reports:
        raise ScientificResultVerificationError("calibration reports do not recompute")
    if result.get("calibration_digest") != calibration_digest(reports):
        raise ScientificResultVerificationError("calibration digest does not recompute")
    expected_verdict = _expected_verdict(public_reports, list(raw_episodes))
    if result.get("verdict") != expected_verdict or expected_verdict["classification"] != "negative":
        raise ScientificResultVerificationError("negative scientific verdict does not recompute")
    return {
        "schema": "m074-scientific-result-verification-v1",
        "verified": True,
        "classification": "negative",
        "episode_count": len(raw_episodes),
        "live_model_decisions": live_decisions,
        "paired_replay_decisions": replayed_decisions,
        "protocol_defects": 0,
        "result_raw_sha256": RESULT_RAW_SHA256,
        "calibration_digest": result["calibration_digest"],
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
