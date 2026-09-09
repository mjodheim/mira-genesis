"""Fixtures for the endogenous-search frontier. Apparatus, not science.

The world these build admits **no body artifacts at all**. That is the whole point: a lineage here
cannot select a descendant, because there is none to select. Anything it adopts, the runtime had to
construct.
"""
from __future__ import annotations

from typing import Any, Mapping

from genesis import controller
from genesis import development_bodies as bodies

#: Questions whose right answer is `input * 2 + 1` — reachable by `double` then `increment` over the
#: probe alphabet, and not by any single operation in it. The seed body answers none of them.
SEARCH_TASKS = [
    {"task_id": "q%d" % index, "input": index, "expected": index * 2 + 1} for index in range(6)
]

#: The operations the host admits for this search. The alphabet is the host's; the sentence is not.
SEARCH_ALPHABET = ("increment", "double", "triple", "negate")


def seed_body() -> Any:
    """A parent that already answers one question.

    A parent that answered *nothing* would make the search trivial: the first candidate to get a
    single task right would strictly improve on it and be adopted, and what the run demonstrated
    would be the trust root accepting an improvement rather than a search finding a body. This seed
    solves `q0`, so a candidate has to beat it — and one that answers other questions while losing
    `q0` is refused by retention rather than traded for.
    """
    return bodies.TableBody({"q0"})


def graded_against_expected(task: Mapping[str, Any], answer: Any) -> str:
    """Host-side grading. The candidate never sees `expected` — the sandbox withholds it."""
    return "solved" if answer == task.get("expected") else "unsolved"


def search_world() -> controller.World:
    return controller.world(
        tasks=SEARCH_TASKS,
        demands={},
        substrates={},
        probe_registry=bodies.PROBE_REGISTRY,
        component_operations={"operator_table": list(SEARCH_ALPHABET)},
        # Deliberately empty. There is nothing here to choose.
        artifacts={},
        grade=graded_against_expected,
    )


def search_then_stop(context) -> Any:
    """Search until something is adopted, then stop.

    A lookup rather than a strategy, and the frontier this closes is not strategy: it is that the
    body which gets adopted did not exist when the run began.
    """
    if context.acquisitions:
        return controller.Stop(reason="a constructed descendant was adopted")
    return controller.SearchTransform(
        name="constructed",
        max_candidates=25,
        max_nodes=3,
        operations=SEARCH_ALPHABET,
        rationale={"why": "the parent answers only the first of these questions"},
    )


def search_once_then_stop(context) -> Any:
    """One search cut short by its own bound, to check the bound is what stops it."""
    if context.observations or context.acquisitions:
        return controller.Stop(reason="the bounded search is spent")
    return controller.SearchTransform(
        name="bounded", max_candidates=2, max_nodes=2, operations=SEARCH_ALPHABET
    )


def search_an_alphabet_that_cannot_reach_it(context) -> Any:
    """A search over operations that cannot express the answer. The negative must be reachable."""
    if context.observations or context.acquisitions:
        return controller.Stop(reason="nothing in this alphabet reaches the demand")
    return controller.SearchTransform(
        name="unreachable", max_candidates=8, max_nodes=3, operations=("negate",)
    )


# ---------------------------------------------------------------------------------------------
# Two acquisition policies, so a policy update can be judged by what each one produces
# ---------------------------------------------------------------------------------------------
#
# `timid_policy` searches an alphabet that cannot reach the demand. `bolder_policy` searches the one
# that can. Neither is told which is which, and neither grades anything: the trust root compares the
# descendants each one actually produced. That is the whole point of the transaction — a policy is
# adopted for what it caused, not for what it claims.


def timid_policy(context) -> Any:
    """The incumbent. It looks only where the answer is not."""
    if context.acquisitions:
        return controller.Stop(reason="nothing further under this policy")
    return controller.SearchTransform(
        name="timid", max_candidates=6, max_nodes=3, operations=("negate",)
    )


def bolder_policy(context) -> Any:
    """The candidate. Same runtime, same evaluator, a wider place to look."""
    if context.acquisitions:
        return controller.Stop(reason="a descendant was adopted")
    return controller.SearchTransform(
        name="bolder", max_candidates=25, max_nodes=3, operations=SEARCH_ALPHABET
    )


def adopt_the_bolder_policy(context) -> Any:
    """Ask once for the machinery change, then run under whatever the evidence licensed."""
    if any(name == "bolder" for name in context.acquisitions):
        return controller.Stop(reason="running under the adopted policy")
    if context.mechanism_artifact_digest and not context.observations:
        return controller.AdoptPolicy(
            candidate="bolder",
            steps=2,
            rationale={"why": "the incumbent's descendants answer nothing"},
        )
    return controller.Stop(reason="the policy question has been settled")


def policy_world() -> controller.World:
    here = search_world()
    return controller.world(
        tasks=here.tasks,
        demands=here.demands,
        substrates=here.substrates,
        probe_registry=here.probe_registry,
        component_operations=here.component_operations,
        artifacts=here.artifacts,
        grade=here.grade,
        policies={
            "timid": "genesis.search_fixtures:timid_policy",
            "bolder": "genesis.search_fixtures:bolder_policy",
        },
    )
