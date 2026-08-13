"""M091: can the lineage add an operation to the language it owns, and be more capable for it?

These tests protect the falsifiers rather than the result. The heavy ones — the acquisition, the
arms, the fresh processes — belong to `scripts/check_m091_result.py`, which replays the science.
What is guarded here is that each condition can fail, that the invariant argument is sound, that
the validator refuses what it should, that an identifier decides nothing, and that the three
lessons this milestone inherits (M055, M089, M090) are enforced by machinery rather than prose.
"""
from __future__ import annotations

import ast
import copy
import json
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import pytest

from metamorphosis.m090_language import (
    INPUT_COUNT,
    SLOT_COUNT,
    UNARY_OPERATORS,
    LanguageError,
    MetaLanguageState,
    PrimitiveDefinition,
    execute,
    run_body,
)
from metamorphosis.m090_migration import PROBE_EXTENSION, migrated_l0
from metamorphosis.m091_expressivity import (
    INVARIANT_NAME,
    SOUNDNESS_INPUTS,
    abstraction_soundness_report,
    closure_lemma,
    parameter_bindings,
    primitive_bend_witness,
    primitive_shape_report,
    refute_affine_single_source,
    verify_bend_witness,
    verify_refutation,
)
from metamorphosis.m091_lineage import (
    ARMS,
    CEILING_ARMS,
    CONDITIONS,
    MACRO_TARGET_WORLD,
    REJECTION_CLASSES,
    RETAINED_WORLDS,
    acquire_primitive,
    conservation_report,
    evaluate,
    inherited_macro_semantics,
    no_m055_style_compositional_false_positive,
    operation_alphabet,
    state_authority_report,
    validate_candidate,
)
from metamorphosis.m091_search import search_transformation
from metamorphosis.m091_substrate import (
    BODY_CONSTANTS,
    MAX_ASSEMBLY_LENGTH,
    SIGNATURES,
    body_alphabet,
    build_definition,
    enumerate_candidate_bodies,
    semantics_digest,
    substrate_manifest,
    well_formed,
)
from metamorphosis.m091_worlds import (
    WorldError,
    development_world,
    evaluate_rule,
    invariant_violations,
    required_slots,
    validate_world,
)

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments/M091"

CLAMP_BODY = (
    ("PUSH_SLOT", "$0"), ("PUSH_CONST", 0), ("BINOP", "max"), ("STORE_SLOT", "$0"),
)


def clamp() -> PrimitiveDefinition:
    return build_definition("probe_clamp", CLAMP_BODY, ("slot",), ("test fixture",))


# -------------------------------------------------------------------------------------------
# the inherited language's invariant
# -------------------------------------------------------------------------------------------


def test_the_inherited_language_is_closed_under_the_declared_invariant():
    report = closure_lemma(migrated_l0())
    assert report["invariant"] == INVARIANT_NAME
    assert report["closed_under_every_primitive"] is True
    assert report["escape_count"] == 0
    # The lemma is a one-step property checked over the whole domain; induction does the rest.
    assert report["abstract_states_checked"] > 10_000


def test_the_abstraction_agrees_with_the_concrete_interpreter():
    language = migrated_l0()
    alphabet = operation_alphabet(language)
    programs = [(item,) for item in alphabet]
    programs += [(alphabet[index], alphabet[-index - 1]) for index in range(0, 30)]
    report = abstraction_soundness_report(language, programs)
    assert report["abstraction_agrees_with_the_interpreter"] is True
    assert report["violation_count"] == 0
    assert report["slot_functions_checked"] > 100


def test_the_requirement_is_single_source_so_this_is_not_m089s_gap():
    world = development_world()

    def required(inputs):
        return required_slots(world, inputs)[0]

    certificate = refute_affine_single_source(required, 0)
    # M089's invariant was fan-in. Breaking it is neither necessary nor sufficient here.
    assert certificate["fan_in"] == 1
    assert certificate["single_source"] is True
    assert certificate["outside_affine_single_source"] is True
    assert verify_refutation(certificate, required) == []


def test_the_refutation_covers_the_whole_affine_class_not_a_sample():
    world = development_world()

    def required(inputs):
        return required_slots(world, inputs)[0]

    certificate = refute_affine_single_source(required, 0)
    points = [(x, y) for x, y in certificate["not_affine_in_its_source"]["points"]]
    # Three non-collinear points refute every integer a and b at once, at any program length.
    (x1, y1), (x2, y2), (x3, y3) = points
    assert (y2 - y1) * (x3 - x1) != (y3 - y1) * (x2 - x1)
    for index in range(INPUT_COUNT):
        if index == certificate["behavioural_sources"][0]:
            continue
        assert certificate["not_a_function_of_any_rival_position"][str(index)] is not None


def test_an_affine_requirement_is_not_refuted():
    """The refutation must not fire for something the inherited language can already do."""

    world = dict(development_world())
    world["requirements"] = [{"slot": 0, "expression": ["double", ["input", 0]]}]

    def required(inputs):
        return required_slots(world, inputs)[0]

    assert refute_affine_single_source(required, 0)["outside_affine_single_source"] is False


# -------------------------------------------------------------------------------------------
# the substrate assembles rather than offers
# -------------------------------------------------------------------------------------------


def test_the_substrate_offers_no_finished_operation():
    for signature in SIGNATURES:
        for name, _ in body_alphabet(signature):
            # Every letter is a micro-operation of M090's frozen machine, never an operation of
            # the language and never a candidate primitive.
            assert name in substrate_manifest()["micro_operations"]
    assert substrate_manifest()["contains_no_finished_operation_to_select"] is True


def test_most_assembled_bodies_are_useless():
    bodies = []
    for body in enumerate_candidate_bodies(("slot",), 3):
        bodies.append(body)
    formed = [item for item in bodies if well_formed(item, ("slot",))]
    assert len(bodies) > 2_000
    # Assembly is not selection: the overwhelming majority of what the substrate produces is junk.
    assert len(formed) * 20 < len(bodies)


def test_the_assembly_bound_respects_the_interpreter():
    assert MAX_ASSEMBLY_LENGTH <= substrate_manifest()["max_assembly_length"]
    assert set(BODY_CONSTANTS) <= {0, 1}


# -------------------------------------------------------------------------------------------
# the independent validator
# -------------------------------------------------------------------------------------------


def test_the_validator_accepts_a_bending_single_source_primitive():
    validation = validate_candidate(clamp(), migrated_l0(), RETAINED_WORLDS, require_bend=True)
    assert validation.accepted is True
    assert validation.receipt
    assert validation.shape["preserves_single_source"] is True
    assert validation.bend_witness is not None


def test_the_validator_refuses_the_m089_shaped_primitive_as_overbroad():
    """M090's authored probe extension routes two inputs into a slot. That is a different gap."""

    validation = validate_candidate(
        PROBE_EXTENSION, migrated_l0(), RETAINED_WORLDS, require_bend=True,
    )
    assert validation.accepted is False
    assert "overbroad_widens_the_source_fan_in" in validation.reasons


def test_the_validator_refuses_a_forbidden_capability():
    with pytest.raises(LanguageError):
        PrimitiveDefinition(
            primitive_id="grabby",
            parameter_kinds=("slot",),
            body=CLAMP_BODY,
            origin="acquired",
            provenance=(),
            capabilities=("network",),
        )


def test_the_validator_refuses_an_inherited_composition():
    composition = build_definition(
        "renamed_macro",
        (("PUSH_SLOT", "$0"), ("UNOP", "double"), ("STORE_SLOT", "$0")),
        ("slot",), ("test fixture",),
    )
    validation = validate_candidate(
        composition, migrated_l0(), RETAINED_WORLDS, require_bend=True,
    )
    assert validation.accepted is False
    assert "macro_equivalent_to_an_inherited_composition" in validation.reasons


def test_the_validator_refuses_a_malformed_body():
    malformed = build_definition(
        "broken", (("BINOP", "add"), ("STORE_SLOT", "$0")), ("slot",), ("test fixture",),
    )
    validation = validate_candidate(malformed, migrated_l0(), RETAINED_WORLDS, require_bend=True)
    assert validation.accepted is False
    assert "malformed_or_partial" in validation.reasons


def test_the_validator_refuses_unbounded_growth():
    explosive = build_definition(
        "explosive",
        (("PUSH_SLOT", "$0"), ("DUP", None), ("BINOP", "mul"), ("STORE_SLOT", "$0")),
        ("slot",), ("test fixture",),
    )
    grown = run_body(explosive.body, (0,), [500, 0, 0, 0], (1, 2, 3))
    assert grown[0] == 250_000
    validation = validate_candidate(explosive, migrated_l0(), RETAINED_WORLDS, require_bend=True)
    assert validation.accepted is False
    assert "exceeds_the_resource_bound" in validation.reasons


def test_the_observed_rejection_classes_are_declared_ones():
    assert len(REJECTION_CLASSES) >= 8
    assert len(set(REJECTION_CLASSES)) == len(REJECTION_CLASSES)
    result_path = EXPERIMENT / "RESULT.json"
    if not result_path.is_file():
        pytest.skip("no M091 result is present yet")
    observed = json.loads(result_path.read_text(encoding="utf-8"))[
        "acquisition"
    ]["rejection_classes_observed"]
    assert set(observed) <= set(REJECTION_CLASSES)
    # A search that refused everything for one reason would say little about what was refused.
    assert len(observed) >= 5


def test_renaming_the_primitive_changes_nothing():
    """Success is never an identifier comparison, and a good name never saves a bad body."""

    base = clamp()
    renamed = replace(base, primitive_id="something_else_entirely")
    assert renamed.semantics_digest() == base.semantics_digest()
    assert semantics_digest(renamed.body, renamed.parameter_kinds) == semantics_digest(
        base.body, base.parameter_kinds
    )
    assert validate_candidate(
        renamed, migrated_l0(), RETAINED_WORLDS, require_bend=True,
    ).accepted is True

    # The right name on the wrong body must still fail.
    impostor = build_definition(
        base.primitive_id, (("PUSH_CONST", 1), ("STORE_SLOT", "$0")), ("slot",), ("impostor",),
    )
    assert validate_candidate(
        impostor, migrated_l0(), RETAINED_WORLDS, require_bend=True,
    ).accepted is False


def test_the_bend_witness_is_re_derivable_from_the_body():
    definition = clamp()
    witness = primitive_bend_witness(definition)
    assert witness is not None
    assert verify_bend_witness(definition, witness) == []
    tampered = dict(witness)
    tampered["points"] = [[-5, -5], [-2, -2], [1, 1]]
    assert verify_bend_witness(definition, tampered) != []


# -------------------------------------------------------------------------------------------
# M055: a cheaper search is not a larger capability
# -------------------------------------------------------------------------------------------


def test_m091_cannot_pass_by_search_cost_only():
    """The falsifier D019 left behind, enforced three ways at once.

    A memoized composition of the inherited language buys a shorter search and no reach. The
    adopted primitive must buy reach, and must be refused a pass on cost alone.
    """

    inherited = migrated_l0()
    memoized = build_definition(
        "memoized",
        (("PUSH_SLOT", "$0"), ("UNOP", "double"), ("UNOP", "double"), ("STORE_SLOT", "$0")),
        ("slot",), ("test fixture",),
    )
    # It really does shorten the search: that is what makes it the right control.
    without = search_transformation(MACRO_TARGET_WORLD, inherited)
    with_macro = search_transformation(
        MACRO_TARGET_WORLD, inherited.register(memoized, "memoized"),
    )
    assert without.found is True
    assert with_macro.found is True
    assert with_macro.programs_examined < without.programs_examined
    assert len(with_macro.program) < len(without.program)

    macro_report = no_m055_style_compositional_false_positive(
        memoized, inherited,
        {"gain_was_reach": False, "gain_was_search_cost_only": True},
    )
    assert macro_report["macro_reducible_to_the_inherited_language"] is True
    assert macro_report["is_an_m055_style_false_positive"] is True

    clamp_report = no_m055_style_compositional_false_positive(
        clamp(), inherited, {"gain_was_reach": True, "gain_was_search_cost_only": False},
    )
    assert clamp_report["macro_reducible_to_the_inherited_language"] is False
    assert clamp_report["bend_is_concretely_witnessed"] is True
    assert clamp_report["is_an_m055_style_false_positive"] is False
    # The extensional comparison is the redundant check; the invariant certificate is the proof
    # that holds at every length. 819 compositions collapse to 87 distinct behaviours, and the
    # adopted primitive matches none of them.
    assert clamp_report["inherited_compositions_compared"] > 50

    # And no budget in the inherited language reaches the development requirement.
    world = development_world()
    assert search_transformation(world, inherited, max_length=5).found is False


def test_the_macro_closure_is_computed_by_running_compositions_not_by_splicing_bodies():
    """A spliced composition would exceed the interpreter's length bound and collapse to refusal.

    That collapse would have made every long macro share one digest, and the macro test would have
    passed for the wrong reason.
    """

    inherited = migrated_l0()
    digests = inherited_macro_semantics(("slot",), inherited)
    assert len(digests) > 50
    # A three-deep composition is nine micro-operations, well past the body bound.
    with pytest.raises(LanguageError):
        run_body(
            tuple(CLAMP_BODY) + tuple(CLAMP_BODY) + tuple(CLAMP_BODY), (0,), [0] * SLOT_COUNT,
            (1, 2, 3),
        )


# -------------------------------------------------------------------------------------------
# M089: the state must be the execution authority
# -------------------------------------------------------------------------------------------


def test_m091_language_state_is_real_execution_authority():
    inherited = migrated_l0()
    extended = inherited.register(clamp(), "test fixture")
    program = (("COPY_INPUT", (0, 0)), ("probe_clamp", (0,)))
    assert execute(program, (-4, 3, 7), extended) == (0, 0, 0, 0)

    report = state_authority_report(extended, [program], "probe_clamp")
    assert report["all_ran_intact"] is True
    # Deleting the acquired operation from the state really deletes the capability.
    assert report["removing_the_primitive_from_state_removes_the_transformation"] is True
    # And so does deleting an inherited one: M090's property, still holding.
    assert report["removing_an_inherited_primitive_removes_it_too"] is True

    with pytest.raises(LanguageError):
        execute(program, (-4, 3, 7), extended.without("probe_clamp", "removed"))
    with pytest.raises(LanguageError):
        execute(program, (-4, 3, 7), extended.without("COPY_INPUT", "removed"))


def test_a_body_is_not_a_capability_until_it_is_registered():
    """The `extension_built_but_not_registered` control, as a property of the architecture."""

    inherited = migrated_l0()
    definition = clamp()
    # The bytes exist and run on the substrate directly.
    assert run_body(definition.body, (0,), [-4, 0, 0, 0], (1, 2, 3))[0] == 0
    # The language cannot call them.
    with pytest.raises(LanguageError):
        execute((("probe_clamp", (0,)),), (1, 2, 3), inherited)


def test_the_interpreter_still_branches_on_no_primitive_identifier():
    source = (ROOT / "metamorphosis/m090_language.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    function = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "execute"
    )
    literals = {
        node.value for node in ast.walk(function)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    extended = migrated_l0().register(clamp(), "test fixture")
    assert not (literals & set(extended.primitive_ids))


# -------------------------------------------------------------------------------------------
# M090: conservation, and provenance that cannot be declared
# -------------------------------------------------------------------------------------------


def test_inherited_semantics_cannot_be_widened_outside_conservation_space():
    inherited = migrated_l0()
    extended = inherited.register(clamp(), "test fixture")
    report = conservation_report(inherited, extended)
    assert report["semantics_conserved"] is True
    assert report["rejection_behaviour_conserved"] is True
    # The A2 lesson: an operator excluded from the space is an operator whose conservation is
    # unproved. The space is the complete cross product of every declared domain, and says so.
    assert report["space_excludes_nothing"] is True
    assert report["declared_binding_counts"] == report["covered_binding_counts"]
    assert report["calls_checked"] >= 1000

    covered = {
        argument for name, (_slot, argument) in operation_alphabet(inherited)
        if name == "APPLY_UNARY"
    }
    assert covered == set(UNARY_OPERATORS)


def test_a_widened_inherited_domain_is_caught_by_the_conservation_report():
    inherited = migrated_l0()
    widened = inherited.with_mutated(
        "APPLY_UNARY", (("PUSH_SLOT", "$0"), ("UNOP", "neg"), ("STORE_SLOT", "$0")),
        "a deliberately altered inherited operation",
    )
    report = conservation_report(inherited, widened)
    assert report["semantics_conserved"] is False
    assert report["mismatch_count"] > 0


def test_attempt_provenance_is_derived_from_artifacts():
    """`attempt` and `retry_used` are read from what is preserved, never from a declared field."""

    runner = (ROOT / "scripts/run_m091_experiment.py").read_text(encoding="utf-8")
    tree = ast.parse(runner)
    sources = {
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert "WITHDRAWN_RESULT_*.json" in sources

    result_path = EXPERIMENT / "RESULT.json"
    if not result_path.is_file():
        pytest.skip("no M091 result is present yet")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    preserved = sorted(path.name for path in EXPERIMENT.glob("WITHDRAWN_RESULT_*.json"))
    assert result["attempt"] == len(preserved) + 1
    assert result["retry_used"] is bool(preserved)
    assert sorted(item["artifact"] for item in result["prior_attempts"]) == preserved


# -------------------------------------------------------------------------------------------
# worlds
# -------------------------------------------------------------------------------------------


def test_a_world_is_data_and_the_schema_is_closed():
    world = development_world()
    validate_world(world)
    with pytest.raises(WorldError):
        validate_world({"world_id": "x"})
    with pytest.raises(WorldError):
        evaluate_rule(["exponentiate", ["input", 0]], (1, 2, 3))


def test_world_correctness_is_more_than_matching_the_target():
    world = development_world()
    inputs = [-4, 3, 7]
    assert invariant_violations(world, inputs, [0, 0, 0, 0]) == []
    # Negative where the world forbids it.
    assert invariant_violations(world, inputs, [-4, 0, 0, 0]) != []
    # Right answer, but scribbled on a slot nobody asked about.
    assert invariant_violations(world, inputs, [0, 1, 0, 0]) != []
    assert invariant_violations(world, inputs, None) != []


def test_no_qualifying_world_lives_in_a_module_the_lineage_imports():
    """D053's finding against M086-A, and PR #136's against M088, enforced from the import graph."""

    materializer = ROOT / "scripts/materialize_m091_qualification.py"
    families = {"capacity_planning", "protocol_window"}
    for relative in (
        "metamorphosis/m091_lineage.py", "metamorphosis/m091_worlds.py",
        "metamorphosis/m091_substrate.py", "metamorphosis/m091_expressivity.py",
        "metamorphosis/m091_search.py",
    ):
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)):
                text = ast.get_docstring(node, clean=False)
                if text:
                    docstrings.add(text)
        constants = {
            node.value for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        } - docstrings
        assert not (constants & families), f"{relative} names a qualifying family"
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported.add(node.module)
                imported.update(alias.name for alias in node.names)
        assert not any("materialize_m091" in name for name in imported), relative
    assert materializer.is_file()


def test_the_qualification_draw_depends_on_the_extended_language():
    sys.path.insert(0, str(ROOT / "scripts"))
    from materialize_m091_qualification import materialize

    first = materialize("salt-one", "digest-a")
    second = materialize("salt-two", "digest-a")
    assert first["artifact_digest"] != second["artifact_digest"]
    assert materialize("salt-one", "digest-a")["artifact_digest"] == first["artifact_digest"]
    assert {world["family"] for world in first["worlds"]} == {
        "capacity_planning", "protocol_window",
    }
    for world in first["worlds"]:
        assert len(world["hidden_instances"]) >= 4
        assert "hidden_pool" not in world


# -------------------------------------------------------------------------------------------
# the fresh process holds no development code
# -------------------------------------------------------------------------------------------


def test_the_fresh_process_cannot_reach_the_development_modules():
    inherited = migrated_l0()
    extended = inherited.register(clamp(), "test fixture")
    world = {
        "world_id": "fresh_probe", "family": "probe", "narrative": "n",
        "input_names": ["a", "b", "c"],
        "requirements": [{"slot": 0, "expression": ["max", ["input", 0], ["const", 0]]}],
        "invariants": [{"kind": "matches_requirement", "slot": 0}],
        "public_instances": [
            {"payload": {}, "inputs": list(item)} for item in SOUNDNESS_INPUTS[:4]
        ],
        "hidden_instances": [
            {"instance_id": "h", "inputs": list(item)} for item in SOUNDNESS_INPUTS[4:]
        ],
    }
    with tempfile.TemporaryDirectory() as scratch:
        state_path = Path(scratch) / "state.json"
        worlds_path = Path(scratch) / "worlds.json"
        state_path.write_text(json.dumps(extended.to_dict(), sort_keys=True), encoding="utf-8")
        worlds_path.write_text(json.dumps([world], sort_keys=True), encoding="utf-8")
        completed = subprocess.run(
            [
                sys.executable, str(ROOT / "scripts/run_m091_fresh_process.py"),
                "--state", str(state_path), "--worlds", str(worlds_path),
            ],
            capture_output=True, text=True, check=True,
        )
    payload = json.loads(completed.stdout)
    assert payload["development_modules_imported"] is False
    assert payload["imported_modules"] == []
    assert payload["correct_worlds"] == 1
    assert payload["language_unchanged_by_this_process"] is True


# -------------------------------------------------------------------------------------------
# the verdict must be able to fail
# -------------------------------------------------------------------------------------------


def _artifacts():
    path = EXPERIMENT / "RESULT.json"
    if not path.is_file():
        pytest.skip("no M091 result is present yet")
    result = json.loads(path.read_text(encoding="utf-8"))
    return (
        result["acquisition"], result["arms"], result["rollback"], result["conservation"],
        result["persistence"], result["integrity"], result,
    )


def test_declared_conditions_equal_evaluated_conditions():
    protocol = json.loads((EXPERIMENT / "PROTOCOL.json").read_text(encoding="utf-8"))
    assert sorted(protocol["conditions"]) == sorted(CONDITIONS)
    assert len(CONDITIONS) == len(set(CONDITIONS)) == 14
    acquisition, arms, rollback, conservation, persistence, integrity, result = _artifacts()
    verdict = evaluate(acquisition, arms, rollback, conservation, persistence, integrity)
    assert sorted(verdict["conditions"]) == sorted(CONDITIONS)
    assert sorted(result["conditions_declared"]) == sorted(CONDITIONS)
    assert verdict == result["evaluation"]


@pytest.mark.parametrize("condition", CONDITIONS)
def test_every_condition_can_fail(condition):
    """M086-A recorded a positive against a threshold that could not fail. This forbids that.

    For each condition, one field of the preserved artifacts is spoiled and the verdict must turn
    negative on that condition and no other pretext.
    """

    acquisition, arms, rollback, conservation, persistence, integrity, _ = _artifacts()
    acquisition = copy.deepcopy(acquisition)
    arms = copy.deepcopy(arms)
    rollback = copy.deepcopy(rollback)
    conservation = copy.deepcopy(conservation)
    persistence = copy.deepcopy(persistence)
    integrity = copy.deepcopy(integrity)

    if condition.startswith("P1_"):
        acquisition["diagnosis"]["outside_constructive_image"] = False
    elif condition.startswith("P2_"):
        acquisition["rejection_counts"] = {"malformed_or_partial": 1}
        acquisition["rejection_classes_observed"] = ["malformed_or_partial"]
    elif condition.startswith("P3_"):
        acquisition["validation"]["bend_witness"] = None
    elif condition.startswith("P4_"):
        acquisition["validation"]["accepted"] = False
    elif condition.startswith("P5_"):
        acquisition["l1_digest"] = acquisition["l0_digest"]
    elif condition.startswith("P6_"):
        arms["fixed_meta_language"]["correct_worlds"] = 1
    elif condition.startswith("P7_"):
        arms["evolvable_meta_language"]["encounters"][0]["hidden_passed"] = 0
    elif condition.startswith("P8_"):
        arms["more_budget_same_meta_language"]["correct_worlds"] = 1
    elif condition.startswith("P9_"):
        arms["macro_only_extension"]["primitive_registered"] = False
    elif condition.startswith("P10_"):
        arms["extension_built_but_not_registered"]["primitive_built"] = False
    elif condition.startswith("P11_"):
        conservation["space_excludes_nothing"] = False
    elif condition.startswith("P12_"):
        rollback["before_adoption"]["restore_reversed_the_live_state"] = False
    elif condition.startswith("P13_"):
        persistence["fresh_process_solves_every_world"] = False
    elif condition.startswith("P14_"):
        integrity["no_lookup_of_the_answer"] = False
    else:  # pragma: no cover - the parametrisation is exhaustive
        raise AssertionError(f"no spoiler is defined for {condition}")

    verdict = evaluate(acquisition, arms, rollback, conservation, persistence, integrity)
    assert verdict["verdict"] == "negative"
    assert condition in verdict["failed_conditions"]


def test_the_ceiling_arm_never_contributes_to_the_verdict():
    acquisition, arms, rollback, conservation, persistence, integrity, result = _artifacts()
    arms = copy.deepcopy(arms)
    for ceiling in CEILING_ARMS:
        assert arms[ceiling]["is_ceiling"] is True
        arms[ceiling]["correct_worlds"] = 0
        arms[ceiling]["families_solved"] = []
    spoiled = evaluate(acquisition, arms, rollback, conservation, persistence, integrity)
    assert spoiled["verdict"] == result["evaluation"]["verdict"]
    assert spoiled["conditions"] == result["evaluation"]["conditions"]


def test_the_arms_are_the_protocols_arms():
    protocol = json.loads((EXPERIMENT / "PROTOCOL.json").read_text(encoding="utf-8"))
    assert sorted(protocol["arms"]) == sorted(ARMS)
    assert sorted(protocol["ceiling_arms"]) == sorted(CEILING_ARMS)
    assert set(CEILING_ARMS) <= set(ARMS)
    for required in (
        "evolvable_meta_language", "fixed_meta_language", "extension_acquisition_ablated",
        "extension_built_but_not_registered", "macro_only_extension",
        "more_budget_same_meta_language", "fresh_agent", "authored_correct_primitive",
    ):
        assert required in ARMS


def test_the_acquisition_adopts_by_construction_and_not_by_name():
    """A short but real end-to-end check: the frozen rule assembles something that bends."""

    acquisition = acquire_primitive(development_world())
    assert acquisition.adopted is not None
    assert acquisition.candidates_assembled > 1_000
    assert len(acquisition.rejected) > 100
    assert acquisition.search_cost["gain_was_reach"] is True
    shape = primitive_shape_report(acquisition.adopted)
    assert shape["bends_the_affine_invariant"] is True
    assert shape["preserves_single_source"] is True
    assert primitive_bend_witness(acquisition.adopted) is not None
    assert semantics_digest(
        acquisition.adopted.body, acquisition.adopted.parameter_kinds
    ) not in inherited_macro_semantics(acquisition.adopted.parameter_kinds, migrated_l0())
    assert len(parameter_bindings(acquisition.adopted.parameter_kinds)) == SLOT_COUNT
