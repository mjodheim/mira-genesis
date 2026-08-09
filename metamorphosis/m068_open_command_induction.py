"""M068: induce opaque command words without an authored descriptor-product grammar.

The target runtime was frozen in an earlier commit.  This learner receives only that freeze's
opaque body/action handles, public interaction boundary and finite resource limit.  It enumerates
the complete word language, derives semantic profiles by observing the inherited source body and
keeps every public-equivalent adapter for separate class-wide hidden validation.

This remains bounded finite-language induction.  It is not arbitrary protocol induction and the
project-authored target bank is not represented as independently authored external evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import itertools
import json
import math
from pathlib import Path
import subprocess
from typing import Mapping, Sequence

from metamorphosis.m056_wasm_compiler import declared_tools
import metamorphosis.m057_constructed_migration as _m057
from metamorphosis.m060_whole_body_migration import reconstruct_m048_version_eight
from mira_core import MemoryLedger


class M068Error(ValueError):
    """Raised when an M068 boundary or frozen discovery invariant is violated."""


ROOT = Path(__file__).resolve().parents[1]
FROZEN_PROTOCOL_PATH = ROOT / "experiments" / "M068" / "FROZEN_PROTOCOL.json"
RUNTIME_PATH = Path(__file__).resolve().with_name("m068_external_body_bank.mjs")
RESPONSE_SCHEMA = "m068-external-body-response-v1"


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + _canonical_json(value)).hexdigest()


def _load_frozen() -> Mapping[str, object]:
    """Load protocol metadata only; the learner never reads the target runtime source."""
    try:
        value = json.loads(FROZEN_PROTOCOL_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise M068Error("M068 frozen protocol is absent or malformed") from exc
    protocol = value.get("protocol") if isinstance(value, Mapping) else None
    expected = value.get("protocol_sha256") if isinstance(value, Mapping) else None
    if not isinstance(protocol, Mapping):
        raise M068Error("M068 frozen executable protocol is absent")
    if expected != hashlib.sha256(b"m068-protocol-v1\0" + _canonical_json(protocol)).hexdigest():
        raise M068Error("M068 frozen protocol digest mismatch")
    return value


FROZEN = _load_frozen()
FROZEN_DATA = FROZEN["protocol"]
FROZEN_ATTESTATION = FROZEN["body_bank_attestation"]
BODY_HANDLES = tuple(str(value) for value in FROZEN_DATA["body_handles"])
ACTION_HANDLES = tuple(str(value) for value in FROZEN_DATA["action_handles"])
SKILLS = tuple(str(value) for value in FROZEN_DATA["source_skills"])


@dataclass(frozen=True)
class M068Protocol:
    max_word_length: int = int(FROZEN_DATA["max_word_length"])
    complete_word_count: int = int(FROZEN_DATA["complete_word_count"])
    max_batch_attempts: int = int(FROZEN_DATA["max_batch_attempts"])
    accepted_commands_per_body: int = int(FROZEN_DATA["accepted_commands_per_body"])
    node_timeout_seconds: float = 120.0
    schema: str = str(FROZEN_DATA["schema"])

    def __post_init__(self) -> None:
        computed = sum(len(ACTION_HANDLES) ** length for length in range(1, self.max_word_length + 1))
        if self.complete_word_count != computed or self.complete_word_count != 37_448:
            raise M068Error("M068 complete word language drifted")
        if ACTION_HANDLES != tuple(sorted(ACTION_HANDLES)):
            raise M068Error("M068 action handles are not in frozen lexical order")
        if self.accepted_commands_per_body != len(SKILLS) or len(BODY_HANDLES) != 4:
            raise M068Error("M068 target or source class size drifted")
        if self.max_batch_attempts < self.complete_word_count:
            raise M068Error("M068 frozen batch cannot hold a complete language scan")

    def to_dict(self) -> dict[str, object]:
        return json.loads(json.dumps(FROZEN_DATA))

    def digest(self) -> str:
        return str(FROZEN["protocol_sha256"])


M068_PROTOCOL = M068Protocol()


@dataclass(frozen=True)
class SourceCase:
    case_id: str
    skill: str
    args: tuple[int, ...]
    expected: float

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.case_id,
            "skill": self.skill,
            "args": list(self.args),
            "expected": self.expected,
        }


@dataclass(frozen=True)
class SourceEvidence:
    public_cases: tuple[SourceCase, ...]
    hidden_cases: tuple[SourceCase, ...]
    diagnostic_profiles: tuple[tuple[str, tuple[float, ...]], ...]
    tools: tuple[Mapping[str, object], ...]
    lineage_version: int

    def profiles(self) -> dict[str, tuple[float, ...]]:
        return dict(self.diagnostic_profiles)


@dataclass(frozen=True)
class CommandAdapter:
    assignments: tuple[tuple[str, tuple[str, ...]], ...]

    def __post_init__(self) -> None:
        skills = tuple(skill for skill, _word in self.assignments)
        words = tuple(word for _skill, word in self.assignments)
        if skills != tuple(sorted(SKILLS)) or len(set(words)) != len(words):
            raise M068Error("M068 adapter must be a sorted one-to-one complete mapping")

    def word_for(self, skill: str) -> tuple[str, ...]:
        try:
            return dict(self.assignments)[skill]
        except KeyError as exc:
            raise M068Error(f"M068 adapter has no command for {skill}") from exc

    def to_dict(self) -> dict[str, object]:
        return {"assignments": {skill: list(word) for skill, word in self.assignments}}

    def digest(self) -> str:
        return _digest(b"m068-command-adapter-v1\0", self.to_dict())


@dataclass(frozen=True)
class DiscoveryOutcome:
    status: str
    accepted_words: tuple[tuple[str, ...], ...]
    diagnostic_observations: tuple[tuple[tuple[str, ...], tuple[float, ...]], ...]
    candidate_class: tuple[CommandAdapter, ...]
    scan_attempts: int
    diagnostic_attempts: int
    public_validation_attempts: int

    @property
    def attempts(self) -> int:
        return self.scan_attempts + self.diagnostic_attempts + self.public_validation_attempts


@dataclass(frozen=True)
class HiddenValidation:
    all_survivors_passed: bool
    results: tuple[tuple[str, bool], ...]
    selected: CommandAdapter | None
    attempts: int


@dataclass(frozen=True)
class M068Manifest:
    mapping: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return json.loads(json.dumps(self.mapping))

    def to_bytes(self) -> bytes:
        return _canonical_json(self.mapping)

    def digest(self) -> str:
        return hashlib.sha256(b"m068-manifest-v1\0" + self.to_bytes()).hexdigest()


def enumerate_command_words(
    protocol: M068Protocol = M068_PROTOCOL,
) -> tuple[tuple[str, ...], ...]:
    words = tuple(
        word
        for length in range(1, protocol.max_word_length + 1)
        for word in itertools.product(ACTION_HANDLES, repeat=length)
    )
    if len(words) != protocol.complete_word_count or len(set(words)) != len(words):
        raise M068Error("M068 command-word enumeration is incomplete or duplicated")
    return words


def _node_call(
    mode: str, request: Mapping[str, object], protocol: M068Protocol = M068_PROTOCOL,
) -> Mapping[str, object]:
    if mode not in {"attest", "public", "hidden"}:
        raise M068Error("M068 runtime mode is outside the frozen boundary")
    try:
        completed = subprocess.run(
            ["node", str(RUNTIME_PATH), mode], input=_canonical_json(request),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=protocol.node_timeout_seconds, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise M068Error(f"M068 target runtime unavailable or timed out: {type(exc).__name__}") from exc
    try:
        response = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise M068Error("M068 target runtime returned malformed output") from exc
    if completed.returncode != 0 or not isinstance(response, Mapping) or response.get("fatal_error"):
        detail = response.get("fatal_error") if isinstance(response, Mapping) else completed.stderr.decode("utf-8", "replace")
        raise M068Error(f"M068 target runtime failed: {detail}")
    if response.get("schema") != RESPONSE_SCHEMA or response.get("mode") != mode:
        raise M068Error("M068 target runtime response identity mismatch")
    result = response.get("result")
    if not isinstance(result, Mapping):
        raise M068Error("M068 target runtime result is not an object")
    return result


def attest_body_bank(protocol: M068Protocol = M068_PROTOCOL) -> Mapping[str, object]:
    attestation = _node_call("attest", {}, protocol)
    if attestation != FROZEN_ATTESTATION:
        raise M068Error("M068 live target attestation differs from the pre-learner freeze")
    return attestation


def _argument_map(field: str) -> dict[int, tuple[tuple[int, ...], ...]]:
    raw = FROZEN_DATA[field]
    if not isinstance(raw, Mapping):
        raise M068Error(f"M068 frozen {field} is malformed")
    return {
        int(arity): tuple(tuple(int(value) for value in args) for args in values)
        for arity, values in raw.items()
    }


def observe_source_evidence() -> SourceEvidence:
    """Observe source behaviour in Node; semantic results are never calculated from tool names."""
    lineage = reconstruct_m048_version_eight()
    tools = declared_tools(lineage.body())
    arities = {tool.tool_name: tool.arity for tool in tools}
    if tuple(sorted(arities)) != tuple(sorted(SKILLS)) or lineage.version() != int(FROZEN_DATA["source_lineage_version"]):
        raise M068Error("M068 inherited source lineage differs from the freeze")

    public_arguments = _argument_map("public_arguments")
    hidden_arguments = _argument_map("hidden_arguments")
    frozen_diagnostics = tuple(
        tuple(int(value) for value in args)
        for args in FROZEN_DATA["public_diagnostic_arguments"]
    )
    public_samples = {skill: [list(args) for args in public_arguments[arity]] for skill, arity in arities.items()}
    hidden_samples = {skill: [list(args) for args in hidden_arguments[arity]] for skill, arity in arities.items()}
    diagnostic_samples = {
        skill: [list(args[:arity]) for args in frozen_diagnostics]
        for skill, arity in arities.items()
    }
    public = _m057._node_call("observe", {"body": lineage.body(), "samples": public_samples}, _m057.M057_PROTOCOL)
    hidden = _m057._node_call("observe", {"body": lineage.body(), "samples": hidden_samples}, _m057.M057_PROTOCOL)
    diagnostic = _m057._node_call("observe", {"body": lineage.body(), "samples": diagnostic_samples}, _m057.M057_PROTOCOL)

    def cases(domain: str, arguments: Mapping[int, Sequence[tuple[int, ...]]], observed: Mapping[str, object]) -> tuple[SourceCase, ...]:
        observations = observed.get("observations")
        if not isinstance(observations, Mapping):
            raise M068Error(f"M068 {domain} source observation is malformed")
        found: list[SourceCase] = []
        for skill in sorted(SKILLS):
            args_for_skill = arguments[arities[skill]]
            values = observations.get(skill)
            if not isinstance(values, Sequence) or len(values) != len(args_for_skill):
                raise M068Error(f"M068 {domain} source observation is incomplete for {skill}")
            for index, (args, value) in enumerate(zip(args_for_skill, values)):
                found.append(SourceCase(f"{domain}:{skill}:{index}", skill, tuple(args), float(value)))
        return tuple(found)

    raw_profiles = diagnostic.get("observations")
    if not isinstance(raw_profiles, Mapping):
        raise M068Error("M068 diagnostic source observation is malformed")
    profiles = tuple(
        (skill, tuple(float(value) for value in raw_profiles[skill]))
        for skill in sorted(SKILLS)
    )
    if any(len(profile) != len(frozen_diagnostics) for _skill, profile in profiles):
        raise M068Error("M068 diagnostic source profiles are incomplete")
    metadata = tuple({
        "tool_name": tool.tool_name,
        "declared_expression_id": tool.expression_id,
        "arity": tool.arity,
        "origin": tool.origin,
        "source_module": tool.source_module,
    } for tool in tools)
    return SourceEvidence(
        cases("public", public_arguments, public),
        cases("hidden", hidden_arguments, hidden),
        profiles, metadata, lineage.version(),
    )


def _envelope_args(args: Sequence[int]) -> list[int]:
    values = [int(value) for value in args]
    if any(float(value) != source or value < -128 or value > 127 for value, source in zip(values, args)):
        raise M068Error("M068 target accepts signed integer argument slots only")
    if len(values) == 2:
        values.append(0)
    if len(values) != 3:
        raise M068Error("M068 source case cannot fit the frozen three-slot host envelope")
    return values


def _transact(
    body_handle: str, attempts: Sequence[Mapping[str, object]], mode: str,
    protocol: M068Protocol,
) -> tuple[Mapping[str, object], ...]:
    if body_handle not in BODY_HANDLES:
        raise M068Error("unknown opaque body handle")
    if len(attempts) > protocol.max_batch_attempts:
        raise M068Error("M068 attempt batch exceeds the frozen resource bound")
    result = _node_call(mode, {"body_handle": body_handle, "attempts": list(attempts)}, protocol)
    records = result.get("records")
    if not isinstance(records, Sequence) or len(records) != len(attempts):
        raise M068Error("M068 target returned an incomplete attempt batch")
    expected_ids = {str(attempt["id"]) for attempt in attempts}
    seen: set[str] = set()
    validated: list[Mapping[str, object]] = []
    for record in records:
        if not isinstance(record, Mapping):
            raise M068Error("M068 target returned a malformed attempt record")
        attempt_id = str(record.get("id"))
        if attempt_id not in expected_ids or attempt_id in seen:
            raise M068Error("M068 target returned an unknown or duplicate attempt")
        if record.get("accepted") not in {True, False}:
            raise M068Error("M068 target returned a non-boolean admission result")
        observation = record.get("observation")
        if record.get("accepted") is True and (not isinstance(observation, (int, float)) or isinstance(observation, bool)):
            raise M068Error("M068 accepted transaction has no numeric observation")
        if record.get("accepted") is False and observation is not None:
            raise M068Error("M068 rejected transaction leaked an observation")
        seen.add(attempt_id)
        validated.append(record)
    return tuple(validated)


def _evaluate_adapters(
    body_handle: str, candidates: Sequence[CommandAdapter], cases: Sequence[SourceCase],
    mode: str, protocol: M068Protocol,
) -> tuple[tuple[CommandAdapter, ...], int]:
    if mode not in {"public", "hidden"}:
        raise M068Error("M068 adapter evaluation must name a public or hidden boundary")
    attempts: list[dict[str, object]] = []
    index: dict[str, tuple[int, SourceCase]] = {}
    for candidate_index, candidate in enumerate(candidates):
        for case in cases:
            attempt_id = f"{candidate_index}:{case.case_id}"
            attempts.append({
                "id": attempt_id,
                "actions": list(candidate.word_for(case.skill)),
                "args": _envelope_args(case.args),
            })
            index[attempt_id] = (candidate_index, case)
    if not attempts:
        return (), 0
    records = _transact(body_handle, attempts, mode, protocol)
    passed = {index: True for index in range(len(candidates))}
    for record in records:
        candidate_index, case = index[str(record["id"])]
        matches = record["accepted"] is True and math.isclose(
            float(record["observation"]), case.expected, rel_tol=0.0, abs_tol=1e-12,
        )
        passed[candidate_index] = passed[candidate_index] and matches
    return tuple(candidate for index, candidate in enumerate(candidates) if passed[index]), len(attempts)


def _candidate_mappings(
    observations: Mapping[tuple[str, ...], tuple[float, ...]],
    source_profiles: Mapping[str, tuple[float, ...]],
) -> tuple[CommandAdapter, ...]:
    if len(observations) != len(SKILLS) or set(source_profiles) != set(SKILLS):
        return ()
    candidates: list[CommandAdapter] = []
    words = tuple(sorted(observations))
    for permutation in itertools.permutations(words):
        assignments = tuple(zip(sorted(SKILLS), permutation))
        if all(
            len(observations[word]) == len(source_profiles[skill])
            and all(math.isclose(left, right, rel_tol=0.0, abs_tol=1e-12) for left, right in zip(observations[word], source_profiles[skill]))
            for skill, word in assignments
        ):
            candidates.append(CommandAdapter(assignments))
    return tuple(sorted(candidates, key=lambda candidate: candidate.digest()))


def discover_public_class(
    body_handle: str, public_cases: Sequence[SourceCase],
    diagnostic_profiles: Mapping[str, tuple[float, ...]],
    protocol: M068Protocol = M068_PROTOCOL,
) -> DiscoveryOutcome:
    """Discover from public source evidence only.  Hidden evidence is absent by construction."""
    if body_handle not in BODY_HANDLES:
        raise M068Error("unknown opaque body handle")
    if not public_cases:
        return DiscoveryOutcome("insufficient_evidence", (), (), (), 0, 0, 0)
    if set(diagnostic_profiles) != set(SKILLS):
        raise M068Error("M068 diagnostic source transcript is incomplete")

    diagnostics = tuple(tuple(int(value) for value in args) for args in FROZEN_DATA["public_diagnostic_arguments"])
    words = enumerate_command_words(protocol)
    scan_attempts = tuple({
        "id": str(index), "actions": list(word), "args": list(diagnostics[0]),
    } for index, word in enumerate(words))
    scan_records = _transact(body_handle, scan_attempts, "public", protocol)
    accepted: list[tuple[str, ...]] = []
    first_observations: dict[tuple[str, ...], float] = {}
    for record in scan_records:
        if record["accepted"] is True:
            word = words[int(str(record["id"]))]
            accepted.append(word)
            first_observations[word] = float(record["observation"])
    if len(accepted) != protocol.accepted_commands_per_body:
        return DiscoveryOutcome("no_complete_command_set", tuple(accepted), (), (), len(words), 0, 0)

    second_attempts = tuple({
        "id": str(index), "actions": list(word), "args": list(diagnostics[1]),
    } for index, word in enumerate(accepted))
    second_records = _transact(body_handle, second_attempts, "public", protocol)
    observations = {
        accepted[int(str(record["id"]))]: (
            first_observations[accepted[int(str(record["id"]))]], float(record["observation"]),
        )
        for record in second_records if record["accepted"] is True
    }
    diagnostic_observations = tuple(sorted(observations.items()))
    mapped = _candidate_mappings(observations, diagnostic_profiles)
    if not mapped:
        return DiscoveryOutcome(
            "no_complete_mapping", tuple(accepted), diagnostic_observations, (),
            len(words), len(second_attempts), 0,
        )
    survivors, public_attempts = _evaluate_adapters(
        body_handle, mapped, public_cases, "public", protocol,
    )
    return DiscoveryOutcome(
        "discovered" if survivors else "no_survivor",
        tuple(accepted), diagnostic_observations, survivors,
        len(words), len(second_attempts), public_attempts,
    )


def independently_validate_hidden_class(
    body_handle: str, candidates: Sequence[CommandAdapter], hidden_cases: Sequence[SourceCase],
    protocol: M068Protocol = M068_PROTOCOL,
) -> HiddenValidation:
    """Validate every public survivor, selecting by digest only after the full class passes."""
    if not candidates or not hidden_cases:
        return HiddenValidation(False, (), None, 0)
    survivors, attempts = _evaluate_adapters(body_handle, candidates, hidden_cases, "hidden", protocol)
    passed_digests = {candidate.digest() for candidate in survivors}
    results = tuple((candidate.digest(), candidate.digest() in passed_digests) for candidate in candidates)
    all_passed = len(survivors) == len(candidates)
    selected = min(survivors, key=lambda candidate: candidate.digest()) if all_passed else None
    return HiddenValidation(all_passed, results, selected, attempts)


def _naive_adapter(words: Sequence[tuple[str, ...]]) -> CommandAdapter:
    return CommandAdapter(tuple(zip(sorted(SKILLS), words)))


def _single_control_rejected(
    body_handle: str, actions: Sequence[str], attempt_id: str, protocol: M068Protocol,
) -> bool:
    records = _transact(body_handle, ({
        "id": attempt_id, "actions": list(actions), "args": [6, 3, 9],
    },), "public", protocol)
    return records[0]["accepted"] is False and records[0]["observation"] is None


def run_m068_development(protocol: M068Protocol = M068_PROTOCOL) -> M068Manifest:
    """Run the unchanged learner and every preregistered control on all frozen bodies."""
    attestation = attest_body_bank(protocol)
    source = observe_source_evidence()
    if {(case.skill, case.args) for case in source.public_cases} & {(case.skill, case.args) for case in source.hidden_cases}:
        raise M068Error("M068 public and hidden source domains overlap")

    memory = MemoryLedger()
    memory.append("m068_run_started", {
        "protocol_digest": protocol.digest(),
        "body_bank_commitment": str(attestation["body_bank_commitment"]),
        "body_count": len(BODY_HANDLES),
    })
    body_results: dict[str, object] = {}
    selected_adapters: list[CommandAdapter] = []
    for body_handle in BODY_HANDLES:
        discovery = discover_public_class(body_handle, source.public_cases, source.profiles(), protocol)
        if discovery.status != "discovered" or not discovery.candidate_class:
            raise M068Error(f"M068 found no public command adapter for {body_handle}")
        hidden = independently_validate_hidden_class(body_handle, discovery.candidate_class, source.hidden_cases, protocol)
        if not hidden.all_survivors_passed or hidden.selected is None:
            raise M068Error(f"M068 public class failed hidden validation for {body_handle}")
        selected = hidden.selected
        selected_adapters.append(selected)

        declaration = _naive_adapter(tuple((action,) for action in ACTION_HANDLES[:len(SKILLS)]))
        declaration_survivors, _ = _evaluate_adapters(body_handle, (declaration,), source.public_cases, "public", protocol)
        lexical = _naive_adapter(tuple(sorted(discovery.accepted_words)))
        lexical_survivors, _ = _evaluate_adapters(body_handle, (lexical,), source.public_cases, "public", protocol)
        no_transcript = discover_public_class(body_handle, (), source.profiles(), protocol)
        corrupted = list(source.public_cases)
        first = corrupted[0]
        corrupted[0] = SourceCase(first.case_id, first.skill, first.args, first.expected + 1.0)
        corrupted_outcome = discover_public_class(body_handle, tuple(corrupted), source.profiles(), protocol)
        non_command = next(word for word in enumerate_command_words(protocol) if word not in discovery.accepted_words)
        unknown_rejected = _single_control_rejected(body_handle, ("signal-unknown",), "unknown", protocol)
        non_command_rejected = _single_control_rejected(body_handle, non_command, "non-command", protocol)
        assignments = list(selected.assignments)
        assignments[0] = (assignments[0][0], selected.assignments[1][1])
        assignments[1] = (assignments[1][0], selected.assignments[0][1])
        mutated = CommandAdapter(tuple(assignments))
        mutation_hidden = independently_validate_hidden_class(body_handle, (mutated,), source.hidden_cases, protocol)

        controls = {
            "declaration_order_actions_passed": bool(declaration_survivors),
            "lexical_semantic_assignment_passed": bool(lexical_survivors),
            "empty_transcript_status": no_transcript.status,
            "empty_transcript_adapter_count": len(no_transcript.candidate_class),
            "corrupted_source_observation_status": corrupted_outcome.status,
            "corrupted_source_observation_adapter_count": len(corrupted_outcome.candidate_class),
            "unknown_action_rejected": unknown_rejected,
            "non_command_word_rejected": non_command_rejected,
            "semantic_assignment_mutation_passed_hidden": mutation_hidden.all_survivors_passed,
            "learner_inspected_target_source": False,
        }
        if (
            controls["declaration_order_actions_passed"]
            or controls["lexical_semantic_assignment_passed"]
            or controls["empty_transcript_adapter_count"] != 0
            or controls["corrupted_source_observation_adapter_count"] != 0
            or not controls["unknown_action_rejected"]
            or not controls["non_command_word_rejected"]
            or controls["semantic_assignment_mutation_passed_hidden"]
            or controls["learner_inspected_target_source"]
        ):
            raise M068Error(f"M068 preregistered control failed for {body_handle}")

        body_results[body_handle] = {
            "accepted_words": [list(word) for word in discovery.accepted_words],
            "accepted_word_count": len(discovery.accepted_words),
            "diagnostic_observations": [
                {"word": list(word), "profile": list(profile)}
                for word, profile in discovery.diagnostic_observations
            ],
            "complete_word_count": protocol.complete_word_count,
            "public_case_count": len(source.public_cases),
            "hidden_case_count": len(source.hidden_cases),
            "public_candidate_class_size": len(discovery.candidate_class),
            "public_discovery_attempts": discovery.attempts,
            "language_scan_attempts": discovery.scan_attempts,
            "additional_diagnostic_attempts": discovery.diagnostic_attempts,
            "public_validation_attempts": discovery.public_validation_attempts,
            "hidden_validation_attempts": hidden.attempts,
            "all_public_survivors_passed_hidden": hidden.all_survivors_passed,
            "hidden_results": dict(hidden.results),
            "selected_adapter_digest": selected.digest(),
            "selected_adapter": selected.to_dict(),
            "controls": controls,
        }
        memory.append("m068_body_qualified", {
            "body_handle": body_handle,
            "selected_adapter_digest": selected.digest(),
            "public_candidate_class_size": len(discovery.candidate_class),
            "all_public_survivors_passed_hidden": hidden.all_survivors_passed,
        })

    all_discovered = len(body_results) == len(BODY_HANDLES)
    all_hidden = all(result["all_public_survivors_passed_hidden"] for result in body_results.values())
    distinct_languages = len({
        _digest(b"m068-selected-command-language-v1\0", adapter.to_dict())
        for adapter in selected_adapters
    })
    memory.append("m068_run_finished", {
        "all_precommitted_bodies_discovered": all_discovered,
        "all_public_classes_passed_hidden": all_hidden,
        "distinct_command_languages": distinct_languages,
    })
    mapping = {
        "schema": "m068-open-command-induction-manifest-v1",
        "status": "development_pending_qualification",
        "freeze_commit": "f8c67f1853743e473785d92bed5195c5621e8943",
        "protocol_digest": protocol.digest(),
        "target_runtime_lf_sha256": FROZEN["target_runtime_lf_sha256"],
        "body_bank_commitment": attestation["body_bank_commitment"],
        "body_handles": list(BODY_HANDLES),
        "action_handles": list(ACTION_HANDLES),
        "source_lineage_version": source.lineage_version,
        "source_tools": list(source.tools),
        "source_diagnostic_profiles": {skill: list(profile) for skill, profile in source.diagnostic_profiles},
        "public_source_case_count": len(source.public_cases),
        "hidden_source_case_count": len(source.hidden_cases),
        "complete_word_count": protocol.complete_word_count,
        "all_precommitted_bodies_discovered": all_discovered,
        "all_public_classes_passed_hidden": all_hidden,
        "distinct_command_languages_discovered": distinct_languages,
        "body_results": body_results,
        "evidence_memory_schema": "mira-memory-ledger-v1",
        "evidence_memory_event_count": len(memory.events),
        "evidence_memory_digest": memory.digest,
        "descriptor_product_grammar_supplied": False,
        "complete_target_adapter_supplied": False,
        "generic_bounded_word_language": True,
        "target_bank_frozen_before_learner": True,
        "discovery_api_has_hidden_input": False,
        "target_source_inspected_by_learner": False,
        "external_target_authorship": False,
        "arbitrary_protocol_induction": False,
        "real_device_competence": False,
        "multimodal_grounding": False,
        "general_intelligence_claimed": False,
        "network_authority": False,
        "repository_write_authority": False,
        "credential_authority": False,
        "deployment_authority": False,
        "canonical": False,
    }
    return M068Manifest(mapping)


__all__ = [
    "ACTION_HANDLES", "BODY_HANDLES", "CommandAdapter", "DiscoveryOutcome", "HiddenValidation",
    "M068Error", "M068Manifest", "M068Protocol", "M068_PROTOCOL", "SKILLS", "SourceCase",
    "SourceEvidence", "attest_body_bank", "discover_public_class", "enumerate_command_words",
    "independently_validate_hidden_class", "observe_source_evidence", "run_m068_development",
]
