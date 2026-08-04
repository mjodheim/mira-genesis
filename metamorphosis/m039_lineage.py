"""M039 cumulative-lineage core.

This module deliberately contains no sealed task and runs no experiment.  It defines the
objects that a later three-cycle engine must use: a persistent registry, computed tool
provenance, causal reuse records, a contiguous lineage manifest and the deliberately narrow
input surface of a seed-to-head replay.

The M038 journal and first canonical artefact remain frozen.  M039 uses a new schema rather
than widening M038's closed event vocabulary after its result.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Mapping, Sequence

from .m038_journal import encode

LINEAGE_SCHEMA = "m039-lineage-manifest/1"
TOOL_SCHEMA = "m039-lineage-tool/1"
REPLAY_INPUT_SCHEMA = "m039-replay-inputs/1"

LINEAGE_MANIFEST_DOMAIN = b"m039-lineage-manifest-v1"
TOOL_ID_DOMAIN = b"m039-lineage-tool-v1"
LINEAGE_ID_DOMAIN = b"m039-lineage-id-v1"
CYCLE_SEED_DOMAIN = b"m039-cycle-seed-v1"

_SHA256 = re.compile(r"\A[0-9a-f]{64}\Z")
_EVENT_HASH = _SHA256

ORIGIN_PROTOCOL_SUPPLIED = "protocol_supplied"
ORIGIN_LINEAGE_CONSTRUCTED = "lineage_constructed"
ORIGIN_EXTERNAL_DEVELOPMENT = "external_development"

KIND_PRIMITIVE = "primitive"
KIND_COMPOSITION = "composition"
KIND_ACCEPTED_TRACE = "accepted_transformation_trace"

PHASE_BIRTH = "birth"
PHASE_CYCLE = "cycle"
PHASE_POST_RUN = "post_run"

_VALID_ORIGINS = {
    ORIGIN_PROTOCOL_SUPPLIED,
    ORIGIN_LINEAGE_CONSTRUCTED,
    ORIGIN_EXTERNAL_DEVELOPMENT,
}
_VALID_KINDS = {KIND_PRIMITIVE, KIND_COMPOSITION, KIND_ACCEPTED_TRACE}
_VALID_PHASES = {PHASE_BIRTH, PHASE_CYCLE, PHASE_POST_RUN}


class M039IntegrityError(ValueError):
    """The lineage, registry, provenance or replay anchors are inconsistent."""


def _hex_digest(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + encode(value)).hexdigest()


def _require_sha256(value: str, *, name: str) -> str:
    if not _SHA256.match(value):
        raise M039IntegrityError(f"{name} must be canonical lowercase SHA-256 hexadecimal")
    return value


def derive_lineage_id(seed: int, protocol_commitment: str) -> str:
    if seed < 0:
        raise ValueError("seed must be non-negative")
    if not protocol_commitment:
        raise ValueError("protocol commitment must be non-empty")
    return _hex_digest(
        LINEAGE_ID_DOMAIN,
        {"seed": seed, "protocol_commitment": protocol_commitment},
    )


def derive_cycle_seed(master_seed: int, cycle: int, protocol_commitment: str) -> int:
    """Derive independent deterministic 64-bit cycle seeds without mutable RNG coupling."""

    if master_seed < 0:
        raise ValueError("master seed must be non-negative")
    if cycle not in (1, 2, 3):
        raise ValueError("M039 has exactly cycles 1, 2 and 3")
    if not protocol_commitment:
        raise ValueError("protocol commitment must be non-empty")
    digest = hashlib.sha256(
        CYCLE_SEED_DOMAIN
        + encode(
            {
                "master_seed": master_seed,
                "cycle": cycle,
                "protocol_commitment": protocol_commitment,
            }
        )
    ).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


@dataclass(frozen=True)
class ToolProvenance:
    origin: str
    construction_kind: str
    introduction_phase: str
    introduced_by_event: str | None
    protocol_commitment: str

    def __post_init__(self) -> None:
        if self.origin not in _VALID_ORIGINS:
            raise ValueError(f"unknown tool origin {self.origin!r}")
        if self.construction_kind not in _VALID_KINDS:
            raise ValueError(f"unknown construction kind {self.construction_kind!r}")
        if self.introduction_phase not in _VALID_PHASES:
            raise ValueError(f"unknown introduction phase {self.introduction_phase!r}")
        if not self.protocol_commitment:
            raise ValueError("protocol commitment must be non-empty")
        if self.introduced_by_event is not None:
            _require_sha256(self.introduced_by_event, name="introduced_by_event")

    def mapping(self) -> dict[str, object]:
        return {
            "origin": self.origin,
            "construction_kind": self.construction_kind,
            "introduction_phase": self.introduction_phase,
            "introduced_by_event": self.introduced_by_event,
            "protocol_commitment": self.protocol_commitment,
        }


@dataclass(frozen=True)
class LineageTool:
    tool_id: str
    version: int
    lineage_id: str
    introduced_cycle: int
    program: tuple[Mapping[str, object], ...]
    input_tool_ids: tuple[str, ...]
    replay_digest: str
    provenance: ToolProvenance
    schema: str = TOOL_SCHEMA

    def __post_init__(self) -> None:
        _require_sha256(self.tool_id, name="tool_id")
        _require_sha256(self.lineage_id, name="lineage_id")
        _require_sha256(self.replay_digest, name="replay_digest")
        if self.version < 1:
            raise ValueError("tool version must be positive")
        if self.introduced_cycle not in (0, 1, 2, 3):
            raise ValueError("introduced cycle must be birth (0) or cycle 1..3")
        if not self.program:
            raise ValueError("a tool program must contain at least one operation")
        if len(set(self.input_tool_ids)) != len(self.input_tool_ids):
            raise ValueError("input tool IDs must be unique")
        for tool_id in self.input_tool_ids:
            _require_sha256(tool_id, name="input tool ID")

    def mapping(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "tool_id": self.tool_id,
            "version": self.version,
            "lineage_id": self.lineage_id,
            "introduced_cycle": self.introduced_cycle,
            "program": [dict(step) for step in self.program],
            "input_tool_ids": list(self.input_tool_ids),
            "replay_digest": self.replay_digest,
            "provenance": self.provenance.mapping(),
        }


@dataclass(frozen=True)
class ToolUse:
    tool_id: str
    cycle: int
    candidate_id: str
    adopted: bool
    proposing_block_index: int

    def __post_init__(self) -> None:
        _require_sha256(self.tool_id, name="used tool ID")
        _require_sha256(self.candidate_id, name="candidate ID")
        if self.cycle not in (1, 2, 3):
            raise ValueError("tool use cycle must be 1..3")
        if self.proposing_block_index < 0:
            raise ValueError("proposing block index must be non-negative")

    def mapping(self) -> dict[str, object]:
        return {
            "tool_id": self.tool_id,
            "cycle": self.cycle,
            "candidate_id": self.candidate_id,
            "adopted": self.adopted,
            "proposing_block_index": self.proposing_block_index,
        }


def protocol_primitive_tool(
    *,
    lineage_id: str,
    protocol_commitment: str,
    primitive_name: str,
    program: Sequence[Mapping[str, object]],
    ordinal: int,
) -> LineageTool:
    """Create one birth-language entry. It is valid but can never count for Gate 2."""

    if ordinal < 0:
        raise ValueError("primitive ordinal must be non-negative")
    canonical_program = tuple(dict(step) for step in program)
    source = {
        "schema": TOOL_SCHEMA,
        "kind": "birth-primitive",
        "lineage_id": lineage_id,
        "protocol_commitment": protocol_commitment,
        "primitive_name": primitive_name,
        "ordinal": ordinal,
        "program": [dict(step) for step in canonical_program],
    }
    replay_digest = _hex_digest(TOOL_ID_DOMAIN, {"replay": source})
    tool_id = _hex_digest(TOOL_ID_DOMAIN, {**source, "replay_digest": replay_digest})
    return LineageTool(
        tool_id=tool_id,
        version=1,
        lineage_id=lineage_id,
        introduced_cycle=0,
        program=canonical_program,
        input_tool_ids=(),
        replay_digest=replay_digest,
        provenance=ToolProvenance(
            origin=ORIGIN_PROTOCOL_SUPPLIED,
            construction_kind=KIND_PRIMITIVE,
            introduction_phase=PHASE_BIRTH,
            introduced_by_event=None,
            protocol_commitment=protocol_commitment,
        ),
    )


def compose_lineage_tool(
    *,
    lineage_id: str,
    protocol_commitment: str,
    introduced_cycle: int,
    introduced_by_event: str,
    input_tools: Sequence[LineageTool],
    program: Sequence[Mapping[str, object]],
    version: int = 1,
) -> LineageTool:
    """Compose a lineage-owned macro from tools that were already in its registry."""

    if introduced_cycle not in (1, 2, 3):
        raise ValueError("a constructed tool must be introduced during cycle 1..3")
    _require_sha256(introduced_by_event, name="introduced_by_event")
    if not input_tools:
        raise ValueError("a composition must consume at least one committed input tool")
    if any(tool.lineage_id != lineage_id for tool in input_tools):
        raise M039IntegrityError("a lineage cannot compose from another lineage's registry")
    if any(tool.introduced_cycle >= introduced_cycle for tool in input_tools):
        raise M039IntegrityError("all composition inputs must predate the construction cycle")

    canonical_program = tuple(dict(step) for step in program)
    input_ids = tuple(tool.tool_id for tool in input_tools)
    source = {
        "schema": TOOL_SCHEMA,
        "kind": "lineage-composition",
        "lineage_id": lineage_id,
        "protocol_commitment": protocol_commitment,
        "introduced_cycle": introduced_cycle,
        "introduced_by_event": introduced_by_event,
        "version": version,
        "input_tool_ids": list(input_ids),
        "program": [dict(step) for step in canonical_program],
    }
    replay_digest = _hex_digest(TOOL_ID_DOMAIN, {"replay": source})
    tool_id = _hex_digest(TOOL_ID_DOMAIN, {**source, "replay_digest": replay_digest})
    return LineageTool(
        tool_id=tool_id,
        version=version,
        lineage_id=lineage_id,
        introduced_cycle=introduced_cycle,
        program=canonical_program,
        input_tool_ids=input_ids,
        replay_digest=replay_digest,
        provenance=ToolProvenance(
            origin=ORIGIN_LINEAGE_CONSTRUCTED,
            construction_kind=KIND_COMPOSITION,
            introduction_phase=PHASE_CYCLE,
            introduced_by_event=introduced_by_event,
            protocol_commitment=protocol_commitment,
        ),
    )


def gate2_eligible(
    tool: LineageTool,
    *,
    valid_construction_event_hashes: Sequence[str],
    registry_before_construction: Sequence[str],
    uses: Sequence[ToolUse],
    ablation_required_tool_ids: Sequence[str],
) -> bool:
    """Compute, never trust, the bounded Gate-2 eligibility described by ADR 0003."""

    valid_events = set(valid_construction_event_hashes)
    registry_before = set(registry_before_construction)
    required = set(ablation_required_tool_ids)
    causal_later_use = any(
        use.tool_id == tool.tool_id
        and use.adopted
        and use.cycle > tool.introduced_cycle
        for use in uses
    )
    return (
        tool.provenance.origin == ORIGIN_LINEAGE_CONSTRUCTED
        and tool.provenance.construction_kind == KIND_COMPOSITION
        and tool.provenance.introduction_phase == PHASE_CYCLE
        and tool.provenance.introduced_by_event in valid_events
        and set(tool.input_tool_ids).issubset(registry_before)
        and causal_later_use
        and tool.tool_id in required
    )


@dataclass(frozen=True)
class CycleManifest:
    cycle: int
    cycle_seed: int
    starting_body_digest: str
    target_digest: str
    ending_body_digest: str
    evidence_digest: str
    certificate_digest: str
    compact_trace_head: str
    checkpoint_digest: str
    journal_head: str
    decision_transcript_digest: str
    accepted_candidate_id: str
    accepted_program_digest: str
    used_tool_ids: tuple[str, ...]
    constructed_tool_ids: tuple[str, ...]
    rollback_restored_exactly: bool
    functional_counters: Mapping[str, int]
    audit_counters: Mapping[str, int]

    def __post_init__(self) -> None:
        if self.cycle not in (1, 2, 3):
            raise ValueError("cycle manifest index must be 1..3")
        if self.cycle_seed < 0:
            raise ValueError("cycle seed must be non-negative")
        for name in (
            "starting_body_digest",
            "target_digest",
            "ending_body_digest",
            "evidence_digest",
            "certificate_digest",
            "compact_trace_head",
            "checkpoint_digest",
            "journal_head",
            "decision_transcript_digest",
            "accepted_candidate_id",
            "accepted_program_digest",
        ):
            _require_sha256(getattr(self, name), name=name)
        for tool_id in self.used_tool_ids + self.constructed_tool_ids:
            _require_sha256(tool_id, name="cycle tool ID")

    def mapping(self) -> dict[str, object]:
        return {
            "cycle": self.cycle,
            "cycle_seed": self.cycle_seed,
            "starting_body_digest": self.starting_body_digest,
            "target_digest": self.target_digest,
            "ending_body_digest": self.ending_body_digest,
            "evidence_digest": self.evidence_digest,
            "certificate_digest": self.certificate_digest,
            "compact_trace_head": self.compact_trace_head,
            "checkpoint_digest": self.checkpoint_digest,
            "journal_head": self.journal_head,
            "decision_transcript_digest": self.decision_transcript_digest,
            "accepted_candidate_id": self.accepted_candidate_id,
            "accepted_program_digest": self.accepted_program_digest,
            "used_tool_ids": list(self.used_tool_ids),
            "constructed_tool_ids": list(self.constructed_tool_ids),
            "rollback_restored_exactly": self.rollback_restored_exactly,
            "functional_counters": dict(self.functional_counters),
            "audit_counters": dict(self.audit_counters),
        }


@dataclass(frozen=True)
class LineageManifest:
    master_seed: int
    protocol_commitment: str
    lineage_id: str
    initial_body_digest: str
    cycles: tuple[CycleManifest, ...]
    tool_registry: tuple[LineageTool, ...]
    tool_uses: tuple[ToolUse, ...]
    ablation_required_tool_ids: tuple[str, ...]
    final_body_digest: str
    schema: str = LINEAGE_SCHEMA

    def __post_init__(self) -> None:
        if self.master_seed < 0:
            raise ValueError("master seed must be non-negative")
        if not self.protocol_commitment:
            raise ValueError("protocol commitment must be non-empty")
        _require_sha256(self.lineage_id, name="lineage_id")
        _require_sha256(self.initial_body_digest, name="initial_body_digest")
        _require_sha256(self.final_body_digest, name="final_body_digest")
        if tuple(cycle.cycle for cycle in self.cycles) != (1, 2, 3):
            raise M039IntegrityError("a complete M039 manifest must contain cycles 1, 2 and 3")
        if self.cycles[0].starting_body_digest != self.initial_body_digest:
            raise M039IntegrityError("cycle 1 does not start from the manifest founder")
        for previous, current in zip(self.cycles, self.cycles[1:]):
            if previous.ending_body_digest != current.starting_body_digest:
                raise M039IntegrityError("cycle bodies do not form one contiguous lineage")
        if self.cycles[-1].ending_body_digest != self.final_body_digest:
            raise M039IntegrityError("final body digest does not match cycle 3")
        if any(
            cycle.starting_body_digest == cycle.ending_body_digest
            for cycle in self.cycles
        ):
            raise M039IntegrityError("every accepted cycle must change the active body")
        registry_ids = [tool.tool_id for tool in self.tool_registry]
        if len(registry_ids) != len(set(registry_ids)):
            raise M039IntegrityError("tool registry contains duplicate IDs")
        if any(tool.lineage_id != self.lineage_id for tool in self.tool_registry):
            raise M039IntegrityError("all tools must belong to the manifest lineage")
        if any(tool_id not in set(registry_ids) for tool_id in self.ablation_required_tool_ids):
            raise M039IntegrityError("ablation names a tool absent from the final registry")

    def mapping(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "master_seed": self.master_seed,
            "protocol_commitment": self.protocol_commitment,
            "lineage_id": self.lineage_id,
            "initial_body_digest": self.initial_body_digest,
            "cycles": [cycle.mapping() for cycle in self.cycles],
            "tool_registry": [tool.mapping() for tool in self.tool_registry],
            "tool_uses": [use.mapping() for use in self.tool_uses],
            "ablation_required_tool_ids": list(self.ablation_required_tool_ids),
            "final_body_digest": self.final_body_digest,
        }

    def digest(self) -> str:
        return _hex_digest(LINEAGE_MANIFEST_DOMAIN, self.mapping())


@dataclass(frozen=True)
class ReplayInputs:
    """The only original-run values a full replay may receive.

    Expected digests are external anchors, not construction hints.  Bodies, targets,
    observations, selected candidates, programs and tool outputs are deliberately absent.
    """

    master_seed: int
    protocol_commitment: str
    primitive_registry_digest: str
    expected_manifest_digest: str
    expected_final_body_digest: str
    expected_cycle_journal_heads: tuple[str, str, str]
    schema: str = REPLAY_INPUT_SCHEMA

    def __post_init__(self) -> None:
        if self.master_seed < 0:
            raise ValueError("master seed must be non-negative")
        if not self.protocol_commitment:
            raise ValueError("protocol commitment must be non-empty")
        _require_sha256(self.primitive_registry_digest, name="primitive_registry_digest")
        _require_sha256(self.expected_manifest_digest, name="expected_manifest_digest")
        _require_sha256(self.expected_final_body_digest, name="expected_final_body_digest")
        for head in self.expected_cycle_journal_heads:
            _require_sha256(head, name="expected cycle journal head")

    def mapping(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "master_seed": self.master_seed,
            "protocol_commitment": self.protocol_commitment,
            "primitive_registry_digest": self.primitive_registry_digest,
            "expected_manifest_digest": self.expected_manifest_digest,
            "expected_final_body_digest": self.expected_final_body_digest,
            "expected_cycle_journal_heads": list(self.expected_cycle_journal_heads),
        }


def verify_replayed_manifest(replayed: LineageManifest, expected: ReplayInputs) -> None:
    """Compare a recomputed lineage only with externally committed anchors."""

    if replayed.master_seed != expected.master_seed:
        raise M039IntegrityError("replay used a different master seed")
    if replayed.protocol_commitment != expected.protocol_commitment:
        raise M039IntegrityError("replay used a different protocol commitment")
    if replayed.digest() != expected.expected_manifest_digest:
        raise M039IntegrityError("replayed manifest digest diverged")
    if replayed.final_body_digest != expected.expected_final_body_digest:
        raise M039IntegrityError("replayed final body diverged")
    heads = tuple(cycle.journal_head for cycle in replayed.cycles)
    if heads != expected.expected_cycle_journal_heads:
        raise M039IntegrityError("one or more replayed cycle journal heads diverged")
