"""M087, attacked at every point where the result could be manufactured rather than earned."""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from metamorphosis.m047_software_core import SoftwareCase
from metamorphosis.m086_evolvable_mechanism import diagnose, generate, m0_mechanism
from metamorphosis.m087_evidence import (
    AcquisitionLog,
    EvidenceError,
    EvidenceSpaces,
    Observation,
    assert_domains_disjoint,
    leak_problems,
)
from metamorphosis.m087_families import (
    FAMILIES,
    QUALIFICATION_POOL,
    all_families,
    family,
    materialize_qualification,
    qualified_family,
)
from metamorphosis.m087_lineage import (
    ARMS,
    CONDITIONS,
    DEVELOPMENT_FAMILY,
    QUALIFICATION_FAMILIES,
    evaluate,
    observe,
    rollback_proof,
)
from metamorphosis.m087_selection_policy import (
    INSTRUCTIONS,
    META_PRIMITIVES,
    SCORING_RULES,
    SOUND_SCORING_RULES,
    Instruction,
    PolicyError,
    SelectionPolicy,
    apply_meta_primitive,
    build_policy,
    candidate_meta_transformations,
    execute_policy,
    m0_policy,
)


ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / "experiments/M087/RESULT.json"


# ---------------------------------------------------------------------------------------------
# M0 is the rule the repository actually froze
# ---------------------------------------------------------------------------------------------


def test_m0_is_score_public_then_argmax_first() -> None:
    assert m0_policy().opcodes == ("SCORE_PUBLIC", "ARGMAX_FIRST")
    assert m0_policy().acquisition_budget == 0
    assert m0_policy().can_acquire is False


def test_m0_reproduces_m086_strict_greater_argmax_over_emission_order() -> None:
    """The differential regression. Without it M0 would be a mechanism written for the occasion.

    `m086_meta_lineage.run_cycle` keeps `best` only when `passed > best[0]`, scanning candidates in
    emission order. On a tie that retains the earlier candidate. M0's program must do the same on
    every tie pattern, not merely on the one M086-C drew.
    """

    labels = ("first", "second", "third")
    for scores in (
        {"first": 1, "second": 1, "third": 0},
        {"first": 0, "second": 1, "third": 1},
        {"first": 1, "second": 1, "third": 1},
        {"first": 2, "second": 1, "third": 2},
    ):
        expected: str | None = None
        best = 0
        for label in labels:  # verbatim shape of run_cycle's loop
            if scores[label] > best:
                expected, best = label, scores[label]
        outcome = execute_policy(
            m0_policy(), candidates=labels, public_scores=scores, incumbent_score=0,
            experiment_space=("a",), predict=lambda *_a: Observation("a", True, 0),
            acquire=lambda _r: Observation("a", True, 0),
        )
        assert outcome.selected == expected, scores
        assert outcome.ambiguity_detected is False
        assert outcome.acquisitions == 0


# ---------------------------------------------------------------------------------------------
# the evidence boundary
# ---------------------------------------------------------------------------------------------


def test_every_family_has_disjoint_acquirable_and_hidden_domains() -> None:
    for fam in all_families():
        assert_domains_disjoint(fam.acquirable_requests, [c.request for c in fam.hidden_cases])
        fam.spaces  # constructing the spaces re-checks it


def test_a_family_whose_domains_overlap_cannot_be_built() -> None:
    # The first draft of the planning family did exactly this.
    with pytest.raises(EvidenceError, match="overlap"):
        EvidenceSpaces(("add 1 add 2 add 3 4",), ("add 1 add 2 add 3 4",))


def test_qualification_draws_stay_out_of_every_experiment_space() -> None:
    for salt in ("alpha", "beta", "gamma", "m087-qualification-salt-2026-08-12"):
        for family_id in QUALIFICATION_FAMILIES:
            fam = qualified_family(family_id, salt)
            assert_domains_disjoint(
                fam.acquirable_requests, [c.request for c in fam.hidden_cases]
            )


def test_acquiring_a_hidden_request_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    spaces = EvidenceSpaces(("allowed",), ("secret",))
    log = AcquisitionLog(spaces, budget=4)
    with pytest.raises(EvidenceError, match="hidden-domain"):
        log.record(Observation("secret", True, 1))


def test_acquiring_outside_the_frozen_experiment_space_is_refused() -> None:
    log = AcquisitionLog(EvidenceSpaces(("allowed",), ("secret",)), budget=4)
    with pytest.raises(EvidenceError, match="outside the frozen experiment space"):
        log.record(Observation("improvised", True, 1))


def test_acquiring_after_hidden_evaluation_is_sealed_is_refused() -> None:
    log = AcquisitionLog(EvidenceSpaces(("allowed",), ("secret",)), budget=4)
    log.seal()
    with pytest.raises(EvidenceError, match="after hidden evaluation was sealed"):
        log.record(Observation("allowed", True, 1))


def test_the_acquisition_budget_cannot_be_exceeded() -> None:
    log = AcquisitionLog(EvidenceSpaces(("a", "b"), ("s",)), budget=1)
    log.record(Observation("a", True, 1))
    with pytest.raises(EvidenceError, match="budget is exhausted"):
        log.record(Observation("b", True, 1))


def test_the_leak_checker_reports_a_hidden_domain_acquisition() -> None:
    spaces = EvidenceSpaces(("allowed",), ("secret",))
    forged = {
        "schema": "m087-acquisition-log-v1", "budget": 4, "count": 1,
        "entries": [{"sequence": 0, "observation": {
            "request": "secret", "ok": True, "output": 1, "error": None, "key": "value:1",
        }}],
        "hidden_evaluation_sealed": True,
        "experiment_space_digest": spaces.digest(),
    }
    problems = leak_problems(forged, spaces, ["secret"])
    assert any("hidden evaluation request" in item for item in problems)


def test_the_leak_checker_reports_a_non_monotone_log() -> None:
    spaces = EvidenceSpaces(("allowed",), ("secret",))
    forged = {
        "schema": "m087-acquisition-log-v1", "budget": 4, "count": 1,
        "entries": [{"sequence": 7, "observation": {
            "request": "allowed", "ok": True, "output": 1, "error": None, "key": "value:1",
        }}],
        "hidden_evaluation_sealed": True,
        "experiment_space_digest": spaces.digest(),
    }
    assert any("append-only" in item for item in leak_problems(forged, spaces, ["secret"]))


def test_no_policy_can_reach_an_evaluator() -> None:
    """Structural: `execute_policy` takes `predict` and `acquire` and no evaluator at all."""

    import inspect

    parameters = set(inspect.signature(execute_policy).parameters)
    assert "acquire" in parameters and "predict" in parameters
    assert not {name for name in parameters if "evaluat" in name or "hidden" in name}


# ---------------------------------------------------------------------------------------------
# the ambiguity is real, and detected only by the evolved policy
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("family_id", FAMILIES)
def test_every_family_leaves_at_least_two_candidates_observationally_equivalent(
    family_id: str,
) -> None:
    from metamorphosis.m087_lineage import _candidate_bodies, _public_scores

    fam = family(family_id)
    prepared = _candidate_bodies(fam)
    scores = _public_scores(prepared, fam)
    best = max(scores.values())
    tied = [label for label, score in scores.items() if score == best]
    assert len(tied) >= 2, (family_id, scores)


@pytest.mark.parametrize("family_id", FAMILIES)
def test_the_frozen_diagnosis_isolates_one_module_in_every_family(family_id: str) -> None:
    from metamorphosis.m087_lineage import _run

    fam = family(family_id)
    hypothesis = diagnose(m0_mechanism(), _run(fam.starting_body, fam.public_cases).cases)
    assert hypothesis.sufficient and hypothesis.modules == (fam.module,)


def test_a_detector_may_not_claim_ambiguity_when_one_candidate_is_already_contradicted() -> None:
    policy = build_policy(m0_policy(), [("add_ambiguity_guard", None)])
    outcome = execute_policy(
        policy, candidates=("a", "b"), public_scores={"a": 2, "b": 1}, incumbent_score=0,
        experiment_space=("q",), predict=lambda *_a: Observation("q", True, 0),
        acquire=lambda _r: Observation("q", True, 0),
    )
    assert outcome.ambiguity_detected is False
    assert outcome.selected == "a"


# ---------------------------------------------------------------------------------------------
# acquisition must inform, not merely differ
# ---------------------------------------------------------------------------------------------


def _full_policy(rule: str) -> SelectionPolicy:
    return build_policy(m0_policy(), [
        ("add_ambiguity_guard", None), ("add_prediction_projection", None),
        ("add_equivalence_partition", None), ("add_experiment_enumerator", None),
        ("add_scoring_rule", rule), ("add_acquisition_transition", None),
        ("add_survivor_filter", None), ("set_acquisition_budget", 4),
        ("add_defer_condition", None),
    ])


def test_a_non_discriminating_experiment_space_leaves_the_policy_deferring() -> None:
    """If no available experiment separates the candidates, the answer is INSUFFICIENT_EVIDENCE.

    Nothing is fabricated from the candidates themselves.
    """

    outcome = execute_policy(
        _full_policy("partition_size"),
        candidates=("a", "b"), public_scores={"a": 1, "b": 1}, incumbent_score=0,
        experiment_space=("q1", "q2"),
        predict=lambda _label, request: Observation(request, True, 0),
        acquire=lambda request: Observation(request, True, 0),
    )
    assert outcome.terminal_state == "deferred_insufficient_evidence"
    assert outcome.selected is None


def test_a_discriminating_experiment_resolves_the_ambiguity() -> None:
    predictions = {"a": {"q1": 1, "q2": 5}, "b": {"q1": 1, "q2": 9}}
    outcome = execute_policy(
        _full_policy("partition_size"),
        candidates=("a", "b"), public_scores={"a": 1, "b": 1}, incumbent_score=0,
        experiment_space=("q1", "q2"),
        predict=lambda label, request: Observation(request, True, predictions[label][request]),
        acquire=lambda request: Observation(request, True, {"q1": 1, "q2": 9}[request]),
    )
    assert outcome.terminal_state == "adopted"
    assert outcome.selected == "b"
    assert outcome.acquisitions == 1


def test_the_decoy_scoring_rules_do_not_resolve_the_ambiguity() -> None:
    """`first_index` and `constant` are plausible and wrong: they pick a useless experiment."""

    predictions = {"a": {"q1": 1, "q2": 5}, "b": {"q1": 1, "q2": 9}}
    for rule in ("first_index", "constant"):
        outcome = execute_policy(
            _full_policy(rule),
            candidates=("a", "b"), public_scores={"a": 1, "b": 1}, incumbent_score=0,
            experiment_space=("q1", "q2"),
            predict=lambda label, request: Observation(request, True, predictions[label][request]),
            acquire=lambda request: Observation(request, True, {"q1": 1, "q2": 9}[request]),
        )
        assert outcome.selected != "b" or outcome.acquisitions > 1, rule


def test_more_than_one_scoring_rule_is_viable() -> None:
    """Falsifier: a meta-language offering exactly one viable transformation proves nothing."""

    predictions = {"a": {"q1": 1, "q2": 5}, "b": {"q1": 1, "q2": 9}}
    viable = []
    for rule in SOUND_SCORING_RULES:
        outcome = execute_policy(
            _full_policy(rule),
            candidates=("a", "b"), public_scores={"a": 1, "b": 1}, incumbent_score=0,
            experiment_space=("q1", "q2"),
            predict=lambda label, request: Observation(request, True, predictions[label][request]),
            acquire=lambda request: Observation(request, True, {"q1": 1, "q2": 9}[request]),
        )
        if outcome.selected == "b":
            viable.append(rule)
    assert len(viable) >= 2, viable


def test_evidence_acquired_is_used_rather_than_assumed() -> None:
    """Reverse the observation and the surviving candidate reverses with it."""

    predictions = {"a": {"q": 5}, "b": {"q": 9}}
    for truth, expected in ((5, "a"), (9, "b")):
        outcome = execute_policy(
            _full_policy("partition_size"),
            candidates=("a", "b"), public_scores={"a": 1, "b": 1}, incumbent_score=0,
            experiment_space=("q",),
            predict=lambda label, request: Observation(request, True, predictions[label][request]),
            acquire=lambda request: Observation(request, True, truth),
        )
        assert outcome.selected == expected


# ---------------------------------------------------------------------------------------------
# the meta-language does not encode the answer
# ---------------------------------------------------------------------------------------------


def test_no_meta_primitive_names_a_family_probe_candidate_or_truth() -> None:
    # `add` and `mul` are excluded deliberately: every primitive begins with the verb `add_`,
    # which says nothing about arithmetic. What must not appear is a family, a probe, a candidate
    # option or a truth.
    forbidden = (
        "mean", "midpoint", "combine", "one_level", "recursive",
        "tool_semantics", "interpretation_routing", "planning_structure",
    )
    for primitive in META_PRIMITIVES:
        for token in forbidden:
            assert token not in primitive, (primitive, token)
    for opcode in INSTRUCTIONS:
        for token in forbidden:
            assert token not in opcode.lower(), (opcode, token)


def test_the_policy_module_contains_no_family_specific_branch() -> None:
    """Prose may explain M086-C; executable code may not know a family, probe or truth.

    Docstrings and comments are stripped, so the check is about what the interpreter can branch
    on rather than about what the file is allowed to say.
    """

    tree = ast.parse((ROOT / "metamorphosis/m087_selection_policy.py").read_text(encoding="utf-8"))
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
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    for token in ("midpoint", "combine", "recursive_postorder", "tool_semantics"):
        assert not any(token in item for item in literals), token
        assert not any(token in item for item in names), token


def test_a_policy_is_an_executable_program_not_a_configuration_flag() -> None:
    policy = _full_policy("partition_size")
    assert len(policy.program) >= 6
    assert all(isinstance(item, Instruction) for item in policy.program)
    restored = SelectionPolicy.from_dict(json.loads(json.dumps(policy.to_dict())))
    assert restored.digest() == policy.digest()


def test_an_unknown_instruction_or_scoring_rule_is_refused() -> None:
    with pytest.raises(PolicyError):
        Instruction("INSTALL_ACTIVE_LEARNING")
    with pytest.raises(PolicyError):
        Instruction("SCORE_EXPERIMENTS", "read_the_answer")
    with pytest.raises(PolicyError):
        apply_meta_primitive(m0_policy(), "install_correct_selector")


def test_no_single_meta_primitive_produces_a_working_acquisition_loop() -> None:
    predictions = {"a": {"q": 5}, "b": {"q": 9}}
    arguments: dict[str, str | int | None] = {
        "add_scoring_rule": "partition_size", "set_acquisition_budget": 4,
    }
    for primitive in META_PRIMITIVES:
        policy = apply_meta_primitive(m0_policy(), primitive, arguments.get(primitive))
        outcome = execute_policy(
            policy, candidates=("a", "b"), public_scores={"a": 1, "b": 1}, incumbent_score=0,
            experiment_space=("q",),
            predict=lambda label, request: Observation(request, True, predictions[label][request]),
            acquire=lambda request: Observation(request, True, 9),
        )
        assert not (outcome.selected == "b" and outcome.acquisitions >= 1), primitive


def test_the_meta_search_space_offers_several_complete_compositions() -> None:
    space = candidate_meta_transformations()
    complete = [
        steps for steps in space
        if {name for name, _ in steps} >= {"add_acquisition_transition", "add_survivor_filter"}
    ]
    assert len(space) >= 8 and len(complete) >= len(SCORING_RULES)


# ---------------------------------------------------------------------------------------------
# persistence and rollback
# ---------------------------------------------------------------------------------------------


def test_rollback_detects_corruption_and_restores_byte_identically() -> None:
    proof = rollback_proof(_full_policy("partition_size"))
    assert proof["corruption_detected"] is True
    assert proof["byte_identical_restore"] is True
    assert proof["digest_matches"] is True
    assert proof["corrupted_digest"] != proof["checkpoint_digest"]


def test_a_restored_policy_behaves_identically() -> None:
    policy = _full_policy("partition_size")
    restored = SelectionPolicy.from_dict(json.loads(json.dumps(policy.to_dict())))
    predictions = {"a": {"q": 5}, "b": {"q": 9}}
    outcomes = [
        execute_policy(
            item, candidates=("a", "b"), public_scores={"a": 1, "b": 1}, incumbent_score=0,
            experiment_space=("q",),
            predict=lambda label, request: Observation(request, True, predictions[label][request]),
            acquire=lambda request: Observation(request, True, 9),
        ).selected
        for item in (policy, restored)
    ]
    assert outcomes[0] == outcomes[1] == "b"


def test_a_malformed_serialized_policy_is_refused() -> None:
    with pytest.raises(PolicyError):
        SelectionPolicy.from_dict({"schema": "wrong", "program": [], "acquisition_budget": 0,
                                   "provenance": [], "version": 0})


# ---------------------------------------------------------------------------------------------
# the verdict function
# ---------------------------------------------------------------------------------------------


def test_every_declared_condition_is_computed() -> None:
    """The M086-A defect, made impossible: four of ten conditions were absent from `evaluate`."""

    stub_arm = {
        "situations": [], "correct_terminal_decisions": 0, "situation_count": 0,
        "total_acquisitions": 0, "total_candidates_evaluated": 0,
    }
    verdict = evaluate(
        {"limitation": {
            "observationally_equivalent_count": 0, "m0_ambiguity_detected": True,
            "m0_correct": True,
        }, "adopted_policy": None, "rejected_count": 0},
        {arm: dict(stub_arm) for arm in ARMS},
        {"corruption_detected": False, "byte_identical_restore": False, "digest_matches": False},
        ["a finding"],
        {"ordered": False},
    )
    assert set(verdict["conditions"]) == set(CONDITIONS)
    assert verdict["verdict"] == "negative"
    assert len(verdict["failed_conditions"]) >= 8


@pytest.mark.parametrize("condition", CONDITIONS)
def test_each_condition_can_independently_fail(condition: str) -> None:
    assert condition in CONDITIONS
    source = (ROOT / "metamorphosis/m087_lineage.py").read_text(encoding="utf-8")
    assert f'"{condition}"' in source


# ---------------------------------------------------------------------------------------------
# the preserved result
# ---------------------------------------------------------------------------------------------


@pytest.fixture()
def result() -> dict[str, object]:
    if not RESULT_PATH.exists():
        pytest.skip("the M087 result has not been materialized in this tree")
    return json.loads(RESULT_PATH.read_text(encoding="utf-8"))


def test_the_result_is_attempt_one_with_no_retry(result: dict[str, object]) -> None:
    assert result["attempt"] == 1 and result["retry_used"] is False


def test_the_result_records_no_model_or_network_call(result: dict[str, object]) -> None:
    assert result["model_calls"] == 0 and result["network_calls"] == 0


def test_the_result_declares_every_frozen_condition(result: dict[str, object]) -> None:
    assert set(result["conditions_declared"]) == set(CONDITIONS)  # type: ignore[arg-type]
    assert set(result["evaluation"]["conditions"]) == set(CONDITIONS)  # type: ignore[index]


def test_the_chronology_puts_adoption_before_qualification(result: dict[str, object]) -> None:
    chronology = result["chronology"]
    assert chronology["adoption_precedes_qualification"] is True  # type: ignore[index]
    order = chronology["order"]  # type: ignore[index]
    assert order.index("T6_policy_adopted_and_serialized") < order.index(
        "T7_qualification_materialized"
    )


def test_the_result_binds_the_frozen_protocol(result: dict[str, object]) -> None:
    import hashlib

    raw = (ROOT / "experiments/M087/PROTOCOL.json").read_bytes()
    assert result["protocol_raw_sha256"] == hashlib.sha256(raw).hexdigest()


def test_no_arm_acquired_anything_it_was_not_entitled_to(result: dict[str, object]) -> None:
    assert result["leak_findings"] == []
    for arm, record in result["arms"].items():  # type: ignore[union-attr]
        if arm != "evolvable_selection_evidence":
            assert record["total_acquisitions"] == 0, arm


def test_the_budget_arm_spent_more_computation_and_gained_nothing(
    result: dict[str, object],
) -> None:
    arms = result["arms"]
    budgeted = arms["more_budget_same_evidence"]  # type: ignore[index]
    fixed = arms["fixed_selection_evidence"]  # type: ignore[index]
    assert budgeted["total_candidates_evaluated"] > fixed["total_candidates_evaluated"]
    assert budgeted["total_acquisitions"] == 0
    assert budgeted["correct_terminal_decisions"] == fixed["correct_terminal_decisions"]


def test_the_ablated_arm_can_see_the_ambiguity_and_cannot_resolve_it(
    result: dict[str, object],
) -> None:
    ablated = result["arms"]["selection_acquisition_ablated"]  # type: ignore[index]
    assert ablated["total_acquisitions"] == 0
    assert ablated["correct_terminal_decisions"] == 0
    for situation in ablated["situations"]:
        assert situation["selection"]["terminal_state"] == "deferred_insufficient_evidence"


def test_the_capability_difference_is_correctness_not_cost(result: dict[str, object]) -> None:
    evaluation = result["evaluation"]
    assert evaluation["discordant_families"], "no correctness discordance was recorded"
    assert not set(evaluation["fixed_correct_families"]) - set(  # type: ignore[arg-type]
        evaluation["evolvable_correct_families"]  # type: ignore[arg-type]
    )


def test_cross_family_reuse_is_recorded(result: dict[str, object]) -> None:
    discordant = set(result["evaluation"]["discordant_families"])  # type: ignore[index]
    assert discordant - {DEVELOPMENT_FAMILY}, "no reuse outside the acquiring family"


def test_the_qualification_draw_is_reproducible_from_the_recorded_salt(
    result: dict[str, object],
) -> None:
    from metamorphosis.m087_evidence import digest_of

    salt = "m087-qualification-salt-2026-08-12"
    assert digest_of(salt) == result["salt_digest"]
    for family_id in QUALIFICATION_FAMILIES:
        drawn = materialize_qualification(family_id, salt)
        assert len(drawn) == 2
        assert all(case.request in dict(QUALIFICATION_POOL[family_id]) for case in drawn)


# ---------------------------------------------------------------------------------------------
# Track A
# ---------------------------------------------------------------------------------------------


M087_MODULES = (
    "metamorphosis/m087_evidence.py",
    "metamorphosis/m087_selection_policy.py",
    "metamorphosis/m087_families.py",
    "metamorphosis/m087_lineage.py",
    "scripts/run_m087_experiment.py",
)


@pytest.mark.parametrize("relative", M087_MODULES)
def test_no_m087_module_can_reach_a_model_or_a_network(relative: str) -> None:
    tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    forbidden = {"socket", "urllib", "urllib.request", "http", "http.client", "requests", "openai"}
    assert not (imported & forbidden), (relative, sorted(imported & forbidden))
