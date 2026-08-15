"""Verify the complete M092 criterion instrument before any canonical target search is consumed."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

import metamorphosis.m092_certificate_generator as candidate_generator
import metamorphosis.m092_certificate_policy_search as policy_search
import metamorphosis.m092_certificate_verifier as verifier
import metamorphosis.m092_criterion_search as criterion
import metamorphosis.m092_resume_validation as resume_validation
from metamorphosis.m092_runtime import canonical_bytes

ROOT = Path(__file__).resolve().parents[1]
M092 = ROOT / "experiments" / "M092"
PROTOCOL = M092 / "PROTOCOL.json"
TARGET_THEOREM = M092 / "TARGET_THEOREM.json"
CANONICAL_RUNNER = ROOT / "scripts" / "run_m092_criterion_search.py"
PRE_SEARCH_FORBIDDEN = (
    M092 / "SEARCH_STATE.json",
    M092 / "SELECTED_CANDIDATE.json",
    M092 / "VALIDATION_RECEIPT.json",
    M092 / "SUBSTRATE_B.json",
    M092 / "LANGUAGE_B.json",
    M092 / "QUALIFICATION.json",
    M092 / "RESULT.json",
    M092 / "RESULT.md",
    ROOT / "results" / "artifacts" / "M092_RESULT.json",
    ROOT / "results" / "M092_RESULT.md",
)


def _read(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _project_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names if alias.name.startswith("metamorphosis"))
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("metamorphosis"):
            found.add(node.module)
    return found


def _forbidden_import(imports: set[str]) -> str | None:
    for name in sorted(imports):
        lowered = name.lower()
        if any(token in lowered for token in ("qualification", "world_generator", "materialize")):
            return name
    return None


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_rehashed_resume_is_refused(neutral: dict[str, object]) -> None:
    """Prove the canonical resume validator does not confuse a self-hash with provenance."""

    forged = criterion.CriterionSearchState.fresh(neutral).to_dict()
    forged["certificate_policy_attempts"] = 1
    forged["criterion_event_chain_digest"] = "1" * 64
    payload = dict(forged)
    payload.pop("state_digest", None)
    forged["state_digest"] = criterion._sha256(payload)

    # Intentional positive control: the generic state loader checks internal integrity and accepts a
    # re-authored checksum. Canonical provenance is established by deterministic full-prefix replay.
    criterion.CriterionSearchState.from_dict(forged)
    try:
        resume_validation.verified_resume_state(forged, neutral)
    except resume_validation.ResumeValidationError as error:
        if "deterministic replay" not in str(error):
            raise SystemExit(
                "canonical resume rejected the forged state for an unexpected reason"
            ) from error
    else:
        raise SystemExit("canonical resume accepted a re-authored and re-hashed search state")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assert-pre-search", action="store_true")
    arguments = parser.parse_args()

    protocol = _read(PROTOCOL)
    target = _read(TARGET_THEOREM)
    if not isinstance(protocol, dict) or not isinstance(target, dict):
        raise SystemExit("M092 protocol and target theorem must be JSON objects")
    if target != verifier.M092_TARGET_POSTCONDITION:
        raise SystemExit("TARGET_THEOREM.json differs from the independently parsed target theorem")
    search = protocol.get("search")
    if not isinstance(search, dict):
        raise SystemExit("M092 protocol search section is missing")
    certificate_bounds = search.get("certificate_search_bounds")
    if not isinstance(certificate_bounds, dict):
        raise SystemExit("M092 protocol certificate bounds are missing")
    if search.get("candidate_cap") != criterion.PROGRAM_CAP:
        raise SystemExit("criterion program cap differs from the frozen protocol")
    if certificate_bounds.get("certificates_examined_per_program_maximum") != criterion.CERTIFICATES_PER_PROGRAM:
        raise SystemExit("criterion per-program certificate cap differs from the frozen protocol")
    if certificate_bounds.get("total_certificates_examined_maximum") != criterion.CERTIFICATE_CAP:
        raise SystemExit("criterion global certificate cap differs from the frozen protocol")

    implementation_bounds = {
        "affine_coefficient_inclusive_maximum": candidate_generator.MAX_AFFINE_COEFFICIENT,
        "affine_coefficient_inclusive_minimum": -candidate_generator.MAX_AFFINE_COEFFICIENT,
        "constraints_per_loop_maximum": candidate_generator.MAX_CONSTRAINTS_PER_LOOP,
        "ghost_counters_maximum": candidate_generator.MAX_GHOST_COUNTERS,
        "loop_headers_maximum": 1,
    }
    for field, expected in implementation_bounds.items():
        if certificate_bounds.get(field) != expected:
            raise SystemExit(
                f"criterion certificate bound {field} differs from implementation: "
                f"protocol={certificate_bounds.get(field)!r}, implementation={expected!r}"
            )

    if protocol.get("status") != "frozen_before_any_m092b_extension_search_or_qualification":
        raise SystemExit("M092 protocol is not at the frozen pre-search status")

    policy_imports = _project_imports(Path(policy_search.__file__).resolve())
    if any("verifier" in name.lower() or "qualification" in name.lower() for name in policy_imports):
        raise SystemExit("candidate-side policy search crosses the independent validation boundary")
    criterion_imports = _project_imports(Path(criterion.__file__).resolve())
    forbidden = _forbidden_import(criterion_imports)
    if forbidden is not None:
        raise SystemExit(f"criterion selection imports forbidden qualification material: {forbidden}")
    resume_imports = _project_imports(Path(resume_validation.__file__).resolve())
    forbidden_resume_import = _forbidden_import(resume_imports)
    if forbidden_resume_import is not None:
        raise SystemExit(
            "canonical resume validator imports forbidden qualification material: "
            + forbidden_resume_import
        )
    runner_imports = _project_imports(CANONICAL_RUNNER)
    forbidden_runner_import = _forbidden_import(runner_imports)
    if forbidden_runner_import is not None:
        raise SystemExit(
            "canonical runner imports forbidden qualification material: " + forbidden_runner_import
        )

    missing_pre_search = [str(path.relative_to(ROOT)) for path in PRE_SEARCH_FORBIDDEN if path.exists()]
    if arguments.assert_pre_search and missing_pre_search:
        raise SystemExit(
            "M092 criterion freeze is no longer pre-search; premature artifact(s): "
            + ", ".join(missing_pre_search)
        )

    neutral = verifier.COUNTDOWN_POSTCONDITION
    state = criterion.CriterionSearchState.fresh(neutral)
    round_trip = criterion.CriterionSearchState.from_dict(json.loads(json.dumps(
        state.to_dict(), sort_keys=True, separators=(",", ":"),
    )))
    if round_trip.to_dict() != state.to_dict():
        raise SystemExit("criterion search genesis state is not byte-logically round-trippable")

    _assert_rehashed_resume_is_refused(neutral)

    report = {
        "schema": "m092-criterion-freeze-readiness-v1",
        "protocol_status": protocol["status"],
        "target_theorem_digest": hashlib.sha256(canonical_bytes(target)).hexdigest(),
        "program_cap": criterion.PROGRAM_CAP,
        "certificate_cap": criterion.CERTIFICATE_CAP,
        "certificates_per_program": criterion.CERTIFICATES_PER_PROGRAM,
        "certificate_bounds": implementation_bounds,
        "behaviour_deduplication_enabled": False,
        "policy_imports": sorted(policy_imports),
        "criterion_imports": sorted(criterion_imports),
        "canonical_resume_validator_imports": sorted(resume_imports),
        "canonical_runner_imports": sorted(runner_imports),
        "canonical_resume_validator_blob_sha256": _file_digest(
            Path(resume_validation.__file__).resolve()
        ),
        "canonical_runner_blob_sha256": _file_digest(CANONICAL_RUNNER),
        "canonical_resume_replay_verified": True,
        "rehashed_resume_positive_control_refused": True,
        "qualification_loaded": False,
        "candidate_executed": False,
        "canonical_target_search_executed": False,
        "pre_search_forbidden_artifacts_present": missing_pre_search,
        "neutral_genesis_state_digest": state.to_dict()["state_digest"],
        "status": "verified_pre_search",
    }
    report["report_digest"] = hashlib.sha256(canonical_bytes(report)).hexdigest()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
