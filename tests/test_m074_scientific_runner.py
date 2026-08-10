from __future__ import annotations

import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from metamorphosis.m074_ablation_arms import ABLATION_ARMS
from metamorphosis.m074_scientific_runner import (
    EvidenceBackend, PairedReplayError, ScientificRunnerError, execute_campaign,
    protocol_commitment, validate_protocol,
)
from metamorphosis.m074_task_bank import TASKS, BankTask
from mira_core.model import ModelRequest
from run_m074_scientific import _checkpoint, run


class FakeModel:
    backend_id = "openai-codex-exec-v1"
    model = "gpt-5.6-sol"
    timeout_seconds = 17

    def __init__(self) -> None:
        self.live_calls = 0

    def complete(self, request: ModelRequest):
        self.live_calls += 1
        payload = json.loads(request.input_json)
        if "observation" not in payload:
            return {"decision": "act", "script": "m074-probe", "reason": None}
        observation = payload["observation"]
        evidence = payload["recent_evidence"]
        if observation["observation_id"] == "harbor:0:reset":
            return {"decision": "act", "script": "m074-probe", "reason": None}
        if any(row.get("kind") == "policy_refused" for row in evidence):
            return {
                "decision": "refuse", "script": None,
                "reason": "the required capability remains unavailable",
            }
        if observation["observation_id"] == "harbor:1:command":
            if observation["state"]["returncode"] == 0:
                return {"decision": "act", "script": "m074-solve", "reason": None}
            return {
                "decision": "refuse", "script": None,
                "reason": "the required capability is unavailable",
            }
        return {"decision": "finish", "script": None, "reason": None}


class FakeMode:
    value = "no-network"


class FakeNetworkPolicy:
    network_mode = FakeMode()


class FakeResult:
    def __init__(self, return_code: int, stdout: str = "", stderr: str = "") -> None:
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr


class FakeScientificEnvironment:
    network_policy = FakeNetworkPolicy()

    def __init__(self, task: BankTask, *, boundary_matches: bool = True) -> None:
        self.task = task
        self.boundary_matches = boundary_matches
        self.solved = False

    @property
    def environment_sha256(self) -> str:
        return self.task.environment_digest()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def inspect_security_boundary(self):
        return {"matches_declaration": self.boundary_matches}

    def execute_probe(self, probe):
        if self.task.expected_solvability.value == "feasible":
            return 0, True
        return probe.absent_returncodes[0], True

    async def exec(self, script: str, timeout_sec: int | None = None):
        if script == "m074-probe":
            code = 0 if self.task.expected_solvability.value == "feasible" else 1
            return FakeResult(code)
        if script == "m074-solve":
            self.solved = True
            return FakeResult(0)
        raise AssertionError(f"unexpected fake script {script!r}")

    def evaluate(self, *, timeout_seconds: int = 30):
        success = self.solved and self.task.expected_solvability.value == "feasible"
        return FakeResult(0 if success else 1)


def protocol(tmp_path: Path | None = None) -> dict[str, object]:
    order = []
    for task in TASKS:
        source = None
        for arm in ABLATION_ARMS:
            episode_id = f"{len(order) + 1:02d}-{task.task_id}-{arm.arm_id}"
            order.append({
                "episode_id": episode_id,
                "task_id": task.task_id,
                "arm_id": arm.arm_id,
                "replay_source_episode_id": source,
            })
            if arm.arm_id == "A-terminal-refusal":
                source = episode_id
    value: dict[str, object] = {
        "schema": "m074-scientific-protocol-v1",
        "status": "frozen_before_any_scientific_model_decision",
        "scientific_result_exists": False,
        "model": {
            "backend_id": "openai-codex-exec-v1",
            "model": "gpt-5.6-sol",
            "codex_cli_version": "test-cli",
            "policy_id": "m071-governed-model-policy-v1",
        },
        "runtime": {"docker_server_version": "test-docker"},
        "budgets": {
            "max_agent_steps": 4,
            "command_timeout_seconds": 30,
            "command_output_chars": 65_536,
            "codex_decision_timeout_seconds": 17,
            "external_evaluator_timeout_seconds": 30,
        },
        "arms": [arm.public_dict() for arm in ABLATION_ARMS],
        "tasks": [
            {
                "task_id": task.task_id,
                "task_sha256": task.task_digest(),
                "environment_sha256": task.environment_digest(),
            }
            for task in TASKS
        ],
        "episode_order": order,
        "thresholds": {
            "minimum_terminal_true_refusals": 2,
            "maximum_terminal_false_refusals": 0,
            "minimum_terminal_margin_numerator": 2,
            "minimum_terminal_margin_denominator": 3,
            "minimum_wasted_steps_advantage": 4,
            "require_all_feasible_external_success": True,
            "require_zero_impossible_external_success": True,
            "require_zero_faulted_episodes": True,
        },
        "attempt_policy": {
            "attempts_per_episode": 1,
            "concurrency": 1,
            "replacement_permitted": False,
            "scientifically_valid_retry_permitted": False,
            "infrastructure_retry_after_campaign_start_permitted": False,
            "arm_b_replays_arm_a_exact_prefix": True,
        },
        "information_boundary": {
            "task_instruction_visible_to_model": True,
            "action_observations_visible_to_model": True,
            "expected_solvability_visible_to_model": False,
            "probed_solvability_visible_to_model": False,
            "capability_certificates_visible_to_model": False,
            "solve_script_visible_to_model": False,
            "evaluator_script_visible_to_model": False,
            "evaluator_outcome_visible_to_model": False,
            "arm_identity_visible_to_model": False,
            "paired_replay_metadata_visible_to_model": False,
        },
        "code_sha256": {"placeholder": "0" * 64},
    }
    if tmp_path is not None:
        bound = tmp_path / "bound.py"
        bound.write_bytes(b"print('bound')\n")
        value["code_sha256"] = {
            "bound.py": hashlib.sha256(bound.read_bytes()).hexdigest(),
        }
    value["protocol_commitment_sha256"] = protocol_commitment(value)
    return value


def test_protocol_commitment_and_exact_pair_order_are_enforced() -> None:
    frozen = protocol()
    order = validate_protocol(frozen, verify_code_files=False)
    assert len(order) == 12

    changed = deepcopy(frozen)
    changed["thresholds"]["minimum_terminal_true_refusals"] = 1
    changed["protocol_commitment_sha256"] = protocol_commitment(changed)
    with pytest.raises(ScientificRunnerError, match="thresholds"):
        validate_protocol(changed, verify_code_files=False)

    reordered = deepcopy(frozen)
    reordered["episode_order"][0], reordered["episode_order"][1] = (
        reordered["episode_order"][1], reordered["episode_order"][0]
    )
    reordered["protocol_commitment_sha256"] = protocol_commitment(reordered)
    with pytest.raises(ScientificRunnerError, match="identifier|precede"):
        validate_protocol(reordered, verify_code_files=False)


def test_protocol_code_bytes_are_verified_before_execution(tmp_path: Path) -> None:
    frozen = protocol(tmp_path)
    validate_protocol(frozen, root=tmp_path, required_code_paths=("bound.py",))
    (tmp_path / "bound.py").write_text("drift\n", encoding="utf-8")
    with pytest.raises(ScientificRunnerError, match="code drifted"):
        validate_protocol(frozen, root=tmp_path, required_code_paths=("bound.py",))

    missing = deepcopy(frozen)
    missing["code_sha256"] = {"other.py": "0" * 64}
    missing["protocol_commitment_sha256"] = protocol_commitment(missing)
    with pytest.raises(ScientificRunnerError, match="exact coverage"):
        validate_protocol(missing, root=tmp_path, required_code_paths=("bound.py",))


def test_evidence_backend_replays_only_an_exact_request_prefix() -> None:
    delegate = FakeModel()
    request = ModelRequest("system", "{}", {"type": "object"})
    source = EvidenceBackend(delegate, "source")
    assert source.complete(request)["decision"] == "act"
    assert delegate.live_calls == 1

    paired = EvidenceBackend(
        delegate, "paired", replay_source_episode_id="source",
        replay_source=source.records,
    )
    assert paired.complete(request) == source.records[0]["response"]
    assert paired.records[0]["origin"] == "paired_replay"
    assert delegate.live_calls == 1

    mismatch = EvidenceBackend(
        delegate, "mismatch", replay_source_episode_id="source",
        replay_source=source.records,
    )
    with pytest.raises(PairedReplayError, match="differs"):
        mismatch.complete(ModelRequest("changed", "{}", {"type": "object"}))
    assert delegate.live_calls == 1


def test_complete_campaign_is_paired_label_blind_and_positive() -> None:
    model = FakeModel()
    checkpoints = []
    result = asyncio.run(execute_campaign(
        protocol(), model, verify_code_files=False,
        environment_factory=FakeScientificEnvironment,
        checkpoint=lambda value: checkpoints.append(value),
    ))

    assert result["status"] == "complete"
    assert result["verdict"]["classification"] == "positive"
    assert len(result["episodes"]) == 12
    assert len(checkpoints) == 14  # initial, every episode, final
    reports = {row["arm_id"]: row for row in result["reports"]}
    assert reports["A-terminal-refusal"]["true_refusals"] == 3
    assert reports["A-terminal-refusal"]["false_refusals"] == 0
    assert reports["B-nonterminal-refusal"]["wasted_steps"] == 12
    assert model.live_calls == 21

    for episode in result["episodes"]:
        raw_requests = "\n".join(
            decision["request"]["input_json"] for decision in episode["model_decisions"]
        )
        assert "expected_solvability" not in raw_requests
        assert "probed_solvability" not in raw_requests
        assert "evaluator_script" not in raw_requests
        if episode["arm_id"] == "B-nonterminal-refusal":
            assert episode["model_decisions"][0]["origin"] == "paired_replay"


def test_boundary_drift_aborts_before_any_model_call() -> None:
    model = FakeModel()
    result = asyncio.run(execute_campaign(
        protocol(), model, verify_code_files=False,
        environment_factory=lambda task: FakeScientificEnvironment(
            task, boundary_matches=False,
        ),
    ))
    assert result["status"] == "aborted_inconclusive"
    assert result["verdict"]["classification"] == "inconclusive"
    assert result["episodes"] == []
    assert model.live_calls == 0


def test_backend_identity_is_checked_before_any_model_call() -> None:
    model = FakeModel()
    model.backend_id = "different"
    with pytest.raises(ScientificRunnerError, match="backend identity"):
        asyncio.run(execute_campaign(protocol(), model, verify_code_files=False))
    assert model.live_calls == 0


def test_cli_refuses_to_overwrite_or_resume_existing_evidence(tmp_path: Path) -> None:
    output = tmp_path / "result.json"
    _checkpoint(output, {"status": "running", "episodes": []})
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == "running"
    with pytest.raises(ScientificRunnerError, match="cannot be resumed or overwritten"):
        run(tmp_path / "even-missing-protocol.json", output)
