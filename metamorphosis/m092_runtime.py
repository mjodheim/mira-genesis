"""The M092 runtime vocabulary. Nothing here imports a historical module.

M092-A's first version still reached into `m090_language` for `LanguageError`,
`MetaLanguageState` and the capability constants. Those are data types rather than semantics, so the
authority claim survived it -- but "the legacy module is loaded and we promise it is not consulted"
is a weaker statement than "the legacy module is not there". This module exists so the second
statement can be made, and so a fresh runtime can be assembled from files that have never heard of
M090.

Three things live here.

* **A refusal taxonomy.** Conservation used to compare `refused == refused`, which passes when two
  implementations refuse for entirely different reasons. `RefusalCode` is an implementation-independent
  vocabulary; both the frozen reference path and the state-owned path are normalized into it, and
  conservation compares codes.

* **A neutral language representation.** `RuntimePrimitive` and `RuntimeLanguage` carry exactly what
  the dispatcher needs. Conversion from M090's `MetaLanguageState` is a *migration* concern and lives
  in `m092_migration`, never on the runtime path.

* **`SubstrateError`.** One exception type carrying a `RefusalCode`, so a refusal is a value the
  caller can compare rather than a string it has to parse.

Historical M090 and M091 objects are converted *into* this representation by migration tooling. The
conversion never runs at runtime, and this module has no import that could pull it in.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Sequence

RUNTIME_SCHEMA = "m092-runtime-v1"


class RefusalCode(str, Enum):
    """Why an execution refused, in terms neither implementation owns.

    The codes describe *situations in the representation*, not exception classes. Two
    implementations that refuse the same input for the same reason must produce the same code even
    though their internal errors differ entirely -- that is the whole point.
    """

    UNKNOWN_OPERATION = "unknown_operation"
    INVALID_SELECTOR = "invalid_selector"
    INVALID_ARGUMENT_ROLE = "invalid_argument_role"
    INVALID_LITERAL = "invalid_literal"
    INVALID_SLOT_INDEX = "invalid_slot_index"
    INVALID_INPUT_INDEX = "invalid_input_index"
    STACK_UNDERFLOW = "stack_underflow"
    BODY_LENGTH_EXCEEDED = "body_length_exceeded"
    STACK_BOUND_EXCEEDED = "stack_bound_exceeded"
    MALFORMED_PROGRAM = "malformed_program"
    MALFORMED_STATE = "malformed_state"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    SIGNATURE_MISMATCH = "signature_mismatch"
    UNDEFINED_PRIMITIVE = "undefined_primitive"
    UNRESOLVED_PARAMETER = "unresolved_parameter"
    PARAMETER_OUT_OF_DOMAIN = "parameter_out_of_domain"


class SubstrateError(Exception):
    """A refusal, carrying the semantic code that makes it comparable across implementations."""

    def __init__(self, code: RefusalCode, detail: str = "") -> None:
        super().__init__(f"{code.value}: {detail}" if detail else code.value)
        self.code = code
        self.detail = detail


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def digest_of(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


# ---------------------------------------------------------------------------------------------
# The language layer, as neutral data
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class RuntimePrimitive:
    """One language operation: a body over micro-operations, plus its declared parameter kinds."""

    primitive_id: str
    parameter_kinds: tuple[str, ...]
    body: tuple[tuple[str, object], ...]
    origin: str = "inherited"
    provenance: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()

    @property
    def arity(self) -> int:
        return len(self.parameter_kinds)

    def to_dict(self) -> dict[str, object]:
        return {
            "primitive_id": self.primitive_id,
            "parameter_kinds": list(self.parameter_kinds),
            "body": [[name, argument] for name, argument in self.body],
            "origin": self.origin,
            "provenance": list(self.provenance),
            "capabilities": list(self.capabilities),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "RuntimePrimitive":
        expected = {
            "primitive_id", "parameter_kinds", "body", "origin", "provenance", "capabilities",
        }
        if set(data) != expected:
            raise SubstrateError(
                RefusalCode.MALFORMED_STATE, "primitive fields differ from the closed schema",
            )
        return cls(
            primitive_id=str(data["primitive_id"]),
            parameter_kinds=tuple(str(k) for k in data["parameter_kinds"]),  # type: ignore[union-attr]
            body=tuple(
                (str(step[0]), step[1]) for step in data["body"]  # type: ignore[index,union-attr]
            ),
            origin=str(data["origin"]),
            provenance=tuple(str(p) for p in data["provenance"]),  # type: ignore[union-attr]
            capabilities=tuple(str(c) for c in data["capabilities"]),  # type: ignore[union-attr]
        )


@dataclass(frozen=True)
class RuntimeLanguage:
    """The language registry the dispatcher consults. Data, with no behaviour of its own."""

    primitives: tuple[RuntimePrimitive, ...]
    language_version: int = 0
    provenance: tuple[str, ...] = ()
    schema: str = RUNTIME_SCHEMA

    def definition(self, primitive_id: str) -> RuntimePrimitive | None:
        return next(
            (item for item in self.primitives if item.primitive_id == primitive_id), None
        )

    @property
    def primitive_ids(self) -> tuple[str, ...]:
        return tuple(item.primitive_id for item in self.primitives)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "language_version": self.language_version,
            "primitives": [item.to_dict() for item in self.primitives],
            "provenance": list(self.provenance),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "RuntimeLanguage":
        if set(data) != {"schema", "language_version", "primitives", "provenance"}:
            raise SubstrateError(
                RefusalCode.MALFORMED_STATE, "language fields differ from the closed schema",
            )
        if data.get("schema") != RUNTIME_SCHEMA:
            raise SubstrateError(RefusalCode.MALFORMED_STATE, "runtime language schema mismatch")
        return cls(
            primitives=tuple(
                RuntimePrimitive.from_dict(item) for item in data["primitives"]  # type: ignore[union-attr]
            ),
            language_version=int(data["language_version"]),  # type: ignore[arg-type]
            provenance=tuple(str(p) for p in data["provenance"]),  # type: ignore[union-attr]
        )

    def digest(self) -> str:
        return digest_of(self.to_dict())


__all__ = [
    "RUNTIME_SCHEMA", "RefusalCode", "RuntimeLanguage", "RuntimePrimitive", "SubstrateError",
    "canonical_bytes", "digest_of",
]
