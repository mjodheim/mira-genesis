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
def provenance(kind: str, *, produced_by: str, detail: str = "") -> dict[str, Any]:
    """Record who produced an artifact. An unclassifiable artifact is refused, not defaulted."""
    if kind not in PROVENANCE_CLASSES:
        raise TrustRootError("unrecognised provenance class %r" % (kind,))
    if not isinstance(produced_by, str) or not produced_by.strip():
        raise TrustRootError("provenance names no producer")
    return {"class": kind, "produced_by": produced_by, "detail": detail}


# ---------------------------------------------------------------------------------------------
# The decision
# ---------------------------------------------------------------------------------------------
def _tally(outcomes: Sequence[Mapping[str, Any]], label: str) -> dict[str, Any]:
    """Recompute an arm's tally from its raw per-task outcomes.

    Deliberately ignores any aggregate the arm reported. If an arm hands us a summary, we do not
    read it; we count the rows ourselves.
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
    return {"counts": counts, "tasks": sorted(seen), "total": len(seen)}


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
) -> dict[str, Any]:
    """Accept or reject a candidate. This is the only place a candidate may become the body.

    Every number in the verdict is recomputed here from raw per-task outcomes. No score, boolean or
    summary produced by the parent, the candidate or any Genesis component is read.
    """
    isolation.assert_no_wider_than(admitted_isolation)

    if candidate_provenance.get("class") not in PROVENANCE_CLASSES:
        raise TrustRootError("candidate carries no recognised provenance")

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

    reasons: list[str] = []
    if required_strict_improvement and not improved:
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
        "candidate_provenance": dict(candidate_provenance),
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
