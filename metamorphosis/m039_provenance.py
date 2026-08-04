"""Independent M039 provenance verification over the authoritative journal bytes.

The lineage engine may propose that a tool is Gate-2 eligible, but it cannot establish that
by repeating fields from the tool itself.  This verifier starts from the persisted journal
records and the final manifest, verifies the journal's internal chain, then requires exact
correspondence between ToolConstructed/ToolReused events and the registry/usage claims.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Mapping, Sequence

from .m038_journal import decode
from .m039_journal import LineageEvent, verify_lineage_records
from .m039_lineage import (
    LineageManifest,
    LineageTool,
    M039IntegrityError,
    ORIGIN_LINEAGE_CONSTRUCTED,
    ToolUse,
    gate2_eligible,
)


def _events(records: Sequence[bytes], manifest: LineageManifest) -> tuple[LineageEvent, ...]:
    parsed: list[LineageEvent] = []
    for raw in records:
        value = decode(raw)
        if not isinstance(value, Mapping):
            raise M039IntegrityError("M039 journal record is not a mapping")
        parsed.append(LineageEvent.from_mapping(value))
    if not parsed:
        raise M039IntegrityError("M039 provenance cannot be verified from an empty journal")

    # This establishes byte authority and internal causal continuity.  The independent
    # seed-to-head replay remains responsible for the external origin anchor.
    verify_lineage_records(
        records,
        protocol_commitment=manifest.protocol_commitment,
        lineage_id=manifest.lineage_id,
        expected_initial_state_digest=parsed[0].previous_state_digest,
        expected_head=parsed[-1].event_hash,
        expected_final_state_digest=parsed[-1].result_state_digest,
    )
    return tuple(parsed)


def _tool_event_matches(event: LineageEvent, tool: LineageTool) -> bool:
    parameters = dict(event.operation_parameters)
    return (
        event.event_type == "ToolConstructed"
        and event.lineage_id == tool.lineage_id
        and event.protocol_commitment == tool.provenance.protocol_commitment
        and event.cycle == tool.introduced_cycle
        and parameters.get("construction_event_id") == tool.provenance.introduced_by_event
        and parameters.get("tool") == tool.mapping()
    )


def _use_event_matches(event: LineageEvent, use: ToolUse) -> bool:
    return (
        event.event_type == "ToolReused"
        and event.cycle == use.cycle
        and dict(event.operation_parameters) == use.mapping()
    )


def journal_verified_gate2_tool_ids(
    manifest: LineageManifest,
    records: Sequence[bytes],
) -> tuple[str, ...]:
    """Return only tools whose construction, later use and ablation all verify.

    A malformed or contradictory provenance record fails loudly.  A well-formed constructed
    tool that was not later required simply does not appear in the returned tuple.
    """

    events = _events(records, manifest)
    registry = {tool.tool_id: tool for tool in manifest.tool_registry}
    if len(registry) != len(manifest.tool_registry):
        raise M039IntegrityError("final registry contains duplicate tool IDs")

    construction_by_id: dict[str, list[LineageEvent]] = defaultdict(list)
    construction_sequence: dict[str, int] = {}
    for event in events:
        if event.event_type != "ToolConstructed":
            continue
        identifier = dict(event.operation_parameters).get("construction_event_id")
        if not isinstance(identifier, str):
            raise M039IntegrityError("ToolConstructed lacks a string construction_event_id")
        construction_by_id[identifier].append(event)
        construction_sequence[identifier] = event.sequence

    use_events = tuple(event for event in events if event.event_type == "ToolReused")
    claimed_uses = tuple(manifest.tool_uses)
    unmatched_use_events = list(use_events)
    for use in claimed_uses:
        match = next(
            (event for event in unmatched_use_events if _use_event_matches(event, use)),
            None,
        )
        if match is None:
            raise M039IntegrityError(
                f"manifest tool use {use.tool_id} in cycle {use.cycle} lacks its exact ToolReused event"
            )
        unmatched_use_events.remove(match)
    if unmatched_use_events:
        raise M039IntegrityError("journal contains ToolReused events absent from the manifest")

    verified: list[str] = []
    for tool in manifest.tool_registry:
        if tool.provenance.origin != ORIGIN_LINEAGE_CONSTRUCTED:
            continue
        identifier = tool.provenance.introduced_by_event
        if identifier is None:
            raise M039IntegrityError("lineage-constructed tool lacks its construction identifier")
        matches = construction_by_id.get(identifier, [])
        if len(matches) != 1:
            raise M039IntegrityError(
                f"tool {tool.tool_id} requires exactly one construction event, found {len(matches)}"
            )
        construction = matches[0]
        if not _tool_event_matches(construction, tool):
            raise M039IntegrityError(
                f"ToolConstructed event does not exactly describe tool {tool.tool_id}"
            )

        input_tools: list[LineageTool] = []
        for input_id in tool.input_tool_ids:
            input_tool = registry.get(input_id)
            if input_tool is None:
                raise M039IntegrityError(
                    f"constructed tool {tool.tool_id} consumes an absent input {input_id}"
                )
            if input_tool.introduced_cycle >= tool.introduced_cycle:
                raise M039IntegrityError(
                    f"constructed tool {tool.tool_id} consumes an input that did not predate it"
                )
            input_tools.append(input_tool)

        relevant_uses = tuple(use for use in claimed_uses if use.tool_id == tool.tool_id)
        for use in relevant_uses:
            matching_event = next(event for event in use_events if _use_event_matches(event, use))
            if matching_event.sequence <= construction.sequence:
                raise M039IntegrityError("ToolReused occurs before its ToolConstructed event")

        registry_before = tuple(
            candidate.tool_id
            for candidate in manifest.tool_registry
            if candidate.introduced_cycle < tool.introduced_cycle
        )
        if gate2_eligible(
            tool,
            valid_construction_event_hashes=(identifier,),
            registry_before_construction=registry_before,
            uses=relevant_uses,
            ablation_required_tool_ids=manifest.ablation_required_tool_ids,
        ):
            verified.append(tool.tool_id)

    unclaimed_constructions = {
        identifier
        for identifier in construction_by_id
        if not any(
            tool.provenance.introduced_by_event == identifier
            for tool in manifest.tool_registry
        )
    }
    if unclaimed_constructions:
        raise M039IntegrityError("journal contains construction events absent from the registry")

    return tuple(sorted(verified))
