"""M112 - the architecture for receiving a consumer-world bank this project did not author.

M110 and M111 both qualified positively, and both carry the same recorded ceiling: **the project
authored the worlds**. `MIRA_GENERALITY_CRITERIA.md` names it for G4 in as many words —
"independently authored held-out transfer is absent". No further milestone inside this repository
removes it, because the removal is not a piece of code. It is an artifact somebody else has to make.

This module is the receiving end. It binds the milestone-agnostic `mira-blind-bank-v1` contract to
the M110/M111 consumer family, so that a world bank materialized outside the project can be sealed,
committed to by digest, and only then revealed against a system that was frozen first.

**No bank exists.** Nothing here generates one, and nothing here may: the payload schema this file
names must never appear in a tracked file, exactly as the generic contract requires of its own.
The readiness assessor fails closed, and its phase is `draft` until artifacts exist that this
project cannot manufacture on its own.

## What makes the generator blind here, and it is unusually clean

The generator is asked for **JSON records**, not for an experiment. The carrier is five documents,
three integer fields in `0..3`, and a reference into a side table holding an integer and a note. That
description contains no feature, no row, no component, no lineage and no notion of ambiguity: a
generator given it cannot know what the worlds are for, because the thing they are for is not in the
prompt.

Stratification then happens **afterwards**, by the structural criterion M111 already froze and
published. The project classifies; the generator emits. Neither knows what the other did.

## What such a bank would and would not establish

It removes **world authorship**. It does not remove **carrier authorship**: the value chain, the
document shape, the reference edge, the operators, the bounds and the evaluator all remain this
project's. A positive run under this contract is therefore evidence that the transfer and diagnosis
results do not depend on the project having chosen the worlds — and nothing more. G4 does not close
on it, and no tier below `human_maintained_sealed_bank` ever will.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from metamorphosis import m110_runtime as consumer
from metamorphosis.blind_bank_protocol import (
    EVIDENCE_TIERS,
    PHASES,
    canonical_bytes,
    contamination_hits,
    opaque_domain_id,
    sha256_hex,
)

MILESTONE = "M112"
CONTRACT_VERSION = "mira-blind-bank-v1"

WORLD_PAYLOAD_SCHEMA = "mira-blind-bank-world-payload-v1"
DEVELOPMENT_WORLD_PAYLOAD_SCHEMA = "mira-blind-bank-world-payload-development-v1"
ANALYSIS_PLAN_SCHEMA = "m112-world-bank-analysis-plan-v1"
SYSTEM_PROTOCOL_SCHEMA = "m112-world-bank-system-protocol-v1"
REPORT_SCHEMA = "m112-world-bank-readiness-v1"

EXPERIMENT_DIRECTORY = Path("experiments/M112")
GENERATOR_SPEC_PATH = EXPERIMENT_DIRECTORY / "GENERATOR_SPEC.json"
GENERATOR_PROMPT_PATH = EXPERIMENT_DIRECTORY / "GENERATOR_PROMPT.txt"
ANALYSIS_PLAN_PATH = EXPERIMENT_DIRECTORY / "ANALYSIS_PLAN.json"
BANK_COMMITMENT_PATH = EXPERIMENT_DIRECTORY / "PUBLIC_BANK_COMMITMENT.json"
SYSTEM_PROTOCOL_PATH = EXPERIMENT_DIRECTORY / "SYSTEM_PROTOCOL.json"
REVEAL_AUTHORIZATION_PATH = EXPERIMENT_DIRECTORY / "REVEAL_AUTHORIZATION.json"
RESULT_PATH = EXPERIMENT_DIRECTORY / "RESULT.json"

# Base rates measured before this module existed, over 1 160 project-generated worlds. They are
# recorded because the analysis plan's minimum stratum sizes have to be reachable *and* refusable,
# and neither can be judged without them.
MEASURED_AMBIGUOUS_RATE = 0.06
MEASURED_WITNESS_RATE = 0.36

# The tested system. Every one of these is frozen before the bank is revealed, and a bank cannot be
# revealed against a system that changed afterwards.
TESTED_SYSTEM_PATHS = (
    "metamorphosis/m107_runtime.py",
    "metamorphosis/m108_runtime.py",
    "metamorphosis/m109_runtime.py",
    "metamorphosis/m110_runtime.py",
    "metamorphosis/m111_runtime.py",
    "scripts/run_m110_process.py",
    "scripts/run_m110_qualification.py",
    "scripts/check_m110_result.py",
    "scripts/run_m111_process.py",
    "scripts/run_m111_qualification.py",
    "scripts/check_m111_result.py",
)

WORLD_BANK_CLAIM_BOUNDARY = {
    "evidence_tier": "blind_generated_sealed_bank",
    "procedural_independence": True,
    "generator_context_blindness": True,
    "generator_training_data_independence": False,
    "human_independence": False,
    "external_reproduction": False,
    "removes_world_authorship": True,
    "removes_carrier_authorship": False,
    "closes_g4": False,
    "advances_any_generality_gate": False,
    "agi": False,
}


class WorldBankError(RuntimeError):
    """Raised when an artifact under this contract is invalid. Every path fails closed."""


# ----------------------------------------------------------------------------------------
# The payload: worlds, and nothing that could tell anyone what they are for.
# ----------------------------------------------------------------------------------------

# Keys that would betray that the emitter knew what the worlds were for. Their presence does not
# prove contamination, but a blind generator has no reason to produce any of them.
FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "row",
        "rows",
        "row_index",
        "row_labels",
        "feature",
        "features",
        "feature_row",
        "component",
        "components",
        "ambiguous",
        "ambiguous_rows",
        "witness",
        "stratum",
        "census",
        "canonical_targets",
        "target",
        "targets",
        "pair",
        "policy",
        "episodes",
        "label",
        "labels",
        "lineage",
        "machinery",
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


def validate_world_bank_payload(
    payload: Mapping[str, Any], *, development: bool = False
) -> dict[str, Any]:
    """Structural conformity to the M110 carrier, and silence about everything else.

    This runs **after** reveal. It never decides whether a world is useful, only whether it is a
    well-formed member of the carrier and whether it says anything it could not have known.
    """
    expected = DEVELOPMENT_WORLD_PAYLOAD_SCHEMA if development else WORLD_PAYLOAD_SCHEMA
    if not isinstance(payload, Mapping) or payload.get("schema") != expected:
        raise WorldBankError("world bank payload schema is not the declared one")
    nonce = payload.get("bank_nonce")
    if not isinstance(nonce, str) or len(nonce) != 64:
        raise WorldBankError("world bank payload carries no 64-character nonce")

    offending = sorted(set(_keys(payload)) & FORBIDDEN_PAYLOAD_KEYS)
    if offending:
        raise WorldBankError(
            "world bank payload names keys a blind generator could not know: %s"
            % ", ".join(offending)
        )
    raw = payload.get("worlds")
    # The contamination scan runs over the generated content, not over the envelope: the schema
    # string legitimately carries the contract's own name, and scanning it would flag every
    # well-formed payload.
    hits = contamination_hits(raw)
    if hits:
        raise WorldBankError("world bank payload is contaminated: %s" % ", ".join(hits))

    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or not raw:
        raise WorldBankError("world bank payload holds no worlds")

    decoded: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, entry in enumerate(raw):
        if not isinstance(entry, Mapping):
            raise WorldBankError("world %d is not an object" % index)
        expected_id = opaque_domain_id(nonce, index)
        if entry.get("world_ref") != expected_id:
            raise WorldBankError(
                "world %d does not carry the opaque identifier derived from the nonce" % index
            )
        # The carrier's own constructor is the validator. A world it refuses is not a world.
        world = consumer.consumer_world(
            expected_id, entry.get("documents") or [], entry.get("side") or {}
        )
        # Duplication is compared on **content**, not on the world digest: the digest binds the
        # opaque identifier, so two identical records under different identifiers would otherwise
        # both pass. The prompt asks the generator not to repeat an entry; this is what checks it.
        content = sha256_hex(
            canonical_bytes({"documents": world["documents"], "side": world["side"]})
        )
        if content in seen:
            raise WorldBankError("world %d duplicates an earlier world" % index)
        seen.add(content)
        decoded.append(world)
    return {
        "schema": "m112-world-bank-acceptance-v1",
        "development": bool(development),
        "world_count": len(decoded),
        "world_digests": [item["world_digest"] for item in decoded],
        "payload_sha256": sha256_hex(canonical_bytes(payload)),
        "worlds": decoded,
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

    The generic contract records the M086-A defect: a threshold that could never fail produced a
    positive verdict. The mirror defect is a threshold that could never pass. Both are refused here
    by deriving, from the base rates measured over 1 160 project-generated worlds, whether the
    declared bank size makes the declared minimum stratum sizes *reachable* and *refusable*.
    """
    if not isinstance(plan, Mapping) or plan.get("schema") != ANALYSIS_PLAN_SCHEMA:
        raise WorldBankError("analysis plan schema is not the declared one")
    for key in (
        "requested_world_count",
        "minimum_ambiguous_worlds",
        "minimum_witness_worlds",
    ):
        value = plan.get(key)
        if not isinstance(value, int) or value <= 0:
            raise WorldBankError("analysis plan field %s is not a positive integer" % key)

    requested = int(plan["requested_world_count"])
    ambiguous = int(plan["minimum_ambiguous_worlds"])
    witness = int(plan["minimum_witness_worlds"])

    expected_ambiguous = requested * MEASURED_AMBIGUOUS_RATE
    expected_witness = requested * MEASURED_WITNESS_RATE
    if ambiguous > expected_ambiguous * 2:
        raise WorldBankError(
            "the ambiguous minimum is unreachable at the measured base rate: %d wanted, about "
            "%.1f expected" % (ambiguous, expected_ambiguous)
        )
    if witness > expected_witness * 2:
        raise WorldBankError(
            "the witness minimum is unreachable at the measured base rate: %d wanted, about "
            "%.1f expected" % (witness, expected_witness)
        )
    if ambiguous < 2:
        raise WorldBankError(
            "an ambiguous minimum below two cannot fail on a bank of this size, so it decides "
            "nothing"
        )
    if plan.get("insufficient_bank_verdict") != "negative":
        raise WorldBankError(
            "the plan must declare that a bank yielding too few worlds is a negative result, not "
            "a retry"
        )
    if plan.get("retries_permitted") is not False:
        raise WorldBankError("the plan must forbid retries")
    if plan.get("stratification_criterion") != "m111_public_structural_criterion":
        raise WorldBankError(
            "stratification must use the criterion M111 already froze and published"
        )
    if plan.get("claim_boundary") != WORLD_BANK_CLAIM_BOUNDARY:
        raise WorldBankError("analysis plan claim boundary drifted")
    if plan.get("plan_commitment_sha256") != analysis_plan_commitment(plan):
        raise WorldBankError("analysis plan commitment drifted")


# ----------------------------------------------------------------------------------------
# The system protocol, frozen after sealing and before reveal.
# ----------------------------------------------------------------------------------------


def system_protocol_commitment(protocol: Mapping[str, Any]) -> str:
    return sha256_hex(
        canonical_bytes({k: v for k, v in protocol.items() if k != "protocol_commitment_sha256"})
    )


def validate_system_protocol(protocol: Mapping[str, Any], *, root: Path) -> None:
    if not isinstance(protocol, Mapping) or protocol.get("schema") != SYSTEM_PROTOCOL_SCHEMA:
        raise WorldBankError("system protocol schema is not the declared one")
    declared = protocol.get("tested_system_digests")
    if not isinstance(declared, Mapping):
        raise WorldBankError("system protocol carries no tested-system digests")
    if sorted(declared) != sorted(TESTED_SYSTEM_PATHS):
        raise WorldBankError("system protocol does not bind exactly the declared tested system")
    for path in TESTED_SYSTEM_PATHS:
        member = root / path
        if not member.is_file():
            raise WorldBankError("tested-system member %s is absent" % path)
        if sha256_hex(member.read_bytes().replace(b"\r\n", b"\n")) != declared[path]:
            raise WorldBankError("tested-system member %s drifted after the freeze" % path)
    if protocol.get("tested_system_unmodified_after_reveal") is not True:
        raise WorldBankError("system protocol does not assert the post-reveal invariant")
    if protocol.get("claim_boundary") != WORLD_BANK_CLAIM_BOUNDARY:
        raise WorldBankError("system protocol claim boundary drifted")
    if protocol.get("protocol_commitment_sha256") != system_protocol_commitment(protocol):
        raise WorldBankError("system protocol commitment drifted")


# ----------------------------------------------------------------------------------------
# The phase machine. Fail-closed, and it never opens a payload.
# ----------------------------------------------------------------------------------------


def _load(path: Path) -> tuple[Mapping[str, Any] | None, str | None]:
    if not path.is_file():
        return None, "missing %s" % path.name
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return None, "unreadable %s: %s" % (path.name, error)
    if not isinstance(value, Mapping):
        return None, "%s is not an object" % path.name
    return value, None


def assess_world_bank_readiness(root: Path) -> dict[str, Any]:
    """Report the phase and every reason a reveal is not authorized.

    An absent artifact, a malformed one and a drifted one are all blockers. There is no code path
    here that opens, decrypts or lists bank content.
    """
    resolved = root.resolve()
    blockers: list[str] = []
    phase = "draft"

    plan, error = _load(resolved / ANALYSIS_PLAN_PATH)
    if error:
        blockers.append(error)
    elif plan is not None:
        try:
            validate_analysis_plan(plan)
        except WorldBankError as exc:
            blockers.append("analysis plan: %s" % exc)
            plan = None

    spec_present = (resolved / GENERATOR_SPEC_PATH).is_file()
    prompt_present = (resolved / GENERATOR_PROMPT_PATH).is_file()
    if plan is not None and spec_present and prompt_present:
        phase = "spec_frozen"
    else:
        if not spec_present:
            blockers.append("missing %s" % GENERATOR_SPEC_PATH.name)
        if not prompt_present:
            blockers.append("missing %s" % GENERATOR_PROMPT_PATH.name)

    commitment, error = _load(resolved / BANK_COMMITMENT_PATH)
    if error:
        blockers.append(error)
    elif phase == "spec_frozen":
        phase = "generated_sealed"

    protocol, error = _load(resolved / SYSTEM_PROTOCOL_PATH)
    if error:
        blockers.append(error)
    elif protocol is not None:
        try:
            validate_system_protocol(protocol, root=resolved)
        except WorldBankError as exc:
            blockers.append("system protocol: %s" % exc)
            protocol = None
        else:
            if phase == "generated_sealed":
                phase = "system_protocol_frozen"

    authorization, error = _load(resolved / REVEAL_AUTHORIZATION_PATH)
    if error:
        blockers.append(error)
    elif phase == "system_protocol_frozen":
        phase = "reveal_authorized"

    if (resolved / RESULT_PATH).is_file():
        phase = "executed"

    return {
        "schema": REPORT_SCHEMA,
        "milestone": MILESTONE,
        "contract_version": CONTRACT_VERSION,
        "phase": phase,
        "phase_is_declared": phase in PHASES,
        "ready_for_reveal": phase == "reveal_authorized" and not blockers,
        "revealed": phase == "executed",
        "blockers": blockers,
        "evidence_tier_if_executed": WORLD_BANK_CLAIM_BOUNDARY["evidence_tier"],
        "evidence_tier_is_declared": WORLD_BANK_CLAIM_BOUNDARY["evidence_tier"] in EVIDENCE_TIERS,
        "claim_boundary": dict(WORLD_BANK_CLAIM_BOUNDARY),
        "tested_system_paths": list(TESTED_SYSTEM_PATHS),
        "bank_exists": (resolved / BANK_COMMITMENT_PATH).is_file(),
    }
