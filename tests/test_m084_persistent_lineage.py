"""Regressions for M084, one persistent lineage across four stages and three real substrates.

Container-backed tests are gated behind MIRA_RUN_DOCKER_TESTS=1. The structural tests run everywhere
and cover what decides whether the result means anything: that the mechanisms are imported rather
than restated, that no stage runs in the parent process, that the induced predicate is the kind that
can transfer, that a broken journal is detected and restored against an independently recorded
digest, and that the ablation removes acquisitions without removing identity.
"""
from __future__ import annotations

import ast
import copy
import json
import os
from pathlib import Path

import pytest

from metamorphosis.m084_persistent_lineage import (
    ARMS,
    GOALS_PER_STAGE,
    STAGE_SUBSTRATES,
    Goal,
    LineageError,
    Organism,
    build_bank,
    build_stage_goals,
    carrier_name,
    evaluate,
    plan_for,
    role_of,
    runnable,
    stage_carriers,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "experiments/M084"
MODULE = ROOT / "metamorphosis/m084_persistent_lineage.py"
RUNNER = ROOT / "scripts/run_m084_lineage.py"
CHILD = ROOT / "scripts/run_m084_stage.py"

requires_docker = pytest.mark.skipif(
    os.getenv("MIRA_RUN_DOCKER_TESTS") != "1",
    reason="real Docker integration is opt-in",
)


@pytest.fixture(scope="module")
def protocol() -> dict:
    return json.loads((BASE / "PROTOCOL.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def salt(protocol: dict) -> bytes:
    return bytes.fromhex(protocol["episode_generation"]["salt_hex"])


@pytest.fixture(scope="module")
def bank(salt: bytes) -> tuple[Goal, ...]:
    return build_bank(salt)


# -- the bank -------------------------------------------------------------------------------

def test_bank_shape_and_determinism(salt: bytes, bank: tuple[Goal, ...]) -> None:
    assert len(bank) == GOALS_PER_STAGE * len(STAGE_SUBSTRATES)
    assert [g.commitment() for g in build_bank(salt)] == [g.commitment() for g in bank]


def test_reachability_split_matches_the_frozen_protocol(
    protocol: dict, bank: tuple[Goal, ...],
) -> None:
    reachable = [g for g in bank if g.reachable]
    assert len(reachable) == protocol["goals"]["reachable_total"] == 11
    assert len(bank) - len(reachable) == protocol["goals"]["must_refuse_total"] == 5
    per_stage = [
        sum(1 for g in bank if g.stage == stage and g.reachable)
        for stage in range(len(STAGE_SUBSTRATES))
    ]
    assert per_stage == protocol["goals"]["reachable_per_stage"] == [3, 3, 2, 3]


def test_the_desktop_cannot_clear_and_every_other_substrate_can() -> None:
    """Removal really is absent on the desktop; that is why affordance discovery is load-bearing."""

    for stage, substrate in enumerate(STAGE_SUBSTRATES):
        clear_goal = build_stage_goals(bytes(32), stage)[1]
        assert clear_goal.kind == "clear"
        assert clear_goal.reachable is (substrate != "desktop")


def test_the_returning_stage_uses_names_the_first_stage_never_saw() -> None:
    """Otherwise stage 3 would test recall of a string, not transfer of an induced predicate."""

    first = set(stage_carriers(0).values())
    last = set(stage_carriers(3).values())
    assert STAGE_SUBSTRATES[0] == STAGE_SUBSTRATES[3] == "shell"
    assert first.isdisjoint(last)


def test_the_trap_is_the_cheapest_carrier_of_its_group(bank: tuple[Goal, ...]) -> None:
    """A cost-minimising planner must walk into it deterministically, not by luck."""

    for goal in bank:
        if goal.kind != "repair":
            continue
        substrate = STAGE_SUBSTRATES[goal.stage]
        costs = [role_of(substrate, name) for name in goal.group]
        assert costs[0] == "trap"


# -- what is imported, and what deliberately is not -----------------------------------------

def _imports(path: Path) -> dict[str, set[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            found.setdefault(node.module, set()).update(alias.name for alias in node.names)
    return found


def test_the_qualified_mechanisms_are_imported_not_restated() -> None:
    imported = _imports(MODULE)
    assert "Journal" in imported["metamorphosis.m077_long_horizon_recovery"]
    assert "GENESIS_DIGEST" in imported["metamorphosis.m077_long_horizon_recovery"]
    assert {"Table", "ExceptionEntry"} <= imported["metamorphosis.m080_continual_retention"]
    assert "uniform_cost_plans" in imported["metamorphosis.bounded_search"]
    assert "ShellEnvironment" in imported["metamorphosis.m081_two_real_environments"]
    assert "BrowserEnvironment" in imported["metamorphosis.m082_browser_environment"]
    assert "DesktopEnvironment" in imported["metamorphosis.m083_gui_desktop_session"]

    defined = {n.name for n in ast.walk(ast.parse(MODULE.read_text(encoding="utf-8")))
               if isinstance(n, ast.ClassDef)}
    for name in ("Journal", "Table", "ExceptionEntry", "ShellEnvironment",
                 "BrowserEnvironment", "DesktopEnvironment"):
        assert name not in defined


def test_m081s_agent_is_deliberately_not_imported(protocol: dict) -> None:
    """It replays a precomputed action list. Citing it would claim a reuse this does not have."""

    imported = _imports(MODULE)
    assert "Agent" not in imported.get("metamorphosis.m081_two_real_environments", set())
    finding = protocol["recorded_finding_about_the_parent_results"]
    assert finding["m081_agent_imported"] is False
    assert finding["m081_agent_not_imported_is_deliberate"] is True
    assert finding["m081_m082_m083_agent_perceives_plans_or_detects_failure"] is False


def test_m079_and_m084_share_one_search() -> None:
    from metamorphosis import m079_planning_clarification as m079

    source = (ROOT / "metamorphosis/m079_planning_clarification.py").read_text(encoding="utf-8")
    assert "uniform_cost_plans" in source
    assert "heapq" not in source, "the search was copied back into M079 instead of shared"
    assert "uniform_cost_plans" in _imports(ROOT / "metamorphosis/m079_planning_clarification.py")[
        "metamorphosis.bounded_search"
    ]
    assert callable(m079.satisfying_plans)


# -- the harness must not hold the state ------------------------------------------------------

def test_the_parent_never_executes_a_stage() -> None:
    tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
    called = {
        node.func.id for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    for forbidden in ("run_stage", "pursue", "complete", "plan_for", "open_embodiment"):
        assert forbidden not in called, f"the parent calls {forbidden} in its own process"
    assert "subprocess.run" in RUNNER.read_text(encoding="utf-8")


def test_the_child_records_the_digest_of_the_file_it_loaded() -> None:
    """The chain of serializations is carried by the organism, not asserted by the harness."""

    source = CHILD.read_text(encoding="utf-8")
    assert "loaded_file_sha256" in source
    assert "written_file_sha256" in source
    assert "journal_verifies" in source


def test_the_runner_never_passes_the_rehearsal_salt_outside_rehearsal() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert '"--salt-hex", salt.hex()' in source
    assert "if rehearsal:" in source


# -- the organism ------------------------------------------------------------------------------

def test_serialization_round_trips_exactly() -> None:
    organism = Organism.genesis(bytes(32))
    organism.remember("shell", carrier_name("shell", 0, "trap"), False)
    organism.remember_affordance("shell", "remove", True)
    organism.refresh_predicate("shell", 0)
    organism.checkpoint(0)
    restored = Organism.from_json(json.loads(json.dumps(organism.to_json())))
    assert restored.live_digest() == organism.live_digest()
    assert restored.predicates == organism.predicates


def test_a_broken_journal_is_detected_and_restored_to_the_recorded_digest() -> None:
    organism = Organism.genesis(bytes(32))
    organism.remember("shell", carrier_name("shell", 0, "trap"), False)
    organism.refresh_predicate("shell", 0)
    organism.checkpoint(0)
    before = organism.live_digest()

    organism.journal_digests.append("0" * 64)
    organism.predicates.pop("shell")
    assert organism.journal_verifies() is False

    restored = organism.restore_last_checkpoint()
    assert restored == before
    assert organism.journal_verifies() is True
    assert "shell" in organism.predicates


def test_restoration_is_not_compared_against_the_checkpoints_own_digest() -> None:
    """M080 recorded a rollback proof that compared a saved state to itself and could never fail."""

    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    method = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "restore_last_checkpoint"
    )
    body = ast.unparse(method)
    assert "self.live_digest()" in body
    assert '["digest"]' not in body


def test_the_ablation_removes_acquisitions_and_keeps_identity() -> None:
    organism = Organism.genesis(bytes(32))
    organism.remember("shell", carrier_name("shell", 0, "trap"), False)
    organism.remember_affordance("shell", "remove", True)
    organism.refresh_predicate("shell", 0)
    organism.policy["verification"] = "per_goal"
    organism.body_version = 2
    identity, version = organism.lineage_id, organism.body_version
    journal = len(organism.journal_payloads)

    organism.forget_acquisitions()

    assert organism.predicates == {} and organism.affordances == {}
    assert organism.memory.used() == 0
    assert organism.policy["verification"] == "end_of_stage"
    assert (organism.lineage_id, organism.body_version) == (identity, version)
    assert len(organism.journal_payloads) == journal


def test_a_fresh_organism_per_stage_has_a_different_identity() -> None:
    identities = {
        Organism.genesis(bytes(32) + b"fresh" + stage.to_bytes(4, "big")).lineage_id
        for stage in range(len(STAGE_SUBSTRATES))
    }
    assert len(identities) == len(STAGE_SUBSTRATES)


# -- induction ---------------------------------------------------------------------------------

def test_the_induced_predicate_is_the_shortest_separating_prefix() -> None:
    organism = Organism.genesis(bytes(32))
    organism.remember("shell", "sealed-a0", False)
    organism.remember("shell", "secure-a0", True)
    organism.remember("shell", "secure-b0", True)
    assert organism.induce_predicate("shell") == {"kind": "prefix", "value": "sea"}


def test_the_induced_predicate_transfers_to_names_never_seen() -> None:
    """A longest-prefix rule would carry the stage tag and transfer to nothing."""

    organism = Organism.genesis(bytes(32))
    organism.remember("shell", "sealed-a0", False)
    organism.remember("shell", "secure-a0", True)
    organism.refresh_predicate("shell", 0)
    assert organism.rejects("shell", "sealed-z3") is True
    assert organism.rejects("shell", "secure-a3") is False


def test_amendment_a1_refuses_to_generalize_from_one_sided_evidence() -> None:
    """The rehearsal's false refusal: with no durable carrier seen, `sea` collapsed to `s`."""

    organism = Organism.genesis(bytes(32))
    organism.remember("browser", carrier_name("browser", 1, "trap"), False)
    predicate = organism.induce_predicate("browser")
    assert predicate == {"kind": "exact", "value": ["sealed-a1"]}

    organism.refresh_predicate("browser", 1)
    assert organism.rejects("browser", "secure-a1") is False
    assert organism.rejects("browser", "sealed-a1") is True


def test_amendment_a1_generalizes_once_the_evidence_is_two_sided() -> None:
    organism = Organism.genesis(bytes(32))
    organism.remember("browser", carrier_name("browser", 1, "trap"), False)
    organism.remember("browser", carrier_name("browser", 1, "alt1"), True)
    assert organism.induce_predicate("browser") == {"kind": "prefix", "value": "sea"}


def test_amendment_a2_records_a_verified_carrier_as_durable(salt: bytes) -> None:
    from metamorphosis.m084_persistent_lineage import _note_durable

    goal = build_stage_goals(salt, 0)[0]
    organism = Organism.genesis(salt)
    organism.remember("shell", goal.group[0], False)
    _note_durable(organism, "shell", 0, goal.redacted(), {goal.group[1]: goal.value})

    assert organism.recall("shell", goal.group[1]) is True
    assert organism.predicates["shell"] == {"kind": "prefix", "value": "sea"}


def test_no_predicate_without_a_non_durable_observation() -> None:
    organism = Organism.genesis(bytes(32))
    organism.remember("shell", "secure-a0", True)
    assert organism.induce_predicate("shell") is None


def test_an_unknown_carrier_is_rejected_by_the_memory() -> None:
    organism = Organism.genesis(bytes(32))
    with pytest.raises(LineageError):
        organism.remember("shell", "not-a-declared-carrier", True)


# -- planning and refusal ------------------------------------------------------------------------

def _view(goal: Goal) -> dict:
    return goal.redacted()


def test_planning_avoids_a_carrier_known_non_durable(salt: bytes) -> None:
    goal = build_stage_goals(salt, 0)[0]
    organism = Organism.genesis(salt)
    observation = {name: None for name in goal.group}

    naive = plan_for(
        _view(goal), observation, organism=organism, substrate="shell",
        removal_believed_effective=False,
    )
    assert naive is not None and naive[1][0][1] == goal.group[0]

    organism.remember("shell", goal.group[0], False)
    informed = plan_for(
        _view(goal), observation, organism=organism, substrate="shell",
        removal_believed_effective=False,
    )
    assert informed is not None and informed[1][0][1] != goal.group[0]


def test_refusal_is_the_absence_of_a_plan_not_an_exhausted_search(salt: bytes) -> None:
    goal = build_stage_goals(salt, 0)[3]
    organism = Organism.genesis(salt)
    organism.remember("shell", goal.group[0], False)
    assert plan_for(
        _view(goal), {name: None for name in goal.group}, organism=organism,
        substrate="shell", removal_believed_effective=False,
    ) is None


def test_a_clear_goal_has_no_plan_where_removal_is_ineffective(salt: bytes) -> None:
    goal = build_stage_goals(salt, 2)[1]
    organism = Organism.genesis(salt)
    observation = {goal.group[0]: "cyan"}
    assert plan_for(
        _view(goal), observation, organism=organism, substrate="desktop",
        removal_believed_effective=False,
    ) is None
    assert plan_for(
        _view(goal), observation, organism=organism, substrate="desktop",
        removal_believed_effective=True,
    ) is not None


# -- the M083 change is additive -----------------------------------------------------------------

def test_the_desktop_state_method_is_unchanged_and_colour_at_is_additive() -> None:
    source = (ROOT / "metamorphosis/m083_gui_desktop_session.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    environment = next(
        n for n in ast.walk(tree)
        if isinstance(n, ast.ClassDef) and n.name == "DesktopEnvironment"
    )
    methods = {n.name for n in environment.body if isinstance(n, ast.FunctionDef)}
    assert "colour_at" in methods
    state = next(n for n in environment.body if isinstance(n, ast.FunctionDef) and n.name == "state")
    assert "_screenshot_colour" in ast.unparse(state)


# -- the frozen threshold --------------------------------------------------------------------

def _preserved() -> dict:
    path = BASE / "RESULT.json"
    if not path.exists():
        pytest.skip("the M084 result has not been preserved yet")
    return json.loads(path.read_text(encoding="utf-8"))


def test_preserved_result_is_single_attempt_and_not_a_rehearsal() -> None:
    preserved = _preserved()
    assert preserved["attempt"] == 1
    assert preserved["retried"] is False
    assert preserved["rehearsal"] is False
    assert preserved["external_model_called"] is False
    for arm in ARMS:
        assert preserved["arms"][arm]["rehearsal_salt_used"] is False


def test_preserved_bank_replays(salt: bytes, bank: tuple[Goal, ...]) -> None:
    path = BASE / "BANK_COMMITMENT.json"
    if not path.exists():
        pytest.skip("the M084 bank has not been bound yet")
    bound = json.loads(path.read_text(encoding="utf-8"))
    assert [g.commitment() for g in bank] == [row["commitment"] for row in bound["goals"]]


def test_preserved_verdict_recomputes_from_the_preserved_arms() -> None:
    preserved = _preserved()
    verdict = evaluate(preserved["arms"])
    assert verdict.positive == (preserved["verdict"] == "positive")
    assert list(verdict.reasons) == preserved["failed_conditions"]


def test_evaluation_rejects_a_lineage_that_reprobes_on_return() -> None:
    preserved = _preserved()
    degraded = copy.deepcopy(preserved["arms"])
    degraded["lineage"]["per_stage"][-1]["diagnostic_probes"] = 1
    assert evaluate(degraded).positive is False
    assert any("P3" in reason for reason in evaluate(degraded).reasons)


def test_evaluation_rejects_an_ablation_that_costs_nothing() -> None:
    preserved = _preserved()
    degraded = copy.deepcopy(preserved["arms"])
    degraded["acquisition_ablated"]["per_stage"][-1]["diagnostic_probes"] = 0
    assert evaluate(degraded).positive is False
    assert any("P4" in reason for reason in evaluate(degraded).reasons)


def test_evaluation_rejects_a_false_refusal() -> None:
    preserved = _preserved()
    degraded = copy.deepcopy(preserved["arms"])
    degraded["lineage"]["false_refusals"] = 1
    assert evaluate(degraded).positive is False


def test_evaluation_rejects_a_stage_run_in_the_parent() -> None:
    preserved = _preserved()
    degraded = copy.deepcopy(preserved["arms"])
    degraded["lineage"]["executed_in_child_process"] = False
    assert evaluate(degraded).positive is False
    assert any("P11" in reason for reason in evaluate(degraded).reasons)


def test_evaluation_rejects_a_restoration_that_does_not_match() -> None:
    preserved = _preserved()
    degraded = copy.deepcopy(preserved["arms"])
    degraded["lineage"]["restored_digest"] = "0" * 64
    assert evaluate(degraded).positive is False
    assert any("P7" in reason for reason in evaluate(degraded).reasons)


def test_evaluation_rejects_a_leaking_ablation() -> None:
    preserved = _preserved()
    degraded = copy.deepcopy(preserved["arms"])
    degraded["fresh_each_stage"]["per_stage"][0]["actions"] += 1
    assert evaluate(degraded).positive is False
    assert any("P9" in reason for reason in evaluate(degraded).reasons)


def test_claim_boundary_stays_bounded(protocol: dict) -> None:
    boundary = protocol["claim_boundary"]
    for key in (
        "establishes_cross_domain_transfer", "closes_generality_gate_g4",
        "closes_generality_gate_g6", "closes_generality_gate_g7",
        "establishes_general_desktop_competence", "establishes_open_ended_evolution",
        "establishes_general_autonomy", "establishes_structural_retention_without_replay",
        "genesis_gate_2_evidence", "genesis_gate_3_evidence", "agi_evidence",
    ):
        assert boundary[key] is False


def test_the_protocol_forbids_calling_a_fact_transfer_cross_domain(protocol: dict) -> None:
    prohibited = protocol["prohibited_adaptation"]
    assert any("cross-domain transfer" in rule for rule in prohibited)
    assert protocol["acquisitions"]["F"]["facts_offered_across_substrates"] is False


def test_no_authority_is_granted_to_the_organism(protocol: dict) -> None:
    envelope = protocol["authority_envelope"]
    for key, expected in (
        ("repository_write_authority_granted_to_the_organism", False),
        ("credential_authority_granted", False),
        ("network_authority_granted", False),
        ("deployment_authority_granted", False),
        ("permission_changing_authority_granted", False),
        ("containers_run_with_networking_disabled", True),
        ("host_repository_or_docker_socket_mounted", False),
    ):
        assert envelope[key] is expected


@requires_docker
def test_the_three_substrates_are_reachable() -> None:
    assert runnable()
