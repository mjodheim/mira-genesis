#!/usr/bin/env python3
"""Neutral M092-H rehearsal.  It cannot arm or read the sealed target/qualification bank."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from metamorphosis.m092_adoption import (
    AdoptionError,
    BEHAVIOUR_FAULT_PROGRAM,
    build_extended_bundle,
    commit_adoption_transaction,
    downstream_primitive_id,
    execute_downstream,
    load_committed_bundle,
    restore_exact,
    sha256_bytes,
    validate_candidate_for_adoption,
)
from metamorphosis.m092_certificate_generator import generate_candidate_certificates
from metamorphosis.m092_certificate_verifier import COUNTDOWN_POSTCONDITION
from metamorphosis.m092_qualification import QualificationTask, run_qualification_ledger
from metamorphosis.m092_runtime import RuntimeLanguage
from metamorphosis.m092_substrate_state import SubstrateState

BASE = Path("experiments/M092/SUBSTRATE_A.json")
ARM_MARKER = Path("experiments/M092/CANONICAL_SEARCH_ARMED.json")
REAL_EXTENDED = Path("experiments/M092/SUBSTRATE_B.json")
NEUTRAL_PROGRAM = (
    ("SPOP", 0),
    ("LOADI", 1, 1),
    ("JZ", 0, 5),
    ("SUB", 0, 0, 1),
    ("JMP", 2),
    ("SPUSH", 0),
    ("HALT",),
)


def _fresh_check(bundle_path: Path, journal_path: Path, primitive_id: str) -> int:
    language, substrate = load_committed_bundle(bundle_path, journal_path)
    state = execute_downstream(language, substrate, primitive_id, 7)
    print(json.dumps({
        "fresh_process_loaded": True,
        "value": state[0],
        "language_digest": language.digest(),
        "substrate_digest": substrate.digest(),
    }, sort_keys=True))
    return 0


def _tasks() -> list[QualificationTask]:
    # Materialized only after the fresh-process check below.  These are neutral synthetic inputs,
    # not values from the sealed qualification generator.
    return [
        QualificationTask("small", f"small-{value}", value, 0) for value in range(10)
    ] + [
        QualificationTask("larger", f"larger-{value}", value, 0) for value in range(10, 20)
    ]


def run() -> dict[str, object]:
    if ARM_MARKER.exists() or REAL_EXTENDED.exists():
        raise AdoptionError("neutral rehearsal refuses an armed or already-adopted repository")

    raw = BASE.read_bytes()
    base = json.loads(raw)
    base_language = RuntimeLanguage.from_dict(base["language"])
    base_substrate = SubstrateState.from_dict(base["substrate"])
    if base_substrate.digest() != base["expected_substrate_digest"]:
        raise AdoptionError("SUBSTRATE_A internal digest mismatch")

    certificate = next(
        generate_candidate_certificates(NEUTRAL_PROGRAM, COUNTDOWN_POSTCONDITION, limit=64)
    )
    receipt = validate_candidate_for_adoption(
        NEUTRAL_PROGRAM,
        certificate,
        expected_postcondition=COUNTDOWN_POSTCONDITION,
    )
    extended = build_extended_bundle(
        base_language,
        base_substrate,
        NEUTRAL_PROGRAM,
        receipt=receipt,
        source_bundle_sha256=sha256_bytes(raw),
    )
    primitive_id = downstream_primitive_id(NEUTRAL_PROGRAM)

    with tempfile.TemporaryDirectory(prefix="m092-h-neutral-") as directory:
        root = Path(directory)
        bundle_path = root / "SUBSTRATE_B_NEUTRAL.json"
        journal_path = root / "ADOPTION_TRANSACTION_NEUTRAL.json"
        commit_adoption_transaction(bundle_path, journal_path, extended)
        preserved = bundle_path.read_bytes()
        preserved_sha = sha256_bytes(preserved)

        child = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--fresh-check",
                str(bundle_path),
                str(journal_path),
                primitive_id,
            ],
            check=True,
            text=True,
            capture_output=True,
        )
        fresh = json.loads(child.stdout.strip().splitlines()[-1])
        if fresh.get("fresh_process_loaded") is not True or fresh.get("value") != 0:
            raise AdoptionError("fresh-process replay did not execute the persisted acquisition")

        # Only now may the neutral qualification tasks be materialized.
        language, substrate = load_committed_bundle(bundle_path, journal_path)
        ledger = run_qualification_ledger(
            _tasks(),
            primitive_id=primitive_id,
            extended_language=language,
            extended_substrate=substrate,
            control_language=base_language,
            control_substrate=base_substrate,
            fresh_process_loaded=True,
            adoption_committed=True,
        )

        normal = execute_downstream(language, substrate, primitive_id, 0)
        corrupted = substrate.replacing(str(extended["operation_key"]), BEHAVIOUR_FAULT_PROGRAM)
        faulted = execute_downstream(language, corrupted, primitive_id, 0)
        if normal == faulted:
            raise AdoptionError("frozen rollback fault failed to change live behaviour")

        # Persist a real program-level corruption.  The committed loader must reject it because the
        # exact adopted program digest no longer matches, then rollback restores independent bytes.
        faulty = dict(extended)
        faulty["substrate"] = corrupted.to_dict()
        faulty["substrate_digest"] = corrupted.digest()
        bundle_path.write_text(json.dumps(faulty, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        rejected_fault = False
        try:
            load_committed_bundle(bundle_path, journal_path)
        except AdoptionError:
            rejected_fault = True
        if not rejected_fault:
            raise AdoptionError("corrupted persisted acquisition was accepted")

        restored_sha = restore_exact(bundle_path, preserved)
        restored_language, restored_substrate = load_committed_bundle(bundle_path, journal_path)
        restored = execute_downstream(restored_language, restored_substrate, primitive_id, 0)
        if restored != normal or restored_sha != preserved_sha:
            raise AdoptionError("rollback did not restore exact pre-fault state and behaviour")

    return {
        "schema": "m092-h-neutral-rehearsal/1",
        "neutral_only": True,
        "canonical_search_armed": False,
        "real_extended_state_materialized": False,
        "sealed_target_loaded": False,
        "hidden_qualification_materialized": False,
        "adoption_validation_recomputed": True,
        "fresh_process_loaded": True,
        "downstream_dependency_real": True,
        "qualification_after_fresh_process": True,
        "task_family_count": len(ledger["families"]),
        "extended_attempts_executed": ledger["extended_attempts_executed"],
        "control_attempts_executed": ledger["control_attempts_executed"],
        "control_budget_multiplier": ledger["control_budget_multiplier"],
        "fault_changed_live_behaviour": normal != faulted,
        "faulted_persistence_rejected": rejected_fault,
        "rollback_byte_identical": restored_sha == preserved_sha,
        "rollback_behaviour_restored": restored == normal,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fresh-check", action="store_true")
    parser.add_argument("fresh_args", nargs="*")
    arguments = parser.parse_args()
    if arguments.fresh_check:
        if len(arguments.fresh_args) != 3:
            parser.error("--fresh-check needs bundle path, journal path and primitive id")
        return _fresh_check(
            Path(arguments.fresh_args[0]),
            Path(arguments.fresh_args[1]),
            arguments.fresh_args[2],
        )
    if arguments.fresh_args:
        parser.error("unexpected positional arguments")
    print(json.dumps(run(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
