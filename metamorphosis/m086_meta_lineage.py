"""The M086 lineage: one cycle, four arms, and a mechanism that may or may not be allowed to change.

Everything is matched across arms — identity, starting body, public evidence, budget, primitives and
evaluator. The single difference is whether the lineage may rewrite the artifact that turns evidence
into candidates.

The evaluator, the sandbox, the task bank and the mechanism interpreter are outside the mutable body.
Success on the holdout is decided by executing hidden cases the mechanism never sees.
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Mapping, Sequence

from metamorphosis.m047_runtime_sandbox import (
    SoftwareSandboxError,
    SoftwareSandboxJob,
    run_bodies_in_sandbox,
    run_body_in_sandbox,
)
from metamorphosis.m047_software_body import (
    SoftwareBody,
    SoftwareBodyError,
    SoftwareCase,
    SourceModule,
    render_allocation,
    render_critique,
    render_execution,
    render_interpretation,
    render_orchestration,
    render_planning,
    render_selection,
    render_tool_core,
)
from metamorphosis.m086_evolvable_mechanism import (
    ARMS,
    Hypothesis,
    Mechanism,
    MechanismError,
    build_mechanism,
    candidate_meta_transformations,
    diagnose,
    generate,
    m0_mechanism,
)

SANDBOX_TIMEOUT = 60.0
CYCLES_PER_PHASE = 2
TASK_ONLY_MUTABLE_CYCLE_MULTIPLIER = 3
MAX_CANDIDATES = 64


class LineageError(RuntimeError):
    """Raised when an arm or phase contract is violated."""


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


# --------------------------------------------------------------------------------------------
# The starting body and the two limitations
# --------------------------------------------------------------------------------------------

def starting_body() -> SoftwareBody:
    """A body that parses four operations but can execute only two.

    Built from M047's own renderers. `mean` and `max` parse and then find no route; anything outside
    the alias table does not parse at all. That is what lets one task fail at two different stages at
    once, which is the evidence M047's mechanism cannot speak about.
    """

    modules = (
        SourceModule("allocation", render_allocation("fixed_four")),
        SourceModule("critique", render_critique("identity")),
        SourceModule("execution", render_execution()),
        SourceModule("interpretation", render_interpretation(
            {"add": "add", "max": "max", "mean": "mean", "mul": "mul"},
        )),
        SourceModule("orchestration", render_orchestration()),
        SourceModule("planning", render_planning("root_only")),
        SourceModule("selection", render_selection({"add": "add", "mul": "mul"})),
        SourceModule("tool_core", render_tool_core()),
    )
    return SoftwareBody(tuple(sorted(modules, key=lambda item: item.name)))


# Each limitation pairs an unparseable token with an unroutable operation, so the evidence names two
# stages at once and M047's mechanism cannot speak. The token's canonical operation deliberately
# already has a route: an earlier bank aliased tokens onto routeless operations, which made repairing
# the alias *reveal* a new missing route, and the greedy tie-break then locked in a wrong alias that
# no later cycle could diagnose. That cascade is a property of the bank, not of the hypothesis under
# test, and it was removed before anything was bound.
DEVELOPMENT_PUBLIC = (
    SoftwareCase("dev_unknown_token", "plus 4 5", 9, "development"),
    SoftwareCase("dev_missing_route", "mean 1 2 3", 2.0, "development"),
)

# The routeless operation is `mean` in both limitations and never `max`. M047's `render_tool_module`
# emits `def max(arguments): ... return max(arguments)` for a tool named `max`, which shadows the
# builtin the expression depends on and recurses until the sandbox kills it. That is a latent defect
# in a qualified module, recorded in FAILURE_LOG rather than repaired here: changing that renderer
# would change M047's synthesized source bytes and therefore its preserved digests.
HOLDOUT_PUBLIC = (
    SoftwareCase("holdout_unknown_token", "times 3 4", 12, "holdout"),
    SoftwareCase("holdout_missing_route", "mean 2 4 9", 5.0, "holdout"),
)

# Evaluator-owned. The mechanism never receives these, and a structural checker verifies that no
# path exists from here into the meta-search.
HOLDOUT_HIDDEN = (
    SoftwareCase("hidden_times_a", "times 6 7", 42, "holdout_hidden"),
    SoftwareCase("hidden_times_b", "times -2 5", -10, "holdout_hidden"),
    SoftwareCase("hidden_mean_a", "mean 3 3 9", 5.0, "holdout_hidden"),
    SoftwareCase("hidden_mean_b", "mean 1 1 1", 1.0, "holdout_hidden"),
)


def bank_commitment() -> str:
    return hashlib.sha256(_canonical({
        "starting_body": starting_body().digest(),
        "development_public": [case.to_dict() for case in DEVELOPMENT_PUBLIC],
        "holdout_public": [case.to_dict() for case in HOLDOUT_PUBLIC],
        "holdout_hidden": [case.to_dict() for case in HOLDOUT_HIDDEN],
    })).hexdigest()


# --------------------------------------------------------------------------------------------
# One improvement cycle
# --------------------------------------------------------------------------------------------

@dataclass
class CycleOutcome:
    diagnosed: bool
    hypothesis: dict[str, object]
    candidates_generated: int
    adopted_label: str | None
    body: SoftwareBody
    public_passed: int
    public_total: int


def run_cycle(
    mechanism: Mechanism, body: SoftwareBody, public: Sequence[SoftwareCase],
) -> CycleOutcome:
    """Observe, diagnose through the mechanism, generate through the mechanism, adopt what passes."""

    incumbent = run_body_in_sandbox(body, public, timeout_seconds=SANDBOX_TIMEOUT)
    if not incumbent.disposable_process:
        raise LineageError("diagnostic execution was not disposable")
    hypothesis = diagnose(mechanism, incumbent.cases)
    if not hypothesis.sufficient:
        return CycleOutcome(
            False, hypothesis.to_dict(), 0, None, body,
            incumbent.passed_cases, len(public),
        )

    candidates = generate(mechanism, body, hypothesis)[:MAX_CANDIDATES]
    prepared: list[tuple[str, SoftwareBody]] = []
    for label, replacements in candidates:
        if not replacements:
            continue
        try:
            prepared.append((label, body.replace_modules(replacements)))
        except (SoftwareBodyError, MechanismError):
            continue
    if not prepared:
        return CycleOutcome(
            True, hypothesis.to_dict(), len(candidates), None, body,
            incumbent.passed_cases, len(public),
        )

    jobs = tuple(
        SoftwareSandboxJob(f"candidate_{index}", candidate, tuple(public))
        for index, (_, candidate) in enumerate(prepared)
    )
    try:
        results = run_bodies_in_sandbox(jobs, timeout_seconds=SANDBOX_TIMEOUT)
    except SoftwareSandboxError:
        results = {}

    best: tuple[int, str, SoftwareBody] | None = None
    for index, (label, candidate) in enumerate(prepared):
        outcome = results.get(f"candidate_{index}")
        if outcome is None or not outcome.disposable_process:
            continue
        passed = outcome.passed_cases
        if best is None or passed > best[0]:
            best = (passed, label, candidate)

    if best is None or best[0] <= incumbent.passed_cases:
        return CycleOutcome(
            True, hypothesis.to_dict(), len(candidates), None, body,
            incumbent.passed_cases, len(public),
        )
    return CycleOutcome(
        True, hypothesis.to_dict(), len(candidates), best[1], best[2],
        best[0], len(public),
    )


def solves(body: SoftwareBody, cases: Sequence[SoftwareCase]) -> bool:
    """Evaluator-owned success: executed behaviour on cases the mechanism never saw."""

    outcome = run_body_in_sandbox(body, cases, timeout_seconds=SANDBOX_TIMEOUT)
    return outcome.disposable_process and outcome.all_cases_passed


def pursue_phase(
    mechanism: Mechanism, body: SoftwareBody, public: Sequence[SoftwareCase], cycles: int,
) -> tuple[SoftwareBody, list[CycleOutcome]]:
    outcomes: list[CycleOutcome] = []
    current = body
    for _ in range(cycles):
        outcome = run_cycle(mechanism, current, public)
        outcomes.append(outcome)
        current = outcome.body
        if outcome.public_passed == outcome.public_total:
            break
        if outcome.adopted_label is None:
            break
    return current, outcomes


# --------------------------------------------------------------------------------------------
# The meta-search: the lineage changing what changes it
# --------------------------------------------------------------------------------------------

@dataclass
class MetaTrial:
    primitives: tuple[str, ...]
    mechanism_digest: str
    diagnosed: bool
    candidates_generated: int
    development_solved: bool
    accepted: bool


def meta_search(
    base: Mechanism, body: SoftwareBody, public: Sequence[SoftwareCase],
) -> tuple[Mechanism | None, list[MetaTrial]]:
    """Try each bounded meta-transformation on a disposable descendant; keep what validates.

    Nothing here knows which combination works. The order is singles before pairs, alphabetical
    within a size, and every trial is run against the development limitation in a disposable sandbox.
    The first that solves it is adopted and the rest are recorded as rejected.
    """

    trials: list[MetaTrial] = []
    adopted: Mechanism | None = None
    for primitives in candidate_meta_transformations():
        candidate_mechanism = build_mechanism(base, primitives)
        descendant_body = copy.deepcopy(body)
        descendant, outcomes = pursue_phase(
            candidate_mechanism, descendant_body, public, CYCLES_PER_PHASE,
        )
        solved = solves(descendant, public)
        trials.append(MetaTrial(
            primitives=tuple(primitives),
            mechanism_digest=candidate_mechanism.digest(),
            diagnosed=any(outcome.diagnosed for outcome in outcomes),
            candidates_generated=sum(outcome.candidates_generated for outcome in outcomes),
            development_solved=solved,
            accepted=solved and adopted is None,
        ))
        if solved and adopted is None:
            adopted = candidate_mechanism
    return adopted, trials


# --------------------------------------------------------------------------------------------
# Arms
# --------------------------------------------------------------------------------------------

@dataclass
class ArmResult:
    arm: str
    mechanism_start_digest: str
    mechanism_after_development_digest: str
    mechanism_at_holdout_digest: str
    meta_transformations_adopted: int
    adopted_primitives: tuple[str, ...]
    rejected_primitives: tuple[tuple[str, ...], ...]
    development_solved: bool
    holdout_public_solved: bool
    holdout_hidden_solved: bool
    holdout_adopted_label: str | None
    holdout_candidates_generated: int
    cycles_used: int
    journal: list[dict[str, object]] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "arm": self.arm,
            "mechanism_start_digest": self.mechanism_start_digest,
            "mechanism_after_development_digest": self.mechanism_after_development_digest,
            "mechanism_at_holdout_digest": self.mechanism_at_holdout_digest,
            "meta_transformations_adopted": self.meta_transformations_adopted,
            "adopted_primitives": list(self.adopted_primitives),
            "rejected_primitives": [list(item) for item in self.rejected_primitives],
            "development_solved": self.development_solved,
            "holdout_public_solved": self.holdout_public_solved,
            "holdout_hidden_solved": self.holdout_hidden_solved,
            "holdout_adopted_label": self.holdout_adopted_label,
            "holdout_candidates_generated": self.holdout_candidates_generated,
            "cycles_used": self.cycles_used,
            "journal": self.journal,
        }


def run_arm(arm: str) -> ArmResult:
    if arm not in ARMS:
        raise LineageError(f"unknown arm {arm!r}")

    mechanism = m0_mechanism()
    start_digest = mechanism.digest()
    body = starting_body()
    journal: list[dict[str, object]] = []
    adopted_primitives: tuple[str, ...] = ()
    rejected: tuple[tuple[str, ...], ...] = ()
    meta_adopted = 0

    # -- development phase ------------------------------------------------------------------
    developed, dev_outcomes = pursue_phase(mechanism, body, DEVELOPMENT_PUBLIC, CYCLES_PER_PHASE)
    dev_solved = solves(developed, DEVELOPMENT_PUBLIC)
    journal.append({
        "step": "development_attempt_with_starting_mechanism",
        "diagnosed": any(outcome.diagnosed for outcome in dev_outcomes),
        "hypothesis": dev_outcomes[0].hypothesis if dev_outcomes else None,
        "candidates_generated": sum(o.candidates_generated for o in dev_outcomes),
        "solved": dev_solved,
    })

    if arm == "evolvable_meta" or arm == "meta_acquisition_ablated":
        if not dev_solved:
            candidate, trials = meta_search(mechanism, body, DEVELOPMENT_PUBLIC)
            rejected = tuple(
                trial.primitives for trial in trials if not trial.development_solved
            )
            journal.append({
                "step": "meta_search",
                "limitation": "the starting mechanism produced no hypothesis for two-stage evidence",
                "trials": [
                    {
                        "primitives": list(trial.primitives),
                        "mechanism": trial.mechanism_digest,
                        "diagnosed": trial.diagnosed,
                        "candidates_generated": trial.candidates_generated,
                        "development_solved": trial.development_solved,
                        "accepted": trial.accepted,
                    }
                    for trial in trials
                ],
            })
            if candidate is not None:
                mechanism = candidate
                adopted_primitives = candidate.provenance
                meta_adopted = 1
                journal.append({
                    "step": "meta_transformation_adopted",
                    "primitives": list(candidate.provenance),
                    "mechanism_before": start_digest,
                    "mechanism_after": candidate.digest(),
                })
                developed, _ = pursue_phase(
                    mechanism, body, DEVELOPMENT_PUBLIC, CYCLES_PER_PHASE,
                )
                dev_solved = solves(developed, DEVELOPMENT_PUBLIC)

    after_development = mechanism.digest()

    if arm == "meta_acquisition_ablated":
        # The lineage continues; only what it acquired about its own mechanism is removed.
        mechanism = m0_mechanism()
        journal.append({
            "step": "meta_acquisition_stripped_before_holdout",
            "mechanism_restored_to": mechanism.digest(),
        })

    # -- holdout phase ----------------------------------------------------------------------
    cycles = CYCLES_PER_PHASE
    if arm == "task_only_mutable":
        cycles = CYCLES_PER_PHASE * TASK_ONLY_MUTABLE_CYCLE_MULTIPLIER

    holdout_body, holdout_outcomes = pursue_phase(
        mechanism, starting_body(), HOLDOUT_PUBLIC, cycles,
    )
    public_solved = solves(holdout_body, HOLDOUT_PUBLIC)
    hidden_solved = public_solved and solves(holdout_body, HOLDOUT_HIDDEN)
    adopted_label = next(
        (o.adopted_label for o in reversed(holdout_outcomes) if o.adopted_label), None,
    )
    journal.append({
        "step": "holdout",
        "mechanism": mechanism.digest(),
        "diagnosed": any(o.diagnosed for o in holdout_outcomes),
        "candidates_generated": sum(o.candidates_generated for o in holdout_outcomes),
        "adopted_label": adopted_label,
        "public_solved": public_solved,
        "hidden_solved": hidden_solved,
    })

    return ArmResult(
        arm=arm,
        mechanism_start_digest=start_digest,
        mechanism_after_development_digest=after_development,
        mechanism_at_holdout_digest=mechanism.digest(),
        meta_transformations_adopted=meta_adopted,
        adopted_primitives=adopted_primitives,
        rejected_primitives=rejected,
        development_solved=dev_solved,
        holdout_public_solved=public_solved,
        holdout_hidden_solved=hidden_solved,
        holdout_adopted_label=adopted_label,
        holdout_candidates_generated=sum(o.candidates_generated for o in holdout_outcomes),
        cycles_used=len(holdout_outcomes),
        journal=journal,
    )


def enumerate_m0_image_on_holdout() -> dict[str, object]:
    """The proof that the control's failure is structural rather than budgetary.

    Enumerates every candidate the starting mechanism can emit for the holdout evidence. If that set
    is empty, no budget can help: there is nothing to run.
    """

    body = starting_body()
    incumbent = run_body_in_sandbox(body, HOLDOUT_PUBLIC, timeout_seconds=SANDBOX_TIMEOUT)
    mechanism = m0_mechanism()
    hypothesis = diagnose(mechanism, incumbent.cases)
    candidates = generate(mechanism, body, hypothesis)
    return {
        "hypothesis": hypothesis.to_dict(),
        "diagnosed": hypothesis.sufficient,
        "candidate_count": len(candidates),
        "candidate_labels": [label for label, _ in candidates],
        "contains_a_passing_candidate": False if not candidates else None,
    }


@dataclass(frozen=True)
class Verdict:
    positive: bool
    reasons: tuple[str, ...] = ()


def evaluate(arms: Mapping[str, Mapping[str, object]], image: Mapping[str, object]) -> Verdict:
    reasons: list[str] = []
    evolvable = arms["evolvable_meta"]

    if evolvable["meta_transformations_adopted"] != 1:
        reasons.append(
            f"P1: evolvable_meta adopted {evolvable['meta_transformations_adopted']} mechanism "
            "modifications rather than exactly one"
        )
    if not evolvable["rejected_primitives"]:
        reasons.append("P1: no rejected alternative was recorded, so the search was not a search")
    if not evolvable["holdout_hidden_solved"]:
        reasons.append("P2: evolvable_meta did not solve the holdout on the evaluator's hidden cases")
    if arms["fixed_meta"]["holdout_hidden_solved"]:
        reasons.append("P3: fixed_meta solved the holdout, which refutes the capability claim")
    if image["candidate_count"] != 0:
        reasons.append(
            f"P3: the starting mechanism can emit {image['candidate_count']} candidates for the "
            "holdout, so its failure is not structural"
        )
    if arms["meta_acquisition_ablated"]["holdout_hidden_solved"]:
        reasons.append("P4: meta_acquisition_ablated solved the holdout, so the acquisition leaked")
    if arms["task_only_mutable"]["holdout_hidden_solved"]:
        reasons.append("P5: task_only_mutable solved the holdout, so ordinary patching suffices")
    if not evolvable["holdout_adopted_label"]:
        reasons.append("P6: evolvable_meta adopted no holdout patch")
    elif str(evolvable["holdout_adopted_label"]) in set(image["candidate_labels"]):
        reasons.append(
            "P6: the adopted holdout patch is inside the starting mechanism's constructive image, "
            "so the acquisition was not needed to produce it"
        )
    if evolvable["mechanism_start_digest"] == evolvable["mechanism_after_development_digest"]:
        reasons.append("P6: the mechanism did not change, so nothing was acquired")

    return Verdict(positive=not reasons, reasons=tuple(reasons))
