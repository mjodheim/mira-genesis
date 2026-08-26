"""M113 - the architecture for receiving a carrier family this project did not design.

M112 removed **world** authorship and recorded, in its own decision record and in
`MIRA_GENERALITY_CRITERIA.md`, exactly what it did not remove: the carrier. The value chain, the
document shape, the reference edge, the operators, the bounds and the evaluator were all this
project's, and a blind generator only chose values inside them.

This module is the receiving end of a bank in which the generator chooses the **carrier**: its state,
its observability, its actions, their preconditions, their effects, its error vocabulary and the wire
grammar it speaks. It binds the milestone-agnostic `mira-blind-bank-v1` custody chain to the
`mira-blind-carrier-v1` meta-schema that `carrier_host` executes.

**No bank exists.** Nothing here generates one and nothing here may. `assess_carrier_bank_readiness`
fails closed and reports phase `draft` until artifacts exist that this project cannot manufacture on
its own without defeating the point.

## What is blind here, and what is not

Blind, and chosen entirely by the generator: how many cells the carrier holds and over what domains,
which of them are observable at all, what the actions are called, how many arguments they take, when
they are refused, what they do, what the errors are called, and which of four wire surfaces the
carrier speaks with which tokens and separators.

Not blind, and this project's reception contract: the meta-schema, the four surface shapes, the
meta-channel, the qualification rule, the demand-derivation rule and the evaluator. The project
builds the contract for receiving a carrier. It does not choose the qualifying implementations.

The prompt is written to make aiming impossible rather than merely forbidden. It names no feature,
no component, no lineage, no demand, no target, no reachability, no refusal and no experiment. A
generator handed it is being asked for a small machine, and there is nothing in the request from
which the use could be recovered.

## The two M112 defects this file exists not to repeat

**The cardinality defect.** M112 froze `requested_record_count = requested_world_count` while a world
was five records, so a hundred bought twenty and no stage compared the two numbers.
`validate_analysis_plan` here refuses a plan that does not declare its cardinality derivation, and
`m113_evaluator.assert_cardinality` compares every adjacent pair mechanically at materialization
time. One carrier is one record; the identity is declared as an identity and is checked.

**The `P5` defect.** M112 inherited a bound of seven expression nodes from an empirical observation
over 1 160 project worlds, and the first blind world needed nine. Nothing in this milestone inherits
a bound. Closure is an exact fixed point over the carrier's own transition relation, and a carrier
whose closure is not reached is non-qualifying under a rule frozen before any carrier existed.

## What a positive M113 would establish, exactly

It removes **carrier authorship** in the sense the meta-schema admits: the interaction language of
each qualifying body -- its actions, its preconditions, its errors, its wire -- is not a product of
descriptors encoded in the discoverer, and was fixed before the learner and selected after the
freeze. It does not remove **substrate** authorship: the meta-schema, the host and the reception
contract remain this project's, and so do the component registry, the feature vocabulary and the
probe primitive.

The evidence tier stays `blind_generated_sealed_bank`. Context blindness is provable;
training-data independence is not; **human independence is not obtained at all**. Nothing produced
under this contract may be reported as independent human reproduction, and no tier below
`human_maintained_sealed_bank` ever closes G4.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from metamorphosis import carrier_host as host
from metamorphosis import m113_evaluator as evaluator
from metamorphosis.blind_bank_protocol import (
    EVIDENCE_TIERS,
    PHASES,
    canonical_bytes,
    contamination_hits,
    opaque_domain_id,
    sha256_hex,
)

MILESTONE = "M113"
CONTRACT_VERSION = "mira-blind-bank-v1"
CARRIER_SCHEMA_VERSION = host.SCHEMA

CARRIER_PAYLOAD_SCHEMA = "m113-blind-carrier-payload-v1"
DEVELOPMENT_PAYLOAD_SCHEMA = "m113-blind-carrier-payload-development-v1"
ANALYSIS_PLAN_SCHEMA = "m113-carrier-bank-analysis-plan-v1"
SYSTEM_PROTOCOL_SCHEMA = "m113-carrier-bank-system-protocol-v1"
REPORT_SCHEMA = "m113-carrier-bank-readiness-v1"
SURVEY_SCHEMA = "m113-devkit-survey-v1"

EXPERIMENT_DIRECTORY = Path("experiments/M113")
GENERATOR_SPEC_PATH = EXPERIMENT_DIRECTORY / "GENERATOR_SPEC.json"
GENERATOR_PROMPT_PATH = EXPERIMENT_DIRECTORY / "GENERATOR_PROMPT.txt"
OUTPUT_SCHEMA_PATH = EXPERIMENT_DIRECTORY / "OUTPUT_SCHEMA.json"
ANALYSIS_PLAN_PATH = EXPERIMENT_DIRECTORY / "ANALYSIS_PLAN.json"
DEVKIT_SURVEY_PATH = EXPERIMENT_DIRECTORY / "DEVKIT_SURVEY.json"
BANK_COMMITMENT_PATH = EXPERIMENT_DIRECTORY / "PUBLIC_BANK_COMMITMENT.json"
SYSTEM_PROTOCOL_PATH = EXPERIMENT_DIRECTORY / "SYSTEM_PROTOCOL.json"
REVEAL_AUTHORIZATION_PATH = EXPERIMENT_DIRECTORY / "REVEAL_AUTHORIZATION.json"
GENERATION_LEDGER_PATH = EXPERIMENT_DIRECTORY / "GENERATION_LEDGER.json"
RESULT_PATH = EXPERIMENT_DIRECTORY / "RESULT.json"

# The tested system. Frozen before the bank is revealed; a bank cannot be revealed against a system
# that changed afterwards. M107-M111 are the acquired machinery under test and are immutable here;
# the four M113 modules are the body that meets the carrier.
TESTED_SYSTEM_PATHS = (
    "metamorphosis/m107_runtime.py",
    "metamorphosis/m108_runtime.py",
    "metamorphosis/m109_runtime.py",
    "metamorphosis/m110_runtime.py",
    "metamorphosis/m111_runtime.py",
    "metamorphosis/carrier_host.py",
    "metamorphosis/m113_evaluator.py",
    "metamorphosis/m113_runtime.py",
    "metamorphosis/m113_carrier_bank.py",
    "scripts/run_m113_qualification.py",
    "scripts/check_m113_result.py",
)

CARRIER_BANK_CLAIM_BOUNDARY = {
    "evidence_tier": "blind_generated_sealed_bank",
    "procedural_independence": True,
    "generator_context_blindness": True,
    "generator_training_data_independence": False,
    "human_independence": False,
    "external_reproduction": False,
    "removes_world_authorship": True,
    "removes_carrier_interaction_language_authorship": True,
    "removes_substrate_authorship": False,
    "closes_g4": False,
    "closes_g1": False,
    "advances_any_generality_gate": False,
    "agi": False,
}


class CarrierBankError(RuntimeError):
    """Raised when an artifact under this contract is invalid. Every path fails closed."""


# ----------------------------------------------------------------------------------------
# The payload: carriers, and nothing that could tell anyone what they are for.
# ----------------------------------------------------------------------------------------

# Keys that would betray that the emitter knew what the carriers were for. Their presence does not
# prove contamination; it means a generator with no context produced a word it had no reason to.
FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "row", "rows", "row_index", "row_labels", "feature", "features", "feature_row",
        "component", "components", "stratum", "census", "target", "targets", "demand",
        "demands", "reachable", "unreachable", "qualifying", "qualifies", "pair", "policy",
        "episodes", "label", "labels", "lineage", "machinery", "learner", "agent", "evaluator",
        "difficulty", "solution", "answer", "expected", "should_refuse", "should_succeed",
    }
)


def _keys(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            found.append(str(key))
            found += _keys(item)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            found += _keys(item)
    return found


def validate_carrier_bank_payload(
    payload: Mapping[str, Any], *, development: bool = False
) -> dict[str, Any]:
    """Structural conformity to the meta-schema, and silence about everything else.

    This runs **after** reveal. It never decides whether a carrier is useful, only whether it is a
    well-formed member of the meta-schema and whether it says anything it could not have known.
    Qualification is a separate question, asked by the evaluator under a separately frozen rule.
    """
    expected = DEVELOPMENT_PAYLOAD_SCHEMA if development else CARRIER_PAYLOAD_SCHEMA
    if not isinstance(payload, Mapping) or payload.get("schema") != expected:
        raise CarrierBankError("carrier bank payload schema is not the declared one")
    nonce = payload.get("bank_nonce")
    if not isinstance(nonce, str) or len(nonce) != 64:
        raise CarrierBankError("carrier bank payload carries no 64-character nonce")

    offending = sorted(set(_keys(payload)) & FORBIDDEN_PAYLOAD_KEYS)
    if offending:
        raise CarrierBankError(
            "carrier bank payload names keys a blind generator could not know: %s"
            % ", ".join(offending)
        )
    raw = payload.get("carriers")
    hits = contamination_hits(raw)
    if hits:
        raise CarrierBankError("carrier bank payload is contaminated: %s" % ", ".join(hits))

    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or not raw:
        raise CarrierBankError("carrier bank payload holds no carriers")

    decoded: list[dict[str, Any]] = []
    refused: list[dict[str, Any]] = []
    signatures: dict[str, int] = {}
    for index, entry in enumerate(raw):
        expected_id = opaque_domain_id(nonce, index)
        if not isinstance(entry, Mapping) or entry.get("carrier_ref") != expected_id:
            raise CarrierBankError(
                "carrier %d does not carry the opaque identifier derived from the nonce" % index
            )
        body = {key: value for key, value in entry.items() if key != "carrier_ref"}
        try:
            carrier = host.validate_carrier(body)
        except host.CarrierError as exc:
            # A payload the host refuses is not a carrier. It is counted and kept in the record --
            # a materialization that emits mostly malformed bodies is a result about the generator,
            # not a reason to generate again.
            refused.append({"index": index, "carrier_ref": expected_id, "reason": str(exc)})
            continue
        carrier["carrier_ref"] = expected_id
        signature = host.structural_signature(carrier)
        signatures[signature] = signatures.get(signature, 0) + 1
        decoded.append(carrier)

    return {
        "schema": "m113-carrier-bank-acceptance-v1",
        "development": bool(development),
        "records_emitted": len(list(raw)),
        "carriers_enveloped": len(list(raw)),
        "schema_valid_carriers": len(decoded),
        "refused_carriers": refused,
        "distinct_structural_signatures": len(signatures),
        "repeated_structural_signatures": sorted(
            key for key, count in signatures.items() if count > 1
        ),
        "carrier_digests": [item["carrier_digest"] for item in decoded],
        "payload_sha256": sha256_hex(canonical_bytes(payload)),
        "carriers": decoded,
    }


# ----------------------------------------------------------------------------------------
# The analysis plan, frozen before the bank is generated.
# ----------------------------------------------------------------------------------------


def analysis_plan_commitment(plan: Mapping[str, Any]) -> str:
    return sha256_hex(
        canonical_bytes({k: v for k, v in plan.items() if k != "plan_commitment_sha256"})
    )


def validate_analysis_plan(plan: Mapping[str, Any]) -> None:
    """The scoring rule, and the honesty condition that it must be able to fail.

    M086-A recorded a positive verdict against a threshold that could never fail; the mirror defect
    is a threshold that could never pass. Both are refused here by deriving, from a rate measured
    over a large devkit sample under this very meta-schema, whether the declared minimum is
    *reachable* and *refusable* at the requested bank size.

    The devkit's distribution is emphatically not the model's -- M112 measured six per cent over its
    own worlds and the blind bank returned twenty-five -- so the measured rate is used only to
    establish that a plausible emitter can both meet and miss the minimum. It is not a prediction and
    the plan may not be read as one.
    """
    if not isinstance(plan, Mapping) or plan.get("schema") != ANALYSIS_PLAN_SCHEMA:
        raise CarrierBankError("analysis plan schema is not the declared one")
    for key in ("requested_carrier_count", "minimum_qualifying_carriers"):
        value = plan.get(key)
        if not isinstance(value, int) or value <= 0:
            raise CarrierBankError("analysis plan field %s is not a positive integer" % key)

    rate = plan.get("measured_qualification_rate")
    if not isinstance(rate, (int, float)) or not 0.0 < float(rate) < 1.0:
        raise CarrierBankError("analysis plan declares no measured qualification rate")
    measured_over = plan.get("measured_over_carriers")
    if not isinstance(measured_over, int) or measured_over < 100:
        raise CarrierBankError(
            "a qualification rate measured over fewer than a hundred carriers cannot support a "
            "minimum"
        )

    requested = int(plan["requested_carrier_count"])
    minimum = int(plan["minimum_qualifying_carriers"])
    expected = requested * float(rate)
    if minimum > expected * 2:
        raise CarrierBankError(
            "the qualifying minimum is unreachable at the measured rate: %d wanted, about %.1f "
            "expected" % (minimum, expected)
        )
    if minimum < 2:
        raise CarrierBankError(
            "a qualifying minimum below two cannot fail on a bank of this size, so it decides "
            "nothing"
        )

    derivation = plan.get("cardinality_derivation")
    if not isinstance(derivation, Mapping):
        raise CarrierBankError("analysis plan declares no cardinality derivation")
    if derivation.get("records_to_carriers") != "identity":
        raise CarrierBankError(
            "the record-to-carrier cardinality must be declared, and must be the identity: M112 "
            "assigned a world count to a record count and bought a fifth of its plan"
        )
    if derivation.get("carriers_to_qualifying") != "measured_after_reveal":
        raise CarrierBankError(
            "how many carriers qualify cannot be an identity and must be declared as measured"
        )

    if plan.get("insufficient_bank_verdict") != "negative":
        raise CarrierBankError(
            "the plan must declare that a bank yielding too few qualifying carriers is a negative "
            "result, not a retry"
        )
    if plan.get("retries_permitted") is not False:
        raise CarrierBankError("the plan must forbid retries")
    if plan.get("qualification_rule") != "m113_evaluator.qualification_report":
        raise CarrierBankError("qualification must use the rule frozen before any carrier existed")
    if plan.get("demand_derivation_rule") != "m113_evaluator.derive_demand_pair":
        raise CarrierBankError("demands must be derived by the frozen rule, never chosen")
    if plan.get("closure_rule") != "exact_fixed_point_no_inherited_bound":
        raise CarrierBankError(
            "the plan must declare closure by exact fixed point: M112's P5 is what an inherited "
            "bound costs"
        )
    if plan.get("claim_boundary") != CARRIER_BANK_CLAIM_BOUNDARY:
        raise CarrierBankError("analysis plan claim boundary drifted")
    if plan.get("evidence_tier") not in EVIDENCE_TIERS:
        raise CarrierBankError("analysis plan evidence tier is outside the declared ladder")
    if plan.get("plan_commitment_sha256") != analysis_plan_commitment(plan):
        raise CarrierBankError("analysis plan commitment drifted")


# ----------------------------------------------------------------------------------------
# The system protocol, frozen after sealing and before reveal.
# ----------------------------------------------------------------------------------------


def system_protocol_commitment(protocol: Mapping[str, Any]) -> str:
    return sha256_hex(
        canonical_bytes({k: v for k, v in protocol.items() if k != "protocol_commitment_sha256"})
    )


def tested_system_digests(root: Path) -> dict[str, str]:
    """Raw working-tree bytes, exactly as every milestone from M100 on binds its apparatus."""
    resolved = Path(root).resolve()
    found: dict[str, str] = {}
    for relative in TESTED_SYSTEM_PATHS:
        path = resolved / relative
        if not path.is_file():
            raise CarrierBankError("tested system member is missing: %s" % relative)
        found[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return found


def validate_system_protocol(protocol: Mapping[str, Any], *, root: Path) -> None:
    if not isinstance(protocol, Mapping) or protocol.get("schema") != SYSTEM_PROTOCOL_SCHEMA:
        raise CarrierBankError("system protocol schema is not the declared one")
    declared = protocol.get("tested_system_digests")
    if not isinstance(declared, Mapping):
        raise CarrierBankError("system protocol declares no tested system digests")
    if sorted(declared) != sorted(TESTED_SYSTEM_PATHS):
        raise CarrierBankError("system protocol does not bind exactly the declared tested system")
    measured = tested_system_digests(root)
    drifted = sorted(key for key in measured if measured[key] != declared.get(key))
    if drifted:
        raise CarrierBankError(
            "the tested system changed after it was frozen: %s" % ", ".join(drifted)
        )
    if protocol.get("tested_system_unmodified_after_reveal") is not True:
        raise CarrierBankError("the system protocol must carry the invariant it exists for")
    if protocol.get("protocol_commitment_sha256") != system_protocol_commitment(protocol):
        raise CarrierBankError("system protocol commitment drifted")


# ----------------------------------------------------------------------------------------
# The phase machine. It never opens a payload, and there is no path here that could.
# ----------------------------------------------------------------------------------------


def _load(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.is_file():
        return None, None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, "%s is unreadable: %s" % (path.name, exc)
    if not isinstance(value, dict):
        return None, "%s is not an object" % path.name
    return value, None


def assess_carrier_bank_readiness(root: Path) -> dict[str, Any]:
    """Report the phase and every reason a reveal is not authorized.

    An absent artifact, a malformed one and a drifted one are all blockers. There is no code path
    here that opens, decrypts or lists bank content, and the report never names a carrier.
    """
    resolved = Path(root).resolve()
    blockers: list[str] = []
    phase = "draft"

    plan, error = _load(resolved / ANALYSIS_PLAN_PATH)
    if error:
        blockers.append(error)
    elif plan is None:
        blockers.append("missing %s" % ANALYSIS_PLAN_PATH.name)
    else:
        try:
            validate_analysis_plan(plan)
        except CarrierBankError as exc:
            blockers.append("analysis plan: %s" % exc)
            plan = None

    survey_present = (resolved / DEVKIT_SURVEY_PATH).is_file()
    if not survey_present:
        blockers.append("missing %s" % DEVKIT_SURVEY_PATH.name)
    spec_present = (resolved / GENERATOR_SPEC_PATH).is_file()
    prompt_present = (resolved / GENERATOR_PROMPT_PATH).is_file()
    schema_present = (resolved / OUTPUT_SCHEMA_PATH).is_file()
    if not spec_present:
        blockers.append("missing %s" % GENERATOR_SPEC_PATH.name)
    if not prompt_present:
        blockers.append("missing %s" % GENERATOR_PROMPT_PATH.name)
    if not schema_present:
        blockers.append("missing %s" % OUTPUT_SCHEMA_PATH.name)
    if plan is not None and survey_present and spec_present and prompt_present and schema_present:
        phase = "spec_frozen"

    commitment, error = _load(resolved / BANK_COMMITMENT_PATH)
    if error:
        blockers.append(error)
    elif commitment is None:
        blockers.append("missing %s" % BANK_COMMITMENT_PATH.name)
    elif phase == "spec_frozen":
        phase = "generated_sealed"

    protocol, error = _load(resolved / SYSTEM_PROTOCOL_PATH)
    if error:
        blockers.append(error)
    elif protocol is None:
        blockers.append("missing %s" % SYSTEM_PROTOCOL_PATH.name)
    else:
        try:
            validate_system_protocol(protocol, root=resolved)
        except CarrierBankError as exc:
            blockers.append("system protocol: %s" % exc)
        else:
            if phase == "generated_sealed":
                phase = "system_protocol_frozen"

    authorization, error = _load(resolved / REVEAL_AUTHORIZATION_PATH)
    if error:
        blockers.append(error)
    elif authorization is None:
        blockers.append("missing %s" % REVEAL_AUTHORIZATION_PATH.name)
    elif phase == "system_protocol_frozen":
        phase = "reveal_authorized"

    revealed = (resolved / RESULT_PATH).is_file()
    if revealed and phase == "reveal_authorized":
        phase = "executed"

    return {
        "schema": REPORT_SCHEMA,
        "milestone": MILESTONE,
        "contract_version": CONTRACT_VERSION,
        "carrier_schema_version": CARRIER_SCHEMA_VERSION,
        "phase": phase,
        "phase_ladder": list(PHASES),
        "ready_for_reveal": phase == "reveal_authorized" and not blockers,
        "revealed": bool(revealed),
        "blockers": sorted(set(blockers)),
        "claim_boundary": dict(CARRIER_BANK_CLAIM_BOUNDARY),
        "tested_system_paths": list(TESTED_SYSTEM_PATHS),
        "evaluator_outside_the_mutable_body": True,
        "payload_never_opened_by_this_assessor": True,
    }


__all__ = [
    "ANALYSIS_PLAN_SCHEMA",
    "CARRIER_BANK_CLAIM_BOUNDARY",
    "CARRIER_PAYLOAD_SCHEMA",
    "CarrierBankError",
    "DEVELOPMENT_PAYLOAD_SCHEMA",
    "MILESTONE",
    "REPORT_SCHEMA",
    "SURVEY_SCHEMA",
    "SYSTEM_PROTOCOL_SCHEMA",
    "TESTED_SYSTEM_PATHS",
    "analysis_plan_commitment",
    "assess_carrier_bank_readiness",
    "evaluator",
    "system_protocol_commitment",
    "tested_system_digests",
    "validate_analysis_plan",
    "validate_carrier_bank_payload",
    "validate_system_protocol",
]
