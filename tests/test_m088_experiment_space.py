"""M088, attacked where the result could be manufactured rather than constructed."""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from metamorphosis.m088_experiment import (
    CONSTRUCTOR_RULES,
    META_PRIMITIVES,
    ConstructorError,
    ExperimentConstructor,
    apply_meta_primitive,
    build_constructor,
    candidate_meta_transformations,
    construct,
    constructive_image,
    m0_constructor,
    outside_image,
)
from metamorphosis.m088_lineage import (
    ARMS,
    CEILING_ARMS,
    CONDITIONS,
    DEVELOPMENT_WORLD,
    QUALIFICATION_WORLDS,
    encounter,
    evaluate,
    hidden_outside_constructive_image,
    observe_limitation,
    rollback_proof,
)
from metamorphosis.m088_worlds import (
    QUALIFICATION_POOL,
    WORLDS,
    WorldError,
    all_worlds,
    materialize_qualification,
    qualified_world,
    world,
)


ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / "experiments/M088/RESULT.json"
SALT = "m088-qualification-salt-2026-08-13"
M1_STEPS = (("add_sequence_constructor", None), ("add_order_sensitivity", None))


def _m1() -> ExperimentConstructor:
    return build_constructor(m0_constructor(), M1_STEPS)


# --------------------------------------------------------------------------------------------
# M0 is a real limitation, proved by exhaustion
# --------------------------------------------------------------------------------------------


def test_m0_builds_only_single_action_programs() -> None:
    item = world(DEVELOPMENT_WORLD)
    for program in construct(m0_constructor(), item.action_names, item.observer_names):
        assert program.depth == 1
        body = [step for step in program.steps if step not in {"reset", "observe"}]
        assert len(body) == 1, program.steps


@pytest.mark.parametrize("world_id", WORLDS)
def test_no_program_in_m0_image_resolves_any_world(world_id: str) -> None:
    """The inexpressibility proof: the COMPLETE image is enumerated and exhausted."""

    limitation = observe_limitation(world(world_id))
    assert limitation["resolved_by_prior_constructor"] is False
    assert limitation["prior_correct"] is False
    assert len(limitation["exhaustive_survivors"]) > 1


@pytest.mark.parametrize("world_id", WORLDS)
def test_the_adopted_constructor_resolves_every_world(world_id: str) -> None:
    record = encounter(world(world_id), _m1(), prior=m0_constructor())
    assert record.correct
    assert record.outside_prior_image, "the discriminating program was already in M0's image"


@pytest.mark.parametrize("world_id", WORLDS)
def test_the_discriminating_program_is_outside_the_enumerated_m0_image(world_id: str) -> None:
    item = world(world_id)
    record = encounter(item, _m1(), prior=m0_constructor())
    image = constructive_image(m0_constructor(), item.action_names, item.observer_names)
    for steps in record.outside_prior_image:
        assert tuple(steps) not in image
        assert outside_image(steps, m0_constructor(), item.action_names, item.observer_names)


def test_a_program_inside_the_m0_image_is_not_reported_as_outside() -> None:
    item = world(DEVELOPMENT_WORLD)
    inside = sorted(constructive_image(m0_constructor(), item.action_names, item.observer_names))[0]
    assert not outside_image(inside, m0_constructor(), item.action_names, item.observer_names)


# --------------------------------------------------------------------------------------------
# no meta-primitive encodes the answer
# --------------------------------------------------------------------------------------------


def test_no_meta_primitive_or_rule_names_a_world_candidate_or_program() -> None:
    forbidden = (
        "send_a", "send_b", "follow_x", "follow_y", "write", "flush", "crash",
        "protocol", "graph", "service", "order_sensitive", "path_sensitive", "buffered",
    )
    for name in META_PRIMITIVES + CONSTRUCTOR_RULES:
        for token in forbidden:
            assert token not in name.lower(), (name, token)


def test_the_constructor_module_contains_no_world_specific_branch() -> None:
    tree = ast.parse((ROOT / "metamorphosis/m088_experiment.py").read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc:
                docstrings.add(doc)
    literals = {
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    } - docstrings
    for token in ("send_a", "follow_x", "write", "flush", "stateful_protocol", "path_graph"):
        assert not any(token in item for item in literals), token


def test_no_single_meta_primitive_suffices_in_the_development_world() -> None:
    item = world(DEVELOPMENT_WORLD)
    for primitive in META_PRIMITIVES:
        candidate = apply_meta_primitive(m0_constructor(), primitive, 1)
        record = encounter(item, candidate, prior=m0_constructor())
        assert not record.correct, primitive


def test_several_meta_transformations_are_rejected_before_one_works() -> None:
    from metamorphosis.m088_lineage import meta_search

    development = meta_search(world(DEVELOPMENT_WORLD))
    assert development.adopted_constructor is not None
    assert len(development.rejected) >= 3


def test_an_unknown_rule_or_primitive_is_refused() -> None:
    with pytest.raises(ConstructorError):
        ExperimentConstructor(rules=("BUILD_THE_CORRECT_EXPERIMENT",), max_depth=1)
    with pytest.raises(ConstructorError):
        apply_meta_primitive(m0_constructor(), "install_discriminating_probe")
    with pytest.raises(ConstructorError):
        ExperimentConstructor(rules=("PREFIX_RESET",), max_depth=99)


# --------------------------------------------------------------------------------------------
# the world is not the evaluator
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("world_id", QUALIFICATION_WORLDS)
def test_no_hidden_program_lies_inside_the_adopted_constructive_image(world_id: str) -> None:
    """Structural no-leak: the lineage cannot build a hidden program, so it cannot run one."""

    proof = hidden_outside_constructive_image(qualified_world(world_id, SALT), _m1())
    assert proof["all_hidden_outside_image"] is True
    assert proof["hidden_inside_image"] == []


def test_hidden_programs_are_deeper_than_the_adopted_constructor_composes() -> None:
    for world_id in WORLDS:
        for program in QUALIFICATION_POOL[world_id]:
            body = [step for step in program if step not in {"reset", "observe"}]
            assert len(body) > _m1().max_depth, (world_id, program)


def test_the_world_answers_behaviour_not_correctness() -> None:
    """`execute` returns what happened. It never says which candidate is right."""

    item = world(DEVELOPMENT_WORLD)
    observation = item.execute(("reset", "send_a", "send_b", "observe"))
    assert observation in {"ready", "ack", "unlocked", "error"}
    assert item.truth_id not in str(observation)


def test_an_unknown_primitive_cannot_be_executed() -> None:
    with pytest.raises(WorldError):
        world(DEVELOPMENT_WORLD).execute(("reset", "ask_correct_hypothesis", "observe"))


def test_no_module_can_reach_a_model_or_network() -> None:
    for relative in (
        "metamorphosis/m088_worlds.py", "metamorphosis/m088_experiment.py",
        "metamorphosis/m088_lineage.py", "scripts/run_m088_experiment.py",
    ):
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        assert not (imported & {"socket", "urllib", "http", "requests", "openai", "subprocess"})


# --------------------------------------------------------------------------------------------
# causal use of the observation
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("world_id", WORLDS)
def test_every_acquisition_eliminates_at_least_one_candidate(world_id: str) -> None:
    record = encounter(world(world_id), _m1(), prior=m0_constructor())
    assert record.acquisitions
    for acquisition in record.acquisitions:
        assert acquisition["eliminated"], acquisition["program"]


def test_the_adopted_candidate_follows_the_observations_not_a_preference() -> None:
    """Reverse what the world says and the surviving candidate changes with it."""

    from dataclasses import replace

    item = world(DEVELOPMENT_WORLD)
    flipped = replace(item, truth_id="count_based")
    normal = encounter(item, _m1(), prior=m0_constructor())
    other = encounter(flipped, _m1(), prior=m0_constructor())
    assert normal.adopted == "order_sensitive"
    assert other.adopted == "count_based"


def test_a_world_whose_candidates_never_diverge_is_not_resolved() -> None:
    """If no constructible program discriminates, the answer is not to guess."""

    from dataclasses import replace

    item = world(DEVELOPMENT_WORLD)
    degenerate = replace(
        item,
        candidates={"a": item.candidates["memoryless"], "b": item.candidates["always_ack"]},
        truth_id="a",
    )
    record = encounter(degenerate, _m1(), prior=m0_constructor())
    assert len(record.survivors_final) > 1
    assert record.adopted is None


# --------------------------------------------------------------------------------------------
# persistence and rollback
# --------------------------------------------------------------------------------------------


def test_rollback_restores_the_constructor_byte_identically() -> None:
    proof = rollback_proof(_m1())
    assert proof["corruption_detected"] is True
    assert proof["byte_identical_restore"] is True
    assert proof["digest_matches"] is True
    assert proof["constructor_included_in_restored_state"] is True


def test_a_restored_constructor_builds_the_same_space() -> None:
    item = world(DEVELOPMENT_WORLD)
    restored = ExperimentConstructor.from_dict(json.loads(json.dumps(_m1().to_dict())))
    assert constructive_image(restored, item.action_names, item.observer_names) == (
        constructive_image(_m1(), item.action_names, item.observer_names)
    )


def test_a_malformed_serialized_constructor_is_refused() -> None:
    with pytest.raises(ConstructorError):
        ExperimentConstructor.from_dict(
            {"schema": "wrong", "rules": [], "max_depth": 1, "provenance": [], "version": 0}
        )


def test_the_ablation_really_removes_the_composition_rules() -> None:
    from metamorphosis.m088_lineage import _strip

    stripped = _strip(_m1())
    assert stripped.max_depth == 1
    assert "EMIT_ACTION_SEQUENCE" not in stripped.rules
    item = world(DEVELOPMENT_WORLD)
    assert constructive_image(stripped, item.action_names, item.observer_names) == (
        constructive_image(m0_constructor(), item.action_names, item.observer_names)
    )


# --------------------------------------------------------------------------------------------
# the verdict function
# --------------------------------------------------------------------------------------------


def test_every_declared_condition_is_computed() -> None:
    stub = {
        "encounters": [], "correct_terminal_decisions": 0, "encounter_count": 0,
        "worlds_with_correct_decision": [], "total_acquisitions": 0,
        "total_programs_executed": 0, "experiments_outside_prior_image": 0,
    }
    verdict = evaluate(
        {"limitation": {
            "resolved_by_prior_constructor": True, "prior_correct": True,
            "discriminating_programs_in_prior_image": [["x"]],
        }, "adopted_constructor": None, "rejected_count": 0},
        {arm: dict(stub) for arm in ARMS},
        {"corruption_detected": False, "byte_identical_restore": False,
         "digest_matches": False, "constructor_included_in_restored_state": False},
    )
    assert set(verdict["conditions"]) == set(CONDITIONS)
    assert verdict["verdict"] == "negative"
    assert len(verdict["failed_conditions"]) == len(CONDITIONS), (
        "every condition must be able to fail; a vacuous pass on an empty arm is the M086-A defect"
    )


# --------------------------------------------------------------------------------------------
# the preserved result
# --------------------------------------------------------------------------------------------


@pytest.fixture()
def result() -> dict[str, object]:
    if not RESULT_PATH.exists():
        pytest.skip("the M088 result has not been materialized in this tree")
    return json.loads(RESULT_PATH.read_text(encoding="utf-8"))


def test_the_result_is_a_single_unretried_attempt(result: dict[str, object]) -> None:
    assert result["attempt"] == 1 and result["retry_used"] is False
    assert result["model_calls"] == 0 and result["network_calls"] == 0


def test_the_result_binds_the_frozen_protocol(result: dict[str, object]) -> None:
    import hashlib

    raw = (ROOT / "experiments/M088/PROTOCOL.json").read_bytes()
    assert result["protocol_raw_sha256"] == hashlib.sha256(raw).hexdigest()


def test_adoption_precedes_qualification(result: dict[str, object]) -> None:
    assert result["chronology"]["adoption_precedes_qualification"] is True
    assert result["chronology"]["ordered"] is True


def test_the_budget_arm_really_searched_more_and_gained_nothing(
    result: dict[str, object],
) -> None:
    budgeted = result["arms"]["more_budget_same_experiment_space"]
    fixed = result["arms"]["fixed_experiment_constructor"]
    assert budgeted["total_programs_executed"] >= 10 * fixed["total_programs_executed"] // 2
    assert budgeted["total_programs_executed"] > fixed["total_programs_executed"]
    assert budgeted["experiments_outside_prior_image"] == 0
    assert budgeted["correct_terminal_decisions"] == 0


def test_the_ceiling_arm_is_flagged_and_excluded_from_the_verdict(
    result: dict[str, object],
) -> None:
    ceiling = result["arms"]["authored_full_experiment_space"]
    assert ceiling["is_ceiling"] is True
    assert ceiling["supplied_experiment_space"] is True
    for name in CEILING_ARMS:
        assert name not in json.dumps(result["evaluation"])


def test_only_the_evolvable_arm_left_the_prior_image(result: dict[str, object]) -> None:
    for arm, record in result["arms"].items():
        if arm in {"evolvable_experiment_constructor", "authored_full_experiment_space"}:
            assert record["experiments_outside_prior_image"] >= 1, arm
        else:
            assert record["experiments_outside_prior_image"] == 0, arm


def test_cross_environment_reuse_used_one_serialized_constructor(
    result: dict[str, object],
) -> None:
    evolvable = result["arms"]["evolvable_experiment_constructor"]
    digests = {record["constructor_digest"] for record in evolvable["encounters"]}
    assert len(digests) == 1
    assert DEVELOPMENT_WORLD not in set(QUALIFICATION_WORLDS)
    assert len(evolvable["worlds_with_correct_decision"]) == 2


def test_the_result_records_no_leak(result: dict[str, object]) -> None:
    assert result["leak_findings"] == []
    for proof in result["no_leak"]:
        assert proof["all_hidden_outside_image"] is True


def test_the_qualification_draw_reproduces_from_the_recorded_salt(
    result: dict[str, object],
) -> None:
    import hashlib

    assert hashlib.sha256(
        json.dumps(SALT, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest() == result["salt_digest"]
    for world_id in QUALIFICATION_WORLDS:
        drawn = materialize_qualification(world_id, SALT)
        assert len(drawn) == 2
        assert all(program in QUALIFICATION_POOL[world_id] for program in drawn)
