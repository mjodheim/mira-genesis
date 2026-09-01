"""M119/H64: what the instrument must do, proved on synthetic fixtures before it is frozen.

Every test below is behavioural. None asserts on the text of a source file, and none ends in a
tautology: M118 shipped one test that ended `assert ... or True` and one that grepped a checker's
source, and both passed while proving nothing.

The named scenarios are the ones that would have caught the defects this design exists to avoid:
a comparator with a standing bias, a runner-written verdict the checker echoes, a guard that can
manufacture a positive, an underpowered bank reported as a refutation, an instrument failure sold
as science, and an entry point that sits outside a freeze reporting itself fully bound.
"""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

import pytest

from metamorphosis import m113_carrier_devkit as devkit
from metamorphosis import m113_evaluator as evaluator
from metamorphosis import m119_arms as arms
from metamorphosis import m119_bank as bank
from metamorphosis import m119_chronology as chronology
from metamorphosis import m119_decomposition as decomposition
from metamorphosis import m119_endpoint as endpoint
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import check_m119_result as checker  # noqa: E402


# ---------------------------------------------------------------------------------------------
# 1-3. The comparator
# ---------------------------------------------------------------------------------------------

def test_fresh_is_uniform_over_components_on_every_row() -> None:
    """M118's comparator short-changed one component in 400 of 400 seeds. This one cannot."""
    counts = {row: {component: 0 for component in arms.COMPONENTS}
              for row in range(arms.ROW_COUNT)}
    samples = 4000
    for index in range(samples):
        assignment = arms.fresh_assignment("carrier-%d" % index, "pair-%d" % index)
        for row, component in enumerate(assignment):
            counts[row][component] += 1
    for row, per_component in counts.items():
        for component, seen in per_component.items():
            share = seen / samples
            assert abs(share - 1 / 3) < 0.03, (
                "row %d gives %s a share of %.4f, not one third" % (row, component, share))


def test_fresh_varies_by_demand_and_is_never_a_constant_assignment() -> None:
    """A comparator that names the same component everywhere is a degenerate baseline, not T0."""
    assignments = {tuple(arms.fresh_assignment("c-%d" % i, "p-%d" % i)) for i in range(200)}
    assert len(assignments) > 100, "the draw barely varies across demands"
    constant = [a for a in assignments if len(set(a)) == 1]
    assert len(constant) < len(assignments) / 4, "too many assignments name a single component"


def test_fresh_never_reproduces_an_acquired_rule_body() -> None:
    """FRESH is a fresh cascade, not a copy of the descendant's with the labels changed."""
    rules, fallthrough = arms.fresh_rules("carrier-x", "pair-x")
    assert fallthrough in arms.COMPONENTS
    assert len(rules) == 2
    for rule in rules:
        assert rule["body"]["node"] == "UNIFORM_PER_DEMAND"
        assert "committed seed" in rule["body"]["derivation"]


# ---------------------------------------------------------------------------------------------
# 4. The arm set
# ---------------------------------------------------------------------------------------------

def test_the_four_arms_are_exactly_the_two_by_two() -> None:
    acquired = [{"rule_id": "acquired-1"}]
    policy = {"truth_table": [True] * arms.ROW_COUNT}
    built = arms.build_arms(acquired, policy, "carrier-x", "pair-x")
    assert set(arms.ARM_NAMES) == {"FRESH", "CASCADE_ONLY", "POLICY_ONLY", "FULL"}
    assert set(built) == set(arms.ALL_ARM_NAMES)
    assert built["FRESH"]["policy"] is None and built["FRESH"]["rules"]
    assert built["CASCADE_ONLY"]["policy"] is None
    assert built["CASCADE_ONLY"]["rules"] == acquired
    assert built["POLICY_ONLY"]["rules"] == [] and built["POLICY_ONLY"]["policy"] == policy
    assert built["FULL"]["rules"] == acquired and built["FULL"]["policy"] == policy
    assert arms.DESCENDANT_ARM == "FULL" and arms.COMPARATOR_ARM == "FRESH"
    # The diagnostic arm holds exactly what FULL holds; only the budget the runner gives it differs.
    assert built["FULL_BUDGET_PLUS"] == built["FULL"]
    assert arms.DESCENDANT_ARM not in arms.DIAGNOSTIC_ARM_NAMES
    assert arms.COMPARATOR_ARM not in arms.DIAGNOSTIC_ARM_NAMES


# ---------------------------------------------------------------------------------------------
# 5-6. The primary endpoint
# ---------------------------------------------------------------------------------------------

def _score(**flags: bool) -> dict[str, bool]:
    keys = ("correct_construction", "unmet_construction", "false_refusal", "calibrated_refusal",
            "invented_adapter", "undetermined")
    base = {key: False for key in keys}
    base.update(flags)
    return base


def test_undetermined_is_a_primary_failure_on_both_demand_classes() -> None:
    undetermined = _score(undetermined=True)
    assert endpoint.primary_success(evaluator.CLASS_REACHABLE, undetermined) is False
    assert endpoint.primary_success(evaluator.CLASS_UNREACHABLE, undetermined) is False


def test_success_requires_the_right_outcome_for_the_demand_class() -> None:
    """There is no disjunction: constructing on an unreachable demand is not a way to win."""
    assert endpoint.primary_success(
        evaluator.CLASS_REACHABLE, _score(correct_construction=True)) is True
    assert endpoint.primary_success(
        evaluator.CLASS_UNREACHABLE, _score(calibrated_refusal=True)) is True
    assert endpoint.primary_success(
        evaluator.CLASS_UNREACHABLE, _score(correct_construction=True)) is False
    assert endpoint.primary_success(
        evaluator.CLASS_REACHABLE, _score(calibrated_refusal=True)) is False
    with pytest.raises(endpoint.EndpointError):
        endpoint.primary_success("structurally_unreachable", _score())


def test_the_endpoint_names_the_evaluators_own_demand_classes() -> None:
    """A class the evaluator never emits would raise on every demand of that class."""
    assert set(endpoint.PRIMARY_SUCCESS_KEY) == set(evaluator.DEMAND_CLASSES)


# ---------------------------------------------------------------------------------------------
# 7-8. The statistical rule
# ---------------------------------------------------------------------------------------------

def test_the_exact_test_matches_the_binomial_tail_by_enumeration() -> None:
    for b in range(0, 9):
        for c in range(0, 9):
            n = b + c
            expected = 1.0 if n == 0 else sum(
                math.comb(n, k) for k in range(b, n + 1)) / (2 ** n)
            assert endpoint.exact_mcnemar_one_sided(b, c) == pytest.approx(expected)


def test_five_discordant_pairs_are_needed_before_significance_is_attainable() -> None:
    assert endpoint.minimum_discordant_for_significance() == 5
    assert endpoint.exact_mcnemar_one_sided(4, 0) > endpoint.ALPHA
    assert endpoint.exact_mcnemar_one_sided(5, 0) <= endpoint.ALPHA


def test_a_plan_whose_criterion_could_never_be_met_is_refused() -> None:
    """Discovering an unsatisfiable criterion after the reveal is not an option."""
    endpoint.assert_feasible(3, 2)
    with pytest.raises(endpoint.EndpointError):
        endpoint.assert_feasible(2, 1)


# ---------------------------------------------------------------------------------------------
# 9-12. The verdicts
# ---------------------------------------------------------------------------------------------

_CLEAN = {"invented_adapter": 0, "false_refusal": 0,
          "attribution_agreement_rate": 1.0, "attribution_examined": 10}


def _series(only_descendant: int, only_fresh: int, both: int = 0, neither: int = 0):
    d = [True] * only_descendant + [False] * only_fresh + [True] * both + [False] * neither
    f = [False] * only_descendant + [True] * only_fresh + [True] * both + [False] * neither
    return d, f


def test_a_guard_vetoes_a_positive_and_cannot_create_one() -> None:
    d, f = _series(only_descendant=10, only_fresh=0, both=5, neither=5)
    clean = endpoint.decide(d, f, _CLEAN, _CLEAN)
    assert clean["primary_holds"] is True and clean["verdict"] == endpoint.POSITIVE

    harmed = dict(_CLEAN, invented_adapter=3)
    vetoed = endpoint.decide(d, f, harmed, _CLEAN)
    assert vetoed["primary_holds"] is True
    assert vetoed["no_harm"]["failed"] == ["invented_adapter"]
    assert vetoed["verdict"] == endpoint.NEGATIVE

    # A guard cannot rescue a failed primary: perfect guards, no effect, still not positive.
    flat_d, flat_f = _series(only_descendant=0, only_fresh=0, both=20, neither=0)
    flat = endpoint.decide(flat_d, flat_f, _CLEAN, _CLEAN)
    assert flat["verdict"] != endpoint.POSITIVE


def test_an_underpowered_bank_is_inconclusive_and_not_a_refutation() -> None:
    d, f = _series(only_descendant=3, only_fresh=0, both=1, neither=1)
    verdict = endpoint.decide(d, f, _CLEAN, _CLEAN)
    assert verdict["underpowered"] is True
    assert verdict["smallest_attainable_p_value"] > endpoint.ALPHA
    assert verdict["verdict"] == endpoint.INCONCLUSIVE
    assert decomposition.decompose({}, verdict=verdict["verdict"])[
        "strongest_supported_statement"].endswith("not evidence against the hypothesis.")


def test_an_adequately_powered_failure_is_negative_not_inconclusive() -> None:
    d, f = _series(only_descendant=3, only_fresh=3, both=10, neither=10)
    verdict = endpoint.decide(d, f, _CLEAN, _CLEAN)
    assert verdict["underpowered"] is False
    assert verdict["primary_holds"] is False
    assert verdict["verdict"] == endpoint.NEGATIVE


def test_an_instrument_failure_is_never_a_scientific_result() -> None:
    d, f = _series(only_descendant=10, only_fresh=0, both=5, neither=5)
    aborted = endpoint.decide(d, f, _CLEAN, _CLEAN, instrument_valid=False,
                              instrument_failures=["fewer qualifying carriers than the plan"])
    # The primary criterion passes and every guard holds, and it still is not a result.
    assert aborted["primary_holds"] is True and aborted["no_harm"]["all_hold"] is True
    assert aborted["verdict"] == endpoint.INSTRUMENT_ABORTED
    assert decomposition.decompose({}, verdict=aborted["verdict"])[
        "strongest_supported_statement"].startswith("H64 was not validly tested")


def test_the_attribution_guard_does_not_veto_a_run_that_examined_nothing() -> None:
    """M118's guard vetoed a descendant that constructed immediately, so its rate never formed."""
    d, f = _series(only_descendant=10, only_fresh=0, both=5, neither=5)
    unformed = {"invented_adapter": 0, "false_refusal": 0,
                "attribution_agreement_rate": None, "attribution_examined": 0}
    verdict = endpoint.decide(d, f, unformed, unformed)
    guard = verdict["no_harm"]["guards"]["attribution_agreement_rate"]
    assert guard["evaluated"] is False and guard["holds"] is True
    assert verdict["verdict"] == endpoint.POSITIVE


def test_the_effect_size_floor_is_binding_on_its_own() -> None:
    """Significant but tiny is not positive: both criteria are required."""
    d, f = _series(only_descendant=6, only_fresh=0, both=0, neither=94)
    verdict = endpoint.decide(d, f, _CLEAN, _CLEAN)
    assert verdict["statistical_criterion_holds"] is True
    assert verdict["risk_difference"] < endpoint.MINIMUM_RISK_DIFFERENCE
    assert verdict["effect_size_criterion_holds"] is False
    assert verdict["verdict"] == endpoint.NEGATIVE


# ---------------------------------------------------------------------------------------------
# 13-15. The independent checker
# ---------------------------------------------------------------------------------------------

def _measurements(entries, *, plan, **overrides):
    record = {
        "schema": "m119-h64-measurements-v1", "milestone": "M119", "hypothesis": "H64",
        "arms_version": arms.ARMS_VERSION, "endpoint_version": endpoint.ENDPOINT_VERSION,
        "arm_names": list(arms.ARM_NAMES),
        "diagnostic_arm_names": list(arms.DIAGNOSTIC_ARM_NAMES),
        "budget_multiplier": dict(arms.BUDGET_MULTIPLIER),
        "descendant_arm": arms.DESCENDANT_ARM, "comparator_arm": arms.COMPARATOR_ARM,
        "fresh_seed": arms.FRESH_SEED, "fresh_seed_source": arms.FRESH_SEED_SOURCE,
        "action_space": arms.action_space_statement(),
        "provenance_checks": {"restored": True}, "corruption": {"failed_closed": True},
        "analysis_plan_commitment_sha256": plan["plan_commitment_sha256"],
        "session_budget": plan["session_budget"],
        "carriers_seen": 40, "qualifying_carriers": 10,
        "distinct_qualifying_structures": 10,
        "demand_classes": list(evaluator.DEMAND_CLASSES),
        "entries": entries,
        "measurements_sha256": "",
    }
    record.update(overrides)
    record["measurements_sha256"] = sha256_hex(canonical_bytes(
        {k: v for k, v in record.items() if k != "measurements_sha256"}))
    return record


def _entry(index: int, *, full_succeeds: bool, fresh_succeeds: bool,
           runner_claims: bool | None = None, budget_plus_succeeds: bool | None = None):
    """One paired demand. `runner_claims` lets a dishonest runner disagree with its own score."""
    def side(succeeds: bool, budget: int = 4000):
        return {
            "budget": budget,
            evaluator.CLASS_REACHABLE: {
                "verdict": "constructed", "invocations_used": 1, "probes_spent": 0,
                "budget": budget, "budget_exhausted": False, "within_budget": True,
                "primary_success": succeeds if runner_claims is None else runner_claims,
                "score": _score(correct_construction=succeeds,
                                unmet_construction=not succeeds),
                "attributed_component": arms.COMPONENTS[0],
                "attribution_correct": succeeds,
            },
            evaluator.CLASS_UNREACHABLE: {
                "verdict": "refused", "invocations_used": 1, "probes_spent": 0,
                "budget": budget, "budget_exhausted": False, "within_budget": True,
                "primary_success": succeeds if runner_claims is None else runner_claims,
                "score": _score(calibrated_refusal=succeeds, invented_adapter=not succeeds),
            },
        }
    plus = full_succeeds if budget_plus_succeeds is None else budget_plus_succeeds
    return {
        "carrier_ref": "opaque-%016x" % index, "carrier_digest": "d" * 64,
        "pair_digest": "p" * 64, "ground_truth_component": arms.COMPONENTS[0],
        "ground_truth_row": 0,
        "arms": {"FULL": side(full_succeeds), "FRESH": side(fresh_succeeds),
                 "CASCADE_ONLY": side(full_succeeds), "POLICY_ONLY": side(fresh_succeeds),
                 "FULL_BUDGET_PLUS": side(plus, budget=16000)},
    }


@pytest.fixture(scope="module")
def plan() -> dict:
    return bank.build_analysis_plan(ROOT)


def test_the_checker_recomputes_outcomes_and_ignores_what_the_runner_claimed(plan) -> None:
    """A runner that mislabels an outcome must not reproduce perfectly."""
    honest = [_entry(i, full_succeeds=True, fresh_succeeds=False) for i in range(6)]
    lying = [_entry(i, full_succeeds=True, fresh_succeeds=False, runner_claims=False)
             for i in range(6)]
    honest_report = checker.check(_measurements(honest, plan=plan), plan)
    lying_report = checker.check(_measurements(lying, plan=plan), plan)
    # The runner claimed every arm failed. The score says otherwise, and the score is what counts.
    assert lying_report["arm_success_rates"] == honest_report["arm_success_rates"]
    assert lying_report["primary"]["contingency"] == honest_report["primary"]["contingency"]
    assert honest_report["arm_success_rates"]["FULL"] == 1.0
    assert honest_report["arm_success_rates"]["FRESH"] == 0.0
    assert honest_report["verdict"] == endpoint.POSITIVE


def test_the_checker_refuses_a_substituted_comparator_seed(plan) -> None:
    entries = [_entry(i, full_succeeds=True, fresh_succeeds=False) for i in range(6)]
    record = _measurements(entries, plan=plan, fresh_seed="0" * 64)
    with pytest.raises(checker.CheckError, match="comparator seed"):
        checker.check(record, plan)


def test_the_checker_refuses_a_budget_the_plan_does_not_specify(plan) -> None:
    entries = [_entry(i, full_succeeds=True, fresh_succeeds=False) for i in range(6)]
    record = _measurements(entries, plan=plan, session_budget=plan["session_budget"] + 7)
    with pytest.raises(checker.CheckError, match="budget"):
        checker.check(record, plan)


def test_the_checker_refuses_a_record_whose_digest_does_not_reproduce(plan) -> None:
    entries = [_entry(i, full_succeeds=True, fresh_succeeds=False) for i in range(6)]
    record = _measurements(entries, plan=plan)
    record["qualifying_carriers"] = 99
    with pytest.raises(checker.CheckError, match="digest"):
        checker.check(record, plan)


def test_a_bank_below_the_plans_minimum_is_untested_not_refuted(plan) -> None:
    entries = [_entry(i, full_succeeds=True, fresh_succeeds=False) for i in range(6)]
    record = _measurements(entries, plan=plan, qualifying_carriers=1,
                           distinct_qualifying_structures=1)
    report = checker.check(record, plan)
    assert report["verdict"] == endpoint.INSTRUMENT_ABORTED
    assert report["hypothesis_status"] == "untested"


def test_the_checker_refuses_a_failed_producer_provenance_check(plan) -> None:
    entries = [_entry(i, full_succeeds=True, fresh_succeeds=False) for i in range(6)]
    record = _measurements(entries, plan=plan, provenance_checks={"restored": False})
    with pytest.raises(checker.CheckError, match="provenance"):
        checker.check(record, plan)


def test_a_flat_result_is_reported_as_not_supported(plan) -> None:
    entries = [_entry(i, full_succeeds=True, fresh_succeeds=True) for i in range(10)]
    report = checker.check(_measurements(entries, plan=plan), plan)
    assert report["verdict"] in (endpoint.NEGATIVE, endpoint.INCONCLUSIVE)
    assert report["hypothesis_status"] != "supported"


# ---------------------------------------------------------------------------------------------
# 16-18. The freeze and the chronology
# ---------------------------------------------------------------------------------------------

def test_the_freeze_scan_finds_an_entry_point_no_root_declares(tmp_path: Path) -> None:
    """A closure walks downward, so a module nothing imports is invisible to it."""
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "run_m119_sneaky.py").write_text("# nothing imports this\n")
    found = chronology.undeclared_measurement_entry_points(tmp_path)
    assert found == ["scripts/run_m119_sneaky.py"]


def test_every_declared_entry_point_is_answered_by_a_root_or_a_stated_exemption() -> None:
    assert chronology.undeclared_measurement_entry_points(ROOT) == []


def test_the_live_interpretation_closure_is_fully_bound() -> None:
    stock = chronology.inventory(ROOT)
    assert stock["unbound_interpretation_modules"] == []
    assert stock["closure_is_fully_bound"] is True


def test_the_chronology_refuses_a_predecessor_that_differs_from_its_committed_bytes(
        tmp_path: Path) -> None:
    """A file edited after it was committed is not the file the freeze was taken against."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@example.invalid"],
                   check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    target = tmp_path / "artifact.json"
    target.write_text('{"a": 1}\n')
    subprocess.run(["git", "-C", str(tmp_path), "add", "artifact.json"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "x"], check=True)

    assert chronology.assert_committed_at_head(Path("artifact.json"), tmp_path)
    target.write_text('{"a": 2}\n')
    with pytest.raises(chronology.ChronologyError, match="differs from its committed bytes"):
        chronology.assert_committed_at_head(Path("artifact.json"), tmp_path)
    target.unlink()
    with pytest.raises(chronology.ChronologyError, match="absent"):
        chronology.assert_committed_at_head(Path("artifact.json"), tmp_path)


def test_an_uncommitted_predecessor_is_refused(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "artifact.json").write_text("{}\n")
    with pytest.raises(chronology.ChronologyError, match="not committed at HEAD"):
        chronology.assert_committed_at_head(Path("artifact.json"), tmp_path)


def test_a_freeze_is_refused_once_a_scientific_artifact_exists(tmp_path: Path) -> None:
    (tmp_path / chronology.DIRECTORY).mkdir(parents=True)
    (tmp_path / chronology.DELIVERY_LEDGER).write_text("{}\n")
    with pytest.raises(chronology.ChronologyError, match="already exists"):
        chronology.assert_no_scientific_observation_yet(tmp_path)


def _synthetic_commitments(tmp_path: Path, plan: dict) -> dict:
    """A minimal committed-artifact set the freeze can be taken against."""
    (tmp_path / chronology.DIRECTORY).mkdir(parents=True, exist_ok=True)
    spec = bank.build_generator_spec(plan, ROOT)
    (tmp_path / chronology.ANALYSIS_PLAN).write_bytes(canonical_bytes(plan) + b"\n")
    (tmp_path / chronology.GENERATOR_SPEC).write_bytes(canonical_bytes(spec) + b"\n")
    (tmp_path / chronology.QUALIFYING_INPUT).write_text(bank.qualifying_input(ROOT))
    (tmp_path / chronology.BANK_NONCE_COMMITMENT).write_bytes(canonical_bytes({
        "bank_nonce": "a" * 64, "bank_nonce_sha256": sha256_hex(b"a" * 64),
        "envelope_version": "x"}) + b"\n")
    return spec


def test_the_freeze_binds_the_plan_the_spec_and_the_nonce_not_only_the_source(
        tmp_path: Path, plan) -> None:
    """Source digests alone would let the request body be rewritten under an intact freeze."""
    spec = _synthetic_commitments(tmp_path, plan)
    bound = chronology._bound_commitments(tmp_path)
    assert bound["analysis_plan_commitment_sha256"] == plan["plan_commitment_sha256"]
    assert bound["spec_commitment_sha256"] == spec["spec_commitment_sha256"]
    assert bound["canonical_request_body_sha256"] == spec["canonical_request_body_sha256"]
    assert bound["bank_nonce_sha256"] == sha256_hex(b"a" * 64)
    assert bound["session_budget"] == plan["session_budget"]
    assert bound["fresh_seed"] == arms.FRESH_SEED

    # Rewriting the request body under an otherwise intact freeze must be caught.
    rewritten = json.loads(json.dumps(spec))
    rewritten["canonical_request_body_sha256"] = "0" * 64
    (tmp_path / chronology.GENERATOR_SPEC).write_bytes(canonical_bytes(rewritten) + b"\n")
    moved = chronology._bound_commitments(tmp_path)
    assert moved["canonical_request_body_sha256"] != bound["canonical_request_body_sha256"]


def test_the_freeze_is_refused_while_a_commitment_is_missing(tmp_path: Path) -> None:
    (tmp_path / chronology.DIRECTORY).mkdir(parents=True, exist_ok=True)
    with pytest.raises(chronology.ChronologyError, match="absent"):
        chronology._bound_commitments(tmp_path)


# ---------------------------------------------------------------------------------------------
# 19-21. The derivation
# ---------------------------------------------------------------------------------------------

def test_the_derived_plan_and_spec_validate_and_are_stable(plan) -> None:
    bank.validate_analysis_plan(plan, ROOT)
    again = bank.build_analysis_plan(ROOT)
    assert canonical_bytes(again) == canonical_bytes(plan)
    spec = bank.build_generator_spec(plan, ROOT)
    bank.validate_generator_spec(spec, plan, ROOT)
    assert canonical_bytes(bank.build_generator_spec(plan, ROOT)) == canonical_bytes(spec)


def test_a_tampered_plan_is_refused_by_its_own_validator(plan) -> None:
    tampered = dict(plan)
    tampered["minimum_qualifying_carriers"] = 1
    with pytest.raises(bank.BankError):
        bank.validate_analysis_plan(tampered, ROOT)


def test_the_qualifying_input_carries_no_project_vocabulary(plan) -> None:
    spec = bank.build_generator_spec(plan, ROOT)
    contract = spec["blindness_contract"]
    assert contract["contamination_hits_in_the_prompt"] == []
    assert contract["the_model_receives_only_the_qualifying_input_and_the_schema"] is True
    assert contract["no_system_message_is_sent"] is True
    body = spec["canonical_request_body"]
    assert "tools" not in body and len(body["messages"]) == 1
    assert "exactly %d entries" % bank.REQUESTED_CARRIER_COUNT in body["messages"][0]["content"]


def test_the_request_body_cannot_name_another_route(plan) -> None:
    spec = bank.build_generator_spec(plan, ROOT)
    substituted = json.loads(json.dumps(spec))
    substituted["canonical_request_body"]["provider"]["only"] = ["SomeOtherProvider"]
    substituted["canonical_request_body_sha256"] = sha256_hex(
        canonical_bytes(substituted["canonical_request_body"]))
    substituted["spec_commitment_sha256"] = sha256_hex(canonical_bytes(
        {k: v for k, v in substituted.items() if k != "spec_commitment_sha256"}))
    with pytest.raises(Exception, match="single provider"):
        bank.validate_generator_spec(substituted, plan, ROOT)


def test_the_bank_sizing_estimate_reproduces() -> None:
    """The plan's sizing numbers are measured, so they must be re-measurable."""
    estimate = bank.BANK_SIZING["yield_estimate"]
    qualifying = 0
    pairs = 0
    for index in range(estimate["sample"]):
        carrier = devkit.development_carrier("%s%d" % (estimate["seed_prefix"], index))
        if not evaluator.qualification_report(carrier)["qualifies"]:
            continue
        qualifying += 1
        pairs += len(evaluator.derive_demand_pairs(carrier, "opaque-%016x" % index, 1))
    rate = qualifying / estimate["sample"]
    mean_pairs = pairs / qualifying
    assert rate == pytest.approx(estimate["measured_qualification_rate"])
    assert mean_pairs == pytest.approx(estimate["mean_demand_pairs_per_qualifying_carrier"])
    expected = bank.REQUESTED_CARRIER_COUNT * rate * mean_pairs * estimate["demands_per_pair"]
    assert round(expected) == estimate["expected_paired_demands"]


def test_the_plan_proves_its_criterion_is_attainable_on_the_smallest_admissible_bank(plan) -> None:
    report = plan["feasibility_on_the_minimum_bank"]
    assert report["criterion_can_pass_on_the_minimum_bank"] is True
    assert report["criterion_can_fail"] is True
    assert report["minimum_paired_demands"] >= report["discordant_pairs_needed_for_significance"]


# ---------------------------------------------------------------------------------------------
# 22-23. The fenced diagnostic arm
# ---------------------------------------------------------------------------------------------

def test_the_diagnostic_arm_cannot_change_the_verdict(plan) -> None:
    """It attributes a negative. It must not be able to create, rescue or destroy one."""
    entries = [_entry(i, full_succeeds=False, fresh_succeeds=True) for i in range(6)]
    losing = checker.check(_measurements(entries, plan=plan), plan)

    rescued = [_entry(i, full_succeeds=False, fresh_succeeds=True, budget_plus_succeeds=True)
               for i in range(6)]
    with_a_winning_diagnostic = checker.check(_measurements(rescued, plan=plan), plan)

    assert losing["verdict"] == with_a_winning_diagnostic["verdict"] == endpoint.NEGATIVE
    assert (losing["primary"]["contingency"]
            == with_a_winning_diagnostic["primary"]["contingency"])
    assert (losing["decomposition"]["strongest_supported_statement"]
            == with_a_winning_diagnostic["decomposition"]["strongest_supported_statement"])
    # The one thing it does change is the attribution, which is reported beside the verdict.
    assert (with_a_winning_diagnostic["budget_attribution"]["improvement_from_budget_alone"]
            > losing["budget_attribution"]["improvement_from_budget_alone"])
    assert "budget" in with_a_winning_diagnostic["budget_attribution"]["reading"]


def test_the_decomposition_never_sees_the_diagnostic_arm(plan) -> None:
    entries = [_entry(i, full_succeeds=True, fresh_succeeds=False) for i in range(6)]
    report = checker.check(_measurements(entries, plan=plan), plan)
    assert set(report["decomposition"]["rates"]) == set(arms.ARM_NAMES)
    assert arms.FULL_BUDGET_PLUS in report["arm_success_rates"]


def test_the_checker_refuses_a_substituted_diagnostic_arm_set(plan) -> None:
    entries = [_entry(i, full_succeeds=True, fresh_succeeds=False) for i in range(6)]
    record = _measurements(entries, plan=plan, diagnostic_arm_names=[])
    with pytest.raises(checker.CheckError, match="diagnostic arm set"):
        checker.check(record, plan)


def test_the_session_budget_is_the_one_inherited_from_m113(plan) -> None:
    """A budget rewritten for this milestone could be rewritten until it suited."""
    inherited = json.loads(
        (ROOT / bank.SESSION_BUDGET_INHERITED_FROM).read_text(encoding="utf-8"))
    assert plan["session_budget"] == inherited["session_budget"] == 4000
