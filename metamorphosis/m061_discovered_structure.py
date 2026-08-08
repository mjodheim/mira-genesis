"""M061: the experiment around the structural scans.

M060 migrated the whole body and authored every structural instruction it used. Its result named
that as the next thing to remove, and named the difficulty: a branch has no observable value, only
an effect on what runs next.

This module runs the three scaffolds, resolves what they characterised, checks the resolution
against what M060 authored, and then proves the recovered opcodes are usable by building a working
loop out of nothing else.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Mapping

from metamorphosis.m061_structural_discovery import (
    M060_AUTHORED_STRUCTURAL, OPCODE_SPACE, PRESUPPOSED, SCAFFOLDS, M061Error, build_copy_loop,
    load_shapes, resolve_load, resolve_unique, resolve_width, scan_scaffold, store_widths,
)


def _digest(domain: bytes, value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(domain + payload).hexdigest()


COPY_SCHEMA = "m061-copy-response-v1"

#: A phrase to copy through the discovered instructions. Recovering an opcode is not the same as
#: being able to compute with it, and a loop that moves bytes exercises load, store and branch
#: together rather than one at a time.
COPY_PHRASE = "mira genesis"
COPY_SOURCE = 100
COPY_DESTINATION = 200


@dataclass(frozen=True)
class M061Protocol:
    probe_timeout_seconds: float = 2.0
    node_timeout_seconds: float = 60.0
    schema: str = "m061-discovered-structure-protocol-v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "opcode_space": len(OPCODE_SPACE),
            "scaffolds": [scaffold.name for scaffold in SCAFFOLDS],
            "presupposed": list(PRESUPPOSED),
            "probe_timeout_seconds": self.probe_timeout_seconds,
        }

    def digest(self) -> str:
        return _digest(b"m061-discovered-structure-protocol-v1\0", self.to_dict())


M061_PROTOCOL = M061Protocol()


def _copy_script() -> Path:
    return Path(__file__).resolve().with_name("m061_copy_runtime.mjs")


def run_copy_loop(module: bytes, protocol: M061Protocol = M061_PROTOCOL) -> Mapping[str, object]:
    """Copy a phrase through a module built only from discovered instructions."""
    request = json.dumps({
        "wasm": base64.b64encode(module).decode("ascii"),
        "phrase": COPY_PHRASE,
        "source": COPY_SOURCE,
        "destination": COPY_DESTINATION,
    }, sort_keys=True, separators=(",", ":")).encode("utf-8")
    try:
        completed = subprocess.run(
            ["node", str(_copy_script())],
            input=request, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=protocol.node_timeout_seconds, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise M061Error(f"Node runtime unavailable or timed out: {type(exc).__name__}") from exc
    if not completed.stdout:
        raise M061Error("the copy runtime produced no output")
    response = json.loads(completed.stdout.decode("utf-8"))
    if response.get("schema") != COPY_SCHEMA:
        raise M061Error("copy runtime response identity mismatch")
    return response


def resolve_structure(scans: Mapping[str, Mapping[str, object]]) -> dict[str, int]:
    """Name the five instructions the body needs, refusing where the probes do not separate."""
    shapes = load_shapes(scans["memory_load"])
    widths = store_widths(scans["memory_store"])
    return {
        "i32.load8_u": int(resolve_load(shapes, 1, True, "i32.load8_u"), 16),
        "i32.load": int(resolve_load(shapes, 4, True, "i32.load"), 16),
        "i32.store8": int(resolve_width(widths, 1, "i32.store8"), 16),
        "i32.store": int(resolve_width(widths, 4, "i32.store"), 16),
        "br_if": int(resolve_unique(scans["conditional_branch"], "br_if"), 16),
    }


def unresolved_shapes(scans: Mapping[str, Mapping[str, object]]) -> dict[str, list[str]]:
    """What the probes saw but could not separate. Reported rather than resolved by preference."""
    shapes = load_shapes(scans["memory_load"])
    grouped: dict[tuple[int, bool], list[str]] = {}
    for name, shape in shapes.items():
        if shape[0] == 0:
            continue
        grouped.setdefault(shape, []).append(name)
    return {
        f"load_width_{width}_unsigned_{unsigned}": sorted(names)
        for (width, unsigned), names in sorted(grouped.items())
        if len(names) > 1
    }


@dataclass
class M061Manifest:
    mapping: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return dict(self.mapping)

    def digest(self) -> str:
        return _digest(b"m061-discovered-structure-manifest-v1\0", self.mapping)


def run_m061_discovered_structure(protocol: M061Protocol = M061_PROTOCOL) -> M061Manifest:
    """Scan three shapes, resolve five instructions, and compute with what came back."""
    scans = {scaffold.name: scan_scaffold(scaffold, protocol.probe_timeout_seconds)
             for scaffold in SCAFFOLDS}

    for name, scan in scans.items():
        if not scan["witness_found"]:
            raise M061Error(
                f"the {name} scaffold did not find its own witness; the instrument is suspect "
                "and its silence is not a result about the substrate"
            )

    resolved = resolve_structure(scans)
    recovered = {label: code == M060_AUTHORED_STRUCTURAL[label] for label, code in resolved.items()}
    if not all(recovered.values()):
        raise M061Error(f"discovery did not recover what M060 authored: {recovered}")

    module = build_copy_loop(resolved)
    copied = run_copy_loop(module, protocol)
    if not copied.get("correct"):
        raise M061Error(f"the loop built from discovered instructions did not compute: {copied}")

    replay = build_copy_loop(resolve_structure(scans))
    mapping = {
        "schema": "m061-discovered-structure-manifest-v1",
        "status": "development_pending_qualification",
        "protocol_digest": protocol.digest(),
        "opcode_space_scanned": len(OPCODE_SPACE),
        "scaffolds": [scaffold.name for scaffold in SCAFFOLDS],
        "witnesses": {name: str(scan["witness"]) for name, scan in sorted(scans.items())},
        "witnesses_found": {name: bool(scan["witness_found"]) for name, scan in sorted(scans.items())},
        "outcome_counts": {name: dict(scan["outcome_counts"]) for name, scan in sorted(scans.items())},
        "non_terminating_candidates": {
            name: int(scan["outcome_counts"].get("did_not_terminate", 0))
            for name, scan in sorted(scans.items())
        },
        "resolved_structural_opcodes": {label: hex(code) for label, code in sorted(resolved.items())},
        "m060_authored_structural_opcodes": {
            label: hex(code) for label, code in sorted(M060_AUTHORED_STRUCTURAL.items())
        },
        "discovery_recovered_every_authored_opcode": all(recovered.values()),
        "shapes_the_probes_could_not_separate": unresolved_shapes(scans),
        "copy_loop_bytes": len(module),
        "copy_loop_uses_only_discovered_instructions": True,
        "copy_phrase_recovered": bool(copied.get("correct")),
        "presupposed": list(PRESUPPOSED),
        "structural_instructions_authored": False,
        "compiler_authored": True,
        "arbitrary_code_generation": False,
        "network_authority": False,
        "repository_authority": False,
        "credential_authority": False,
        "deployment_authority": False,
        "canonical": False,
        "replay_identical": module == replay,
    }
    return M061Manifest(mapping)


__all__ = [
    "COPY_DESTINATION", "COPY_PHRASE", "COPY_SOURCE", "M061Manifest", "M061Protocol",
    "M061_PROTOCOL", "resolve_structure", "run_copy_loop", "run_m061_discovered_structure",
    "unresolved_shapes",
]
