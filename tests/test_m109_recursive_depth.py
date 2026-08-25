"""M109 recursive-depth tests.

The phase check is bound to the artefacts on disk from the start: M105's equivalent test asserted a
pre-result invariant unconditionally and turned both CI jobs red the moment its result was sealed.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from metamorphosis import m107_runtime as m107
from metamorphosis import m109_runtime as runtime
from scripts import audit_m109_boundaries
from scripts import author_m109_curriculum as author
from scripts import check_m109_result as checker
from scripts import run_m109_qualification as qualification

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "M109"
_PHASE_CHECK = "canonical_evidence_absent_before_attempt"


def _canonical_evidence_exists() -> bool:
    return (EXPERIMENT / "RESULT.json").exists() or (EXPERIMENT / "CHECK_REPORT.json").exists()


def _stage(index: int) -> dict:
    return json.loads((EXPERIMENT / ("DEMAND_STAGE%d.json" % index)).read_text("ascii"))


@pytest.fixture(scope="module")
def domain() -> dict:
    return runtime.attribution_domain()


@pytest.fixture(scope="module")
def chain(domain: dict) -> dict:
    """The two-generation chain, built once for every test that needs it."""
    m0 = runtime.create_state()
    episode1 = runtime.record_episode(m0, _stage(1)["demand"])
    first = runtime.acquire_rule(m0, [episode1], domain, register_result=True)
    m1 = first["next_state"]
    resolved = runtime.resolve(m1, _stage(1)["demand"])
    m1_after = runtime.create_state(
        m1["operators"],
        signal_width=resolved["final_signal_width"],
        candidate_space=resolved["final_candidate_space"],
        rules=m1["rules"],
    )
    episode2 = runtime.record_episode(m1_after, _stage(2)["demand"])
    second = runtime.acquire_rule(m1_after, [episode1, episode2], domain, register_result=True)
    return {
        "m0": m0,
        "m1": m1,
        "m1_after": m1_after,
        "m2": second["next_state"],
        "episode1": episode1,
        "episode2": episode2,
        "first": first,
        "second": second,
        "stage_one_resolution": resolved,
    }


def test_the_monotone_candidate_space_is_closed_by_a_lemma_not_a_budget() -> None:
    m0 = runtime.create_state()
    for bound in (5, runtime.MAX_EXPRESSION_NODES, 11):
        certificate = runtime.candidate_space_closure_certificate(
            m0["operators"], m0["signal_width"], runtime.MONOTONE_SPACE, bound
        )
        assert certificate["confirmed"] is True
        assert certificate["closed_by_monotonicity_lemma"] is True
        assert certificate["budget_independent"] is True
        assert certificate["everything_reachable_is_monotone"] is True
    # The certificate must be false for a space that is not closed, or it proves nothing.
    complete = runtime.candidate_space_closure_certificate(
        m0["operators"], m0["signal_width"], runtime.COMPLETE_SPACE
    )
    assert complete["closed_by_monotonicity_lemma"] is False


def test_the_attribution_domain_is_a_census_with_no_ambiguous_row(domain: dict) -> None:
    assert domain["census_complete"] is True
    assert domain["ambiguous_rows"] == []
    assert domain["state_family_size"] == len(runtime.probe_states())
    assert domain["world_function_count"] == 2 ** (2 ** runtime.WORLD_SIGNAL_WIDTH)
    assert all(len(labels) == 1 for labels in domain["row_labels"].values())
    assert sorted(domain["rows"]) + sorted(domain["unreachable_rows"]) != []


def test_the_blame_labels_come_from_the_lineage_not_from_a_fixture(chain: dict) -> None:
    assert not (EXPERIMENT / "EPISODES.json").exists()
    for episode in (chain["episode1"], chain["episode2"]):
        assert episode["trial"]["label_source"] == "lineage_component_trial"
        assert episode["trial"]["semantics"] == "minimal_necessary_component"
        assert sorted(episode["trial"]["outcomes"]) == sorted(runtime.COMPONENTS)
        assert episode["usable"] is True
    assert chain["episode1"]["component"] == runtime.COMPONENT_SIGNALS
    assert chain["episode2"]["component"] == runtime.COMPONENT_CANDIDATES


def test_the_hardwired_machinery_fails_with_progress_still_available(chain: dict) -> None:
    """Not exhaustion in general: exhaustion for this demand, on the only axis it can name."""
    resolution = runtime.resolve(chain["m0"], _stage(1)["demand"])
    assert resolution["confirmed"] is False
    assert resolution["reason"] == "candidate_space_exhausted_for_this_demand"
    step = resolution["trace"][0]
    assert step["attribution"]["mode"] == "hardwired_operator_axis"
    assert step["attribution"]["component"] == runtime.COMPONENT_OPERATORS
    assert step["features"]["values"][2] is True
    # And still nothing at a strictly larger node bound: reach, not budget.
    deeper = runtime.resolve(chain["m0"], _stage(1)["demand"], 13)
    assert deeper["confirmed"] is False


def test_two_generations_target_different_components_and_both_resolve(chain: dict) -> None:
    first, second = chain["first"], chain["second"]
    assert first["confirmed"] is True
    assert first["selected_component"] == runtime.COMPONENT_SIGNALS
    assert first["surviving_rule_classes"] == 1
    assert second["confirmed"] is True
    assert second["selected_component"] == runtime.COMPONENT_CANDIDATES
    assert second["surviving_rule_classes"] == 1
    assert first["adopted_rule"]["rule_id"] != second["adopted_rule"]["rule_id"]
    assert second["adopted_rule"]["generation"] == 2

    stage_one = chain["stage_one_resolution"]
    assert stage_one["confirmed"] is True
    assert stage_one["final_signal_width"] == runtime.WORLD_SIGNAL_WIDTH
    assert stage_one["construction"]["executes_to_target"] is True

    stage_two = runtime.resolve(chain["m2"], _stage(2)["demand"])
    assert stage_two["confirmed"] is True
    assert stage_two["final_candidate_space"] == runtime.COMPLETE_SPACE
    assert stage_two["construction"]["executes_to_target"] is True
    # The generation-one lineage cannot resolve stage two.
    assert runtime.resolve(chain["m1_after"], _stage(2)["demand"])["confirmed"] is False


def test_reach_improve_is_a_strict_chain(chain: dict) -> None:
    sets = {
        label: set(runtime.reach_improve(chain[label], 2)["tables"])
        for label in ("m0", "m1", "m2")
    }
    assert sets["m0"] < sets["m1"], "generation one must strictly enlarge the improvement reach"
    assert sets["m1"] < sets["m2"], "generation two must strictly enlarge it again"


def test_generation_two_is_inexpressible_before_generation_one(chain: dict, domain: dict) -> None:
    """The monotonicity lemma, one level up: on the attribution cascade rather than the operators."""
    handed = runtime.acquire_rule(
        chain["m0"], [chain["episode2"]], domain, register_result=False
    )
    assert handed["confirmed"] is False
    assert handed["reason"] == "no_expressible_rule_reproduces_the_trial_record"
    assert handed["consistent_rule_count"] == 0
    # Row 3 lies below row 7 componentwise, so every monotone program true at 3 is true at 7.
    space = runtime.expression_image(chain["m0"]["operators"], runtime.FEATURE_COUNT)
    assert all(a <= b for a, b in zip(runtime.FEATURE_ROWS[3], runtime.FEATURE_ROWS[7]))
    assert not [table for table in space if table[3] and not table[7]]


def test_a_record_naming_two_components_or_nothing_is_refused(chain: dict, domain: dict) -> None:
    conflated = runtime.acquire_rule(
        chain["m0"], [chain["episode1"], chain["episode2"]], domain, register_result=False
    )
    assert conflated["confirmed"] is False
    assert conflated["reason"] == "uncovered_episodes_name_more_than_one_component"

    nothing_left = runtime.acquire_rule(
        chain["m1"], [chain["episode1"]], domain, register_result=False
    )
    assert nothing_left["confirmed"] is False
    assert nothing_left["reason"] == "no_uncovered_component_to_attribute"


def test_ablation_mutation_and_corruption(chain: dict) -> None:
    m2 = chain["m2"]
    ablated = runtime.create_state(
        m2["operators"],
        signal_width=m2["signal_width"],
        candidate_space=m2["candidate_space"],
        rules=m2["rules"][:-1],
    )
    assert runtime.encode_state(ablated) == runtime.encode_state(chain["m1_after"])
    assert runtime.resolve(ablated, _stage(2)["demand"])["confirmed"] is False

    rule = m2["rules"][-1]
    mutated = runtime.create_state(
        m2["operators"],
        signal_width=m2["signal_width"],
        candidate_space=m2["candidate_space"],
        rules=list(m2["rules"][:-1])
        + [
            runtime.attribution_rule(
                rule["body"],
                [not value for value in rule["truth_table"]],
                rule["selects_component_when_true"],
                rule["generation"],
            )
        ],
    )
    assert runtime.resolve(mutated, _stage(2)["demand"])["confirmed"] is False

    corrupt = json.loads(runtime.encode_state(m2).decode("ascii"))
    corrupt["rules"][-1]["rule_id"] = "rule-0000000000000000"
    with pytest.raises(ValueError, match="identity mismatch"):
        runtime.decode_state(corrupt)


def test_the_lineage_cannot_grant_itself_more_authority(chain: dict, domain: dict) -> None:
    m0 = chain["m0"]
    for field, value, expected in (
        ("component_registry", [*runtime.COMPONENTS, "evaluator"], "registry"),
        ("candidate_space", "unbounded", "candidate space"),
    ):
        tampered = json.loads(runtime.encode_state(m0).decode("ascii"))
        tampered[field] = value
        with pytest.raises(ValueError, match=expected):
            runtime.decode_state(tampered)
    beyond = runtime.acquire_rule(
        chain["m2"], [chain["episode1"], chain["episode2"]], domain, register_result=False
    )
    assert beyond["reason"] == "machinery_generation_ceiling_reached"
    at_ceiling = runtime.create_state(m0["operators"], signal_width=runtime.MAX_SIGNAL_WIDTH)
    assert runtime.extend_signal_interface(at_ceiling)["reason"] == "signal_interface_ceiling_reached"
    widened = runtime.create_state(m0["operators"], candidate_space=runtime.COMPLETE_SPACE)
    assert runtime.widen_candidate_space(widened)["reason"] == "candidate_space_ceiling_reached"


def test_the_fixtures_match_their_authoring_script() -> None:
    assert (EXPERIMENT / "DEMAND_STAGE1.json").read_bytes() == runtime.canonical_json(
        author.build_stage_one()
    ).encode("ascii")
    assert (EXPERIMENT / "DEMAND_STAGE2.json").read_bytes() == runtime.canonical_json(
        author.build_stage_two()
    ).encode("ascii")


def test_m109_binds_no_file_an_earlier_frozen_protocol_binds() -> None:
    from scripts import build_m106_protocol as m106_builder
    from scripts import build_m107_protocol as m107_builder
    from scripts import build_m108_protocol as m108_builder

    try:
        from scripts import build_m109_protocol as m109_builder
    except ImportError:  # pragma: no cover - the builder lands with the freeze apparatus
        pytest.skip("M109 protocol builder does not exist yet")
    earlier = (
        set(m106_builder.APPARATUS_FILES)
        | set(m107_builder.APPARATUS_FILES)
        | set(m108_builder.APPARATUS_FILES)
    )
    overlap = earlier & set(m109_builder.APPARATUS_FILES)
    assert not overlap, overlap


def test_input_preflight_binds_the_fixtures() -> None:
    report = qualification.verify_inputs()
    assert report["confirmed"] is True, [k for k, v in report["checks"].items() if not v]


def test_adversarial_boundary_audit_still_holds() -> None:
    report = audit_m109_boundaries.audit()
    checks = report["checks"]
    substantive = {key: value for key, value in checks.items() if key != _PHASE_CHECK}
    assert all(substantive.values()), [k for k, v in substantive.items() if not v]
    if _canonical_evidence_exists():
        assert checks[_PHASE_CHECK] is False
    else:
        assert checks[_PHASE_CHECK] is True


def test_the_checker_replay_import_resolves_as_a_direct_script() -> None:
    """The exact defect that lost M103 and M105."""
    source = (ROOT / "scripts" / "check_m109_result.py").read_text(encoding="utf-8")
    assert "from scripts import run_m109_qualification" in source
    assert "_ROOT = Path(__file__).resolve().parents[1]" in source
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import runpy,sys;sys.argv=['check_m109_result.py'];"
            "runpy.run_path(r'%s', run_name='not_main')"
            % (ROOT / "scripts" / "check_m109_result.py"),
        ],
        capture_output=True,
        text=True,
        cwd=ROOT / "scripts",
    )
    assert completed.returncode == 0, completed.stderr


def test_predicate_semantics_import_nothing() -> None:
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(checker.evaluate_conditions))
    assert not any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(tree))


def test_canonical_entrypoint_is_gated_by_the_final_freeze() -> None:
    content_refusals = (
        "final protocol is absent",
        "schema or digest mismatch",
        "is not owner-authorized",
        "decisive predicate declaration changed",
        "bound apparatus changed",
        "digest mode is undeclared",
    )
    if not qualification.PROTOCOL_PATH.exists():
        try:
            qualification.require_frozen()
        except qualification.QualificationRefused as error:
            assert "final protocol is absent" in str(error)
        else:  # pragma: no cover
            raise AssertionError("M109 unexpectedly has a final protocol before freeze")
        return
    try:
        armed = qualification.require_frozen()
    except qualification.QualificationRefused as error:
        assert not any(reason in str(error) for reason in content_refusals), str(error)
    else:
        assert armed["status"] == "frozen_protocol_owner_authorized"


def test_m107_substrate_is_imported_unchanged() -> None:
    """A fork at any level would end the generational chain."""
    assert runtime.expr is m107
    assert runtime.base.expr is m107
    assert runtime.expression_image is runtime.base.expression_image
