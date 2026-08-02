"""M024 — a portable passport for executable bodies and learned rewrite tools.

M013e transported a bounded competence to an opaque substrate. M020 added bounded
self-rewrite and internal learned tools. M024 makes the self-rewrite state itself
portable: active source, rollback archive, adopted digests, primitive tool configuration
and learned patch tools are serialised into one canonical, hashed passport.

Import validates the complete bundle before creating live objects. A corrupted source,
operation, tool name, digest history or envelope hash is rejected rather than partially
loaded.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping, Sequence

from .m020_self_rewrite import (
    BinaryOperatorRewriteTool,
    ComparisonOperatorRewriteTool,
    ConstantRewriteTool,
    LearnedRewriteTool,
    PatchOperation,
    ToolRegistry,
    VersionedCodeBody,
    apply_patch,
    source_digest,
    validate_source,
)


PASSPORT_VERSION = "m024-rewrite-passport/1"
ENVELOPE_VERSION = "m024-rewrite-envelope/1"
_LOWERCASE_HEX = frozenset("0123456789abcdef")


class InvalidPassport(ValueError):
    """Raised when a rewrite passport is incomplete, inconsistent or corrupted."""


@dataclass(frozen=True)
class RewritePassport:
    version: str
    function_name: str
    active_source: str
    archive: tuple[str, ...]
    adopted_digests: tuple[str, ...]
    primitive_tools: tuple[dict[str, object], ...]
    learned_tools: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "function_name": self.function_name,
            "active_source": self.active_source,
            "archive": list(self.archive),
            "adopted_digests": list(self.adopted_digests),
            "primitive_tools": [dict(row) for row in self.primitive_tools],
            "learned_tools": [dict(row) for row in self.learned_tools],
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
        )

    def sha256(self) -> str:
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()


def _operation_to_dict(operation: PatchOperation) -> dict[str, object]:
    return {
        "kind": operation.kind,
        "index": operation.index,
        "value": operation.value,
    }


def _operation_from_dict(data: Mapping[str, object]) -> PatchOperation:
    try:
        kind = data["kind"]
        index = data["index"]
        value = data["value"]
    except KeyError as error:
        raise InvalidPassport("invalid patch operation") from error
    if not isinstance(kind, str) or type(index) is not int:
        raise InvalidPassport("patch operation kind and index have invalid types")
    if index < 0:
        raise InvalidPassport("patch operation index must be non-negative")
    if type(value) not in (int, str):
        raise InvalidPassport("patch operation value must be an integer or string")
    if kind not in {"constant", "binary_operator", "comparison_operator"}:
        raise InvalidPassport(f"unsupported patch operation kind: {kind}")
    return PatchOperation(kind, index, value)


def _primitive_to_dict(tool: object) -> dict[str, object]:
    if isinstance(tool, ConstantRewriteTool):
        return {
            "kind": "constant",
            "name": tool.name,
            "values": list(tool.values),
        }
    if isinstance(tool, BinaryOperatorRewriteTool):
        return {"kind": "binary_operator", "name": tool.name}
    if isinstance(tool, ComparisonOperatorRewriteTool):
        return {"kind": "comparison_operator", "name": tool.name}
    raise InvalidPassport(f"unsupported primitive rewrite tool: {type(tool).__name__}")


def _primitive_from_dict(data: Mapping[str, object]):
    kind = data.get("kind")
    name = data.get("name")
    if not isinstance(kind, str) or not isinstance(name, str):
        raise InvalidPassport("primitive tool kind and name must be strings")
    if kind == "constant":
        raw_values = data.get("values")
        if not isinstance(raw_values, list) or not raw_values:
            raise InvalidPassport("constant tool requires a non-empty value list")
        if any(type(value) is not int for value in raw_values):
            raise InvalidPassport("constant tool values must be integers")
        tool = ConstantRewriteTool(tuple(int(value) for value in raw_values))
    elif kind == "binary_operator":
        tool = BinaryOperatorRewriteTool()
    elif kind == "comparison_operator":
        tool = ComparisonOperatorRewriteTool()
    else:
        raise InvalidPassport(f"unsupported primitive tool kind: {kind}")
    if tool.name != name:
        raise InvalidPassport("primitive tool name does not match its kind")
    return tool


def _learned_to_dict(tool: LearnedRewriteTool) -> dict[str, object]:
    return {
        "name": tool.name,
        "operations": [_operation_to_dict(operation) for operation in tool.operations],
    }


def _validate_sources(
    function_name: str,
    active_source: str,
    archive: Sequence[str],
    adopted_digests: Sequence[str],
) -> None:
    validate_source(active_source, function_name)
    for source in archive:
        validate_source(source, function_name)
    if not adopted_digests:
        raise InvalidPassport("adopted digest history must not be empty")
    if any(
        len(digest) != 64 or any(character not in _LOWERCASE_HEX for character in digest)
        for digest in adopted_digests
    ):
        raise InvalidPassport("adopted digest history contains an invalid digest")
    if adopted_digests[-1] != source_digest(active_source):
        raise InvalidPassport("active source does not match the latest adopted digest")

    # Rollbacks append to the digest ledger while removing entries from the archive,
    # so the current archive is an ordered subsequence rather than necessarily a
    # prefix. Every rollback source must nevertheless have existed in the ledger
    # before the current active body.
    prior_digests = iter(adopted_digests[:-1])
    for source in archive:
        expected = source_digest(source)
        if not any(digest == expected for digest in prior_digests):
            raise InvalidPassport(
                "archive source does not match the adopted digest history"
            )


def create_passport(
    body: VersionedCodeBody,
    registry: ToolRegistry,
) -> RewritePassport:
    """Capture a complete deterministic self-rewrite state."""
    _validate_sources(
        body.function_name,
        body.active_source,
        body.archive,
        body.adopted_digests,
    )
    return RewritePassport(
        version=PASSPORT_VERSION,
        function_name=body.function_name,
        active_source=body.active_source,
        archive=tuple(body.archive),
        adopted_digests=tuple(body.adopted_digests),
        primitive_tools=tuple(_primitive_to_dict(tool) for tool in registry.primitives),
        learned_tools=tuple(_learned_to_dict(tool) for tool in registry.learned),
    )


def export_passport(
    body: VersionedCodeBody,
    registry: ToolRegistry,
) -> str:
    """Return a canonical integrity-protected envelope."""
    passport = create_passport(body, registry)
    payload = passport.to_dict()
    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    envelope = {
        "version": ENVELOPE_VERSION,
        "payload": payload,
        "payload_sha256": hashlib.sha256(payload_json.encode("utf-8")).hexdigest(),
    }
    return json.dumps(envelope, sort_keys=True, separators=(",", ":"))


def _passport_from_payload(payload: Mapping[str, object]) -> RewritePassport:
    if payload.get("version") != PASSPORT_VERSION:
        raise InvalidPassport("unsupported rewrite-passport version")
    try:
        function_name = payload["function_name"]
        active_source = payload["active_source"]
        archive_raw = payload["archive"]
        digests_raw = payload["adopted_digests"]
        primitive_raw = payload["primitive_tools"]
        learned_raw = payload["learned_tools"]
    except KeyError as error:
        raise InvalidPassport(f"missing passport field: {error.args[0]}") from error

    if not isinstance(function_name, str) or not isinstance(active_source, str):
        raise InvalidPassport("function_name and active_source must be strings")
    if not isinstance(archive_raw, list) or not all(
        isinstance(source, str) for source in archive_raw
    ):
        raise InvalidPassport("archive must be a list of source strings")
    if not isinstance(digests_raw, list) or not all(
        isinstance(digest, str) for digest in digests_raw
    ):
        raise InvalidPassport("adopted_digests must be a list of strings")
    if not isinstance(primitive_raw, list) or not all(
        isinstance(row, dict) for row in primitive_raw
    ):
        raise InvalidPassport("primitive_tools must be a list of objects")
    if not isinstance(learned_raw, list) or not all(
        isinstance(row, dict) for row in learned_raw
    ):
        raise InvalidPassport("learned_tools must be a list of objects")

    passport = RewritePassport(
        version=PASSPORT_VERSION,
        function_name=function_name,
        active_source=active_source,
        archive=tuple(archive_raw),
        adopted_digests=tuple(digests_raw),
        primitive_tools=tuple(dict(row) for row in primitive_raw),
        learned_tools=tuple(dict(row) for row in learned_raw),
    )
    _validate_sources(
        passport.function_name,
        passport.active_source,
        passport.archive,
        passport.adopted_digests,
    )
    return passport


def import_passport(raw: str) -> tuple[VersionedCodeBody, ToolRegistry, RewritePassport]:
    """Verify an envelope completely, then rehydrate body and tool registry."""
    try:
        envelope = json.loads(raw)
    except json.JSONDecodeError as error:
        raise InvalidPassport("passport envelope is not valid JSON") from error
    if not isinstance(envelope, dict):
        raise InvalidPassport("passport envelope must be an object")
    if envelope.get("version") != ENVELOPE_VERSION:
        raise InvalidPassport("unsupported rewrite-envelope version")
    payload = envelope.get("payload")
    claimed_digest = envelope.get("payload_sha256")
    if not isinstance(payload, dict) or not isinstance(claimed_digest, str):
        raise InvalidPassport("passport envelope is incomplete")
    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    actual_digest = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
    if actual_digest != claimed_digest:
        raise InvalidPassport("passport payload digest mismatch")

    passport = _passport_from_payload(payload)
    primitives = tuple(_primitive_from_dict(row) for row in passport.primitive_tools)
    registry = ToolRegistry(primitives=primitives, learned=[])

    seen_names: set[str] = set()
    for row in passport.learned_tools:
        name = row.get("name")
        raw_operations = row.get("operations")
        if not isinstance(name, str) or not isinstance(raw_operations, list):
            raise InvalidPassport("invalid learned tool")
        if name in seen_names:
            raise InvalidPassport("duplicate learned tool name")
        seen_names.add(name)
        if not raw_operations or not all(
            isinstance(operation, dict) for operation in raw_operations
        ):
            raise InvalidPassport("learned tool operations must be non-empty objects")
        operations = tuple(
            _operation_from_dict(operation) for operation in raw_operations
        )
        reconstructed = registry.absorb(operations)
        if reconstructed.name != name:
            raise InvalidPassport("learned tool name does not match its operations")

    # Every learned trace must remain syntactically replayable on at least one source in
    # the passport lineage. It need not apply to the current body after later rewrites.
    lineage_sources = (passport.active_source,) + passport.archive
    for tool in registry.learned:
        if not any(
            _trace_applies(source, tool.operations) for source in lineage_sources
        ):
            raise InvalidPassport(
                f"learned tool {tool.name!r} is not replayable on the passport lineage"
            )

    body = VersionedCodeBody(
        function_name=passport.function_name,
        active_source=passport.active_source,
        archive=list(passport.archive),
        adopted_digests=list(passport.adopted_digests),
    )
    return body, registry, passport


def _trace_applies(source: str, operations: Sequence[PatchOperation]) -> bool:
    try:
        apply_patch(source, operations)
    except (SyntaxError, TypeError, ValueError):
        return False
    return True
