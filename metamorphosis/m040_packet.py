"""M040 canonical transport packet for cumulative post-migration plasticity."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Mapping, Sequence

from .m012b_dfa import DFA, canonicalize
from .m013e_runtime import DiscoveredOpcode, DiscoveredSubstrate, OpaqueNativeBody
from .m039_lineage import LineageTool, ToolProvenance

PACKET_SCHEMA = "m040-trans-substrate-lineage-packet/1"
LEARNING_STATE_SCHEMA = "m040-learning-state/2"
_SHA256 = re.compile(r"\A[0-9a-f]{64}\Z")


class M040PacketError(ValueError):
    """The packet is malformed, internally inconsistent or non-canonical."""


def _require_sha(value: str, name: str) -> str:
    if not _SHA256.match(value):
        raise M040PacketError(f"{name} must be canonical lowercase SHA-256 hexadecimal")
    return value


def _sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def dfa_to_mapping(dfa: DFA) -> dict[str, object]:
    canonical = canonicalize(dfa)
    return {
        "alphabet": list(canonical.alphabet),
        "transitions": [list(row) for row in canonical.transitions],
        "accepting": [bool(value) for value in canonical.accepting],
        "initial": canonical.initial,
    }


def dfa_from_mapping(data: Mapping[str, object]) -> DFA:
    alphabet = tuple(int(value) for value in data["alphabet"])
    transitions = tuple(
        tuple(int(value) for value in row)
        for row in data["transitions"]
    )
    accepting = tuple(bool(value) for value in data["accepting"])
    initial = int(data["initial"])
    if alphabet != (0, 1):
        raise M040PacketError("M040 source bodies must use the binary alphabet")
    if len(transitions) != len(accepting) or not transitions:
        raise M040PacketError("source DFA dimensions are inconsistent")
    for row in transitions:
        if len(row) != 2 or any(target < 0 or target >= len(transitions) for target in row):
            raise M040PacketError("source DFA transition is out of range")
    if initial < 0 or initial >= len(transitions):
        raise M040PacketError("source DFA initial state is out of range")
    return canonicalize(DFA(alphabet, transitions, accepting, initial))


@dataclass(frozen=True)
class M040LearningState:
    accepted_candidate_ids: tuple[str, ...]
    lineage_tool_ids: tuple[str, ...]
    causal_tool_use_ids: tuple[str, ...]
    preferred_tool_ids: tuple[str, ...]
    continuation_programs: tuple[tuple[str, ...], ...]
    exploration_depth: int
    remaining_search_nodes: int
    schema: str = LEARNING_STATE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != LEARNING_STATE_SCHEMA:
            raise M040PacketError("unsupported learning-state schema")
        for name, values in (
            ("accepted candidate", self.accepted_candidate_ids),
            ("lineage tool", self.lineage_tool_ids),
            ("causal tool use", self.causal_tool_use_ids),
            ("preferred tool", self.preferred_tool_ids),
        ):
            if len(set(values)) != len(values):
                raise M040PacketError(f"{name} identifiers must be unique")
            for value in values:
                _require_sha(value, f"{name} identifier")
        if not set(self.preferred_tool_ids).issubset(self.lineage_tool_ids):
            raise M040PacketError("preferred tools must belong to the transported lineage tools")
        if not self.continuation_programs:
            raise M040PacketError("the continuation frontier must contain an adopted program")
        for program in self.continuation_programs:
            if not program or len(program) > 3:
                raise M040PacketError("continuation programs must contain one to three tools")
            for tool_id in program:
                _require_sha(tool_id, "continuation-program tool identifier")
            if not set(program).intersection(self.lineage_tool_ids):
                raise M040PacketError("each continuation program must use a lineage-owned tool")
        if self.exploration_depth < 1:
            raise M040PacketError("exploration depth must be positive")
        if self.remaining_search_nodes < 1:
            raise M040PacketError("remaining search nodes must be positive")

    def mapping(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "accepted_candidate_ids": list(self.accepted_candidate_ids),
            "lineage_tool_ids": list(self.lineage_tool_ids),
            "causal_tool_use_ids": list(self.causal_tool_use_ids),
            "preferred_tool_ids": list(self.preferred_tool_ids),
            "continuation_programs": [list(program) for program in self.continuation_programs],
            "exploration_depth": self.exploration_depth,
            "remaining_search_nodes": self.remaining_search_nodes,
        }

    @staticmethod
    def from_mapping(data: Mapping[str, object]) -> "M040LearningState":
        return M040LearningState(
            accepted_candidate_ids=tuple(str(value) for value in data["accepted_candidate_ids"]),
            lineage_tool_ids=tuple(str(value) for value in data["lineage_tool_ids"]),
            causal_tool_use_ids=tuple(str(value) for value in data["causal_tool_use_ids"]),
            preferred_tool_ids=tuple(str(value) for value in data["preferred_tool_ids"]),
            continuation_programs=tuple(
                tuple(str(tool_id) for tool_id in program)
                for program in data["continuation_programs"]
            ),
            exploration_depth=int(data["exploration_depth"]),
            remaining_search_nodes=int(data["remaining_search_nodes"]),
            schema=str(data["schema"]),
        )


def _tool_from_mapping(data: Mapping[str, object]) -> LineageTool:
    provenance_data = data["provenance"]
    if not isinstance(provenance_data, Mapping):
        raise M040PacketError("tool provenance must be a mapping")
    program_data = data["program"]
    if not isinstance(program_data, Sequence) or isinstance(program_data, (str, bytes, bytearray)):
        raise M040PacketError("tool program must be a sequence")
    program: list[Mapping[str, object]] = []
    for step in program_data:
        if not isinstance(step, Mapping):
            raise M040PacketError("tool program steps must be mappings")
        program.append(dict(step))
    tool = LineageTool(
        tool_id=str(data["tool_id"]),
        version=int(data["version"]),
        lineage_id=str(data["lineage_id"]),
        introduced_cycle=int(data["introduced_cycle"]),
        program=tuple(program),
        input_tool_ids=tuple(str(value) for value in data["input_tool_ids"]),
        replay_digest=str(data["replay_digest"]),
        provenance=ToolProvenance(
            origin=str(provenance_data["origin"]),
            construction_kind=str(provenance_data["construction_kind"]),
            introduction_phase=str(provenance_data["introduction_phase"]),
            introduced_by_event=(
                None
                if provenance_data["introduced_by_event"] is None
                else str(provenance_data["introduced_by_event"])
            ),
            protocol_commitment=str(provenance_data["protocol_commitment"]),
        ),
        schema=str(data["schema"]),
    )
    return tool


def discovered_substrate_mapping(substrate: DiscoveredSubstrate) -> list[dict[str, object]]:
    return [
        {
            "opcode": opcode.opcode,
            "arity": opcode.arity,
            "cost": opcode.cost,
            "table": list(opcode.table) if opcode.table is not None else None,
            "stable": opcode.stable,
        }
        for opcode in substrate.opcodes
    ]


def discovered_substrate_from_mapping(
    values: Sequence[Mapping[str, object]],
) -> DiscoveredSubstrate:
    opcodes: list[DiscoveredOpcode] = []
    identifiers: set[str] = set()
    for value in values:
        opcode_id = str(value["opcode"])
        if opcode_id in identifiers:
            raise M040PacketError("discovered opcode identifiers must be unique")
        identifiers.add(opcode_id)
        arity = int(value["arity"])
        cost = int(value["cost"])
        stable = bool(value["stable"])
        raw_table = value["table"]
        table = None if raw_table is None else tuple(int(bit) for bit in raw_table)
        if arity not in (1, 2):
            raise M040PacketError("only unary and binary Boolean opcodes are supported")
        if cost < 0:
            raise M040PacketError("opcode cost must be non-negative")
        if stable and (table is None or len(table) != 2 ** arity):
            raise M040PacketError("stable opcode has an invalid truth table")
        if table is not None and any(bit not in (0, 1) for bit in table):
            raise M040PacketError("opcode truth tables must be Boolean")
        if not stable and table is not None:
            raise M040PacketError("unstable opcodes may not carry a trusted table")
        opcodes.append(DiscoveredOpcode(opcode_id, arity, cost, table, stable))
    return DiscoveredSubstrate(tuple(opcodes), 0, tuple(
        sorted(opcode.opcode for opcode in opcodes if not opcode.stable)
    ))


@dataclass(frozen=True)
class M040TransportPacket:
    protocol_commitment: str
    lineage_id: str
    pre_migration_manifest_digest: str
    source_body: Mapping[str, object]
    source_body_digest: str
    opaque_body_json: str
    opaque_body_sha256: str
    machine_id: str
    discovered_opcodes: tuple[Mapping[str, object], ...]
    tool_registry: tuple[LineageTool, ...]
    learning_state: M040LearningState
    schema: str = PACKET_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != PACKET_SCHEMA:
            raise M040PacketError("unsupported M040 packet schema")
        if not self.protocol_commitment:
            raise M040PacketError("protocol commitment must be non-empty")
        if not self.machine_id:
            raise M040PacketError("machine identifier must be non-empty")
        _require_sha(self.lineage_id, "lineage_id")
        _require_sha(self.pre_migration_manifest_digest, "pre-migration manifest digest")
        _require_sha(self.source_body_digest, "source-body digest")
        _require_sha(self.opaque_body_sha256, "opaque-body digest")
        source = dfa_from_mapping(self.source_body)
        actual_source = hashlib.sha256(
            json.dumps(
                dfa_to_mapping(source),
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        if actual_source != self.source_body_digest:
            raise M040PacketError("source-body digest mismatch")
        if _sha_text(self.opaque_body_json) != self.opaque_body_sha256:
            raise M040PacketError("opaque-body digest mismatch")
        OpaqueNativeBody.from_json(self.opaque_body_json)
        substrate = discovered_substrate_from_mapping(self.discovered_opcodes)
        if not substrate.stable_opcodes:
            raise M040PacketError("packet contains no stable discovered opcode")
        tool_ids = tuple(tool.tool_id for tool in self.tool_registry)
        if len(set(tool_ids)) != len(tool_ids):
            raise M040PacketError("tool registry contains duplicate identifiers")
        for tool in self.tool_registry:
            if tool.lineage_id != self.lineage_id:
                raise M040PacketError("tool belongs to a different lineage")
            if tool.provenance.protocol_commitment != self.protocol_commitment:
                raise M040PacketError("tool protocol commitment differs from the packet")
        if not set(self.learning_state.lineage_tool_ids).issubset(tool_ids):
            raise M040PacketError("learning state refers to an absent lineage tool")
        for program in self.learning_state.continuation_programs:
            if not set(program).issubset(tool_ids):
                raise M040PacketError("continuation frontier refers to an absent tool")

    @staticmethod
    def build(
        *,
        protocol_commitment: str,
        lineage_id: str,
        pre_migration_manifest_digest: str,
        source_dfa: DFA,
        opaque_body: OpaqueNativeBody,
        machine_id: str,
        substrate: DiscoveredSubstrate,
        tool_registry: Sequence[LineageTool],
        learning_state: M040LearningState,
    ) -> "M040TransportPacket":
        source_mapping = dfa_to_mapping(source_dfa)
        source_digest = hashlib.sha256(
            json.dumps(source_mapping, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        opaque_json = opaque_body.to_json()
        return M040TransportPacket(
            protocol_commitment=protocol_commitment,
            lineage_id=lineage_id,
            pre_migration_manifest_digest=pre_migration_manifest_digest,
            source_body=source_mapping,
            source_body_digest=source_digest,
            opaque_body_json=opaque_json,
            opaque_body_sha256=_sha_text(opaque_json),
            machine_id=machine_id,
            discovered_opcodes=tuple(discovered_substrate_mapping(substrate)),
            tool_registry=tuple(tool_registry),
            learning_state=learning_state,
        )

    def mapping(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "protocol_commitment": self.protocol_commitment,
            "lineage_id": self.lineage_id,
            "pre_migration_manifest_digest": self.pre_migration_manifest_digest,
            "source_body": dict(self.source_body),
            "source_body_digest": self.source_body_digest,
            "opaque_body_json": self.opaque_body_json,
            "opaque_body_sha256": self.opaque_body_sha256,
            "machine_id": self.machine_id,
            "discovered_opcodes": [dict(value) for value in self.discovered_opcodes],
            "tool_registry": [tool.mapping() for tool in self.tool_registry],
            "learning_state": self.learning_state.mapping(),
        }

    def to_json(self) -> str:
        return json.dumps(self.mapping(), sort_keys=True, separators=(",", ":"))

    def sha256(self) -> str:
        return _sha_text(self.to_json())

    @staticmethod
    def from_json(raw: str) -> "M040TransportPacket":
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as error:
            raise M040PacketError("packet is not valid JSON") from error
        if not isinstance(data, Mapping):
            raise M040PacketError("packet root must be a mapping")
        discovered = data["discovered_opcodes"]
        tools = data["tool_registry"]
        learning = data["learning_state"]
        if not isinstance(discovered, Sequence) or isinstance(discovered, (str, bytes, bytearray)):
            raise M040PacketError("discovered opcodes must be a sequence")
        if not isinstance(tools, Sequence) or isinstance(tools, (str, bytes, bytearray)):
            raise M040PacketError("tool registry must be a sequence")
        if not isinstance(learning, Mapping):
            raise M040PacketError("learning state must be a mapping")
        parsed_discovered: list[Mapping[str, object]] = []
        for value in discovered:
            if not isinstance(value, Mapping):
                raise M040PacketError("discovered opcode entries must be mappings")
            parsed_discovered.append(dict(value))
        parsed_tools: list[LineageTool] = []
        for value in tools:
            if not isinstance(value, Mapping):
                raise M040PacketError("tool entries must be mappings")
            parsed_tools.append(_tool_from_mapping(value))
        packet = M040TransportPacket(
            schema=str(data["schema"]),
            protocol_commitment=str(data["protocol_commitment"]),
            lineage_id=str(data["lineage_id"]),
            pre_migration_manifest_digest=str(data["pre_migration_manifest_digest"]),
            source_body=dict(data["source_body"]),
            source_body_digest=str(data["source_body_digest"]),
            opaque_body_json=str(data["opaque_body_json"]),
            opaque_body_sha256=str(data["opaque_body_sha256"]),
            machine_id=str(data["machine_id"]),
            discovered_opcodes=tuple(parsed_discovered),
            tool_registry=tuple(parsed_tools),
            learning_state=M040LearningState.from_mapping(learning),
        )
        if packet.to_json() != raw:
            raise M040PacketError("packet JSON is not canonical")
        return packet

    def source_dfa(self) -> DFA:
        return dfa_from_mapping(self.source_body)

    def opaque_body(self) -> OpaqueNativeBody:
        return OpaqueNativeBody.from_json(self.opaque_body_json)

    def discovered_substrate(self) -> DiscoveredSubstrate:
        return discovered_substrate_from_mapping(self.discovered_opcodes)
