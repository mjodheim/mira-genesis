"""Pre-arm M092 adoption, persistence, ablation and rollback apparatus.

This module is deliberately target-neutral.  It never opens the sealed theorem or qualification
material.  A caller must supply an already selected program, its candidate certificate and the
precommitted postcondition.  The scanner and independent global verifier are rerun here: stored
acceptance fields are not trusted.

The persisted execution authority is one closed bundle containing the extended substrate and the
downstream language.  The transaction journal is evidence only and is never consulted by runtime
execution.  Both the acquired operation and the downstream primitive have deterministic
content-addressed identities fixed before result reveal.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Mapping, Sequence

from metamorphosis.m092_candidate_validation import validate_candidate_artifacts
from metamorphosis.m092_certificate_verifier import verify_global_certificate
from metamorphosis.m092_kernel import Program, program_digest
from metamorphosis.m092_runtime import RuntimeLanguage, RuntimePrimitive, canonical_bytes
from metamorphosis.m092_substrate_state import (
    SubstrateOperation,
    SubstrateState,
    execute_from_state,
)

EXTENDED_BUNDLE_SCHEMA = "m092-extended-runtime-bundle/1"
ADOPTION_RECEIPT_SCHEMA = "m092-adoption-receipt/1"
TRANSACTION_SCHEMA = "m092-adoption-transaction/1"
DOWNSTREAM_KEY_SCHEMA = "m092-downstream-primitive-key/1"
ACQUIRED_KEY_PREFIX = "ACQUIRED_"
DOWNSTREAM_PRIMITIVE_PREFIX = "M092_USE_"
DOWNSTREAM_PARAMETER_KINDS = ("slot", "input")
DOWNSTREAM_CAPABILITIES = ("pure_slot_write",)

# Fixed pre-result fault.  For x=0 it returns 1, whereas both the neutral countdown rehearsal and
# the frozen M092 target postcondition require y=0.  It changes executable behaviour, not metadata.
BEHAVIOUR_FAULT_PROGRAM: Program = (
    ("SPOP", 0),
    ("LOADI", 0, 1),
    ("SPUSH", 0),
    ("HALT",),
)


class AdoptionError(ValueError):
    """The pre-arm adoption contract was violated."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest(value: object) -> str:
    return sha256_bytes(canonical_bytes(value))


def operation_key(program: Program) -> str:
    """Return the frozen, full-content-addressed substrate-operation key."""

    return ACQUIRED_KEY_PREFIX + program_digest(program)


def downstream_body(program: Program) -> tuple[tuple[str, object], ...]:
    return (("PUSH_INPUT", "$1"), (operation_key(program), 0), ("STORE_SLOT", "$0"))


def downstream_primitive_id(program: Program) -> str:
    """Content-address the exact downstream body and signature, not the K1 digest alone."""

    payload = {
        "schema": DOWNSTREAM_KEY_SCHEMA,
        "parameter_kinds": list(DOWNSTREAM_PARAMETER_KINDS),
        "body": [[name, argument] for name, argument in downstream_body(program)],
        "capabilities": list(DOWNSTREAM_CAPABILITIES),
    }
    return DOWNSTREAM_PRIMITIVE_PREFIX + _digest(payload)


def validate_candidate_for_adoption(
    program: Program,
    certificate: Mapping[str, object],
    *,
    expected_postcondition: Mapping[str, object],
    support_artifacts: Sequence[object] = (),
) -> dict[str, object]:
    """Recompute structural/anti-cheating and global-proof acceptance from raw candidate bytes."""

    scanner = validate_candidate_artifacts(
        program, certificate, support_artifacts=support_artifacts,
    )
    if scanner.get("accepted") is not True:
        raise AdoptionError("candidate scanner refused adoption")
    verification = verify_global_certificate(
        program, certificate, expected_postcondition=expected_postcondition,
    )
    exact_program_digest = program_digest(program)
    if verification.get("status") != "accepted":
        raise AdoptionError("independent certificate verifier refused adoption")
    if scanner.get("program_digest") != exact_program_digest:
        raise AdoptionError("scanner program digest differs from recomputed program digest")
    if verification.get("program_digest") != exact_program_digest:
        raise AdoptionError("verifier program digest differs from recomputed program digest")

    receipt: dict[str, object] = {
        "schema": ADOPTION_RECEIPT_SCHEMA,
        "program_digest": exact_program_digest,
        "operation_key": operation_key(program),
        "primitive_id": downstream_primitive_id(program),
        "scanner_report_digest": scanner["report_digest"],
        "verification_report_digest": _digest(verification),
        "certificate_digest": verification["certificate_digest"],
        "candidate_executed_during_validation": False,
        "qualification_read_during_validation": False,
    }
    receipt["receipt_digest"] = _digest(receipt)
    return receipt


def _require_pure_slot_write(substrate: SubstrateState) -> tuple[str, ...]:
    capability = "pure_slot_write"
    if capability not in substrate.permitted_capabilities:
        raise AdoptionError("base substrate lacks the capability required by the downstream primitive")
    return (capability,)


def extend_substrate(
    base: SubstrateState,
    program: Program,
    *,
    receipt: Mapping[str, object],
) -> SubstrateState:
    exact_digest = program_digest(program)
    key = operation_key(program)
    if receipt.get("program_digest") != exact_digest or receipt.get("operation_key") != key:
        raise AdoptionError("adoption receipt is not bound to the exact program")
    if base.operation(key) is not None:
        raise AdoptionError("content-addressed operation is already registered")

    acquired = SubstrateOperation(
        key=key,
        argument_role="none",
        program=program,
        origin="acquired",
        provenance=("M092 independently validated acquisition", exact_digest),
        capabilities=(),
        minimum_stack_depth=1,
    )
    return SubstrateState(
        operations=base.operations + (acquired,),
        slot_count=base.slot_count,
        input_count=base.input_count,
        max_body_length=base.max_body_length,
        max_stack_depth=base.max_stack_depth,
        literal_values=base.literal_values,
        parameter_domains=base.parameter_domains,
        permitted_capabilities=base.permitted_capabilities,
        forbidden_capabilities=base.forbidden_capabilities,
        substrate_version=base.substrate_version + 1,
        provenance=base.provenance + ("M092 acquired operation registered", exact_digest),
    )


def extend_language(
    base: RuntimeLanguage,
    substrate: SubstrateState,
    program: Program,
    *,
    receipt: Mapping[str, object],
) -> RuntimeLanguage:
    key = operation_key(program)
    primitive_id = downstream_primitive_id(program)
    if receipt.get("operation_key") != key or receipt.get("primitive_id") != primitive_id:
        raise AdoptionError("adoption receipt does not bind the downstream primitive")
    if substrate.operation(key) is None:
        raise AdoptionError("downstream primitive cannot be registered before its dependency")
    if base.definition(primitive_id) is not None:
        raise AdoptionError("downstream primitive is already registered")

    capabilities = _require_pure_slot_write(substrate)
    if capabilities != DOWNSTREAM_CAPABILITIES:
        raise AdoptionError("downstream capability signature differs from the frozen contract")
    primitive = RuntimePrimitive(
        primitive_id=primitive_id,
        parameter_kinds=DOWNSTREAM_PARAMETER_KINDS,
        body=downstream_body(program),
        origin="acquired",
        provenance=("M092 downstream primitive", receipt["program_digest"]),
        capabilities=capabilities,
    )
    return RuntimeLanguage(
        primitives=base.primitives + (primitive,),
        language_version=base.language_version + 1,
        provenance=base.provenance + ("M092 downstream primitive registered",),
    )


def build_extended_bundle(
    base_language: RuntimeLanguage,
    base_substrate: SubstrateState,
    program: Program,
    *,
    receipt: Mapping[str, object],
    source_bundle_sha256: str,
) -> dict[str, object]:
    """Build S1/L1 without persistence or qualification materialization."""

    extended_substrate = extend_substrate(base_substrate, program, receipt=receipt)
    extended_language = extend_language(
        base_language, extended_substrate, program, receipt=receipt,
    )
    bundle: dict[str, object] = {
        "schema": EXTENDED_BUNDLE_SCHEMA,
        "source_bundle_sha256": source_bundle_sha256,
        "program_digest": program_digest(program),
        "operation_key": operation_key(program),
        "primitive_id": downstream_primitive_id(program),
        "substrate_digest": extended_substrate.digest(),
        "language_digest": extended_language.digest(),
        "substrate": extended_substrate.to_dict(),
        "language": extended_language.to_dict(),
    }
    bundle["bundle_digest"] = _digest(bundle)
    return bundle


def parse_extended_bundle(bundle: Mapping[str, object]) -> tuple[RuntimeLanguage, SubstrateState]:
    expected = {
        "schema", "source_bundle_sha256", "program_digest", "operation_key", "primitive_id",
        "substrate_digest", "language_digest", "substrate", "language", "bundle_digest",
    }
    if set(bundle) != expected or bundle.get("schema") != EXTENDED_BUNDLE_SCHEMA:
        raise AdoptionError("extended bundle fields differ from the closed schema")
    without_digest = {key: bundle[key] for key in bundle if key != "bundle_digest"}
    if bundle["bundle_digest"] != _digest(without_digest):
        raise AdoptionError("extended bundle digest mismatch")
    language = RuntimeLanguage.from_dict(bundle["language"])  # type: ignore[arg-type]
    substrate = SubstrateState.from_dict(bundle["substrate"])  # type: ignore[arg-type]
    if language.digest() != bundle["language_digest"]:
        raise AdoptionError("persisted language digest mismatch")
    if substrate.digest() != bundle["substrate_digest"]:
        raise AdoptionError("persisted substrate digest mismatch")
    key = str(bundle["operation_key"])
    operation = substrate.operation(key)
    if operation is None or program_digest(operation.program) != bundle["program_digest"]:
        raise AdoptionError("persisted acquired operation does not match its bound program digest")
    if key != operation_key(operation.program):
        raise AdoptionError("persisted acquired operation key is not content-addressed")
    expected_primitive_id = downstream_primitive_id(operation.program)
    if bundle["primitive_id"] != expected_primitive_id:
        raise AdoptionError("persisted downstream primitive id is not content-addressed from body/signature")
    primitive = language.definition(expected_primitive_id)
    if primitive is None:
        raise AdoptionError("persisted downstream primitive is absent")
    if primitive.parameter_kinds != DOWNSTREAM_PARAMETER_KINDS:
        raise AdoptionError("persisted downstream signature differs")
    if primitive.body != downstream_body(operation.program):
        raise AdoptionError("persisted downstream body differs from its content-addressed identity")
    if primitive.capabilities != DOWNSTREAM_CAPABILITIES:
        raise AdoptionError("persisted downstream capabilities differ")
    return language, substrate


def _atomic_json(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    data = json.dumps(value, indent=2, sort_keys=True) + "\n"
    temporary.write_text(data, encoding="utf-8")
    os.replace(temporary, path)


def commit_adoption_transaction(
    bundle_path: Path,
    journal_path: Path,
    bundle: Mapping[str, object],
) -> dict[str, object]:
    """Persist PREPARED -> STAGED -> COMMITTED; the journal never becomes execution authority."""

    parse_extended_bundle(bundle)
    base: dict[str, object] = {
        "schema": TRANSACTION_SCHEMA,
        "bundle_path": str(bundle_path),
        "bundle_digest": bundle["bundle_digest"],
        "program_digest": bundle["program_digest"],
        "operation_key": bundle["operation_key"],
        "primitive_id": bundle["primitive_id"],
    }
    prepared = dict(base, phase="PREPARED")
    prepared["journal_digest"] = _digest(prepared)
    _atomic_json(journal_path, prepared)

    _atomic_json(bundle_path, bundle)
    reloaded = json.loads(bundle_path.read_text(encoding="utf-8"))
    parse_extended_bundle(reloaded)
    if reloaded != dict(bundle):
        raise AdoptionError("staged bundle differs from the validated bundle")

    staged = dict(base, phase="STAGED")
    staged["journal_digest"] = _digest(staged)
    _atomic_json(journal_path, staged)

    committed = dict(base, phase="COMMITTED")
    committed["journal_digest"] = _digest(committed)
    _atomic_json(journal_path, committed)
    return committed


def load_committed_bundle(bundle_path: Path, journal_path: Path) -> tuple[RuntimeLanguage, SubstrateState]:
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    if journal.get("schema") != TRANSACTION_SCHEMA or journal.get("phase") != "COMMITTED":
        raise AdoptionError("adoption transaction is not committed")
    claimed = journal.get("journal_digest")
    raw = {key: journal[key] for key in journal if key != "journal_digest"}
    if claimed != _digest(raw):
        raise AdoptionError("transaction journal digest mismatch")
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    if bundle.get("bundle_digest") != journal.get("bundle_digest"):
        raise AdoptionError("journal and persisted bundle disagree")
    return parse_extended_bundle(bundle)


def execute_downstream(
    language: RuntimeLanguage,
    substrate: SubstrateState,
    primitive_id: str,
    value: int,
) -> tuple[int, ...]:
    return execute_from_state(((primitive_id, (0, 0)),), (int(value),), language, substrate)


def dependency_ablation(bundle: Mapping[str, object]) -> tuple[RuntimeLanguage, SubstrateState]:
    language, substrate = parse_extended_bundle(bundle)
    return language, substrate.without(str(bundle["operation_key"]))


def behaviour_fault(bundle: Mapping[str, object]) -> dict[str, object]:
    """Return a valid but semantically corrupted persisted bundle using the frozen fault program."""

    language, substrate = parse_extended_bundle(bundle)
    corrupted = substrate.replacing(str(bundle["operation_key"]), BEHAVIOUR_FAULT_PROGRAM)
    result = dict(bundle)
    result["substrate"] = corrupted.to_dict()
    result["substrate_digest"] = corrupted.digest()
    result_without_digest = {key: result[key] for key in result if key != "bundle_digest"}
    result["bundle_digest"] = _digest(result_without_digest)
    if language.definition(str(bundle["primitive_id"])) is None:
        raise AdoptionError("fault construction lost the downstream primitive")
    return result


def restore_exact(path: Path, preserved_bytes: bytes) -> str:
    """Rollback from independently preserved bytes and return their recomputed SHA-256."""

    temporary = path.with_name(path.name + ".rollback.tmp")
    temporary.write_bytes(preserved_bytes)
    os.replace(temporary, path)
    restored = path.read_bytes()
    if restored != preserved_bytes:
        raise AdoptionError("rollback bytes differ from the independently preserved snapshot")
    return sha256_bytes(restored)


__all__ = [
    "ACQUIRED_KEY_PREFIX", "ADOPTION_RECEIPT_SCHEMA", "AdoptionError",
    "BEHAVIOUR_FAULT_PROGRAM", "DOWNSTREAM_CAPABILITIES", "DOWNSTREAM_KEY_SCHEMA",
    "DOWNSTREAM_PARAMETER_KINDS", "DOWNSTREAM_PRIMITIVE_PREFIX", "EXTENDED_BUNDLE_SCHEMA",
    "TRANSACTION_SCHEMA", "behaviour_fault", "build_extended_bundle",
    "commit_adoption_transaction", "dependency_ablation", "downstream_body",
    "downstream_primitive_id", "execute_downstream", "extend_language", "extend_substrate",
    "load_committed_bundle", "operation_key", "parse_extended_bundle", "restore_exact",
    "sha256_bytes", "validate_candidate_for_adoption",
]
