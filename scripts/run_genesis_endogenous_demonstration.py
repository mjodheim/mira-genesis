#!/usr/bin/env python3
"""A lineage that builds its own descendants and changes the rule it builds them by.

This is the **second** DEVELOPMENT demonstration. The first
(``run_genesis_demonstration.py``) drives a fixed programme through the controller and stays as the
integration regression for architecture transitions: acquisition, vocabulary extension, migration,
causal chain. Its bodies were importable symbols the host wrote before the run, and every descendant
it adopts was therefore *selected* from a catalogue.

This one starts with no catalogue at all. ``World.artifacts`` is empty, so there is nothing to
select; the seed body answers one question out of six; and the two things the objective actually asks
for have to happen or the run shows nothing:

1. the lineage's **body** is constructed rather than chosen — a program that did not exist at
   admission, built from an admitted operation alphabet, evaluated under the immutable trust root,
   and recoverable from the artifact store after process death;
2. the lineage's **acquisition machinery** changes on evidence about what it produced — two policies
   drive matched forks of the same committed state, and the trust root compares their descendants.

It is still DEVELOPMENT apparatus and it advances no gate. The operations are arithmetic on integers,
the grammar is unary chains, and the candidate policies are a host-admitted pair. What it establishes
is that the mechanisms compose into one lineage and refuse what they claim to refuse — not that any
of it generalises.

Run with ``--write`` to persist the record under ``experiments/GENESIS/``.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from genesis import controller  # noqa: E402
from genesis import search_fixtures as fixtures  # noqa: E402
from genesis import state as lineage_state  # noqa: E402
from genesis import trust_root as tr  # noqa: E402
from genesis.loop import Genesis  # noqa: E402

RECORD_PATH = ROOT / "experiments" / "GENESIS" / "ENDOGENOUS_RECORD.json"
STATE_PATH = ROOT / "experiments" / "GENESIS" / "endogenous_state"


def _seed_state() -> dict:
    return lineage_state.create_state(
        body_digest="seed",
        components=[
            {
                "name": "operator_table",
                "origin": "seed",
                "certificate": None,
                "provenance": tr.provenance("host_written", produced_by="seed"),
            }
        ],
        vocabulary=[
            {"name": "resolvable_by_operator_table", "origin": "seed", "certificate": None}
        ],
    )


def demonstrate() -> dict:
    if STATE_PATH.exists():
        shutil.rmtree(STATE_PATH)

    genesis = Genesis(
        state=_seed_state(),
        # Answers `q0` and nothing else. A parent that answered nothing would make the search
        # trivial: the first candidate to get one question right would strictly improve on it.
        body_factory=fixtures.seed_body,
        budget=tr.Budget(limits={"generations": 200, "probes": 200}),
        isolation=tr.Isolation(),
        grade=fixtures.graded_against_expected,
    )
    here = fixtures.policy_world()
    parent_answers = [
        genesis.body_factory().attempt(task) == task["expected"] for task in fixtures.SEARCH_TASKS
    ]

    run = controller.run(
        genesis,
        here,
        # The incumbent asks to be replaced, then the replacement searches.
        fixtures.adopt_the_bolder_policy,
        max_steps=5,
        checkpoint_directory=STATE_PATH,
    )

    # Process death, with nobody able to hand back a body that only ever existed as bytes.
    restored = Genesis.restore(STATE_PATH, grade=fixtures.graded_against_expected)
    body = genesis.body_factory

    record = {
        "schema": "genesis-endogenous-demonstration-v1",
        "development": True,
        "is_a_scientific_observation": False,
        "advances_a_generality_gate": False,
        "frozen": False,
        "world_offered_no_body_to_select": sorted(here.artifacts) == [],
        "parent_answered": parent_answers,
        "run": run,
        "final_body": {
            "artifact": tr.artifact_digest_of(body),
            "calls_in_order": body.calls() if hasattr(body, "calls") else [],
            "answers": [
                body().attempt(task) == task["expected"] for task in fixtures.SEARCH_TASKS
            ],
        },
        "machinery_in_force": controller.bound_mechanism_artifact(genesis),
        "survives_process_death": {
            "state_digest_matches": restored.state["state_digest"] == genesis.state["state_digest"],
            "journal_head_matches": restored.journal.head == genesis.journal.head,
            "body_recovered_without_a_caller_supplying_it": tr.artifact_digest_of(
                restored.body_factory
            )
            == tr.artifact_digest_of(body),
            "machinery_matches": controller.bound_mechanism_artifact(restored)
            == controller.bound_mechanism_artifact(genesis),
        },
        "trust_root_sha256": tr.source_digest(),
        "evaluation_contract_digest": genesis.evaluation_contract["contract_digest"],
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

    print("  parent answered              %s" % record["parent_answered"])
    for step in record["run"]["steps"]:
        detail = ""
        if step["intent"] == "AdoptPolicy":
            detail = "updated=%s  descendants %d -> %d solved" % (
                step["policy_updated"], step["incumbent_solved"], step["candidate_solved"]
            )
        elif step["intent"] == "SearchTransform":
            detail = "built %d candidates, adopted=%s" % (
                step["candidates_considered"], step["accepted"]
            )
        else:
            detail = step.get("reason", "")
        print("  %-18s %s" % (step["intent"], detail))
    print("  final body                   %s" % "->".join(record["final_body"]["calls_in_order"]))
    print("  final body answers           %s" % record["final_body"]["answers"])
    print(json.dumps(record["survives_process_death"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
