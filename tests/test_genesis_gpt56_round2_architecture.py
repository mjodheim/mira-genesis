"""Architecture-level counterexamples against the empirical-metamorphosis stopping criterion."""
from __future__ import annotations

import ast
from pathlib import Path

from genesis import development_bodies as bodies
from genesis import probe
from genesis import state as st
from genesis import trust_root as tr
from genesis.loop import Genesis, Proposal

ROOT = Path(__file__).resolve().parents[1]
LINEAGE = tr.provenance("lineage_owned", produced_by="lineage")
HOST = tr.provenance("host_written", produced_by="round-two architecture test")
TASKS = [{"task_id": "t%d" % index, "input": index} for index in range(8)]


def _seed_state():
    return st.create_state(
        body_digest="b0",
        components=[
            {
                "name": name,
                "origin": "seed",
                "certificate": None,
                "provenance": HOST,
            }
            for name in ("operator_table", "signal_interface")
        ],
        vocabulary=[
            {"name": "resolvable_by_%s" % name, "origin": "seed", "certificate": None}
            for name in ("operator_table", "signal_interface")
        ],
    )


def _genesis():
    return Genesis(
        state=_seed_state(),
        body_factory=bodies.parent_body,
        budget=tr.Budget(limits={"generations": 8, "probes": 5000}),
        isolation=tr.Isolation(),
        grade=bodies.grade,
    )


def _improved_proposal(*_):
    return Proposal(
        name="candidate",
        body_factory=bodies.improved_body,
        provenance=LINEAGE,
        rationale={"why": "control-policy counterexample"},
    )


def test_control_arm_policy_and_identity_are_part_of_the_evaluation_contract():
    """The same contract digest must not cover two decision rules with opposite verdicts."""
    without_control = _genesis()
    with_control = _genesis()

    accepted = without_control.cycle(TASKS, _improved_proposal)
    rejected = with_control.cycle(
        TASKS,
        _improved_proposal,
        control_factory=bodies.improved_body,
    )

    assert accepted["accepted"] is True
    assert rejected["accepted"] is False
    assert accepted["verdict"]["evaluation_contract_digest"] != rejected["verdict"][
        "evaluation_contract_digest"
    ]


def test_acquired_component_becomes_operational_without_host_editing_component_operations():
    """A certified component acquisition must make the certified demand resolvable by held machinery."""
    state = _seed_state()
    diagnosis = probe.diagnose_by_experiment(
        state,
        registry_reference=bodies.PROBE_REGISTRY,
        component_operations=bodies.COMPONENT_OPERATIONS,
        tasks=bodies.SPANNING_DEMAND,
        isolation=tr.Isolation(),
        budget=tr.Budget(limits={"probes": 1000}),
    )
    certificate = probe.certificate_from_experiment(
        diagnosis,
        new_component="joint_registry",
    )
    grown = st.extend_components(state, certificate=certificate, provenance=LINEAGE)

    repeated = probe.diagnose_by_experiment(
        grown,
        registry_reference=bodies.PROBE_REGISTRY,
        component_operations=bodies.COMPONENT_OPERATIONS,
        tasks=bodies.SPANNING_DEMAND,
        isolation=tr.Isolation(),
        budget=tr.Budget(limits={"probes": 1000}),
    )
    assert repeated["resolved_by"] == "joint_registry"
    assert repeated["registry_exhausted"] is False


def test_extended_vocabulary_is_used_by_later_measurements():
    """Adding a feature must change the executable diagnostic representation, not only its name list."""
    state = _seed_state()
    pair = probe.find_confusable_pair_by_experiment(
        state,
        [bodies.CONFUSABLE_A, bodies.CONFUSABLE_B],
        registry_reference=bodies.PROBE_REGISTRY,
        component_operations=bodies.COMPONENT_OPERATIONS,
        isolation=tr.Isolation(),
        budget=tr.Budget(limits={"probes": 3000}),
    )
    assert pair is not None
    certificate = probe.vocabulary_certificate_from_experiment(state, pair)
    grown = st.extend_vocabulary(state, certificate=certificate, provenance=LINEAGE)

    measurement = probe.measure(
        grown,
        bodies.CONFUSABLE_A,
        registry_reference=bodies.PROBE_REGISTRY,
        component_operations=bodies.COMPONENT_OPERATIONS,
        isolation=tr.Isolation(),
        budget=tr.Budget(limits={"probes": 2000}),
    )
    assert len(measurement["row"]) == len(st.vocabulary_names(grown))


def test_demonstration_does_not_orchestrate_lineage_state_transitions_from_the_host_script():
    """The stopping criterion requires one runtime loop, not a host script assigning lineage state."""
    path = ROOT / "scripts" / "run_genesis_demonstration.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))

    direct_state_assignments = []
    direct_journal_appends = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "genesis"
                    and target.attr == "state"
                ):
                    direct_state_assignments.append(target.lineno)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            owner = node.func.value
            if (
                node.func.attr == "append"
                and isinstance(owner, ast.Attribute)
                and isinstance(owner.value, ast.Name)
                and owner.value.id == "genesis"
                and owner.attr == "journal"
            ):
                direct_journal_appends.append(node.lineno)

    assert direct_state_assignments == []
    assert direct_journal_appends == []
