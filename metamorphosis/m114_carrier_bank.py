"""M114: the M113 mechanism, unchanged, behind a corrected delivery instrument.

M113 is closed. It froze a generator identity, made one physical request, received HTTP 429,
materialized no bank and left H58 untested. It is an instrument failure, it is not re-frozen, and
nothing here repairs, reinterprets or completes it.

M114 asks the same scientific question under H59 — the register carries one hypothesis per
milestone, and M106 established that a corrective replication takes a new number rather than
inheriting its predecessor's, so that the predecessor's record stays exactly as it was.

**What is imported unchanged, and is therefore not re-litigated here.** The scientific mechanism and
every rule that decides what a carrier is, what qualifies, and what the verdict means:

    carrier_host             the reception contract
    m113_evaluator           qualification, closure, demand derivation, scoring
    m113_runtime             the learner
    m113_carrier_bank        the analysis-plan, generator-spec, payload and system-protocol
                             contracts, imported by reference rather than copied

Importing rather than copying is what makes "the mechanism is unchanged" a checkable statement
instead of a claim about two files that happen to look alike. A copy drifts; an import cannot.

**What M114 changes, and it is only this.** M113's protocol used one predicate, "one physical
request", for two different quantities: how many times the instrument may *reach* for the generator,
and how many times the generator may *produce* a bank. Those coincide only while the network
cooperates, and a capacity rejection from a shared upstream pool spent the second budget without
ever spending the first. `m114_delivery` separates them. See that module for the rule and for why
its retry window is as narrow as it is.

The separation was decided **after** M113's instrument failure, **before** any M114 bank existed,
and with **no observation of H58 whatsoever**. It was never part of M113.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from metamorphosis import m113_carrier_bank as mechanism
from metamorphosis import m114_delivery as delivery
from metamorphosis.blind_bank_protocol import PHASES, canonical_bytes, sha256_hex

# ----------------------------------------------------------------------------------------
# Identity, and the filiation the record must carry
# ----------------------------------------------------------------------------------------

MILESTONE = "M114"
HYPOTHESIS = "H59"
CONTRACT_VERSION = mechanism.CONTRACT_VERSION
REPORT_SCHEMA = "m114-carrier-bank-readiness-v1"
ANALYSIS_PLAN_SCHEMA = "m114-carrier-bank-analysis-plan-v1"
GENERATOR_SPEC_SCHEMA = "m114-carrier-bank-generator-spec-v1"

FILIATION = {
    "predecessor": "M113",
    "predecessor_hypothesis": "H58",
    "predecessor_outcome": "instrument-aborted before bank materialization",
    "predecessor_record_is_closed_and_not_repaired": True,
    "this_milestone": "M114",
    "this_hypothesis": HYPOTHESIS,
    "relationship": "corrective replication with transport-capacity semantics preregistered "
                    "before any new generation",
    "scientific_target_is_unchanged": True,
    "delivery_rule_decided_after_m113_instrument_failure": True,
    "delivery_rule_decided_before_any_m114_bank_existed": True,
    "delivery_rule_decided_without_any_observation_of_the_hypothesis": True,
    "delivery_rule_was_never_part_of_m113": True,
}

# ----------------------------------------------------------------------------------------
# Paths. The generator's inputs are M113's, byte for byte.
# ----------------------------------------------------------------------------------------

EXPERIMENT_DIRECTORY = Path("experiments/M114")
ANALYSIS_PLAN_PATH = EXPERIMENT_DIRECTORY / "ANALYSIS_PLAN.json"
ANALYSIS_PLAN_CANDIDATE_PATH = EXPERIMENT_DIRECTORY / "ANALYSIS_PLAN_CANDIDATE.json"
GENERATOR_SPEC_PATH = EXPERIMENT_DIRECTORY / "GENERATOR_SPEC.json"
GENERATOR_SPEC_CANDIDATE_PATH = EXPERIMENT_DIRECTORY / "GENERATOR_SPEC_CANDIDATE.json"
GENERATOR_PROMPT_PATH = EXPERIMENT_DIRECTORY / "GENERATOR_PROMPT.txt"
QUALIFYING_INPUT_PATH = EXPERIMENT_DIRECTORY / "QUALIFYING_INPUT.txt"
OUTPUT_SCHEMA_PATH = EXPERIMENT_DIRECTORY / "OUTPUT_SCHEMA.json"
DELIVERY_LEDGER_PATH = EXPERIMENT_DIRECTORY / "DELIVERY_LEDGER.json"
BANK_COMMITMENT_PATH = EXPERIMENT_DIRECTORY / "PUBLIC_BANK_COMMITMENT.json"
SYSTEM_PROTOCOL_PATH = EXPERIMENT_DIRECTORY / "SYSTEM_PROTOCOL.json"
REVEAL_AUTHORIZATION_PATH = EXPERIMENT_DIRECTORY / "REVEAL_AUTHORIZATION.json"
SEALED_BANK_PATH = EXPERIMENT_DIRECTORY / "SEALED_BANK.json.gpg"
RESULT_PATH = EXPERIMENT_DIRECTORY / "RESULT.json"

# The three files the generator sees. M114 changes none of them, and the digests are pinned here
# so that "the prompt, the schema and the input are M113's" is checked rather than asserted.
GENERATOR_INPUT_DIGESTS = {
    "GENERATOR_PROMPT.txt":
        "f79fb18cde53e0efd4b1defef43460589376c0d3e93ff0eb2443836de526269e",
    "QUALIFYING_INPUT.txt":
        "c73721aec1de46b792551c9b16291b69806f21b4181a212b356bcc73e3f592e0",
    "OUTPUT_SCHEMA.json":
        "1020a1db9625f2734be1f548edd4c5af0139cb17732d13fb25913144f9106075",
}


# What is never retried, whatever the delivery budget says. The frozen plan must carry this list
# exactly. Stating it only in a module docstring would leave the enumeration outside the
# commitment, where it could be narrowed later without the plan's digest moving -- and the one
# clause a milestone with three attempts must not be able to quietly narrow is the list of things
# that are final on their first outcome.
NEVER_RETRIED = (
    "any_scientific_outcome_including_p22_false",
    "any_status_other_than_429",
    "connection_lost_in_an_ambiguous_state",
    "insufficient_bank",
    "invalid_json",
    "model_refusal",
    "output_schema_violation",
    "timeout_after_transmission_in_an_unestablished_state",
    "truncated_completion",
)

# ----------------------------------------------------------------------------------------
# The plan. Every scientific rule is M113's; only the schema name and the delivery clause differ.
# ----------------------------------------------------------------------------------------

CarrierBankError = mechanism.CarrierBankError


def _posix(path: Path) -> str:
    """Compare declared paths the way they are written in JSON, on every platform."""
    return str(path).replace("\\", "/")



def analysis_plan_commitment(plan: Mapping[str, Any]) -> str:
    return sha256_hex(
        canonical_bytes({k: v for k, v in plan.items() if k != "plan_commitment_sha256"})
    )


def validate_analysis_plan(plan: Mapping[str, Any]) -> None:
    """M113's plan rules, unchanged, plus the two clauses M114 exists to add.

    The scientific content is delegated rather than restated: hypothesis, carrier count, minima,
    closure rule, qualification rule, selection and correction prohibitions, and the
    insufficient-bank verdict are all checked by `m113_carrier_bank.validate_analysis_plan`, on a
    view of the plan wearing M113's schema name. A rule this milestone re-typed would be a rule it
    could quietly soften.
    """
    if not isinstance(plan, Mapping) or plan.get("schema") != ANALYSIS_PLAN_SCHEMA:
        raise CarrierBankError("analysis plan schema is not the declared one")

    # Delegate the rules, not the bookkeeping. M113's validator also re-checks its own commitment
    # field, which cannot match on a plan carrying M114's added clauses, so the view handed to it
    # carries the commitment *it* would compute. That is not a softening: M114's real commitment is
    # checked at the end of this function, over the real plan, and is the one that binds.
    inherited = dict(plan)
    inherited["schema"] = mechanism.ANALYSIS_PLAN_SCHEMA
    inherited["plan_commitment_sha256"] = mechanism.analysis_plan_commitment(inherited)
    mechanism.validate_analysis_plan(inherited)

    if plan.get("hypothesis") != HYPOTHESIS:
        raise CarrierBankError(
            "M114's plan must name %s. The register carries one hypothesis per milestone, and a "
            "corrective replication takes a new number so its predecessor's record stays as it "
            "was." % HYPOTHESIS
        )
    if plan.get("scientific_target_is_m113s_unchanged") is not True:
        raise CarrierBankError(
            "the plan must declare that the scientific target is unchanged; a corrective "
            "replication that quietly moved the target would be a new experiment"
        )
    if plan.get("delivery_semantics") != "m114-delivery-v1":
        raise CarrierBankError("the plan must declare the delivery semantics it is run under")
    if plan.get("max_delivery_attempts") != delivery.MAX_DELIVERY_ATTEMPTS:
        raise CarrierBankError("the plan's delivery budget differs from the frozen one")
    if plan.get("max_bank_materializations") != delivery.MAX_BANK_MATERIALIZATIONS:
        raise CarrierBankError("a plan permitting more than one bank is not this experiment")
    if plan.get("retry_wait_seconds") != delivery.RETRY_WAIT_SECONDS:
        raise CarrierBankError("the plan's retry interval differs from the frozen one")
    if plan.get("only_capacity_rejection_before_generation_may_be_retried") is not True:
        raise CarrierBankError(
            "the plan must declare the asymmetry the delivery rule rests on: a capacity rejection "
            "before generation may be retried, and anything that may have reached the model may "
            "never be"
        )
    if list(plan.get("never_retried") or ()) != list(NEVER_RETRIED):
        raise CarrierBankError(
            "the plan must enumerate, exactly, what is never retried: %s" % ", ".join(NEVER_RETRIED)
        )
    if plan.get("a_scientific_outcome_is_never_retried") is not True:
        raise CarrierBankError(
            "the plan must declare that no scientific outcome, P22 false included, is ever a "
            "reason to deliver again"
        )
    filiation = plan.get("filiation")
    if not isinstance(filiation, Mapping) or filiation != FILIATION:
        raise CarrierBankError(
            "the plan must carry the M113 filiation exactly, including that the delivery rule was "
            "decided after M113's failure, before any bank, and without observing the hypothesis"
        )
    if plan.get("plan_commitment_sha256") != analysis_plan_commitment(plan):
        raise CarrierBankError("analysis plan commitment drifted")


def validate_generator_spec(
    spec: Mapping[str, Any],
    *,
    root: Path | None = None,
    plan_commitment_sha256: str | None = None,
) -> None:
    """M113's generator contract, unchanged, on an M114 spec.

    Same delegation, same reason. The identity M114 pins is M113's: the same model, the same
    provider, the same declared quantization with the same epistemic status, the same prompt,
    schema and input by digest, the same sampling, the same prohibitions on aliases, open
    providers, fallbacks and routing.
    """
    if not isinstance(spec, Mapping) or spec.get("schema") != GENERATOR_SPEC_SCHEMA:
        raise CarrierBankError("generator spec schema is not the declared one")

    # Same delegation, same reason: M113's validator re-checks its own commitment field, which
    # cannot match a spec carrying M114's schema name and delivery clause. M114's commitment is
    # checked below, over the real spec.
    inherited = dict(spec)
    inherited["schema"] = mechanism.GENERATOR_SPEC_SCHEMA
    inherited["milestone"] = mechanism.MILESTONE

    # The three files the generator sees are M113's byte for byte, but M114 keeps its own copies,
    # and M113's validator compares the declared paths against its own constants. So the view
    # handed to it names M113's copies, and the real spec's paths and digests are checked below
    # against the files actually sitting in `experiments/M114`. The two halves together say more
    # than either alone: the digests the predecessor's validator measures and the digests measured
    # here are the same declared digests, so passing both proves the two copies identical rather
    # than asserting it.
    for key, predecessor_path in (
        ("output_schema", mechanism.OUTPUT_SCHEMA_PATH),
        ("prompt", mechanism.GENERATOR_PROMPT_PATH),
        ("qualifying_input", mechanism.QUALIFYING_INPUT_PATH),
    ):
        record = inherited.get(key)
        if not isinstance(record, Mapping):
            raise CarrierBankError("generator spec declares no %s" % key)
        inherited[key] = dict(record, path=_posix(predecessor_path))
    structured = inherited.get("structured_output")
    if not isinstance(structured, Mapping):
        raise CarrierBankError("generator spec declares no structured output configuration")
    inherited["structured_output"] = dict(
        structured, schema_path=_posix(mechanism.OUTPUT_SCHEMA_PATH)
    )

    inherited["spec_commitment_sha256"] = mechanism.generator_spec_commitment(inherited)
    try:
        mechanism.validate_generator_spec(
            inherited, root=root, plan_commitment_sha256=plan_commitment_sha256
        )
    except OSError as exc:
        # The delegation deliberately points at the predecessor's directory, which a caller's root
        # need not contain. An unreadable file there is a refusal, not a traceback: the phase
        # machine catches `CarrierBankError` and would otherwise crash while reporting a blocker.
        raise CarrierBankError(
            "the predecessor's copy of a generator input cannot be read under this root, so the "
            "two copies cannot be shown identical: %s" % exc
        )

    # M114's own copies, named and measured. Nothing here is a second opinion on a scientific
    # rule; it is the half of the digest binding the delegation cannot perform, because the
    # delegation was pointed at the predecessor's directory.
    if spec["structured_output"].get("schema_path") != _posix(OUTPUT_SCHEMA_PATH):
        raise CarrierBankError("structured output must bind this milestone's own schema")
    for key, path in (
        ("output_schema", OUTPUT_SCHEMA_PATH),
        ("prompt", GENERATOR_PROMPT_PATH),
        ("qualifying_input", QUALIFYING_INPUT_PATH),
    ):
        record = spec[key]
        if record.get("path") != _posix(path):
            raise CarrierBankError("%s does not name this milestone's own file" % key)
        if root is not None:
            try:
                measured = sha256_hex((Path(root).resolve() / record["path"]).read_bytes())
            except OSError as exc:
                raise CarrierBankError("%s names a file that cannot be read: %s" % (key, exc))
            if measured != record.get("sha256"):
                raise CarrierBankError(
                    "%s digest does not match this milestone's own copy of the file" % key
                )

    if spec.get("milestone") != MILESTONE:
        raise CarrierBankError("generator spec does not belong to this milestone")
    if spec.get("delivery_semantics") != "m114-delivery-v1":
        raise CarrierBankError("the generator spec must declare the delivery semantics")
    if spec.get("spec_commitment_sha256") != generator_spec_commitment(spec):
        raise CarrierBankError("generator spec commitment drifted")


def generator_spec_commitment(spec: Mapping[str, Any]) -> str:
    return sha256_hex(
        canonical_bytes({k: v for k, v in spec.items() if k != "spec_commitment_sha256"})
    )


def generator_inputs_are_m113s(root: Path) -> dict[str, bool]:
    """Check, rather than assert, that the generator sees exactly what M113's would have."""
    resolved = Path(root).resolve()
    return {
        name: (resolved / EXPERIMENT_DIRECTORY / name).is_file()
        and sha256_hex((resolved / EXPERIMENT_DIRECTORY / name).read_bytes()) == digest
        for name, digest in GENERATOR_INPUT_DIGESTS.items()
    }


# ----------------------------------------------------------------------------------------
# The phase machine. It never opens a payload.
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
    """Report the phase and every reason a reveal is not authorized."""
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

    inputs = generator_inputs_are_m113s(resolved)
    for name, ok in sorted(inputs.items()):
        if not ok:
            blockers.append(
                "%s is missing or is not M113's byte for byte" % name
            )

    spec, spec_error = _load(resolved / GENERATOR_SPEC_PATH)
    spec_ok = False
    if spec_error:
        blockers.append(spec_error)
    elif spec is None:
        blockers.append("missing %s" % GENERATOR_SPEC_PATH.name)
    else:
        try:
            validate_generator_spec(
                spec,
                root=resolved,
                plan_commitment_sha256=(
                    plan.get("plan_commitment_sha256") if plan is not None else None
                ),
            )
        except CarrierBankError as exc:
            blockers.append("generator spec: %s" % exc)
        else:
            spec_ok = True

    if plan is not None and all(inputs.values()) and spec_ok:
        phase = "spec_frozen"

    # The delivery ledger, which is where M114 differs from its predecessor.
    ledger, error = _load(resolved / DELIVERY_LEDGER_PATH)
    delivery_ok = False
    if error:
        blockers.append(error)
    elif ledger is None:
        blockers.append("missing %s" % DELIVERY_LEDGER_PATH.name)
    else:
        try:
            delivery.validate_delivery_ledger(
                ledger,
                spec_commitment_sha256=(
                    spec.get("spec_commitment_sha256") if spec is not None else None
                ),
                request_body_sha256=(
                    spec.get("canonical_request_body_sha256") if spec is not None else None
                ),
            )
        except delivery.DeliveryError as exc:
            blockers.append("delivery ledger: %s" % exc)
        else:
            if ledger.get("bank_materialization_index") is None:
                blockers.append(
                    "no delivery attempt materialized a bank; the frozen budget of %d attempts "
                    "produced none" % delivery.MAX_DELIVERY_ATTEMPTS
                )
            else:
                delivery_ok = True

    commitment, error = _load(resolved / BANK_COMMITMENT_PATH)
    if error:
        blockers.append(error)
    elif commitment is None:
        blockers.append("missing %s" % BANK_COMMITMENT_PATH.name)
    elif phase == "spec_frozen" and delivery_ok:
        phase = "generated_sealed"

    protocol, error = _load(resolved / SYSTEM_PROTOCOL_PATH)
    if error:
        blockers.append(error)
    elif protocol is None:
        blockers.append("missing %s" % SYSTEM_PROTOCOL_PATH.name)
    else:
        try:
            mechanism.validate_system_protocol(protocol, root=resolved)
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
        "hypothesis": HYPOTHESIS,
        "filiation": dict(FILIATION),
        "contract_version": CONTRACT_VERSION,
        "carrier_schema_version": mechanism.CARRIER_SCHEMA_VERSION,
        "phase": phase,
        "phase_ladder": list(PHASES),
        "ready_for_reveal": phase == "reveal_authorized" and not blockers,
        "revealed": bool(revealed),
        "blockers": sorted(set(blockers)),
        "generator_inputs_are_m113s": inputs,
        "delivery_summary": delivery.delivery_summary(ledger) if ledger else None,
        "claim_boundary": dict(mechanism.CARRIER_BANK_CLAIM_BOUNDARY),
        "tested_system_paths": list(mechanism.TESTED_SYSTEM_PATHS),
    }


__all__ = [
    "ANALYSIS_PLAN_SCHEMA",
    "CarrierBankError",
    "FILIATION",
    "GENERATOR_INPUT_DIGESTS",
    "GENERATOR_SPEC_SCHEMA",
    "HYPOTHESIS",
    "MILESTONE",
    "REPORT_SCHEMA",
    "analysis_plan_commitment",
    "assess_carrier_bank_readiness",
    "generator_inputs_are_m113s",
    "generator_spec_commitment",
    "validate_analysis_plan",
    "validate_generator_spec",
]
