#!/usr/bin/env python3
"""Drive one Genesis lineage through the whole metamorphosis cycle and emit a reproducible record.

This is the DEVELOPMENT demonstration the stopping criterion in
``docs/METAMORPHOSIS_TARGET.md`` asks for: not that the components exist, but that **one lineage**
does all of it. It is not a scientific result, it is not frozen, and it advances no gate. Every
mechanism it exercises is already qualified in a bounded setting; what is new is that they run as one
program.

The lineage, in order:

1. measures itself against a task family in an isolated child process;
2. proposes a transformation, has it rejected on evidence, and **keeps going**;
3. proposes another, has it accepted, and records the acquisition;
4. measures two demands its features read identically whose causes differ, and **extends its own
   diagnostic vocabulary** against that measured pair, taking the separating feature out of the
   measurements rather than choosing it and justifying it afterwards;
5. meets a demand no component in its registry resolves, **composes and runs probes** until it has
   exhausted what its components can express, finds that something outside them does resolve it,
   and **names a component class it did not have** — against a certificate, not by editing a tuple;
6. discovers a second substrate by probing, migrates into it carrying everything it owned;
7. **evolves again in the new form**, which is the only thing that distinguishes transported
   intelligence from transported output;
8. dies, and comes back from disk with the same state digest and the same journal head.

Run it with ``--write`` to persist the record under ``experiments/GENESIS/``.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from genesis import development_bodies as bodies  # noqa: E402
from genesis import probe  # noqa: E402
from genesis import state as lineage_state  # noqa: E402
from genesis import trust_root as tr  # noqa: E402
from genesis.loop import Genesis, Proposal, ablation_supports_causal_dependency  # noqa: E402
from genesis.sandbox import run_candidate  # noqa: E402
from genesis.migration import (  # noqa: E402
    Substrate,
    discover,
    metamorphosis_succeeded,
    migrate,
)

RECORD_PATH = ROOT / "experiments" / "GENESIS" / "DEMONSTRATION_RECORD.json"
TASKS = [{"task_id": "t%d" % index} for index in range(4)]
LINEAGE = tr.provenance("lineage_owned", produced_by="lineage")

def _seed_state() -> dict:
    return lineage_state.create_state(
        body_digest="s0",
        components=[
            {
                "name": name,
                "origin": "seed",
                "certificate": None,
                "provenance": tr.provenance("host_written", produced_by="seed"),
            }
            for name in ("operator_table", "signal_interface")
        ],
        # One feature per held component: "can a composition over this component's own operations
        # resolve the demand". Naming them after what they measure is what lets the row be read by
        # experiment instead of asserted.
        vocabulary=[
            {"name": "resolvable_by_%s" % name, "origin": "seed", "certificate": None}
            for name in ("operator_table", "signal_interface")
        ],
    )


def _proposal(name, factory):
    return Proposal(name=name, body_factory=factory, provenance=LINEAGE, rationale={"step": name})


def _one(genesis, name, factory):
    queue = [factory]
    return genesis.cycle(
        TASKS,
        lambda _g, _t: _proposal(name, queue.pop(0)) if queue else None,
    )


def causal_step(*, candidate_sandbox, parent_sandbox, ablated_sandbox) -> dict:
    """Assemble the causal-dependency claim, and refuse it when the ablation removed nothing.

    Two things have to hold and they are not the same. The measured loss says the later generation
    solved less without the acquisition. The distinctness check says the ablated arm is not simply
    the parent arm wearing another name — because if it is, the comparison repeats the verdict that
    accepted the candidate in the first place and adds no evidence at all.

    Kept as a function so a test can hand it an arm that never depended on the acquisition and
    watch it refuse. A check that cannot return `False` is not a check.
    """
    causal = ablation_supports_causal_dependency(
        with_acquisition=candidate_sandbox["outcomes"],
        without_acquisition=ablated_sandbox["outcomes"],
        equal_budget=True,
    )
    distinct = ablated_sandbox["result_digest"] != parent_sandbox["result_digest"]
    causal["ablated_arm_ran_separately"] = ablated_sandbox["completed"]
    causal["ablated_arm_differs_from_the_parent_arm"] = distinct
    causal["establishes_causal_dependency"] = bool(
        causal["supported"] and distinct and ablated_sandbox["completed"]
    )
    causal["why_not"] = (
        ""
        if causal["establishes_causal_dependency"]
        else "the ablated arm is behaviourally identical to the parent arm, so removing the "
        "acquisition cost nothing the verdict had not already measured"
    )
    # Stated, not checked: which body was ablated is a property of how the arm was built, and a
    # boolean written here would only be this runner agreeing with itself. The test suite compares
    # the two bodies field by field instead.
    causal["ablated_arm_construction"] = (
        "genesis.development_bodies.migrated_ablated_body: the accepted candidate with the "
        "acquired component removed and nothing else changed"
    )
    causal["fixture_not_evidence"] = (
        "these are development fixtures; this shows the runtime can hold and refuse a causal "
        "claim, not that any real mechanism has one"
    )
    return causal


def demonstrate() -> dict:
    genesis = Genesis(
        state=_seed_state(),
        body_factory=bodies.parent_body,
        budget=tr.Budget(limits={"generations": 8, "probes": 2000}),
        isolation=tr.Isolation(),
    )
    steps: list[dict] = []

    rejected = _one(genesis, "regressed", bodies.regressed_body)
    steps.append(
        {
            "step": "rejected_candidate_does_not_end_the_run",
            "accepted": rejected["accepted"],
            "reason": rejected["reason"],
            "observations_kept": len(genesis.state["observations"]),
        }
    )

    accepted = _one(genesis, "improved", bodies.improved_body)
    steps.append(
        {
            "step": "candidate_accepted_on_evidence",
            "accepted": accepted["accepted"],
            "generation": genesis.state["generation"],
            "acquisitions": len(genesis.state["acquisitions"]),
        }
    )

    # The confusable pair is measured, not declared. Both demands read identically through the
    # lineage's per-component vocabulary — neither component resolves either — and their causes
    # differ, which is read off which component each resolving composition mostly lives in. The
    # separating feature is then taken out of the measurements rather than chosen and justified.
    pair = probe.find_confusable_pair_by_experiment(
        genesis.state,
        [bodies.CONFUSABLE_A, bodies.CONFUSABLE_B],
        registry_reference=bodies.PROBE_REGISTRY,
        component_operations=bodies.COMPONENT_OPERATIONS,
        isolation=genesis.isolation,
        budget=genesis.budget,
    )
    vocabulary_certificate = probe.vocabulary_certificate_from_experiment(genesis.state, pair)
    genesis.state = lineage_state.extend_vocabulary(
        genesis.state, certificate=vocabulary_certificate
    )
    genesis.journal.append(
        "vocabulary_extended",
        genesis.state["generation"],
        {"feature": vocabulary_certificate["new_feature"]},
    )
    steps.append(
        {
            "step": "lineage_extends_its_own_diagnostic_vocabulary",
            "shared_prior_row": pair["shared_prior_row"],
            "limiting_components": pair["limiting_components"],
            "resolving_operations": [
                measurement["resolving_operations"] for measurement in pair["measurements"]
            ],
            "feature_read_out_of_the_measurements": vocabulary_certificate["new_feature"],
            "vocabulary_after": lineage_state.vocabulary_names(genesis.state),
            "rests_on_a_host_supplied_oracle": False,
        }
    )

    # The probes are composed and run, not consulted. Nothing here answers "does this component
    # resolve the demand" — compositions are built, executed in isolation, and the verdict is read
    # off raw per-task outcomes. The host supplied the operations and the tasks; it did not and
    # could not supply the finding.
    found = probe.diagnose_by_experiment(
        genesis.state,
        registry_reference=bodies.PROBE_REGISTRY,
        component_operations=bodies.COMPONENT_OPERATIONS,
        tasks=bodies.SPANNING_DEMAND,
        isolation=genesis.isolation,
        budget=genesis.budget,
    )
    certificate = probe.certificate_from_experiment(found, new_component="joint_registry")
    genesis.state = lineage_state.extend_components(
        genesis.state, certificate=certificate, provenance=LINEAGE
    )
    genesis.journal.append(
        "component_acquired",
        genesis.state["generation"],
        {"component": "joint_registry", "certificate_digest": certificate["certificate_digest"]},
    )
    steps.append(
        {
            "step": "lineage_names_a_component_class_it_did_not_have",
            "registry_exhausted": found["registry_exhausted"],
            "probed": [record["component"] for record in found["probes"]],
            "compositions_run": sum(record["attempts"] for record in found["probes"]),
            # Exhaustion alone is a failed search. This is the half that makes it a finding about
            # the lineage's representation.
            "reachable_with_wider_operations": found["reachable_with_wider_operations"],
            "composition_the_lineage_found": found["resolving_composition"]["operations"],
            "probe_is_experimental_not_an_oracle": True,
            "registry_after": lineage_state.component_names(genesis.state),
        }
    )

    substrate = Substrate(name="record-store", operations=bodies.SUBSTRATE_OPERATIONS)
    probing = discover(substrate, ["read", "write", "list", "transact"], genesis.budget)
    migration = migrate(
        genesis,
        substrate,
        lambda state, operations: bodies.migrated_parent_body,
        used_operations=["read"],
    )
    steps.append(
        {
            "step": "substrate_semantics_discovered_then_migrated",
            "found": probing["found"],
            "missing": probing["missing"],
            "journal_continues": migration["journal_continues"],
            "nothing_lost": all(c["missing"] == 0 for c in migration["carried"].values()),
        }
    )

    after = [_one(genesis, "improved_in_new_form", bodies.migrated_improved_body)]
    outcome = metamorphosis_succeeded(migration, after)
    steps.append(
        {
            "step": "evolved_again_in_the_new_form",
            "metamorphosis_succeeded": outcome["succeeded"],
            "accepted_after_migration": outcome["accepted_after_migration"],
            "transported_intelligence": outcome[
                "is_transported_intelligence_rather_than_transported_output"
            ],
        }
    )

    # A real ablation, not the verdict relabelled. The earlier acquisition is removed and the later
    # generation is retried at the same budget in its own isolated run; comparing the candidate with
    # its parent would only repeat the comparison the verdict already made.
    ablated = run_candidate(
        bodies.migrated_ablated_body, TASKS, genesis.isolation,
        admitted_isolation=genesis.admitted_isolation,
    )
    causal = causal_step(
        candidate_sandbox=after[0]["candidate_sandbox"],
        parent_sandbox=after[0]["parent_sandbox"],
        ablated_sandbox=ablated,
    )
    steps.append({"step": "causal_dependency_between_generations", **causal})

    directory = ROOT / "experiments" / "GENESIS" / "runtime_state"
    genesis.persist(directory)
    restored = Genesis.restore(
        directory,
        body_factory=bodies.migrated_improved_body,
        budget=tr.Budget(limits={"generations": 8, "probes": 2000}),
        isolation=tr.Isolation(),
    )
    steps.append(
        {
            "step": "survives_process_death",
            "state_digest_matches": restored.state["state_digest"]
            == genesis.state["state_digest"],
            "journal_head_matches": restored.journal.head == genesis.journal.head,
            "journal_length": len(restored.journal),
        }
    )

    record = {
        "schema": "genesis-demonstration-v1",
        "development": True,
        "is_a_scientific_observation": False,
        "advances_a_generality_gate": False,
        "frozen": False,
        "steps": steps,
        "journal_kinds": [entry["kind"] for entry in genesis.journal],
        "final_generation": genesis.state["generation"],
        "final_components": lineage_state.component_names(genesis.state),
        "final_vocabulary": lineage_state.vocabulary_names(genesis.state),
        "budget": genesis.budget.record(),
        "trust_root_sha256": tr.source_digest(),
    }
    record["record_digest"] = tr.digest_of(record)
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="persist the demonstration record")
    arguments = parser.parse_args()
    record = demonstrate()
    if arguments.write:
        RECORD_PATH.parent.mkdir(parents=True, exist_ok=True)
        RECORD_PATH.write_bytes(tr.canonical_bytes(record) + b"\n")
        print("wrote %s" % RECORD_PATH.relative_to(ROOT))
    for step in record["steps"]:
        print("  %-52s %s" % (step["step"], {k: v for k, v in step.items() if k != "step"}))
    print(json.dumps({k: record[k] for k in ("final_generation", "final_components", "final_vocabulary")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
