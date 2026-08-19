"""Run the M094 pipeline and preserve what it did.

This replaces the development probe that used to live here. `docs/REPOSITORY_AUDIT_2026_08_18.md`
recorded that the probe's docstring claimed a pipeline including sandbox, comparison, adoption
and rollback while importing none of it; the pipeline now exists in
`metamorphosis/m094_lineage.py` and this orchestrates it:

    observe → develop → sandbox → compare → validate → run every search arm from the same
    starting state → adopt → persist → restart → the restart arm → rollback → RESULT.json

The arms run *before* adoption on purpose. Running them afterwards would measure them against
a repository the endogenous arm had already repaired: the diagnosis would have moved on to the
next insufficiency, and the controls would be controls of a different experiment. Only the
restart arm runs after adoption, because persisted state is the thing it exists to check.

Two safety properties, because a runner that can acquire a scientific result as a side effect
of being run is a hazard rather than an instrument:

* **it does not touch the working tree by default.** Adoption writes to the live component,
  so without ``--root`` the run happens on a throwaway copy made with `git archive`. A
  canonical run passes ``--root .`` deliberately;
* **it does not write into `experiments/M094/` without ``--arm``.** Materializing a result
  there is the scientific act the protocol governs, and the protocol forbids repairing one
  after a verdict. It must be a decision, not a default.

The qualification is **not** run from here. It is a separate process keyed on the adopted
mechanism's digest — `scripts/materialize_m094_qualification.py` — and this prints the command
to invoke once a mechanism exists.

Usage:
    python -m scripts.run_m094_experiment                     # rehearsal on a scratch copy
    python -m scripts.run_m094_experiment --root . --arm \
        --out experiments/M094/RESULT.json                    # a canonical run
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from metamorphosis.m094_lineage import (  # noqa: E402
    ARMS,
    TransformationStore,
    _source_digest,
    behavioural_cases,
    compare,
    develop,
    fresh_process_check,
    observe,
    rollback_proof,
    run_arm,
    sandbox_component,
    validate_independently,
)

PROTOCOL_PATH = REPO_ROOT / "experiments" / "M094" / "PROTOCOL.json"
RESULT_SCHEMA = "m094-result-v1"


def eligible_components() -> tuple[str, ...]:
    """The eligible set, as the frozen protocol enumerates it. Read, never copied."""

    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    return tuple(protocol["eligible_components"]["enumerated"])


def scratch_copy() -> Path:
    """A throwaway checkout of HEAD, so a rehearsal cannot modify the working tree."""

    work = Path(tempfile.mkdtemp(prefix="m094-run-"))
    archive = work / "head.tar"
    with archive.open("wb") as handle:
        subprocess.run(["git", "archive", "HEAD"], cwd=REPO_ROOT, stdout=handle, check=True)
    root = work / "repo"
    root.mkdir()
    subprocess.run(["tar", "-xf", str(archive), "-C", str(root)], check=True)
    return root


def step(message: str) -> None:
    print(f"\n=== {message} ===", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", default=None,
        help="repository to run against. Omitted means a throwaway copy of HEAD.",
    )
    parser.add_argument("--out", default=None, help="where to write RESULT.json")
    parser.add_argument(
        "--arm", action="store_true",
        help="required to write into experiments/M094/, which is a scientific act",
    )
    args = parser.parse_args()

    rehearsal = args.root is None
    root = scratch_copy() if rehearsal else Path(args.root).resolve()
    components = eligible_components()
    started = time.time()

    print(f"root: {root}")
    print(f"mode: {'rehearsal on a throwaway copy' if rehearsal else 'against ' + str(root)}")
    print(f"eligible: {list(components)}")

    result: dict[str, object] = {
        "schema": RESULT_SCHEMA,
        "milestone": "M094",
        "track": "A",
        # Track A forbids both. Recorded so P12 can check rather than assume.
        "model_calls": 0,
        "network_calls": 0,
        "is_rehearsal": rehearsal,
        "eligible_components": list(components),
    }

    step("1. observe")
    diagnosis = observe(root, components)
    if not diagnosis.unmet:
        print("  nothing is insufficient; there is nothing to repair")
        result["stopped"] = "no unmet insufficiency"
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    target = diagnosis.unmet[0]
    print(f"  selected {target.component_path}::{target.target} "
          f"(capability {target.capability}, demand {target.demand})")
    result["diagnosis"] = diagnosis.to_dict()

    step("2. develop")
    development = develop(root, components)
    if development.modified_source is None:
        print("  synthesis produced no candidate")
        result["stopped"] = "synthesis produced no candidate"
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    mechanism = development.mechanism_digest
    print(f"  mechanism {mechanism}")
    print(f"  {development.search.get('description')}")

    step("3. sandbox and compare")
    cases = behavioural_cases(
        root, target.component_path, target.target, development.requirement,
    )
    original = (root / target.component_path).read_text(encoding="utf-8")
    before = sandbox_component(
        root, target.component_path, original, target.target,
        development.requirement, cases, variant="original",
    )
    after = sandbox_component(
        root, target.component_path, development.modified_source, target.target,
        development.requirement, cases, variant="candidate",
    )
    comparison = compare(before, after)
    print(f"  original  {before.cases_satisfied}/{before.cases_constructible} constructible cases")
    print(f"  candidate {after.cases_satisfied}/{after.cases_constructible} "
          f"via {after.satisfying_methods}")
    print(f"  null_rejected: {comparison['null_rejected']} — {comparison['reason']}")

    step("4. independent validation")
    validation = validate_independently(
        root, target.component_path, development.modified_source,
        target.target, development.requirement,
    )
    print(f"  accepted={validation.accepted} "
          f"{validation.cases_satisfied}/{validation.cases_total} cases "
          f"receipt={validation.receipt[:16]}")

    step("5. every search arm, each from the same starting state")
    # The controls must measure S0. Running them after adoption would compare them against a
    # repository the endogenous arm had already repaired -- the diagnosis would have moved on
    # to the next insufficiency, and the arms would not be arms of the same experiment.
    arms: dict[str, object] = {}
    for arm in ARMS:
        if arm == "fresh_agent":
            continue  # needs persisted state; run after adoption
        elapsed = time.time()
        record = run_arm(arm, root, components, work_dir=root)
        arms[arm] = record
        print(f"  {arm:38s} closed={str(record.get('closed')):5s} "
              f"ceiling={str(record.get('is_ceiling')):5s} {time.time()-elapsed:6.1f}s")

    step("6. adopt")
    store = TransformationStore.init_or_load(root, root, _source_digest(original))
    adopted = store.adopt(
        target.component_path, original, development.modified_source,
        mechanism, validation, comparison,
    )
    print(f"  adopted={adopted} store version {store.version}")
    result["adoption"] = {
        "adopted": adopted,
        "version": store.version,
        "state_digest": store.state.digest(),
        "journal": [entry.to_dict() for entry in store.state.journal],
    }
    if not adopted:
        result["stopped"] = "the candidate was not adopted"
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    step("7. persist, kill the process, resume")
    persistence = fresh_process_check(root, root)
    print(f"  resumed_from_state={persistence.get('resumed_from_state')} "
          f"version={persistence.get('version')}")
    result["persistence"] = persistence

    step("8. the restart arm, which needs the persisted state")
    elapsed = time.time()
    arms["fresh_agent"] = run_arm("fresh_agent", root, components, work_dir=root)
    print(f"  {'fresh_agent':38s} closed={arms['fresh_agent']['closed']} "
          f"{time.time()-elapsed:6.1f}s")

    # The endogenous arm carries the adopted source so the checker can replay the validator
    # against the very bytes that were adopted rather than re-deriving them.
    endogenous = arms.get("endogenous_diagnosis_and_synthesis")
    if isinstance(endogenous, dict):
        endogenous["adopted_source"] = development.modified_source
    result["arms"] = arms
    result["mechanism_digest"] = mechanism

    step("9. rollback, with the fault on the live file")
    proof = rollback_proof(
        root, store, target.component_path, target.target, development.requirement, cases,
    )
    for key in ("fault", "fault_struck_the_live_file", "adopted_supplied_the_capability",
                "damage_was_behavioural", "restoration_is_byte_exact",
                "restored_matches_the_original_behaviour", "store_version_after_restore"):
        print(f"  {key}: {proof[key]}")
    result["rollback"] = proof

    result["elapsed_seconds"] = round(time.time() - started, 1)
    # Derived from the preserved artifacts rather than declared, as the retry policy requires.
    experiment = REPO_ROOT / "experiments" / "M094"
    withdrawn = sorted(p.name for p in experiment.glob("WITHDRAWN_RESULT_*.json"))
    result["prior_attempts"] = withdrawn
    result["attempt"] = len(withdrawn) + 1

    step("10. the qualification is a separate process")
    print("  Run it deliberately, with the salt this run produced:")
    print(f"    python -m scripts.materialize_m094_qualification \\\n"
          f"        --mechanism-digest {mechanism}")

    if args.out:
        out = Path(args.out)
        if out.resolve().parent == experiment and not args.arm:
            print(
                "\nRefusing to write into experiments/M094/ without --arm. Preserving a result\n"
                "there is the scientific act the protocol governs, and a correction after a\n"
                "verdict is forbidden. Pass --arm deliberately, or write elsewhere.",
                file=sys.stderr,
            )
            return 2
        if rehearsal:
            print(
                "\nRefusing to write a result from a rehearsal. This run happened on a\n"
                "throwaway copy, so its persistence and rollback evidence does not describe\n"
                "the repository. Pass --root . for a run whose result means something.",
                file=sys.stderr,
            )
            return 2
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8", newline="\n",
        )
        print(f"\nResult written to {out}")

    print(f"\n{'=' * 60}")
    print(json.dumps({k: v for k, v in result.items() if k != "diagnosis"},
                     indent=2, sort_keys=True, default=str)[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
