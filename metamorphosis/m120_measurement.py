"""The H65 measurement, in one place, so the runner and the checker cannot differ.

M119's checker recomputed the paired outcomes and the guard measures **from the runner's per-demand
evidence**. That is a real improvement over M118, which evaluated its guards on aggregates the
runner had written — but it still trusts the evidence. A fabricated `entries` array with a
recomputed `measurements_sha256` reproduces perfectly, because every number the checker forms is
formed from the array it was handed.

M120's own DEVELOPMENT rehearsal demonstrated exactly that: an attack that rewrote every score in
the committed measurements file, recomputed its digest and committed it over the canonical path was
**accepted**, because the file was at HEAD, matched its own digest, named the right reveal and
carried the right freeze commitment. Authenticating a file is not the same as knowing what is in it.

The fix is not another binding. It is that the measurement is a **pure function of committed data**:

    the revealed carrier bank   committed, and digest-bound to the committed reveal record
    the analysis plan           committed, and re-derived from code
    the committed bank nonce    committed, and checked against its own digest
    the frozen arms, evaluator, runtime and host   bound by the tested-system freeze

Nothing else enters it. So the checker does not have to trust `entries`: it recomputes the whole
record from those inputs and requires canonical-byte equality with what was committed. A forged
measurement is then not a file that has to be caught by a rule someone remembered to write; it is a
file that does not reproduce.

This module holds that function. `scripts/run_m120_qualification.py` calls it to produce the record
and `scripts/check_m120_result.py` calls it to reproduce the record, so there is no second
implementation for the two to drift apart in.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from metamorphosis import carrier_host as host
from metamorphosis import m113_evaluator as evaluator
from metamorphosis import m113_runtime as runtime
from metamorphosis import m119_arms as arms
from metamorphosis import m119_endpoint as endpoint
from metamorphosis import m120_adequacy as adequacy
from metamorphosis import m120_carrier_contract as contract
from metamorphosis.blind_bank_protocol import canonical_bytes, opaque_domain_id, sha256_hex

MEASUREMENTS_SCHEMA = "m120-h65-measurements-v1"


class MeasurementError(RuntimeError):
    """The measurement cannot be taken honestly. Every path fails closed."""


def _score_keys() -> tuple[str, ...]:
    from scripts import run_m113_qualification as inherited  # noqa: PLC0415
    return tuple(inherited.SCORE_KEYS)


def restore_acquired() -> dict[str, Any]:
    """The acquired cascade and policy, from the producers' frozen bytes.

    Taken out of the inherited restoration rather than decoded again, so the provenance path is the
    one the predecessor milestones already prove.
    """
    from scripts import run_m113_qualification as inherited  # noqa: PLC0415
    restored = inherited.restore_arms()
    cascades = restored["cascades"]
    cascade_rules = cascades["M2"]["rules"]
    policy = cascades["M3"]["policy"]
    if not policy:
        raise MeasurementError("the acquired diagnostic policy did not restore")
    if not cascade_rules:
        raise MeasurementError("the acquired cascade did not restore")
    return {"cascade_rules": cascade_rules, "policy": policy,
            "pooled_record": restored["record"],
            "provenance_checks": restored["provenance_checks"],
            "corruption": restored["corruption"]}


def committed_nonce(root: Path, nonce_path: Path) -> str:
    """The bank nonce, from the committed commitment, checked against its own digest."""
    record = json.loads((root / nonce_path).read_text(encoding="utf-8"))
    nonce = record.get("bank_nonce")
    if not isinstance(nonce, str) or len(nonce) != 64:
        raise MeasurementError("the committed bank nonce is not a 64-character value")
    if record.get("bank_nonce_sha256") != sha256_hex(nonce.encode("ascii")):
        raise MeasurementError("the committed bank nonce does not match its own digest")
    return nonce


def load_carriers(path: Path, nonce: str) -> list[dict[str, Any]]:
    """The revealed carrier payload, read as the payload it is."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping) or not isinstance(value.get("carriers"), list):
        raise MeasurementError(
            "the carrier file is not a revealed carrier payload carrying a `carriers` list")
    if value.get("bank_nonce") != nonce:
        raise MeasurementError(
            "the carrier payload was enveloped under a different bank nonce than the committed one")
    return [dict(carrier) for carrier in value["carriers"]]


def measure(carriers: Sequence[Mapping[str, Any]], nonce: str, plan: Mapping[str, Any],
            *, provenance: Mapping[str, Any]) -> dict[str, Any]:
    """Every arm, every qualifying carrier, every demand. A pure function of its inputs.

    Deterministic by construction: the comparator draws from the committed seed and the opaque
    reference the committed nonce fixes, the demand pairs are a function of the carrier alone, and
    the runtime is total. Two calls on the same committed bank produce the same bytes, which is
    what lets the checker reproduce this record rather than believe it.
    """
    from scripts import run_m113_qualification as inherited  # noqa: PLC0415

    score_keys = _score_keys()
    session_budget = int(plan["session_budget"])
    acquired = restore_acquired()
    entries: list[dict[str, Any]] = []
    qualifying = 0
    refused = 0
    signatures: Counter = Counter()

    for index, carrier in enumerate(carriers):
        # The envelope is positional: carrier *i* is machine *i*, tagged with the opaque identifier
        # the committed nonce determines. Checking that here means the reference the comparator is
        # seeded from is the one the nonce fixed before the bank existed.
        expected_reference = opaque_domain_id(nonce, index)
        reference = carrier.get("carrier_ref") or expected_reference
        if reference != expected_reference:
            raise MeasurementError(
                "carrier %d carries a reference the committed nonce does not determine" % index)

        # A carrier the frozen host refuses is counted, never repaired and never fatal.
        try:
            validated = host.validate_carrier(carrier)
        except host.CarrierError:
            refused += 1
            continue
        if not evaluator.qualification_report(validated)["qualifies"]:
            continue
        qualifying += 1
        signatures[host.structural_signature(validated)] += 1

        for pair in evaluator.derive_demand_pairs(validated, reference, session_budget):
            evaluator.assert_demand_pair_delta(pair)
            truth = pair["ground_truth"]
            cascades = arms.build_arms(acquired["cascade_rules"], acquired["policy"],
                                       str(reference), str(pair["pair_digest"]))
            states = inherited.build_states(cascades, acquired["pooled_record"],
                                            pair["shared"]["entry"])
            record: dict[str, Any] = {
                "carrier_ref": str(reference),
                "carrier_digest": validated["carrier_digest"],
                "pair_digest": pair["pair_digest"],
                "ground_truth_component": truth["component"],
                "ground_truth_row": truth["row_index"],
                "arms": {},
            }
            for name in arms.ALL_ARM_NAMES:
                state = states[name]
                budget = session_budget * arms.BUDGET_MULTIPLIER.get(name, 1)
                arm_record: dict[str, Any] = {"budget": budget}
                for demand_class in evaluator.DEMAND_CLASSES:
                    demand = evaluator.materialize_twin(pair, demand_class)
                    channel = host.Channel(validated, reference, budget)
                    outcome = runtime.resolve(state, channel, demand)
                    score = evaluator.score_attempt(validated, demand, outcome)
                    row: dict[str, Any] = {
                        "verdict": outcome["verdict"],
                        "invocations_used": outcome["invocations_used"],
                        "probes_spent": outcome["probes_spent"],
                        "budget": budget,
                        "budget_exhausted": bool(outcome["invocations_used"] >= budget),
                        "within_budget": bool(score["within_budget"]),
                        "primary_success": endpoint.primary_success(demand_class, score),
                        "score": {key: bool(score[key]) for key in score_keys},
                    }
                    if outcome["trace"] and demand_class == evaluator.CLASS_REACHABLE:
                        attributed = outcome["trace"][0]["attribution"]["component"]
                        row["attributed_component"] = attributed
                        row["attribution_correct"] = bool(attributed == truth["component"])
                    arm_record[demand_class] = row
                record["arms"][name] = arm_record
            entries.append(record)

    record = {
        "schema": MEASUREMENTS_SCHEMA,
        "milestone": "M120", "hypothesis": "H65",
        "arms_version": arms.ARMS_VERSION,
        "endpoint_version": endpoint.ENDPOINT_VERSION,
        "contract_version": contract.CONTRACT_VERSION,
        "decoder_version": contract.DECODER_VERSION,
        "candidate_schema_sha256": sha256_hex(canonical_bytes(contract.candidate_schema())),
        "arm_names": list(arms.ARM_NAMES),
        "diagnostic_arm_names": list(arms.DIAGNOSTIC_ARM_NAMES),
        "budget_multiplier": dict(arms.BUDGET_MULTIPLIER),
        "descendant_arm": arms.DESCENDANT_ARM,
        "comparator_arm": arms.COMPARATOR_ARM,
        "fresh_seed": arms.FRESH_SEED,
        "fresh_seed_source": arms.FRESH_SEED_SOURCE,
        "action_space": arms.action_space_statement(),
        "provenance_checks": acquired["provenance_checks"],
        "corruption": acquired["corruption"],
        "analysis_plan_commitment_sha256": plan["plan_commitment_sha256"],
        "session_budget": session_budget,
        "session_budget_came_from_the_committed_plan_not_the_command_line": True,
        "every_input_was_resolved_from_the_chronology_not_from_argv": True,
        "this_record_is_a_pure_function_of_the_committed_bank_plan_and_nonce": True,
        "carriers_seen": len(carriers),
        "carriers_refused_by_the_frozen_host": refused,
        "qualifying_carriers": qualifying,
        "distinct_qualifying_structures": len(signatures),
        # The same gate the pre-seal stage ran, over the bank that was actually revealed.
        "adequacy_recomputed_after_the_reveal": adequacy.evaluate(carriers, plan),
        "demand_classes": list(evaluator.DEMAND_CLASSES),
        "entries": entries,
        "the_runner_records_evidence_and_decides_nothing": True,
        "freeze_commitment_sha256": provenance["freeze_commitment_sha256"],
        "reveal_record_sha256": provenance["reveal_record_sha256"],
        "carrier_bank_sha256": provenance["carrier_bank_sha256"],
        "measurements_sha256": "",
    }
    record["measurements_sha256"] = sha256_hex(
        canonical_bytes({k: v for k, v in record.items() if k != "measurements_sha256"}))
    return record


__all__ = [
    "MEASUREMENTS_SCHEMA",
    "MeasurementError",
    "committed_nonce",
    "load_carriers",
    "measure",
    "restore_acquired",
]
