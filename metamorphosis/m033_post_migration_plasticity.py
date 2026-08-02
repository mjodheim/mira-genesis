"""M033 — deterministic post-migration lineage construction.

This module does not implement or reveal the M033 primary task family.  It constructs
independent lineage variants from one validated M032 packet so the later experiment can
attribute differences to explicit ablations rather than accidental state drift.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json

from .m012b_dfa import DFA
from .m013e_runtime import OpaqueNativeBody
from .m020_self_rewrite import ToolRegistry, VersionedCodeBody
from .m024_rewrite_passport import import_passport
from .m032_trans_substrate_lifecycle import (
    PortableLearningState,
    TransSubstratePacket,
)


class LineageVariant(StrEnum):
    COMPLETE = "complete"
    OUTPUT_ONLY = "output_only"
    LEARNING_STATE_ABLATED = "learning_state_ablated"
    LEARNED_TOOLS_ABLATED = "learned_tools_ablated"


@dataclass
class PostMigrationLineage:
    """One isolated packet-derived lineage at the post-migration reveal boundary."""

    variant: LineageVariant
    body: VersionedCodeBody
    registry: ToolRegistry
    source_dfa: DFA
    opaque_body: OpaqueNativeBody
    learning_state: PortableLearningState
    can_update_learning_state: bool
    can_rewrite: bool
    source_packet_sha256: str

    def canonical_snapshot(self) -> str:
        """Serialise all evaluator-visible state except the explicit variant label."""

        return json.dumps(
            {
                "active_source": self.body.active_source,
                "function_name": self.body.function_name,
                "archive": list(self.body.archive),
                "adopted_digests": list(self.body.adopted_digests),
                "primitive_tools": [tool.name for tool in self.registry.primitives],
                "learned_tools": [
                    {
                        "name": tool.name,
                        "operations": [list(operation.key()) for operation in tool.operations],
                    }
                    for tool in self.registry.learned
                ],
                "source_dfa": self.source_dfa.to_dict(),
                "opaque_body": json.loads(self.opaque_body.to_json()),
                "learning_state": self.learning_state.to_dict(),
                "can_update_learning_state": self.can_update_learning_state,
                "can_rewrite": self.can_rewrite,
                "source_packet_sha256": self.source_packet_sha256,
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    def snapshot_sha256(self) -> str:
        return hashlib.sha256(self.canonical_snapshot().encode("utf-8")).hexdigest()


def _rehydrate_base(packet_json: str) -> tuple[
    TransSubstratePacket,
    VersionedCodeBody,
    ToolRegistry,
    DFA,
    OpaqueNativeBody,
]:
    packet = TransSubstratePacket.from_json(packet_json)
    body, registry, _ = import_passport(packet.rewrite_passport_json)
    return (
        packet,
        body,
        registry,
        DFA.from_dict(packet.source_dfa),
        OpaqueNativeBody.from_json(packet.opaque_body_json),
    )


def build_packet_derived_lineage(
    packet_json: str,
    variant: LineageVariant,
) -> PostMigrationLineage:
    """Build one independent M033 lineage from the same validated M032 packet.

    The function rehydrates the packet for every call.  No body, archive, registry or
    learned tool is shared between variants.
    """

    packet, body, registry, source_dfa, opaque_body = _rehydrate_base(packet_json)
    learning_state = packet.learning_state
    can_update_learning_state = True
    can_rewrite = True

    if variant is LineageVariant.OUTPUT_ONLY:
        can_update_learning_state = False
        can_rewrite = False
    elif variant is LineageVariant.LEARNING_STATE_ABLATED:
        learning_state = PortableLearningState()
    elif variant is LineageVariant.LEARNED_TOOLS_ABLATED:
        registry.learned.clear()
    elif variant is not LineageVariant.COMPLETE:
        raise ValueError(f"unsupported M033 lineage variant: {variant}")

    return PostMigrationLineage(
        variant=variant,
        body=body,
        registry=registry,
        source_dfa=source_dfa,
        opaque_body=opaque_body,
        learning_state=learning_state,
        can_update_learning_state=can_update_learning_state,
        can_rewrite=can_rewrite,
        source_packet_sha256=packet.sha256(),
    )


def build_packet_derived_lineages(
    packet_json: str,
) -> dict[LineageVariant, PostMigrationLineage]:
    """Construct every packet-derived M033 lineage from independent rehydrations."""

    return {
        variant: build_packet_derived_lineage(packet_json, variant)
        for variant in LineageVariant
    }
