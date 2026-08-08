"""M059: the lineage judges whether its substrate still suits it.

Every migration until now happened because the protocol said so. M058 closed the last gap in
*how* the lineage crosses — it discovers the instruction set, learns what the operations do,
composes its tools — but not *why* or *when*. Nothing made it judge that its substrate no longer
suits the task in front of it.

M059 supplies two substrates and no ranking between them. Both are scanned, neither is described.
The lineage attempts a capability where it currently lives, and moves only when it cannot express
it there and can express it elsewhere.

A timing-based design was tried first and rejected: JavaScript beats WebAssembly at every
per-call workload, and with the loop moved inside the module the comparison inverts at ten
million iterations because V8 eliminates the JavaScript loop. That measures an optimiser, not a
substrate. See `experiments/M059/PROTOCOL.md`.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Mapping, Sequence

from metamorphosis.m058_instruction_discovery import M058Error


class M059Error(ValueError):
    """Raised when an M059 artifact violates the bounded protocol."""


def _digest(domain: bytes, value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(domain + payload).hexdigest()


RESPONSE_SCHEMA = "m059-node-response-v1"

#: The two signature shapes. Only the shapes are declared; what either contains is discovered.
SHAPES: dict[str, int] = {"f64": 0x7C, "i32": 0x7F}
OPCODE_SPACE = tuple(range(0x00, 0x100))
SCAN_PAIRS: tuple[tuple[int, int], ...] = ((12, 5), (7, 3), (-8, 3))

_LOCAL_GET = 0x20
_END = 0x0B


def _uleb(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def _vec(items: Sequence[bytes]) -> bytes:
    return _uleb(len(items)) + b"".join(items)


def _section(identifier: int, payload: bytes) -> bytes:
    return bytes([identifier]) + _uleb(len(payload)) + payload


def _name(text: str) -> bytes:
    encoded = text.encode("utf-8")
    return _uleb(len(encoded)) + encoded


def candidate_module(opcode: int, value_type: int, export: str = "f") -> bytes:
    signature = bytes([0x60]) + _vec([bytes([value_type])] * 2) + _vec([bytes([value_type])])
    inner = _vec([]) + bytes([_LOCAL_GET, 0, _LOCAL_GET, 1, opcode]) + bytes([_END])
    return (
        b"\x00asm\x01\x00\x00\x00"
        + _section(1, _vec([signature]))
        + _section(3, _vec([_uleb(0)]))
        + _section(7, _vec([_name(export) + bytes([0x00]) + _uleb(0)]))
        + _section(10, _vec([_uleb(len(inner)) + inner]))
    )


def operations_module(opcodes: Sequence[str], value_type: int) -> bytes:
    """One module exposing every discovered operation of a substrate."""
    signature = bytes([0x60]) + _vec([bytes([value_type])] * 2) + _vec([bytes([value_type])])
    bodies = []
    for name in opcodes:
        inner = _vec([]) + bytes([_LOCAL_GET, 0, _LOCAL_GET, 1, int(name, 16)]) + bytes([_END])
        bodies.append(_uleb(len(inner)) + inner)
    return (
        b"\x00asm\x01\x00\x00\x00"
        + _section(1, _vec([signature]))
        + _section(3, _vec([_uleb(0)] * len(opcodes)))
        + _section(7, _vec([_name(name) + bytes([0x00]) + _uleb(index) for index, name in enumerate(opcodes)]))
        + _section(10, _vec(bodies))
    )


@dataclass(frozen=True)
class M059Protocol:
    max_expression_size: int = 7
    judgement_budget: int = 200_000
    starting_substrate: str = "f64"
    node_timeout_seconds: float = 300.0
    schema: str = "m059-substrate-judgement-protocol-v1"

    def __post_init__(self) -> None:
        if self.max_expression_size != 7 or self.judgement_budget != 200_000:
            raise M059Error("M059 judgement bounds are frozen")
        if self.starting_substrate not in SHAPES:
            raise M059Error("the starting substrate must be one of the declared shapes")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "max_expression_size": self.max_expression_size,
            "judgement_budget": self.judgement_budget,
            "starting_substrate": self.starting_substrate,
            "shapes": sorted(SHAPES),
            "opcode_space": len(OPCODE_SPACE),
        }

    def digest(self) -> str:
        return _digest(b"m059-substrate-judgement-protocol-v1\0", self.to_dict())


M059_PROTOCOL = M059Protocol()


def _runtime_script() -> Path:
    return Path(__file__).resolve().with_name("m059_wasm_runtime.mjs")


def _node_call(mode: str, request: Mapping[str, object], protocol: M059Protocol) -> Mapping[str, object]:
    payload = json.dumps(request, sort_keys=True, separators=(",", ":")).encode("utf-8")
    try:
        completed = subprocess.run(
            ["node", str(_runtime_script()), mode],
            input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=protocol.node_timeout_seconds, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise M059Error(f"Node runtime unavailable or timed out: {type(exc).__name__}") from exc
    try:
        response = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise M059Error("Node runtime returned malformed output") from exc
    if completed.returncode != 0 or not isinstance(response, Mapping) or response.get("fatal_error"):
        detail = response.get("fatal_error") if isinstance(response, Mapping) else completed.stderr.decode("utf-8", "replace")
        raise M059Error(f"Node runtime failed: {detail}")
    if response.get("schema") != RESPONSE_SCHEMA or response.get("mode") != mode:
        raise M059Error("Node runtime response identity mismatch")
    result = response.get("result")
    if not isinstance(result, Mapping):
        raise M059Error("Node runtime result is not an object")
    return result


def scan_substrate(shape: str, protocol: M059Protocol = M059_PROTOCOL) -> Mapping[str, object]:
    """Discover what one substrate contains. Nothing describes it in advance."""
    if shape not in SHAPES:
        raise M059Error("unknown signature shape")
    value_type = SHAPES[shape]
    candidates = {
        f"{opcode:#04x}": base64.b64encode(candidate_module(opcode, value_type)).decode("ascii")
        for opcode in OPCODE_SPACE
    }
    return _node_call("scan", {
        "candidates": candidates,
        "pairs": [list(pair) for pair in SCAN_PAIRS],
        "export_name": "f",
    }, protocol)


#: Three task families. The first two reverse which substrate is inadequate; the third is
#: expressible where the lineage already lives and must produce a refusal.
def task_families() -> dict[str, dict[str, object]]:
    return {
        "bitwise_difference": {
            "arity": 2,
            "observations": [
                {"args": [a, b], "expected": a ^ b}
                for a, b in ((12, 5), (7, 3), (9, 9), (6, 1), (15, 8))
            ],
            "hidden": [
                {"args": [a, b], "expected": a ^ b} for a, b in ((10, 3), (255, 15), (1, 1))
            ],
        },
        "fractional_mean": {
            "arity": 3,
            "observations": [
                {"args": list(a), "expected": sum(a) / 3}
                for a in ((1, 2, 4), (6, 3, 9), (-4, 7, 0), (5, -5, 10), (2, 2, 2))
            ],
            "hidden": [
                {"args": list(a), "expected": sum(a) / 3} for a in ((9, 1, 2), (-3, -3, -3), (7, 7, 7))
            ],
        },
        "larger_of_two": {
            "arity": 2,
            "observations": [
                {"args": [a, b], "expected": max(a, b)}
                for a, b in ((12, 5), (7, 3), (-8, 3), (4, 4), (0, -2))
            ],
            "hidden": [
                {"args": [a, b], "expected": max(a, b)} for a, b in ((9, -1), (-7, -7), (12, 4))
            ],
        },
    }


def judge_family(
    family: Mapping[str, object], current: str, alternative: str,
    discovered: Mapping[str, Sequence[str]], protocol: M059Protocol = M059_PROTOCOL,
) -> Mapping[str, object]:
    """One mechanism, three possible outcomes. The refusal is not a separate branch."""
    return _node_call("judge", {
        "current": current,
        "alternative": alternative,
        "current_wasm": base64.b64encode(operations_module(discovered[current], SHAPES[current])).decode("ascii"),
        "alternative_wasm": base64.b64encode(operations_module(discovered[alternative], SHAPES[alternative])).decode("ascii"),
        "observations": list(family["observations"]),
        "arity": int(family["arity"]),
        "max_size": protocol.max_expression_size,
        "budget": protocol.judgement_budget,
    }, protocol)


@dataclass
class M059Manifest:
    mapping: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return dict(self.mapping)

    def digest(self) -> str:
        return _digest(b"m059-substrate-judgement-manifest-v1\0", self.mapping)


def run_m059_substrate_judgement(protocol: M059Protocol = M059_PROTOCOL) -> M059Manifest:
    """Three judgements: move, move back, and stay."""
    scans = {shape: scan_substrate(shape, protocol) for shape in sorted(SHAPES)}
    discovered = {shape: sorted(scan["valid"]) for shape, scan in scans.items()}
    for shape, names in discovered.items():
        if not names:
            raise M059Error(f"the scan discovered no operation in {shape}")

    families = task_families()
    order = ("bitwise_difference", "fractional_mean", "larger_of_two")
    current = protocol.starting_substrate
    journey = [current]
    judgements: dict[str, Mapping[str, object]] = {}
    for name in order:
        alternative = next(shape for shape in SHAPES if shape != current)
        verdict = judge_family(families[name], current, alternative, discovered, protocol)
        judgements[name] = verdict
        if verdict["decision"] == "migrate":
            current = str(verdict["substrate"])
            journey.append(current)

    # The judgement must reverse, or it is a fact about the substrates rather than about the task.
    migrations = [name for name in order if judgements[name]["decision"] == "migrate"]
    targets = {str(judgements[name]["substrate"]) for name in migrations}
    if len(targets) < 2:
        raise M059Error("the judgement never reversed; no situation distinguished the substrates")
    if judgements["larger_of_two"]["decision"] != "stay":
        raise M059Error("a capability the current substrate expresses did not produce a refusal")

    # Every synthesized body is verified on arguments the judgement never saw.
    verified: dict[str, bool] = {}
    for name in order:
        verdict = judgements[name]
        chosen = verdict["there"] if verdict["decision"] == "migrate" else verdict["here"]
        if not chosen or chosen.get("status") != "synthesized":
            raise M059Error(f"no body was accepted for {name}")
        shape = str(verdict["substrate"])
        module = _emit_from(chosen["expression"], int(families[name]["arity"]), SHAPES[shape], name)
        result = _node_call("verify", {
            "tool_modules": {name: base64.b64encode(module).decode("ascii")},
            "checks": {name: list(families[name]["hidden"])},
        }, protocol)["verified"]
        verified[name] = bool(result[name])
    if not all(verified.values()):
        raise M059Error("an accepted body failed on the hidden domain")

    mapping = {
        "schema": "m059-substrate-judgement-manifest-v1",
        "status": "development_pending_qualification",
        "protocol_digest": protocol.digest(),
        "shapes_declared": sorted(SHAPES),
        "substrate_ranking_supplied": False,
        "operations_discovered": {shape: len(names) for shape, names in sorted(discovered.items())},
        "operations_rejected": {shape: int(scan["rejected_count"]) for shape, scan in sorted(scans.items())},
        "starting_substrate": protocol.starting_substrate,
        "journey": journey,
        "decisions": {name: str(judgements[name]["decision"]) for name in order},
        "reasons": {name: str(judgements[name]["reason"]) for name in order},
        "current_substrate_outcome": {
            name: str(judgements[name]["here"]["status"]) for name in order
        },
        "candidates_constructed_here": {
            name: int(judgements[name]["here"]["candidates_constructed"]) for name in order
        },
        "expression_sizes": {
            name: int((judgements[name]["there"] or judgements[name]["here"])["expression_size"])
            for name in order
        },
        "migrations": migrations,
        "distinct_migration_targets": sorted(targets),
        "refusals": [name for name in order if judgements[name]["decision"] == "stay"],
        "hidden_domain_verified": verified,
        "arbitrary_code_generation": False,
        "network_authority": False,
        "repository_authority": False,
        "credential_authority": False,
        "deployment_authority": False,
        "canonical": False,
    }
    return M059Manifest(mapping)


def _emit_from(expression: Mapping[str, object], arity: int, value_type: int, export: str) -> bytes:
    """Emit a module for an accepted expression, in the substrate that produced it."""
    import struct

    def instructions(node: Mapping[str, object]) -> bytes:
        if "atom" in node:
            atom = str(node["atom"])
            if atom == "k":
                if value_type == 0x7C:
                    return bytes([0x44]) + struct.pack("<d", float(arity))
                return bytes([0x41]) + _sleb(arity)
            index = int(atom[1:])
            if not 0 <= index < arity:
                raise M059Error("expression reads a parameter the tool does not have")
            return bytes([_LOCAL_GET, index])
        return (
            instructions(node["left"])
            + instructions(node["right"])
            + bytes([int(str(node["operation"]), 16)])
        )

    signature = bytes([0x60]) + _vec([bytes([value_type])] * arity) + _vec([bytes([value_type])])
    inner = _vec([]) + instructions(expression) + bytes([_END])
    return (
        b"\x00asm\x01\x00\x00\x00"
        + _section(1, _vec([signature]))
        + _section(3, _vec([_uleb(0)]))
        + _section(7, _vec([_name(export) + bytes([0x00]) + _uleb(0)]))
        + _section(10, _vec([_uleb(len(inner)) + inner]))
    )


def _sleb(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if (value == 0 and not byte & 0x40) or (value == -1 and byte & 0x40):
            out.append(byte)
            return bytes(out)
        out.append(byte | 0x80)


__all__ = [
    "M059Error", "M059Manifest", "M059Protocol", "M059_PROTOCOL", "OPCODE_SPACE", "SCAN_PAIRS",
    "SHAPES", "candidate_module", "judge_family", "operations_module",
    "run_m059_substrate_judgement", "scan_substrate", "task_families",
]
