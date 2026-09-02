"""The M120 instrument gates: adequacy, plan re-derivation, chronology, and the checker's surface.

Each test here names the M119 finding it exists for. A gate with no named failure behind it is
complexity the budget refuses; a named failure with no gate is what M119 was.
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

import pytest

from metamorphosis import carrier_host as host
from metamorphosis import m116_chronology as m116
from metamorphosis import m119_endpoint as endpoint
from metamorphosis import m120_adequacy as adequacy
from metamorphosis import m120_admission as admission
from metamorphosis import m120_bank as bank
from metamorphosis import m120_carrier_contract as contract
from metamorphosis import m120_chronology as chronology
from metamorphosis import m120_devkit as devkit
from metamorphosis import m120_stress_schema as stress
from metamorphosis import m116_schema as schema_tools
from metamorphosis.blind_bank_protocol import canonical_bytes, opaque_domain_id, sha256_hex

ROOT = Path(__file__).resolve().parents[1]
NONCE = "a" * 64


@pytest.fixture(scope="module")
def plan():
    return bank.build_analysis_plan(ROOT)


def _bank(count, *, mode=devkit.MODE_UNIFORM, seed="m120-test-"):
    machines = list(devkit.development_candidates(seed, count, mode=mode))
    return admission.envelope_payload({"machines": machines}, NONCE)["carriers"]


# ---------------------------------------------------------------------------------------------
# R2 -- the pre-seal adequacy gate
# ---------------------------------------------------------------------------------------------

def test_an_adequate_bank_clears_the_gate(plan):
    gate = adequacy.evaluate(_bank(48), plan)
    adequacy.validate_record(gate)
    assert gate["adequate"] is True and gate["shortfalls"] == []
    assert gate["carriers_refused_by_the_frozen_host"] == 0
    assert gate["qualifying_carriers"] >= plan["minimum_qualifying_carriers"]


def test_an_admissible_but_inadequate_bank_is_refused_before_the_seal(plan):
    """M119's exact failure: the payload was admissible and the plan could not be run on it."""
    gate = adequacy.evaluate(_bank(1, mode=devkit.MODE_CORNER, seed="m120-tiny-"), plan)
    adequacy.validate_record(gate)
    assert gate["adequate"] is False
    assert adequacy.SHORTFALL_QUALIFYING in gate["shortfalls"]
    assert gate["carriers_refused_by_the_frozen_host"] == 0, (
        "the bank must be inadequate for scientific reasons, not because the host refused it")


def test_an_empty_bank_names_every_shortfall(plan):
    gate = adequacy.evaluate([], plan)
    assert gate["adequate"] is False
    assert set(gate["shortfalls"]) == set(adequacy.SHORTFALLS)


def test_the_gate_output_allowlist_is_enforced_not_described(plan):
    """The information boundary is only worth what refuses to publish past it."""
    gate = adequacy.evaluate(_bank(6), plan)
    with pytest.raises(adequacy.AdequacyError):
        adequacy.validate_record(dict(gate, leaked_carrier={"cells": [{"name": "secret"}]}))
    with pytest.raises(adequacy.AdequacyError):
        adequacy.validate_record({k: v for k, v in gate.items() if k != "qualifying_carriers"})
    with pytest.raises(adequacy.AdequacyError):
        adequacy.validate_record(dict(gate, shortfalls=["a reason nobody froze"]))
    with pytest.raises(adequacy.AdequacyError):
        adequacy.validate_record(dict(gate, adequate=not gate["adequate"]))


def test_the_gate_record_carries_no_carrier_value(plan):
    """No name, token, separator or cell value from any carrier may appear in the record."""
    carriers = _bank(24)
    gate = adequacy.evaluate(carriers, plan)
    text = canonical_bytes(gate).decode("ascii")
    for carrier in carriers:
        validated = host.validate_carrier(carrier)
        for cell in validated["cells"]:
            assert cell["name"] not in text
        for action in validated["actions"]:
            assert action["name"] not in text
        assert validated["carrier_digest"] not in text
        assert carrier["carrier_ref"] not in text


def test_the_gate_names_no_carrier_so_there_is_no_selection_channel(plan):
    """A caller that could learn *which* carriers qualified could select on them."""
    gate = adequacy.evaluate(_bank(24), plan)
    assert set(gate["blocking_clause_counts"]) <= {
        "closed_by_fixed_point", "enough_reachable_observations", "demand_needs_a_sequence",
        "an_unreachable_observation_exists", "the_carrier_imposes_a_protocol",
        "a_determined_attribution_pair_exists"}
    assert all(isinstance(count, int) for count in gate["blocking_clause_counts"].values())
    assert gate["no_carrier_was_selected_filtered_or_reordered"] is True


def test_the_gate_is_deterministic_and_order_independent_in_its_counts(plan):
    carriers = _bank(20)
    first = adequacy.evaluate(carriers, plan)
    second = adequacy.evaluate(carriers, plan)
    assert canonical_bytes(first) == canonical_bytes(second)


def test_the_preseal_and_post_reveal_gates_bind(plan):
    carriers = _bank(20)
    matched, differences = adequacy.binding_matches(
        adequacy.evaluate(carriers, plan), adequacy.evaluate(carriers, plan))
    assert matched and differences == []
    moved = adequacy.evaluate(carriers, plan)
    moved["qualifying_carriers"] += 1
    matched, differences = adequacy.binding_matches(adequacy.evaluate(carriers, plan), moved)
    assert not matched and "qualifying_carriers" in differences


def test_the_gate_refuses_a_plan_that_carries_no_usable_minimum():
    with pytest.raises(adequacy.AdequacyError):
        adequacy.evaluate([], {"minimum_qualifying_carriers": 0})


def test_the_minimum_paired_demands_comes_from_the_inherited_endpoint(plan):
    gate = adequacy.evaluate(_bank(4), plan)
    assert (gate["minimum_paired_demands_for_attainable_significance"]
            == endpoint.required_paired_demands())


# ---------------------------------------------------------------------------------------------
# R3 -- the analysis plan is re-derived, not trusted
# ---------------------------------------------------------------------------------------------

def test_the_derived_plan_validates_against_itself(plan):
    bank.validate_analysis_plan(plan, ROOT)


def test_a_plan_with_zeroed_minimums_keeping_the_frozen_digest_is_refused(plan):
    """M119's first disclosed checker defect, as a fixture."""
    forged = dict(plan)
    forged["minimum_qualifying_carriers"] = 0
    forged["minimum_distinct_qualifying_structures"] = 0
    with pytest.raises(bank.BankError, match="does not match its contents"):
        bank.validate_analysis_plan(forged, ROOT)


def test_a_plan_with_a_recomputed_digest_over_rewritten_thresholds_is_refused(plan):
    """Recomputing the digest gets past the first check and not past the derivation."""
    forged = dict(plan)
    forged["alpha"] = 0.5
    forged["minimum_qualifying_carriers"] = 0
    forged["plan_commitment_sha256"] = sha256_hex(canonical_bytes(
        {k: v for k, v in forged.items() if k != "plan_commitment_sha256"}))
    with pytest.raises(bank.BankError, match="not the one the derivation produces"):
        bank.validate_analysis_plan(forged, ROOT)


def test_a_plan_from_another_milestone_is_refused(plan):
    with pytest.raises(bank.BankError, match="not an M120 analysis plan"):
        bank.validate_analysis_plan(dict(plan, schema="m119-carrier-bank-analysis-plan-v1"), ROOT)


def test_the_plan_inherits_the_science_and_says_which_bytes(plan):
    assert plan["arm_names"] == ["FRESH", "CASCADE_ONLY", "POLICY_ONLY", "FULL"]
    assert plan["descendant_arm"] == "FULL" and plan["comparator_arm"] == "FRESH"
    assert plan["alpha"] == endpoint.ALPHA
    assert plan["minimum_risk_difference"] == endpoint.MINIMUM_RISK_DIFFERENCE
    assert plan["session_budget"] == 4000
    assert plan["minimum_qualifying_carriers"] == 3
    assert plan["minimum_distinct_qualifying_structures"] == 3
    assert set(plan["inherited_science_digests"]) == set(bank.INHERITED_SCIENCE)


def test_the_derivation_refuses_to_run_on_scientific_modules_that_have_drifted(monkeypatch):
    """A milestone that quietly edited the endpoint it claims to inherit tests something else."""
    monkeypatch.setitem(bank.INHERITED_DIGESTS, "metamorphosis/m119_endpoint.py", "0" * 64)
    with pytest.raises(bank.BankError, match="no longer matches the bytes"):
        bank.build_analysis_plan(ROOT)


def test_the_generator_spec_binds_the_plan_and_the_route(plan):
    spec = bank.build_generator_spec(plan, ROOT)
    bank.validate_generator_spec(spec, plan, ROOT)
    assert spec["generator_identity"]["provider"] == "OpenInference"
    assert spec["requested_carrier_count"] == bank.REQUESTED_CARRIER_COUNT
    assert spec["blindness_contract"]["contamination_hits_in_the_prompt"] == []
    assert spec["blindness_contract"]["no_system_message_is_sent"] is True
    assert spec["blindness_contract"]["tools_sent"] is False
    with pytest.raises(bank.BankError, match="bound to a different analysis plan"):
        bank.validate_generator_spec(spec, dict(plan, plan_commitment_sha256="0" * 64), ROOT)


def test_the_qualifying_input_substitutes_only_the_count():
    text = bank.qualifying_input(ROOT)
    assert "exactly %d entries" % bank.REQUESTED_CARRIER_COUNT in text
    assert "exactly N entries" not in text
    template = (ROOT / "experiments" / "M120" / "GENERATOR_PROMPT.txt").read_text(encoding="utf-8")
    assert len(text) == len(template.replace(
        "exactly N entries", "exactly %d entries" % bank.REQUESTED_CARRIER_COUNT))


def test_the_prompt_names_nothing_the_generator_must_not_see():
    text = (ROOT / "experiments" / "M120" / "GENERATOR_PROMPT.txt").read_text(encoding="utf-8")
    lowered = text.lower()
    for forbidden in ("hypothesis", "cascade", "policy", "attribution", "comparator", "arm",
                      "qualif", "descendant", "experiment", "carrier"):
        assert forbidden not in lowered, "the prompt leaks %r" % forbidden


# ---------------------------------------------------------------------------------------------
# R4 -- the checker resolves and reproduces its own evidence
# ---------------------------------------------------------------------------------------------

def _checker_source() -> ast.Module:
    return ast.parse((ROOT / "scripts" / "check_m120_result.py").read_text(encoding="utf-8"))


def test_the_checker_offers_no_argument_that_selects_evidence():
    """M119's second disclosed defect was reachable through `--measurements` and `--plan`."""
    options = set()
    for node in ast.walk(_checker_source()):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_argument"):
            for argument in node.args:
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                    options.add(argument.value)
    assert options == {"--out", "--require-result"}, (
        "the checker grew a command-line option; every evidence path must be resolved from the "
        "chronology, not named by a caller: %s" % sorted(options))


def test_the_runner_offers_no_argument_that_selects_evidence():
    source = ast.parse((ROOT / "scripts" / "run_m120_qualification.py").read_text(
        encoding="utf-8"))
    options = set()
    for node in ast.walk(source):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_argument"):
            for argument in node.args:
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                    options.add(argument.value)
    assert options == {"--out"}


def test_the_checker_reads_its_evidence_from_the_chronology_constants():
    text = (ROOT / "scripts" / "check_m120_result.py").read_text(encoding="utf-8")
    for constant in ("chronology.MEASUREMENTS", "chronology.ANALYSIS_PLAN",
                     "chronology.REVEAL_RECORD", "chronology.ADEQUACY",
                     "chronology.CARRIER_BANK", "chronology.PUBLIC_BANK_COMMITMENT",
                     "chronology.REVEAL_AUTHORIZATION", "chronology.ADMISSION",
                     "chronology.SEALED_BANK"):
        assert constant in text
    assert "measurement.measure(" in text, "the checker must reproduce, not read, the measurement"


# ---------------------------------------------------------------------------------------------
# The chronology
# ---------------------------------------------------------------------------------------------

def test_sealing_requires_the_adequacy_record():
    """An admissible-but-inadequate bank must not be able to reach the seal."""
    assert chronology.ADEQUACY in chronology.STAGES["sealing"]
    assert chronology.ADEQUACY in chronology.STAGES["authorization"]
    assert chronology.ADEQUACY in chronology.STAGES["replay"]


def test_the_freeze_requires_the_development_records():
    for artifact in (chronology.BANK_SIZING, chronology.DEVELOPMENT_REHEARSAL,
                     chronology.READINESS_RESULT):
        assert artifact in chronology.STAGES["scientific_freeze"]
        assert artifact in chronology.STAGES["qualifying_generation"]


def test_no_scientific_artifact_may_predate_the_generation():
    for artifact in (chronology.DELIVERY_LEDGER, chronology.ADMISSION, chronology.ADEQUACY,
                     chronology.SEALED_BANK, chronology.CARRIER_BANK, chronology.MEASUREMENTS,
                     chronology.RESULT):
        assert artifact in chronology.NO_SCIENTIFIC_ARTIFACT_BEFORE


def test_the_closure_is_fully_bound_and_names_every_entry_point():
    assert chronology.unbound_interpretation_modules(ROOT) == []
    assert chronology.undeclared_measurement_entry_points(ROOT) == []
    stock = chronology.inventory(ROOT)
    assert stock["closure_is_fully_bound"] is True
    for module in ("metamorphosis/m120_carrier_contract.py", "metamorphosis/m120_adequacy.py",
                   "metamorphosis/m120_admission.py", "metamorphosis/m120_measurement.py",
                   "scripts/check_m120_result.py"):
        assert module in stock["tested_system_paths"]


def test_every_m120_entry_point_on_disk_is_answered():
    """A runner nothing imports is invisible to the closure; this is the guard that sees it."""
    answered = set(chronology.INTERPRETATION_ROOTS) | set(chronology.UNBOUND_BY_DESIGN)
    for path in sorted((ROOT / "scripts").glob("*m120*.py")):
        assert "scripts/%s" % path.name in answered, "%s is answered by nothing" % path.name


def test_the_readiness_gate_refuses_a_result_that_is_not_ready(tmp_path, monkeypatch):
    """M119 inherited a readiness result across a schema change. This one refuses to."""
    record = {"milestone": "M120", "ready": False, "verdict": "not_ready_stress",
              "development": True, "is_a_qualifying_call": False,
              "candidate_schema_sha256": sha256_hex(canonical_bytes(
                  contract.candidate_schema())),
              "result_sha256": "0" * 64}
    path = tmp_path / chronology.READINESS_RESULT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record), encoding="utf-8")
    monkeypatch.setattr(chronology, "assert_committed_at_head", lambda *a, **k: "digest")
    with pytest.raises(chronology.ChronologyError, match="did not pass the M120 readiness gate"):
        chronology.assert_readiness_passed(tmp_path)


def test_the_readiness_gate_refuses_a_result_measured_against_another_schema(tmp_path, monkeypatch):
    record = {"milestone": "M120", "ready": True, "verdict": "ready",
              "development": True, "is_a_qualifying_call": False,
              "candidate_schema_sha256": "0" * 64, "result_sha256": "0" * 64}
    path = tmp_path / chronology.READINESS_RESULT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record), encoding="utf-8")
    monkeypatch.setattr(chronology, "assert_committed_at_head", lambda *a, **k: "digest")
    with pytest.raises(chronology.ChronologyError, match="different candidate schema"):
        chronology.assert_readiness_passed(tmp_path)


def test_the_readiness_gate_refuses_a_result_that_claims_to_be_qualifying(tmp_path, monkeypatch):
    record = {"milestone": "M120", "ready": True, "verdict": "ready",
              "development": True, "is_a_qualifying_call": True,
              "candidate_schema_sha256": sha256_hex(canonical_bytes(
                  contract.candidate_schema())),
              "result_sha256": "0" * 64}
    path = tmp_path / chronology.READINESS_RESULT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record), encoding="utf-8")
    monkeypatch.setattr(chronology, "assert_committed_at_head", lambda *a, **k: "digest")
    with pytest.raises(chronology.ChronologyError, match="qualifying call"):
        chronology.assert_readiness_passed(tmp_path)


def test_the_freeze_binds_the_decision_relevant_commitments():
    """Source digests alone say nothing about the thresholds the verdict turns on."""
    source = (ROOT / "metamorphosis" / "m120_chronology.py").read_text(encoding="utf-8")
    for key in ("minimum_qualifying_carriers", "minimum_distinct_qualifying_structures",
                "alpha", "minimum_risk_difference", "candidate_schema_sha256",
                "session_budget", "fresh_seed"):
        assert '"%s"' % key in source


# ---------------------------------------------------------------------------------------------
# Admission and its decoder neutrality proof
# ---------------------------------------------------------------------------------------------

def test_admission_admits_a_conforming_completion_and_refuses_nothing_to_the_host():
    machines = list(devkit.development_candidates("m120-admit-", 12))
    raw = json.dumps({"choices": [{"message": {"content": json.dumps({"machines": machines})}}]}
                     ).encode("utf-8")
    record = admission.evaluate(raw, candidate_schema=contract.candidate_schema(),
                                bank_nonce=NONCE, request_body_sha256="0" * 64)
    admission.validate_record(record)
    assert record["admitted"] is True
    assert record["carriers_refused"] == 0
    assert record["carriers_enveloped"] == 12


def test_admission_refuses_a_completion_the_candidate_schema_rejects():
    raw = json.dumps({"choices": [{"message": {"content": json.dumps(
        {"machines": [{"surface": {}, "cells": [], "hidden": [], "errors": [],
                       "conditional_actions": [], "actions": []}]})}}]}).encode("utf-8")
    record = admission.evaluate(raw, candidate_schema=contract.candidate_schema(),
                                bank_nonce=NONCE)
    admission.validate_record(record)
    assert record["admitted"] is False
    assert record["failure_stage"] == "output_schema_violation"


@pytest.mark.parametrize("raw,stage", [
    (b"not json", "raw_response_not_json"),
    (json.dumps({"choices": []}).encode(), "choice_cardinality"),
    (json.dumps({"choices": [{"message": {"content": "  "}}]}).encode(), "no_completion_content"),
    (json.dumps({"choices": [{"message": {"content": "{"}}]}).encode(), "content_not_json"),
    (json.dumps({"choices": [{"message": {"content": "[]"}}]}).encode(), "content_not_object"),
])
def test_admission_names_the_stage_it_refused_at(raw, stage):
    record = admission.evaluate(raw, candidate_schema=contract.candidate_schema(),
                                bank_nonce=NONCE)
    admission.validate_record(record)
    assert record["admitted"] is False and record["failure_stage"] == stage


def test_the_admission_record_allowlist_is_enforced():
    record = admission.evaluate(b"not json", candidate_schema=contract.candidate_schema(),
                                bank_nonce=NONCE)
    with pytest.raises(admission.AdmissionError):
        admission.validate_record(dict(record, carrier_names=["leaked"]))
    with pytest.raises(admission.AdmissionError):
        admission.validate_record(dict(record, admitted=True, failure_stage="content_not_json"))


def test_the_decoder_envelope_is_neutral_and_says_so_mechanically():
    machines = list(devkit.development_candidates("m120-neutrality-", 20))
    proof = admission.decoder_neutrality({"machines": machines}, NONCE)
    assert proof["neutral"] is True
    assert proof["cardinality_preserved"] and proof["ordering_preserved"]
    assert proof["decode_is_deterministic"] and proof["decode_is_position_independent"]
    assert proof["nonce_changes_only_refs_and_nonce"]
    payload = admission.envelope_payload({"machines": machines}, NONCE)
    for index, carrier in enumerate(payload["carriers"]):
        assert carrier["carrier_ref"] == opaque_domain_id(NONCE, index)


# ---------------------------------------------------------------------------------------------
# The readiness stress schema, and the sizing derivation
# ---------------------------------------------------------------------------------------------

def test_the_stress_schema_dominates_the_candidate_schema():
    """A stress easier than the contract proves nothing about the contract."""
    dominates, shortfalls = schema_tools.census_dominates(
        schema_tools.census(stress.build_stress_schema()),
        schema_tools.census(contract.candidate_schema()))
    assert dominates, shortfalls


def test_m118s_stress_schema_does_not_dominate_it_which_is_why_readiness_is_re_run():
    from metamorphosis import m116_stress_schema as inherited_stress
    dominates, _ = schema_tools.census_dominates(
        schema_tools.census(inherited_stress.build_stress_schema()),
        schema_tools.census(contract.candidate_schema()))
    assert not dominates, (
        "if the inherited stress did dominate, re-running readiness would be unnecessary and the "
        "chronology gate would be complexity with no failure behind it")


def test_the_stress_schema_carries_no_carrier_vocabulary():
    """Previewing the bank during DEVELOPMENT would be a degree of freedom over the contract."""
    text = json.dumps(stress.build_stress_schema()) + stress.STRESS_PROMPT
    for forbidden in ("cell", "guard", "effect", "arity", "arg_size", "surface", "machine",
                      "carrier"):
        assert forbidden not in text.lower()


def test_the_committed_bank_sizing_matches_what_the_derivation_produces():
    """The plan's numbers are a measurement, not a memory."""
    rate = devkit.qualification_rate("m120-sizing-", 400, mode=devkit.MODE_CORNER)
    estimate = bank.BANK_SIZING["yield_estimate"]
    assert rate["qualification_rate"] == estimate["measured_qualification_rate_at_the_corner"]
    assert (rate["mean_demand_pairs_per_qualifying_carrier"]
            == estimate["mean_demand_pairs_per_qualifying_carrier"])
    assert rate["every_decoded_candidate_was_accepted"] is True
    assert estimate["planning_qualification_rate"] == round(rate["qualification_rate"] / 2, 4)


def test_the_planning_rate_yields_more_than_the_plan_minimum(plan):
    estimate = plan["bank_sizing"]["yield_estimate"]
    expected = bank.REQUESTED_CARRIER_COUNT * estimate["planning_qualification_rate"]
    assert expected >= plan["minimum_qualifying_carriers"]
    assert (estimate["expected_paired_demands_at_the_planning_rate"]
            >= endpoint.required_paired_demands())


def test_the_token_envelope_stays_under_what_readiness_proved(plan):
    envelope = plan["bank_sizing"]["token_envelope"]
    assert envelope["estimated_completion_tokens_at_the_contract_ceiling"] < envelope[
        "readiness_proved_completion_tokens"]
    assert envelope["readiness_proved_completion_tokens"] < envelope["max_output_tokens"]


def test_the_development_emitter_only_draws_schema_valid_candidates():
    for mode in devkit.MODES:
        for candidate in devkit.development_candidates("m120-devkit-", 40, mode=mode):
            ok, location, keyword = schema_tools.instance_is_valid(
                {"machines": [candidate]}, contract.candidate_schema())
            assert ok, "%s draw left the candidate schema at %s (%s)" % (mode, location, keyword)


def test_the_corner_draw_is_the_pessimistic_one():
    """Sizing against the uniform draw would be sizing against a generator nobody has observed."""
    corner = devkit.qualification_rate("m120-order-", 200, mode=devkit.MODE_CORNER)
    uniform = devkit.qualification_rate("m120-order-", 200, mode=devkit.MODE_UNIFORM)
    assert corner["qualification_rate"] < uniform["qualification_rate"]


# ---------------------------------------------------------------------------------------------
# The claim boundary travels with the plan
# ---------------------------------------------------------------------------------------------

def test_the_plan_claims_no_generality_gate(plan):
    boundary = plan["claim_boundary"]
    assert boundary["advances_any_generality_gate"] is False
    assert boundary["agi"] is False
    assert boundary["recursive_self_improvement"] is False
    assert boundary["carrier_family_is_narrower_than_m115"] is True
    assert boundary["external_reproduction"] is False


def test_the_plan_discloses_the_dependency_on_the_closed_m119_record(plan):
    limitations = " ".join(plan["limitations"]).lower()
    assert "narrower" in limitations
    assert "m119" in limitations
    assert "closed" in limitations
    report = plan["carrier_contract"]
    assert report["family_is_narrower_than_m115_and_that_is_disclosed"] is True
    assert plan["filiation"]["predecessor_record_is_closed_and_not_repaired"] is True


def test_the_verdict_vocabulary_is_the_inherited_one(plan):
    assert plan["verdicts"] == list(endpoint.VERDICTS)
    assert plan["an_instrument_failure_is_not_a_scientific_result"] is True
    assert plan["an_underpowered_bank_is_inconclusive_not_negative"] is True


# ---------------------------------------------------------------------------------------------
# The declared digest mode
# ---------------------------------------------------------------------------------------------

def test_the_chronology_declares_how_it_compares_committed_bytes():
    """A gate that is a property of the checkout is not a property of the repository.

    M119 compared raw bytes, which makes every committed-at-HEAD check fail on any clone whose git
    converts line endings -- including this repository's own default. Pinning the files through
    `.gitattributes` is not available either: that file is a raw-byte-frozen member of M106's
    apparatus, and appending to it breaks a closed milestone's freeze. So the mode is declared.
    """
    assert chronology.DIGEST_MODE == "lf_normalized"
    # The stage permission record carries the mode, so a downstream reader never has to guess
    # which comparison the gate performed. Checked without requiring the milestone's own
    # artifacts to be committed yet.
    import unittest.mock

    with unittest.mock.patch.object(chronology, "assert_committed_at_head",
                                    return_value="0" * 64):
        permission = chronology.assert_stage_permitted("preregistration", ROOT)
    assert permission["digest_mode"] == chronology.DIGEST_MODE


def test_the_chronology_still_refuses_a_predecessor_whose_content_differs(tmp_path, monkeypatch):
    """Normalizing line endings must not normalize away a real difference."""
    relative = Path("experiments/M120/PREREGISTRATION.md")
    (tmp_path / relative.parent).mkdir(parents=True, exist_ok=True)
    (tmp_path / relative).write_bytes(b"one thing\r\n")
    monkeypatch.setattr(chronology, "_head_blob", lambda *a, **k: b"a different thing\n")
    with pytest.raises(chronology.ChronologyError, match="differs from its committed bytes"):
        chronology.assert_committed_at_head(relative, tmp_path)
    # ... and must accept the same content under either convention.
    monkeypatch.setattr(chronology, "_head_blob", lambda *a, **k: b"one thing\n")
    assert chronology.assert_committed_at_head(relative, tmp_path)


def test_an_uncommitted_predecessor_is_refused(tmp_path, monkeypatch):
    relative = Path("experiments/M120/PREREGISTRATION.md")
    (tmp_path / relative.parent).mkdir(parents=True, exist_ok=True)
    (tmp_path / relative).write_bytes(b"present\n")
    monkeypatch.setattr(chronology, "_head_blob", lambda *a, **k: None)
    with pytest.raises(chronology.ChronologyError, match="not committed at HEAD"):
        chronology.assert_committed_at_head(relative, tmp_path)


def test_the_repository_gitattributes_is_left_alone():
    """M106 binds it by raw-byte SHA-256. M120 does not touch it, and this says so out loud."""
    text = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "m120" not in text.lower(), (
        "an M120 entry in .gitattributes would change bytes M106's freeze binds")
