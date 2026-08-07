import copy

import pytest

from metamorphosis.m054_compositional_construction import (
    ADMISSIBLE_SPACE, AMBIGUOUS_PUBLIC, ATOMS, BEAM_WIDTH, CONSTRUCTION_BUDGET,
    CREATION_CONTRADICTORY_HIDDEN, CREATION_HIDDEN, CREATION_PUBLIC, MAX_COMPOSITION_LENGTH,
    MAX_EXPRESSION_DEPTH, OPERATORS, REUSE_HIDDEN, REUSE_PUBLIC, Expr, M054Error, Probe,
    Registry, certify_founder_insufficiency, compose_from_registry, construct_primitive,
    corrupt_registry, detect_fault, expression_space_size, independently_validate,
    load_primitive, run_m054_compositional_construction, run_program,
)

ABS_DELTA = Expr(
    operator="maximum",
    left=Expr(operator="subtract", left=Expr(atom="previous"), right=Expr(atom="current")),
    right=Expr(operator="subtract", left=Expr(atom="current"), right=Expr(atom="previous")),
)


def test_the_admissible_space_is_far_larger_than_the_budget():
    assert expression_space_size(0) == len(ATOMS)
    assert expression_space_size(1) == 22
    assert expression_space_size(2) == 2422
    assert ADMISSIBLE_SPACE == expression_space_size(MAX_EXPRESSION_DEPTH) == 29330422
    # The budget cannot enumerate even the second formation level, let alone the declared one.
    assert CONSTRUCTION_BUDGET < expression_space_size(2)
    assert CONSTRUCTION_BUDGET * 1000 < ADMISSIBLE_SPACE


def test_the_founder_language_cannot_reach_either_task():
    for probes in (CREATION_PUBLIC, REUSE_PUBLIC):
        certificate = certify_founder_insufficiency(probes)
        assert certificate["founder_candidate_count"] == 80
        assert certificate["survivor_count"] == 0
        assert certificate["insufficient"] is True


def test_construction_builds_the_primitive_without_enumerating_the_space():
    result = construct_primitive(CREATION_PUBLIC)

    assert result.status == "constructed"
    assert result.reduction == "sum"
    assert load_primitive(result.primitive).behaviour() == ABS_DELTA.behaviour()
    assert load_primitive(result.primitive).depth == 2
    assert 0 < result.candidates_constructed < expression_space_size(2)
    assert result.candidates_constructed <= CONSTRUCTION_BUDGET


def test_behaviour_is_judged_on_the_declared_domain_not_on_syntax():
    commuted = Expr(operator="maximum", left=ABS_DELTA.right, right=ABS_DELTA.left)

    assert commuted.artifact()["digest"] != ABS_DELTA.artifact()["digest"]
    assert commuted.behaviour() == ABS_DELTA.behaviour()
    assert Expr(atom="previous").behaviour() != Expr(atom="current").behaviour()


def test_ambiguous_evidence_refuses_to_commit_without_widening():
    result = construct_primitive(AMBIGUOUS_PUBLIC)

    assert result.status == "insufficient_evidence"
    assert result.primitive is None
    assert result.admissible_space == ADMISSIBLE_SPACE
    assert result.candidates_constructed <= CONSTRUCTION_BUDGET


def test_hidden_validation_accepts_and_rejects_independently():
    result = construct_primitive(CREATION_PUBLIC)

    assert independently_validate((result.primitive,), "sum", CREATION_HIDDEN) is True
    assert independently_validate((result.primitive,), "sum", CREATION_CONTRADICTORY_HIDDEN) is False
    with pytest.raises(M054Error, match="hidden probes are required"):
        independently_validate((result.primitive,), "sum", ())


def test_a_tampered_primitive_is_rejected():
    result = construct_primitive(CREATION_PUBLIC)
    tampered = copy.deepcopy(result.primitive)
    tampered["expression"]["operator"] = "minimum"

    with pytest.raises(M054Error, match="digest mismatch"):
        independently_validate((tampered,), "sum", CREATION_HIDDEN)


def test_an_unvalidated_primitive_cannot_be_adopted():
    result = construct_primitive(CREATION_PUBLIC)

    with pytest.raises(M054Error, match="unvalidated"):
        Registry().adopt(result.primitive, False)


def test_the_second_task_is_solved_only_by_composing_the_acquired_primitive():
    registry = Registry().adopt(construct_primitive(CREATION_PUBLIC).primitive, True)

    composed = compose_from_registry(REUSE_PUBLIC, registry.primitives())

    assert composed is not None
    chain, reduction = composed
    assert len(chain) == 2
    assert chain[0].behaviour() == chain[1].behaviour() == ABS_DELTA.behaviour()
    assert reduction == "maximum"
    assert independently_validate(tuple(p.artifact() for p in chain), reduction, REUSE_HIDDEN) is True
    # One application of the same primitive does not reach the second task.
    for single in REUSE_PUBLIC:
        assert run_program(chain[:1], reduction, single.values) != single.expected


def test_the_acquired_primitive_is_what_makes_the_second_task_reachable():
    """The ablation arms. Without the acquisition, the same budget does not get there."""
    assert compose_from_registry(REUSE_PUBLIC, Registry().primitives()) is None

    from_scratch = construct_primitive(REUSE_PUBLIC, max_chain=MAX_COMPOSITION_LENGTH)

    assert from_scratch.status != "constructed"
    assert from_scratch.candidates_constructed == CONSTRUCTION_BUDGET


def test_an_intact_registry_reports_no_fault():
    """The fault detector must be able to answer no, or detecting a fault proves nothing."""
    registry = Registry().adopt(construct_primitive(CREATION_PUBLIC).primitive, True)

    assert detect_fault(registry, registry.checkpoint()) is False


def test_a_tampered_registry_is_detected_and_restored_byte_for_byte():
    registry = Registry().adopt(construct_primitive(CREATION_PUBLIC).primitive, True)
    checkpoint = registry.checkpoint()
    snapshot = registry.snapshot()

    faulted = corrupt_registry(registry)

    assert faulted.accepted[-1] != registry.accepted[-1]
    assert detect_fault(faulted, checkpoint) is True

    restored = Registry.restore(snapshot, checkpoint)

    assert restored.accepted == registry.accepted
    assert restored.checkpoint() == checkpoint
    assert restored.snapshot() == snapshot
    assert detect_fault(restored, checkpoint) is False


def test_restore_refuses_a_snapshot_that_does_not_match_its_checkpoint():
    registry = Registry().adopt(construct_primitive(CREATION_PUBLIC).primitive, True)

    with pytest.raises(M054Error, match="does not match its checkpoint"):
        Registry.restore(registry.snapshot(), Registry().checkpoint())
    with pytest.raises(M054Error, match="does not match its checkpoint"):
        Registry.restore(corrupt_registry(registry).snapshot(), registry.checkpoint())


def test_an_empty_registry_cannot_carry_a_post_adoption_fault():
    with pytest.raises(M054Error, match="empty registry"):
        corrupt_registry(Registry())


def test_a_primitive_beyond_the_declared_depth_is_rejected():
    deep = Expr(operator="add", left=ABS_DELTA, right=ABS_DELTA)
    assert deep.depth == 3

    too_deep = Expr(operator="add", left=deep, right=deep)
    artifact = too_deep.artifact()

    assert too_deep.depth == 4
    with pytest.raises(M054Error, match="declared formation depth"):
        load_primitive(artifact)


def test_malformed_expressions_are_refused_at_construction():
    with pytest.raises(M054Error, match="unknown atom"):
        Expr(atom="next")
    with pytest.raises(M054Error, match="unknown operator"):
        Expr(operator="divide", left=Expr(atom="previous"), right=Expr(atom="current"))
    with pytest.raises(M054Error, match="two operands"):
        Expr(operator="add", left=Expr(atom="previous"))
    with pytest.raises(M054Error, match="no operator or operands"):
        Expr(atom="previous", operator="add")


def test_manifest_is_deterministic_and_preserves_authority_boundaries():
    first = run_m054_compositional_construction()
    second = run_m054_compositional_construction()

    assert first == second
    assert first["admissible_space"] == ADMISSIBLE_SPACE
    assert first["construction_budget"] == CONSTRUCTION_BUDGET
    assert first["creation_candidates_constructed"] < first["admissible_space"]
    assert first["creation_hidden_validated"] is True
    assert first["creation_contradictory_hidden_accepted"] is False
    assert first["reuse_chain_length"] == 2
    assert first["reuse_hidden_validated"] is True
    assert first["reuse_solved_without_acquired_primitive"] is False
    assert first["reuse_reachable_from_scratch_within_budget"] is False
    assert first["refusal_status"] == "insufficient_evidence"
    assert first["fault_detected"] is True
    assert first["rollback_exact"] is True
    assert first["arbitrary_code_generation"] is False
    assert first["network_authority"] is False
    assert first["repository_authority"] is False
    assert first["credential_authority"] is False
    assert first["deployment_authority"] is False
    assert first["canonical"] is False


def test_the_declared_search_parameters_are_pinned():
    assert ATOMS == ("previous", "current")
    assert OPERATORS == ("add", "subtract", "minimum", "maximum", "multiply")
    assert BEAM_WIDTH == 12
    assert MAX_COMPOSITION_LENGTH == 2
    assert MAX_EXPRESSION_DEPTH == 3
