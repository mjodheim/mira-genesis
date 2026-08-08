"""M062: synthesize a bounded control arrangement from discovered effects.

M061 recovered the bytes for the operations used by a copy loop, but a Python function still
placed those operations in their final order and wrote the ``block`` and ``loop`` openers.  M062
removes that literal arrangement for one deliberately small task.  It first identifies the two
region openers by what a discovered branch does inside them, then constructs a finite grammar of
loop arrangements and keeps only programs that satisfy public behavioural evidence.

The boundary is as important as the result.  The task decomposition, search grammar, WebAssembly
framing, block type and label encoding are authored.  This is not an arbitrary compiler and it
does not infer a new language.  It establishes only that the final control topology and ordering
for this copy task need not be handed to the emitter as a complete program.
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
    LOOP_REQUIRED,
    M061Error,
    OPCODE_SPACE,
    _END,
    _I32_CONST,
    _LOCAL_GET,
    _module,
    probe,
)


class M062Error(ValueError):
    """Raised when discovery, synthesis or independent validation is inconclusive."""


def _digest(domain: bytes, value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(domain + payload).hexdigest()


STEP_NAMES = ("copy_byte", "advance_source", "advance_destination", "decrement_remaining")
TOPOLOGIES = ("block_then_loop", "loop_then_block")
CONDITIONS = ("remaining_le_zero", "zero_le_remaining")
REGION_LABELS = ("block", "loop")

# The floor is stated in the manifest rather than hidden behind a boolean.  The opcodes that have
# an observable effect are discovered; these format and observation mechanisms are still given.
PRESUPPOSED = (
    "local.get",
    "i32.const",
    "end 0x0b",
    "empty blocktype 0x40",
    "i32 result blocktype 0x7f in the region probe",
    "label-depth encoding",
    "module framing",
    "function signature shape",
)


@dataclass(frozen=True)
class CopyCase:
    """One copy observation.  ``payload`` may contain bytes beyond ``count`` as a sentinel."""

    name: str
    payload: bytes
    count: int
    source: int
    destination: int
    destination_fill: int = 0x55

    def __post_init__(self) -> None:
        if not self.name:
            raise M062Error("a copy case needs a name")
        if not 0 <= self.count <= len(self.payload):
            raise M062Error("copy count must lie inside the supplied payload")
        if self.source < 1 or self.destination < 1:
            raise M062Error("copy offsets must leave room for a guard byte")
        source_range = range(self.source, self.source + len(self.payload))
        destination_range = range(self.destination - 1, self.destination + self.count + 2)
        if set(source_range) & set(destination_range):
            raise M062Error("source and observed destination ranges must not overlap")
        if not 0 <= self.destination_fill <= 0xFF:
            raise M062Error("destination fill must be a byte")

    def to_public_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "payload": list(self.payload),
            "count": self.count,
            "source": self.source,
            "destination": self.destination,
            "destination_fill": self.destination_fill,
        }

    def digest(self) -> str:
        return _digest(b"m062-copy-case-v1\0", self.to_public_dict())

    def expected_destination_window(self) -> list[int]:
        return [self.destination_fill, *self.payload[: self.count], self.destination_fill,
                self.destination_fill]


PUBLIC_CASES = (
    # The zero-length case carries a non-zero source sentinel.  A candidate that copies before it
    # checks the exit condition therefore changes the destination and is observable.
    CopyCase("public_zero", b"\xe7", 0, 64, 192),
    # The extra byte catches candidates that execute one iteration too many.
    CopyCase("public_one", b"AZ", 1, 80, 224),
    CopyCase("public_four", b"Mira!", 4, 96, 256),
)

HIDDEN_CASES = (
    CopyCase("hidden_two", b"\x00\xff\x91", 2, 320, 512, destination_fill=0xA3),
    CopyCase("hidden_seven", b"Genesis?", 7, 352, 560, destination_fill=0x6C),
    CopyCase("hidden_zero_shifted", b"\x99", 0, 400, 640, destination_fill=0x3D),
)


@dataclass(frozen=True)
class Arrangement:
    """One program constructed by the M062 grammar, not an embedded byte sequence."""

    topology: str
    condition: str
    exit_position: int
    step_order: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.topology not in TOPOLOGIES:
            raise M062Error(f"unknown topology {self.topology!r}")
        if self.condition not in CONDITIONS:
            raise M062Error(f"unknown condition {self.condition!r}")
        if not 0 <= self.exit_position <= len(STEP_NAMES):
            raise M062Error("exit position is outside the step sequence")
        if sorted(self.step_order) != sorted(STEP_NAMES):
            raise M062Error("an arrangement must contain each copy step exactly once")

    def to_dict(self) -> dict[str, object]:
        return {
            "topology": self.topology,
            "condition": self.condition,
            "exit_position": self.exit_position,
            "step_order": list(self.step_order),
        }

    def digest(self) -> str:
        return _digest(b"m062-arrangement-v1\0", self.to_dict())

    def region_order(self) -> tuple[str, str]:
        if self.topology == "block_then_loop":
            return ("block", "loop")
        return ("loop", "block")

    def branch_depths(self) -> tuple[int, int]:
        """Return ``(exit_depth, repeat_depth)`` derived from the selected topology."""
        outer, inner = self.region_order()
        depth_for = {inner: 0, outer: 1}
        return depth_for["block"], depth_for["loop"]


def candidate_space() -> tuple[Arrangement, ...]:
    """Construct the complete bounded grammar deterministically.

    There is no catalogue of finished programs: the 480 candidates are the Cartesian product of
    two region nestings, two observable predicates, five exit positions and every permutation of
    the four atomic state transitions.
    """
    return tuple(
        Arrangement(topology, condition, exit_position, tuple(order))
        for topology in TOPOLOGIES
        for condition in CONDITIONS
        for exit_position in range(len(STEP_NAMES) + 1)
        for order in itertools.permutations(STEP_NAMES)
    )


def _require_opcodes(opcodes: Mapping[str, int], labels: Iterable[str]) -> None:
    missing = sorted(label for label in labels if label not in opcodes)
    if missing:
        raise M062Error(f"discovery did not supply the required operations: {missing}")
    invalid = sorted(label for label in labels if not 0 <= int(opcodes[label]) <= 0xFF)
    if invalid:
        raise M062Error(f"resolved operations are not single-byte opcodes: {invalid}")


def _region_scaffold(opcode: int, br: int, add: int) -> bytes:
    """Make a region opener observable without assuming either opener.

    The candidate opens an i32-result region.  A branch to depth zero exits a block and the
    transported seven is incremented to eight.  The same branch restarts a loop and does not
    terminate.  The branch and addition are supplied by M061 discovery, so neither region opener
    is used to expose the other.
    """
    body = bytes([
        opcode, I32,
        _I32_CONST, 0x07,
        br, 0x00,
        _I32_CONST, 0x09,
        _END,
        _I32_CONST, 0x01,
        add,
    ])
    return _module([], [I32], body)


def scan_region_openers(
    resolved: Mapping[str, int], timeout_seconds: float = 2.0,
) -> dict[str, object]:
    """Scan every byte in one shape and identify block versus loop by control effect."""
    _require_opcodes(resolved, ("br", "i32.add"))
    outcomes: dict[str, str] = {}
    observations: dict[str, object] = {}
    for opcode in OPCODE_SPACE:
        name = f"{opcode:#04x}"
        response = probe(
            _region_scaffold(opcode, int(resolved["br"]), int(resolved["i32.add"])),
            ({"args": [], "memory": []},),
            timeout_seconds,
        )
        outcome = str(response.get("outcome"))
        outcomes[name] = outcome
        if outcome == "observed":
            observations[name] = response.get("observations")

    block_matches = sorted(name for name, value in observations.items() if value == [8])
    loop_matches = sorted(name for name, value in outcomes.items() if value == "did_not_terminate")
    if not block_matches:
        raise M062Error("the region probe found no exit-region candidate")
    if not loop_matches:
        raise M062Error("the region probe found no repeat-region candidate")
    # More than one byte can have the required bounded effect.  The scan preserves that class
    # instead of calling the familiar byte "block" by preference.  The smallest byte is only a
    # deterministic representation; run_m062 validates every class member on the complete task.
    block_canonical = min(int(name, 16) for name in block_matches)
    loop_canonical = min(int(name, 16) for name in loop_matches)

    counts: dict[str, int] = {}
    for outcome in outcomes.values():
        counts[outcome] = counts.get(outcome, 0) + 1
    return {
        "scanned": len(OPCODE_SPACE),
        "outcome_counts": counts,
        "block_matches": block_matches,
        "loop_matches": loop_matches,
        "effect_classes": {
            "exit_region": [int(name, 16) for name in block_matches],
            "repeat_region": [int(name, 16) for name in loop_matches],
        },
        "uniquely_determined": {
            "exit_region": len(block_matches) == 1,
            "repeat_region": len(loop_matches) == 1,
        },
        "resolved": {
            "block": block_canonical,
            "loop": loop_canonical,
        },
        "witnesses": {"block": "0x02", "loop": "0x03"},
        "witnesses_found": {
            "block": "0x02" in block_matches,
            "loop": "0x03" in loop_matches,
        },
    }


def _exit_bytes(arrangement: Arrangement, opcodes: Mapping[str, int], depth: int) -> bytes:
    remaining = bytes([_LOCAL_GET, 0x02])
    zero = bytes([_I32_CONST, 0x00])
    operands = remaining + zero if arrangement.condition == "remaining_le_zero" else zero + remaining
    return operands + bytes([opcodes["i32.le_s"], opcodes["br_if"], depth])


def _step_bytes(name: str, opcodes: Mapping[str, int]) -> bytes:
    if name == "copy_byte":
        return bytes([
            _LOCAL_GET, 0x01,
            _LOCAL_GET, 0x00,
            opcodes["i32.load8_u"], 0x00, 0x00,
            opcodes["i32.store8"], 0x00, 0x00,
        ])
    if name == "advance_source":
        local = 0x00
        operation = opcodes["i32.add"]
    elif name == "advance_destination":
        local = 0x01
        operation = opcodes["i32.add"]
    elif name == "decrement_remaining":
        local = 0x02
        operation = opcodes["i32.sub"]
    else:  # Arrangement validates names, but keep the emitter fail-closed on direct misuse.
        raise M062Error(f"unknown step {name!r}")
    return bytes([
        _LOCAL_GET, local,
        _I32_CONST, 0x01,
        operation,
        opcodes["local.set"], local,
    ])


def emit_arrangement(
    arrangement: Arrangement,
    opcodes: Mapping[str, int],
    regions: Mapping[str, int],
) -> bytes:
    """Render one grammar product with no fallback to authored operation bytes."""
    _require_opcodes(opcodes, LOOP_REQUIRED)
    _require_opcodes(regions, REGION_LABELS)
    outer, inner = arrangement.region_order()
    exit_depth, repeat_depth = arrangement.branch_depths()
    body = bytearray([regions[outer], 0x40, regions[inner], 0x40])
    for position in range(len(STEP_NAMES) + 1):
        if position == arrangement.exit_position:
            body += _exit_bytes(arrangement, opcodes, exit_depth)
        if position < len(STEP_NAMES):
            body += _step_bytes(arrangement.step_order[position], opcodes)
    body += bytes([opcodes["br"], repeat_depth, _END, _END, _I32_CONST, 0x00])
    return _module([I32, I32, I32], [I32], bytes(body))


def _runtime_script() -> Path:
    return Path(__file__).resolve().with_name("m062_arrangement_runtime.mjs")


def _runtime_cases(cases: Sequence[CopyCase]) -> list[dict[str, object]]:
    return [case.to_public_dict() for case in cases]


def evaluate_arrangements(
    arrangements: Sequence[Arrangement],
    opcodes: Mapping[str, int],
    regions: Mapping[str, int],
    cases: Sequence[CopyCase],
    timeout_seconds: float = 60.0,
) -> dict[str, Mapping[str, object]]:
    """Execute a batch in one disposable Node process and return observations by digest."""
    if not arrangements:
        return {}
    request = {
        "schema": "m062-arrangement-request-v1",
        "candidates": [
            {
                "digest": arrangement.digest(),
                "wasm": base64.b64encode(emit_arrangement(arrangement, opcodes, regions)).decode("ascii"),
            }
            for arrangement in arrangements
        ],
        "cases": _runtime_cases(cases),
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
        raise M062Error(f"arrangement runtime unavailable or timed out: {type(exc).__name__}") from exc
    if not completed.stdout:
        error = completed.stderr.decode("utf-8", errors="replace").strip()
        raise M062Error(f"arrangement runtime produced no output: {error}")
    try:
        response = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise M062Error("arrangement runtime produced malformed output") from exc
    if response.get("schema") != "m062-arrangement-response-v1":
        raise M062Error("arrangement runtime response identity mismatch")
    results = response.get("results")
    if not isinstance(results, dict):
        raise M062Error("arrangement runtime omitted its result mapping")
    return results


def case_passes(observation: Mapping[str, object], case: CopyCase) -> bool:
    return (
        observation.get("outcome") == "observed"
        and observation.get("return_value") == 0
        and observation.get("destination_window") == case.expected_destination_window()
        and observation.get("source_after") == list(case.payload)
    )


@dataclass(frozen=True)
class SynthesisResult:
    candidate_count: int
    public_survivors: tuple[Arrangement, ...]
    selected: Arrangement
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


def synthesize_arrangement(
    opcodes: Mapping[str, int],
    regions: Mapping[str, int],
    public_cases: Sequence[CopyCase] = PUBLIC_CASES,
    timeout_seconds: float = 60.0,
) -> SynthesisResult:
    """Construct and filter the grammar using public evidence only.

    Hidden cases are intentionally absent from this signature.  Multiple syntactic survivors are
    allowed only because each has the same complete observed behaviour on every public case; a
    digest selects a deterministic representative, not a preferred hidden outcome.
    """
    candidates = candidate_space()
    observations = evaluate_arrangements(
        candidates, opcodes, regions, tuple(public_cases), timeout_seconds=timeout_seconds
    )
    survivors = tuple(
        candidate
        for candidate in candidates
        if all(
            case_passes(observations[candidate.digest()]["cases"][case.name], case)
            for case in public_cases
        )
    )
    if not survivors:
        raise M062Error("public evidence admits no arrangement")

    # The choice among byte-equivalent public survivors is deterministic and independent of
    # enumeration order.  Hidden validation remains outside this function.
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
        public_evidence_digest=_digest(b"m062-public-evidence-v1\0", evidence),
        observations=observations,
    )


def validate_arrangement(
    arrangement: Arrangement,
    opcodes: Mapping[str, int],
    regions: Mapping[str, int],
    hidden_cases: Sequence[CopyCase] = HIDDEN_CASES,
    timeout_seconds: float = 60.0,
) -> dict[str, object]:
    """Independent task-side admission; the generator never receives these cases."""
    observations = evaluate_arrangements(
        (arrangement,), opcodes, regions, tuple(hidden_cases), timeout_seconds=timeout_seconds
    )[arrangement.digest()]["cases"]
    passed = {
        case.name: case_passes(observations[case.name], case)
        for case in hidden_cases
    }
    evidence = {
        "arrangement_digest": arrangement.digest(),
        "case_digests": [case.digest() for case in hidden_cases],
        "passed": passed,
    }
    return {
        "schema": "m062-independent-validation-v1",
        "accepted": bool(passed) and all(passed.values()),
        "case_count": len(hidden_cases),
        "passed": passed,
        "hidden_evidence_digest": _digest(b"m062-hidden-evidence-v1\0", evidence),
    }


def validate_survivor_class(
    arrangements: Sequence[Arrangement],
    opcodes: Mapping[str, int],
    regions: Mapping[str, int],
    hidden_cases: Sequence[CopyCase] = HIDDEN_CASES,
    timeout_seconds: float = 60.0,
) -> dict[str, object]:
    """Require every public survivor to agree with the independent hidden evidence.

    A digest may choose a canonical source representation only after this check.  Otherwise the
    digest would be deciding hidden behaviour under the appearance of harmless determinism.
    """
    observations = evaluate_arrangements(
        tuple(arrangements), opcodes, regions, tuple(hidden_cases), timeout_seconds=timeout_seconds
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
        "schema": "m062-survivor-class-validation-v1",
        "candidate_count": len(arrangements),
        "accepted_count": sum(accepted.values()),
        "all_accepted": bool(accepted) and all(accepted.values()),
        "accepted": accepted,
        "hidden_evidence_digest": _digest(b"m062-survivor-class-evidence-v1\0", evidence),
    }


@dataclass(frozen=True)
class M062Protocol:
    region_probe_timeout_seconds: float = 2.0
    arrangement_timeout_seconds: float = 60.0
    schema: str = "m062-synthesized-control-protocol-v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "opcode_space": len(OPCODE_SPACE),
            "topologies": list(TOPOLOGIES),
            "conditions": list(CONDITIONS),
            "exit_positions": len(STEP_NAMES) + 1,
            "step_names": list(STEP_NAMES),
            "candidate_budget": len(candidate_space()),
            "public_case_digests": [case.digest() for case in PUBLIC_CASES],
            "hidden_case_count": len(HIDDEN_CASES),
            "hidden_case_commitment": _digest(
                b"m062-hidden-case-commitment-v1\0", [case.digest() for case in HIDDEN_CASES]
            ),
            "presupposed": list(PRESUPPOSED),
            "region_probe_timeout_seconds": self.region_probe_timeout_seconds,
            "arrangement_timeout_seconds": self.arrangement_timeout_seconds,
        }

    def digest(self) -> str:
        return _digest(b"m062-synthesized-control-protocol-v1\0", self.to_dict())


M062_PROTOCOL = M062Protocol()


@dataclass
class M062Manifest:
    mapping: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return dict(self.mapping)

    def digest(self) -> str:
        return _digest(b"m062-synthesized-control-manifest-v1\0", self.mapping)


def run_m062_synthesized_control(
    protocol: M062Protocol = M062_PROTOCOL,
    m061_protocol: M061Protocol = M061_PROTOCOL,
) -> M062Manifest:
    """Discover operations and region openers, synthesize an arrangement, then validate it."""
    structural_scans = run_all_scans(m061_protocol)
    opcodes = resolve_structure(structural_scans)
    region_scan = scan_region_openers(opcodes, protocol.region_probe_timeout_seconds)
    if not all(region_scan["witnesses_found"].values()):
        raise M062Error("the region scaffold missed a declared witness")
    regions = region_scan["resolved"]

    synthesis = synthesize_arrangement(
        opcodes, regions, PUBLIC_CASES, protocol.arrangement_timeout_seconds
    )
    # Choosing the smallest byte from an observational equivalence class is representation-only
    # if and only if every region member *and* every public arrangement survivor survives the
    # independent whole-program check.  Refuse otherwise instead of letting either canonical
    # digest decide hidden behaviour.
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
        label = f"exit={int(block_opcode):#04x},repeat={int(loop_opcode):#04x}"
        equivalence_validation[label] = verdict
    if not all(value["all_accepted"] for value in equivalence_validation.values()):
        raise M062Error(
            "a public arrangement or region-effect survivor disagrees on hidden behaviour"
        )

    validation = validate_arrangement(
        synthesis.selected, opcodes, regions, HIDDEN_CASES, protocol.arrangement_timeout_seconds
    )

    selected_module = emit_arrangement(synthesis.selected, opcodes, regions)
    replay = emit_arrangement(replace(synthesis.selected), dict(opcodes), dict(regions))
    mapping = {
        "schema": "m062-synthesized-control-manifest-v1",
        "status": "development_pending_qualification",
        "protocol_digest": protocol.digest(),
        "m061_protocol_digest": m061_protocol.digest(),
        "m061_scaffolds_replayed": len(structural_scans),
        "structural_opcodes_resolved": {
            label: hex(value) for label, value in sorted(opcodes.items())
        },
        "region_opcode_space_scanned": region_scan["scanned"],
        "region_outcome_counts": dict(region_scan["outcome_counts"]),
        "region_effect_classes": {
            label: [hex(value) for value in values]
            for label, values in region_scan["effect_classes"].items()
        },
        "region_openers_uniquely_determined": dict(region_scan["uniquely_determined"]),
        "region_openers_discovered": {
            label: hex(value) for label, value in sorted(regions.items())
        },
        "region_effect_class_hidden_validation": equivalence_validation,
        "region_witnesses_found": dict(region_scan["witnesses_found"]),
        "synthesis": synthesis.to_dict(),
        "independent_validation": validation,
        "selected_module_bytes": len(selected_module),
        # D020 forbids dressing statements about authorship up as measured booleans.  What came
        # from execution is present as mappings and digests above; what a person still supplied is
        # named as a list at the same level instead of asserted as `*_authored: True/False`.
        "emitter_inputs_from_discovery": {
            "operation_labels": sorted(opcodes),
            "region_effect_classes": {
                label: [hex(value) for value in values]
                for label, values in region_scan["effect_classes"].items()
            },
            "selected_arrangement_digest": synthesis.selected.digest(),
            "selection_evidence_digest": synthesis.public_evidence_digest,
        },
        "authored_elements": [
            "copy-task decomposition",
            "four atomic steps",
            "finite Cartesian search grammar",
            "generic WebAssembly emitter",
            "blocktype and label-depth encoding",
            "scaffold shapes",
            "public and hidden cases",
        ],
        "presupposed": list(PRESUPPOSED),
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
    return M062Manifest(mapping)


__all__ = [
    "Arrangement",
    "CONDITIONS",
    "CopyCase",
    "HIDDEN_CASES",
    "M062Error",
    "M062Manifest",
    "M062Protocol",
    "M062_PROTOCOL",
    "PRESUPPOSED",
    "PUBLIC_CASES",
    "REGION_LABELS",
    "STEP_NAMES",
    "SynthesisResult",
    "TOPOLOGIES",
    "candidate_space",
    "case_passes",
    "emit_arrangement",
    "evaluate_arrangements",
    "run_m062_synthesized_control",
    "scan_region_openers",
    "synthesize_arrangement",
    "validate_arrangement",
    "validate_survivor_class",
]
