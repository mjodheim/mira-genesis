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
    BlindBankError,
    canonical_bytes,
    contamination_hits,
    opaque_domain_id,
    sha256_hex,
    validate_generation_ledger,
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
# The prompt with `N` substituted, and nothing else. It is the generator's sole input, so it
# is bound by its own digest rather than reconstructed at invocation time from a template and
# a number that could differ from the frozen one.
QUALIFYING_INPUT_PATH = EXPERIMENT_DIRECTORY / "QUALIFYING_INPUT.txt"
GENERATOR_SPEC_CANDIDATE_PATH = EXPERIMENT_DIRECTORY / "GENERATOR_SPEC_CANDIDATE.json"
SEALED_BANK_PATH = EXPERIMENT_DIRECTORY / "SEALED_BANK.json.gpg"
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

# How each member's bytes are reduced before hashing, declared per member rather than assumed.
#
# M110 and M111 established this and the reason is not stylistic. A raw-byte digest binds the bytes
# a *particular checkout* produced, so a member that no attributes file pins to LF hashes one way on
# a POSIX clone and another on a Windows one, and the freeze stops being verifiable by anyone else.
# Five of the members above -- `m107_runtime.py` through `m111_runtime.py` -- belong to frozen
# milestones and are pinned by no attributes file this milestone may extend; four of them are CRLF
# in this working tree right now. Declaring `lf_normalized` for every source member removes the
# dependence without touching a byte any predecessor owns.
TESTED_SYSTEM_DIGEST_MODES = {path: "lf_normalized" for path in TESTED_SYSTEM_PATHS}

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
    if derivation.get("qualifying_to_distinct_structures") != "measured_after_reveal":
        raise CarrierBankError(
            "how many of the qualifying carriers are distinct machines rather than renamings of "
            "one another cannot be an identity and must be declared as measured: a bank of "
            "renamings satisfies every count above it while presenting fewer machines than it "
            "counts"
        )

    distinct_minimum = plan.get("minimum_distinct_qualifying_structures")
    if not isinstance(distinct_minimum, int) or distinct_minimum < 2:
        raise CarrierBankError(
            "the plan must declare a minimum over distinct qualifying structures, and a minimum "
            "below two cannot fail"
        )
    if distinct_minimum > minimum:
        raise CarrierBankError(
            "the distinct-structure minimum cannot exceed the carrier minimum: every distinct "
            "structure is a qualifying carrier, so such a plan could never pass"
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
    """Working-tree bytes under each member's declared digest mode, as M110 and M111 bind theirs.

    An undeclared mode is refused rather than defaulted. M110 recorded why: a default is a decision
    nobody made, and the decision here is which bytes a third party has to reproduce.
    """
    resolved = Path(root).resolve()
    found: dict[str, str] = {}
    for relative in TESTED_SYSTEM_PATHS:
        path = resolved / relative
        if not path.is_file():
            raise CarrierBankError("tested system member is missing: %s" % relative)
        raw = path.read_bytes()
        mode = TESTED_SYSTEM_DIGEST_MODES.get(relative)
        if mode == "lf_normalized":
            raw = raw.replace(bytes((13, 10)), bytes((10,)))
        elif mode != "raw":
            raise CarrierBankError("tested system member has no declared digest mode: %s" % relative)
        found[relative] = hashlib.sha256(raw).hexdigest()
    return found


def validate_system_protocol(protocol: Mapping[str, Any], *, root: Path) -> None:
    if not isinstance(protocol, Mapping) or protocol.get("schema") != SYSTEM_PROTOCOL_SCHEMA:
        raise CarrierBankError("system protocol schema is not the declared one")
    declared = protocol.get("tested_system_digests")
    if not isinstance(declared, Mapping):
        raise CarrierBankError("system protocol declares no tested system digests")
    if sorted(declared) != sorted(TESTED_SYSTEM_PATHS):
        raise CarrierBankError("system protocol does not bind exactly the declared tested system")
    modes = protocol.get("tested_system_digest_modes")
    if modes != TESTED_SYSTEM_DIGEST_MODES:
        raise CarrierBankError(
            "the system protocol must carry the digest mode of every member it binds, or the "
            "digests it names are the bytes of one checkout rather than of the system"
        )
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
# The generator spec, frozen before the single invocation exists.
# ----------------------------------------------------------------------------------------

GENERATOR_SPEC_SCHEMA = "m113-carrier-bank-generator-spec-v1"

# A model name that names a moving target rather than a fixed one. M112's generator was a blob
# digest in a pinned image, so its identity could not drift underneath the experiment. A hosted
# model has no blob to digest, and the only thing standing in for one is an identifier that the
# provider promises not to repoint. An alias is exactly the identifier that carries no such
# promise, so a spec naming one is refused before it can be frozen rather than after the bank
# turns out to have come from something else.
FORBIDDEN_MODEL_MARKERS = (
    ":auto",
    ":free",
    ":latest",
    "auto-router",
    "auto_router",
    "/auto",
    "openrouter/auto",
)

TRANSPORTS = ("hermes", "http_direct")

# Every layer that can turn one logical call into several physical ones. The spec must name each
# and disable it. The list is written out rather than summarised because "retries are off" is the
# kind of claim that is true of the layer the author was thinking about and false of one they were
# not, and M112's contract exists because a hidden second attempt is indistinguishable afterwards
# from a first one that went well.
RETRY_LAYERS = (
    "client_library",
    "http_transport",
    "invalid_output",
    "provider_side_application_retry",
    "rate_limit_429",
    "server_error_5xx",
    "timeout",
    "truncated_output",
)


def generator_spec_commitment(spec: Mapping[str, Any]) -> str:
    return sha256_hex(
        canonical_bytes({k: v for k, v in spec.items() if k != "spec_commitment_sha256"})
    )


def _digest_of_file(root: Path, relative: str) -> str:
    return sha256_hex(Path(root).joinpath(relative).read_bytes())


def validate_generator_spec(
    spec: Mapping[str, Any],
    *,
    root: Path | None = None,
    plan_commitment_sha256: str | None = None,
) -> None:
    """Everything about the generator that must be fixed before it is allowed to produce a carrier.

    M112 froze a container image digest, a model blob digest and a runtime version, and could
    therefore say afterwards exactly what had emitted its bank. A hosted model offers none of
    those. What it offers instead is an identifier, a provider, and a set of routing switches that
    decide whether the request you froze is the request that gets served -- so those are what this
    contract pins, and it refuses every shape in which the served identity could differ from the
    frozen one:

    * an **alias** for a model, which is an identifier whose whole purpose is to be repointed;
    * a **provider left open**, so the host chooses the backend and the bank's origin is whichever
      machine happened to be free;
    * **fallbacks**, of model or of provider, which are a silent substitution by design;
    * **retries** at any of the layers that can each turn one logical call into several physical
      ones, because several physical requests presented afterwards as one invocation is the exact
      thing the no-retry rule exists to prevent.

    Two honesty conditions have no analogue in M112 and are enforced here because a remote
    generator invites both errors. A seed is recorded as *requested* and never as a guarantee: a
    provider that does not promise determinism does not acquire it by being asked. And no secret
    may appear anywhere in the spec, including inside the canonical request body it records, which
    is checked rather than trusted -- the body is what gets digested and published, and a key that
    reached it would be published with it.
    """
    if not isinstance(spec, Mapping) or spec.get("schema") != GENERATOR_SPEC_SCHEMA:
        raise CarrierBankError("generator spec schema is not the declared one")
    if spec.get("milestone") != MILESTONE:
        raise CarrierBankError("generator spec does not belong to this milestone")
    if spec.get("frozen_before_generation") is not True:
        raise CarrierBankError("a generator spec that is not frozen before generation is not one")

    # -- the identity that must be served ------------------------------------------------
    identity = spec.get("generator_identity")
    if not isinstance(identity, Mapping):
        raise CarrierBankError("generator spec declares no generator identity")

    transport = identity.get("transport")
    if transport not in TRANSPORTS:
        raise CarrierBankError("generator transport must be one of %s" % (TRANSPORTS,))
    if transport == "hermes":
        for key in ("hermes_version", "hermes_config_sha256"):
            if not isinstance(identity.get(key), str) or not identity.get(key):
                raise CarrierBankError(
                    "a Hermes transport must record %s, or what ran cannot be identified" % key
                )
    endpoint = identity.get("endpoint")
    if not isinstance(endpoint, str) or not endpoint.startswith("https://"):
        raise CarrierBankError("generator endpoint must be a declared https endpoint")

    model = identity.get("model")
    if not isinstance(model, str) or not model:
        raise CarrierBankError("generator spec declares no exact model")
    lowered = model.casefold()
    marker = next((item for item in FORBIDDEN_MODEL_MARKERS if item in lowered), None)
    if marker is not None:
        raise CarrierBankError(
            "the model identifier contains %r, which names a moving target rather than a fixed "
            "one; a bank's generator must be identifiable afterwards" % marker
        )
    if identity.get("model_identity_confirmed_against_the_api") is not True:
        raise CarrierBankError(
            "the exact model identifier must be confirmed against the provider's own catalogue "
            "before it is frozen, not assumed from how such identifiers are usually spelled"
        )

    provider = identity.get("provider")
    if not isinstance(provider, str) or not provider:
        raise CarrierBankError(
            "the provider must be one concrete backend chosen before the freeze: an unset provider "
            "means the host picks, and the bank's origin is then whichever machine was free"
        )
    if identity.get("provider_serves_the_model_confirmed") is not True:
        raise CarrierBankError(
            "the chosen provider must be confirmed to serve the exact model, by discovery rather "
            "than by assumption"
        )

    # What weights actually ran, to the extent a hosted provider lets that be known.
    #
    # M112 froze a model blob digest, so it could say afterwards exactly which weights emitted its
    # bank. A hosted model offers no blob. The nearest thing is the provider's declared
    # quantization: `deepseek-v4-flash-0731` served at fp4 and at bf16 is not the same computation
    # under one name. So the quantization is pinned -- and pinned with its epistemic status
    # attached, because OpenRouter reports it in the provider catalogue and *not* in the completion
    # response. It is a property this project read at discovery time and cannot re-verify from the
    # served answer, and a spec that claimed otherwise would be claiming more than the instrument
    # supports.
    if not isinstance(identity.get("quantization"), str) or not identity.get("quantization"):
        raise CarrierBankError(
            "the provider's declared quantization must be pinned: it is the nearest thing a hosted "
            "generator has to the weight digest M112 could freeze"
        )
    if identity.get("quantization_source") != "provider_discovery_catalogue":
        raise CarrierBankError(
            "the quantization must record where it was read from, and the only place it is "
            "available is the provider discovery catalogue"
        )
    if identity.get("quantization_is_runtime_attested") is not False:
        raise CarrierBankError(
            "the completion response does not carry a quantization, so it may not be recorded as "
            "attested at serve time; a discovery-bound property is not a verified one"
        )

    # -- how this provider came to be the one --------------------------------------------
    #
    # The rule this milestone declared before any data adopts a provider only when exactly one can
    # serve the frozen request. When discovery returns several, the choice is a judgement, and a
    # judgement is only admissible here if the record says plainly when it was formed and what it
    # could not have been formed from. So a spec that selected among several candidates has to
    # carry its criterion, the moment it was written relative to every gate, and the statement that
    # no result of the hypothesis under test could have informed it.
    selection = spec.get("provider_selection")
    if not isinstance(selection, Mapping):
        raise CarrierBankError(
            "a spec whose provider was chosen among several candidates must record the criterion "
            "that chose it"
        )
    if not isinstance(selection.get("criterion"), str) or not selection["criterion"].strip():
        raise CarrierBankError("the provider selection criterion must be stated, not implied")
    if selection.get("selected") != provider:
        raise CarrierBankError(
            "the recorded selection does not name the provider the spec pins"
        )
    candidates = selection.get("candidates_considered")
    if not isinstance(candidates, list) or provider not in candidates:
        raise CarrierBankError(
            "the candidates the criterion was applied to must be recorded, and must include the "
            "one it selected"
        )
    for key in (
        "formulated_before_any_bank_existed",
        "formulated_before_generator_freeze",
        "formulated_before_smoke_with_the_final_identity",
        "formulated_before_the_qualifying_invocation",
    ):
        if selection.get(key) is not True:
            raise CarrierBankError(
                "the criterion must be recorded as formed before %s; a criterion formed later is "
                "a result-shaped choice" % key.replace("formulated_before_", "").replace("_", " ")
            )
    if selection.get("depends_on_any_h58_result") is not False:
        raise CarrierBankError(
            "a provider criterion that depends on a result of the hypothesis under test is not a "
            "criterion, it is an outcome being selected for"
        )
    if not isinstance(selection.get("formulated_after_observing_the_provider_catalogue"), bool):
        raise CarrierBankError(
            "whether the criterion was formed before or after the catalogue was seen must be "
            "recorded either way; silence on it is the part a reader cannot check"
        )

    # -- routing: nothing may be substituted for what was frozen -------------------------
    routing = spec.get("routing")
    if not isinstance(routing, Mapping):
        raise CarrierBankError("generator spec declares no routing policy")
    if routing.get("allow_fallbacks") is not False:
        raise CarrierBankError("fallbacks must be disabled: a fallback is a silent substitution")
    if routing.get("automatic_routing") is not False:
        raise CarrierBankError("automatic routing must be disabled")
    for key in ("model_fallbacks", "provider_fallbacks"):
        value = routing.get(key)
        if value != []:
            raise CarrierBankError("%s must be declared and empty" % key)
    if not isinstance(routing.get("require_parameters"), bool) and routing.get(
        "require_parameters"
    ) is not None:
        raise CarrierBankError(
            "require_parameters must be declared as a boolean, or as null when the contract does "
            "not support it -- silence is not a declaration"
        )
    if routing.get("a_provider_that_cannot_serve_the_frozen_request_is_an_instrument_failure")             is not True:
        raise CarrierBankError(
            "the spec must declare that an unservable frozen request fails the instrument rather "
            "than moving to another provider"
        )

    # -- exactly one physical invocation --------------------------------------------------
    policy = spec.get("invocation_policy")
    if not isinstance(policy, Mapping):
        raise CarrierBankError("generator spec declares no invocation policy")
    if policy.get("qualifying_invocations_permitted") != 1:
        raise CarrierBankError("exactly one qualifying invocation is permitted")
    for key in (
        "retries_permitted",
        "manual_correction_permitted",
        "selection_among_outputs_permitted",
        "repair_parsing_permitted",
        "second_request_to_correct_the_output_permitted",
    ):
        if policy.get(key) is not False:
            raise CarrierBankError("invocation policy must declare %s false" % key)
    if policy.get("invalid_output_is_the_result_of_the_single_invocation") is not True:
        raise CarrierBankError(
            "the spec must declare that a non-conforming output is the result, not a reason to ask "
            "again"
        )
    disabled = policy.get("retries_disabled_at")
    if not isinstance(disabled, list) or sorted(str(item) for item in disabled) != sorted(
        RETRY_LAYERS
    ):
        raise CarrierBankError(
            "every retry layer must be named and disabled: %s" % ", ".join(sorted(RETRY_LAYERS))
        )
    if policy.get("an_undetected_automatic_retry_fails_closed") is not True:
        raise CarrierBankError(
            "the spec must declare what happens if a layer retries anyway, or the no-retry rule is "
            "a hope rather than a protocol"
        )

    # -- blindness ------------------------------------------------------------------------
    blindness = spec.get("blindness_contract")
    if not isinstance(blindness, Mapping):
        raise CarrierBankError("generator spec declares no blindness contract")
    required_absent = (
        "conversation_history",
        "genesis_files",
        "hypothesis_information",
        "mcp",
        "memory",
        "milestone_information",
        "qualification_criteria",
        "rag",
        "repository",
        "shell_or_tool_calls",
        "summarization",
        "system_prompt_context",
        "tools",
        "web_search",
    )
    absent = blindness.get("absent")
    if not isinstance(absent, list) or sorted(str(item) for item in absent) != sorted(
        required_absent
    ):
        raise CarrierBankError(
            "the blindness contract must name every channel that is absent: %s"
            % ", ".join(sorted(required_absent))
        )
    if blindness.get("audited_before_the_freeze") is not True:
        raise CarrierBankError("the blindness contract must be audited rather than asserted")
    if blindness.get("the_model_receives_only_the_qualifying_input_and_the_schema") is not True:
        raise CarrierBankError("the spec must declare what the model does receive, not only what it does not")

    # -- sampling, and one honesty condition about seeds ----------------------------------
    sampling = spec.get("sampling")
    if not isinstance(sampling, Mapping):
        raise CarrierBankError("generator spec declares no sampling parameters")
    if sampling.get("declared_before_generation") is not True:
        raise CarrierBankError("sampling parameters must be declared before generation")
    if not isinstance(sampling.get("temperature"), (int, float)):
        raise CarrierBankError("sampling must declare a temperature")
    if not isinstance(sampling.get("max_output_tokens"), int) or sampling["max_output_tokens"] <= 0:
        raise CarrierBankError("sampling must declare a positive output bound")
    if "seed" not in sampling or "seed_is_honoured_by_the_provider" not in sampling:
        raise CarrierBankError("a seed must be declared, together with whether it is honoured")
    if sampling.get("seed") is not None and sampling.get("seed_is_honoured_by_the_provider") not in (
        True,
        False,
    ):
        raise CarrierBankError(
            "whether the provider honours the seed must be recorded as measured or as unknown, and "
            "a seed a provider does not guarantee does not make a hosted model reproducible"
        )
    if sampling.get("determinism_is_claimed") is not False:
        raise CarrierBankError(
            "a hosted generator may not claim determinism; record what is actually guaranteed"
        )
    if not isinstance(sampling.get("every_parameter_sent"), Mapping):
        raise CarrierBankError(
            "the spec must record every sampling parameter actually sent, not only the ones worth "
            "mentioning"
        )
    if "reasoning" not in sampling:
        raise CarrierBankError(
            "reasoning or thinking parameters must be declared, as null when there are none"
        )

    # -- structured output ----------------------------------------------------------------
    structured = spec.get("structured_output")
    if not isinstance(structured, Mapping):
        raise CarrierBankError("generator spec declares no structured output configuration")
    if structured.get("mode") != "json_schema":
        raise CarrierBankError(
            "the frozen JSON schema is the contract and may not be replaced by an instruction in "
            "prose"
        )
    if structured.get("strict") is not True:
        raise CarrierBankError("structured output must be strict")
    if structured.get("schema_path") != str(OUTPUT_SCHEMA_PATH).replace("\\", "/"):
        raise CarrierBankError("structured output must bind this milestone's own schema")

    # -- what the generator is given, bound by digest -------------------------------------
    for key, path in (
        ("output_schema", OUTPUT_SCHEMA_PATH),
        ("prompt", GENERATOR_PROMPT_PATH),
        ("qualifying_input", QUALIFYING_INPUT_PATH),
    ):
        record = spec.get(key)
        if not isinstance(record, Mapping):
            raise CarrierBankError("generator spec declares no %s" % key)
        declared_digest = record.get("sha256")
        if not isinstance(declared_digest, str) or len(declared_digest) != 64:
            raise CarrierBankError("%s is not bound by a digest" % key)
        if record.get("path") != str(path).replace("\\", "/"):
            raise CarrierBankError("%s does not name this milestone's own file" % key)
        if root is not None:
            measured = _digest_of_file(root, record["path"])
            if measured != declared_digest:
                raise CarrierBankError("%s digest does not match the file it names" % key)

    if spec.get("requested_carrier_count") != 24:
        raise CarrierBankError("the generator spec must request the frozen carrier count")

    # -- the request that will actually be sent, secret-free ------------------------------
    request = spec.get("canonical_request_body")
    if not isinstance(request, Mapping):
        raise CarrierBankError("generator spec records no canonical request body")
    if spec.get("canonical_request_body_sha256") != sha256_hex(canonical_bytes(request)):
        raise CarrierBankError("the canonical request body digest does not match the body")
    if contamination_hits(canonical_bytes(request).decode("utf-8")):
        raise CarrierBankError("the canonical request body carries project context")
    _refuse_secret_material(spec)

    # -- provenance and boundary ------------------------------------------------------------
    if plan_commitment_sha256 is not None:
        if spec.get("analysis_plan_commitment_sha256") != plan_commitment_sha256:
            raise CarrierBankError(
                "the generator spec does not bind the frozen analysis plan, so it could have been "
                "written for a different set of rules"
            )
    boundary = spec.get("claim_boundary")
    if not isinstance(boundary, Mapping):
        raise CarrierBankError("generator spec declares no claim boundary")
    for key in ("human_independence", "external_reproduction", "agi"):
        if boundary.get(key) is not False:
            raise CarrierBankError("the claim boundary may not claim %s" % key)

    if spec.get("spec_commitment_sha256") != generator_spec_commitment(spec):
        raise CarrierBankError("generator spec commitment drifted")


# A key is a secret and this spec is published, so credential material is refused wherever it
# appears rather than trusted to have been kept out.
#
# The names are matched exactly, and that precision is not fussiness. A first version matched any
# key ending in `_key` or `_token` and refused the carrier meta-schema itself, because a carrier's
# wire surface has an `action_key`, an `argument_key`, a `status_key`, an `ok_token` and an
# `error_token`. A guard that fires on the thing it is protecting gets switched off, so it names
# the credentials instead of guessing at them.
SECRET_BEARING_KEYS = frozenset({
    "access_token",
    "api-key",
    "api_key",
    "apikey",
    "auth",
    "auth_token",
    "authorization",
    "bearer",
    "credential",
    "credentials",
    "openrouter_api_key",
    "passwd",
    "password",
    "private_key",
    "refresh_token",
    "secret",
    "secret_key",
    "session_token",
})
SECRET_VALUE_PREFIXES = ("sk-", "sk_", "or-", "or_v1-", "hf_", "gsk_")


def _refuse_secret_material(value: Any, path: str = "spec") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).casefold() in SECRET_BEARING_KEYS:
                raise CarrierBankError(
                    "%s.%s names credential material, which may never enter a published artifact; "
                    "reference the environment variable instead" % (path, key)
                )
            _refuse_secret_material(item, "%s.%s" % (path, key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _refuse_secret_material(item, "%s[%d]" % (path, index))
    elif isinstance(value, str):
        stripped = value.strip()
        if any(stripped.startswith(prefix) for prefix in SECRET_VALUE_PREFIXES) and len(
            stripped
        ) > 16:
            raise CarrierBankError("%s carries something shaped like a credential" % path)


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
    else:
        # Presence was the whole check here, which made the spec a file rather than a contract.
        # The ledger binds to `spec_commitment_sha256`, so an unvalidated spec would let a ledger
        # bind to a commitment nothing had checked.
        spec_document, spec_error = _load(resolved / GENERATOR_SPEC_PATH)
        if spec_error:
            blockers.append(spec_error)
        elif spec_document is None:
            blockers.append("missing %s" % GENERATOR_SPEC_PATH.name)
        else:
            try:
                validate_generator_spec(
                    spec_document,
                    root=resolved,
                    plan_commitment_sha256=(
                        plan.get("plan_commitment_sha256") if plan is not None else None
                    ),
                )
            except CarrierBankError as exc:
                blockers.append("generator spec: %s" % exc)
    if not prompt_present:
        blockers.append("missing %s" % GENERATOR_PROMPT_PATH.name)
    if not schema_present:
        blockers.append("missing %s" % OUTPUT_SCHEMA_PATH.name)
    if plan is not None and survey_present and spec_present and prompt_present and schema_present:
        phase = "spec_frozen"

    # The generator phase's own record. M113 declared GENERATION_LEDGER_PATH and then never read
    # it, so nothing counted the physical invocations that produced the bank -- and "one qualifying
    # invocation, no retries" was a promise rather than a checked fact. M112 carried the ledger and
    # M113 dropped it. The shared contract is what refuses a second materialization and what keeps
    # every failed attempt visible, so several physical requests cannot be presented afterwards as
    # one logical invocation.
    ledger, error = _load(resolved / GENERATION_LEDGER_PATH)
    ledger_valid = False
    if error:
        blockers.append(error)
    elif ledger is None:
        blockers.append("missing %s" % GENERATION_LEDGER_PATH.name)
    else:
        spec_commitment = None
        spec, spec_error = _load(resolved / GENERATOR_SPEC_PATH)
        if spec is not None and not spec_error:
            declared = spec.get("spec_commitment_sha256")
            if isinstance(declared, str) and declared:
                spec_commitment = declared
        try:
            validate_generation_ledger(ledger, spec_commitment_sha256=spec_commitment)
        except BlindBankError as exc:
            blockers.append("generation ledger: %s" % exc)
        else:
            if spec_commitment is None:
                blockers.append(
                    "the generator spec declares no commitment for the ledger to bind, so the "
                    "ledger cannot be shown to be this bank's"
                )
            else:
                ledger_valid = True

    commitment, error = _load(resolved / BANK_COMMITMENT_PATH)
    if error:
        blockers.append(error)
    elif commitment is None:
        blockers.append("missing %s" % BANK_COMMITMENT_PATH.name)
    elif phase == "spec_frozen" and ledger_valid:
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
    "FORBIDDEN_MODEL_MARKERS",
    "GENERATOR_SPEC_SCHEMA",
    "MILESTONE",
    "RETRY_LAYERS",
    "REPORT_SCHEMA",
    "SURVEY_SCHEMA",
    "SYSTEM_PROTOCOL_SCHEMA",
    "TESTED_SYSTEM_DIGEST_MODES",
    "TESTED_SYSTEM_PATHS",
    "analysis_plan_commitment",
    "assess_carrier_bank_readiness",
    "evaluator",
    "generator_spec_commitment",
    "system_protocol_commitment",
    "tested_system_digests",
    "validate_analysis_plan",
    "validate_carrier_bank_payload",
    "validate_generator_spec",
    "validate_system_protocol",
]
