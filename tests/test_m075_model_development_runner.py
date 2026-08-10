from __future__ import annotations

import asyncio
import json

from metamorphosis.m074_scientific_runner import portable_file_sha256, protocol_commitment
from metamorphosis.m075_development_bank import TASKS, BankTask
from metamorphosis.m075_model_development_runner import (
    CONDITIONS, REQUIRED_CODE_PATHS, ROOT, execute_public_development, validate_protocol,
)


class FakeModel:
    backend_id = "openai-codex-exec-v1"
    model = "gpt-5.6-sol"

    def complete(self, request):
        payload = json.loads(request.input_json)
        observation = payload["observation"]
        if observation["observation_id"] == "harbor:0:reset":
            return {"decision": "act", "script": "m075-solve", "reason": None}
        if observation["state"]["returncode"] == 0:
            return {"decision": "finish", "script": None, "reason": None}
        if "epistemic_state" in payload:
            return {
                "decision": "refuse", "script": None,
                "reason": "visible failure persists with bounded budget",
            }
        return {"decision": "act", "script": "m075-solve", "reason": None}


class FakeMode:
    value = "no-network"


class FakeNetworkPolicy:
    network_mode = FakeMode()


class FakeResult:
    def __init__(self, return_code: int) -> None:
        self.return_code = return_code
        self.stdout = ""
        self.stderr = "" if return_code == 0 else "operation unavailable"


class FakeEnvironment:
    network_policy = FakeNetworkPolicy()

    def __init__(self, task: BankTask) -> None:
        self.task = task
        self.solved = False

    @property
    def environment_sha256(self):
        return self.task.environment_digest()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def inspect_security_boundary(self):
        return {"matches_declaration": True}

    def execute_probe(self, probe):
        if self.task.expected_solvability.value == "feasible":
            return 0, True
        return probe.absent_returncodes[0], True

    async def exec(self, script, timeout_sec=None):
        if self.task.expected_solvability.value == "feasible":
            self.solved = True
            return FakeResult(0)
        return FakeResult(1)

    def evaluate(self, timeout_seconds=30):
        return FakeResult(0 if self.solved else 1)


def protocol(tmp_path=None):
    order = []
    for task in TASKS:
        for condition in CONDITIONS:
            order.append({
                "episode_id": f"{len(order) + 1:02d}-{task.task_id}-{condition.arm_id}",
                "task_id": task.task_id,
                "condition_id": condition.arm_id,
            })
    value = {
        "schema": "m075-public-model-development-protocol-v1",
        "status": "committed_before_public_model_development",
        "scientific_result": False,
        "public_contaminated_development": True,
        "apparatus_commit": "0" * 40,
        "model": {
            "backend_id": "openai-codex-exec-v1",
            "model": "gpt-5.6-sol",
            "codex_cli_version": "codex-cli 0.147.0",
        },
        "budgets": {
            "max_agent_steps": 4,
            "command_timeout_seconds": 30,
            "command_output_chars": 65_536,
            "codex_decision_timeout_seconds": 180,
            "external_evaluator_timeout_seconds": 30,
        },
        "conditions": [condition.public_dict() for condition in CONDITIONS],
        "tasks": [
            {
                "task_id": task.task_id,
                "task_sha256": task.task_digest(),
                "environment_sha256": task.environment_digest(),
            }
            for task in TASKS
        ],
        "attempt_policy": {
            "attempts_per_condition_task": 1,
            "concurrency": 1,
            "replacement_permitted": False,
            "development_retry_permitted": False,
            "independent_model_samples_make_comparison_noncausal": True,
        },
        "information_boundary": {
            "task_instruction_visible_to_model": True,
            "action_observations_visible_to_model": True,
            "epistemic_self_evidence_visible_only_in_context_condition": True,
            "expected_or_probed_solvability_visible_to_model": False,
            "capability_certificates_visible_to_model": False,
            "solve_script_visible_to_model": False,
            "evaluator_or_outcome_visible_to_model": False,
            "condition_identity_visible_to_model": False,
        },
        "claim_boundary": {
            "agi": False,
            "scientific_evidence": False,
            "causal_comparison": False,
            "public_project_authored_bank": True,
            "private_cross_domain_transfer": False,
            "m074_tasks_reused": False,
        },
        "runtime": {
            "docker_server_version": "test-docker",
            "host_system": "test-host",
            "python_version": "test-python",
        },
        "raw_evidence_boundary": (
            "Preserves each complete ModelRequest and the structured JSON mapping returned by "
            "CodexExecBackend; provider transport envelopes, token accounting, sampling seed and "
            "pre-parse output whitespace are unavailable."
        ),
        "episode_order": order,
    }
    root = tmp_path if tmp_path is not None else ROOT
    value["code_sha256"] = {}
    for relative in REQUIRED_CODE_PATHS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(relative, encoding="utf-8")
        value["code_sha256"][relative] = portable_file_sha256(path)
    value["protocol_commitment_sha256"] = protocol_commitment(value)
    return value


def test_public_model_development_protocol_has_exact_noncausal_coverage(tmp_path) -> None:
    assert len(validate_protocol(protocol(tmp_path), root=tmp_path)) == 12


def test_fake_public_comparison_exercises_baseline_and_epistemic_paths() -> None:
    result = asyncio.run(execute_public_development(
        protocol(), FakeModel(), environment_factory=FakeEnvironment,
    ))
    assert result["status"] == "development_complete"
    assert len(result["episodes"]) == 12
    reports = {report["arm_id"]: report for report in result["reports"]}
    assert reports["baseline-structured-request"]["true_refusals"] == 0
    assert reports["epistemic-context-request"]["true_refusals"] == 3
    baseline = result["episodes"][0]
    enriched = result["episodes"][1]
    assert baseline["epistemic_states"] is None
    assert enriched["epistemic_states"][0]["remaining_steps_including_current"] == 4
    assert "epistemic_state" not in baseline["model_decisions"][0]["request"]["input_json"]
    assert "epistemic_state" in enriched["model_decisions"][0]["request"]["input_json"]


def test_model_development_is_explicitly_non_scientific_and_noncausal() -> None:
    value = protocol()
    assert value["scientific_result"] is False
    assert value["public_contaminated_development"] is True
    assert value["attempt_policy"]["independent_model_samples_make_comparison_noncausal"] is True
