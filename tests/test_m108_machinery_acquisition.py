"""M108 machinery-acquisition tests.

The phase check is bound to the artefacts on disk from the start: M105's equivalent test asserted a
pre-result invariant unconditionally and turned both CI jobs red the moment its result was sealed.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from metamorphosis import m107_runtime as m107
from metamorphosis import m108_runtime as runtime
from scripts import audit_m108_boundaries
from scripts import author_m108_episodes as author
from scripts import build_m108_protocol as builder
from scripts import check_m108_result as checker
from scripts import run_m108_qualification as qualification

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "M108"
_PHASE_CHECK = "canonical_evidence_absent_before_attempt"


def _canonical_evidence_exists() -> bool:
    return (EXPERIMENT / "RESULT.json").exists() or (EXPERIMENT / "CHECK_REPORT.json").exists()


def _episodes() -> dict:
    return json.loads((EXPERIMENT / "EPISODES.json").read_text("ascii"))


def _target() -> tuple[bool, ...]:
    fixture = json.loads((EXPERIMENT / "DEMAND.json").read_text("ascii"))
    return runtime.demand_target(fixture["demand"])


def _m0() -> dict:
    return runtime.create_state(_episodes()["m0_operators"], signal_width=runtime.BASE_SIGNAL_WIDTH)


def test_m108_starts_from_the_operator_table_m107_actually_acquired() -> None:
    """The generational chain must be a computed fact, not a narrated one."""
    operators, _ = author.m107_acquired_operators()
    assert [item["name"] for item in operators] == [
        item["name"] for item in _episodes()["m0_operators"]
    ]
    assert any(item["name"].startswith("ACQUIRED_") for item in operators)
    # M0's operator table is already saturated at the base width: nothing on the operator axis is
    # left to gain there, which is what makes the later refusal about the interface and not search.
    assert len(runtime.expression_image(operators, runtime.BASE_SIGNAL_WIDTH)) == 16


def test_the_interpreter_is_m107_generalized_rather_than_a_second_interpreter() -> None:
    for operators in (m107.initial_operators(), _m0()["operators"]):
        certificate = runtime.interpreter_equivalence_certificate(operators)
        assert certificate["confirmed"] is True
        assert certificate["images_identical"] is True
        assert certificate["m107_executes_m108_witnesses"] is True


def test_one_feature_row_is_unreachable_while_attributing() -> None:
    """Attribution is consulted only on a failure, and one row admits no failure at all."""
    domain = runtime.attribution_domain()
    assert domain["rows"] == [0, 2, 3]
    assert domain["unreachable_rows"] == [1]
    assert domain["census_complete"] is True
    assert domain["unconstructible_pairs_examined"] > 1000


def test_a_monotone_lineage_cannot_express_its_own_corrected_attribution() -> None:
    monotone = runtime.create_state(
        m107.initial_operators(), signal_width=runtime.BASE_SIGNAL_WIDTH
    )
    report = runtime.acquire_attribution(
        monotone, _episodes()["episodes"], register_result=False
    )
    assert report["confirmed"] is False
    assert report["reason"] == "no_expressible_rule_reproduces_the_blame_record"
    assert report["consistent_rule_count"] == 0
    assert report["rule_space_size"] == 4
    # The exclusion is a lemma, not a budget: the monotone image is the same at every bound.
    for bound in (5, 9, 13):
        assert len(runtime.expression_image(m107.initial_operators(), runtime.FEATURE_COUNT, bound)) == 4


def test_an_uncovered_domain_row_leaves_the_attribution_underdetermined() -> None:
    episodes = _episodes()
    subset = set(episodes["underdetermined_subset"])
    partial = [item for item in episodes["episodes"] if item["episode_id"] in subset]
    report = runtime.acquire_attribution(_m0(), partial, register_result=False)
    assert report["confirmed"] is False
    assert report["reason"] == "attribution_underdetermined_by_episodes"
    assert report["surviving_attribution_classes"] >= 2
    assert report["attribution_domain_covered"] is False


def test_the_full_record_determines_exactly_one_attribution_class() -> None:
    report = runtime.acquire_attribution(_m0(), _episodes()["episodes"], register_result=True)
    assert report["confirmed"] is True
    assert report["surviving_attribution_classes"] == 1
    assert report["rule_space_exhausted"] is True
    assert report["attribution_domain_covered"] is True
    assert report["every_consistent_rule_is_non_monotone"] is True
    assert report["adopted_rule"]["rule_id"].startswith("attribution-")


def test_the_acquired_rule_changes_attribution_and_ablation_restores_it() -> None:
    m0 = _m0()
    target = _target()
    demand = runtime.capability_demand("B", target)
    m1 = runtime.acquire_attribution(m0, _episodes()["episodes"], register_result=True)["next_state"]

    hardwired = runtime.resolve(m0, demand)
    assert hardwired["confirmed"] is False
    assert hardwired["reason"] == "operator_candidate_space_exhausted"
    assert hardwired["trace"][0]["attribution"]["mode"] == "hardwired_operator_axis"

    corrected = runtime.resolve(m1, demand)
    assert corrected["confirmed"] is True
    assert corrected["trace"][0]["attribution"]["component"] == runtime.COMPONENT_SIGNALS
    assert corrected["final_signal_width"] == runtime.WORLD_SIGNAL_WIDTH
    assert corrected["construction"]["executes_to_target"] is True
    # Equal machinery-step budget: the difference is attribution, not allowance.
    assert hardwired["steps"] == corrected["steps"]

    ablated = runtime.create_state(m1["operators"], signal_width=m1["signal_width"], attribution=None)
    assert runtime.encode_state(ablated) == runtime.encode_state(m0)
    assert runtime.resolve(ablated, demand)["confirmed"] is False


def test_the_later_capability_needs_both_generations() -> None:
    target = _target()
    assert runtime.structural_exclusion_certificate(target, runtime.BASE_SIGNAL_WIDTH)["confirmed"]
    monotone = runtime.monotone_exclusion_certificate(m107.initial_operators(), target)
    assert monotone["confirmed"] is True
    assert monotone["excluded_by_monotonicity_lemma"] is True
    assert monotone["budget_independent"] is True
    both = runtime.create_state(_m0()["operators"], signal_width=runtime.WORLD_SIGNAL_WIDTH)
    assert runtime.construct(both, target)["constructible"] is True


def test_the_lineage_cannot_grant_itself_more_authority() -> None:
    m0 = _m0()
    at_ceiling = runtime.create_state(m0["operators"], signal_width=runtime.MAX_SIGNAL_WIDTH)
    assert runtime.extend_signal_interface(at_ceiling)["reason"] == "signal_interface_ceiling_reached"
    tampered = json.loads(runtime.encode_state(m0).decode("ascii"))
    tampered["component_registry"] = [*runtime.COMPONENTS, "evaluator"]
    try:
        runtime.decode_state(tampered)
    except ValueError as error:
        assert "registry" in str(error)
    else:  # pragma: no cover - a lineage must never widen its own registry
        raise AssertionError("M108 accepted a widened component registry")


def test_the_fixtures_match_their_authoring_script() -> None:
    assert (EXPERIMENT / "EPISODES.json").read_bytes() == runtime.canonical_json(
        author.build_episodes()
    ).encode("ascii")
    assert (EXPERIMENT / "DEMAND.json").read_bytes() == runtime.canonical_json(
        author.build_demand()
    ).encode("ascii")


def test_bound_members_are_digested_by_a_declared_mode() -> None:
    """M107 pinned bytes with attribute files it bound; that scheme cannot extend to M108."""
    bound = builder.bound_files()
    assert set(bound["member_digest_modes"]) == set(bound["files"])
    assert all(mode in {"raw", "lf_normalized"} for mode in bound["member_digest_modes"].values())
    assert bound["member_digest_modes"]["experiments/M108/EPISODES.json"] == "raw"
    assert bound["member_digest_modes"]["metamorphosis/m108_runtime.py"] == "lf_normalized"
    # A member bound LF-normalized must digest identically from CRLF and LF bytes.
    source = (ROOT / "metamorphosis" / "m108_runtime.py").read_bytes()
    crlf = source.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    import hashlib

    assert hashlib.sha256(crlf.replace(b"\r\n", b"\n")).hexdigest() == bound["member_digests"][
        "metamorphosis/m108_runtime.py"
    ]


def test_m108_binds_no_file_an_earlier_frozen_protocol_binds() -> None:
    """The defect that made M107's freeze temporarily unverifiable, as a standing assertion."""
    from scripts import build_m106_protocol as m106_builder
    from scripts import build_m107_protocol as m107_builder

    earlier = set(m106_builder.APPARATUS_FILES) | set(m107_builder.APPARATUS_FILES)
    overlap = earlier & set(builder.APPARATUS_FILES)
    assert not overlap, overlap


def test_input_preflight_binds_the_fixtures() -> None:
    report = qualification.verify_inputs()
    assert report["confirmed"] is True, [k for k, v in report["checks"].items() if not v]


def test_adversarial_boundary_audit_still_holds() -> None:
    report = audit_m108_boundaries.audit()
    checks = report["checks"]
    substantive = {key: value for key, value in checks.items() if key != _PHASE_CHECK}
    assert all(substantive.values()), [k for k, v in substantive.items() if not v]
    assert report["monotone_rule_space_size"] == 4
    assert report["extended_rule_space_size"] == 16
    if _canonical_evidence_exists():
        assert checks[_PHASE_CHECK] is False
    else:
        assert checks[_PHASE_CHECK] is True


def test_the_checker_replay_import_resolves_as_a_direct_script() -> None:
    """The exact defect that lost M103 and M105."""
    source = (ROOT / "scripts" / "check_m108_result.py").read_text(encoding="utf-8")
    assert "from scripts import run_m108_qualification" in source
    assert "_ROOT = Path(__file__).resolve().parents[1]" in source
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import runpy,sys;sys.argv=['check_m108_result.py'];"
            "runpy.run_path(r'%s', run_name='not_main')"
            % (ROOT / "scripts" / "check_m108_result.py"),
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
            raise AssertionError("M108 unexpectedly has a final protocol before freeze")
        return
    try:
        armed = qualification.require_frozen()
    except qualification.QualificationRefused as error:
        assert not any(reason in str(error) for reason in content_refusals), str(error)
    else:
        assert armed["status"] == "frozen_protocol_owner_authorized"
