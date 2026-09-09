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


def _canonical_configuration(value: Any, *, path: str) -> Any:
    """Reduce a bound value to something a digest can cover, or refuse.

    Identity that skips a callable's bound state is not identity. This walks the configuration and
    either produces a canonical form of it or raises, so an artifact descriptor never quietly omits
    a value that changes what the code does.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_canonical_configuration(item, path=path) for item in value]
    if isinstance(value, (set, frozenset)):
        members = [_canonical_configuration(item, path=path) for item in value]
        return {"__set__": sorted(members, key=lambda item: canonical_bytes(item))}
    if isinstance(value, Mapping):
        return {
            str(key): _canonical_configuration(value[key], path=path)
            for key in sorted(value, key=str)
        }
    if callable(value):
        return artifact_digest_of(value)
    raise TrustRootError(
        "the executable configuration at %s holds %r, whose value a digest cannot cover; package "
        "it into an exact artifact rather than letting identity omit it" % (path, type(value))
    )


def _module_source_digest(target: Any) -> str:
    import inspect

    try:
        source_file = inspect.getsourcefile(target)
    except (OSError, TypeError):  # pragma: no cover - built-ins and C callables
        return ""
    if not source_file:
        return ""
    try:
        raw = Path(source_file).read_bytes().replace(b"\r\n", b"\n")
    except OSError:  # pragma: no cover - source removed after import
        return ""
    return hashlib.sha256(raw).hexdigest()


def _symbol_artifact(target: Any) -> dict[str, Any]:
    """A module-level function or class, bound to the source that defines it.

    Anything whose behaviour depends on state a reader cannot reconstruct from the symbol — a
    lambda, a nested function, a closure over live values — is refused here rather than collapsed
    into a name. That collapse is exactly how two different bodies came to share one digest.
    """
    qualname = str(getattr(target, "__qualname__", getattr(target, "__name__", "")))
    if not qualname:
        raise TrustRootError("this callable has no name a digest could bind")
    if "<lambda>" in qualname or "<locals>" in qualname:
        raise TrustRootError(
            "%r is defined inside another scope, so its behaviour depends on values no descriptor "
            "here can reconstruct; package it into an importable artifact before using it where "
            "identity is a trust boundary" % qualname
        )
    if getattr(target, "__closure__", None):
        raise TrustRootError(
            "%r closes over live values, which an importable-symbol identity does not cover" % qualname
        )
    payload = {
        "schema": ARTIFACT_SCHEMA,
        "kind": "importable_symbol",
        "module": str(getattr(target, "__module__", "")),
        "qualname": qualname,
        "module_source_sha256": _module_source_digest(target),
        "binds_exact_executed_bytes": False,
    }
    return {**payload, "artifact_digest": digest_of(payload)}


def artifact_digest_of(factory: Any) -> dict[str, Any]:
    """Identify executable code by what it *is*, not by what it is called.

    `Proposal.digest()` used to hash a name, a provenance record and a rationale, so two different
    bodies with the same metadata were the same proposal and an accepted state's `body_digest` was
    not a digest of any body. Identity has to reach the code that runs.

    The first repair reached the defining module but stopped at the symbol: a `functools.partial`
    was unwrapped to its underlying callable and the bound arguments were thrown away. Two zero-
    argument factories built from the same class with different configuration therefore shared one
    digest, so restore could hand a persisted lineage a differently configured body — and the same
    collision applied to the grader, which is the measure itself. Bound state is behaviour, so it is
    part of identity here:

    * an importable module-level function or class binds its qualified symbol and the digest of the
      module source that defines it;
    * a `functools.partial` binds the recursive identity of its callable *and* its bound arguments
      and keywords, canonicalised;
    * an object that publishes `artifact_configuration()` binds that configuration exactly, which is
      what lets the runtime construct a licensed ablation of it rather than take a caller's word;
    * an object that publishes `exact_artifact_bytes()` binds those bytes and nothing else. This is
      the only kind whose digest covers what actually executes: the bytes *are* the program, so
      there is nothing behind the digest that could drift out from under it. A generated body uses
      this; an importable fixture cannot, because its behaviour lives in a module the digest only
      points at;
    * anything else — a lambda, a closure, a callable whose state cannot be reconstructed — is
      **refused**. Failing closed is the point: a weak symbolic identity that silently covers two
      different executables is worse than no identity, because a record then testifies to a binding
      that does not hold.

    `binds_exact_executed_bytes` distinguishes the third case from the rest, so a reader never has
    to infer which kind of binding a record is claiming.
    """
    import functools

    if hasattr(factory, "exact_artifact_bytes"):
        raw = factory.exact_artifact_bytes()
        if not isinstance(raw, (bytes, bytearray)):
            raise TrustRootError("exact_artifact_bytes() did not return bytes")
        payload = {
            "schema": ARTIFACT_SCHEMA,
            "kind": "exact_bytes",
            "artifact_kind": str(
                factory.artifact_kind() if hasattr(factory, "artifact_kind") else "opaque"
            ),
            "bytes_sha256": hashlib.sha256(bytes(raw)).hexdigest(),
            "byte_length": len(bytes(raw)),
            "binds_exact_executed_bytes": True,
        }
        return {**payload, "artifact_digest": digest_of(payload)}

    if hasattr(factory, "artifact_configuration"):
        configuration = factory.artifact_configuration()
        if not isinstance(configuration, Mapping):
            raise TrustRootError("artifact_configuration() did not return a record")
        payload = {
            "schema": ARTIFACT_SCHEMA,
            "kind": "configured_artifact",
            "configuration": _canonical_configuration(
                dict(configuration), path="configured_artifact"
            ),
            "binds_exact_executed_bytes": False,
        }
        return {**payload, "artifact_digest": digest_of(payload)}

    if isinstance(factory, functools.partial):
        payload = {
            "schema": ARTIFACT_SCHEMA,
            "kind": "partial_application",
            "callable": artifact_digest_of(factory.func),
            "args": _canonical_configuration(list(factory.args), path="partial args"),
            "keywords": _canonical_configuration(
                dict(factory.keywords or {}), path="partial keywords"
            ),
            "binds_exact_executed_bytes": False,
        }
        return {**payload, "artifact_digest": digest_of(payload)}

    if not callable(factory):
        raise TrustRootError("an executable artifact must be callable")
    return _symbol_artifact(factory)


#: What a comparison may require of a control arm. `none` means the measure does not use one;
#: `required` means a control is part of the measure and its identity is admitted with it.
CONTROL_POLICIES = ("none", "required")

#: How a task set is identified. Named in the contract because changing the rule changes what
#: "the same tasks" means, and a verdict has to say which rule it was reached under.
TASK_IDENTITY_RULE = "question_contents_v1"


def evaluation_contract(
    *,
    grade: Any,
    outcome_vocabulary: Sequence[str] = TASK_OUTCOMES,
    retention_policy: str = "parent_solved_must_remain_solved",
    strict_improvement: bool = True,
    control_policy: str = "none",
    control: Any = None,
    task_identity_rule: str = TASK_IDENTITY_RULE,
    admitted_isolation: "Isolation | None" = None,
) -> dict[str, Any]:
    """The measure, as one content-addressed value that every arm of a comparison must name.

    Once task correctness is decided by a grader, the grader *is* part of the measure. A verdict
    bound to the bytes of this file while correctness is decided by an unbound callable is not bound
    to its measure: swap the grader and every verdict still names the same trust-root digest. So the
    grader is admitted as an artifact and the contract digest travels with the verdict.

    The same argument reaches further than the grader, and for a while the contract stopped short of
    it. `decide()` took a separate `required_strict_improvement` flag, so a caller could accept a
    candidate that improved nothing while the verdict named a contract whose recorded policy said
    strict improvement was required. And whether a control arm was part of the comparison at all was
    not in the contract, so two instances carrying the same digest could reach opposite verdicts on
    the same candidate. **Everything the decision rule reads lives here**, and `decide()` reads it
    from here and from nowhere else.
    """
    if control_policy not in CONTROL_POLICIES:
        raise TrustRootError("unrecognised control policy %r" % (control_policy,))
    if control_policy == "required" and control is None:
        raise TrustRootError(
            "a contract that requires a control must admit which control, or the same digest covers "
            "every possible comparison"
        )
    if control_policy == "none" and control is not None:
        raise TrustRootError(
            "a control artifact was admitted under a contract whose policy does not use one"
        )
    payload = {
        "schema": CONTRACT_SCHEMA,
        "grader": artifact_digest_of(grade) if grade is not None else None,
        "outcome_vocabulary": list(outcome_vocabulary),
        "retention_policy": retention_policy,
        "strict_improvement": bool(strict_improvement),
        "control_policy": control_policy,
        "control": artifact_digest_of(control) if control is not None else None,
        "task_identity_rule": str(task_identity_rule),
        "admitted_isolation": admitted_isolation.record() if admitted_isolation else None,
    }
    return {**payload, "contract_digest": digest_of(payload)}


def contract_agrees_on_the_measure(
    admitted: Mapping[str, Any], used: Mapping[str, Any]
) -> list[str]:
    """Which parts of the measure a per-cycle contract changed from the admitted one.

    A cycle may narrow the comparison by admitting a control; it may not change the grader, the
    outcome vocabulary, the retention policy, the strict-improvement requirement or the task
    identity rule. Those are the lineage's measure, and a lineage that could rewrite them per cycle
    would be choosing what counts as better.
    """
    fixed = (
        "grader",
        "outcome_vocabulary",
        "retention_policy",
        "strict_improvement",
        "task_identity_rule",
        "admitted_isolation",
    )
    return [name for name in fixed if admitted.get(name) != used.get(name)]


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
PROVENANCE_SCHEMA = "genesis-provenance-v1"


def provenance(kind: str, *, produced_by: str, detail: str = "") -> dict[str, Any]:
    """Record who produced an artifact. An unclassifiable artifact is refused, not defaulted."""
    if kind not in PROVENANCE_CLASSES:
        raise TrustRootError("unrecognised provenance class %r" % (kind,))
    if not isinstance(produced_by, str) or not produced_by.strip():
        raise TrustRootError("provenance names no producer")
    return {
        "schema": PROVENANCE_SCHEMA,
        "class": kind,
        "produced_by": produced_by,
        "detail": detail,
    }


def validate_provenance(record: Any, *, what: str = "artifact") -> dict[str, Any]:
    """The one place a provenance record is checked, wherever it enters a trusted value.

    The constructor above always required a producer. Every *validation* path checked only that
    `record["class"]` was recognised, so a mapping written by hand — `{"class": "lineage_owned"}` —
    reached a verdict and a lineage state with nobody named as having produced anything. A class
    without a producer is a category, not provenance, and the whole vocabulary exists to say who did
    the work. So the invariant the constructor enforces is enforced here too, and callers validate
    rather than re-checking one field each.
    """
    if not isinstance(record, Mapping):
        raise TrustRootError("%s carries no provenance record" % what)
    kind = record.get("class")
    if kind not in PROVENANCE_CLASSES:
        raise TrustRootError("%s carries no recognised provenance class" % what)
    producer = record.get("produced_by")
    if not isinstance(producer, str) or not producer.strip():
        raise TrustRootError(
            "%s carries provenance of class %r that names no producer" % (what, kind)
        )
    validated = {
        "schema": str(record.get("schema") or PROVENANCE_SCHEMA),
        "class": kind,
        "produced_by": producer,
        "detail": record.get("detail", ""),
    }
    extra = {k: v for k, v in record.items() if k not in validated}
    return {**validated, **extra}


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
    evaluation_contract_record: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Accept or reject a candidate. This is the only place a candidate may become the body.

    Every number in the verdict is recomputed here from raw per-task outcomes. No score, boolean or
    summary produced by the parent, the candidate or any Genesis component is read.

    **The decision rule comes from the admitted contract and from nowhere else.** There used to be a
    `required_strict_improvement` argument beside the contract, so a caller could pass `False` and
    obtain an acceptance whose verdict named a contract recording that strict improvement was
    required — a verdict naming one measure while using another. Whether a control arm is part of
    the comparison is read from the contract for the same reason: without it, two lineages carrying
    one contract digest could reach opposite verdicts on the same candidate.
    """
    isolation.assert_no_wider_than(admitted_isolation)

    provenance_record = validate_provenance(candidate_provenance, what="the candidate")

    contract = dict(evaluation_contract_record or {})
    if contract.get("schema") != CONTRACT_SCHEMA:
        raise TrustRootError("no admitted evaluation contract: there is no measure to decide under")
    if contract.get("contract_digest") != digest_of(
        {k: v for k, v in contract.items() if k != "contract_digest"}
    ):
        raise TrustRootError("the evaluation contract does not reproduce its own digest")
    required_strict_improvement = bool(contract.get("strict_improvement"))
    control_policy = contract.get("control_policy", "none")
    if control_policy not in CONTROL_POLICIES:
        raise TrustRootError("the evaluation contract names an unrecognised control policy")
    if control_policy == "required" and control_outcomes is None:
        raise TrustRootError(
            "the admitted contract makes a control part of the measure and no control arm ran"
        )
    if control_policy == "none" and control_outcomes is not None:
        raise TrustRootError(
            "a control arm was supplied under a contract whose measure does not use one; admit a "
            "contract that names the control rather than changing the comparison beneath the digest"
        )

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
        "lost_solved_tasks": lost_solved,
        "evaluation_contract_digest": contract["contract_digest"],
        "decision_rule": {
            "strict_improvement": required_strict_improvement,
            "retention_policy": contract.get("retention_policy"),
            "control_policy": control_policy,
            "read_from_the_admitted_contract": True,
        },
        "candidate_provenance": provenance_record,
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
