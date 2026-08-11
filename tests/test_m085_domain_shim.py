"""Regressions for the M085 organism-side shim.

The shim exists to answer one question early: does M084's organism transfer to a domain written
without reference to it? Building it found that `Embodiment` had abstracted only acting and
observing, while the organism still reached into M084's own carrier tables in ten places. These
tests hold that rerouting in place, and hold the wiring control honest about what it exercises.

The wiring control is project-written and is **not** a bank domain. Nothing here is evidence of
transfer.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from metamorphosis.m084_persistent_lineage import (
    ACTION_BUDGET_PER_STAGE,
    SUBSTRATES,
    Embodiment,
    LineageError,
    Organism,
    _new_metrics,
    pursue,
    view_for,
)
from metamorphosis.m085_cross_domain_intake import ADAPTER_CONTRACT_VERSION
from metamorphosis.m085_domain_shim import (
    ACTION_KINDS,
    REQUIRED_PROBE_ROLES,
    DomainContractError,
    DomainDescription,
    ExternalEmbodiment,
    goals_from_domain,
    view_from_description,
)
from metamorphosis.m085_wiring_control import (
    CARRIER_COSTS,
    DISCARDING_SLOTS,
    WiringControlDomain,
    expected_shape,
    wiring_tasks,
)

ROOT = Path(__file__).resolve().parents[1]
SALT = bytes.fromhex("5a" * 32)


def _description() -> DomainDescription:
    return WiringControlDomain().describe()


# -- M084's own substrates still work through the same interface --------------------------------

def test_m084_substrates_register_views_built_from_their_own_tables() -> None:
    for substrate in SUBSTRATES:
        view = view_for(substrate)
        assert view.key == substrate
        assert view.costs, "a native view must supply carrier costs"
        assert view.carrier_index, "a native view must supply memory keys"
    assert view_for("desktop").observes_one_carrier_at_a_time is True
    assert view_for("shell").observes_one_carrier_at_a_time is False


def test_an_unregistered_domain_is_refused_rather_than_guessed() -> None:
    with pytest.raises(LineageError, match="no domain view is registered"):
        view_for("a-domain-nobody-declared")


def test_the_embodiment_budget_defaults_to_the_frozen_m084_bound() -> None:
    class _Stub:
        def state(self) -> dict:
            return {}

    assert Embodiment(_Stub(), "shell").action_budget == ACTION_BUDGET_PER_STAGE


# -- the contract ---------------------------------------------------------------------------------

def test_a_conforming_description_yields_a_usable_view() -> None:
    view = view_from_description("some-domain", 0, _description())
    assert view.costs == CARRIER_COSTS
    assert set(view.carrier_index) == set(CARRIER_COSTS)
    assert view.carrier_for(0, "probe_aff") == "slot6"
    assert view.value_for(SALT, 0, 800) in _description().values


def test_a_description_naming_the_wrong_contract_is_refused() -> None:
    description = DomainDescription(
        contract_version="m085-domain-adapter-v99",
        carriers={"a": 1}, values=("x",),
        probe_carriers={role: "a" for role in REQUIRED_PROBE_ROLES},
    )
    with pytest.raises(DomainContractError, match="drives"):
        description.validate()


def test_a_description_missing_a_probe_carrier_is_refused() -> None:
    """The organism probes with these and cannot invent them; M084 read them from its own table."""

    probes = {role: "a" for role in REQUIRED_PROBE_ROLES}
    del probes["probe_aff"]
    description = DomainDescription(
        contract_version=ADAPTER_CONTRACT_VERSION,
        carriers={"a": 1}, values=("x",), probe_carriers=probes,
    )
    with pytest.raises(DomainContractError, match="probe_aff"):
        description.validate()


def test_a_probe_carrier_outside_the_declared_carriers_is_refused() -> None:
    description = DomainDescription(
        contract_version=ADAPTER_CONTRACT_VERSION,
        carriers={"a": 1}, values=("x",),
        probe_carriers={role: "elsewhere" for role in REQUIRED_PROBE_ROLES},
    )
    with pytest.raises(DomainContractError, match="not among the declared carriers"):
        description.validate()


def test_carriers_need_positive_costs_and_a_value_alphabet() -> None:
    probes = {role: "a" for role in REQUIRED_PROBE_ROLES}
    with pytest.raises(DomainContractError, match="positive cost"):
        DomainDescription(
            contract_version=ADAPTER_CONTRACT_VERSION,
            carriers={"a": 0}, values=("x",), probe_carriers=probes,
        ).validate()
    with pytest.raises(DomainContractError, match="value alphabet"):
        DomainDescription(
            contract_version=ADAPTER_CONTRACT_VERSION,
            carriers={"a": 1}, values=(), probe_carriers=probes,
        ).validate()


def test_an_unknown_action_kind_is_refused() -> None:
    domain = WiringControlDomain()
    embodiment = ExternalEmbodiment(domain, context=0)
    assert set(ACTION_KINDS) == {"put", "remove", "read", "list"}
    with pytest.raises(DomainContractError, match="unknown action"):
        embodiment.act("detonate", "slot0", "amber")


def test_goals_from_domain_rejects_a_malformed_task() -> None:
    with pytest.raises(DomainContractError, match="missing"):
        goals_from_domain("d", 0, [{"requirement": "durable", "group": ("a",)}])
    with pytest.raises(DomainContractError, match="unknown requirement"):
        goals_from_domain(
            "d", 0, [{"requirement": "wish", "group": ("a",), "value": "v", "reachable": True}],
        )
    with pytest.raises(DomainContractError, match="names no carriers"):
        goals_from_domain(
            "d", 0, [{"requirement": "durable", "group": (), "value": "v", "reachable": True}],
        )


def test_the_organism_never_sees_reachability() -> None:
    goals = goals_from_domain("d", 0, wiring_tasks())
    for goal in goals:
        assert "reachable" not in goal.redacted()


# -- the wiring control ---------------------------------------------------------------------------

def test_the_wiring_control_looks_nothing_like_m084() -> None:
    """A control sharing M084's vocabulary would prove the shim works on M084 twice."""

    description = _description()
    assert not any(name.startswith("sealed-") for name in description.carriers)
    assert not any(name.startswith("secure-") for name in description.carriers)
    assert not any(name.startswith("r") and "c" in name for name in description.carriers)
    assert set(description.values).isdisjoint({"cyan", "magenta", "lime"})


def test_the_trap_is_the_cheapest_carrier_of_the_repair_group() -> None:
    """The defect the first version of this control had: the planner walked around the trap."""

    repair = wiring_tasks()[0]
    group = list(repair["group"])  # type: ignore[arg-type]
    cheapest = min(group, key=lambda name: CARRIER_COSTS[name])
    assert cheapest in DISCARDING_SLOTS
    assert CARRIER_COSTS[cheapest] < min(
        CARRIER_COSTS[name] for name in group if name not in DISCARDING_SLOTS
    )


def test_the_organism_drives_the_external_domain_end_to_end() -> None:
    domain = WiringControlDomain()
    goals = goals_from_domain(domain.domain_id, 0, wiring_tasks())
    organism = Organism.genesis(SALT)
    organism.policy["verification"] = "per_goal"
    embodiment = ExternalEmbodiment(domain, context=0)
    metrics = _new_metrics()
    domain.act("put", "slot4", "rust")

    outcomes = [
        pursue(
            organism, goal.redacted(), embodiment, domain.domain_id, 0, metrics, SALT,
            verify=True,
        )
        for goal in goals
    ]
    shape = expected_shape()

    reached = sum(
        1 for goal, outcome in zip(goals, outcomes)
        if goal.reachable and domain.evaluate(goal.group, goal.requirement, goal.value)
    )
    assert reached == shape["reachable_goals"]
    assert sum(1 for o in outcomes if o.outcome == "refused") == shape["unreachable_goals"]
    assert not [
        goal for goal, outcome in zip(goals, outcomes)
        if outcome.outcome == "refused" and goal.reachable
    ]
    assert metrics["diagnostic_probes"] >= shape["minimum_diagnostic_probes"]
    assert metrics["repair_cycles"] >= shape["minimum_repair_cycles"]


def test_the_organism_induces_a_predicate_in_the_external_domain() -> None:
    """Its bounded memory must key on this domain, not fall back to an M084 substrate."""

    domain = WiringControlDomain()
    organism = Organism.genesis(SALT)
    organism.policy["verification"] = "per_goal"
    embodiment = ExternalEmbodiment(domain, context=0)
    metrics = _new_metrics()
    for goal in goals_from_domain(domain.domain_id, 0, wiring_tasks()):
        pursue(
            organism, goal.redacted(), embodiment, domain.domain_id, 0, metrics, SALT,
            verify=True,
        )
    assert organism.predicates.get(domain.domain_id) is not None
    assert organism.memory.used() > 0
    for substrate in SUBSTRATES:
        assert substrate not in organism.predicates


def test_the_shim_reuses_the_organism_rather_than_writing_a_second_one() -> None:
    tree = ast.parse((ROOT / "metamorphosis/m085_domain_shim.py").read_text(encoding="utf-8"))
    imported = {
        alias.name for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module == "metamorphosis.m084_persistent_lineage"
        for alias in node.names
    }
    assert {"Embodiment", "Goal", "DomainView"} <= imported
    defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    assert "Organism" not in defined, "the point of M085 is whether *that* organism transfers"


def test_the_wiring_control_declares_itself_non_scientific() -> None:
    for path in (
        ROOT / "metamorphosis/m085_wiring_control.py",
        ROOT / "scripts/run_m085_wiring_control.py",
    ):
        text = path.read_text(encoding="utf-8")
        assert "not" in text.lower() and "evidence" in text.lower()
    assert WiringControlDomain.domain_id == "wiring-control-not-a-bank-domain"


def test_a_genuine_key_collision_is_still_refused() -> None:
    """Idempotence must not become 'last writer wins' for two different domains."""

    from metamorphosis.m084_persistent_lineage import register_domain_view

    first = view_from_description("colliding-domain", 0, _description())
    register_domain_view(first)
    register_domain_view(view_from_description("colliding-domain", 0, _description()))

    other = DomainDescription(
        contract_version=ADAPTER_CONTRACT_VERSION,
        carriers={"a": 1, "b": 2}, values=("x",),
        probe_carriers={role: "a" for role in REQUIRED_PROBE_ROLES},
    )
    with pytest.raises(LineageError, match="already registered"):
        register_domain_view(view_from_description("colliding-domain", 0, other))
