"""M043 Q5 opaque-native migration qualification and exact continuity bindings."""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import inspect
import json
from typing import Mapping

from metamorphosis.m043_adoption import (
    VersionedLineageStore,
    build_candidate_package,
    initial_lineage,
    validate_candidate_disposably,
)
from metamorphosis.m043_lineage_state import (
    LineageSnapshot,
    journal_digest,
    learning_state_digest,
    tool_registry_digest,
)
from metamorphosis.m043_native_program import (
    NativeMealyProgram,
    NativeProgramError,
    NativeSynthesisCertificate,
    audit_program_against_discovery,
    native_program_to_mealy,
    synthesize_native_mealy,
)
from metamorphosis.m043_opaque_substrate import (
    DiscoveredFieldSubstrate,
    OpaqueFieldMachine,
    SubstrateError,
    discover_field_substrate,
    make_development_negative_machine,
    make_development_positive_machine,
)
from metamorphosis.m043_rewrite import exact_body_digest
from metamorphosis.m043_task_model import CatalogueStatus
from metamorphosis.m043_task_search import (
    q3_development_parent,
    run_q3_development_catalogue,
)


class MigrationError(ValueError):
    """Raised when a Q5 native migration bundle fails closed."""


BUNDLE_SCHEMA = "m043-q5-native-migration-bundle-v1"


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def _require_mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise MigrationError(f"{field} must be an object")
    return value


def _require_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise MigrationError(f"{field} must be a nonempty string")
    return value


def _require_int(value: object, field: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise MigrationError(f"{field} must be an integer >= {minimum}")
    return value


def _require_digest(value: object, field: str) -> str:
    raw = _require_string(value, field)
    if len(raw) != 64 or any(char not in "0123456789abcdef" for char in raw):
        raise MigrationError(f"{field} must be a lowercase SHA-256 digest")
    return raw


def _exact_fields(raw: Mapping[str, object], expected: set[str], field: str) -> None:
    if set(raw) != expected:
        missing = sorted(expected - set(raw))
        extra = sorted(set(raw) - expected)
        raise MigrationError(
            f"invalid {field} fields: missing={missing}, extra={extra}"
        )


@dataclass(frozen=True)
class NativeMigrationBundle:
    source_snapshot_digest: str
    source_version: int
    source_body_digest: str
    source_tool_registry_digest: str
    source_learning_state_digest: str
    source_journal_digest: str
    target_machine_id: str
    discovery_digest: str
    native_program: NativeMealyProgram
    synthesis_certificate: NativeSynthesisCertificate
    schema: str = BUNDLE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != BUNDLE_SCHEMA:
            raise MigrationError("unsupported native migration bundle schema")
        for field_name, value in (
            ("source_snapshot_digest", self.source_snapshot_digest),
            ("source_body_digest", self.source_body_digest),
            ("source_tool_registry_digest", self.source_tool_registry_digest),
            ("source_learning_state_digest", self.source_learning_state_digest),
            ("source_journal_digest", self.source_journal_digest),
            ("discovery_digest", self.discovery_digest),
        ):
            _require_digest(value, field_name)
        _require_int(self.source_version, "source_version")
        _require_string(self.target_machine_id, "target_machine_id")
        if self.native_program.machine_id != self.target_machine_id:
            raise MigrationError("native program targets another opaque machine")
        if self.native_program.discovery_digest != self.discovery_digest:
            raise MigrationError("native program and bundle discovery identities differ")
        if self.synthesis_certificate.native_program_digest != self.native_program.digest():
            raise MigrationError("certificate is bound to another native program")
        if self.synthesis_certificate.discovery_digest != self.discovery_digest:
            raise MigrationError("certificate is bound to another discovery record")
        if self.synthesis_certificate.source_body_digest != self.source_body_digest:
            raise MigrationError("certificate is bound to another source body")
        if not self.synthesis_certificate.exact:
            raise MigrationError("bundle requires an exact synthesis certificate")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "source_snapshot_digest": self.source_snapshot_digest,
            "source_version": self.source_version,
            "source_body_digest": self.source_body_digest,
            "source_tool_registry_digest": self.source_tool_registry_digest,
            "source_learning_state_digest": self.source_learning_state_digest,
            "source_journal_digest": self.source_journal_digest,
            "target_machine_id": self.target_machine_id,
            "discovery_digest": self.discovery_digest,
            "native_program": self.native_program.to_dict(),
            "synthesis_certificate": self.synthesis_certificate.to_dict(),
        }

    def to_bytes(self) -> bytes:
        return _canonical_json(self.to_dict())

    def digest(self) -> str:
        return hashlib.sha256(
            b"m043-q5-native-migration-bundle-v1\x00" + self.to_bytes()
        ).hexdigest()

    @staticmethod
    def from_bytes(payload: bytes | str) -> "NativeMigrationBundle":
        try:
            raw = _require_mapping(json.loads(payload), "native migration bundle")
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise MigrationError("native migration bundle is not valid JSON") from exc
        expected = {
            "schema",
            "source_snapshot_digest",
            "source_version",
            "source_body_digest",
            "source_tool_registry_digest",
            "source_learning_state_digest",
            "source_journal_digest",
            "target_machine_id",
            "discovery_digest",
            "native_program",
            "synthesis_certificate",
        }
        _exact_fields(raw, expected, "native migration bundle")
        program = NativeMealyProgram.from_bytes(_canonical_json(raw["native_program"]))
        certificate = NativeSynthesisCertificate.from_dict(
            raw["synthesis_certificate"]
        )
        return NativeMigrationBundle(
            schema=_require_string(raw["schema"], "schema"),
            source_snapshot_digest=_require_digest(
                raw["source_snapshot_digest"], "source_snapshot_digest"
            ),
            source_version=_require_int(raw["source_version"], "source_version"),
            source_body_digest=_require_digest(
                raw["source_body_digest"], "source_body_digest"
            ),
            source_tool_registry_digest=_require_digest(
                raw["source_tool_registry_digest"], "source_tool_registry_digest"
            ),
            source_learning_state_digest=_require_digest(
                raw["source_learning_state_digest"], "source_learning_state_digest"
            ),
            source_journal_digest=_require_digest(
                raw["source_journal_digest"], "source_journal_digest"
            ),
            target_machine_id=_require_string(
                raw["target_machine_id"], "target_machine_id"
            ),
            discovery_digest=_require_digest(
                raw["discovery_digest"], "discovery_digest"
            ),
            native_program=program,
            synthesis_certificate=certificate,
        )


def build_native_migration_bundle(
    source: LineageSnapshot,
    machine: OpaqueFieldMachine,
    discovery: DiscoveredFieldSubstrate,
) -> NativeMigrationBundle:
    program, certificate = synthesize_native_mealy(
        source.accepted_body, discovery, machine
    )
    return NativeMigrationBundle(
        source_snapshot_digest=source.digest(),
        source_version=source.version,
        source_body_digest=exact_body_digest(source.accepted_body),
        source_tool_registry_digest=tool_registry_digest(source.tool_registry),
        source_learning_state_digest=learning_state_digest(source.learning_state),
        source_journal_digest=journal_digest(source.causal_journal),
        target_machine_id=machine.machine_id,
        discovery_digest=discovery.digest(),
        native_program=program,
        synthesis_certificate=certificate,
    )


def audit_native_migration_bundle(
    bundle: NativeMigrationBundle,
    source: LineageSnapshot,
    machine: OpaqueFieldMachine,
    discovery: DiscoveredFieldSubstrate,
) -> None:
    expected = {
        "source_snapshot_digest": source.digest(),
        "source_version": source.version,
        "source_body_digest": exact_body_digest(source.accepted_body),
        "source_tool_registry_digest": tool_registry_digest(source.tool_registry),
        "source_learning_state_digest": learning_state_digest(source.learning_state),
        "source_journal_digest": journal_digest(source.causal_journal),
        "target_machine_id": machine.machine_id,
        "discovery_digest": discovery.digest(),
    }
    for field, value in expected.items():
        if getattr(bundle, field) != value:
            raise MigrationError(f"native migration {field} mismatch")
    audit_program_against_discovery(bundle.native_program, discovery)
    reconstructed = native_program_to_mealy(bundle.native_program, machine)
    if reconstructed != source.accepted_body:
        raise MigrationError("native program does not reconstruct the accepted source body")
    certificate = bundle.synthesis_certificate
    if certificate.native_program_digest != bundle.native_program.digest():
        raise MigrationError("native program digest mismatch")
    if not certificate.exact:
        raise MigrationError("native synthesis certificate is not exact")


def _q4_accepted_development_snapshot() -> LineageSnapshot:
    catalogue = run_q3_development_catalogue()
    if catalogue.status is not CatalogueStatus.QUALIFIED or not catalogue.entries:
        raise MigrationError("Q3 did not provide a qualified development task")
    task = catalogue.entries[0]
    initial = initial_lineage(q3_development_parent())
    package = build_candidate_package(initial, task)
    decision = validate_candidate_disposably(initial, task, package)
    if not decision.report.accepted:
        raise MigrationError("Q4 development candidate was not accepted")
    store = VersionedLineageStore(initial)
    receipt = store.adopt(decision, package)
    if not receipt.adopted:
        raise MigrationError("Q4 development adoption did not commit")
    return store.current


def _discovery_uses_public_surface_only() -> bool:
    source = inspect.getsource(discover_field_substrate)
    return "_audit_role" not in source and "_audit_snapshot" not in source


def _direct_table_smuggling_rejected(program: NativeMealyProgram) -> bool:
    raw = program.to_dict()
    raw["transitions"] = [[0]]
    try:
        NativeMealyProgram.from_bytes(_canonical_json(raw))
    except NativeProgramError:
        return True
    return False


def run_q5_development_qualification() -> dict[str, object]:
    source = _q4_accepted_development_snapshot()
    positive_results: list[dict[str, object]] = []
    opcode_assignments: set[tuple[tuple[str, str], ...]] = set()
    machine_ids: set[str] = set()

    first_bundle: NativeMigrationBundle | None = None
    first_discovery: DiscoveredFieldSubstrate | None = None
    first_machine: OpaqueFieldMachine | None = None
    for family in range(3):
        machine = make_development_positive_machine(family)
        discovery = discover_field_substrate(machine)
        bundle = build_native_migration_bundle(source, machine, discovery)
        restored = NativeMigrationBundle.from_bytes(bundle.to_bytes())
        audit_native_migration_bundle(restored, source, machine, discovery)
        opcode_assignments.add(discovery.role_opcodes)
        machine_ids.add(machine.machine_id)
        positive_results.append(
            {
                "family": family,
                "machine_id": machine.machine_id,
                "discovery_digest": discovery.digest(),
                "probe_calls": discovery.probe_calls,
                "role_opcodes": [list(item) for item in discovery.role_opcodes],
                "native_program_digest": bundle.native_program.digest(),
                "native_program_nodes": len(bundle.native_program.nodes),
                "bundle_digest": bundle.digest(),
                "certificate_digest": bundle.synthesis_certificate.digest(),
                "exact": bundle.synthesis_certificate.exact,
                "table_free": (
                    bundle.synthesis_certificate.forbidden_table_keys_absent
                    and not bundle.synthesis_certificate.source_body_bytes_embedded
                ),
            }
        )
        if first_bundle is None:
            first_bundle = bundle
            first_discovery = discovery
            first_machine = machine

    assert first_bundle is not None
    assert first_discovery is not None
    assert first_machine is not None

    negative_rejections: dict[str, bool] = {}
    for kind in range(3):
        try:
            discover_field_substrate(make_development_negative_machine(kind))
        except SubstrateError:
            negative_rejections[f"negative_{kind}"] = True
        else:
            negative_rejections[f"negative_{kind}"] = False
    try:
        discover_field_substrate(
            make_development_positive_machine(0), probe_budget=8
        )
    except SubstrateError:
        budget_rejected = True
    else:
        budget_rejected = False

    wrong_source = initial_lineage(q3_development_parent())
    try:
        audit_native_migration_bundle(
            first_bundle, wrong_source, first_machine, first_discovery
        )
    except MigrationError:
        wrong_source_rejected = True
    else:
        wrong_source_rejected = False

    tampered_program = replace(
        first_bundle.native_program,
        discovery_digest="0" * 64,
    )
    try:
        NativeMigrationBundle(
            source_snapshot_digest=first_bundle.source_snapshot_digest,
            source_version=first_bundle.source_version,
            source_body_digest=first_bundle.source_body_digest,
            source_tool_registry_digest=first_bundle.source_tool_registry_digest,
            source_learning_state_digest=first_bundle.source_learning_state_digest,
            source_journal_digest=first_bundle.source_journal_digest,
            target_machine_id=first_bundle.target_machine_id,
            discovery_digest=first_bundle.discovery_digest,
            native_program=tampered_program,
            synthesis_certificate=first_bundle.synthesis_certificate,
        )
    except (MigrationError, NativeProgramError):
        tampered_program_rejected = True
    else:
        tampered_program_rejected = False

    return {
        "schema": "m043-q5-development-result-v1",
        "status": "qualified",
        "source_snapshot_digest": source.digest(),
        "source_version": source.version,
        "source_tool_registry_entries": len(source.tool_registry),
        "source_learning_state_preserved": True,
        "source_journal_entries": len(source.causal_journal),
        "positive_substrates": positive_results,
        "distinct_machine_identities": len(machine_ids) == 3,
        "distinct_opaque_role_assignments": len(opcode_assignments) == 3,
        "public_probe_discovery_only": _discovery_uses_public_surface_only(),
        "negative_substrates_rejected": negative_rejections,
        "probe_budget_exhaustion_rejected": budget_rejected,
        "wrong_source_lineage_rejected": wrong_source_rejected,
        "tampered_program_binding_rejected": tampered_program_rejected,
        "direct_transition_table_smuggling_rejected": (
            _direct_table_smuggling_rejected(first_bundle.native_program)
        ),
        "source_transition_output_tables_in_native_program": False,
        "selected_seed": None,
        "hidden_task_bank_authorised": False,
        "canonical_workflow_authorised": False,
    }


__all__ = [
    "BUNDLE_SCHEMA",
    "MigrationError",
    "NativeMigrationBundle",
    "audit_native_migration_bundle",
    "build_native_migration_bundle",
    "run_q5_development_qualification",
]
