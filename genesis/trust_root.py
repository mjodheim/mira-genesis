"""The immutable trust root of the Genesis runtime.

Genesis may evolve. This module may not, and Genesis must never be able to become better by
modifying the measure that decides it is better. That sentence is the whole purpose of this file,
and everything in it exists to make the sentence mechanically true rather than merely intended.

Four things live here and nowhere else:

* **isolation** — the declared limits a candidate runs under;
* **budget** — what a lineage may spend, and the refusal when it is spent;
* **provenance** — who produced each artifact, recorded so a later reader can tell
  lineage-owned work from host-written and model-mediated work;
* **the final accept/reject** — the only place a candidate becomes the new body.

Three structural rules keep it honest, each one a lesson already paid for elsewhere in this
repository:

1. **This module imports nothing from mutable Genesis.** Data flows one way. There is no import
   through which an evolving component could reach in here, and the test suite asserts it.
2. **The verdict is re-derived, never read.** `decide()` recomputes the comparison from raw
   per-task outcomes. It never consults a score, a boolean or a summary produced by the thing being
   judged. M120 established the difference: authenticating a file is not the same as knowing what is
   in it, and a checker that recomputes a number *from the record the runner wrote* has verified
   nothing.

   **This rule reaches exactly as far as the rows do, and no further.** For a long time the sentence
   above was written as though it settled the matter, while the per-task rows themselves came out of
   the candidate's own process: `attempt` returned the outcome, so the thing being judged awarded
   its own marks and everything here was arithmetic on its claim. `sandbox.run_candidate` now takes
   a host-side `grade`, under which a body returns an *answer* and the parent decides whether it is
   right. `decide()` cannot tell the difference — the rows look the same either way — so every
   sandbox result and every cycle record carries `outcomes_are_self_reported`, and a reader weighing
   a verdict has to look at it. A tally recomputed from self-reported rows is honest arithmetic over
   an unverified claim, which is a weaker thing than it looks.
3. **The root verifies its own bytes before deciding.** A decision carries the digest of this
   source file. A Genesis that rewrote its evaluator cannot have the resulting verdict accepted,
   because the verdict names bytes that no longer match.

Nothing here is a scientific claim. This is apparatus.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

TRUST_ROOT_SCHEMA = "genesis-trust-root-v1"
ARTIFACT_SCHEMA = "genesis-executable-artifact-v1"
CONTRACT_SCHEMA = "genesis-evaluation-contract-v1"
VERDICT_SCHEMA = "genesis-verdict-v1"
BUDGET_SCHEMA = "genesis-budget-v1"
ISOLATION_SCHEMA = "genesis-isolation-v1"

#: Provenance classes. The distinction M070/M071 forced on this project: a transformation a model
#: produced is not a transformation the lineage owns, and the record must say which.
PROVENANCE_CLASSES = ("lineage_owned", "host_written", "model_mediated", "external")

#: Outcomes a task may have. `refused` is a first-class outcome, not a failure: a lineage that
#: declines an action it cannot justify is behaving correctly, and M074/M078 make refusal a measured
#: quantity rather than an absence.
TASK_OUTCOMES = ("solved", "unsolved", "refused", "error")


class TrustRootError(RuntimeError):
    """Raised when something tries to decide more than the evidence supports."""


class BudgetExhausted(TrustRootError):
    """Raised when a lineage asks to spend past its declared allowance."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest_of(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def source_digest() -> str:
    """SHA-256 of this file's own LF-normalised bytes.

    Recomputed at decision time rather than cached, so a rewritten evaluator produces a different
    digest and its verdicts stop matching the manifest a lineage was admitted under.
    """
    raw = Path(__file__).resolve().read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(raw).hexdigest()


def _artifact_value(value: Any) -> Any:
    """Canonical, non-executable representation of bound callable configuration.

    Artifact identity must include the configuration that changes behaviour. `functools.partial`
    used to be unwrapped to its underlying symbol, so two bodies or graders with different bound
    values had the same identity. The current fixtures need only ordinary data; unsupported opaque
    objects fail closed rather than silently disappearing from identity.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, bytes):
        return {"type": "bytes", "hex": value.hex()}
    if isinstance(value, (list, tuple)):
        return {"type": type(value).__name__, "items": [_artifact_value(item) for item in value]}
    if isinstance(value, (set, frozenset)):
        items = [_artifact_value(item) for item in value]
        return {
            "type": type(value).__name__,
            "items": sorted(items, key=lambda item: canonical_bytes(item)),
        }
    if isinstance(value, Mapping):
        items = [
            [_artifact_value(key), _artifact_value(item)] for key, item in value.items()
        ]
        items.sort(key=lambda pair: canonical_bytes(pair[0]))
        return {"type": "mapping", "items": items}
    if isinstance(value, Path):
        return {"type": "path", "value": str(value)}
    raise TrustRootError(
        "executable artifact has opaque bound configuration of type %s; package it into a "
        "reconstructible artifact before using it as trusted identity" % type(value).__name__
    )


def artifact_digest_of(factory: Any) -> dict[str, Any]:
    """Identify executable code by what it *is*, including behaviour-changing bound values.

    Plain importable symbols bind their qualified name and defining module source. A partial binds
    that symbol recursively plus canonical bound arguments and keyword arguments. This is still a
    weaker identity than exact executed bytes, which the record states explicitly, but it no longer
    treats two differently configured callables as the same executable artifact.
    """
    import functools
    import inspect

    if isinstance(factory, functools.partial):
        payload = {
            "schema": ARTIFACT_SCHEMA,
            "kind": "partial",
            "callable": artifact_digest_of(factory.func),
            "args": [_artifact_value(value) for value in factory.args],
            "keywords": {
                str(key): _artifact_value(value)
                for key, value in sorted((factory.keywords or {}).items())
            },
            "binds_exact_executed_bytes": False,
        }
        return {**payload, "artifact_digest": digest_of(payload)}

    target = factory
    source_digest_of_module = ""
    try:
        source_file = inspect.getsourcefile(target)
        if source_file:
            raw = Path(source_file).read_bytes().replace(b"\r\n", b"\n")
            source_digest_of_module = hashlib.sha256(raw).hexdigest()
    except (OSError, TypeError):  # pragma: no cover - built-ins and C callables
        source_digest_of_module = ""
    payload = {
        "schema": ARTIFACT_SCHEMA,
        "kind": "importable_symbol",
        "module": str(getattr(target, "__module__", "")),
        "qualname": str(getattr(target, "__qualname__", getattr(target, "__name__", ""))),
        "module_source_sha256": source_digest_of_module,
        "binds_exact_executed_bytes": False,
    }
    return {**payload, "artifact_digest": digest_of(payload)}


def evaluation_contract(
    *,
    grade: Any,
    outcome_vocabulary: Sequence[str] = TASK_OUTCOMES,
    retention_policy: str = "parent_solved_must_remain_solved",
    strict_improvement: bool = True,
    control_policy: str = "none",
    control_artifact: Any | None = None,
) -> dict[str, Any]:
    """The measure, as one content-addressed value that every arm of a comparison must name.

    Once task correctness is decided by a grader, the grader *is* part of the measure. The same is
    true of whether a control arm is part of the comparison. These choices are content-addressed so
    two opposite decision procedures cannot travel under one contract digest.
    """
    if control_policy not in ("none", "equal_budget_control"):
        raise TrustRootError("unrecognised control policy %r" % control_policy)
    if control_policy == "none" and control_artifact is not None:
        raise TrustRootError("a control artifact was supplied under a no-control policy")
    if control_policy != "none" and control_artifact is None:
        raise TrustRootError("the control policy requires an identified control artifact")
    payload = {
        "schema": CONTRACT_SCHEMA,
        "grader": artifact_digest_of(grade) if grade is not None else None,
        "outcome_vocabulary": list(outcome_vocabulary),
        "retention_policy": retention_policy,
        "strict_improvement": bool(strict_improvement),
        "control_policy": control_policy,
        "control_artifact": artifact_digest_of(control_artifact)
        if control_artifact is not None
        else None,
    }
    return {**payload, "contract_digest": digest_of(payload)}


# ---------------------------------------------------------------------------------------------
# Isolation
# ---------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Isolation:
    """The limits a candidate runs under. Declared by the host, never by the lineage."""

    cpu_seconds: float = 30.0
    memory_bytes: int = 512 * 1024 * 1024
    wall_clock_seconds: float = 60.0
    filesystem_writes_permitted: bool = False
    network_permitted: bool = False
    subprocess_permitted: bool = False

    def record(self) -> dict[str, Any]:
        return {
            "schema": ISOLATION_SCHEMA,
            "cpu_seconds": self.cpu_seconds,
            "memory_bytes": self.memory_bytes,
            "wall_clock_seconds": self.wall_clock_seconds,
            "filesystem_writes_permitted": self.filesystem_writes_permitted,
            "network_permitted": self.network_permitted,
            "subprocess_permitted": self.subprocess_permitted,
        }

    def assert_no_wider_than(self, other: "Isolation") -> None:
        """A candidate may never run under looser limits than the lineage was admitted under."""
        if (
            self.cpu_seconds > other.cpu_seconds
            or self.memory_bytes > other.memory_bytes
            or self.wall_clock_seconds > other.wall_clock_seconds
            or (self.filesystem_writes_permitted and not other.filesystem_writes_permitted)
            or (self.network_permitted and not other.network_permitted)
            or (self.subprocess_permitted and not other.subprocess_permitted)
        ):
            raise TrustRootError("candidate isolation is wider than the admitted envelope")


# ---------------------------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------------------------
@dataclass
class Budget:
    """A spend ledger the lineage cannot widen.

    Every dimension is declared up front. `spend` refuses past the limit rather than warning, so a
    loop that would exceed its allowance stops instead of finishing and reporting that it overran.
    """

    limits: Mapping[str, int]
    spent: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.limits = {str(k): int(v) for k, v in dict(self.limits).items()}
        for name, value in self.limits.items():
            if value < 0:
                raise TrustRootError("budget dimension %r is negative" % name)
        self.spent = {name: int(self.spent.get(name, 0)) for name in self.limits}
        for name, value in self.spent.items():
            if value < 0 or value > self.limits[name]:
                raise TrustRootError(
                    "budget dimension %r has invalid spent value %d for limit %d"
                    % (name, value, self.limits[name])
                )

    def remaining(self, dimension: str) -> int:
        if dimension not in self.limits:
            raise TrustRootError("undeclared budget dimension %r" % dimension)
        return self.limits[dimension] - self.spent[dimension]

    def spend(self, dimension: str, amount: int = 1) -> int:
        if amount < 0:
            raise TrustRootError("cannot spend a negative amount")
        if self.remaining(dimension) < amount:
            raise BudgetExhausted(
                "budget %r exhausted: %d remaining, %d requested"
                % (dimension, self.remaining(dimension), amount)
            )
        self.spent[dimension] += amount
        return self.remaining(dimension)

    def record(self) -> dict[str, Any]:
        return {
            "schema": BUDGET_SCHEMA,
            "limits": dict(sorted(self.limits.items())),
            "spent": dict(sorted(self.spent.items())),
            "remaining": {name: self.remaining(name) for name in sorted(self.limits)},
        }


# ---------------------------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------------------------
def validate_provenance(record: Mapping[str, Any], *, what: str = "artifact") -> dict[str, Any]:
    """Require both a recognised class and a real producer everywhere provenance is trusted."""
    if not isinstance(record, Mapping):
        raise TrustRootError("%s carries no provenance record" % what)
    kind = record.get("class")
    if kind not in PROVENANCE_CLASSES:
        raise TrustRootError("%s carries no recognised provenance" % what)
    produced_by = record.get("produced_by")
    if not isinstance(produced_by, str) or not produced_by.strip():
        raise TrustRootError("%s provenance names no producer" % what)
    detail = record.get("detail", "")
    return {"class": kind, "produced_by": produced_by, "detail": str(detail)}


def provenance(kind: str, *, produced_by: str, detail: str = "") -> dict[str, Any]:
    """Record who produced an artifact. An unclassifiable artifact is refused, not defaulted."""
    return validate_provenance(
        {"class": kind, "produced_by": produced_by, "detail": detail}, what="artifact"
    )


# ---------------------------------------------------------------------------------------------
# The decision
# ---------------------------------------------------------------------------------------------
def _tally(outcomes: Sequence[Mapping[str, Any]], label: str) -> dict[str, Any]:
    """Recompute an arm's tally from its raw per-task outcomes.

    Deliberately ignores any aggregate the arm reported. If an arm hands us a summary, we do not
    read it; we count the rows ourselves.

    Counting rows correctly says nothing about where the rows came from. Whether they were graded by
    the host or reported by the candidate is recorded upstream, in the sandbox result, and this
    function neither knows nor could tell.
    """
    counts = {name: 0 for name in TASK_OUTCOMES}
    seen: set[str] = set()
    for row in outcomes:
        if not isinstance(row, Mapping):
            raise TrustRootError("%s outcome row is not a record" % label)
        task = row.get("task_id")
        if not isinstance(task, str) or not task:
            raise TrustRootError("%s outcome row carries no task id" % label)
        if task in seen:
            raise TrustRootError("%s reports task %r twice" % (label, task))
        seen.add(task)
        result = row.get("outcome")
        if result not in TASK_OUTCOMES:
            raise TrustRootError("%s task %r has an unrecognised outcome" % (label, task))
        counts[result] += 1
    return {
        "counts": counts,
        "tasks": sorted(seen),
        "total": len(seen),
        "solved": sorted(
            str(row.get("task_id")) for row in outcomes if row.get("outcome") == "solved"
        ),
    }


def decide(
    *,
    parent_outcomes: Sequence[Mapping[str, Any]],
    candidate_outcomes: Sequence[Mapping[str, Any]],
    control_outcomes: Sequence[Mapping[str, Any]] | None = None,
    budget: Budget,
    isolation: Isolation,
    admitted_isolation: Isolation,
    candidate_provenance: Mapping[str, Any],
    required_strict_improvement: bool = True,
    evaluation_contract_record: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Accept or reject a candidate. This is the only place a candidate may become the body.

    Every number in the verdict is recomputed here from raw per-task outcomes. No score, boolean or
    summary produced by the parent, the candidate or any Genesis component is read.
    """
    isolation.assert_no_wider_than(admitted_isolation)
    validated_provenance = validate_provenance(candidate_provenance, what="candidate")

    strict_improvement = bool(required_strict_improvement)
    if evaluation_contract_record is not None:
        contract = dict(evaluation_contract_record)
        expected_contract_digest = digest_of(
            {k: v for k, v in contract.items() if k != "contract_digest"}
        )
        if contract.get("schema") != CONTRACT_SCHEMA or contract.get(
            "contract_digest"
        ) != expected_contract_digest:
            raise TrustRootError("evaluation contract does not reproduce")
        strict_improvement = bool(contract.get("strict_improvement", True))
        control_policy = contract.get("control_policy", "none")
        if control_policy == "none" and control_outcomes is not None:
            raise TrustRootError("a control arm was supplied outside the admitted evaluation contract")
        if control_policy == "equal_budget_control" and control_outcomes is None:
            raise TrustRootError("the admitted evaluation contract requires a control arm")

    parent = _tally(parent_outcomes, "parent")
    candidate = _tally(candidate_outcomes, "candidate")
    control = _tally(control_outcomes, "control") if control_outcomes is not None else None

    if parent["tasks"] != candidate["tasks"]:
        raise TrustRootError("parent and candidate did not face the same tasks")
    if control is not None and control["tasks"] != parent["tasks"]:
        raise TrustRootError("control did not face the same tasks")

    parent_solved = parent["counts"]["solved"]
    candidate_solved = candidate["counts"]["solved"]
    improved = candidate_solved > parent_solved
    regressed = candidate["counts"]["error"] > parent["counts"]["error"]

    # Retention is set inclusion, not a larger scalar. Comparing counts let a candidate forget work
    # the parent could do, gain more elsewhere, and be adopted for the trade — which is a lineage
    # that improved its score while losing what it had. Under the metamorphosis objective the
    # acquired must be *kept*, so the tasks the parent solved have to remain solved.
    lost_solved = sorted(set(parent["solved"]) - set(candidate["solved"]))

    reasons: list[str] = []
    if lost_solved:
        reasons.append(
            "the candidate forgot work the parent could do: %s" % ", ".join(lost_solved)
        )
    if strict_improvement and not improved:
        reasons.append(
            "no strict improvement: parent solved %d, candidate solved %d"
            % (parent_solved, candidate_solved)
        )
    if regressed:
        reasons.append(
            "candidate errors rose from %d to %d"
            % (parent["counts"]["error"], candidate["counts"]["error"])
        )
    if control is not None and candidate_solved <= control["counts"]["solved"]:
        reasons.append(
            "candidate did not beat the equal-budget control: %d against %d"
            % (candidate_solved, control["counts"]["solved"])
        )

    accepted = not reasons
    verdict = {
        "schema": VERDICT_SCHEMA,
        "accepted": accepted,
        "rejection_reasons": reasons,
        "parent": parent,
        "candidate": candidate,
        "control": control,
        "improved": improved,
        "lost_solved_tasks": lost_solved,
        "evaluation_contract_digest": (
            dict(evaluation_contract_record)["contract_digest"]
            if evaluation_contract_record
            else ""
        ),
        "candidate_provenance": validated_provenance,
        "budget": budget.record(),
        "isolation": isolation.record(),
        "admitted_isolation": admitted_isolation.record(),
        "trust_root_source_sha256": source_digest(),
        "recomputed_from_raw_outcomes": True,
        "read_any_self_reported_score": False,
    }
    verdict["verdict_digest"] = digest_of({k: v for k, v in verdict.items()})
    return verdict


def verify_verdict(verdict: Mapping[str, Any], *, admitted_source_sha256: str) -> list[str]:
    """Check a verdict was produced by the trust root a lineage was admitted under."""
    problems: list[str] = []
    if verdict.get("schema") != VERDICT_SCHEMA:
        problems.append("verdict uses an unrecognised schema")
    recorded = verdict.get("trust_root_source_sha256")
    if recorded != admitted_source_sha256:
        problems.append(
            "verdict was produced by a different trust root: admitted %s, verdict %s"
            % (admitted_source_sha256, recorded)
        )
    if recorded != source_digest():
        problems.append("the trust root on disk no longer matches the verdict's own record")
    expected = digest_of({k: v for k, v in verdict.items() if k != "verdict_digest"})
    if verdict.get("verdict_digest") != expected:
        problems.append("verdict digest does not reproduce")
    return problems
