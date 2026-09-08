"""Hostile tests for the descent journal, the sandbox and the evolution loop.

The properties that matter here are the ones every M107–M111 experiment demonstrated once and then
stopped at: a rejection does not end the run, the history keeps what actually happened, an
infrastructure failure is not a candidate failure, and a later generation must be shown to have
needed an earlier acquisition.
"""
from __future__ import annotations

import functools
import json

import pytest

from genesis import development_bodies as bodies
from genesis import journal as jr
from genesis import sandbox as sb
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import Genesis, Proposal, ablation_supports_causal_dependency

TASKS = [{"task_id": "t%d" % index, "input": index} for index in range(8)]
LINEAGE = tr.provenance("lineage_owned", produced_by="lineage")


def _seed_state():
    return st.create_state(
        body_digest="b0",
        components=[
            {
                "name": "operator_table",
                "origin": "seed",
                "certificate": None,
                "provenance": tr.provenance("host_written", produced_by="seed"),
            }
        ],
        vocabulary=[{"name": "axis_progress", "origin": "seed", "certificate": None}],
    )


def _genesis(
    *,
    generations: int = 6,
    body=bodies.parent_body,
    grade=bodies.grade,
    allow_self_reported_outcomes: bool = False,
):
    return Genesis(
        state=_seed_state(),
        body_factory=body,
        budget=tr.Budget(limits={"generations": generations}),
        isolation=tr.Isolation(),
        grade=grade,
        allow_self_reported_outcomes=allow_self_reported_outcomes,
    )


def _proposer(*factories):
    queue = list(factories)

    def propose(genesis, tasks):
        if not queue:
            return None
        factory = queue.pop(0)
        return Proposal(
            name=factory.__name__,
            body_factory=factory,
            provenance=LINEAGE,
            rationale={"why": "test"},
        )

    return propose


# -- the descent journal ------------------------------------------------------------------------

def test_the_chain_links_every_entry_to_its_predecessor():
    journal = jr.Journal()
    journal.append("seed", 0, {"a": 1})
    journal.append("observation", 0, {"b": 2})
    journal.append("candidate_rejected", 0, {"c": 3})
    assert jr.verify(journal.entries()) == []
    assert journal.entries()[1]["previous_digest"] == journal.entries()[0]["entry_digest"]


def test_altering_an_entry_breaks_everything_after_it():
    journal = jr.Journal()
    journal.append("seed", 0, {"a": 1})
    journal.append("observation", 0, {"b": 2})
    journal.append("candidate_accepted", 0, {"c": 3})
    entries = journal.entries()
    entries[1]["payload"] = {"b": 99}
    problems = jr.verify(entries)
    assert any("does not reproduce its own digest" in problem for problem in problems)
    assert any("does not follow its predecessor" in problem for problem in problems)


def test_a_removed_entry_is_detected():
    journal = jr.Journal()
    for index in range(4):
        journal.append("observation", 0, {"i": index})
    entries = journal.entries()
    del entries[2]
    assert any("does not follow its predecessor" in problem for problem in jr.verify(entries))


def test_an_unrecognised_entry_kind_is_refused():
    with pytest.raises(jr.JournalError, match="unrecognised journal entry kind"):
        jr.Journal().append("looked_fine", 0, {})


def test_the_journal_survives_a_save_and_load(tmp_path):
    journal = jr.Journal()
    journal.append("seed", 0, {"a": 1})
    journal.append("candidate_rejected", 0, {"why": "kept on purpose"})
    journal.save(tmp_path / "j.json")
    restored = jr.Journal.load(tmp_path / "j.json")
    assert restored.entries() == journal.entries()
    assert restored.head == journal.head


def test_a_tampered_journal_file_is_refused(tmp_path):
    journal = jr.Journal()
    journal.append("seed", 0, {"a": 1})
    journal.save(tmp_path / "j.json")
    payload = json.loads((tmp_path / "j.json").read_text())
    payload["entries"][0]["payload"] = {"a": 2}
    (tmp_path / "j.json").write_text(json.dumps(payload))
    with pytest.raises(jr.JournalError):
        jr.Journal.load(tmp_path / "j.json")


# -- the sandbox --------------------------------------------------------------------------------

def test_a_candidate_runs_in_a_separate_process_without_network():
    result = sb.run_candidate(bodies.parent_body, TASKS, tr.Isolation(), grade=bodies.grade)
    assert result["completed"] is True
    assert result["separate_process"] is True
    assert result["network_permitted"] is False
    assert result["carries_a_score"] is False
    assert {row["outcome"] for row in result["outcomes"]} <= set(tr.TASK_OUTCOMES)


def test_network_can_never_be_granted_to_a_candidate():
    with pytest.raises(tr.TrustRootError, match="may not be granted network access"):
        sb.run_candidate(bodies.parent_body, TASKS, tr.Isolation(network_permitted=True))


def test_the_sandbox_reports_which_limits_it_actually_enforced():
    result = sb.run_candidate(bodies.parent_body, TASKS, tr.Isolation())
    assert isinstance(result["enforced"], list)
    assert isinstance(result["unenforced"], list)
    assert sb.isolation_is_complete(result) == (not result["unenforced"])


def test_a_body_that_throws_yields_error_rows_rather_than_crashing_the_runtime():
    result = sb.run_candidate(bodies.throwing_body, TASKS, tr.Isolation())
    assert result["completed"] is True
    assert all(row["outcome"] == "error" for row in result["outcomes"])


def test_a_body_that_cannot_be_constructed_is_an_instrument_failure_not_a_candidate_failure():
    """The distinction that keeps an infrastructure fault out of the science."""
    result = sb.run_candidate(bodies.unconstructible_body, TASKS, tr.Isolation())
    assert result["completed"] is False
    assert result["instrument_failure"] is True
    assert result["outcomes"] == [], "a run that never happened must not invent outcomes"


def test_a_repeated_task_id_is_refused():
    with pytest.raises(sb.SandboxError, match="repeats a task id"):
        sb.run_candidate(bodies.parent_body, TASKS + [TASKS[0]], tr.Isolation())


def test_refusal_reaches_the_trust_root_as_its_own_outcome():
    result = sb.run_candidate(bodies.refusing_body, TASKS, tr.Isolation(), grade=bodies.grade)
    assert any(row["outcome"] == "refused" for row in result["outcomes"])


# -- isolation that is applied rather than declared ----------------------------------------------
#
# `filesystem_writes_permitted` and `network_permitted` were on Isolation, were checked by
# assert_no_wider_than, appeared in the record — and applied to nothing. A declared limit nobody
# enforces is worse than an absent one, because the record then testifies to a boundary that was
# never there. These tests fail if the enforcement is removed again.

def test_a_candidate_that_tries_to_write_is_stopped(tmp_path):
    target = tmp_path / "escaped.txt"
    result = sb.run_candidate(
        functools.partial(bodies.writing_body, target), TASKS, tr.Isolation()
    )
    assert result["completed"] is True
    assert all(row["outcome"] == "error" for row in result["outcomes"])
    assert not target.exists(), "the write was reported as blocked but the file is on disk"
    assert "filesystem_writes_permitted" in result["enforced"]


def test_the_write_test_is_not_passing_for_some_unrelated_reason(tmp_path):
    """Non-vacuity: the same body succeeds when nothing stops it."""
    target = tmp_path / "written.txt"
    assert bodies.writing_body(target).attempt(TASKS[0]) == "solved"
    assert target.read_text(encoding="utf-8") == TASKS[0]["task_id"]


def test_a_candidate_that_tries_to_reach_the_network_is_stopped():
    result = sb.run_candidate(bodies.networking_body, TASKS, tr.Isolation())
    assert result["completed"] is True
    assert all(row["outcome"] == "error" for row in result["outcomes"])
    assert "network_permitted" in result["enforced"]


def test_the_network_test_is_not_passing_for_some_unrelated_reason():
    """Non-vacuity: loopback resolution needs no network, so it succeeds unless something forbids it."""
    assert bodies.networking_body().attempt(TASKS[0]) == "solved"


def test_a_candidate_cannot_write_by_taking_the_low_level_route(tmp_path):
    """`os.open` carries its write intent in the flags and reports mode `None`.

    A guard that only inspects the string mode enforces the limit against `open(path, "w")` and
    against nothing else. This is the spelling that found the hole.
    """
    target = tmp_path / "by_flags.txt"
    result = sb.run_candidate(
        functools.partial(bodies.low_level_writing_body, target), TASKS, tr.Isolation()
    )
    assert all(row["outcome"] == "error" for row in result["outcomes"])
    assert not target.exists()


def test_the_low_level_write_test_is_not_passing_for_some_unrelated_reason(tmp_path):
    target = tmp_path / "by_flags_ok.txt"
    assert bodies.low_level_writing_body(target).attempt(TASKS[0]) == "solved"
    assert target.read_text(encoding="utf-8") == TASKS[0]["task_id"]


def test_a_candidate_cannot_delete_a_file(tmp_path):
    """Deleting never touches `open`. A write guard that only watches `open` misses it entirely."""
    target = tmp_path / "keep_me.txt"
    target.write_text("mine", encoding="utf-8")
    result = sb.run_candidate(
        functools.partial(bodies.deleting_body, target), TASKS, tr.Isolation()
    )
    assert all(row["outcome"] == "error" for row in result["outcomes"])
    assert target.read_text(encoding="utf-8") == "mine", "the candidate deleted a file it was denied"


def test_the_delete_test_is_not_passing_for_some_unrelated_reason(tmp_path):
    target = tmp_path / "gone.txt"
    target.write_text("x", encoding="utf-8")
    assert bodies.deleting_body(target).attempt(TASKS[0]) == "solved"
    assert not target.exists()


def test_a_candidate_cannot_start_a_subprocess():
    """`RLIMIT_NPROC` is refused on some platforms; the limit must hold anyway."""
    result = sb.run_candidate(bodies.subprocess_body, TASKS, tr.Isolation())
    assert all(row["outcome"] == "error" for row in result["outcomes"])
    assert "subprocess_permitted" in result["enforced"]
    assert "subprocess_permitted" not in result["unenforced"]


def test_the_sandbox_does_not_overstate_what_the_audit_hook_covers():
    """A pure-Python hook cannot stop a C extension, and the record must not imply that it can."""
    result = sb.run_candidate(bodies.parent_body, TASKS, tr.Isolation())
    assert result["audit_hook_covers_pure_python_only"] is True


# -- the loop -----------------------------------------------------------------------------------

def test_a_rejected_candidate_does_not_end_the_run():
    genesis = _genesis()
    campaign = genesis.evolve(
        [TASKS, TASKS, TASKS],
        _proposer(bodies.regressed_body, bodies.throwing_body, bodies.improved_body),
    )
    assert campaign["rejected"] == 2
    assert campaign["accepted"] == 1
    assert [record["accepted"] for record in campaign["cycles"]] == [False, False, True]


def test_a_rejection_is_kept_as_an_observation_the_lineage_holds():
    genesis = _genesis()
    genesis.cycle(TASKS, _proposer(bodies.regressed_body))
    observations = genesis.state["observations"]
    assert len(observations) == 1
    assert observations[0]["kind"] == "rejected_candidate"
    assert observations[0]["reasons"]


def test_a_rejection_does_not_advance_the_generation_and_an_acceptance_does():
    genesis = _genesis()
    genesis.cycle(TASKS, _proposer(bodies.regressed_body))
    assert genesis.state["generation"] == 0
    genesis.cycle(TASKS, _proposer(bodies.improved_body))
    assert genesis.state["generation"] == 1


def test_an_equal_candidate_is_rejected_for_want_of_strict_improvement():
    record = _genesis().cycle(TASKS, _proposer(bodies.equal_body))
    assert record["accepted"] is False
    assert "no strict improvement" in record["reason"]


def test_a_candidate_cannot_win_by_reporting_a_summary():
    record = _genesis().cycle(TASKS, _proposer(bodies.lying_body))
    assert record["accepted"] is False
    assert record["verdict"]["read_any_self_reported_score"] is False
    assert record["verdict"]["candidate"]["counts"]["solved"] == 1


def test_an_instrument_abort_produces_no_verdict_at_all():
    genesis = _genesis()
    record = genesis.cycle(TASKS, _proposer(bodies.unconstructible_body))
    assert record["instrument_abort"] is True
    assert record["stopped"] is True
    assert "verdict" not in record, "a run that never happened must not be scored"
    assert genesis.journal.of_kind("instrument_abort")


def test_the_budget_stops_the_loop_rather_than_letting_it_overrun():
    genesis = _genesis(generations=2)
    campaign = genesis.evolve(
        [TASKS, TASKS, TASKS],
        _proposer(bodies.regressed_body, bodies.regressed_body, bodies.improved_body),
    )
    assert campaign["cycles"][-1]["stopped"] is True
    assert "exhausted" in campaign["cycles"][-1]["reason"]
    assert genesis.journal.of_kind("budget_exhausted")


def test_no_proposal_is_a_cycle_that_continues_rather_than_an_error():
    record = _genesis().cycle(TASKS, lambda genesis, tasks: None)
    assert record["stopped"] is False
    assert record["accepted"] is False
    assert record["reason"] == "no candidate proposed"


def test_an_accepted_candidate_becomes_the_body_and_is_recorded_as_an_acquisition():
    genesis = _genesis()
    genesis.cycle(TASKS, _proposer(bodies.improved_body))
    assert len(genesis.state["acquisitions"]) == 1
    assert genesis.state["acquisitions"][0]["name"] == "improved_body"
    assert genesis.journal.of_kind("candidate_accepted")


def test_every_cycle_verdict_names_the_admitted_trust_root():
    genesis = _genesis()
    record = genesis.cycle(TASKS, _proposer(bodies.improved_body))
    assert record["verdict"]["trust_root_source_sha256"] == genesis.admitted_source_sha256
    assert tr.verify_verdict(
        record["verdict"], admitted_source_sha256=genesis.admitted_source_sha256
    ) == []


def test_the_control_arm_is_compared_when_supplied():
    record = _genesis().cycle(
        TASKS, _proposer(bodies.improved_body), control_factory=bodies.improved_body
    )
    assert record["accepted"] is False
    assert "equal-budget control" in record["reason"]


def test_the_whole_lineage_survives_process_death(tmp_path):
    genesis = _genesis()
    genesis.evolve([TASKS, TASKS], _proposer(bodies.regressed_body, bodies.improved_body))
    genesis.persist(tmp_path)
    restored = Genesis.restore(
        tmp_path,
        body_factory=bodies.improved_body,
        budget=tr.Budget(limits={"generations": 6}),
        isolation=tr.Isolation(),
        grade=bodies.grade,
    )
    assert restored.state["state_digest"] == genesis.state["state_digest"]
    assert restored.journal.head == genesis.journal.head
    assert restored.state["acquisitions"] == genesis.state["acquisitions"]
    assert restored.state["observations"] == genesis.state["observations"]


# -- causal dependency between generations ------------------------------------------------------

def test_removing_an_earlier_acquisition_must_cost_something():
    outcome = ablation_supports_causal_dependency(
        with_acquisition=[{"task_id": "t%d" % i, "outcome": "solved"} for i in range(4)],
        without_acquisition=[
            {"task_id": "t0", "outcome": "solved"},
            {"task_id": "t1", "outcome": "unsolved"},
            {"task_id": "t2", "outcome": "unsolved"},
            {"task_id": "t3", "outcome": "unsolved"},
        ],
        equal_budget=True,
    )
    assert outcome["supported"] is True
    assert outcome["solved_with_acquisition"] == 4
    assert outcome["solved_without_acquisition"] == 1


def test_an_ablation_that_costs_nothing_refutes_the_causal_claim():
    rows = [{"task_id": "t%d" % i, "outcome": "solved"} for i in range(4)]
    outcome = ablation_supports_causal_dependency(
        with_acquisition=rows, without_acquisition=list(rows), equal_budget=True
    )
    assert outcome["supported"] is False
    assert "cost nothing" in outcome["reason"]


def test_an_unequal_budget_voids_the_comparison_rather_than_passing_it():
    outcome = ablation_supports_causal_dependency(
        with_acquisition=[{"task_id": "t0", "outcome": "solved"}],
        without_acquisition=[{"task_id": "t0", "outcome": "unsolved"}],
        equal_budget=False,
    )
    assert outcome["supported"] is False
    assert "same budget" in outcome["reason"]


# -- causal dependency as a property of the runtime, not of whatever script drives it --------------
#
# `ablation_supports_causal_dependency` existed as a function and the loop's docstring called it a
# permanent obligation of the runtime, while the only thing ever calling it was the demonstration
# script. The cycle runs it now, and these tests are about the cycle.

def _cycle_with(genesis, factory, *, ablated=None, depends_on="", name="candidate"):
    queue = [factory]
    return genesis.cycle(
        TASKS,
        lambda _g, _t: Proposal(
            name=name,
            body_factory=queue.pop(0),
            provenance=LINEAGE,
            rationale={},
            ablated_body_factory=ablated,
            depends_on=depends_on,
        )
        if queue
        else None,
    )


def test_a_first_acquisition_depends_on_nothing_earlier():
    """No arm is required where there is nothing to have depended on, and the record says why."""
    genesis = _genesis()
    record = _cycle_with(genesis, bodies.improved_body)
    assert record["accepted"] is True
    causal = record["causal_dependency"]
    assert causal["established"] is False
    assert causal["arm_supplied"] is False
    assert "depends on nothing earlier" in causal["why"]


def test_a_later_acceptance_without_an_ablation_arm_is_recorded_as_unestablished():
    """Silence must read as silence. An unexamined acceptance is not an examined one."""
    genesis = _genesis()
    _cycle_with(genesis, bodies.improved_body, name="first")
    record = _cycle_with(genesis, bodies.refusing_body, name="second")
    causal = record["causal_dependency"]
    assert causal["arm_supplied"] is False
    assert causal["established"] is False
    assert "supplied no ablation arm" in causal["why"]


def test_the_cycle_runs_the_ablation_arm_the_proposal_carried():
    genesis = _genesis()
    _cycle_with(genesis, bodies.migrated_parent_body, name=bodies.ACQUIRED_COMPONENT)
    record = _cycle_with(
        genesis,
        bodies.migrated_improved_body,
        ablated=bodies.migrated_ablated_body,
        depends_on=bodies.ACQUIRED_COMPONENT,
        name="second",
    )
    causal = record["causal_dependency"]
    assert causal["arm_supplied"] is True
    assert causal["established"] is True
    assert causal["depends_on"] == bodies.ACQUIRED_COMPONENT
    assert causal["solved_without_acquisition"] < causal["solved_with_acquisition"]


def test_an_ablation_arm_that_is_really_the_parent_establishes_nothing():
    """The negative control, on the runtime's own path.

    The arm solves less than the candidate, so the measured loss alone would call it supported. It
    is refused because it is behaviourally the parent, and comparing a candidate with its parent is
    the verdict this cycle just reached rather than evidence on top of it.
    """
    genesis = _genesis()
    _cycle_with(genesis, bodies.migrated_parent_body, name=bodies.ACQUIRED_COMPONENT)
    record = _cycle_with(
        genesis,
        bodies.migrated_improved_body,
        ablated=bodies.migrated_uncoupled_ablation_body,
        depends_on=bodies.ACQUIRED_COMPONENT,
        name="second",
    )
    causal = record["causal_dependency"]
    assert causal["solved_without_acquisition"] < causal["solved_with_acquisition"]
    assert causal["ablated_arm_differs_from_the_parent_arm"] is False
    assert causal["established"] is False
    assert "identical to the parent arm" in causal["why"]


def test_an_ablation_arm_that_cannot_run_aborts_the_cycle():
    """A missing measurement is not a passed one, and it must not be scored as a candidate failure."""
    genesis = _genesis()
    _cycle_with(genesis, bodies.improved_body, name="something")
    record = _cycle_with(
        genesis,
        bodies.refusing_body,
        ablated=bodies.unconstructible_body,
        depends_on="something",
        name="second",
    )
    assert record["stopped"] is True
    assert record["instrument_abort"] is True
    assert record["accepted"] is False


def test_a_run_of_acceptances_is_not_a_chain():
    """`causal_chain` counts established links, so a claim about recursion reads a real number."""
    genesis = _genesis()
    _cycle_with(genesis, bodies.migrated_parent_body, name="first")
    _cycle_with(genesis, bodies.migrated_improved_body, name="second_unexamined")
    chain = genesis.causal_chain()
    assert chain["acquisitions"] == 2
    assert chain["established_links"] == 0
    assert chain["makes_no_recursion_claim"] is True


def test_the_chain_report_counts_links_without_grading_them():
    genesis = _genesis()
    _cycle_with(genesis, bodies.migrated_parent_body, name=bodies.ACQUIRED_COMPONENT)
    _cycle_with(
        genesis,
        bodies.migrated_improved_body,
        ablated=bodies.migrated_ablated_body,
        depends_on=bodies.ACQUIRED_COMPONENT,
        name=bodies.SECOND_ACQUISITION,
    )
    _cycle_with(
        genesis,
        bodies.migrated_further_body,
        ablated=bodies.migrated_further_ablated_body,
        depends_on=bodies.SECOND_ACQUISITION,
        name="third",
    )
    chain = genesis.causal_chain()
    assert chain["acquisitions"] == 3
    assert chain["established_links"] == 2
    assert "is_a_chain_rather_than_a_sequence" not in chain


# -- who decides whether a task was solved -----------------------------------------------------
#
# The trust root recomputes every number from raw per-task rows and never reads a score. That was
# always true and it was never enough: the rows themselves came out of the candidate's own process,
# so recomputing a tally from them is arithmetic on a claim rather than a measurement of it. A body
# that returns "solved" for everything was, quite literally, solving everything.

CHEAT_TASKS = [{"task_id": "t%d" % index, "input": index} for index in range(4)]


def test_a_body_that_claims_every_task_wins_when_it_grades_itself():
    """The hole, stated as a passing test so removing the fix cannot pass silently."""
    result = sb.run_candidate(bodies.cheating_body, CHEAT_TASKS, tr.Isolation())
    assert result["outcomes_are_self_reported"] is True
    assert all(row["outcome"] == "solved" for row in result["outcomes"])


def test_the_same_body_scores_nothing_when_the_parent_grades():
    """Same body, same tasks, one difference: it no longer gets to say whether it was right."""
    result = sb.run_candidate(
        bodies.cheating_body, CHEAT_TASKS, tr.Isolation(), grade=bodies.grade
    )
    assert result["outcomes_are_self_reported"] is False
    assert all(row["outcome"] == "unsolved" for row in result["outcomes"])


def test_a_cheating_candidate_is_rejected_by_the_cycle_when_grading_is_on():
    genesis = _genesis()
    record = _cycle_with(genesis, bodies.cheating_body, name="cheat")
    assert record["accepted"] is False
    assert record["outcomes_are_self_reported"] is False


def test_a_cheating_candidate_is_accepted_by_the_cycle_when_it_grades_itself():
    """The negative control for the fix, and the reason the flag is in every cycle record."""
    genesis = _genesis(grade=None, allow_self_reported_outcomes=True)
    record = _cycle_with(genesis, bodies.cheating_body, name="cheat")
    assert record["accepted"] is True, "self-reporting is what makes this candidate look good"
    assert record["outcomes_are_self_reported"] is True


def test_a_body_that_reads_the_answer_out_of_the_task_scores_nothing():
    """Grading in the parent decides nothing if the answer key rides in with the question.

    Every fixture in `development_bodies` used to return `task["expected"]`, so the grader added to
    stop a candidate marking its own paper was comparing the answer key against itself. The sandbox
    withholds the key now, and a body with nothing but the question has nothing to read.
    """
    result = sb.run_candidate(
        bodies.peeking_body, CHEAT_TASKS, tr.Isolation(), grade=bodies.grade
    )
    assert result["withheld_from_the_candidate"] == ["expected"]
    assert all(row["outcome"] == "unsolved" for row in result["outcomes"])


def test_the_same_body_scores_full_marks_when_the_answer_is_handed_to_it():
    """The negative control, and the reason the withholding is not decoration."""
    with_answers = [dict(task, expected=bodies.answer_to(task)) for task in CHEAT_TASKS]
    result = sb.run_candidate(
        bodies.peeking_body, with_answers, tr.Isolation(), grade=bodies.grade, withhold=()
    )
    assert result["withheld_from_the_candidate"] == []
    assert all(row["outcome"] == "solved" for row in result["outcomes"])


def test_the_child_never_receives_a_withheld_key():
    """Asserted on the task the child actually got, not on the outcome it produced."""
    with_answers = [dict(task, expected=bodies.answer_to(task)) for task in CHEAT_TASKS]
    result = sb.run_candidate(
        bodies.reporting_body, with_answers, tr.Isolation(), grade=bodies.keys_grade
    )
    assert all(row["outcome"] == "solved" for row in result["outcomes"]), (
        "the child saw a key the parent withheld"
    )


def test_an_honest_body_is_graded_on_the_answers_it_actually_gives():
    result = sb.run_candidate(
        bodies.parent_body, CHEAT_TASKS, tr.Isolation(), grade=bodies.grade
    )
    outcomes = {row["task_id"]: row["outcome"] for row in result["outcomes"]}
    assert outcomes == {"t0": "solved", "t1": "solved", "t2": "unsolved", "t3": "unsolved"}


def test_a_body_that_raises_is_an_error_and_is_never_handed_to_the_grader():
    """There is no answer to grade, so the grader must not be asked to invent one."""
    seen = []

    def grade(task, answer):
        seen.append(task)
        return "solved"

    result = sb.run_candidate(bodies.throwing_body, CHEAT_TASKS, tr.Isolation(), grade=grade)
    assert all(row["outcome"] == "error" for row in result["outcomes"])
    assert seen == [], "a body that produced nothing must not be graded as though it had"


def test_a_grader_that_raises_yields_error_rather_than_bringing_down_the_run():
    def grade(task, answer):
        raise RuntimeError("this grader is broken")

    result = sb.run_candidate(bodies.parent_body, CHEAT_TASKS, tr.Isolation(), grade=grade)
    assert all(row["outcome"] == "error" for row in result["outcomes"])


def test_a_grader_returning_something_outside_the_vocabulary_is_a_fault_not_a_pass():
    def grade(task, answer):
        return "brilliant"

    result = sb.run_candidate(bodies.parent_body, CHEAT_TASKS, tr.Isolation(), grade=grade)
    assert all(row["outcome"] == "error" for row in result["outcomes"])


def test_the_isolation_report_is_sent_before_the_candidate_exists():
    """A body sharing the process can reach locals through the frame stack.

    An isolation report assembled after the body ran is a report the body had the chance to
    rewrite, so it is sent first and read from the first message only.
    """
    result = sb.run_candidate(bodies.throwing_body, CHEAT_TASKS, tr.Isolation())
    # The body raised on every task and the limits are still reported, which can only be true if
    # the report did not depend on the body finishing.
    assert "filesystem_writes_permitted" in result["enforced"]
    assert all(row["outcome"] == "error" for row in result["outcomes"])


def test_a_lineage_cannot_reach_a_self_reported_verdict_by_forgetting_an_argument():
    """Labelling the difference is not refusing it. Saying so is the whole fix."""
    with pytest.raises(tr.TrustRootError, match="own account of itself"):
        Genesis(
            state=_seed_state(),
            body_factory=bodies.parent_body,
            budget=tr.Budget(limits={"generations": 2}),
            isolation=tr.Isolation(),
        )


def test_self_reported_outcomes_remain_available_to_a_caller_who_asks_for_them():
    """A refusal that cannot be overridden would forbid a legitimate setup rather than surface it."""
    genesis = _genesis(grade=None, allow_self_reported_outcomes=True)
    assert genesis.grade is None
    assert genesis.allow_self_reported_outcomes is True
