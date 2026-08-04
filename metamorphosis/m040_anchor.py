"""Deterministic M040 lineage-anchor task and proposal derivation."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import hashlib
import random
from typing import Mapping, Sequence

from .m012b_dfa import DFA
from .m038_certificate import (
    MAXIMUM_PREFIX_COUNT,
    MAXIMUM_SEARCH_NODES,
    proved_structural_incapacity,
)
from .m038_journal import encode
from .m039_engine import dfa_digest
from .m039_lineage import (
    LineageTool,
    ORIGIN_LINEAGE_CONSTRUCTED,
    ORIGIN_PROTOCOL_SUPPLIED,
)
from .m040_packet import M040TransportPacket
from .structural import Atom, apply_atom, normalize_dfa

ANCHOR_SCHEMA = "m040-lineage-anchor-task/1"
ANCHOR_DOMAIN = b"m040-lineage-anchor-task-v1"
MAXIMUM_COMBINED_PROGRAMS = 2_048


class M040AnchorError(ValueError):
    """The transported registry cannot produce a valid bounded anchor task."""


@dataclass(frozen=True)
class LineageAnchorTask:
    task_seed: int
    parent_digest: str
    target: DFA
    generating_tool_ids: tuple[str, ...]
    generating_program: tuple[Atom, ...]
    anchor_tool_ids: tuple[str, ...]
    suffix_tool_ids: tuple[str, ...]
    programs_considered: int
    schema: str = ANCHOR_SCHEMA

    def mapping(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "task_seed": self.task_seed,
            "parent_digest": self.parent_digest,
            "target_digest": dfa_digest(self.target),
            "target_states": self.target.n_states,
            "generating_tool_ids": list(self.generating_tool_ids),
            "generating_program": [atom.to_list() for atom in self.generating_program],
            "anchor_tool_ids": list(self.anchor_tool_ids),
            "suffix_tool_ids": list(self.suffix_tool_ids),
            "programs_considered": self.programs_considered,
        }

    def digest(self) -> str:
        return hashlib.sha256(ANCHOR_DOMAIN + encode(self.mapping())).hexdigest()


def _tool_atoms(tool: LineageTool) -> tuple[Atom, ...]:
    atoms: list[Atom] = []
    for step in tool.program:
        raw = step.get("atom")
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
            raise M040AnchorError("tool program step lacks an atom sequence")
        atoms.append(Atom.from_list(raw))
    return tuple(atoms)


def _apply_program(
    founder: DFA,
    registry: Mapping[str, LineageTool],
    tool_ids: Sequence[str],
) -> tuple[DFA | None, tuple[Atom, ...]]:
    current: DFA | None = founder
    atoms: list[Atom] = []
    for tool_id in tool_ids:
        tool = registry.get(str(tool_id))
        if tool is None:
            raise M040AnchorError("derived program refers to an absent transported tool")
        for atom in _tool_atoms(tool):
            current = apply_atom(current, atom)  # type: ignore[arg-type]
            atoms.append(atom)
            if current is None:
                return None, tuple(atoms)
    return current, tuple(atoms)


def derive_lineage_anchors(packet: M040TransportPacket) -> tuple[tuple[str, ...], ...]:
    """Derive canonical contiguous fragments containing a pre-migration lineage tool."""

    registry_ids = {tool.tool_id for tool in packet.tool_registry}
    lineage_ids = {
        tool.tool_id
        for tool in packet.tool_registry
        if tool.provenance.origin == ORIGIN_LINEAGE_CONSTRUCTED
    }
    anchors: list[tuple[str, ...]] = []
    seen: set[tuple[str, ...]] = set()
    for continuation in packet.learning_state.continuation_programs:
        if not set(continuation).issubset(registry_ids):
            raise M040AnchorError("continuation program refers to an absent tool")
        for start in range(len(continuation)):
            for length in (1, 2):
                end = start + length
                if end > len(continuation):
                    continue
                fragment = tuple(continuation[start:end])
                if not set(fragment).intersection(lineage_ids):
                    continue
                if fragment not in seen:
                    seen.add(fragment)
                    anchors.append(fragment)
    if not anchors:
        raise M040AnchorError("packet produced no lineage-owned anchor fragment")
    return tuple(anchors)


def _primitive_suffixes(
    packet: M040TransportPacket,
) -> tuple[tuple[str, ...], ...]:
    primitive_ids = tuple(
        tool.tool_id
        for tool in packet.tool_registry
        if tool.provenance.origin == ORIGIN_PROTOCOL_SUPPLIED
    )
    if not primitive_ids:
        raise M040AnchorError("packet contains no protocol-supplied primitive tool")
    return tuple((tool_id,) for tool_id in primitive_ids) + tuple(
        tuple(values) for values in product(primitive_ids, repeat=2)
    )


def derive_adapted_programs(
    packet: M040TransportPacket,
    *,
    task_seed: int,
    maximum_depth: int,
) -> tuple[tuple[str, ...], ...]:
    """Derive all bounded anchor-plus-suffix programs in seed-defined order."""

    anchors = list(derive_lineage_anchors(packet))
    suffixes = list(_primitive_suffixes(packet))
    rng = random.Random(task_seed)
    rng.shuffle(anchors)
    rng.shuffle(suffixes)
    combined: list[tuple[str, ...]] = []
    seen: set[tuple[str, ...]] = set()
    for anchor in anchors:
        for suffix in suffixes:
            program = anchor + suffix
            if len(program) > maximum_depth or program in seen:
                continue
            seen.add(program)
            combined.append(program)
            if len(combined) >= MAXIMUM_COMBINED_PROGRAMS:
                return tuple(combined)
    if not combined:
        raise M040AnchorError("bounded anchor enumeration produced no combined program")
    return tuple(combined)


def primitive_reachable_digests(
    founder: DFA,
    primitive_registry: Sequence[LineageTool],
    *,
    maximum_depth: int,
    maximum_nodes: int,
) -> tuple[set[str], int]:
    """Enumerate birth-registry results within an explicit equal-resource bound."""

    digests: set[str] = set()
    nodes = 0
    stop = False

    def descend(current: DFA, remaining: int) -> None:
        nonlocal nodes, stop
        if stop:
            return
        if remaining == 0:
            digests.add(dfa_digest(normalize_dfa(current)))
            return
        for tool in primitive_registry:
            nodes += 1
            if nodes > maximum_nodes:
                stop = True
                return
            body: DFA | None = current
            for atom in _tool_atoms(tool):
                body = apply_atom(body, atom)  # type: ignore[arg-type]
                if body is None:
                    break
            if body is not None:
                descend(body, remaining - 1)
            if stop:
                return

    for depth in range(1, maximum_depth + 1):
        descend(founder, depth)
        if stop:
            break
    return digests, nodes


def generate_lineage_anchor_task(
    *,
    packet: M040TransportPacket,
    founder: DFA,
    task_seed: int,
    maximum_depth: int,
    node_budget: int,
    observations: Sequence[tuple[int, ...]],
) -> LineageAnchorTask:
    """Choose the first admissible hidden anchor task under frozen bounded rules."""

    registry = {tool.tool_id: tool for tool in packet.tool_registry}
    primitives = tuple(
        tool
        for tool in packet.tool_registry
        if tool.provenance.origin == ORIGIN_PROTOCOL_SUPPLIED
    )
    reachable, _ = primitive_reachable_digests(
        founder,
        primitives,
        maximum_depth=maximum_depth,
        maximum_nodes=node_budget,
    )
    anchors = set(derive_lineage_anchors(packet))
    programs = derive_adapted_programs(
        packet,
        task_seed=task_seed,
        maximum_depth=maximum_depth,
    )
    for index, program_ids in enumerate(programs, start=1):
        raw, expanded = _apply_program(founder, registry, program_ids)
        if raw is None:
            continue
        target = normalize_dfa(raw)
        if target.n_states <= founder.n_states:
            continue
        if dfa_digest(target) in reachable:
            continue
        evidence = {word: target.accepts(word) for word in observations}
        certificate = proved_structural_incapacity(
            founder,
            evidence,
            maximum_search_nodes=MAXIMUM_SEARCH_NODES,
            maximum_prefix_count=MAXIMUM_PREFIX_COUNT,
        )
        if not certificate.proves_incapacity():
            continue
        anchor = next(
            candidate
            for candidate in anchors
            if len(candidate) < len(program_ids) and program_ids[: len(candidate)] == candidate
        )
        suffix = program_ids[len(anchor) :]
        if len(suffix) not in (1, 2):
            raise M040AnchorError("selected anchor program has an invalid suffix length")
        return LineageAnchorTask(
            task_seed=task_seed,
            parent_digest=dfa_digest(founder),
            target=target,
            generating_tool_ids=program_ids,
            generating_program=expanded,
            anchor_tool_ids=anchor,
            suffix_tool_ids=suffix,
            programs_considered=index,
        )
    raise M040AnchorError(
        "no lineage anchor plus bounded primitive suffix produced an admissible task"
    )
