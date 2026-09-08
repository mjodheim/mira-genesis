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
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

from genesis import state as lineage_state
from genesis.journal import Journal
from genesis.sandbox import run_candidate
from genesis.trust_root import (
    Budget,
    BudgetExhausted,
    Isolation,
    TrustRootError,
    digest_of,
    verify_verdict,
)

CYCLE_SCHEMA = "genesis-cycle-v1"
CAMPAIGN_SCHEMA = "genesis-campaign-v1"


class Body(Protocol):
    """The minimum a body must offer. Anything richer is the lineage's business, not the loop's."""

    def attempt(self, task: Mapping[str, Any]) -> str:  # pragma: no cover - protocol
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

    def digest(self) -> str:
        return digest_of(
            {"name": self.name, "provenance": dict(self.provenance), "rationale": dict(self.rationale)}
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
    ) -> None:
        from genesis.trust_root import source_digest

        self.state = lineage_state.decode_state(state)
        self.body_factory = body_factory
        self.budget = budget
        self.isolation = isolation
        self.admitted_isolation = isolation
        self.admitted_source_sha256 = admitted_source_sha256 or source_digest()
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
        required_strict_improvement: bool = True,
    ) -> dict[str, Any]:
        """Run one observe→…→continue cycle. Returns the cycle record; never raises on rejection."""
        generation = self.state["generation"]
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

        parent = run_candidate(
            self.body_factory, tasks, self.isolation, admitted_isolation=self.admitted_isolation
        )
        if not parent["completed"]:
            return abort("parent", parent)
        self.journal.append(
            "observation",
            generation,
            {"arm": "parent", "sandbox_digest": parent["result_digest"]},
        )

        proposal = propose(self, tasks)
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
            tasks,
            self.isolation,
            admitted_isolation=self.admitted_isolation,
        )
        if not candidate["completed"]:
            return abort("candidate", candidate)
        control = (
            run_candidate(
                control_factory, tasks, self.isolation, admitted_isolation=self.admitted_isolation
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
        )
        problems = verify_verdict(verdict, admitted_source_sha256=self.admitted_source_sha256)
        if problems:
            raise TrustRootError("; ".join(problems))

        causal = self._causal_dependency(proposal, tasks, parent, candidate)
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
            "causal_dependency": causal["record"],
            "journal_entry": entry["entry_digest"],
            "state_digest": self.state["state_digest"],
        }

    # -- causal dependency, on every cycle rather than once per milestone ------------------
    def _causal_dependency(self, proposal, tasks, parent, candidate) -> dict[str, Any]:
        """Run the proposal's ablation arm, if it supplied one, and judge what it shows.

        This lives in the cycle rather than in whatever script happens to be driving it. It was in a
        script for a while, and the loop's own docstring described the check as a permanent
        obligation of the runtime the whole time — which is a record testifying to a property the
        code did not have.

        A lineage with no acquisitions yet has nothing to have depended on, so the absence of an arm
        is not a failure there. Once it has one, an acceptance without an ablation arm is recorded as
        `established: false` with the reason, never as an unexamined pass.
        """
        first_acquisition = not self.state["acquisitions"]
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
        )
        if not run["completed"]:
            return {"instrument_abort": True, "run": run, "record": {"established": False}}

        outcome = ablation_supports_causal_dependency(
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
        """How far back the lineage's improvements actually depend on each other.

        A run of acceptances is not a chain. This counts the consecutive acquisitions, ending at the
        most recent, whose dependency on the one before was established by ablation — so a claim
        about recursive improvement has to read a number that can be small.
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
            "is_a_chain_rather_than_a_sequence": length >= 2,
        }

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
    def persist(self, directory: Path) -> dict[str, str]:
        directory = Path(directory)
        return {
            "state": lineage_state.save_state(self.state, directory / "lineage_state.json"),
            "journal": self.journal.save(directory / "descent_journal.json"),
        }

    @staticmethod
    def restore(
        directory: Path,
        *,
        body_factory: Callable[[], Body],
        budget: Budget,
        isolation: Isolation,
    ) -> "Genesis":
        """Come back after process death from persisted state, re-validating both artifacts."""
        directory = Path(directory)
        return Genesis(
            state=lineage_state.load_state(directory / "lineage_state.json"),
            body_factory=body_factory,
            budget=budget,
            isolation=isolation,
            journal=Journal.load(directory / "descent_journal.json"),
        )


# ---------------------------------------------------------------------------------------------
# Causal dependency between generations
# ---------------------------------------------------------------------------------------------
def ablation_supports_causal_dependency(
    *,
    with_acquisition: Sequence[Mapping[str, Any]],
    without_acquisition: Sequence[Mapping[str, Any]],
    equal_budget: bool,
) -> dict[str, Any]:
    """Test whether a later generation actually needed an earlier acquisition.

    Remove the earlier acquisition, retry the later generation at the same budget, and require a
    measured loss. A sequence of improvements that each happened to work is not a causal chain, and
    this is checked on every generation rather than once per milestone.
    """
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
