"""M067: discover enough of an opaque body contract to re-embody four inherited skills.

M066 closed the constructive sequence, but its target ABI and compiler were still authored in
advance.  M067 opens a distinct phase.  Four target bodies live behind a separate Node process;
the Python lineage sees only opaque handles, accepted/rejected byte frames and four-byte replies.
It searches a frozen, finite contract grammar using public observations of its own behaviour,
then validates *every* public survivor on a disjoint hidden domain.

This is deliberately bounded contract discovery, not arbitrary hardware adaptation.  The grammar,
body bank, observation domains and budgets are explicit so the result cannot silently claim more.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import subprocess
from typing import Mapping, Sequence

from metamorphosis.m056_wasm_compiler import declared_tools
import metamorphosis.m057_constructed_migration as _m057
from metamorphosis.m060_whole_body_migration import reconstruct_m048_version_eight


class M067Error(ValueError):
    """Raised when the M067 boundary or a bounded discovery invariant is violated."""


RESPONSE_SCHEMA = "m067-opaque-body-response-v1"
BODY_HANDLES = (
    "body-0d62a9c8",
    "body-3f91e574",
    "body-71bc406e",
    "body-c4a28f13",
)
BODY_BANK_COMMITMENT = "019c70ec4ec82e45747cabf495ef4778a52b76036d6f3292217d91187c5fbfe3"
BODY_DIGESTS = (
    "309b3506ae3f466a5c71b488318af9b7e6ce8544802ffd9d0b723a4d9d28468e",
    "29a74b4c968b19d868d834fca6f9b8dde2e6870c61a8b654c8c835e06da7ea50",
    "2429f3337ec364915fddcb3706c4c4848042ed9acddf5e1af23b2e9161877688",
    "7648224f930d42a13a9c28e5b51a7ffc51503f73b63baebda6098ba7de37efeb",
)
FAMILIES = ("register", "stack", "mailbox")
CHECKSUMS = ("xor", "sum")
OPCODE_CANDIDATES = (0x11, 0x29, 0x43, 0x67)
RESPONSE_OFFSETS = (0, 1, 2)
RESPONSE_ENDIANNESS = ("little", "big")
RESPONSE_TRANSFORMS = ("identity", "xor_a5a5")
SKILLS = ("add", "max", "mean", "mul")
ANCHOR_SKILL = "add"
RESULT_SCALE = 300


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + _canonical_json(value)).hexdigest()


@dataclass(frozen=True)
class M067Protocol:
    body_count: int = 4
    base_candidate_count: int = 288
    max_batch_attempts: int = 50_000
    node_timeout_seconds: float = 120.0
    result_scale: int = RESULT_SCALE
    schema: str = "m067-body-contract-protocol-v1"

    def __post_init__(self) -> None:
        computed = (
            len(FAMILIES) * len(CHECKSUMS) * len(OPCODE_CANDIDATES)
            * len(RESPONSE_OFFSETS) * len(RESPONSE_ENDIANNESS)
            * len(RESPONSE_TRANSFORMS)
        )
        if self.body_count != len(BODY_HANDLES) or self.base_candidate_count != computed:
            raise M067Error("M067 bounded grammar size drifted")
        if self.result_scale != 300 or self.max_batch_attempts != 50_000:
            raise M067Error("M067 numeric representation or batch boundary drifted")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "body_bank_commitment": BODY_BANK_COMMITMENT,
            "body_handles": list(BODY_HANDLES),
            "body_digests": list(BODY_DIGESTS),
            "contract_grammar": {
                "families": list(FAMILIES),
                "checksums": list(CHECKSUMS),
                "opcode_candidates": list(OPCODE_CANDIDATES),
                "response_offsets": list(RESPONSE_OFFSETS),
                "response_endianness": list(RESPONSE_ENDIANNESS),
                "response_transforms": list(RESPONSE_TRANSFORMS),
                "result_scale": self.result_scale,
            },
            "anchor_skill": ANCHOR_SKILL,
            "base_candidate_count": self.base_candidate_count,
            "max_batch_attempts": self.max_batch_attempts,
            "public_arguments": {
                str(arity): [list(arguments) for arguments in values]
                for arity, values in sorted(_m057.OBSERVATION_ARGUMENTS.items())
            },
            "hidden_arguments": {
                str(arity): [list(arguments) for arguments in values]
                for arity, values in sorted(_m057.HIDDEN_ARGUMENTS.items())
            },
        }

    def digest(self) -> str:
        return _digest(b"m067-body-contract-protocol-v1\0", self.to_dict())


M067_PROTOCOL = M067Protocol()


@dataclass(frozen=True)
class SourceCase:
    case_id: str
    skill: str
    args: tuple[float, ...]
    expected: float

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.case_id,
            "skill": self.skill,
            "args": list(self.args),
            "expected": self.expected,
        }


@dataclass(frozen=True)
class AdapterCandidate:
    family: str
    checksum: str
    opcodes: tuple[tuple[str, int], ...]
    response_offset: int
    response_endian: str
    response_transform: str

    def opcode_for(self, skill: str) -> int:
        mapping = dict(self.opcodes)
        if skill not in mapping:
            raise M067Error(f"candidate has no opcode for {skill}")
        return mapping[skill]

    def to_dict(self) -> dict[str, object]:
        return {
            "family": self.family,
            "checksum": self.checksum,
            "opcodes": dict(self.opcodes),
            "response_offset": self.response_offset,
            "response_endian": self.response_endian,
            "response_transform": self.response_transform,
        }

    def digest(self) -> str:
        return _digest(b"m067-adapter-candidate-v1\0", self.to_dict())


@dataclass(frozen=True)
class DiscoveryOutcome:
    status: str
    anchor_survivors: tuple[AdapterCandidate, ...]
    candidate_class: tuple[AdapterCandidate, ...]
    attempts: int


@dataclass(frozen=True)
class HiddenValidation:
    all_survivors_passed: bool
    results: tuple[tuple[str, bool], ...]
    selected: AdapterCandidate | None
    attempts: int


@dataclass(frozen=True)
class M067Manifest:
    mapping: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return json.loads(json.dumps(self.mapping))

    def to_bytes(self) -> bytes:
        return _canonical_json(self.mapping)

    def digest(self) -> str:
        return hashlib.sha256(b"m067-manifest-v1\0" + self.to_bytes()).hexdigest()


def _runtime_script() -> Path:
    return Path(__file__).resolve().with_name("m067_opaque_body_runtime.mjs")


def _node_call(
    mode: str, request: Mapping[str, object], protocol: M067Protocol = M067_PROTOCOL,
) -> Mapping[str, object]:
    payload = _canonical_json(request)
    try:
        completed = subprocess.run(
            ["node", str(_runtime_script()), mode], input=payload,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=protocol.node_timeout_seconds, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise M067Error(f"opaque body runtime unavailable or timed out: {type(exc).__name__}") from exc
    try:
        response = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise M067Error("opaque body runtime returned malformed output") from exc
    if completed.returncode != 0 or not isinstance(response, Mapping) or response.get("fatal_error"):
        detail = response.get("fatal_error") if isinstance(response, Mapping) else completed.stderr.decode("utf-8", "replace")
        raise M067Error(f"opaque body runtime failed: {detail}")
    if response.get("schema") != RESPONSE_SCHEMA or response.get("mode") != mode:
        raise M067Error("opaque body runtime response identity mismatch")
    result = response.get("result")
    if not isinstance(result, Mapping):
        raise M067Error("opaque body runtime result is not an object")
    return result


def attest_body_bank(protocol: M067Protocol = M067_PROTOCOL) -> Mapping[str, object]:
    attestation = _node_call("attest", {}, protocol)
    if (
        attestation.get("body_count") != len(BODY_HANDLES)
        or tuple(attestation.get("body_handles", ())) != BODY_HANDLES
        or attestation.get("body_bank_commitment") != BODY_BANK_COMMITMENT
        or tuple(attestation.get("body_digests", ())) != BODY_DIGESTS
        or attestation.get("contract_descriptors_disclosed") is not False
    ):
        raise M067Error("opaque body-bank attestation differs from the frozen protocol")
    return attestation


def observe_source_cases(
    protocol: M067Protocol = M067_PROTOCOL,
) -> tuple[tuple[SourceCase, ...], tuple[SourceCase, ...], tuple[dict[str, object], ...], int]:
    """Observe the inherited source body; targets are not calculated from semantic labels."""
    lineage = reconstruct_m048_version_eight()
    tools = declared_tools(lineage.body())
    arities = {tool.tool_name: tool.arity for tool in tools}
    if tuple(sorted(arities)) != SKILLS:
        raise M067Error("the inherited source body does not expose the frozen skill class")
    public = _m057.observe_own_tools(lineage.body(), arities)
    hidden_samples = {
        name: [list(args) for args in _m057.HIDDEN_ARGUMENTS[arity]]
        for name, arity in arities.items()
    }
    hidden = _m057._node_call("observe", {"body": lineage.body(), "samples": hidden_samples}, _m057.M057_PROTOCOL)

    def cases(domain: str, arguments: Mapping[int, Sequence[tuple[float, ...]]], observations: Mapping[str, object]) -> tuple[SourceCase, ...]:
        found: list[SourceCase] = []
        values_by_skill = observations.get("observations")
        if not isinstance(values_by_skill, Mapping):
            raise M067Error("source observation result is malformed")
        for skill in SKILLS:
            args_for_skill = arguments[arities[skill]]
            values = values_by_skill.get(skill)
            if not isinstance(values, Sequence) or len(values) != len(args_for_skill):
                raise M067Error(f"source observations are incomplete for {skill}")
            for index, (args, value) in enumerate(zip(args_for_skill, values)):
                found.append(SourceCase(f"{domain}:{skill}:{index}", skill, tuple(args), float(value)))
        return tuple(found)

    metadata = tuple(
        {
            "tool_name": tool.tool_name,
            "declared_expression_id": tool.expression_id,
            "arity": tool.arity,
            "origin": tool.origin,
            "source_module": tool.source_module,
        }
        for tool in tools
    )
    return (
        cases("public", _m057.OBSERVATION_ARGUMENTS, public),
        cases("hidden", _m057.HIDDEN_ARGUMENTS, hidden),
        metadata,
        lineage.version(),
    )


def encode_frame(candidate: AdapterCandidate, case: SourceCase) -> bytes:
    opcode = candidate.opcode_for(case.skill)
    args = [int(value) & 0xFF for value in case.args]
    if any(float(int(value)) != value or not -128 <= value <= 127 for value in case.args):
        raise M067Error("M067 frames accept signed integer arguments only")
    arity = len(args)
    check_bytes = [opcode, arity, *args]
    if candidate.checksum == "xor":
        check = 0x5A
        for value in check_bytes:
            check ^= value
    elif candidate.checksum == "sum":
        check = (0x17 + sum(check_bytes)) & 0xFF
    else:
        raise M067Error("unknown candidate checksum")
    if candidate.family == "register":
        frame = [0xA7, arity, opcode, *args, check, 0x7A]
    elif candidate.family == "stack":
        frame = [0xB1]
        for value in args:
            frame.extend((0x05, value))
        frame.extend((opcode, arity, check, 0x0F))
    elif candidate.family == "mailbox":
        frame = [0xC3, arity]
        for index, value in enumerate(args):
            frame.extend((0x60 + index, value))
        frame.extend((0x6F, opcode, check, 0x64))
    else:
        raise M067Error("unknown candidate frame family")
    return bytes(frame)


def decode_response(candidate: AdapterCandidate, encoded: str) -> float:
    try:
        response = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as exc:
        raise M067Error("body response is not valid base64") from exc
    if len(response) != 4:
        raise M067Error("body response does not have the frozen four-byte length")
    pair = response[candidate.response_offset:candidate.response_offset + 2]
    if len(pair) != 2:
        raise M067Error("candidate response offset is outside the reply")
    raw = int.from_bytes(pair, candidate.response_endian, signed=False)
    if candidate.response_transform == "xor_a5a5":
        raw ^= 0xA5A5
    elif candidate.response_transform != "identity":
        raise M067Error("unknown candidate response transform")
    if raw >= 0x8000:
        raw -= 0x10000
    return raw / RESULT_SCALE


def _base_candidates() -> tuple[AdapterCandidate, ...]:
    candidates = tuple(
        AdapterCandidate(family, checksum, ((ANCHOR_SKILL, opcode),), offset, endian, transform)
        for family, checksum, opcode, offset, endian, transform in itertools.product(
            FAMILIES, CHECKSUMS, OPCODE_CANDIDATES, RESPONSE_OFFSETS,
            RESPONSE_ENDIANNESS, RESPONSE_TRANSFORMS,
        )
    )
    if len(candidates) != M067_PROTOCOL.base_candidate_count:
        raise M067Error("base candidate enumeration is incomplete")
    return candidates


def _evaluate_candidates(
    body_handle: str, candidates: Sequence[AdapterCandidate], cases: Sequence[SourceCase],
    mode: str, protocol: M067Protocol,
) -> tuple[tuple[AdapterCandidate, ...], int]:
    if mode not in {"public", "hidden"}:
        raise M067Error("candidate evaluation must name a public or hidden boundary")
    attempts: list[dict[str, str]] = []
    index: dict[str, tuple[int, SourceCase]] = {}
    for candidate_index, candidate in enumerate(candidates):
        for case in cases:
            attempt_id = f"{candidate_index}:{case.case_id}"
            attempts.append({
                "id": attempt_id,
                "frame": base64.b64encode(encode_frame(candidate, case)).decode("ascii"),
            })
            index[attempt_id] = (candidate_index, case)
    if len(attempts) > protocol.max_batch_attempts:
        raise M067Error("candidate evaluation exceeds the frozen attempt budget")
    if not attempts:
        return (), 0
    result = _node_call(mode, {"body_handle": body_handle, "attempts": attempts}, protocol)
    records = result.get("records")
    if not isinstance(records, Sequence) or len(records) != len(attempts):
        raise M067Error("opaque body returned an incomplete attempt batch")
    passed: dict[int, bool] = {candidate_index: True for candidate_index in range(len(candidates))}
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, Mapping):
            raise M067Error("opaque body returned a malformed attempt")
        attempt_id = str(record.get("id"))
        if attempt_id not in index or attempt_id in seen:
            raise M067Error("opaque body returned an unknown or duplicate attempt")
        seen.add(attempt_id)
        candidate_index, case = index[attempt_id]
        accepted = record.get("accepted") is True
        encoded = record.get("output")
        matches = False
        if accepted and isinstance(encoded, str):
            observed = decode_response(candidates[candidate_index], encoded)
            matches = math.isclose(observed, case.expected, rel_tol=0.0, abs_tol=1e-12)
        passed[candidate_index] = passed[candidate_index] and matches
    return tuple(candidate for i, candidate in enumerate(candidates) if passed[i]), len(attempts)


def _complete_candidates(anchor: AdapterCandidate) -> tuple[AdapterCandidate, ...]:
    used = {anchor.opcode_for(ANCHOR_SKILL)}
    remaining_opcodes = tuple(opcode for opcode in OPCODE_CANDIDATES if opcode not in used)
    remaining_skills = tuple(skill for skill in SKILLS if skill != ANCHOR_SKILL)
    return tuple(
        AdapterCandidate(
            anchor.family,
            anchor.checksum,
            tuple(sorted(((ANCHOR_SKILL, anchor.opcode_for(ANCHOR_SKILL)), *zip(remaining_skills, permutation)))),
            anchor.response_offset,
            anchor.response_endian,
            anchor.response_transform,
        )
        for permutation in itertools.permutations(remaining_opcodes)
    )


def discover_public_class(
    body_handle: str, public_cases: Sequence[SourceCase],
    protocol: M067Protocol = M067_PROTOCOL,
) -> DiscoveryOutcome:
    """Discover solely from public cases.  Hidden cases are absent from this API by design."""
    if body_handle not in BODY_HANDLES:
        raise M067Error("unknown opaque body handle")
    if not public_cases:
        return DiscoveryOutcome("insufficient_evidence", (), (), 0)
    anchor_cases = tuple(case for case in public_cases if case.skill == ANCHOR_SKILL)
    if len(anchor_cases) != len(_m057.OBSERVATION_ARGUMENTS[2]):
        raise M067Error("public anchor transcript is incomplete")
    anchors, first_attempts = _evaluate_candidates(
        body_handle, _base_candidates(), anchor_cases, "public", protocol,
    )
    complete = tuple(candidate for anchor in anchors for candidate in _complete_candidates(anchor))
    survivors, second_attempts = _evaluate_candidates(
        body_handle, complete, public_cases, "public", protocol,
    )
    status = "discovered" if survivors else "no_survivor"
    return DiscoveryOutcome(status, anchors, survivors, first_attempts + second_attempts)


def independently_validate_hidden_class(
    body_handle: str, candidates: Sequence[AdapterCandidate], hidden_cases: Sequence[SourceCase],
    protocol: M067Protocol = M067_PROTOCOL,
) -> HiddenValidation:
    """Validate the entire public equivalence class, never only a favoured survivor."""
    if not candidates or not hidden_cases:
        return HiddenValidation(False, (), None, 0)
    survivors, attempts = _evaluate_candidates(body_handle, candidates, hidden_cases, "hidden", protocol)
    passed_digests = {candidate.digest() for candidate in survivors}
    results = tuple((candidate.digest(), candidate.digest() in passed_digests) for candidate in candidates)
    all_passed = len(survivors) == len(candidates)
    selected = min(survivors, key=lambda candidate: candidate.digest()) if all_passed else None
    return HiddenValidation(all_passed, results, selected, attempts)


def select_body_handle(marker_parent_sha: str) -> str:
    """Predeclared post-freeze selector available to a later canonical workflow."""
    if not re.fullmatch(r"[0-9a-f]{40}", marker_parent_sha):
        raise M067Error("M067 parent must be a lower-case forty-character Git SHA")
    digest = hashlib.sha256(
        b"m067-body-selection-v1\0"
        + bytes.fromhex(BODY_BANK_COMMITMENT)
        + bytes.fromhex(marker_parent_sha)
    ).digest()
    return BODY_HANDLES[int.from_bytes(digest, "big") % len(BODY_HANDLES)]


def _default_candidate() -> AdapterCandidate:
    return AdapterCandidate(
        "register", "xor", tuple(zip(SKILLS, OPCODE_CANDIDATES)), 0, "little", "identity",
    )


def run_m067_development(protocol: M067Protocol = M067_PROTOCOL) -> M067Manifest:
    """Qualify one uniform discovery procedure against every precommitted opaque body."""
    attestation = attest_body_bank(protocol)
    public_cases, hidden_cases, source_tools, lineage_version = observe_source_cases(protocol)
    if {
        (case.skill, case.args) for case in public_cases
    } & {(case.skill, case.args) for case in hidden_cases}:
        raise M067Error("public and hidden observation domains overlap")

    body_results: dict[str, object] = {}
    selected_candidates: list[AdapterCandidate] = []
    for body_handle in BODY_HANDLES:
        discovery = discover_public_class(body_handle, public_cases, protocol)
        if discovery.status != "discovered" or not discovery.candidate_class:
            raise M067Error(f"no public contract survived for {body_handle}")
        hidden = independently_validate_hidden_class(
            body_handle, discovery.candidate_class, hidden_cases, protocol,
        )
        if not hidden.all_survivors_passed or hidden.selected is None:
            raise M067Error(f"the public class failed hidden validation for {body_handle}")
        selected = hidden.selected
        selected_candidates.append(selected)

        default_survivors, _ = _evaluate_candidates(
            body_handle, (_default_candidate(),), public_cases, "public", protocol,
        )
        framing_only = AdapterCandidate(
            selected.family,
            selected.checksum,
            tuple(zip(SKILLS, OPCODE_CANDIDATES)),
            selected.response_offset,
            selected.response_endian,
            selected.response_transform,
        )
        framing_survivors, _ = _evaluate_candidates(
            body_handle, (framing_only,), public_cases, "public", protocol,
        )
        corrupted = list(public_cases)
        first = corrupted[0]
        corrupted[0] = SourceCase(first.case_id, first.skill, first.args, first.expected + 1.0)
        corrupted_outcome = discover_public_class(body_handle, tuple(corrupted), protocol)
        no_transcript = discover_public_class(body_handle, (), protocol)

        body_results[body_handle] = {
            "public_case_count": len(public_cases),
            "hidden_case_count": len(hidden_cases),
            "base_candidate_count": protocol.base_candidate_count,
            "anchor_survivor_count": len(discovery.anchor_survivors),
            "public_candidate_class_size": len(discovery.candidate_class),
            "public_discovery_attempts": discovery.attempts,
            "hidden_validation_attempts": hidden.attempts,
            "all_public_survivors_passed_hidden": hidden.all_survivors_passed,
            "hidden_results": dict(hidden.results),
            "selected_adapter_digest": selected.digest(),
            "selected_adapter": selected.to_dict(),
            "controls": {
                "default_adapter_passed": bool(default_survivors),
                "framing_only_default_semantics_passed": bool(framing_survivors),
                "no_transcript_status": no_transcript.status,
                "no_transcript_adapter_count": len(no_transcript.candidate_class),
                "corrupted_transcript_status": corrupted_outcome.status,
                "corrupted_transcript_survivor_count": len(corrupted_outcome.candidate_class),
            },
        }

    if any(
        result["controls"][name]
        for result in body_results.values()
        for name in ("default_adapter_passed", "framing_only_default_semantics_passed")
    ):
        raise M067Error("a no-discovery control unexpectedly passed")
    if any(
        result["controls"]["corrupted_transcript_survivor_count"] != 0
        for result in body_results.values()
    ):
        raise M067Error("a corrupted source transcript retained an adapter")

    mapping = {
        "schema": "m067-body-contract-manifest-v1",
        "status": "development_pending_qualification",
        "protocol_digest": protocol.digest(),
        "body_bank_commitment": attestation["body_bank_commitment"],
        "body_bank_size": attestation["body_count"],
        "body_contract_descriptors_disclosed": attestation["contract_descriptors_disclosed"],
        "source_lineage_version": lineage_version,
        "source_tools": list(source_tools),
        "public_case_count": len(public_cases),
        "hidden_case_count": len(hidden_cases),
        "body_results": body_results,
        "all_precommitted_bodies_discovered": len(body_results) == len(BODY_HANDLES),
        "all_public_classes_passed_hidden": all(
            result["all_public_survivors_passed_hidden"] for result in body_results.values()
        ),
        "distinct_frame_families_discovered": sorted({candidate.family for candidate in selected_candidates}),
        "distinct_contracts_discovered": len({candidate.digest() for candidate in selected_candidates}),
        "bounded_contract_grammar": True,
        "complete_target_adapter_handed_to_lineage": False,
        "arbitrary_unknown_body_adaptation": False,
        "network_authority": False,
        "repository_write_authority": False,
        "credential_authority": False,
        "deployment_authority": False,
        "canonical": False,
    }
    return M067Manifest(mapping)


__all__ = [
    "AdapterCandidate", "BODY_BANK_COMMITMENT", "BODY_DIGESTS", "BODY_HANDLES",
    "DiscoveryOutcome", "HiddenValidation", "M067Error", "M067Manifest", "M067Protocol",
    "M067_PROTOCOL", "SourceCase", "attest_body_bank", "decode_response",
    "discover_public_class", "encode_frame", "independently_validate_hidden_class",
    "observe_source_cases", "run_m067_development", "select_body_handle",
]
