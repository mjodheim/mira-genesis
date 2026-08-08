"""M063: transfer bounded control-arrangement synthesis to a checksum body.

M062 constructed one byte-copy loop from discovered effects, but its finite grammar and
emitter were tailored to copying.  M063 asks a deliberately smaller follow-up question: does
the same arrangement mechanism transfer to a genuinely different executable body?  The new
body reduces bytes into an accumulator, has no destination parameter and performs no memory
write.  Its task decomposition and emitter remain authored and are reported as such.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field, replace
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
from typing import Iterable, Mapping, Sequence

from metamorphosis.m061_discovered_structure import (
    M061_PROTOCOL,
    M061Protocol,
    resolve_structure,
    run_all_scans,
)
from metamorphosis.m061_structural_discovery import (
    I32,
    OPCODE_SPACE,
    _END,
    _I32_CONST,
    _LOCAL_GET,
    _module,
)
from metamorphosis.m062_synthesized_control import (
    CONDITIONS,
    M062_PROTOCOL,
    TOPOLOGIES,
    emit_arrangement as emit_copy_arrangement,
    scan_region_openers,
    synthesize_arrangement as synthesize_copy_arrangement,
)


class M063Error(ValueError):
    """Raised when transfer synthesis or independent admission is inconclusive."""


def _digest(domain: bytes, value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(domain + payload).hexdigest()


STEP_NAMES = ("accumulate_byte", "advance_source", "decrement_remaining")
REGION_LABELS = ("block", "loop")
CHECKSUM_REQUIRED = (
    "i32.load8_u", "br_if", "br", "local.set", "i32.add", "i32.sub", "i32.le_s",
)
PRESUPPOSED = (
    "local.get",
    "i32.const",
    "end 0x0b",
    "empty blocktype 0x40",
    "local declaration encoding",
    "label-depth encoding",
    "module framing",
    "function signature shape",
)


@dataclass(frozen=True)
class ChecksumCase:
    """One byte-reduction observation; payload may include a sentinel beyond count."""

    name: str
    payload: bytes
    count: int
    source: int
    background: int = 0x5A

    def __post_init__(self) -> None:
        if not self.name:
            raise M063Error("a checksum case needs a name")
        if not 0 <= self.count <= len(self.payload):
            raise M063Error("checksum count must lie inside the supplied payload")
        if self.source < 2:
            raise M063Error("checksum source must leave an observable prefix")
        if self.source + len(self.payload) + 2 > 65536:
            raise M063Error("checksum observation exceeds the one-page memory")
        if not 0 <= self.background <= 0xFF:
            raise M063Error("checksum background must be a byte")

    def expected(self) -> int:
        return sum(self.payload[: self.count])

    def to_public_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "payload": list(self.payload),
            "count": self.count,
            "source": self.source,
            "background": self.background,
        }

    def digest(self) -> str:
        return _digest(b"m063-checksum-case-v1\0", self.to_public_dict())


PUBLIC_CASES = (
    ChecksumCase("public_zero", b"\xe7", 0, 64),
    ChecksumCase("public_one", b"\x11\xf2", 1, 96, background=0xA1),
    ChecksumCase("public_five", b"Mira!x", 5, 128, background=0x3C),
)

HIDDEN_CASES = (
    ChecksumCase("hidden_two_extremes", b"\x00\xff\x91", 2, 320, background=0xC7),
    ChecksumCase("hidden_seven", b"Genesis?", 7, 512, background=0x29),
    ChecksumCase("hidden_zero_shifted", b"\x99", 0, 768, background=0xD4),
)


@dataclass(frozen=True)
class ChecksumArrangement:
    """One checksum program constructed from the transferred arrangement dimensions."""

    topology: str
    condition: str
    exit_position: int
    step_order: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.topology not in TOPOLOGIES:
            raise M063Error(f"unknown topology {self.topology!r}")
        if self.condition not in CONDITIONS:
            raise M063Error(f"unknown condition {self.condition!r}")
        if not 0 <= self.exit_position <= len(STEP_NAMES):
            raise M063Error("exit position is outside the checksum step sequence")
        if sorted(self.step_order) != sorted(STEP_NAMES):
            raise M063Error("an arrangement must contain each checksum step exactly once")

    def to_dict(self) -> dict[str, object]:
        return {
            "topology": self.topology,
            "condition": self.condition,
            "exit_position": self.exit_position,
            "step_order": list(self.step_order),
        }

    def digest(self) -> str:
        return _digest(b"m063-checksum-arrangement-v1\0", self.to_dict())

    def region_order(self) -> tuple[str, str]:
        if self.topology == "block_then_loop":
            return ("block", "loop")
        return ("loop", "block")

    def branch_depths(self) -> tuple[int, int]:
        outer, inner = self.region_order()
        depth_for = {inner: 0, outer: 1}
        return depth_for["block"], depth_for["loop"]


def candidate_space() -> tuple[ChecksumArrangement, ...]:
    """Construct the 96-product transfer grammar without storing finished programs."""
    return tuple(
        ChecksumArrangement(topology, condition, exit_position, tuple(order))
        for topology in TOPOLOGIES
        for condition in CONDITIONS
        for exit_position in range(len(STEP_NAMES) + 1)
        for order in itertools.permutations(STEP_NAMES)
    )


def _require_opcodes(opcodes: Mapping[str, int], labels: Iterable[str]) -> None:
    missing = sorted(label for label in labels if label not in opcodes)
    if missing:
        raise M063Error(f"discovery did not supply the required operations: {missing}")
    invalid = sorted(label for label in labels if not 0 <= int(opcodes[label]) <= 0xFF)
    if invalid:
        raise M063Error(f"resolved operations are not single-byte opcodes: {invalid}")


def _exit_bytes(
    arrangement: ChecksumArrangement, opcodes: Mapping[str, int], depth: int,
) -> bytes:
    remaining = bytes([_LOCAL_GET, 0x01])
    zero = bytes([_I32_CONST, 0x00])
    operands = remaining + zero if arrangement.condition == "remaining_le_zero" else zero + remaining
    return operands + bytes([opcodes["i32.le_s"], opcodes["br_if"], depth])


def _step_bytes(name: str, opcodes: Mapping[str, int]) -> bytes:
    if name == "accumulate_byte":
        return bytes([
            _LOCAL_GET, 0x02,
            _LOCAL_GET, 0x00,
            opcodes["i32.load8_u"], 0x00, 0x00,
            opcodes["i32.add"],
            opcodes["local.set"], 0x02,
        ])
    if name == "advance_source":
        local = 0x00
        operation = opcodes["i32.add"]
    elif name == "decrement_remaining":
        local = 0x01
        operation = opcodes["i32.sub"]
    else:
        raise M063Error(f"unknown checksum step {name!r}")
    return bytes([
        _LOCAL_GET, local,
        _I32_CONST, 0x01,
        operation,
        opcodes["local.set"], local,
    ])


def emit_arrangement(
    arrangement: ChecksumArrangement,
    opcodes: Mapping[str, int],
    regions: Mapping[str, int],
) -> bytes:
    """Render one checksum candidate entirely from supplied discovered effect bytes."""
    _require_opcodes(opcodes, CHECKSUM_REQUIRED)
    _require_opcodes(regions, REGION_LABELS)
    outer, inner = arrangement.region_order()
    exit_depth, repeat_depth = arrangement.branch_depths()
    body = bytearray([regions[outer], 0x40, regions[inner], 0x40])
    for position in range(len(STEP_NAMES) + 1):
        if position == arrangement.exit_position:
            body += _exit_bytes(arrangement, opcodes, exit_depth)
        if position < len(STEP_NAMES):
            body += _step_bytes(arrangement.step_order[position], opcodes)
    body += bytes([
        opcodes["br"], repeat_depth,
        _END, _END,
        _LOCAL_GET, 0x02,
    ])
    return _module([I32, I32], [I32], bytes(body), locals_=[I32])


def _runtime_script() -> Path:
    return Path(__file__).resolve().with_name("m063_checksum_runtime.mjs")


def evaluate_modules(
    modules: Mapping[str, bytes],
    cases: Sequence[ChecksumCase],
    timeout_seconds: float = 30.0,
) -> dict[str, Mapping[str, object]]:
    """Execute arbitrary candidate modules on checksum evidence in one disposable process."""
    if not modules:
        return {}
    request = {
        "schema": "m063-checksum-request-v1",
        "candidates": [
            {"digest": digest, "wasm": base64.b64encode(module).decode("ascii")}
            for digest, module in sorted(modules.items())
        ],
        "cases": [case.to_public_dict() for case in cases],
    }
    try:
        completed = subprocess.run(
            ["node", str(_runtime_script())],
            input=json.dumps(request, sort_keys=True, separators=(",", ":")).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise M063Error(f"checksum runtime unavailable or timed out: {type(exc).__name__}") from exc
    if not completed.stdout:
        error = completed.stderr.decode("utf-8", errors="replace").strip()
        raise M063Error(f"checksum runtime produced no output: {error}")
    try:
        response = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise M063Error("checksum runtime produced malformed output") from exc
    if response.get("schema") != "m063-checksum-response-v1":
        raise M063Error("checksum runtime response identity mismatch")
    results = response.get("results")
    if not isinstance(results, dict):
        raise M063Error("checksum runtime omitted its result mapping")
    return results


def evaluate_arrangements(
    arrangements: Sequence[ChecksumArrangement],
    opcodes: Mapping[str, int],
    regions: Mapping[str, int],
    cases: Sequence[ChecksumCase],
    timeout_seconds: float = 30.0,
) -> dict[str, Mapping[str, object]]:
    modules = {
        arrangement.digest(): emit_arrangement(arrangement, opcodes, regions)
        for arrangement in arrangements
    }
    return evaluate_modules(modules, cases, timeout_seconds)


def case_passes(observation: Mapping[str, object], case: ChecksumCase) -> bool:
    return (
        observation.get("outcome") == "observed"
        and observation.get("return_value") == case.expected()
        and observation.get("memory_unchanged") is True
        and observation.get("source_after") == list(case.payload)
    )


@dataclass(frozen=True)
class SynthesisResult:
    candidate_count: int
    public_survivors: tuple[ChecksumArrangement, ...]
    selected: ChecksumArrangement
    public_evidence_digest: str
    observations: Mapping[str, Mapping[str, object]] = field(repr=False, compare=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_count": self.candidate_count,
            "public_survivor_count": len(self.public_survivors),
            "public_survivor_digests": [item.digest() for item in self.public_survivors],
            "selected": self.selected.to_dict(),
            "selected_digest": self.selected.digest(),
            "public_evidence_digest": self.public_evidence_digest,
        }


def synthesize_checksum_arrangement(
    opcodes: Mapping[str, int],
    regions: Mapping[str, int],
    public_cases: Sequence[ChecksumCase] = PUBLIC_CASES,
    timeout_seconds: float = 30.0,
) -> SynthesisResult:
    """Construct and filter the transfer grammar using public evidence only."""
    candidates = candidate_space()
    observations = evaluate_arrangements(candidates, opcodes, regions, public_cases, timeout_seconds)
    survivors = tuple(
        candidate
        for candidate in candidates
        if all(
            case_passes(observations[candidate.digest()]["cases"][case.name], case)
            for case in public_cases
        )
    )
    if not survivors:
        raise M063Error("public checksum evidence admits no arrangement")
    selected = min(survivors, key=lambda item: item.digest())
    evidence = {
        "case_digests": [case.digest() for case in public_cases],
        "survivor_digests": sorted(item.digest() for item in survivors),
        "selected_digest": selected.digest(),
    }
    return SynthesisResult(
        candidate_count=len(candidates),
        public_survivors=tuple(sorted(survivors, key=lambda item: item.digest())),
        selected=selected,
        public_evidence_digest=_digest(b"m063-public-evidence-v1\0", evidence),
        observations=observations,
    )


def validate_arrangement(
    arrangement: ChecksumArrangement,
    opcodes: Mapping[str, int],
    regions: Mapping[str, int],
    hidden_cases: Sequence[ChecksumCase] = HIDDEN_CASES,
    timeout_seconds: float = 30.0,
) -> dict[str, object]:
    observations = evaluate_arrangements(
        (arrangement,), opcodes, regions, hidden_cases, timeout_seconds
    )[arrangement.digest()]["cases"]
    passed = {case.name: case_passes(observations[case.name], case) for case in hidden_cases}
    evidence = {
        "arrangement_digest": arrangement.digest(),
        "case_digests": [case.digest() for case in hidden_cases],
        "passed": passed,
    }
    return {
        "schema": "m063-independent-validation-v1",
        "accepted": bool(passed) and all(passed.values()),
        "case_count": len(hidden_cases),
        "passed": passed,
        "hidden_evidence_digest": _digest(b"m063-hidden-evidence-v1\0", evidence),
    }


def validate_survivor_class(
    arrangements: Sequence[ChecksumArrangement],
    opcodes: Mapping[str, int],
    regions: Mapping[str, int],
    hidden_cases: Sequence[ChecksumCase] = HIDDEN_CASES,
    timeout_seconds: float = 30.0,
) -> dict[str, object]:
    observations = evaluate_arrangements(
        tuple(arrangements), opcodes, regions, hidden_cases, timeout_seconds
    )
    accepted: dict[str, bool] = {}
    for arrangement in arrangements:
        cases = observations[arrangement.digest()]["cases"]
        accepted[arrangement.digest()] = all(
            case_passes(cases[case.name], case) for case in hidden_cases
        )
    evidence = {
        "arrangement_digests": sorted(accepted),
        "case_digests": [case.digest() for case in hidden_cases],
        "accepted": accepted,
        "regions": {label: hex(value) for label, value in sorted(regions.items())},
    }
    return {
        "schema": "m063-survivor-class-validation-v1",
        "candidate_count": len(arrangements),
        "accepted_count": sum(accepted.values()),
        "all_accepted": bool(accepted) and all(accepted.values()),
        "accepted": accepted,
        "hidden_evidence_digest": _digest(b"m063-survivor-class-evidence-v1\0", evidence),
    }


def evaluate_copy_negative_control(
    opcodes: Mapping[str, int],
    regions: Mapping[str, int],
    timeout_seconds: float = 30.0,
) -> dict[str, object]:
    """Require M062's selected copy body to fail the new checksum observations."""
    copy = synthesize_copy_arrangement(opcodes, regions, timeout_seconds=timeout_seconds)
    module = emit_copy_arrangement(copy.selected, opcodes, regions)
    label = copy.selected.digest()
    observations = evaluate_modules({label: module}, PUBLIC_CASES, timeout_seconds)[label]["cases"]
    passed = {case.name: case_passes(observations[case.name], case) for case in PUBLIC_CASES}
    return {
        "schema": "m063-copy-negative-control-v1",
        "copy_arrangement_digest": label,
        "case_count": len(PUBLIC_CASES),
        "passed": passed,
        "rejected": not all(passed.values()),
        "control_evidence_digest": _digest(
            b"m063-copy-negative-control-v1\0", {"passed": passed, "copy_digest": label}
        ),
    }


@dataclass(frozen=True)
class M063Protocol:
    region_probe_timeout_seconds: float = 2.0
    arrangement_timeout_seconds: float = 30.0
    schema: str = "m063-control-transfer-protocol-v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "source_mechanism_protocol_digest": M062_PROTOCOL.digest(),
            "opcode_space": len(OPCODE_SPACE),
            "topologies": list(TOPOLOGIES),
            "conditions": list(CONDITIONS),
            "exit_positions": len(STEP_NAMES) + 1,
            "step_names": list(STEP_NAMES),
            "candidate_budget": len(candidate_space()),
            "public_case_digests": [case.digest() for case in PUBLIC_CASES],
            "hidden_case_count": len(HIDDEN_CASES),
            "hidden_case_commitment": _digest(
                b"m063-hidden-case-commitment-v1\0", [case.digest() for case in HIDDEN_CASES]
            ),
            "negative_control": "M062 selected copy body on checksum evidence",
            "presupposed": list(PRESUPPOSED),
            "region_probe_timeout_seconds": self.region_probe_timeout_seconds,
            "arrangement_timeout_seconds": self.arrangement_timeout_seconds,
        }

    def digest(self) -> str:
        return _digest(b"m063-control-transfer-protocol-v1\0", self.to_dict())


M063_PROTOCOL = M063Protocol()


@dataclass
class M063Manifest:
    mapping: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return dict(self.mapping)

    def digest(self) -> str:
        return _digest(b"m063-control-transfer-manifest-v1\0", self.mapping)


def run_m063_control_transfer(
    protocol: M063Protocol = M063_PROTOCOL,
    m061_protocol: M061Protocol = M061_PROTOCOL,
) -> M063Manifest:
    """Replay discovery, transfer arrangement synthesis, and admit every survivor."""
    structural_scans = run_all_scans(m061_protocol)
    opcodes = resolve_structure(structural_scans)
    region_scan = scan_region_openers(opcodes, protocol.region_probe_timeout_seconds)
    if not all(region_scan["witnesses_found"].values()):
        raise M063Error("the transferred region scaffold missed a declared witness")
    regions = region_scan["resolved"]

    synthesis = synthesize_checksum_arrangement(
        opcodes, regions, PUBLIC_CASES, protocol.arrangement_timeout_seconds
    )
    equivalence_validation: dict[str, Mapping[str, object]] = {}
    for block_opcode, loop_opcode in itertools.product(
        region_scan["effect_classes"]["exit_region"],
        region_scan["effect_classes"]["repeat_region"],
    ):
        variant = {"block": int(block_opcode), "loop": int(loop_opcode)}
        verdict = validate_survivor_class(
            synthesis.public_survivors, opcodes, variant, HIDDEN_CASES,
            protocol.arrangement_timeout_seconds,
        )
        equivalence_validation[
            f"exit={int(block_opcode):#04x},repeat={int(loop_opcode):#04x}"
        ] = verdict
    if not all(value["all_accepted"] for value in equivalence_validation.values()):
        raise M063Error("a checksum or region-effect survivor disagrees on hidden behaviour")

    validation = validate_arrangement(
        synthesis.selected, opcodes, regions, HIDDEN_CASES, protocol.arrangement_timeout_seconds
    )
    negative_control = evaluate_copy_negative_control(
        opcodes, regions, protocol.arrangement_timeout_seconds
    )
    if not negative_control["rejected"]:
        raise M063Error("the M062 copy body unexpectedly passed the checksum transfer task")

    selected_module = emit_arrangement(synthesis.selected, opcodes, regions)
    replay = emit_arrangement(replace(synthesis.selected), dict(opcodes), dict(regions))
    selected_import_count = synthesis.observations[synthesis.selected.digest()].get("import_count")
    if selected_import_count != 0:
        raise M063Error("the selected checksum body unexpectedly declares imports")
    mapping = {
        "schema": "m063-control-transfer-manifest-v1",
        "status": "development_pending_qualification",
        "protocol_digest": protocol.digest(),
        "source_mechanism_protocol_digest": M062_PROTOCOL.digest(),
        "m061_protocol_digest": m061_protocol.digest(),
        "m061_scaffolds_replayed": len(structural_scans),
        "structural_opcodes_resolved": {
            label: hex(value) for label, value in sorted(opcodes.items())
        },
        "region_opcode_space_scanned": region_scan["scanned"],
        "region_effect_classes": {
            label: [hex(value) for value in values]
            for label, values in region_scan["effect_classes"].items()
        },
        "region_effect_class_hidden_validation": equivalence_validation,
        "synthesis": synthesis.to_dict(),
        "independent_validation": validation,
        "copy_body_negative_control": negative_control,
        "selected_module_bytes": len(selected_module),
        "selected_module_imports": selected_import_count,
        "emitter_inputs_from_discovery": {
            "operation_labels": sorted(CHECKSUM_REQUIRED),
            "region_effect_classes": {
                label: [hex(value) for value in values]
                for label, values in region_scan["effect_classes"].items()
            },
            "selected_arrangement_digest": synthesis.selected.digest(),
            "selection_evidence_digest": synthesis.public_evidence_digest,
        },
        "authored_elements": [
            "checksum-task decomposition",
            "three checksum atomic steps",
            "finite transferred Cartesian grammar",
            "checksum WebAssembly emitter",
            "local, blocktype and label-depth encoding",
            "public and hidden cases",
        ],
        "claim_exclusions": [
            "arbitrary compiler synthesis",
            "self-authored grammar",
            "unrestricted code generation",
            "open-ended evolution",
        ],
        "external_authority_not_granted": [
            "network", "repository", "credentials", "deployment", "production systems"
        ],
        "canonical": False,
        "replay_identical": selected_module == replay,
    }
    return M063Manifest(mapping)


__all__ = [
    "CHECKSUM_REQUIRED",
    "ChecksumArrangement",
    "ChecksumCase",
    "HIDDEN_CASES",
    "M063Error",
    "M063Manifest",
    "M063Protocol",
    "M063_PROTOCOL",
    "PRESUPPOSED",
    "PUBLIC_CASES",
    "STEP_NAMES",
    "SynthesisResult",
    "candidate_space",
    "case_passes",
    "emit_arrangement",
    "evaluate_arrangements",
    "evaluate_copy_negative_control",
    "evaluate_modules",
    "run_m063_control_transfer",
    "synthesize_checksum_arrangement",
    "validate_arrangement",
    "validate_survivor_class",
]
