"""M089, attacked where a false positive would look exactly like a real one."""
from __future__ import annotations

import ast
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from metamorphosis.m089_lineage import (
    ARMS,
    CEILING_ARMS,
    CONDITIONS,
    DEVELOPMENT_TASK,
    PARAMETER_KINDS,
    PRIMITIVE_ID,
    acquire_primitive,
    evaluate,
    macro_reducible_to_l0,
    operation_alphabet,
    prove_l0_insufficient,
    rollback_proof,
    search_transformation,
    task_from_spec,
    validate_primitive,
)
from metamorphosis.m089_meta_language import (
    MetaLanguageError,
    MetaLanguageState,
    PrimitiveContract,
    SLOT_COUNT,
    enumerate_l0_reachable_signatures,
    execute,
    l0_language,
    source_signature,
)
from metamorphosis.m089_substrate import (
    FORBIDDEN_CAPABILITIES,
    SubstrateError,
    build_primitive,
    enumerate_candidate_bodies,
    primitive_max_source_fanout,
    run_body,
    semantics_digest,
    well_formed,
)

ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / "experiments/M089/RESULT.json"
SALT = "m089-qualification-salt-2026-08-13"

sys.path.insert(0, str(ROOT / "scripts"))
from materialize_m089_qualification import QUALIFICATION_POOL  # noqa: E402


ADOPTED_BODY = (
    ("PUSH_INPUT", "$1"), ("PUSH_INPUT", "$2"), ("BINOP", "add"), ("STORE_SLOT", "$0"),
)


def _primitive(body=ADOPTED_BODY, primitive_id: str = PRIMITIVE_ID) -> PrimitiveContract:
    return build_primitive(primitive_id, body, PARAMETER_KINDS, ("substrate",), 1)


# ---------------------------------------------------------------------------------------------
# L0 cannot express it — proof, not failed search
# ---------------------------------------------------------------------------------------------


def test_the_l0_invariant_holds_over_the_whole_enumerated_prefix() -> None:
    signatures = enumerate_l0_reachable_signatures(3)
    assert signatures
    assert max(max((len(item) for item in sig), default=0) for sig in signatures) == 1


def test_no_l0_program_of_any_length_can_reach_two_sources() -> None:
    """The induction, exercised: appending any L0 operation never raises the bound."""

    language = l0_language()
    alphabet = operation_alphabet(language)
    frontier = [()]
    for _ in range(4):
        nxt = []
        for program in frontier:
            for operation in alphabet:
                candidate = program + (operation,)
                assert max(len(item) for item in source_signature(candidate, language)) <= 1
                nxt.append(candidate)
        frontier = nxt[:200]


def test_the_development_task_is_proved_outside_l0() -> None:
    proof = prove_l0_insufficient(DEVELOPMENT_TASK)
    assert proof["task_outside_l0_constructive_image"] is True
    assert proof["l0_max_sources_reachable"] == 1
    assert proof["task_required_sources"] == 2
    assert proof["l0_exhaustive_search_found_program"] is False


# ---------------------------------------------------------------------------------------------
# the M055 trap
# ---------------------------------------------------------------------------------------------


def test_a_primitive_that_cannot_break_the_invariant_is_macro_reducible() -> None:
    """M055's acquisition made the search cheaper and nothing newly reachable."""

    macro = _primitive((("PUSH_INPUT", "$1"), ("UNOP", "inc"), ("STORE_SLOT", "$0")))
    assert primitive_max_source_fanout(macro) == 1
    assert macro_reducible_to_l0(macro) is True


def test_the_adopted_primitive_is_not_macro_reducible() -> None:
    assert primitive_max_source_fanout(_primitive()) == 2
    assert macro_reducible_to_l0(_primitive()) is False


def test_a_macro_primitive_is_refused_by_the_validator() -> None:
    macro = _primitive((("PUSH_SLOT", "$0"), ("UNOP", "double"), ("STORE_SLOT", "$0")))
    validation = validate_primitive(macro, l0_language(), [], [(7, 3, 5)])
    assert validation.accepted is False
    assert any("macro-equivalent" in reason for reason in validation.reasons)


def test_the_macro_only_arm_cannot_acquire_anything_that_solves_development() -> None:
    """Restricted to invariant-preserving micro-ops, no assembly resolves the task at all."""

    development = acquire_primitive(DEVELOPMENT_TASK, macro_only=True, limit=400)
    assert development.adopted is None
    assert development.l1 is None


# ---------------------------------------------------------------------------------------------
# semantics over names
# ---------------------------------------------------------------------------------------------


def test_renaming_the_primitive_does_not_change_its_semantics_digest() -> None:
    assert _primitive(primitive_id="something_else").semantics_digest == (
        _primitive().semantics_digest
    )


def test_the_right_name_with_the_wrong_semantics_is_a_different_primitive() -> None:
    impostor = _primitive(
        (("PUSH_INPUT", "$1"), ("PUSH_INPUT", "$2"), ("BINOP", "mul"), ("STORE_SLOT", "$0")),
    )
    assert impostor.primitive_id == _primitive().primitive_id
    assert impostor.semantics_digest != _primitive().semantics_digest


def test_a_declared_semantics_digest_that_does_not_match_is_refused() -> None:
    forged = replace(_primitive(), semantics_digest="0" * 64)
    validation = validate_primitive(forged, l0_language(), [], [(7, 3, 5)])
    assert validation.accepted is False
    assert any("declared semantics" in reason for reason in validation.reasons)


def test_two_extensionally_equal_implementations_agree() -> None:
    direct = _primitive()
    swapped = _primitive(
        (("PUSH_INPUT", "$2"), ("PUSH_INPUT", "$1"), ("BINOP", "add"), ("STORE_SLOT", "$0")),
    )
    assert direct.semantics_digest == swapped.semantics_digest
    assert direct.implementation_digest != swapped.implementation_digest


# ---------------------------------------------------------------------------------------------
# authority and safety
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("capability", FORBIDDEN_CAPABILITIES)
def test_a_primitive_requesting_new_authority_is_refused(capability: str) -> None:
    greedy = replace(_primitive(), capabilities=(capability,))
    validation = validate_primitive(greedy, l0_language(), [], [(7, 3, 5)])
    assert validation.accepted is False
    assert any("forbidden capability" in reason for reason in validation.reasons)


def test_a_body_that_does_not_terminate_cleanly_is_refused() -> None:
    assert not well_formed((("BINOP", "add"), ("STORE_SLOT", "$0")), PARAMETER_KINDS)
    with pytest.raises(SubstrateError):
        run_body((("BINOP", "add"),), (0, 1, 2), (0, 0, 0, 0), (1, 2, 3))


def test_an_unknown_micro_operation_is_refused() -> None:
    with pytest.raises(SubstrateError):
        run_body((("SOLVE_THE_TASK", None),), (0, 1, 2), (0, 0, 0, 0), (1, 2, 3))


# ---------------------------------------------------------------------------------------------
# the substrate is construction, not selection
# ---------------------------------------------------------------------------------------------


def test_the_substrate_is_mostly_useless_which_is_what_makes_it_construction() -> None:
    bodies = enumerate_candidate_bodies(4)
    well = [item for item in bodies if well_formed(item, PARAMETER_KINDS)]
    breaking = [
        item for item in well
        if primitive_max_source_fanout(_primitive(item)) > 1
    ]
    assert len(bodies) > 10_000
    assert len(breaking) < len(well) / 50, "the substrate is too close to being the answer"


def test_no_micro_operation_is_itself_a_primitive() -> None:
    for body in enumerate_candidate_bodies(1):
        assert not well_formed(body, PARAMETER_KINDS) or len(body) > 1


def test_the_substrate_module_names_no_task_or_target() -> None:
    tree = ast.parse((ROOT / "metamorphosis/m089_substrate.py").read_text(encoding="utf-8"))
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
    for token in ("development_pairwise", "composed_combination", "repeated_combination"):
        assert not any(token in item for item in literals), token


# ---------------------------------------------------------------------------------------------
# registration is what matters
# ---------------------------------------------------------------------------------------------


def test_an_unregistered_primitive_cannot_be_executed() -> None:
    with pytest.raises(MetaLanguageError):
        execute(((PRIMITIVE_ID, (0, 1, 2)),), (1, 2, 3), l0_language())


def test_registration_changes_the_language_digest_and_the_alphabet() -> None:
    base = l0_language()
    extended = base.register(_primitive(), "test")
    assert extended.digest() != base.digest()
    assert extended.version == base.version + 1
    assert len(operation_alphabet(extended)) > len(operation_alphabet(base))


def test_the_transformation_is_constructible_under_l1_and_not_under_l0() -> None:
    base = l0_language()
    extended = base.register(_primitive(), "test")
    assert search_transformation(DEVELOPMENT_TASK, base).found is False
    found = search_transformation(DEVELOPMENT_TASK, extended)
    assert found.found is True and found.uses_registered_primitive is True


def test_registering_the_same_primitive_twice_is_refused() -> None:
    extended = l0_language().register(_primitive(), "test")
    with pytest.raises(MetaLanguageError):
        extended.register(_primitive(), "again")


# ---------------------------------------------------------------------------------------------
# persistence and rollback on both sides
# ---------------------------------------------------------------------------------------------


def test_the_language_survives_serialization_and_still_executes() -> None:
    extended = l0_language().register(_primitive(), "test")
    reloaded = MetaLanguageState.from_dict(json.loads(json.dumps(extended.to_dict())))
    assert reloaded.digest() == extended.digest()
    program = ((PRIMITIVE_ID, (0, 1, 2)),)
    assert execute(program, (1, 2, 3), reloaded) == execute(program, (1, 2, 3), extended)


def test_rollback_corrupts_the_state_it_restores_on_both_sides() -> None:
    base = l0_language()
    extended = base.register(_primitive(), "test")
    proof = rollback_proof(base, extended)
    assert proof["language_digests_differ"] is True
    for side in ("before_extension", "after_extension"):
        assert proof[side]["corruption_detected"] is True
        assert proof[side]["corrupted_state_was_the_restored_state"] is True
        assert proof[side]["byte_identical_restore"] is True
        assert proof[side]["restored_behaviour_matches_intact"] is True
    assert proof["after_extension"]["primitive_count"] == 1


def test_only_the_registry_is_executable_state() -> None:
    """The finding that made M089 negative, pinned so it cannot be lost.

    `execute` dispatches base operations from the module constant `L0_OPERATIONS`, not from
    `language.base_operations`. For a language with an empty registry, therefore, NO fault to the
    serialized state can change behaviour: the pre-extension language has nothing executable to
    roll back. Only the registry is real state.
    """

    base = l0_language()
    damaged = MetaLanguageState.from_dict(
        {**json.loads(json.dumps(base.to_dict())), "base_operations": []}
    )
    probe = (("COPY_INPUT", (0, 1)),)
    assert damaged.digest() != base.digest()
    assert execute(probe, (1, 2, 3), damaged) == execute(probe, (1, 2, 3), base)

    extended = base.register(_primitive(), "test")
    stripped = MetaLanguageState.from_dict(
        {**json.loads(json.dumps(extended.to_dict())), "registry": []}
    )
    with pytest.raises(MetaLanguageError):
        execute(((PRIMITIVE_ID, (0, 1, 2)),), (1, 2, 3), stripped)


def test_a_forged_language_digest_does_not_survive_reserialization() -> None:
    extended = l0_language().register(_primitive(), "test")
    data = json.loads(json.dumps(extended.to_dict()))
    data["version"] = 99
    assert MetaLanguageState.from_dict(data).digest() != extended.digest()


# ---------------------------------------------------------------------------------------------
# leakage
# ---------------------------------------------------------------------------------------------


def test_the_qualification_pool_is_not_importable_by_the_lineage() -> None:
    import metamorphosis.m089_lineage as lineage
    import metamorphosis.m089_meta_language as language
    import metamorphosis.m089_substrate as substrate

    for module in (lineage, language, substrate):
        assert not hasattr(module, "QUALIFICATION_POOL")
        assert not hasattr(module, "HIDDEN_INPUT_POOL")
    source = (ROOT / "metamorphosis/m089_lineage.py").read_text(encoding="utf-8")
    for family, pool in QUALIFICATION_POOL.items():
        for spec in pool:
            assert str(spec["task_id"]) not in source


def test_no_module_can_reach_a_model_or_network() -> None:
    for relative in (
        "metamorphosis/m089_meta_language.py", "metamorphosis/m089_substrate.py",
        "metamorphosis/m089_lineage.py",
    ):
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        assert not (imported & {"socket", "urllib", "http", "requests", "openai", "subprocess"})


def test_the_validator_never_sees_a_qualification_task() -> None:
    import inspect

    parameters = set(inspect.signature(validate_primitive).parameters)
    assert "retained_tasks" in parameters
    assert not {item for item in parameters if "qualification" in item or "hidden_task" in item}


# ---------------------------------------------------------------------------------------------
# the verdict function
# ---------------------------------------------------------------------------------------------


def test_every_declared_condition_is_computed_and_can_fail() -> None:
    stub = {
        "encounters": [], "correct_terminal_decisions": 0, "encounter_count": 0,
        "families_with_correct_decision": [], "total_programs_examined": 0,
        "uses_registered_primitive": False, "primitive_built_but_not_registered": None,
    }
    verdict = evaluate(
        {"insufficiency_proof": {
            "task_outside_l0_constructive_image": False, "invariant_holds_for_l0": False,
            "l0_exhaustive_search_found_program": True, "l0_max_sources_reachable": 2,
            "task_required_sources": 1,
        }, "adopted_primitive": None, "rejected_count": 0, "candidates_constructed": 0,
            "validation": None, "l0_digest": "a", "l1_digest": None, "l1_version": None},
        {arm: dict(stub) for arm in ARMS},
        {"language_digests_differ": False,
         "before_extension": {"corruption_detected": False, "byte_identical_restore": False,
                              "digest_matches": False, "fault_actually_changed_behaviour": False},
         "after_extension": {"corruption_detected": False, "byte_identical_restore": False,
                             "digest_matches": False, "fault_actually_changed_behaviour": False}},
    )
    assert set(verdict["conditions"]) == set(CONDITIONS)
    assert verdict["verdict"] == "negative"
    assert len(verdict["failed_conditions"]) == len(CONDITIONS), (
        "every condition must be able to fail; a vacuous pass is the M086-A defect"
    )


# ---------------------------------------------------------------------------------------------
# the preserved result
# ---------------------------------------------------------------------------------------------


@pytest.fixture()
def result() -> dict[str, object]:
    if not RESULT_PATH.exists():
        pytest.skip("the M089 result has not been materialized in this tree")
    return json.loads(RESULT_PATH.read_text(encoding="utf-8"))


def test_the_result_is_a_single_unretried_attempt(result: dict[str, object]) -> None:
    assert result["attempt"] == 1 and result["retry_used"] is False
    assert result["model_calls"] == 0 and result["network_calls"] == 0


def test_the_result_binds_the_frozen_protocol(result: dict[str, object]) -> None:
    import hashlib

    raw = (ROOT / "experiments/M089/PROTOCOL.json").read_bytes()
    assert result["protocol_raw_sha256"] == hashlib.sha256(raw).hexdigest()


def test_adoption_precedes_qualification(result: dict[str, object]) -> None:
    assert result["chronology"]["adoption_precedes_qualification"] is True
    assert result["chronology"]["ordered"] is True
    assert result["qualification_artifact"]["materialized_by"] == "separate process"


def test_the_adopted_primitive_breaks_the_invariant(result: dict[str, object]) -> None:
    assert result["adopted_primitive_max_source_fanout"] >= 2


def test_the_recorded_verdict_is_negative_on_p10_only(
    result: dict[str, object],
) -> None:
    """The preserved result. P1-P9 held; P10 did not, and the negative is not repaired."""

    assert result["evaluation"]["verdict"] == "negative"
    assert result["evaluation"]["failed_conditions"] == [
        "P10_language_persisted_and_restored_on_both_sides"
    ]
    assert result["rollback"]["before_extension"]["fault_actually_changed_behaviour"] is False
    assert result["rollback"]["after_extension"]["fault_actually_changed_behaviour"] is True


def test_the_controls_that_kill_the_false_positives_all_failed(
    result: dict[str, object],
) -> None:
    for arm in (
        "fixed_meta_language", "macro_only_extension",
        "extension_built_but_not_registered", "extension_acquisition_ablated",
        "more_budget_same_meta_language", "fresh_agent",
    ):
        assert result["arms"][arm]["correct_terminal_decisions"] == 0, arm
        assert result["arms"][arm]["uses_registered_primitive"] is False, arm
    assert result["arms"]["extension_built_but_not_registered"][
        "primitive_built_but_not_registered"
    ] is not None


def test_the_budget_arm_really_searched_far_more_and_gained_nothing(
    result: dict[str, object],
) -> None:
    budgeted = result["arms"]["more_budget_same_meta_language"]
    fixed = result["arms"]["fixed_meta_language"]
    assert budgeted["total_programs_examined"] >= 50 * fixed["total_programs_examined"]
    assert budgeted["correct_terminal_decisions"] == 0


def test_the_ceiling_arm_is_flagged_and_absent_from_the_verdict(
    result: dict[str, object],
) -> None:
    assert result["arms"]["authored_correct_primitive"]["is_ceiling"] is True
    for name in CEILING_ARMS:
        assert name not in json.dumps(result["evaluation"])


def test_reuse_used_one_serialized_language_across_two_families(
    result: dict[str, object],
) -> None:
    evolvable = result["arms"]["evolvable_meta_language"]
    digests = {record["language_digest"] for record in evolvable["encounters"]}
    families = {record["family"] for record in evolvable["encounters"]}
    assert len(digests) == 1
    assert len(families) == 2
    assert evolvable["correct_terminal_decisions"] == evolvable["encounter_count"] == 2
