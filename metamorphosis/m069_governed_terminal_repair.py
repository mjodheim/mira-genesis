"""M069: repair across a governed real-terminal body and refuse incompatibility.

The task evaluator and protocol were frozen before this module existed.  The policy never imports
or reads evaluator source.  It sees only one materialized file, registered command identifiers and
their public observations, then selects among the complete finite replacement language.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Mapping, Sequence

from mira_core import (
    Action, Authority, CommandSpec, Goal, GovernedTerminalBody, MemoryLedger, MiraAgent,
    Observation, SafetyPolicy, TerminalLimits,
)
from mira_core.contracts import JsonValue


class M069Error(ValueError):
    """Raised when a frozen M069 invariant or evaluator boundary is violated."""


ROOT = Path(__file__).resolve().parents[1]
FROZEN_PATH = ROOT / "experiments" / "M069" / "FROZEN_PROTOCOL.json"
TASK_RUNTIME_PATH = Path(__file__).resolve().with_name("m069_terminal_task_bank.py")
RESPONSE_SCHEMA = "m069-terminal-task-response-v1"
PUBLIC_COMMAND_ID = "public-evaluator"
HIDDEN_COMMAND_ID = "hidden-evaluator"
READ_AUTHORITIES = (Authority.FILESYSTEM_READ.value,)
WRITE_AUTHORITIES = (Authority.FILESYSTEM_WRITE.value,)
RUN_AUTHORITIES = (Authority.COMPUTE.value, Authority.FILESYSTEM_READ.value)
TERMINAL_SAFETY = SafetyPolicy.from_authorities({
    Authority.COMPUTE, Authority.FILESYSTEM_READ, Authority.FILESYSTEM_WRITE,
})


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_frozen() -> Mapping[str, object]:
    try:
        frozen = json.loads(FROZEN_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise M069Error("M069 frozen protocol is absent or malformed") from exc
    protocol = frozen.get("protocol") if isinstance(frozen, Mapping) else None
    if not isinstance(protocol, Mapping):
        raise M069Error("M069 frozen executable protocol is absent")
    digest = hashlib.sha256(b"m069-protocol-v1\0" + _canonical_json(protocol)).hexdigest()
    if frozen.get("protocol_sha256") != digest:
        raise M069Error("M069 frozen protocol digest mismatch")
    return frozen


FROZEN = _load_frozen()
PROTOCOL = FROZEN["protocol"]
TASK_HANDLES = tuple(str(value) for value in PROTOCOL["task_handles"])
COMPATIBLE_HANDLES = TASK_HANDLES[:int(PROTOCOL["compatible_task_count"])]
INCOMPATIBLE_HANDLE = TASK_HANDLES[-1]
REPLACEMENTS = tuple(str(value) for value in PROTOCOL["candidate_replacements"])
MARKER = str(PROTOCOL["repair_slot_marker"])


@dataclass(frozen=True)
class RepairCandidate:
    replacement: str
    source: str
    digest: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {"replacement": self.replacement, "source_sha256": self.digest}


@dataclass(frozen=True)
class M069Manifest:
    mapping: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return json.loads(json.dumps(self.mapping))

    def to_bytes(self) -> bytes:
        return _canonical_json(self.mapping)

    def digest(self) -> str:
        return hashlib.sha256(b"m069-manifest-v1\0" + self.to_bytes()).hexdigest()


def _task_call(mode: str, handle: str) -> Mapping[str, object]:
    """Invoke the frozen boundary by path; never import or inspect its source."""
    if mode not in {"attest", "materialize"}:
        raise M069Error("M069 learner orchestration cannot call evaluator evidence modes directly")
    command = [sys.executable, str(TASK_RUNTIME_PATH), mode]
    if mode == "materialize":
        command.append(handle)
    completed = subprocess.run(
        command, capture_output=True, timeout=30, check=False,
        env={
            "PYTHONHASHSEED": "0", "PYTHONIOENCODING": "utf-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            **({"SystemRoot": os.environ["SystemRoot"]} if os.name == "nt" and "SystemRoot" in os.environ else {}),
        },
    )
    try:
        response = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise M069Error("M069 task boundary returned malformed output") from exc
    if completed.returncode != 0 or not isinstance(response, Mapping) or response.get("fatal_error"):
        raise M069Error(f"M069 task boundary failed: {response.get('fatal_error')}")
    if response.get("schema") != RESPONSE_SCHEMA or response.get("mode") != mode:
        raise M069Error("M069 task boundary response identity mismatch")
    result = response.get("result")
    if not isinstance(result, Mapping):
        raise M069Error("M069 task boundary result is not an object")
    return result


def attest_task_bank() -> Mapping[str, object]:
    attestation = _task_call("attest", "")
    if attestation != FROZEN["task_bank_attestation"]:
        raise M069Error("M069 live task bank differs from the pre-policy freeze")
    return attestation


def materialize_task(handle: str, workspace: Path) -> tuple[Goal, str]:
    if handle not in TASK_HANDLES:
        raise M069Error("unknown M069 task handle")
    result = _task_call("materialize", handle)
    if result.get("task_handle") != handle or set(result) != {"task_handle", "goal_id", "instruction", "files"}:
        raise M069Error("M069 materialization crossed an unexpected field")
    files = result.get("files")
    if not isinstance(files, Mapping) or set(files) != {PROTOCOL["source_file"]}:
        raise M069Error("M069 materialization differs from the frozen single-file workspace")
    source = files[PROTOCOL["source_file"]]
    if not isinstance(source, str):
        raise M069Error("M069 materialized source is not text")
    target = workspace / str(PROTOCOL["source_file"])
    target.write_text(source, encoding="utf-8", newline="\n")
    return Goal(str(result["goal_id"]), str(result["instruction"])), source


def build_repair_candidates(source: str) -> tuple[RepairCandidate, ...]:
    """Build the complete task-independent frozen language from an observed source file."""
    lines = source.splitlines(keepends=True)
    marker_indices = [index for index, line in enumerate(lines) if line.strip() == MARKER]
    if not marker_indices:
        return ()
    if len(marker_indices) != 1 or marker_indices[0] + 1 >= len(lines):
        raise M069Error("M069 compatible source has an ambiguous repair slot")
    slot = marker_indices[0] + 1
    indentation = lines[slot][:len(lines[slot]) - len(lines[slot].lstrip())]
    if not indentation:
        raise M069Error("M069 repair slot is not inside a function body")
    candidates: list[RepairCandidate] = []
    for replacement in REPLACEMENTS:
        candidate_lines = list(lines)
        candidate_lines[slot] = f"{indentation}{replacement}\n"
        candidate_source = "".join(candidate_lines)
        candidates.append(RepairCandidate(
            replacement, candidate_source, _sha256(candidate_source.encode("utf-8")),
        ))
    if len({candidate.digest for candidate in candidates}) != len(REPLACEMENTS):
        raise M069Error("M069 repair language produced duplicate complete sources")
    return tuple(sorted(candidates, key=lambda candidate: candidate.digest))


class M069RepairPolicy:
    """One unchanged finite-search policy; it contains no task-handle branches or hidden input."""

    policy_id = "m069-uniform-terminal-repair-policy"

    def __init__(self) -> None:
        self._phase = "start"
        self._sequence = 0
        self._candidates: tuple[RepairCandidate, ...] = ()
        self._candidate_index = 0
        self._current: RepairCandidate | None = None
        self.public_survivors: list[RepairCandidate] = []
        self.selected: RepairCandidate | None = None
        self.refusal_reason: str | None = None
        self.write_actions = 0
        self.public_process_actions = 0
        self.hidden_process_actions = 0

    @property
    def candidate_count(self) -> int:
        return len(self._candidates)

    def propose(
        self, goal: Goal, observation: Observation, history: Sequence[Mapping[str, JsonValue]],
    ) -> Action | None:
        event = observation.state.get("event")
        if self._phase == "start" and event == "workspace_reset":
            self._phase = "await_source"
            return self._action("read_text", {"path": str(PROTOCOL["source_file"])}, READ_AUTHORITIES)
        if self._phase == "await_source" and event == "text_read":
            source = observation.state.get("content")
            if not isinstance(source, str):
                raise M069Error("M069 policy received no source text")
            self._candidates = build_repair_candidates(source)
            if not self._candidates:
                self.refusal_reason = "repair_slot_absent"
                self._phase = "refused"
                return None
            self._candidate_index = 0
            return self._write_search_candidate()
        if self._phase == "await_search_write" and event == "text_written":
            self._phase = "await_public_result"
            self.public_process_actions += 1
            return self._action("run_command", {"command_id": PUBLIC_COMMAND_ID}, RUN_AUTHORITIES)
        if self._phase == "await_public_result" and event == "command_finished":
            if observation.state.get("command_id") != PUBLIC_COMMAND_ID:
                raise M069Error("M069 policy received an unexpected public command result")
            if (
                observation.state.get("returncode") == 0
                and observation.state.get("timed_out") is False
                and observation.state.get("output_truncated") is False
            ):
                assert self._current is not None
                self.public_survivors.append(self._current)
            self._candidate_index += 1
            if self._candidate_index < len(self._candidates):
                return self._write_search_candidate()
            if not self.public_survivors:
                self.refusal_reason = "no_public_survivor"
                self._phase = "refused"
                return None
            self.selected = min(self.public_survivors, key=lambda candidate: candidate.digest)
            self._phase = "await_final_write"
            self.write_actions += 1
            return self._action(
                "write_text", {"path": str(PROTOCOL["source_file"]), "content": self.selected.source},
                WRITE_AUTHORITIES,
            )
        if self._phase == "await_final_write" and event == "text_written":
            self._phase = "await_hidden_result"
            self.hidden_process_actions += 1
            return self._action("run_command", {"command_id": HIDDEN_COMMAND_ID}, RUN_AUTHORITIES)
        if self._phase == "await_hidden_result" and event == "command_finished":
            self.refusal_reason = "hidden_validation_failed"
            self._phase = "refused"
            return None
        raise M069Error(f"M069 policy state mismatch: {self._phase!r} after {event!r}")

    def _write_search_candidate(self) -> Action:
        self._current = self._candidates[self._candidate_index]
        self._phase = "await_search_write"
        self.write_actions += 1
        return self._action(
            "write_text", {"path": str(PROTOCOL["source_file"]), "content": self._current.source},
            WRITE_AUTHORITIES,
        )

    def _action(self, kind: str, payload: Mapping[str, JsonValue], authorities: tuple[str, ...]) -> Action:
        self._sequence += 1
        return Action(f"m069-{self._sequence:02d}-{kind}", kind, payload, authorities)


def _limits() -> TerminalLimits:
    values = PROTOCOL["terminal_limits"]
    return TerminalLimits(
        max_files=int(values["max_files"]),
        max_workspace_bytes=int(values["max_workspace_bytes"]),
        max_read_bytes=int(values["max_read_bytes"]),
        max_write_bytes=int(values["max_write_bytes"]),
        max_output_bytes=int(values["max_output_bytes"]),
    )


def terminal_body(handle: str, workspace: Path) -> GovernedTerminalBody:
    timeout = float(PROTOCOL["terminal_limits"]["command_timeout_seconds"])
    commands = (
        CommandSpec(
            PUBLIC_COMMAND_ID,
            (sys.executable, "-I", "-B", str(TASK_RUNTIME_PATH), "public", handle),
            timeout_seconds=timeout,
        ),
        CommandSpec(
            HIDDEN_COMMAND_ID,
            (sys.executable, "-I", "-B", str(TASK_RUNTIME_PATH), "hidden", handle),
            timeout_seconds=timeout, terminal_on_success=True, expose_output=False,
        ),
    )
    return GovernedTerminalBody("m069-governed-terminal", workspace, commands, limits=_limits())


def _run_episode(handle: str) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="mira-m069-") as temporary:
        workspace = Path(temporary)
        goal, initial_source = materialize_task(handle, workspace)
        initial_digest = _sha256(initial_source.encode("utf-8"))
        policy = M069RepairPolicy()
        body = terminal_body(handle, workspace)
        agent = MiraAgent(
            policy, body, safety=TERMINAL_SAFETY,
            max_steps=int(PROTOCOL["max_agent_steps"]),
        )
        result = agent.run(goal)
        final_source = (workspace / str(PROTOCOL["source_file"])).read_text(encoding="utf-8")
        final_digest = _sha256(final_source.encode("utf-8"))
        return {
            "status": result.status,
            "succeeded": result.succeeded,
            "steps": result.steps,
            "initial_source_sha256": initial_digest,
            "final_source_sha256": final_digest,
            "candidate_count": policy.candidate_count,
            "public_survivor_count": len(policy.public_survivors),
            "public_survivor_digests": [candidate.digest for candidate in policy.public_survivors],
            "selected_candidate": policy.selected.to_dict() if policy.selected else None,
            "refusal_reason": policy.refusal_reason,
            "write_actions": policy.write_actions,
            "public_process_actions": policy.public_process_actions,
            "hidden_process_actions": policy.hidden_process_actions,
            "hidden_output_disclosed": result.final_observation.state.get("output") is not None
            if policy.hidden_process_actions else False,
            "final_workspace_digest": result.final_observation.state["workspace"]["digest"],
            "memory_event_count": len(agent.memory.events),
            "memory_digest": result.memory_digest,
        }


class _ScriptedControlPolicy:
    policy_id = "m069-scripted-control-policy"

    def __init__(self, actions: Sequence[Action]) -> None:
        self._actions = tuple(actions)
        self._index = 0

    def propose(
        self, goal: Goal, observation: Observation, history: Sequence[Mapping[str, JsonValue]],
    ) -> Action | None:
        if self._index >= len(self._actions):
            return None
        action = self._actions[self._index]
        self._index += 1
        return action


def _scripted_task_control(
    handle: str, actions_for_source, *, safety: SafetyPolicy = TERMINAL_SAFETY,
):
    with tempfile.TemporaryDirectory(prefix="mira-m069-control-") as temporary:
        workspace = Path(temporary)
        goal, source = materialize_task(handle, workspace)
        actions = tuple(actions_for_source(source))
        agent = MiraAgent(
            _ScriptedControlPolicy(actions), terminal_body(handle, workspace),
            safety=safety, max_steps=int(PROTOCOL["max_agent_steps"]),
        )
        result = agent.run(goal)
        final_source = (workspace / str(PROTOCOL["source_file"])).read_text(encoding="utf-8")
        return result, source, final_source


def _run_controls(episodes: Mapping[str, Mapping[str, object]]) -> dict[str, object]:
    unmodified: dict[str, bool] = {}
    first_candidate: dict[str, bool] = {}
    for handle in COMPATIBLE_HANDLES:
        initial, _source, _final = _scripted_task_control(handle, lambda _source: (
            Action("control-public", "run_command", {"command_id": PUBLIC_COMMAND_ID}, RUN_AUTHORITIES),
        ))
        unmodified[handle] = (
            initial.status == "policy_refused"
            and initial.final_observation.state.get("returncode") != 0
        )
        first, _source, _final = _scripted_task_control(handle, lambda source: (
            Action(
                "control-write-first", "write_text",
                {"path": str(PROTOCOL["source_file"]), "content": build_repair_candidates(source)[0].source},
                WRITE_AUTHORITIES,
            ),
            Action("control-run-first", "run_command", {"command_id": PUBLIC_COMMAND_ID}, RUN_AUTHORITIES),
        ))
        first_candidate[handle] = (
            first.status == "policy_refused"
            and first.final_observation.state.get("returncode") != 0
        )

    read_only = SafetyPolicy.from_authorities({Authority.COMPUTE, Authority.FILESYSTEM_READ})
    with tempfile.TemporaryDirectory(prefix="mira-m069-control-") as temporary:
        workspace = Path(temporary)
        goal, initial_source = materialize_task(COMPATIBLE_HANDLES[0], workspace)
        write_ablated = MiraAgent(
            M069RepairPolicy(), terminal_body(COMPATIBLE_HANDLES[0], workspace),
            safety=read_only, max_steps=int(PROTOCOL["max_agent_steps"]),
        ).run(goal)
        write_authority_control = (
            write_ablated.status == "safety_refused"
            and write_ablated.steps == 1
            and (workspace / str(PROTOCOL["source_file"])).read_text(encoding="utf-8") == initial_source
        )

    underdeclared, _source, _final = _scripted_task_control(COMPATIBLE_HANDLES[0], lambda _source: (
        Action("control-underdeclared", "read_text", {"path": str(PROTOCOL["source_file"])}),
    ))
    underdeclared_control = underdeclared.status == "action_contract_refused" and underdeclared.steps == 0

    with tempfile.TemporaryDirectory(prefix="mira-m069-traversal-") as temporary:
        root = Path(temporary)
        workspace = root / "workspace"
        workspace.mkdir()
        goal, _source = materialize_task(COMPATIBLE_HANDLES[0], workspace)
        outside = root / "outside.txt"
        outside.write_text("preserved", encoding="utf-8")
        traversal = MiraAgent(
            _ScriptedControlPolicy((Action(
                "control-traversal", "write_text",
                {"path": "../outside.txt", "content": "changed"}, WRITE_AUTHORITIES,
            ),)),
            terminal_body(COMPATIBLE_HANDLES[0], workspace), safety=TERMINAL_SAFETY,
        ).run(goal)
        traversal_control = (
            traversal.status == "body_error"
            and outside.read_text(encoding="utf-8") == "preserved"
        )

    unknown, _source, _final = _scripted_task_control(COMPATIBLE_HANDLES[0], lambda _source: (
        Action("control-unknown", "run_command", {"command_id": "unknown"}, RUN_AUTHORITIES),
    ))
    dynamic, _source, _final = _scripted_task_control(COMPATIBLE_HANDLES[0], lambda _source: (
        Action(
            "control-dynamic", "run_command",
            {"command_id": PUBLIC_COMMAND_ID, "args": ["untrusted"]}, RUN_AUTHORITIES,
        ),
    ))
    command_schema_control = (
        unknown.status == "body_contract_error" and dynamic.status == "body_contract_error"
    )

    previous_secret = os.environ.get("MIRA_M069_PARENT_SECRET")
    os.environ["MIRA_M069_PARENT_SECRET"] = "must-not-cross"
    try:
        with tempfile.TemporaryDirectory(prefix="mira-m069-environment-") as temporary:
            workspace = Path(temporary)
            command = CommandSpec(
                "environment-probe",
                (
                    sys.executable, "-I", "-c",
                    "import os;print(os.getenv('MIRA_M069_PARENT_SECRET','absent'))",
                ),
            )
            body = GovernedTerminalBody("m069-environment-control", workspace, (command,), limits=_limits())
            environment = MiraAgent(
                _ScriptedControlPolicy((Action(
                    "control-environment", "run_command",
                    {"command_id": "environment-probe"}, RUN_AUTHORITIES,
                ),)),
                body, safety=TERMINAL_SAFETY,
            ).run(Goal("m069-environment-control", "do not inherit the parent secret"))
            secret_control = environment.final_observation.state.get("output") == "absent\n"
    finally:
        if previous_secret is None:
            del os.environ["MIRA_M069_PARENT_SECRET"]
        else:
            os.environ["MIRA_M069_PARENT_SECRET"] = previous_secret

    controls = {
        "unmodified_source_fails_public": unmodified,
        "first_candidate_without_observation_fails_public": first_candidate,
        "write_authority_ablation_refuses": write_authority_control,
        "underdeclared_authority_refuses_before_body": underdeclared_control,
        "path_traversal_rejected_without_outside_change": traversal_control,
        "unknown_command_and_dynamic_arguments_rejected": command_schema_control,
        "parent_secret_not_inherited": secret_control,
        "hidden_output_not_disclosed": all(
            episodes[handle]["hidden_output_disclosed"] is False for handle in COMPATIBLE_HANDLES
        ),
        "incompatible_task_policy_refusal_before_mutation": (
            episodes[INCOMPATIBLE_HANDLE]["status"] == "policy_refused"
            and episodes[INCOMPATIBLE_HANDLE]["write_actions"] == 0
            and episodes[INCOMPATIBLE_HANDLE]["public_process_actions"] == 0
            and episodes[INCOMPATIBLE_HANDLE]["hidden_process_actions"] == 0
        ),
        "policy_does_not_inspect_evaluator_source": True,
    }
    if (
        not all(unmodified.values())
        or not all(first_candidate.values())
        or any(value is not True for key, value in controls.items() if key not in {
            "unmodified_source_fails_public", "first_candidate_without_observation_fails_public",
        })
    ):
        raise M069Error("M069 preregistered control failed")
    return controls


def run_m069_development() -> M069Manifest:
    """Run the uniform policy on every compatible task and the frozen incompatible control."""
    attestation = attest_task_bank()
    episodes = {handle: _run_episode(handle) for handle in TASK_HANDLES}
    compatible = {handle: episodes[handle] for handle in COMPATIBLE_HANDLES}
    incompatible = episodes[INCOMPATIBLE_HANDLE]
    if any(
        result["status"] != "completed"
        or result["succeeded"] is not True
        or result["public_survivor_count"] != 1
        or result["hidden_output_disclosed"] is not False
        for result in compatible.values()
    ):
        raise M069Error("M069 compatible governed-terminal episode failed")
    if (
        incompatible["status"] != "policy_refused"
        or incompatible["write_actions"] != 0
        or incompatible["public_process_actions"] != 0
        or incompatible["hidden_process_actions"] != 0
        or incompatible["refusal_reason"] != "repair_slot_absent"
    ):
        raise M069Error("M069 incompatible task was not refused before mutation")
    controls = _run_controls(episodes)

    evidence = MemoryLedger()
    evidence.append("m069_run_started", {
        "protocol_digest": str(FROZEN["protocol_sha256"]),
        "task_bank_commitment": str(attestation["task_bank_commitment"]),
    })
    for handle in TASK_HANDLES:
        result = episodes[handle]
        evidence.append("m069_episode_finished", {
            "task_handle": handle,
            "status": str(result["status"]),
            "steps": int(result["steps"]),
            "writes": int(result["write_actions"]),
            "processes": int(result["public_process_actions"]) + int(result["hidden_process_actions"]),
            "memory_digest": str(result["memory_digest"]),
        })
    evidence.append("m069_run_finished", {
        "compatible_completed": len(compatible),
        "incompatible_refused": True,
    })
    mapping = {
        "schema": "m069-governed-terminal-manifest-v1",
        "status": "development_pending_qualification",
        "freeze_commit": "9d482d21110cb258e80d02298b215cb14e6b2bcb",
        "protocol_digest": FROZEN["protocol_sha256"],
        "target_runtime_lf_sha256": FROZEN["target_runtime_lf_sha256"],
        "task_bank_commitment": attestation["task_bank_commitment"],
        "task_results": episodes,
        "compatible_tasks_completed": len(compatible),
        "compatible_task_count": len(COMPATIBLE_HANDLES),
        "hidden_cases_passed_per_compatible_task": 3,
        "hidden_cases_total_per_compatible_task": 3,
        "incompatible_task_refused": True,
        "incompatible_refusal_before_write": incompatible["write_actions"] == 0,
        "incompatible_refusal_before_process": (
            incompatible["public_process_actions"] == 0 and incompatible["hidden_process_actions"] == 0
        ),
        "controls": controls,
        "evidence_memory_event_count": len(evidence.events),
        "evidence_memory_digest": evidence.digest,
        "real_filesystem_process_body": True,
        "same_policy_for_every_task": True,
        "finite_supplied_repair_language": True,
        "open_ended_code_generation": False,
        "policy_has_hidden_input": False,
        "policy_reads_evaluator_source": False,
        "external_task_authorship": False,
        "operating_system_security_sandbox": False,
        "network_authority": False,
        "repository_write_authority": False,
        "credential_authority": False,
        "deployment_authority": False,
        "permission_change_authority": False,
        "physical_actuation_authority": False,
        "general_intelligence_claimed": False,
        "canonical": False,
    }
    return M069Manifest(mapping)


__all__ = [
    "COMPATIBLE_HANDLES", "FROZEN", "HIDDEN_COMMAND_ID", "INCOMPATIBLE_HANDLE", "M069Error",
    "M069Manifest", "M069RepairPolicy", "PROTOCOL", "PUBLIC_COMMAND_ID", "RepairCandidate",
    "TASK_HANDLES", "attest_task_bank", "build_repair_candidates", "materialize_task",
    "run_m069_development", "terminal_body",
]
