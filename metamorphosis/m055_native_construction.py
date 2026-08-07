"""M055: construct a capability inside the migrated M048 lineage.

Requirement 1 of issue #72 asked the language-extension work to continue the qualified M048
lineage. M053 and M054 do not: both import the frozen M051 catalogue and start from an empty
registry. Since M049 the line has run on integer sequences, separated from the executable
modular body M047 built and M048 migrated into Node.

M055 puts the construction back inside that body. It reconstructs the accepted M048
version-eight native state, faces a task no program expressible in the accepted module
language solves, constructs a tool from formation rules rather than selecting a template,
verifies that every inherited capability still holds, adopts transactionally, and then reaches
a second task only by using the acquired expression as material for the next construction.

M048 is qualified, so under D003 nothing here modifies it. Its reconstruction helpers are read
and its Node runtime is left untouched; M055 ships its own.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Mapping, Sequence

import metamorphosis.m048_runtime_migration as _m048_facade  # applies the qualified M048 corrections
import metamorphosis.m048_native_lineage as _m048


class M055Error(ValueError):
    """Raised when an M055 artifact violates the bounded protocol."""


def _digest(domain: bytes, value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(domain + payload).hexdigest()


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


ATOMS = ("previous", "current")
OPERATORS = ("add", "subtract", "minimum", "maximum", "multiply")
RESPONSE_SCHEMA = "m055-node-response-v1"


def expression_space_size(depth: int) -> int:
    if depth < 0:
        raise M055Error("depth must not be negative")
    count = len(ATOMS)
    for _ in range(depth):
        count = len(ATOMS) + len(OPERATORS) * count * count
    return count


@dataclass(frozen=True)
class M055Protocol:
    max_expression_depth: int = 3
    construction_budget: int = 1024
    beam_width: int = 12
    node_timeout_seconds: float = 60.0
    creation_tool: str = "variation"
    reuse_tool: str = "amplified"
    schema: str = "m055-native-construction-protocol-v1"

    def __post_init__(self) -> None:
        if self.max_expression_depth != 3:
            raise M055Error("M055 fixes the formation depth at three")
        if self.construction_budget != 1024 or self.beam_width != 12:
            raise M055Error("M055 construction bounds are frozen")
        if self.construction_budget >= expression_space_size(2):
            raise M055Error("the budget must not be able to enumerate the depth-two space")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "max_expression_depth": self.max_expression_depth,
            "construction_budget": self.construction_budget,
            "beam_width": self.beam_width,
            "node_timeout_seconds": self.node_timeout_seconds,
            "creation_tool": self.creation_tool,
            "reuse_tool": self.reuse_tool,
            "admissible_space": expression_space_size(self.max_expression_depth),
        }

    def digest(self) -> str:
        return _digest(b"m055-native-construction-protocol-v1\0", self.to_dict())


M055_PROTOCOL = M055Protocol()
ADMISSIBLE_SPACE = expression_space_size(M055_PROTOCOL.max_expression_depth)


def _node_script() -> Path:
    return Path(__file__).resolve().with_name("m055_node_runtime.mjs")


def _node_call(mode: str, request: Mapping[str, object], protocol: M055Protocol) -> Mapping[str, object]:
    """Every candidate runs in a separate disposable Node process."""
    try:
        completed = subprocess.run(
            ["node", str(_node_script()), mode],
            input=_canonical_json(request),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=protocol.node_timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise M055Error(f"Node runtime unavailable or timed out: {type(exc).__name__}") from exc
    try:
        response = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise M055Error("Node runtime returned malformed output") from exc
    if completed.returncode != 0 or not isinstance(response, Mapping) or response.get("fatal_error"):
        detail = response.get("fatal_error") if isinstance(response, Mapping) else completed.stderr.decode("utf-8", "replace")
        raise M055Error(f"Node runtime failed: {detail}")
    if response.get("schema") != RESPONSE_SCHEMA or response.get("mode") != mode:
        raise M055Error("Node runtime response identity mismatch")
    result = response.get("result")
    if not isinstance(result, Mapping):
        raise M055Error("Node runtime result is not an object")
    return result


@dataclass(frozen=True)
class InheritedLineage:
    """The accepted M048 version-eight state and everything it must not lose."""

    state: Mapping[str, object]
    retained: tuple[object, ...]
    source_retained_count: int

    def body(self) -> Mapping[str, object]:
        return self.state["body"]

    def version(self) -> int:
        return int(self.state["version"])


def reconstruct_m048_version_eight(protocol: M055Protocol = M055_PROTOCOL) -> InheritedLineage:
    """Re-derive the accepted M048 state rather than assert it.

    The lineage claim is only worth something if the starting point is the state M048 actually
    accepted, so it is rebuilt through M048's own reconstruction, migration, proposal,
    validation and adoption path.
    """
    snapshot, memory, retained, _artifacts = _m048._reconstruct_m047()
    migrated = _m048._build_migrated_state(snapshot, memory, _m048.M048_PROTOCOL)
    tasks = _m048._task_cases()
    public, hidden = tasks["maximum"]
    proposal = _m048._propose(migrated["body"], "m048_native_maximum", public, _m048.M048_PROTOCOL)
    selection = _m048._validate(
        migrated["body"], proposal, retained, public, hidden,
        ("interpretation", "selection", "tool_max"), _m048.M048_PROTOCOL,
    )
    accepted, adoption = _m048._adopt_native_candidate(migrated, "m048_native_maximum", selection)
    if not adoption.get("adopted") or accepted.get("version") != 8:
        raise M055Error("could not reconstruct the accepted M048 version-eight state")
    inherited = tuple(retained) + tuple(public) + tuple(hidden)
    return InheritedLineage(state=accepted, retained=inherited, source_retained_count=len(retained))


def _case_dicts(cases: Sequence[object]) -> list[dict[str, object]]:
    return _m048._case_dicts(cases)


def _case(case_id: str, request: str, expected: object, origin: str):
    return _m048._case(case_id, request, expected, origin)


def _variation(values: Sequence[int]) -> int:
    return sum(abs(b - a) for a, b in zip(values, values[1:]))


def _amplified(values: Sequence[int]) -> int:
    """Per adjacent pair, the larger of the gap and its square; summed.

    The point of this shape is depth. Written from the formation atoms the expression is
    `maximum(|d|, multiply(|d|, |d|))` where `|d|` is itself depth two, so the whole tree is
    depth four and lies outside the declared formation depth of three: unreachable, not merely
    expensive. With the acquired expression available as an atom the same function is depth
    two. The acquisition therefore enlarges what is expressible at fixed depth.

    An earlier reuse task — the maximum of second-order absolute differences — was withdrawn
    because its ablation refuted it. See `experiments/M055/PROTOCOL.md`.
    """
    return sum(max(abs(b - a), abs(b - a) * abs(b - a)) for a, b in zip(values, values[1:]))


def creation_cases() -> tuple[tuple[object, ...], tuple[object, ...]]:
    public = tuple(
        _case(f"m055_variation_public_{index}", f"variation {a} {b} {c}", _variation((a, b, c)), "m055_variation")
        for index, (a, b, c) in enumerate(((2, -1, 4), (9, -8, 5), (5, 7, -1)), start=1)
    )
    hidden = tuple(
        _case(f"m055_variation_hidden_{index}", f"variation {a} {b} {c}", _variation((a, b, c)), "m055_variation")
        for index, (a, b, c) in enumerate(((-3, 6, -2), (0, 0, 4)), start=1)
    )
    return public, hidden


def reuse_cases() -> tuple[tuple[object, ...], tuple[object, ...]]:
    public = tuple(
        _case(f"m055_amplified_public_{index}", f"amplified {a} {b} {c}", _amplified((a, b, c)), "m055_amplified")
        for index, (a, b, c) in enumerate(((1, -4, 3), (-6, 0, -8), (4, -2, -3)), start=1)
    )
    hidden = tuple(
        _case(f"m055_amplified_hidden_{index}", f"amplified {a} {b} {c}", _amplified((a, b, c)), "m055_amplified")
        for index, (a, b, c) in enumerate(((3, -5, 2), (0, 5, -5)), start=1)
    )
    return public, hidden


def construct_capability(
    body: Mapping[str, object],
    *,
    task_id: str,
    token: str,
    tool_name: str,
    arity: int,
    passes: int,
    public: Sequence[object],
    reductions: Sequence[str],
    acquired_expression: Mapping[str, object] | None = None,
    protocol: M055Protocol = M055_PROTOCOL,
) -> Mapping[str, object]:
    """Build a tool from formation rules. The hidden bank never reaches this call."""
    return _node_call("construct", {
        "body": body,
        "task_id": task_id,
        "token": token,
        "tool_name": tool_name,
        "arity": arity,
        "passes": passes,
        "public_cases": _case_dicts(public),
        "budget": protocol.construction_budget,
        "beam_width": protocol.beam_width,
        "max_depth": protocol.max_expression_depth,
        "reductions": list(reductions),
        "acquired_expression": acquired_expression,
    }, protocol)


def validate_candidate(
    candidate_body: Mapping[str, object],
    *,
    retained: Sequence[object],
    public: Sequence[object],
    hidden: Sequence[object],
    protocol: M055Protocol = M055_PROTOCOL,
) -> Mapping[str, object]:
    """Independent validation in a separate process, including inherited regression."""
    return _node_call("validate", {
        "candidate_body": candidate_body,
        "retained_cases": _case_dicts(retained),
        "public_cases": _case_dicts(public),
        "hidden_cases": _case_dicts(hidden),
    }, protocol)


def _state_digest(state: Mapping[str, object]) -> str:
    """M048's full-state digest, reproducible across processes since D018.

    It was not, when M055 was first written: M048 computed `validation_digest` over a selection
    mapping containing the Node worker pid, so the value drifted between processes and carried
    that drift into the patch registry, the native journal and causal memory. M055 could
    publish only `body_digest` and had to declare the full-state identity unusable.

    That defect was found here, repaired under D018, and the identity is publishable again.
    """
    return _m048._native_state_digest(state)


def body_digest(state: Mapping[str, object]) -> str:
    """The reproducible identity of an accepted body: stable across processes."""
    return _m048._native_body_digest(state["body"])


def adopt(state: Mapping[str, object], candidate_body: Mapping[str, object], verdict: Mapping[str, object]) -> dict[str, object]:
    if not verdict.get("accepted"):
        raise M055Error("an unvalidated candidate cannot be adopted")
    if not verdict.get("inherited_regression_passed"):
        raise M055Error("adoption requires the inherited regression bank to pass")
    return {**state, "version": int(state["version"]) + 1, "body": candidate_body}


def corrupt_state(state: Mapping[str, object]) -> dict[str, object]:
    """Force a post-adoption fault by tampering with the accepted body."""
    modules = [dict(module) for module in state["body"]["modules"]]
    if not modules:
        raise M055Error("an empty body cannot carry a post-adoption fault")
    modules[-1] = {**modules[-1], "source": modules[-1]["source"] + "\n// forced fault\n"}
    return {**state, "body": {**state["body"], "modules": modules}}


def detect_fault(state: Mapping[str, object], expected_digest: str) -> bool:
    return _state_digest(state) != expected_digest


def restore(snapshot: str, expected_digest: str) -> dict[str, object]:
    restored = json.loads(snapshot)
    if _state_digest(restored) != expected_digest:
        raise M055Error("restored state does not match its digest")
    return restored


def snapshot_state(state: Mapping[str, object]) -> str:
    return json.dumps(state, sort_keys=True, separators=(",", ":"))


@dataclass
class M055Manifest:
    mapping: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return dict(self.mapping)

    def digest(self) -> str:
        return _digest(b"m055-native-construction-manifest-v1\0", self.mapping)


def run_m055_native_construction(protocol: M055Protocol = M055_PROTOCOL) -> M055Manifest:
    """One continuing lineage: construct inside the migrated body, keep everything inherited."""
    lineage = reconstruct_m048_version_eight(protocol)
    inherited_digest = _state_digest(lineage.state)

    creation_public, creation_hidden = creation_cases()
    creation = construct_capability(
        lineage.body(), task_id="m055_variation", token="variation",
        tool_name=protocol.creation_tool, arity=3, passes=1,
        public=creation_public, reductions=("sum", "maximum", "minimum"), protocol=protocol,
    )
    if creation.get("status") != "constructed":
        raise M055Error(f"the creation task did not construct a capability: {creation.get('status')}")
    if int(creation["candidates_constructed"]) >= int(creation["admissible_space"]):
        raise M055Error("the construction enumerated its admissible space")
    if int(creation["candidates_constructed"]) >= expression_space_size(2):
        raise M055Error("the construction enumerated the depth-two space")

    creation_verdict = validate_candidate(
        creation["candidate_body"], retained=lineage.retained,
        public=creation_public, hidden=creation_hidden, protocol=protocol,
    )
    if not creation_verdict.get("inherited_regression_passed"):
        raise M055Error("the constructed capability regressed an inherited capability")
    accepted = adopt(lineage.state, creation["candidate_body"], creation_verdict)
    accepted_digest = _state_digest(accepted)
    accepted_snapshot = snapshot_state(accepted)
    if accepted.get("version") != 9:
        raise M055Error("the accepted construction is not version nine")

    # Second-order reuse: the acquired expression becomes an atom for the next construction.
    retained_after_creation = lineage.retained + creation_public + creation_hidden
    reuse_public, reuse_hidden = reuse_cases()
    reuse = construct_capability(
        accepted["body"], task_id="m055_amplified", token="amplified",
        tool_name=protocol.reuse_tool, arity=3, passes=1,
        public=reuse_public, reductions=("sum", "maximum", "minimum"),
        acquired_expression=creation["expression"], protocol=protocol,
    )
    if reuse.get("status") != "constructed":
        raise M055Error(f"the reuse task did not construct a capability: {reuse.get('status')}")
    reuse_uses_acquired = "ACQUIRED" in str(reuse.get("expression_canonical"))
    if not reuse_uses_acquired:
        raise M055Error("the reuse task did not use the acquired expression as material")

    reuse_verdict = validate_candidate(
        reuse["candidate_body"], retained=retained_after_creation,
        public=reuse_public, hidden=reuse_hidden, protocol=protocol,
    )
    if not reuse_verdict.get("inherited_regression_passed"):
        raise M055Error("the reuse construction regressed an inherited capability")

    # Ablation: the same construction denied the acquired expression, same budget, same depth.
    #
    # This arm is recorded, not asserted. It refuted the capability-gain claim, and the
    # experiment reports that rather than being rewritten until the arm agrees. A third reuse
    # task chosen after seeing two ablations would be selecting the task that flatters the
    # hypothesis, which is the failure mode recorded in CHANGELOG 0.33.0.
    ablation = construct_capability(
        accepted["body"], task_id="m055_amplified_ablation", token="amplified",
        tool_name=protocol.reuse_tool, arity=3, passes=1,
        public=reuse_public, reductions=("sum", "maximum", "minimum"),
        acquired_expression=None, protocol=protocol,
    )
    capability_gain = ablation.get("status") != "constructed"
    reuse_constructed = int(reuse["candidates_constructed"])
    ablation_constructed = int(ablation.get("candidates_constructed", 0))
    search_cost_gain = bool(reuse_constructed < ablation_constructed)

    # Refusal: evidence that does not determine the capability must not be committed to.
    refusal_public = (_case("m055_refusal_public_1", "variation 3 3 3", 0, "m055_refusal"),)
    refusal = construct_capability(
        lineage.body(), task_id="m055_refusal", token="variation",
        tool_name=protocol.creation_tool, arity=3, passes=1,
        public=refusal_public, reductions=("sum", "maximum", "minimum"), protocol=protocol,
    )
    if refusal.get("status") == "constructed":
        raise M055Error("ambiguous evidence was committed to instead of refused")

    # Forced post-adoption fault on the accepted version-nine state.
    faulted = corrupt_state(accepted)
    fault_detected = detect_fault(faulted, accepted_digest)
    restored = restore(accepted_snapshot, accepted_digest)
    rollback_exact = (
        fault_detected
        and not detect_fault(accepted, accepted_digest)
        and _state_digest(restored) == accepted_digest
        and snapshot_state(restored) == accepted_snapshot
        and accepted_digest != inherited_digest
    )
    if not rollback_exact:
        raise M055Error("the forced post-adoption fault did not restore the exact state")

    replay = construct_capability(
        lineage.body(), task_id="m055_variation", token="variation",
        tool_name=protocol.creation_tool, arity=3, passes=1,
        public=creation_public, reductions=("sum", "maximum", "minimum"), protocol=protocol,
    )
    replay_identical = replay.get("expression_canonical") == creation.get("expression_canonical")

    mapping = {
        "schema": "m055-native-construction-manifest-v1",
        "status": "negative_on_capability_gain" if not capability_gain else "development_pending_qualification",
        "capability_gain_claim_supported": capability_gain,
        "search_cost_gain_observed": search_cost_gain,
        "protocol_digest": protocol.digest(),
        "inherited_version": lineage.version(),
        "inherited_body_digest": body_digest(lineage.state),
        "inherited_state_digest": inherited_digest,
        "inherited_retained_case_count": len(lineage.retained),
        "source_m047_retained_case_count": lineage.source_retained_count,
        "admissible_space": int(creation["admissible_space"]),
        "construction_budget": protocol.construction_budget,
        "creation_candidates_constructed": int(creation["candidates_constructed"]),
        "creation_expression": creation["expression_canonical"],
        "creation_reduction": creation["reduction"],
        "creation_formation_depth": int(creation["formation_depth"]),
        "creation_changed_modules": list(creation["changed_modules"]),
        "creation_inherited_regression_passed": creation_verdict["inherited_regression_passed"],
        "creation_retained_passed": int(creation_verdict["retained_passed"]),
        "creation_retained_total": int(creation_verdict["retained_total"]),
        "creation_hidden_passed": creation_verdict["hidden_passed"],
        "accepted_version": int(accepted["version"]),
        "accepted_body_digest": body_digest(accepted),
        "accepted_state_digest": accepted_digest,
        "reuse_expression": reuse["expression_canonical"],
        "reuse_uses_acquired_expression": reuse_uses_acquired,
        "reuse_candidates_constructed": int(reuse["candidates_constructed"]),
        "reuse_inherited_regression_passed": reuse_verdict["inherited_regression_passed"],
        "reuse_retained_total": int(reuse_verdict["retained_total"]),
        "reuse_hidden_passed": reuse_verdict["hidden_passed"],
        "ablation_status": ablation.get("status"),
        "ablation_candidates_constructed": ablation_constructed,
        "ablation_expression": ablation.get("expression_canonical"),
        "reuse_candidates_constructed_with_acquisition": reuse_constructed,
        "refusal_status": refusal.get("status"),
        "forced_fault": "accepted_native_body_tampering",
        "fault_detected": fault_detected,
        "rollback_exact": rollback_exact,
        "replay_identical": replay_identical,
        "semantic_delegation_to_python": False,
        "arbitrary_code_generation": False,
        "network_authority": False,
        "repository_authority": False,
        "credential_authority": False,
        "deployment_authority": False,
        "canonical": False,
    }
    return M055Manifest(mapping)


__all__ = [
    "ADMISSIBLE_SPACE", "ATOMS", "M055Error", "M055Manifest", "M055Protocol", "M055_PROTOCOL",
    "OPERATORS", "InheritedLineage", "adopt", "construct_capability", "corrupt_state",
    "creation_cases", "detect_fault", "expression_space_size",
    "reconstruct_m048_version_eight", "restore", "reuse_cases", "run_m055_native_construction",
    "snapshot_state", "validate_candidate",
]
