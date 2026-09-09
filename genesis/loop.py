"""The continuous evolution loop.

    observe -> diagnose -> hypothesize -> construct candidates -> isolate -> test
           -> compare -> adopt/reject -> persist -> continue

Two properties of this loop are the reason it exists, and both are things the M107–M111 experiments
demonstrated once each and then stopped.

**A rejected candidate does not end the run.** It becomes an observation the lineage holds, and the
loop continues within its budget. Every experiment in this line terminated at its verdict; a program
that stops at its first rejection is not evolving, it is being tested. (A *scientific* negative stays
frozen under the repository's rules — that is a different thing from the program learning that a
candidate does not work.)

**Causal dependency between generations is checked every time, not once per milestone.** "Version 1
better, version 2 better" is not the claim. A proposal may carry an ablation arm — itself with the
earlier acquisition it depends on removed and nothing else changed — and `cycle` runs that arm at the
same budget and requires a loss in work the current generation newly solved over its parent.
Losing only retained work is not evidence that the new work needed the earlier acquisition.
`causal_chain` then counts the consecutive acquisitions whose dependency was actually established, so a
claim about recursive improvement reads a number that can be small.

This sentence was true of the docstring and false of the code for a while: the function existed, the
docstring called it a permanent obligation of the runtime, and the only thing calling it was a
demonstration script. An acceptance with no arm is now recorded as `established: false` with the
reason, never as an unexamined pass, and an arm that cannot run aborts the cycle rather than being
scored as a candidate failure.

The loop never decides anything. It gathers raw outcomes and hands them to the trust root, which
recomputes the comparison and returns the verdict.

**Who grades.** Recomputing a tally from rows the candidate wrote is arithmetic on a claim rather
than a measurement of it. Pass `grade` to `Genesis` and a body's return value becomes an answer the
parent judges against the real task. Leaving it out is allowed and has to be *said* —
`allow_self_reported_outcomes=True` — because a label on the difference is not a refusal of it, and
nobody should reach a self-reported verdict by forgetting an argument. Every cycle record still
carries `outcomes_are_self_reported`, since the flag is what a later reader weighs.
"""
from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping, Protocol, Sequence

from genesis import state as lineage_state
from genesis.journal import Journal
from genesis.sandbox import run_candidate
from genesis.trust_root import (
    Budget,
    artifact_digest_of,
    canonical_bytes,
    evaluation_contract,
    BudgetExhausted,
    Isolation,
    TrustRootError,
    digest_of,
    verify_verdict,
)

CYCLE_SCHEMA = "genesis-cycle-v1"
CAMPAIGN_SCHEMA = "genesis-campaign-v1"
CONTEXT_SCHEMA = "genesis-lineage-context-v1"
CHECKPOINT_SCHEMA = "genesis-runtime-checkpoint-v1"

#: The manifest a directory currently commits, and the one it committed before that. Two files
#: rather than one, because a checkpoint that overwrites its predecessor leaves nothing to fall back
#: to when the newest one turns out not to be resumable.
CHECKPOINT_NAME = "runtime_checkpoint.json"
PREVIOUS_CHECKPOINT_NAME = "runtime_checkpoint.previous.json"


def question_digest(task: Mapping[str, Any]) -> str:
    """Identify one task by its question, ignoring the label it happens to carry."""
    return digest_of({k: v for k, v in dict(task).items() if k != "task_id"})


def evaluation_snapshot(tasks: Sequence[Mapping[str, Any]]) -> tuple[Mapping[str, Any], ...]:
    """The one question set every arm of a comparison is judged on, taken once and unwritable.

    `cycle` used to pass the caller's own mappings to the parent arm, then hand those same mappings
    to the proposer, then judge the candidate, the control and the ablation on them again. A proposer
    could therefore rewrite what the questions *were* after the parent had been graded, keeping every
    `task_id` intact — and the trust root, which requires both arms to have faced the same tasks,
    compares by identifier and sees a match. Two arms answering different questions under one set of
    labels is the exact failure the task-identity rule exists to prevent, reached from inside the
    cycle rather than from the caller.

    So the snapshot is deep-copied away from the caller and wrapped read-only. Nothing downstream can
    write through it, and the caller's list is left as it was.
    """
    return tuple(MappingProxyType(deepcopy(dict(task))) for task in tasks)


def detached_tasks(tasks: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """A copy for code that may look at the questions but must not be able to change them."""
    return [deepcopy(dict(task)) for task in tasks]


def task_set_digest(tasks: Sequence[Mapping[str, Any]]) -> str:
    """Identify a task set by the questions in it, not by the labels on them.

    This hashed `task_id` values, which are labels: a caller could reuse the identifiers of a set the
    lineage had been judged on, put easier contents underneath, and present the result as previously
    evaluated work. Duplicates are kept — two identical questions asked twice are not the same body
    of work as one — and the target is included, because changing what counts as right changes what
    the lineage was judged on.
    """
    return digest_of(sorted(question_digest(task) for task in tasks))


@dataclass(frozen=True)
class LineageContext:
    """What a lineage-owned proposer may see: a value, not the runtime.

    `cycle` used to call `propose(self, tasks)`. That handed lineage-owned code the body, the budget,
    the isolation envelope, the state, the journal, the admitted trust-root digest and the grader —
    everything the measure is made of. No downstream guard can repair that, because the authority was
    already given away: a proposer could widen its own budget, swap the evaluator between the parent
    arm and the candidate arm, or replace the body with no adoption at all. That is precisely the
    invariant this runtime exists to hold, so the interface is now data.

    Frozen, so an attempt to write through it raises rather than silently failing, and the cycle
    records the attempt instead of letting it pass unremarked.
    """

    schema: str
    state_digest: str
    generation: int
    components: tuple[str, ...]
    vocabulary: tuple[str, ...]
    acquisitions: tuple[str, ...]
    observations: int
    budget_remaining: Mapping[str, int]
    evaluated_task_sets: tuple[str, ...]
    body_artifact_digest: str


class Body(Protocol):
    """The minimum a body must offer. Anything richer is the lineage's business, not the loop's.

    What `attempt` returns depends on who grades. With a grader it is an **answer** the parent
    judges; without one it is the body's own verdict on itself, which is a much weaker thing and is
    marked as such in every record it reaches.
    """

    def attempt(self, task: Mapping[str, Any]) -> Any:  # pragma: no cover - protocol
        ...


@dataclass
class Proposal:
    """A candidate transformation, with the provenance that says who really produced it.

    `depends_on` names the earlier acquisition this generation claims to have needed. The cycle
    **constructs** the counterfactual itself, from the candidate's own configuration, and runs that;
    it does not accept an arm from the proposer.

    `ablated_body_factory` survives only as a record that a proposer offered one. It is never run
    and never read as evidence: an arm the proposal chose is the proposal's own account of what the
    counterfactual is, and for a while the runtime measured a loss against exactly that.
    """

    name: str
    body_factory: Callable[[], Body]
    provenance: Mapping[str, Any]
    rationale: Mapping[str, Any]
    ablated_body_factory: Callable[[], Body] | None = None
    depends_on: str = ""

    def body_artifact(self) -> dict[str, Any]:
        """What this proposal would actually run, identified by its code."""
        return artifact_digest_of(self.body_factory)

    def digest(self) -> str:
        """Identity that reaches the executable, not just the paperwork around it.

        This hashed the name, the provenance and the rationale, so two different bodies submitted
        with the same metadata were the same proposal, and the `body_digest` an acceptance wrote
        into the lineage state was a digest of a description rather than of a body.
        """
        return digest_of(
            {
                "name": self.name,
                "provenance": dict(self.provenance),
                "rationale": dict(self.rationale),
                "body_artifact": self.body_artifact(),
            }
        )


class Genesis:
    """A lineage that observes, diagnoses, proposes, tests, adopts or rejects, and continues."""

    def __init__(
        self,
        *,
        state: Mapping[str, Any],
        body_factory: Callable[[], Body],
        budget: Budget,
        isolation: Isolation,
        journal: Journal | None = None,
        admitted_isolation: Isolation | None = None,
        admitted_source_sha256: str | None = None,
        grade: Callable[[Mapping[str, Any], Any], str] | None = None,
        allow_self_reported_outcomes: bool = False,
    ) -> None:
        from genesis.trust_root import source_digest

        # Hati's second blocking correction: labelling the difference is not refusing it. A lineage
        # whose verdicts rest on the candidate's own account of itself is a legitimate thing to run
        # — it is what the fixtures did for most of this runtime's life — but it has to be asked
        # for, so that nobody arrives at a self-reported verdict by forgetting an argument.
        if grade is None and not allow_self_reported_outcomes:
            raise TrustRootError(
                "no grader was supplied, so every verdict would rest on the candidate's own "
                "account of itself; pass grade=..., or allow_self_reported_outcomes=True to say "
                "that is what you meant"
            )

        self.state = lineage_state.decode_state(state)
        self.body_factory = body_factory
        self.budget = budget
        self.isolation = isolation
        # The envelope a lineage was admitted under and the limits it is actually running under are
        # two things. They coincide on a first admission, and they need not on a resumption: a
        # lineage that ran narrower than its ceiling should come back narrower, not at the widest
        # limits it was ever allowed. Supplying one wider than the admitted envelope is refused here
        # rather than downstream, where the widening would already have happened.
        self.admitted_isolation = admitted_isolation or isolation
        isolation.assert_no_wider_than(self.admitted_isolation)
        self.admitted_source_sha256 = admitted_source_sha256 or source_digest()
        # Host-supplied and host-side. Without it a body's return value *is* its outcome, so the
        # thing being judged awards its own marks and everything downstream rests on that; with it
        # the body supplies an answer and the parent decides. The cycle records which happened
        # rather than leaving a reader to assume the stronger one.
        self.grade = grade
        # The grader is part of the measure, so it is admitted as an artifact and every verdict
        # names the contract digest alongside the trust-root source digest. So is the rest of the
        # decision rule: strict improvement, retention, whether a control is part of the comparison,
        # and the rule by which a task set is identified. `decide()` reads all of it from here, so a
        # verdict cannot name one measure and use another.
        self.evaluation_contract = evaluation_contract(
            grade=grade, admitted_isolation=self.admitted_isolation
        )
        self.allow_self_reported_outcomes = allow_self_reported_outcomes
        # Which task sets this lineage has actually been evaluated on. A migration verified against
        # tasks nobody ever judged this lineage by is verified against a set chosen by whoever
        # wanted the migration to pass.
        self.evaluated_task_digests: set[str] = set()
        self.journal = journal if journal is not None else Journal()
        if not len(self.journal):
            self.journal.append(
                "seed",
                self.state["generation"],
                {
                    "state_digest": self.state["state_digest"],
                    "components": lineage_state.component_names(self.state),
                    "vocabulary": lineage_state.vocabulary_names(self.state),
                    "admitted_trust_root_sha256": self.admitted_source_sha256,
                },
            )

    # -- one cycle ------------------------------------------------------------------------
    def cycle(
        self,
        tasks: Sequence[Mapping[str, Any]],
        propose: Callable[["Genesis", Sequence[Mapping[str, Any]]], Proposal | None],
        *,
        control_factory: Callable[[], Body] | None = None,
        required_strict_improvement: bool | None = None,
    ) -> dict[str, Any]:
        """Run one observe→…→continue cycle. Returns the cycle record; never raises on rejection.

        `required_strict_improvement` is kept only so that a caller asking for a decision rule the
        admitted contract does not license is *refused* rather than silently obeyed. It used to be
        passed straight through to the trust root, so a cycle could accept a candidate that improved
        nothing while its verdict named a contract recording that strict improvement was required.

        A `control_factory` narrows the comparison, and narrowing it changes the measure — so the
        cycle admits a contract that names the control and its identity, and the verdict carries
        that digest. Two lineages whose comparisons differ can no longer share one contract digest.
        """
        generation = self.state["generation"]

        if required_strict_improvement is not None and bool(
            required_strict_improvement
        ) != bool(self.evaluation_contract["strict_improvement"]):
            entry = self.journal.append(
                "decision_rule_refused",
                generation,
                {
                    "asked_for_strict_improvement": bool(required_strict_improvement),
                    "admitted_contract_requires": bool(
                        self.evaluation_contract["strict_improvement"]
                    ),
                    "contract_digest": self.evaluation_contract["contract_digest"],
                },
            )
            return {
                "schema": CYCLE_SCHEMA,
                "generation": generation,
                "stopped": False,
                "accepted": False,
                "reason": "this cycle asked to decide under a rule the admitted contract does not "
                "license: strict improvement is %s in the contract and was asked to be %s"
                % (
                    self.evaluation_contract["strict_improvement"],
                    bool(required_strict_improvement),
                ),
                "journal_entry": entry["entry_digest"],
            }

        try:
            self.budget.spend("generations")
        except BudgetExhausted as exhausted:
            record = self.journal.append(
                "budget_exhausted", generation, {"detail": str(exhausted)}
            )
            return {
                "schema": CYCLE_SCHEMA,
                "generation": generation,
                "stopped": True,
                "reason": str(exhausted),
                "journal_entry": record["entry_digest"],
            }

        def abort(arm: str, run: Mapping[str, Any]) -> dict[str, Any]:
            """A sandbox that never ran produced no evidence about any body.

            Scoring a candidate on rows the instrument invented for it would let an infrastructure
            failure masquerade as a scientific one. The cycle aborts instead, and the abort is
            recorded so the history shows the run did not happen rather than showing it failed.
            """
            record = self.journal.append(
                "instrument_abort",
                generation,
                {"arm": arm, "reason": run.get("reason", ""), "sandbox_digest": run["result_digest"]},
            )
            return {
                "schema": CYCLE_SCHEMA,
                "generation": generation,
                "stopped": True,
                "instrument_abort": True,
                "accepted": False,
                "reason": "%s arm did not run: %s" % (arm, run.get("reason", "")),
                "journal_entry": record["entry_digest"],
            }

        # Taken once, before any arm runs, and used by every one of them. Everything below judges
        # this snapshot; nothing below judges the caller's list.
        questions = evaluation_snapshot(tasks)

        parent = run_candidate(
            self.body_factory,
            questions,
            self.isolation,
            admitted_isolation=self.admitted_isolation,
            grade=self.grade,
        )
        if not parent["completed"]:
            return abort("parent", parent)
        # Recorded only now. It used to be added before the parent ran, so an instrument abort left
        # a task set marked as work the lineage had been evaluated on when no evaluation happened —
        # and the migration gate reads that ledger.
        self.evaluated_task_digests.add(task_set_digest(questions))
        self.journal.append(
            "observation",
            generation,
            {"arm": "parent", "sandbox_digest": parent["result_digest"]},
        )

        try:
            # A detached copy. The proposer is entitled to look at the questions — diagnosing what
            # the lineage cannot do is the point — and entitled to nothing else about them. What it
            # writes here reaches no arm and no ledger.
            proposal = propose(self.context(), detached_tasks(questions))
        except Exception as failure:
            # A proposer that reaches for the runtime now raises, because the context is frozen.
            # Its attempt is an observation about the lineage, not a crash of the host.
            entry = self.journal.append(
                "diagnosis",
                generation,
                {"proposed": False, "detail": "the proposer failed: %s" % failure},
            )
            return {
                "schema": CYCLE_SCHEMA,
                "generation": generation,
                "stopped": False,
                "accepted": False,
                "reason": "the proposer failed: %s" % failure,
                "journal_entry": entry["entry_digest"],
            }
        if proposal is None:
            entry = self.journal.append(
                "diagnosis", generation, {"proposed": False, "detail": "no candidate proposed"}
            )
            return {
                "schema": CYCLE_SCHEMA,
                "generation": generation,
                "stopped": False,
                "accepted": False,
                "reason": "no candidate proposed",
                "journal_entry": entry["entry_digest"],
            }

        self.journal.append(
            "candidate_proposed",
            generation,
            {
                "name": proposal.name,
                "proposal_digest": proposal.digest(),
                "provenance": dict(proposal.provenance),
            },
        )

        candidate = run_candidate(
            proposal.body_factory,
            questions,
            self.isolation,
            admitted_isolation=self.admitted_isolation,
            grade=self.grade,
        )
        if not candidate["completed"]:
            return abort("candidate", candidate)
        control = (
            run_candidate(
                control_factory,
                questions,
                self.isolation,
                admitted_isolation=self.admitted_isolation,
                grade=self.grade,
            )
            if control_factory is not None
            else None
        )
        if control is not None and not control["completed"]:
            return abort("control", control)

        from genesis.trust_root import contract_agrees_on_the_measure, decide

        # The contract this cycle decides under. Without a control it is the admitted one; with a
        # control it is the admitted measure plus the control's identity, admitted here so the
        # verdict names the comparison it actually made.
        contract = self.evaluation_contract
        if control_factory is not None:
            contract = evaluation_contract(
                grade=self.grade,
                admitted_isolation=self.admitted_isolation,
                control_policy="required",
                control=control_factory,
            )
            changed = contract_agrees_on_the_measure(self.evaluation_contract, contract)
            if changed:
                raise TrustRootError(
                    "a per-cycle contract may narrow the comparison, not rewrite the measure: %s"
                    % ", ".join(changed)
                )

        verdict = decide(
            parent_outcomes=parent["outcomes"],
            candidate_outcomes=candidate["outcomes"],
            control_outcomes=control["outcomes"] if control else None,
            budget=self.budget,
            isolation=self.isolation,
            admitted_isolation=self.admitted_isolation,
            candidate_provenance=proposal.provenance,
            evaluation_contract_record=contract,
        )
        problems = verify_verdict(verdict, admitted_source_sha256=self.admitted_source_sha256)
        if problems:
            raise TrustRootError("; ".join(problems))

        causal = self._causal_dependency(proposal, questions, parent, candidate)
        if causal.get("instrument_abort"):
            return abort("ablation", causal["run"])

        if verdict["accepted"]:
            self.body_factory = proposal.body_factory
            self.state = lineage_state.create_state(
                body_digest=proposal.digest(),
                components=self.state["components"],
                vocabulary=self.state["vocabulary"],
                tools=self.state["tools"],
                acquisitions=self.state["acquisitions"]
                + [
                    {
                        "name": proposal.name,
                        "generation": generation,
                        "verdict_digest": verdict["verdict_digest"],
                        "provenance": dict(proposal.provenance),
                        "causal_dependency": causal["record"],
                    }
                ],
                observations=self.state["observations"],
                generation=generation + 1,
            )
            entry = self.journal.append(
                "candidate_accepted",
                generation,
                {
                    "name": proposal.name,
                    "verdict_digest": verdict["verdict_digest"],
                    "new_state_digest": self.state["state_digest"],
                    "causal_dependency_established": causal["record"]["established"],
                },
            )
        else:
            # The rejection is kept. It is an observation the lineage holds, not the end of the run.
            self.state = lineage_state.create_state(
                body_digest=self.state["body_digest"],
                components=self.state["components"],
                vocabulary=self.state["vocabulary"],
                tools=self.state["tools"],
                acquisitions=self.state["acquisitions"],
                observations=self.state["observations"]
                + [
                    {
                        "kind": "rejected_candidate",
                        "name": proposal.name,
                        "generation": generation,
                        "reasons": list(verdict["rejection_reasons"]),
                        "verdict_digest": verdict["verdict_digest"],
                    }
                ],
                generation=generation,
            )
            entry = self.journal.append(
                "candidate_rejected",
                generation,
                {
                    "name": proposal.name,
                    "reasons": list(verdict["rejection_reasons"]),
                    "verdict_digest": verdict["verdict_digest"],
                    "loop_continues": True,
                },
            )

        return {
            "schema": CYCLE_SCHEMA,
            "generation": generation,
            "stopped": False,
            "accepted": verdict["accepted"],
            "reason": "; ".join(verdict["rejection_reasons"]),
            "verdict": verdict,
            "parent_sandbox": parent,
            "candidate_sandbox": candidate,
            "control_sandbox": control,
            "outcomes_are_self_reported": candidate["outcomes_are_self_reported"],
            "causal_dependency": causal["record"],
            "journal_entry": entry["entry_digest"],
            "state_digest": self.state["state_digest"],
        }

    def context(self) -> LineageContext:
        """The read-only value a lineage-owned proposer receives in place of this object."""
        return LineageContext(
            schema=CONTEXT_SCHEMA,
            state_digest=self.state["state_digest"],
            generation=self.state["generation"],
            components=tuple(lineage_state.component_names(self.state)),
            vocabulary=tuple(lineage_state.vocabulary_names(self.state)),
            acquisitions=tuple(
                str(item.get("name", "")) for item in self.state["acquisitions"]
            ),
            observations=len(self.state["observations"]),
            budget_remaining=MappingProxyType(
                {name: self.budget.remaining(name) for name in sorted(self.budget.limits)}
            ),
            evaluated_task_sets=tuple(sorted(self.evaluated_task_digests)),
            body_artifact_digest=artifact_digest_of(self.body_factory)["artifact_digest"],
        )

    # -- causal dependency, on every cycle rather than once per milestone ------------------
    def _causal_dependency(self, proposal, tasks, parent, candidate) -> dict[str, Any]:
        """Construct this candidate minus the acquisition it names, run it, and judge what it shows.

        This lives in the cycle rather than in whatever script happens to be driving it. It was in a
        script for a while, and the loop's own docstring described the check as a permanent
        obligation of the runtime the whole time — which is a record testifying to a property the
        code did not have.

        **The arm is built here, not accepted from the proposer.** The previous version ran whatever
        `ablated_body_factory` the proposal carried, having checked only that `depends_on` named an
        acquisition the lineage really held. A deliberately weak unrelated body, labelled with a real
        acquisition's name, therefore produced a measured loss and was recorded as causal
        dependency — the proposer writing its own evidence. Now the runtime derives the arm from the
        candidate's own configuration, verifies that the two differ in exactly the licensed removal,
        and records `established: false` whenever it cannot. A counterfactual nobody could construct
        is not a counterfactual that passed.

        A lineage with no acquisitions yet has nothing to have depended on, so the absence of an arm
        is not a failure there. Once it has one, an acceptance with no established arm is recorded as
        `established: false` with the reason, never as an unexamined pass.
        """
        from genesis.artifacts import ArtifactError, derive_ablation, single_difference

        first_acquisition = not self.state["acquisitions"]
        held = {str(item.get("name", "")) for item in self.state["acquisitions"]}
        # Kept in the record so a reader can see the proposer offered an arm and that it was not
        # read. Deleting the field would hide the refusal rather than make it.
        offered = proposal.ablated_body_factory is not None

        def unestablished(why: str, **extra) -> dict[str, Any]:
            return {
                "record": {
                    "established": False,
                    "arm_run": False,
                    "caller_supplied_arm_offered": offered,
                    "caller_supplied_arm_used_as_evidence": False,
                    "depends_on": proposal.depends_on,
                    "why": why,
                    **extra,
                }
            }

        if not proposal.depends_on:
            return unestablished(
                "the lineage's first acquisition depends on nothing earlier"
                if first_acquisition
                else "the proposal named no earlier acquisition, so nothing shows this generation "
                "needed the one before it"
            )
        if proposal.depends_on not in held:
            return unestablished(
                "the proposal names %r, which this lineage never acquired, so no arm can be that "
                "acquisition removed" % proposal.depends_on
            )

        try:
            arm = derive_ablation(proposal.body_factory, proposal.depends_on)
        except ArtifactError as refusal:
            return unestablished(
                "the runtime could not construct this candidate without %r: %s"
                % (proposal.depends_on, refusal)
            )
        differences = single_difference(proposal.body_factory, arm, proposal.depends_on)
        if differences:
            return unestablished(
                "the derived arm is not a single-difference counterfactual: %s"
                % "; ".join(differences)
            )

        run = run_candidate(
            arm,
            tasks,
            self.isolation,
            admitted_isolation=self.admitted_isolation,
            grade=self.grade,
        )
        if not run["completed"]:
            return {"instrument_abort": True, "run": run, "record": {"established": False}}

        outcome = ablation_supports_causal_dependency(
            parent_outcomes=parent["outcomes"],
            with_acquisition=candidate["outcomes"],
            without_acquisition=run["outcomes"],
            equal_budget=True,
        )
        # An ablated arm indistinguishable from the parent is the parent, and comparing a candidate
        # with its parent is the verdict this cycle just reached, not evidence on top of it.
        distinct = run["result_digest"] != parent["result_digest"]
        established = bool(outcome["supported"] and distinct)
        return {
            "record": {
                "established": established,
                "arm_run": True,
                "arm_derived_by_the_runtime": True,
                "caller_supplied_arm_offered": offered,
                "caller_supplied_arm_used_as_evidence": False,
                "depends_on": proposal.depends_on,
                "candidate_artifact_digest": artifact_digest_of(proposal.body_factory)[
                    "artifact_digest"
                ],
                "ablated_artifact_digest": artifact_digest_of(arm)["artifact_digest"],
                "solved_with_acquisition": outcome["solved_with_acquisition"],
                "solved_without_acquisition": outcome["solved_without_acquisition"],
                "newly_solved_with_acquisition": outcome["newly_solved_with_acquisition"],
                "newly_solved_lost_without_acquisition": outcome[
                    "newly_solved_lost_without_acquisition"
                ],
                "retained_solved_lost_without_acquisition": outcome[
                    "retained_solved_lost_without_acquisition"
                ],
                "ablated_arm_differs_from_the_parent_arm": distinct,
                "ablated_sandbox_digest": run["result_digest"],
                "why": ""
                if established
                else outcome["reason"]
                or "the ablated arm is behaviourally identical to the parent arm, so removing the "
                "acquisition cost nothing the verdict had not already measured",
            }
        }

    def causal_chain(self) -> dict[str, Any]:
        """How far back the lineage's improvements actually depend on each other.

        A run of acceptances is not a chain. This counts the consecutive acquisitions, ending at the
        most recent, whose dependency on the one before was established by ablation — so a claim
        about recursive improvement has to read a number that can be small.

        It reports the number and nothing else. Converting it into a verdict was the previous
        version's mistake: `length >= 2` became "a chain rather than a sequence", which is a
        threshold set at the minimum that permits the word. Whether n links is recursion is not a
        question the thing being measured gets to settle.
        """
        acquisitions = list(self.state["acquisitions"])
        length = 0
        for acquisition in reversed(acquisitions):
            if not (acquisition.get("causal_dependency") or {}).get("established"):
                break
            length += 1
        return {
            "acquisitions": len(acquisitions),
            "established_links": length,
            # There is deliberately no boolean here. One existed, and it turned `length >= 2` into
            # "this is a chain rather than a sequence" — two being the smallest number that lets the
            # word be used at all. Hati's fifth blocking correction is that the threshold was doing
            # the work the evidence was supposed to do. The number is reported; what it is worth is
            # a judgement the runtime is not entitled to make on its own behalf.
            "makes_no_recursion_claim": True,
        }

    # -- architecture changes, owned by the runtime rather than by whatever drives it -------
    def adopt_component(
        self, certificate: Mapping[str, Any], *, provenance: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Install a component class the lineage's own evidence licensed, and journal it.

        The demonstration script used to assign `genesis.state` and append the journal entry itself,
        which made the architectural transition a property of the script rather than of the runtime.
        """
        self.state = lineage_state.extend_components(
            self.state, certificate=certificate, provenance=provenance
        )
        entry = self.journal.append(
            "component_acquired",
            self.state["generation"],
            {
                "component": certificate["new_component"],
                "certificate_digest": certificate["certificate_digest"],
                "operations": list(
                    (certificate.get("resolving_composition") or {}).get("operations") or []
                ),
                "new_state_digest": self.state["state_digest"],
            },
        )
        return entry

    def adopt_vocabulary(
        self, certificate: Mapping[str, Any], *, provenance: Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        """Install a diagnostic feature the lineage measured a need for, and journal it."""
        self.state = lineage_state.extend_vocabulary(
            self.state, certificate=certificate, provenance=provenance
        )
        entry = self.journal.append(
            "vocabulary_extended",
            self.state["generation"],
            {
                "feature": certificate["new_feature"],
                "certificate_digest": certificate["certificate_digest"],
                "new_state_digest": self.state["state_digest"],
            },
        )
        return entry

    # -- many cycles ----------------------------------------------------------------------
    def evolve(
        self,
        task_families: Sequence[Sequence[Mapping[str, Any]]],
        propose: Callable[["Genesis", Sequence[Mapping[str, Any]]], Proposal | None],
        *,
        control_factory: Callable[[], Body] | None = None,
    ) -> dict[str, Any]:
        """Run cycles until the families are exhausted or the budget refuses. Rejections continue."""
        cycles = []
        for tasks in task_families:
            record = self.cycle(tasks, propose, control_factory=control_factory)
            cycles.append(record)
            if record.get("stopped"):
                break
        campaign = {
            "schema": CAMPAIGN_SCHEMA,
            "cycles": cycles,
            "accepted": sum(1 for record in cycles if record.get("accepted")),
            "rejected": sum(
                1
                for record in cycles
                if not record.get("accepted") and not record.get("stopped")
            ),
            "final_generation": self.state["generation"],
            "final_state_digest": self.state["state_digest"],
            "journal_head": self.journal.head,
            "budget": self.budget.record(),
        }
        campaign["campaign_digest"] = digest_of(campaign)
        return campaign

    # -- persistence ----------------------------------------------------------------------
    def _state_filename(self) -> str:
        return "lineage_state.%s.json" % self.state["state_digest"][:16]

    def _journal_filename(self) -> str:
        return "descent_journal.%s.json" % self.journal.head[:16]

    def checkpoint(self) -> dict[str, Any]:
        """Everything that decides which lineage resumes and under which rules, as one value.

        State and journal are each authenticated, and that was never enough: nothing bound them to
        each other, to the budget already spent, to the isolation envelope, to the evaluator, or to
        the body. A restart could therefore present the persisted state under a fresh allowance and a
        caller-chosen body and call the result the same lineage.

        The manifest also names the files its payloads live in. They used to be two fixed names, so
        publishing a new checkpoint overwrote the only copy of the payloads the previous manifest
        pointed at — which made a crash mid-write fail closed, and made the lineage before it
        unrecoverable. Content-addressed names mean a new checkpoint never lands on an old one's
        payloads.
        """
        payload = {
            "schema": CHECKPOINT_SCHEMA,
            "generation": self.state["generation"],
            "state_digest": self.state["state_digest"],
            "journal_head": self.journal.head,
            "state_path": self._state_filename(),
            "journal_path": self._journal_filename(),
            "body_artifact": artifact_digest_of(self.body_factory),
            "admitted_trust_root_sha256": self.admitted_source_sha256,
            "evaluation_contract": dict(self.evaluation_contract),
            "admitted_isolation": self.admitted_isolation.record(),
            "isolation": self.isolation.record(),
            "budget": self.budget.record(),
            "evaluated_task_sets": sorted(self.evaluated_task_digests),
            "allow_self_reported_outcomes": self.allow_self_reported_outcomes,
        }
        return {**payload, "checkpoint_digest": digest_of(payload)}

    def persist(self, directory: Path) -> dict[str, str]:
        """Write the payloads under names nothing else claims, then publish the manifest last.

        Commit-last ordering means a crash between the two leaves the previous manifest as the last
        committed lineage: half-written files are not history. That was true and it was not enough.
        The payloads went to two fixed filenames, so the new state and journal landed **on top of**
        the ones the previous manifest named: after a crash the surviving manifest pointed at files
        that had already been replaced, and its digest checks would refuse them. Fail-closed, which
        is right, but the lineage before this one was gone.

        Payload files are now content-addressed, so a new checkpoint cannot overwrite an old one's,
        and the manifest being replaced is kept beside the new one. The previous committed lineage
        stays loadable rather than merely being refused.
        """
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        written = {
            "state": lineage_state.save_state(self.state, directory / self._state_filename()),
            "journal": self.journal.save(directory / self._journal_filename()),
        }
        manifest = self.checkpoint()
        path = directory / CHECKPOINT_NAME
        if path.exists():
            # Retained before the new manifest is published, so the lineage it names — whose
            # payloads are still on disk under their own digests — can be resumed.
            superseded = directory / PREVIOUS_CHECKPOINT_NAME
            temporary = superseded.with_suffix(".partial")
            temporary.write_bytes(path.read_bytes())
            temporary.replace(superseded)
            written["superseded"] = superseded.name
        temporary = path.with_suffix(".partial")
        temporary.write_bytes(canonical_bytes(manifest) + b"\n")
        temporary.replace(path)
        written["checkpoint"] = manifest["checkpoint_digest"]
        return written

    @staticmethod
    def restore(
        directory: Path,
        *,
        body_factory: Callable[[], Body],
        budget: Budget | None = None,
        isolation: Isolation | None = None,
        grade: Callable[[Mapping[str, Any], Any], str] | None = None,
        allow_self_reported_outcomes: bool = False,
        superseded: bool = False,
    ) -> "Genesis":
        """Resume one committed checkpoint, or refuse.

        The caller may supply the means to *resolve* the body, but not to choose a different one; the
        budget and its spend ledger come from the checkpoint rather than from the caller; and the
        isolation envelope may not be widened on the way back in. `budget` and `isolation` are kept
        in the signature only to be checked against what was committed.

        The manifest is read **first** and names the payload files to load. It used to load two fixed
        filenames and then check them against the manifest, which worked only because nothing else
        could ever be on disk. `superseded=True` resumes the checkpoint this directory committed
        before its current one — the reason the payloads are content-addressed, so that falling back
        is a real option rather than a refusal.
        """
        directory = Path(directory)
        path = directory / (PREVIOUS_CHECKPOINT_NAME if superseded else CHECKPOINT_NAME)
        if not path.exists():
            raise TrustRootError(
                "no committed checkpoint at %s: state and journal alone do not say which body, "
                "budget or evaluator this lineage was admitted under" % path
            )
        manifest = json.loads(path.read_bytes().decode("utf-8"))
        expected = digest_of({k: v for k, v in manifest.items() if k != "checkpoint_digest"})
        if manifest.get("checkpoint_digest") != expected:
            raise TrustRootError("the checkpoint manifest does not reproduce its own digest")

        # Named by the manifest, with the pre-content-addressing filenames as the fallback so a
        # checkpoint written by an earlier build still resumes.
        state = lineage_state.load_state(
            directory / str(manifest.get("state_path") or "lineage_state.json")
        )
        journal = Journal.load(
            directory / str(manifest.get("journal_path") or "descent_journal.json")
        )
        if manifest.get("state_digest") != state["state_digest"]:
            raise TrustRootError("the persisted state is not the one this checkpoint committed")
        if manifest.get("journal_head") != journal.head:
            raise TrustRootError("the persisted journal is not the one this checkpoint committed")

        arriving = artifact_digest_of(body_factory)
        committed_body = manifest.get("body_artifact") or {}
        if arriving["artifact_digest"] != committed_body.get("artifact_digest"):
            raise TrustRootError(
                "the supplied body is not the body this lineage was persisted with: committed %s, "
                "supplied %s" % (committed_body.get("qualname"), arriving.get("qualname"))
            )

        committed_isolation = Isolation(
            **{k: v for k, v in manifest["admitted_isolation"].items() if k != "schema"}
        )
        # What the lineage was actually running under, which is not necessarily its ceiling. Resuming
        # at the admitted envelope when the caller supplies nothing silently widens a lineage that
        # had been running narrower — process death is not an occasion to be granted more room.
        running_isolation = Isolation(
            **{k: v for k, v in manifest.get("isolation", manifest["admitted_isolation"]).items()
               if k != "schema"}
        )
        if isolation is not None:
            isolation.assert_no_wider_than(committed_isolation)
        committed_budget = Budget(
            limits=dict(manifest["budget"]["limits"]), spent=dict(manifest["budget"]["spent"])
        )
        if budget is not None and dict(budget.limits) != dict(committed_budget.limits):
            raise TrustRootError(
                "restore may not re-admit a different allowance: committed %s, supplied %s"
                % (dict(committed_budget.limits), dict(budget.limits))
            )

        resumed = Genesis(
            state=state,
            body_factory=body_factory,
            budget=committed_budget,
            isolation=isolation or running_isolation,
            journal=journal,
            admitted_isolation=committed_isolation,
            admitted_source_sha256=manifest["admitted_trust_root_sha256"],
            grade=grade,
            allow_self_reported_outcomes=manifest.get("allow_self_reported_outcomes", False)
            or allow_self_reported_outcomes,
        )
        committed_contract = manifest.get("evaluation_contract") or {}
        if resumed.evaluation_contract["contract_digest"] != committed_contract.get(
            "contract_digest"
        ):
            raise TrustRootError(
                "the evaluator this lineage was admitted under is not the one supplied on restore"
            )
        resumed.evaluated_task_digests = set(manifest.get("evaluated_task_sets") or [])
        return resumed


# ---------------------------------------------------------------------------------------------
# Causal dependency between generations
# ---------------------------------------------------------------------------------------------
def ablation_supports_causal_dependency(
    *,
    parent_outcomes: Sequence[Mapping[str, Any]],
    with_acquisition: Sequence[Mapping[str, Any]],
    without_acquisition: Sequence[Mapping[str, Any]],
    equal_budget: bool,
) -> dict[str, Any]:
    """Test whether the *new work* of a later generation needed an earlier acquisition.

    A raw loss in total solved tasks is insufficient. The earlier acquisition is retained work, so
    ablating it can trivially break tasks the parent already solved while leaving every task newly
    solved by the later generation intact. That demonstrates retention dependence, not causal
    dependence of the new improvement.

    The comparison identifies the tasks the candidate newly solves relative to its parent and
    requires the equal-budget ablation to lose at least one of those tasks. Losses confined to work
    the parent already solved are recorded separately and establish nothing about this generation's
    novelty.
    """
    if not equal_budget:
        return {
            "supported": False,
            "reason": "the ablated arm did not run at the same budget, so the comparison is void",
        }

    def by_task(rows: Sequence[Mapping[str, Any]], label: str) -> dict[str, str]:
        mapped: dict[str, str] = {}
        for row in rows:
            task_id = row.get("task_id")
            if not isinstance(task_id, str) or not task_id:
                raise TrustRootError("%s causal outcome carries no task id" % label)
            if task_id in mapped:
                raise TrustRootError("%s causal outcome repeats task %r" % (label, task_id))
            mapped[task_id] = str(row.get("outcome") or "")
        return mapped

    parent = by_task(parent_outcomes, "parent")
    intact = by_task(with_acquisition, "candidate")
    ablated = by_task(without_acquisition, "ablated candidate")
    if set(parent) != set(intact) or set(parent) != set(ablated):
        raise TrustRootError("causal parent, candidate and ablation did not face the same tasks")

    parent_solved = {task for task, outcome in parent.items() if outcome == "solved"}
    intact_solved = {task for task, outcome in intact.items() if outcome == "solved"}
    ablated_solved = {task for task, outcome in ablated.items() if outcome == "solved"}

    newly_solved = intact_solved - parent_solved
    lost_newly_solved = newly_solved - ablated_solved
    retained_solved = parent_solved & intact_solved
    lost_retained_solved = retained_solved - ablated_solved
    all_lost = intact_solved - ablated_solved

    supported = bool(lost_newly_solved)
    if supported:
        reason = ""
    elif not newly_solved:
        reason = (
            "the later generation solved no task its parent did not already solve, so there is no "
            "new work whose dependency could be established"
        )
    elif all_lost:
        reason = (
            "removing the earlier acquisition only broke retained work; every task newly solved by "
            "the later generation remained solved"
        )
    else:
        reason = (
            "removing the earlier acquisition cost nothing on the later generation's newly solved "
            "work, so the new improvement did not need it"
        )

    return {
        "supported": supported,
        "solved_with_acquisition": len(intact_solved),
        "solved_without_acquisition": len(ablated_solved),
        "newly_solved_with_acquisition": sorted(newly_solved),
        "newly_solved_lost_without_acquisition": sorted(lost_newly_solved),
        "retained_solved_lost_without_acquisition": sorted(lost_retained_solved),
        "reason": reason,
        "equal_budget": True,
    }
