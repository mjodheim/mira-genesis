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
same budget and requires a loss of reach. `causal_chain` then counts the consecutive acquisitions
whose dependency was actually established, so a claim about recursive improvement reads a number that
can be small.

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


def question_digest(task: Mapping[str, Any]) -> str:
    """Identify one task by its question, ignoring the label it happens to carry."""
    return digest_of({k: v for k, v in dict(task).items() if k != "task_id"})


def task_set_digest(tasks: Sequence[Mapping[str, Any]]) -> str:
    """Identify a task set by the questions in it, not by the labels on them.

    This hashed `task_id` values, which are labels: a caller could reuse the identifiers of a set the
    lineage had been judged on, put easier contents underneath, and present the result as previously
    evaluated work. Duplicates are kept — two identical questions asked twice are not the same body
    of work as one — and the target is included, because changing what counts as right changes what
    the lineage was judged on.
    """
    return digest_of(sorted(question_digest(task) for task in tasks))


def _task_snapshot(tasks: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    """Canonical detached task values shared by every evaluator arm in one cycle.

    The proposer used to receive the same mutable task objects that were later handed to the
    candidate. It ran after the parent arm, so changing a question in place changed only the
    candidate's exam while preserving the labels the trust root compared. Canonical JSON copying
    fixes the evaluation set before any lineage-owned callback runs. The proposer receives another
    detached copy of this snapshot, so it can annotate or rearrange its private input without
    changing what any arm is measured on.
    """
    copied = json.loads(canonical_bytes([dict(task) for task in tasks]).decode("utf-8"))
    if not isinstance(copied, list) or not all(isinstance(task, dict) for task in copied):
        raise TrustRootError("evaluation tasks did not canonicalise to records")
    return tuple(copied)


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

    `ablated_body_factory` is this candidate with the earlier acquisition it depends on taken away
    and nothing else changed. Supplying it is how a lineage offers evidence that this generation
    *needed* the one before it; omitting it is allowed, and the cycle then records that the causal
    claim was not established rather than quietly assuming it. `depends_on` names the acquisition
    that was removed, so the record says what the arm actually is.
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
        admitted_source_sha256: str | None = None,
        grade: Callable[[Mapping[str, Any], Any], str] | None = None,
        control_factory: Callable[[], Body] | None = None,
        allow_self_reported_outcomes: bool = False,
    ) -> None:
        from genesis.trust_root import source_digest

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
        self.admitted_isolation = isolation
        self.admitted_source_sha256 = admitted_source_sha256 or source_digest()
        self.grade = grade
        self.control_factory = control_factory
        self.evaluation_contract = evaluation_contract(
            grade=grade,
            control_policy="equal_budget_control" if control_factory is not None else "none",
            control_artifact=control_factory,
        )
        self.allow_self_reported_outcomes = allow_self_reported_outcomes
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
                    "evaluation_contract_digest": self.evaluation_contract["contract_digest"],
                },
            )

    # -- one cycle ------------------------------------------------------------------------
    def cycle(
        self,
        tasks: Sequence[Mapping[str, Any]],
        propose: Callable[[LineageContext, Sequence[Mapping[str, Any]]], Proposal | None],
        *,
        control_factory: Callable[[], Body] | None = None,
        required_strict_improvement: bool = True,
    ) -> dict[str, Any]:
        """Run one observe→…→continue cycle. Returns the cycle record; never raises on rejection."""
        generation = self.state["generation"]
        evaluation_tasks = _task_snapshot(tasks)
        evaluation_task_digest = task_set_digest(evaluation_tasks)

        admitted_control = self.control_factory
        if control_factory is not None:
            if admitted_control is None:
                raise TrustRootError(
                    "a control arm was supplied outside the admitted evaluation contract"
                )
            if artifact_digest_of(control_factory)["artifact_digest"] != artifact_digest_of(
                admitted_control
            )["artifact_digest"]:
                raise TrustRootError(
                    "the supplied control arm is not the control artifact admitted in the evaluation contract"
                )
        control_factory = admitted_control

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

        parent = run_candidate(
            self.body_factory,
            evaluation_tasks,
            self.isolation,
            admitted_isolation=self.admitted_isolation,
            grade=self.grade,
        )
        if not parent["completed"]:
            return abort("parent", parent)
        self.evaluated_task_digests.add(evaluation_task_digest)
        self.journal.append(
            "observation",
            generation,
            {
                "arm": "parent",
                "sandbox_digest": parent["result_digest"],
                "task_set_digest": evaluation_task_digest,
            },
        )

        proposer_tasks = json.loads(canonical_bytes(list(evaluation_tasks)).decode("utf-8"))
        try:
            proposal = propose(self.context(), proposer_tasks)
        except Exception as failure:
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
                "task_set_digest": evaluation_task_digest,
            },
        )

        candidate = run_candidate(
            proposal.body_factory,
            evaluation_tasks,
            self.isolation,
            admitted_isolation=self.admitted_isolation,
            grade=self.grade,
        )
        if not candidate["completed"]:
            return abort("candidate", candidate)
        control = (
            run_candidate(
                control_factory,
                evaluation_tasks,
                self.isolation,
                admitted_isolation=self.admitted_isolation,
                grade=self.grade,
            )
            if control_factory is not None
            else None
        )
        if control is not None and not control["completed"]:
            return abort("control", control)

        from genesis.trust_root import decide

        verdict = decide(
            parent_outcomes=parent["outcomes"],
            candidate_outcomes=candidate["outcomes"],
            control_outcomes=control["outcomes"] if control else None,
            budget=self.budget,
            isolation=self.isolation,
            admitted_isolation=self.admitted_isolation,
            candidate_provenance=proposal.provenance,
            required_strict_improvement=required_strict_improvement,
            evaluation_contract_record=self.evaluation_contract,
        )
        problems = verify_verdict(verdict, admitted_source_sha256=self.admitted_source_sha256)
        if problems:
            raise TrustRootError("; ".join(problems))

        causal = self._causal_dependency(proposal, evaluation_tasks, parent, candidate)
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
                        "body_artifact": proposal.body_artifact(),
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
                    "body_artifact": proposal.body_artifact(),
                    "causal_dependency_established": causal["record"]["established"],
                },
            )
        else:
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
            "task_set_digest": evaluation_task_digest,
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

    def _causal_dependency(self, proposal, tasks, parent, candidate) -> dict[str, Any]:
        first_acquisition = not self.state["acquisitions"]
        held = {str(item.get("name", "")) for item in self.state["acquisitions"]}
        if proposal.ablated_body_factory is not None and proposal.depends_on not in held:
            return {
                "record": {
                    "established": False,
                    "arm_supplied": True,
                    "depends_on": proposal.depends_on,
                    "why": "the proposal names %r, which this lineage never acquired, so the arm "
                    "cannot be that acquisition removed" % proposal.depends_on,
                }
            }
        if proposal.ablated_body_factory is None:
            return {
                "record": {
                    "established": False,
                    "arm_supplied": False,
                    "why": "the lineage's first acquisition depends on nothing earlier"
                    if first_acquisition
                    else "the proposal supplied no ablation arm, so nothing shows this generation "
                    "needed the one before it",
                    "depends_on": proposal.depends_on,
                }
            }

        run = run_candidate(
            proposal.ablated_body_factory,
            tasks,
            self.isolation,
            admitted_isolation=self.admitted_isolation,
            grade=self.grade,
        )
        if not run["completed"]:
            return {"instrument_abort": True, "run": run, "record": {"established": False}}

        outcome = ablation_supports_causal_dependency(
            with_acquisition=candidate["outcomes"],
            without_acquisition=run["outcomes"],
            equal_budget=True,
        )
        distinct = run["result_digest"] != parent["result_digest"]
        established = bool(outcome["supported"] and distinct)
        return {
            "record": {
                "established": established,
                "arm_supplied": True,
                "depends_on": proposal.depends_on,
                "solved_with_acquisition": outcome["solved_with_acquisition"],
                "solved_without_acquisition": outcome["solved_without_acquisition"],
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
        acquisitions = list(self.state["acquisitions"])
        length = 0
        for acquisition in reversed(acquisitions):
            if not (acquisition.get("causal_dependency") or {}).get("established"):
                break
            length += 1
        return {
            "acquisitions": len(acquisitions),
            "established_links": length,
            "makes_no_recursion_claim": True,
        }

    def evolve(
        self,
        task_families: Sequence[Sequence[Mapping[str, Any]]],
        propose: Callable[[LineageContext, Sequence[Mapping[str, Any]]], Proposal | None],
        *,
        control_factory: Callable[[], Body] | None = None,
    ) -> dict[str, Any]:
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
    def checkpoint(self) -> dict[str, Any]:
        """Everything that decides which lineage resumes and under which rules, as one value."""
        payload = {
            "schema": CHECKPOINT_SCHEMA,
            "generation": self.state["generation"],
            "state_digest": self.state["state_digest"],
            "journal_head": self.journal.head,
            "state_payload": "states/%s.json" % self.state["state_digest"],
            "journal_payload": "journals/%s.json" % self.journal.head,
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
        """Persist immutable payloads first and publish the checkpoint pointer last.

        Fixed filenames are only compatibility mirrors now. The committed manifest resolves
        content-addressed state and journal payloads that are never overwritten, so death before a
        later manifest publication leaves the previous committed lineage recoverable rather than
        merely detectable as torn.
        """
        directory = Path(directory)
        manifest = self.checkpoint()
        state_path = directory / manifest["state_payload"]
        journal_path = directory / manifest["journal_payload"]
        written = {
            "state": lineage_state.save_state(self.state, state_path),
            "journal": self.journal.save(journal_path),
        }

        path = directory / "runtime_checkpoint.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".partial")
        temporary.write_bytes(canonical_bytes(manifest) + b"\n")
        temporary.replace(path)
        written["checkpoint"] = manifest["checkpoint_digest"]

        # Compatibility mirrors for existing tooling. Restore never trusts these when the manifest
        # names content-addressed payloads, so a crash while refreshing a mirror cannot destroy the
        # last committed checkpoint.
        lineage_state.save_state(self.state, directory / "lineage_state.json")
        self.journal.save(directory / "descent_journal.json")
        return written

    @staticmethod
    def restore(
        directory: Path,
        *,
        body_factory: Callable[[], Body],
        budget: Budget | None = None,
        isolation: Isolation | None = None,
        grade: Callable[[Mapping[str, Any], Any], str] | None = None,
        control_factory: Callable[[], Body] | None = None,
        allow_self_reported_outcomes: bool = False,
    ) -> "Genesis":
        """Resume one committed checkpoint, or refuse."""
        directory = Path(directory)
        path = directory / "runtime_checkpoint.json"
        if not path.exists():
            raise TrustRootError(
                "no committed checkpoint at %s: state and journal alone do not say which body, "
                "budget or evaluator this lineage was admitted under" % path
            )
        manifest = json.loads(path.read_bytes().decode("utf-8"))
        expected = digest_of({k: v for k, v in manifest.items() if k != "checkpoint_digest"})
        if manifest.get("checkpoint_digest") != expected:
            raise TrustRootError("the checkpoint manifest does not reproduce its own digest")

        state_relative = manifest.get("state_payload") or "lineage_state.json"
        journal_relative = manifest.get("journal_payload") or "descent_journal.json"
        state = lineage_state.load_state(directory / state_relative)
        journal = Journal.load(directory / journal_relative)
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

        admitted_isolation = Isolation(
            **{k: v for k, v in manifest["admitted_isolation"].items() if k != "schema"}
        )
        current_isolation_record = manifest.get("isolation") or manifest["admitted_isolation"]
        current_isolation = Isolation(
            **{k: v for k, v in current_isolation_record.items() if k != "schema"}
        )
        if isolation is not None and isolation.record() != current_isolation.record():
            raise TrustRootError(
                "restore may not change the current isolation envelope: committed %s, supplied %s"
                % (current_isolation.record(), isolation.record())
            )
        current_isolation.assert_no_wider_than(admitted_isolation)

        committed_budget = Budget(
            limits=dict(manifest["budget"]["limits"]), spent=dict(manifest["budget"]["spent"])
        )
        if budget is not None and dict(budget.limits) != dict(committed_budget.limits):
            raise TrustRootError(
                "restore may not re-admit a different allowance: committed %s, supplied %s"
                % (dict(committed_budget.limits), dict(budget.limits))
            )

        committed_self_reported = bool(manifest.get("allow_self_reported_outcomes", False))
        if allow_self_reported_outcomes and not committed_self_reported:
            raise TrustRootError(
                "restore may not widen the admitted outcome authority to self-reported verdicts"
            )

        resumed = Genesis(
            state=state,
            body_factory=body_factory,
            budget=committed_budget,
            isolation=current_isolation,
            journal=journal,
            admitted_source_sha256=manifest["admitted_trust_root_sha256"],
            grade=grade,
            control_factory=control_factory,
            allow_self_reported_outcomes=committed_self_reported,
        )
        resumed.admitted_isolation = admitted_isolation
        committed_contract = manifest.get("evaluation_contract") or {}
        if resumed.evaluation_contract["contract_digest"] != committed_contract.get(
            "contract_digest"
        ):
            raise TrustRootError(
                "the evaluator/control contract this lineage was admitted under is not the one supplied on restore"
            )
        resumed.evaluated_task_digests = set(manifest.get("evaluated_task_sets") or [])
        return resumed


# ---------------------------------------------------------------------------------------------
# Causal dependency between generations
# ---------------------------------------------------------------------------------------------
def ablation_supports_causal_dependency(
    *,
    with_acquisition: Sequence[Mapping[str, Any]],
    without_acquisition: Sequence[Mapping[str, Any]],
    equal_budget: bool,
) -> dict[str, Any]:
    """Test whether a later generation actually needed an earlier acquisition."""
    if not equal_budget:
        return {
            "supported": False,
            "reason": "the ablated arm did not run at the same budget, so the comparison is void",
        }

    def solved(rows: Sequence[Mapping[str, Any]]) -> int:
        return sum(1 for row in rows if row.get("outcome") == "solved")

    intact, ablated = solved(with_acquisition), solved(without_acquisition)
    supported = ablated < intact
    return {
        "supported": supported,
        "solved_with_acquisition": intact,
        "solved_without_acquisition": ablated,
        "reason": ""
        if supported
        else "removing the earlier acquisition cost nothing, so the later generation did not need it",
        "equal_budget": True,
    }
