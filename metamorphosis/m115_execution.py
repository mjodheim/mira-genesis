"""Post-seal custody and reveal gates for M115/H60.

The qualifying response was generated and sealed by the already-frozen M115 instrument.  This
module starts strictly after that boundary.  It never decrypts the bank.  Its only responsibilities
are to bind the tested system after sealing, validate the owner's later reveal authorization, and
report whether the single in-memory reveal entry point may run.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Mapping

from metamorphosis import m113_carrier_bank as scientific_bank
from metamorphosis import m115_carrier_bank as bank
from metamorphosis import m115_delivery as delivery
from metamorphosis import m115_identity as identity
from metamorphosis import m115_sealing as sealing
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex


SYSTEM_PROTOCOL_SCHEMA = "m115-carrier-bank-system-protocol-v1"
REVEAL_AUTHORIZATION_SCHEMA = "m115-reveal-authorization-v1"
READINESS_SCHEMA = "m115-execution-readiness-v1"

SYSTEM_PROTOCOL_PATH = bank.SYSTEM_PROTOCOL_PATH
REVEAL_AUTHORIZATION_PATH = bank.REVEAL_AUTHORIZATION_PATH
RESULT_PATH = bank.RESULT_PATH
CHECK_REPORT_PATH = bank.EXPERIMENT_DIRECTORY / "CHECK_REPORT.json"
REVEAL_ATTEMPT_PATH = bank.EXPERIMENT_DIRECTORY / "REVEAL_ATTEMPT.json"

PHASES = (
    "spec_frozen",
    "generated_sealed",
    "system_protocol_frozen",
    "reveal_authorized",
    "reveal_consumed",
    "executed",
)

# M113's scientific system and M114's corrective P15 are inherited, not copied.  M115 adds only the
# sealed-response provenance, identity gate, phase machine, orchestration and checker that meet the
# already-frozen bank.  Every member is frozen before reveal.
TESTED_SYSTEM_PATHS = tuple(
    dict.fromkeys(
        scientific_bank.TESTED_SYSTEM_PATHS
        + (
            "metamorphosis/m114_carrier_bank.py",
            "metamorphosis/m114_delivery.py",
            "scripts/run_m114_qualification.py",
            "scripts/check_m114_result.py",
            "metamorphosis/m115_carrier_bank.py",
            "metamorphosis/m115_delivery.py",
            "metamorphosis/m115_identity.py",
            "metamorphosis/m115_sealing.py",
            "metamorphosis/m115_execution.py",
            "scripts/authorize_m115_reveal.py",
            "scripts/check_m115_execution_readiness.py",
            "scripts/run_m115_postseal.py",
            "scripts/run_m115_qualification.py",
            "scripts/check_m115_result.py",
        )
    )
)
TESTED_SYSTEM_DIGEST_MODES = {path: "lf_normalized" for path in TESTED_SYSTEM_PATHS}

_SHA256_RE = re.compile(r"\A[0-9a-f]{64}\Z")
_COMMIT_RE = re.compile(r"\A[0-9a-f]{40}\Z")


class ExecutionError(RuntimeError):
    """Raised whenever a post-seal transition cannot be proved from preserved files."""


def _root(root: Path | None) -> Path:
    return Path.cwd().resolve() if root is None else Path(root).resolve()


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ExecutionError("cannot read %s: %s" % (path, exc))
    if not isinstance(value, dict):
        raise ExecutionError("%s is not a JSON object" % path)
    return value


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and bool(_SHA256_RE.match(value))


def _digest_without(record: Mapping[str, Any], field: str) -> str:
    return sha256_hex(canonical_bytes({key: value for key, value in record.items() if key != field}))


def system_protocol_commitment(protocol: Mapping[str, Any]) -> str:
    return _digest_without(protocol, "protocol_commitment_sha256")


def reveal_authorization_commitment(authorization: Mapping[str, Any]) -> str:
    return _digest_without(authorization, "authorization_sha256")


def tested_system_digests(root: Path | None = None) -> dict[str, str]:
    base = _root(root)
    found: dict[str, str] = {}
    for relative in TESTED_SYSTEM_PATHS:
        path = base / relative
        if not path.is_file():
            raise ExecutionError("tested system member is missing: %s" % relative)
        raw = path.read_bytes()
        mode = TESTED_SYSTEM_DIGEST_MODES.get(relative)
        if mode == "lf_normalized":
            raw = raw.replace(b"\r\n", b"\n")
        elif mode != "raw":
            raise ExecutionError("tested system member has no declared digest mode: %s" % relative)
        found[relative] = hashlib.sha256(raw).hexdigest()
    return found


def _validated_frozen_records(root: Path) -> tuple[dict[str, Any], ...]:
    plan = _load(root / bank.ANALYSIS_PLAN_PATH)
    bank.validate_analysis_plan(plan, root=root)
    spec = _load(root / bank.GENERATOR_SPEC_PATH)
    bank.validate_generator_spec(
        spec,
        root=root,
        plan_commitment_sha256=plan.get("plan_commitment_sha256"),
    )
    ledger = _load(root / bank.DELIVERY_LEDGER_PATH)
    delivery.validate_delivery_ledger(
        ledger,
        spec_commitment_sha256=spec.get("spec_commitment_sha256"),
        request_body_sha256=spec.get("canonical_request_body_sha256"),
    )
    commitment = _load(root / bank.BANK_COMMITMENT_PATH)
    sealing.validate_public_commitment(commitment, root=root)
    return plan, spec, ledger, commitment


def build_system_protocol(root: Path | None = None) -> dict[str, Any]:
    """Build the only tested-system freeze the sealed bank and frozen plan permit."""
    base = _root(root)
    sealed_state = sealing.readiness(base)
    if sealed_state.get("phase") != "generated_sealed" or sealed_state.get("blockers"):
        raise ExecutionError("M115 must be generated_sealed with no blockers before system freeze")
    if (base / RESULT_PATH).exists() or (base / REVEAL_AUTHORIZATION_PATH).exists():
        raise ExecutionError("the tested system cannot be frozen behind reveal or execution")

    plan, spec, ledger, commitment = _validated_frozen_records(base)
    materialized = [
        attempt
        for attempt in ledger.get("attempts", [])
        if isinstance(attempt, Mapping) and attempt.get("outcome") == "materialized"
    ]
    if len(materialized) != 1:
        raise ExecutionError("the system freeze requires exactly one materialization")
    attestation = materialized[0].get("identity_attestation")
    if not isinstance(attestation, Mapping) or attestation.get("holds") is not True:
        raise ExecutionError("the system freeze requires the materialized runtime identity")

    protocol: dict[str, Any] = {
        "schema": SYSTEM_PROTOCOL_SCHEMA,
        "milestone": bank.MILESTONE,
        "hypothesis": bank.HYPOTHESIS,
        "frozen_after_sealing_and_before_reveal": True,
        "bank_content_known_at_freeze": False,
        "analysis_plan_commitment_sha256": plan["plan_commitment_sha256"],
        "spec_commitment_sha256": spec["spec_commitment_sha256"],
        "request_body_sha256": spec["canonical_request_body_sha256"],
        "delivery_ledger_sha256": delivery.ledger_digest(ledger),
        "generation_response_sha256": commitment["generation_response_sha256"],
        "bank_commitment_sha256": commitment["commitment_sha256"],
        "ciphertext_sha256": commitment["ciphertext_sha256"],
        "runtime_identity": {
            "identity_version": identity.IDENTITY_VERSION,
            "requested_model_alias": identity.REQUESTED_MODEL,
            "canonical_checkpoint": identity.CANONICAL_CHECKPOINT,
            "selected_provider": identity.SELECTED_PROVIDER,
            "materialized_attestation_holds": True,
        },
        "qualification": {
            "requested_carrier_count": plan["requested_carrier_count"],
            "minimum_qualifying_carriers": plan["minimum_qualifying_carriers"],
            "minimum_distinct_qualifying_structures": plan[
                "minimum_distinct_qualifying_structures"
            ],
            "session_budget": plan["session_budget"],
            "qualification_rule": plan["qualification_rule"],
            "demand_derivation_rule": plan["demand_derivation_rule"],
            "closure_rule": plan["closure_rule"],
            "scoring_rule": plan["scoring_rule"],
            "selection_among_carriers_permitted": plan[
                "selection_among_carriers_permitted"
            ],
            "manual_correction_permitted": plan["manual_correction_permitted"],
            "insufficient_bank_verdict": plan["insufficient_bank_verdict"],
            "one_attempt": True,
            "one_checker_replay": True,
        },
        "predicate_contract": {
            "retains_m114_computations": ["P%d" % index for index in range(1, 23)],
            "newly_versioned_for_m115": [],
            "p15_version": plan["p15_version"],
        },
        "claim_boundary": plan["claim_boundary"],
        "tested_system_paths": list(TESTED_SYSTEM_PATHS),
        "tested_system_digest_modes": dict(TESTED_SYSTEM_DIGEST_MODES),
        "tested_system_digests": tested_system_digests(base),
        "tested_system_unmodified_after_reveal": True,
        "protocol_commitment_sha256": "",
    }
    protocol["protocol_commitment_sha256"] = system_protocol_commitment(protocol)
    return protocol


def validate_system_protocol(
    protocol: Mapping[str, Any],
    *,
    root: Path | None = None,
    tested_system_commit: str | None = None,
) -> None:
    base = _root(root)
    if not isinstance(protocol, Mapping) or protocol.get("schema") != SYSTEM_PROTOCOL_SCHEMA:
        raise ExecutionError("M115 system protocol schema drifted")
    if protocol.get("milestone") != bank.MILESTONE or protocol.get("hypothesis") != bank.HYPOTHESIS:
        raise ExecutionError("M115 system protocol belongs to another experiment")
    if protocol.get("frozen_after_sealing_and_before_reveal") is not True:
        raise ExecutionError("M115 system protocol was not frozen at the declared boundary")
    if protocol.get("bank_content_known_at_freeze") is not False:
        raise ExecutionError("M115 system freeze may not claim knowledge of bank content")
    if protocol.get("tested_system_unmodified_after_reveal") is not True:
        raise ExecutionError("M115 post-reveal tested-system invariant is absent")
    if protocol.get("tested_system_paths") != list(TESTED_SYSTEM_PATHS):
        raise ExecutionError("M115 system protocol does not bind the exact tested system")
    if protocol.get("tested_system_digest_modes") != TESTED_SYSTEM_DIGEST_MODES:
        raise ExecutionError("M115 tested-system digest modes drifted")
    measured = (
        tested_system_digests(base)
        if tested_system_commit is None
        else tested_system_digests_at_commit(base, tested_system_commit)
    )
    if protocol.get("tested_system_digests") != measured:
        drifted = sorted(
            key
            for key, value in measured.items()
            if (protocol.get("tested_system_digests") or {}).get(key) != value
        )
        raise ExecutionError("the tested system changed after freeze: %s" % ", ".join(drifted))
    if protocol.get("protocol_commitment_sha256") != system_protocol_commitment(protocol):
        raise ExecutionError("M115 system protocol commitment drifted")

    plan, spec, ledger, commitment = _validated_frozen_records(base)
    bindings = {
        "analysis_plan_commitment_sha256": plan.get("plan_commitment_sha256"),
        "spec_commitment_sha256": spec.get("spec_commitment_sha256"),
        "request_body_sha256": spec.get("canonical_request_body_sha256"),
        "delivery_ledger_sha256": delivery.ledger_digest(ledger),
        "generation_response_sha256": commitment.get("generation_response_sha256"),
        "bank_commitment_sha256": commitment.get("commitment_sha256"),
        "ciphertext_sha256": commitment.get("ciphertext_sha256"),
    }
    drifted_bindings = sorted(key for key, value in bindings.items() if protocol.get(key) != value)
    if drifted_bindings:
        raise ExecutionError("M115 system protocol binding drifted: %s" % ", ".join(drifted_bindings))
    if protocol.get("claim_boundary") != plan.get("claim_boundary"):
        raise ExecutionError("M115 system protocol claim boundary drifted")
    if protocol.get("predicate_contract") != {
        "retains_m114_computations": ["P%d" % index for index in range(1, 23)],
        "newly_versioned_for_m115": [],
        "p15_version": plan.get("p15_version"),
    }:
        raise ExecutionError("M115 predicate contract drifted")


def _git(root: Path, *arguments: str, binary: bool = False) -> bytes | str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode != 0:
        raise ExecutionError("git could not verify the reveal chronology")
    return completed.stdout if binary else completed.stdout.decode("ascii").strip()


def tested_system_digests_at_commit(root: Path, commit: str) -> dict[str, str]:
    """Recompute the frozen system from its historical commit after an attempt is consumed.

    Before reveal, validation always uses current working-tree bytes.  A closed record must instead
    continue to prove the exact code that met the bank, even when prospective safety fixes land
    later.  This helper never makes a pre-reveal system eligible.
    """
    if not _COMMIT_RE.match(commit):
        raise ExecutionError("M115 tested-system commit is malformed")
    found: dict[str, str] = {}
    for relative in TESTED_SYSTEM_PATHS:
        raw = _git(root, "show", "%s:%s" % (commit, relative), binary=True)
        mode = TESTED_SYSTEM_DIGEST_MODES.get(relative)
        if mode == "lf_normalized":
            raw = raw.replace(b"\r\n", b"\n")
        elif mode != "raw":
            raise ExecutionError("tested system member has no declared digest mode: %s" % relative)
        found[relative] = hashlib.sha256(raw).hexdigest()
    return found


def commit_that_added(root: Path, relative: Path) -> str:
    output = str(
        _git(
            root,
            "log",
            "--format=%H",
            "--diff-filter=A",
            "--",
            str(relative).replace("\\", "/"),
        )
    )
    commits = [line for line in output.splitlines() if _COMMIT_RE.match(line)]
    if not commits:
        raise ExecutionError("no commit adds %s" % relative)
    return commits[0]


def build_reveal_authorization(
    *,
    root: Path | None = None,
    bank_commitment_published_at_commit: str,
    system_protocol_frozen_at_commit: str,
    authorized_by: str,
) -> dict[str, Any]:
    base = _root(root)
    if not _COMMIT_RE.match(bank_commitment_published_at_commit):
        raise ExecutionError("bank commitment commit is malformed")
    if not _COMMIT_RE.match(system_protocol_frozen_at_commit):
        raise ExecutionError("system protocol commit is malformed")
    protocol = _load(base / SYSTEM_PROTOCOL_PATH)
    validate_system_protocol(protocol, root=base)
    commitment = _load(base / bank.BANK_COMMITMENT_PATH)
    sealing.validate_public_commitment(commitment, root=base)
    plan = _load(base / bank.ANALYSIS_PLAN_PATH)
    bank.validate_analysis_plan(plan, root=base)

    authorization: dict[str, Any] = {
        "schema": REVEAL_AUTHORIZATION_SCHEMA,
        "milestone": bank.MILESTONE,
        "hypothesis": bank.HYPOTHESIS,
        "authorized": True,
        "authorized_by": authorized_by,
        "authorization_scope": (
            "one in-memory decryption and canonical qualification under the frozen M115 analysis "
            "plan, followed by one independent checker replay; every observed outcome is terminal"
        ),
        "reveal_attempts_permitted": 1,
        "bank_commitment_sha256": commitment["commitment_sha256"],
        "ciphertext_sha256": commitment["ciphertext_sha256"],
        "generation_response_sha256": commitment["generation_response_sha256"],
        "analysis_plan_commitment_sha256": plan["plan_commitment_sha256"],
        "system_protocol_commitment_sha256": protocol["protocol_commitment_sha256"],
        "claim_boundary": plan["claim_boundary"],
        "bank_commitment_published_at_commit": bank_commitment_published_at_commit,
        "system_protocol_frozen_at_commit": system_protocol_frozen_at_commit,
        "commitment_published_before_this": True,
        "tested_system_frozen_before_this": True,
        "no_post_hoc_repair_or_rescue_retry": True,
        "authorization_sha256": "",
    }
    authorization["authorization_sha256"] = reveal_authorization_commitment(authorization)
    return authorization


def _commit_has_current_bytes(root: Path, commit: str, relative: Path) -> bool:
    try:
        preserved = _git(root, "show", "%s:%s" % (commit, str(relative).replace("\\", "/")), binary=True)
    except ExecutionError:
        return False
    return preserved == (root / relative).read_bytes()


def _head_has_current_bytes(root: Path, relative: Path) -> bool:
    try:
        preserved = _git(root, "show", "HEAD:%s" % str(relative).replace("\\", "/"), binary=True)
    except ExecutionError:
        return False
    return preserved == (root / relative).read_bytes()


def validate_reveal_authorization(
    authorization: Mapping[str, Any],
    *,
    root: Path | None = None,
    require_committed_authorization: bool = True,
) -> None:
    base = _root(root)
    if not isinstance(authorization, Mapping) or authorization.get("schema") != REVEAL_AUTHORIZATION_SCHEMA:
        raise ExecutionError("M115 reveal authorization schema drifted")
    if authorization.get("milestone") != bank.MILESTONE or authorization.get("hypothesis") != bank.HYPOTHESIS:
        raise ExecutionError("M115 reveal authorization belongs to another experiment")
    for key in (
        "authorized",
        "commitment_published_before_this",
        "tested_system_frozen_before_this",
        "no_post_hoc_repair_or_rescue_retry",
    ):
        if authorization.get(key) is not True:
            raise ExecutionError("M115 reveal authorization must declare %s" % key)
    if authorization.get("reveal_attempts_permitted") != 1:
        raise ExecutionError("M115 reveal authorization must permit exactly one attempt")
    if not isinstance(authorization.get("authorized_by"), str) or not authorization.get("authorized_by"):
        raise ExecutionError("M115 reveal authorization records no owner instruction")
    if authorization.get("authorization_sha256") != reveal_authorization_commitment(authorization):
        raise ExecutionError("M115 reveal authorization digest drifted")

    bank_commit = authorization.get("bank_commitment_published_at_commit")
    system_commit = authorization.get("system_protocol_frozen_at_commit")
    if not isinstance(bank_commit, str) or not _COMMIT_RE.match(bank_commit):
        raise ExecutionError("M115 bank commitment publication commit is malformed")
    if not isinstance(system_commit, str) or not _COMMIT_RE.match(system_commit):
        raise ExecutionError("M115 system freeze commit is malformed")

    consumed = (base / RESULT_PATH).is_file() or (base / REVEAL_ATTEMPT_PATH).exists()
    protocol = _load(base / SYSTEM_PROTOCOL_PATH)
    validate_system_protocol(
        protocol,
        root=base,
        tested_system_commit=system_commit if consumed else None,
    )
    commitment = _load(base / bank.BANK_COMMITMENT_PATH)
    sealing.validate_public_commitment(commitment, root=base)
    plan = _load(base / bank.ANALYSIS_PLAN_PATH)
    bank.validate_analysis_plan(plan, root=base)
    expected = {
        "bank_commitment_sha256": commitment.get("commitment_sha256"),
        "ciphertext_sha256": commitment.get("ciphertext_sha256"),
        "generation_response_sha256": commitment.get("generation_response_sha256"),
        "analysis_plan_commitment_sha256": plan.get("plan_commitment_sha256"),
        "system_protocol_commitment_sha256": protocol.get("protocol_commitment_sha256"),
        "claim_boundary": plan.get("claim_boundary"),
    }
    drifted = sorted(key for key, value in expected.items() if authorization.get(key) != value)
    if drifted:
        raise ExecutionError("M115 reveal authorization binding drifted: %s" % ", ".join(drifted))

    if not _commit_has_current_bytes(base, bank_commit, bank.BANK_COMMITMENT_PATH):
        raise ExecutionError("the named sealed checkpoint does not contain the current commitment")
    if not _commit_has_current_bytes(base, system_commit, SYSTEM_PROTOCOL_PATH):
        raise ExecutionError("the named system-freeze commit does not contain the current protocol")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", bank_commit, system_commit],
        cwd=base,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if ancestor.returncode != 0:
        raise ExecutionError("the system freeze does not descend from the sealed checkpoint")
    if require_committed_authorization and not _head_has_current_bytes(base, REVEAL_AUTHORIZATION_PATH):
        raise ExecutionError("the reveal authorization is not committed at HEAD")


def readiness(root: Path | None = None) -> dict[str, Any]:
    """Report the complete post-seal phase without decrypting or listing a carrier."""
    base = _root(root)
    sealed = sealing.readiness(base)
    phase = sealed.get("phase") or "spec_frozen"
    blockers = list(sealed.get("blockers") or [])
    result_present = (base / RESULT_PATH).is_file()
    attempt_present = (base / REVEAL_ATTEMPT_PATH).exists()

    historical_system_commit: str | None = None
    authorization_path = base / REVEAL_AUTHORIZATION_PATH
    if (result_present or attempt_present) and authorization_path.is_file():
        try:
            candidate = _load(authorization_path).get("system_protocol_frozen_at_commit")
        except ExecutionError:
            candidate = None
        if isinstance(candidate, str) and _COMMIT_RE.match(candidate):
            historical_system_commit = candidate

    protocol_path = base / SYSTEM_PROTOCOL_PATH
    if protocol_path.is_file():
        try:
            protocol = _load(protocol_path)
            validate_system_protocol(
                protocol,
                root=base,
                tested_system_commit=historical_system_commit,
            )
        except (ExecutionError, sealing.SealingError, bank.CarrierBankError, delivery.DeliveryError) as exc:
            blockers.append("system protocol: %s" % exc)
        else:
            if phase == "generated_sealed":
                phase = "system_protocol_frozen"
    elif phase == "generated_sealed":
        blockers.append("missing SYSTEM_PROTOCOL.json")

    if authorization_path.is_file():
        try:
            authorization = _load(authorization_path)
            validate_reveal_authorization(authorization, root=base)
        except (ExecutionError, sealing.SealingError, bank.CarrierBankError, delivery.DeliveryError) as exc:
            blockers.append("reveal authorization: %s" % exc)
        else:
            if phase == "system_protocol_frozen":
                phase = "reveal_authorized"
    elif phase == "system_protocol_frozen":
        blockers.append("missing REVEAL_AUTHORIZATION.json")

    if attempt_present and not result_present:
        phase = "reveal_consumed"
        blockers.append("the single reveal attempt is consumed without a canonical result")
    if result_present:
        if phase == "reveal_authorized" and not blockers:
            phase = "executed"
        elif phase != "executed":
            blockers.append("RESULT.json exists without a valid reveal chain")

    blockers = sorted(set(blockers))
    return {
        "schema": READINESS_SCHEMA,
        "milestone": bank.MILESTONE,
        "hypothesis": bank.HYPOTHESIS,
        "phase": phase,
        "phase_ladder": list(PHASES),
        "ready_for_reveal": (
            phase == "reveal_authorized"
            and not blockers
            and not result_present
            and not attempt_present
        ),
        "revealed": result_present or attempt_present,
        "reveal_attempt_consumed": result_present or attempt_present,
        "blockers": blockers,
        "identity_semantics": identity.IDENTITY_VERSION,
        "canonical_checkpoint": identity.CANONICAL_CHECKPOINT,
        "selected_provider": identity.SELECTED_PROVIDER,
    }


__all__ = [
    "CHECK_REPORT_PATH",
    "ExecutionError",
    "PHASES",
    "READINESS_SCHEMA",
    "REVEAL_ATTEMPT_PATH",
    "RESULT_PATH",
    "REVEAL_AUTHORIZATION_PATH",
    "REVEAL_AUTHORIZATION_SCHEMA",
    "SYSTEM_PROTOCOL_PATH",
    "SYSTEM_PROTOCOL_SCHEMA",
    "TESTED_SYSTEM_DIGEST_MODES",
    "TESTED_SYSTEM_PATHS",
    "build_reveal_authorization",
    "build_system_protocol",
    "commit_that_added",
    "readiness",
    "reveal_authorization_commitment",
    "system_protocol_commitment",
    "tested_system_digests",
    "tested_system_digests_at_commit",
    "validate_reveal_authorization",
    "validate_system_protocol",
]
