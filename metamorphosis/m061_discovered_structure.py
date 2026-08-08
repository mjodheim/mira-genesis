"""M061: the experiment around the structural scans.

M060 migrated the whole body and authored every structural instruction it used. Its result named
that as the next thing to remove, and named the difficulty: a branch has no observable value, only
an effect on what runs next.

This module runs the scaffolds in two stages, resolves what they characterised, checks the
resolution against what M060 authored, and then proves the recovered opcodes are usable by building
a working loop with them.

The second stage exists because two shapes need an instruction the first stage recovered. The
alternative was to write that instruction into the scaffold that discovers instructions, which is
the kind of shortcut this experiment is about removing.
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
    LOOP_REQUIRED, M060_AUTHORED_STRUCTURAL, OPCODE_SPACE, PRESUPPOSED, SCAFFOLDS,
    STAGED_SCAFFOLD_NAMES, UNDISCOVERED_IN_LOOP, M061Error, build_copy_loop, load_shapes,
    resolve_i32_binary, resolve_load, resolve_unique, resolve_width, scan_scaffold,
    staged_scaffolds, store_widths,
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


#: Every shape, in the order it is scanned: the first stage, then the two the first stage enables.
SCAFFOLD_NAMES = [scaffold.name for scaffold in SCAFFOLDS] + list(STAGED_SCAFFOLD_NAMES)


@dataclass(frozen=True)
class M061Protocol:
    probe_timeout_seconds: float = 2.0
    node_timeout_seconds: float = 60.0
    schema: str = "m061-discovered-structure-protocol-v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "opcode_space": len(OPCODE_SPACE),
            "scaffolds": SCAFFOLD_NAMES,
            "staged_scaffolds": list(STAGED_SCAFFOLD_NAMES),
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


def run_all_scans(
    protocol: M061Protocol = M061_PROTOCOL,
) -> dict[str, Mapping[str, object]]:
    """Scan every shape in two stages, refusing to report anything from a scaffold that is suspect.

    The first stage is self-contained. Its integer shape yields the addition that the two staged
    shapes need in order to observe their candidates at all, so the second stage is scanned with a
    byte the first stage found rather than one written here.
    """
    scans: dict[str, Mapping[str, object]] = {
        scaffold.name: scan_scaffold(scaffold, protocol.probe_timeout_seconds)
        for scaffold in SCAFFOLDS
    }
    _require_witnesses(scans)

    add = resolve_i32_binary(scans["i32_binary"])["i32.add"]
    for scaffold in staged_scaffolds(add):
        scans[scaffold.name] = scan_scaffold(scaffold, protocol.probe_timeout_seconds)
    _require_witnesses(scans)
    return scans


def _require_witnesses(scans: Mapping[str, Mapping[str, object]]) -> None:
    for name, scan in scans.items():
        if not scan["witness_found"]:
            raise M061Error(
                f"the {name} scaffold did not find its own witness; the instrument is suspect "
                "and its silence is not a result about the substrate"
            )


def resolve_structure(scans: Mapping[str, Mapping[str, object]]) -> dict[str, int]:
    """Name the instructions the body needs, refusing where the probes do not separate.

    The loads and stores are characterised by width and signedness, the two branches by what they
    make the scaffold return, and the integer operations by what they compute. Nothing here matches
    a name against a table.
    """
    shapes = load_shapes(scans["memory_load"])
    widths = store_widths(scans["memory_store"])
    resolved = {
        "i32.load8_u": int(resolve_load(shapes, 1, True, "i32.load8_u"), 16),
        "i32.load": int(resolve_load(shapes, 4, True, "i32.load"), 16),
        "i32.store8": int(resolve_width(widths, 1, "i32.store8"), 16),
        "i32.store": int(resolve_width(widths, 4, "i32.store"), 16),
        "br_if": int(resolve_unique(scans["conditional_branch"], "br_if"), 16),
        "br": int(resolve_unique(scans["unconditional_branch"], "br"), 16),
        "local.set": int(resolve_unique(scans["local_set"], "local.set"), 16),
    }
    resolved.update(resolve_i32_binary(scans["i32_binary"]))
    return resolved


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
    """Scan six shapes, resolve ten instructions, and compute with what came back."""
    scans = run_all_scans(protocol)
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
        "scaffolds": SCAFFOLD_NAMES,
        "staged_scaffolds": list(STAGED_SCAFFOLD_NAMES),
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
        # An earlier manifest claimed the loop used discovered instructions alone while the builder
        # wrote seven opcodes into it directly. The claim was false. Six of the seven are now
        # discovered and named below; what is still written by hand is named below it, in the same
        # manifest, at the same level. A reader should not have to open the builder to find out.
        "copy_loop_discovered_instructions": sorted(LOOP_REQUIRED),
        "copy_loop_authored_elements": list(UNDISCOVERED_IN_LOOP),
        "copy_loop_uses_only_discovered_instructions": False,
        "copy_phrase_recovered": bool(copied.get("correct")),
        "presupposed": list(PRESUPPOSED),
        "structural_operations_authored": False,
        "block_structure_authored": True,
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
    "COPY_DESTINATION", "COPY_PHRASE", "COPY_SOURCE", "SCAFFOLD_NAMES", "M061Manifest",
    "M061Protocol", "M061_PROTOCOL", "resolve_structure", "run_all_scans", "run_copy_loop",
    "run_m061_discovered_structure", "unresolved_shapes",
]
