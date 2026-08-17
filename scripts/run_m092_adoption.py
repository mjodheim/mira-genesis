#!/usr/bin/env python3
"""Post-reproduction M092 adoption runner.

This file is frozen pre-arm but must not be executed until the canonical result is candidate_selected
and the independent reproduction result opens the qualification gate.  It creates the real persisted
extended runtime only after revalidating the exact selected program and certificate from raw bytes.
The protocol-exact independent validation receipt is persisted before registration.  Qualification
material is never loaded or materialized here.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Mapping

from metamorphosis.m092_adoption import (
    AdoptionError,
    build_extended_bundle,
    commit_adoption_transaction,
    execute_downstream,
    load_committed_bundle,
    validate_candidate_for_adoption,
)
from metamorphosis.m092_adoption_checkpoint import load_frozen_base
from metamorphosis.m092_criterion_search import CriterionSearchState
from metamorphosis.m092_kernel import program_from_list
from metamorphosis.m092_qualification import validate_reproduction_gate
from metamorphosis.m092_validation_receipt import recompute_validation_receipt, validate_receipt_shape

DEFAULT_TARGET_THEOREM = Path("experiments/M092/TARGET_THEOREM.json")
DEFAULT_VALIDATION_RECEIPT = Path("experiments/M092/VALIDATION_RECEIPT.json")
DEFAULT_OUTPUT = Path("experiments/M092/SUBSTRATE_B.json")
DEFAULT_JOURNAL = Path("experiments/M092/ADOPTION_TRANSACTION.json")
DEFAULT_FRESH_RECEIPT = Path("experiments/M092/FRESH_PROCESS_RECEIPT.json")


def _read(path: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AdoptionError(f"{label} is not readable JSON") from error
    if not isinstance(value, dict):
        raise AdoptionError(f"{label} must be a JSON object")
    return value


def _write(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _fresh_check(bundle: Path, journal: Path, primitive_id: str) -> int:
    language, substrate = load_committed_bundle(bundle, journal)
    state = execute_downstream(language, substrate, primitive_id, 0)
    print(json.dumps({
        "schema": "m092-fresh-process-receipt/1",
        "fresh_process_loaded": True,
        "qualification_loaded": False,
        "primitive_id": primitive_id,
        "probe_input": 0,
        "probe_state": list(state),
        "language_digest": language.digest(),
        "substrate_digest": substrate.digest(),
    }, sort_keys=True))
    return 0


def adopt(
    *,
    canonical_result_path: Path,
    reproduction_result_path: Path,
    target_theorem_path: Path,
    validation_receipt_path: Path,
    output_path: Path,
    journal_path: Path,
    fresh_receipt_path: Path,
) -> dict[str, object]:
    for path in (validation_receipt_path, output_path, journal_path, fresh_receipt_path):
        if path.exists():
            raise AdoptionError("real adoption artifacts already exist; adoption is single-shot")

    canonical = _read(canonical_result_path, "canonical result")
    reproduction = _read(reproduction_result_path, "independent reproduction result")
    gate = validate_reproduction_gate(canonical, reproduction)
    theorem = _read(target_theorem_path, "target theorem")

    search_state_raw = canonical.get("search_state")
    if not isinstance(search_state_raw, dict):
        raise AdoptionError("canonical result lacks a search state")
    try:
        search_state = CriterionSearchState.from_dict(search_state_raw)
    except ValueError as error:
        raise AdoptionError("canonical search state failed semantic validation") from error
    if search_state.status != "candidate_selected" or search_state.selected is None:
        raise AdoptionError("canonical result has no selected candidate to adopt")
    selected = search_state.selected
    program_raw = selected.get("program")
    certificate = selected.get("certificate")
    if not isinstance(program_raw, list) or not isinstance(certificate, dict):
        raise AdoptionError("selected candidate program/certificate is malformed")
    program = program_from_list(program_raw)

    base_language, base_substrate, base_sha, checkpoint = load_frozen_base()
    checkpoint_digest = checkpoint.get("checkpoint_digest")
    if not isinstance(checkpoint_digest, str) or len(checkpoint_digest) != 64:
        raise AdoptionError("CHECKPOINT_A does not expose its exact checkpoint digest")

    validation_receipt = recompute_validation_receipt(
        program,
        certificate,
        expected_postcondition=theorem,
        checkpoint_digest=checkpoint_digest,
    )
    validate_receipt_shape(validation_receipt)
    if validation_receipt["program_digest"] != selected.get("program_digest"):
        raise AdoptionError("protocol validation digest differs from selected candidate")
    if validation_receipt["certificate_digest"] != selected.get("certificate_digest"):
        raise AdoptionError("protocol validation certificate digest differs from selected candidate")

    # The adoption helper independently reruns the same scanner/global-verifier boundary.  Its
    # receipt is internal construction metadata; the persisted protocol authority is the closed
    # VALIDATION_RECEIPT written immediately below, before S1/L1 registration begins.
    adoption_receipt = validate_candidate_for_adoption(
        program,
        certificate,
        expected_postcondition=theorem,
    )
    if adoption_receipt["program_digest"] != validation_receipt["program_digest"]:
        raise AdoptionError("adoption and protocol validation program digests differ")
    if adoption_receipt["certificate_digest"] != validation_receipt["certificate_digest"]:
        raise AdoptionError("adoption and protocol validation certificate digests differ")

    _write(validation_receipt_path, validation_receipt)
    persisted_validation = _read(validation_receipt_path, "persisted validation receipt")
    validate_receipt_shape(persisted_validation)
    if persisted_validation != validation_receipt:
        raise AdoptionError("persisted validation receipt differs before registration")

    bundle = build_extended_bundle(
        base_language,
        base_substrate,
        program,
        receipt=adoption_receipt,
        source_bundle_sha256=base_sha,
    )
    committed = commit_adoption_transaction(output_path, journal_path, bundle)

    child = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--fresh-check",
            str(output_path),
            str(journal_path),
            str(bundle["primitive_id"]),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    fresh = json.loads(child.stdout.strip().splitlines()[-1])
    if fresh.get("fresh_process_loaded") is not True or fresh.get("qualification_loaded") is not False:
        raise AdoptionError("fresh-process verification failed")
    _write(fresh_receipt_path, fresh)

    return {
        "schema": "m092-adoption-run-result/1",
        "canonical_result_digest": gate["canonical_result_digest"],
        "reproduction_result_digest": gate["reproduction_result_digest"],
        "reproduced_state_digest": gate["state_digest"],
        "qualification_gate_was_open_before_adoption": True,
        "validation_receipt_digest": validation_receipt["receipt_digest"],
        "internal_adoption_receipt_digest": adoption_receipt["receipt_digest"],
        "program_digest": bundle["program_digest"],
        "operation_key": bundle["operation_key"],
        "primitive_id": bundle["primitive_id"],
        "extended_bundle_digest": bundle["bundle_digest"],
        "transaction_phase": committed["phase"],
        "fresh_process_verified": True,
        "qualification_materialized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fresh-check", action="store_true")
    parser.add_argument("--canonical-result", type=Path)
    parser.add_argument("--reproduction-result", type=Path)
    parser.add_argument("--target-theorem", type=Path, default=DEFAULT_TARGET_THEOREM)
    parser.add_argument("--validation-receipt", type=Path, default=DEFAULT_VALIDATION_RECEIPT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--journal", type=Path, default=DEFAULT_JOURNAL)
    parser.add_argument("--fresh-receipt", type=Path, default=DEFAULT_FRESH_RECEIPT)
    parser.add_argument("fresh_args", nargs="*")
    args = parser.parse_args()

    if args.fresh_check:
        if len(args.fresh_args) != 3:
            parser.error("--fresh-check requires bundle, journal and primitive id")
        return _fresh_check(Path(args.fresh_args[0]), Path(args.fresh_args[1]), args.fresh_args[2])
    if args.fresh_args:
        parser.error("unexpected positional arguments")
    if args.canonical_result is None or args.reproduction_result is None:
        parser.error("real adoption requires --canonical-result and --reproduction-result")

    result = adopt(
        canonical_result_path=args.canonical_result,
        reproduction_result_path=args.reproduction_result,
        target_theorem_path=args.target_theorem,
        validation_receipt_path=args.validation_receipt,
        output_path=args.output,
        journal_path=args.journal,
        fresh_receipt_path=args.fresh_receipt,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
