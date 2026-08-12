"""Three materially different situations in which the evidence does not determine the answer.

Each family gives M047's frozen diagnosis a limitation it recognises, and M047's frozen generator
a candidate set in which **two candidates pass every public case**. The families differ in what is
ambiguous, not in degree:

* **tool semantics** — a missing route. `mean` and `midpoint` coincide on `mean 1 2 3` because
  `2b = a + c` makes the average and the endpoint-midpoint equal. This is the exact draw that made
  M086-C negative, and it is reused as the *development* limitation so the acquisition is provoked
  by the failure that motivated the milestone rather than by a fresh convenience.
* **interpretation routing** — an unknown token. Routing it to `add` or to `mul` is
  indistinguishable on `2 2`, because addition and multiplication agree on that argument.
* **planning structure** — a nested request the founder's planner refuses. `one_level` and
  `recursive_postorder` both plan a depth-two request; they differ only at depth three, where
  `one_level` raises.

Nothing in the mechanism knows any of that. The discriminating request is not marked, not ordered
first and not referenced anywhere outside this module's *truth*, which only the evaluator reads.
The experiment space is the same kind of object in all three families — a bounded set of request
strings — and the observation is the same operation: run the reference source and read what came
back.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from metamorphosis.m047_software_core import SoftwareCase, SourceModule
from metamorphosis.m047_software_model import SoftwareBody
from metamorphosis.m047_software_pipeline import (
    render_allocation,
    render_critique,
    render_execution,
    render_interpretation,
    render_orchestration,
    render_planning,
    render_selection,
)
from metamorphosis.m047_software_tools import render_tool_core, render_tool_module
from metamorphosis.m087_evidence import EvidenceSpaces


FAMILIES = ("tool_semantics", "interpretation_routing", "planning_structure")


class FamilyError(RuntimeError):
    """Raised when a family definition would not actually be ambiguous."""


def _body(
    *, aliases: Mapping[str, str], routes: Mapping[str, str], planning: str,
    extra: Sequence[SourceModule] = (),
) -> SoftwareBody:
    modules = [
        SourceModule("allocation", render_allocation("plan_length")),
        SourceModule("critique", render_critique("identity")),
        SourceModule("execution", render_execution()),
        SourceModule("interpretation", render_interpretation(dict(aliases))),
        SourceModule("orchestration", render_orchestration()),
        SourceModule("planning", render_planning(planning)),
        SourceModule("selection", render_selection(dict(routes))),
        SourceModule("tool_core", render_tool_core()),
        *extra,
    ]
    return SoftwareBody(tuple(sorted(modules, key=lambda item: item.name)))


@dataclass(frozen=True)
class Family:
    """One ambiguous situation, with its own body, evidence and disjoint hidden domain."""

    family_id: str
    module: str
    starting_body: SoftwareBody
    reference_body: SoftwareBody
    public_cases: tuple[SoftwareCase, ...]
    hidden_cases: tuple[SoftwareCase, ...]
    acquirable_requests: tuple[str, ...]
    # Evaluator-side only. Never read by the mechanism, the policy or any arm.
    truth_label_fragment: str
    equivalent_label_fragment: str

    @property
    def spaces(self) -> EvidenceSpaces:
        return EvidenceSpaces(
            self.acquirable_requests,
            tuple(case.request for case in self.hidden_cases),
        )

    def to_public_dict(self) -> dict[str, object]:
        """What may be recorded publicly before the hidden evaluation runs."""

        return {
            "family_id": self.family_id,
            "module": self.module,
            "public_case_ids": [case.case_id for case in self.public_cases],
            "hidden_case_count": len(self.hidden_cases),
            "experiment_space_size": len(self.acquirable_requests),
            "starting_body_digest": self.starting_body.digest(),
            "experiment_space_digest": self.spaces.digest(),
        }


def tool_semantics_family() -> Family:
    """`mean` is unrouted. `mean` and `midpoint` agree on an arithmetic progression."""

    aliases = {"add": "add", "mean": "mean", "mul": "mul"}
    starting = _body(aliases=aliases, routes={"add": "add", "mul": "mul"}, planning="one_level")
    reference = _body(
        aliases=aliases, routes={"add": "add", "mul": "mul", "mean": "mean"},
        planning="one_level",
        extra=(SourceModule("tool_mean", render_tool_module("mean", "mean")),),
    )
    return Family(
        family_id="tool_semantics",
        module="selection",
        starting_body=starting,
        reference_body=reference,
        # 2*2 == 1+3, so the average and the endpoint midpoint are both 2.0.
        public_cases=(SoftwareCase("tool_public_progression", "mean 1 2 3", 2.0, "public"),),
        hidden_cases=(
            SoftwareCase("tool_hidden_skew", "mean 2 3 10", 5.0, "hidden"),
            SoftwareCase("tool_hidden_tail", "mean 4 4 10", 6.0, "hidden"),
        ),
        acquirable_requests=(
            "mean 1 2 3", "mean 0 0 0", "mean 5 5 5", "mean 1 2 6",
            "mean 2 2 8", "mean 3 9 12", "add 1 1", "mul 2 3",
        ),
        truth_label_fragment="mean",
        equivalent_label_fragment="midpoint",
    )


def interpretation_routing_family() -> Family:
    """An unknown token. Routing it to `add` or `mul` is indistinguishable on `2 2`."""

    aliases = {"add": "add", "mul": "mul"}
    starting = _body(aliases=aliases, routes={"add": "add", "mul": "mul"}, planning="one_level")
    reference = _body(
        aliases={**aliases, "combine": "add"}, routes={"add": "add", "mul": "mul"},
        planning="one_level",
    )
    return Family(
        family_id="interpretation_routing",
        module="interpretation",
        starting_body=starting,
        reference_body=reference,
        # 2 + 2 == 2 * 2, so addition and multiplication agree here and nowhere useful else.
        public_cases=(SoftwareCase("routing_public_fixpoint", "combine 2 2", 4, "public"),),
        hidden_cases=(
            SoftwareCase("routing_hidden_sum", "combine 7 5", 12, "hidden"),
            SoftwareCase("routing_hidden_zero", "combine 9 0", 9, "hidden"),
        ),
        acquirable_requests=(
            "combine 2 2", "combine 0 0", "combine 1 1", "combine 2 3",
            "combine 4 6", "combine 3 0", "add 1 1", "mul 2 3",
        ),
        truth_label_fragment="add",
        equivalent_label_fragment="mul",
    )


def planning_structure_family() -> Family:
    """A nested request. `one_level` and `recursive_postorder` agree at depth two only."""

    aliases = {"add": "add", "mul": "mul"}
    starting = _body(aliases=aliases, routes={"add": "add", "mul": "mul"}, planning="root_only")
    reference = _body(
        aliases=aliases, routes={"add": "add", "mul": "mul"}, planning="recursive_postorder",
    )
    return Family(
        family_id="planning_structure",
        module="planning",
        starting_body=starting,
        reference_body=reference,
        public_cases=(SoftwareCase("planning_public_depth_two", "add 1 add 2 3", 6, "public"),),
        hidden_cases=(
            SoftwareCase("planning_hidden_depth_three", "add 1 add 2 add 3 4", 10, "hidden"),
            SoftwareCase("planning_hidden_deep_mul", "mul 2 add 1 add 1 1", 6, "hidden"),
        ),
        # `add 1 add 2 add 3 4` is deliberately ABSENT: it is a hidden case, and an experiment
        # space containing it would let acquisition read the evaluation set verbatim. The first
        # draft of this family did contain it and `assert_domains_disjoint` refused to build the
        # family at all, which is the check working rather than a rule being remembered.
        acquirable_requests=(
            "add 1 add 2 3", "add 0 add 0 0", "mul 2 add 1 2", "add 5 add 6 add 7 8",
            "mul 3 mul 1 mul 1 2", "add 5 5", "mul 2 3", "add 2 add 2 2",
        ),
        truth_label_fragment="recursive_postorder",
        equivalent_label_fragment="one_level",
    )


# --------------------------------------------------------------------------------------------
# qualification materialization
# --------------------------------------------------------------------------------------------
#
# M086-A was disqualified partly because its holdout existed as module constants before the
# meta-search ran, so the promised chronology was replaced by a source-text absence check. The
# hidden cases above are DEVELOPMENT cases. The qualifying ones are drawn here from a salt that is
# revealed only after the adopted policy has been committed by digest.
#
# One rule governs the draw and it is not truth-dependent: a hidden case must DISCRIMINATE the
# candidates that the public evidence leaves equivalent. A case both survivors pass measures
# nothing about selection, so admitting one would make the arm's correctness unmeasurable. Whether
# a case discriminates is a property of the candidate pair, computable without knowing which
# candidate is correct.

QUALIFICATION_POOL: Mapping[str, tuple[tuple[str, object], ...]] = {
    "tool_semantics": (
        ("mean 2 3 10", 5.0), ("mean 4 4 10", 6.0), ("mean 1 1 7", 3.0),
        ("mean 0 6 6", 4.0), ("mean 3 3 12", 6.0), ("mean 2 8 8", 6.0),
    ),
    "interpretation_routing": (
        ("combine 7 5", 12), ("combine 9 0", 9), ("combine 3 4", 7),
        ("combine 6 1", 7), ("combine 8 5", 13), ("combine 2 9", 11),
    ),
    "planning_structure": (
        ("add 1 add 2 add 3 4", 10), ("mul 2 add 1 add 1 1", 6),
        ("add 9 add 8 add 7 6", 30), ("mul 3 add 2 add 1 1", 12),
        ("add 4 add 4 add 4 4", 16), ("mul 2 mul 2 mul 2 2", 16),
    ),
}


def materialize_qualification(family_id: str, salt: str, count: int = 2) -> tuple[SoftwareCase, ...]:
    """Draw this family's qualifying hidden cases from a post-adoption salt.

    Deterministic in the salt, so the draw is reproducible and auditable, and unknowable before
    the salt is released.
    """

    import hashlib

    pool = QUALIFICATION_POOL[family_id]
    order = sorted(
        range(len(pool)),
        key=lambda index: hashlib.sha256(
            f"m087-qualification-v1\0{family_id}\0{salt}\0{index}".encode("utf-8")
        ).hexdigest(),
    )
    drawn = order[:count]
    return tuple(
        SoftwareCase(f"{family_id}_qual_{position}", pool[index][0], pool[index][1], "hidden")
        for position, index in enumerate(sorted(drawn))
    )


def qualified_family(family_id: str, salt: str) -> Family:
    """The family with its hidden cases replaced by the post-adoption draw."""

    base = family(family_id)
    drawn = materialize_qualification(family_id, salt)
    from dataclasses import replace as _replace

    return _replace(base, hidden_cases=drawn)


def family(family_id: str) -> Family:
    builders = {
        "tool_semantics": tool_semantics_family,
        "interpretation_routing": interpretation_routing_family,
        "planning_structure": planning_structure_family,
    }
    if family_id not in builders:
        raise FamilyError(f"unknown family {family_id!r}")
    return builders[family_id]()


def all_families() -> tuple[Family, ...]:
    return tuple(family(name) for name in FAMILIES)


__all__ = [
    "FAMILIES", "Family", "FamilyError", "all_families", "family",
    "interpretation_routing_family", "planning_structure_family", "tool_semantics_family",
]
