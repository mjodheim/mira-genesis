"""Run M097's frozen endogenous operation-acquisition qualification once and locally."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from metamorphosis.m097_acquisition import acquire  # noqa: E402
from metamorphosis.m097_execution import confirm_search  # noqa: E402
from metamorphosis.m097_language import (  # noqa: E402
    OperationLanguageState,
    canonical_json,
    digest,
    insufficiency_certificate,
    observe_requirement,
    search,
)
from metamorphosis.m097_validator import validate  # noqa: E402
from author_m097_qualification_pool import (  # noqa: E402
    COMPONENT,
    OUTPUT as POOL_PATH,
    audit as audit_pool,
    build_world,
    cases_for,
    load_pool,
)
from run_m095_qualification import file_set_digest  # noqa: E402

EXPERIMENT = ROOT / "experiments" / "M097"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
RESULT_SCHEMA = "m097-result-v1"

DEVELOPMENT = {
    "id": "development_cycle",
    "class": "Cycle",
    "key": "width",
    "left_field": "upper",
    "right_field": "lower",
    "operator": "sub",
    "caller_count": 3,
    "fields": [
        {"name": "lower", "annotation": "int"},
        {"name": "upper", "annotation": "int"},
        {"name": "name", "annotation": "str"},
    ],
    "cases": [
        {"lower": 2, "upper": 8, "name": "a"},
        {"lower": -3, "upper": 5, "name": "b"},
        {"lower": 7, "upper": 1, "name": "c"},
        {"lower": 0, "upper": 0, "name": "d"},
        {"lower": -9, "upper": -2, "name": "e"},
    ],
}


class QualificationRefused(RuntimeError):
    pass


def mechanism_digest(protocol: dict[str, object]) -> tuple[str, dict[str, str]]:
    return file_set_digest(protocol, "mechanism")


def require_frozen(protocol: dict[str, object], pool: dict[str, object]) -> None:
    if protocol.get("status") != "frozen":
        raise QualificationRefused("M097 protocol is not frozen")
    if pool.get("status") != "frozen":
        raise QualificationRefused("M097 pool is not frozen")
    if protocol.get("qualification_population", {}).get("pool_digest") != pool.get("pool_digest"):
        raise QualificationRefused("M097 protocol does not bind this pool digest")
    measured, _members = mechanism_digest(protocol)
    if protocol.get("mechanism", {}).get("digest") != measured:
        raise QualificationRefused("M097 mechanism moved after freeze")
    apparatus, _apparatus_members = file_set_digest(protocol, "qualification_apparatus")
    if protocol.get("qualification_apparatus", {}).get("digest") != apparatus:
        raise QualificationRefused("M097 apparatus moved after freeze")


def _public_cases(entry: dict[str, object]) -> list[dict[str, int | float]]:
    return [
        {
            "left": case[str(entry["left_field"])],
            "right": case[str(entry["right_field"])],
            "expected": (
                case[str(entry["left_field"])] - case[str(entry["right_field"])]
            ),
        }
        for case in entry["cases"]
    ]


def _search_record(
    root: Path,
    entry: dict[str, object],
    state: OperationLanguageState,
) -> dict[str, object]:
    requirement = observe_requirement(root, COMPONENT)
    source = (root / COMPONENT).read_text(encoding="utf-8")
    fields = [str(item["name"]) for item in entry["fields"]]
    searched = search(source, requirement, fields, state)
    executed, adopted_source, execution = confirm_search(
        root, COMPONENT, searched.sources, requirement, cases_for(entry)
    )
    return {
        "requirement": requirement.to_dict(),
        "search": searched.to_dict(),
        "executed_candidates": executed,
        "execution_confirmed": adopted_source is not None,
        "adopted_source_digest": (
            hashlib.sha256(adopted_source.encode("utf-8")).hexdigest()
            if adopted_source is not None else None
        ),
        "execution": execution,
    }


def run_experiment(pool: dict[str, object]) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="m097-run-") as temporary:
        base = Path(temporary)
        development_root = build_world(base / "development", DEVELOPMENT)
        development_requirement = observe_requirement(development_root, COMPONENT)
        public_cases = _public_cases(DEVELOPMENT)
        inherited_state = OperationLanguageState.inherited()
        inherited_before = _search_record(development_root, DEVELOPMENT, inherited_state)
        acquisition = acquire(public_cases)
        if acquisition.adopted is None:
            raise QualificationRefused("the frozen acquisition assembled no accepted operation")
        validation = validate(acquisition.adopted, public_cases)
        built_not_registered = _search_record(development_root, DEVELOPMENT, inherited_state)
        extended_state = inherited_state.register(acquisition.adopted)
        serialized = canonical_json(extended_state.to_dict())
        restored_state = OperationLanguageState.from_dict(json.loads(serialized))
        development_after = _search_record(development_root, DEVELOPMENT, restored_state)

        qualification = []
        for entry in pool["entries"]:
            inherited_root = build_world(base / "qualification" / "inherited" / str(entry["id"]), entry)
            extended_root = build_world(base / "qualification" / "extended" / str(entry["id"]), entry)
            qualification.append({
                "entry": entry["id"],
                "entry_digest": entry["entry_digest"],
                "inherited": _search_record(inherited_root, entry, inherited_state),
                "extended": _search_record(extended_root, entry, restored_state),
            })

    return {
        "schema": "m097-scientific-evidence-v1",
        "development_requirement": development_requirement.to_dict(),
        "inherited_insufficiency": insufficiency_certificate(development_requirement),
        "inherited_before": inherited_before,
        "acquisition": acquisition.to_dict(),
        "independent_validation": validation.to_dict(),
        "built_not_registered": built_not_registered,
        "inherited_language_state": inherited_state.to_dict(),
        "extended_language_state": extended_state.to_dict(),
        "serialized_state": serialized,
        "restored_state_equals_extended": restored_state == extended_state,
        "development_after_registration": development_after,
        "qualification": qualification,
        "controls": {
            "more_budget_same_language": {
                "same_language_more_budget_cannot_help": True,
                "basis": "the inherited closure certificate excludes ast.BinOp at any depth",
            },
            "acquisition_ablated_correct_worlds": sum(
                bool(row["inherited"]["execution_confirmed"]) for row in qualification
            ),
            "extended_correct_worlds": sum(
                bool(row["extended"]["execution_confirmed"]) for row in qualification
            ),
        },
        "conservation": {
            "inherited_digest_before": inherited_state.inherited_digest,
            "inherited_digest_after": restored_state.inherited_digest,
            "inherited_unchanged": inherited_state.inherited_digest == restored_state.inherited_digest,
            "extensions_before": len(inherited_state.extensions),
            "extensions_after": len(restored_state.extensions),
        },
    }


def materialize(*, armed: bool = False) -> dict[str, object]:
    if not armed:
        raise QualificationRefused("M097 result acquisition requires --arm")
    result_path = EXPERIMENT / "RESULT.json"
    if result_path.exists():
        raise QualificationRefused("M097 RESULT.json already exists; overwrite and rerun are forbidden")
    protocol_bytes = PROTOCOL_PATH.read_bytes()
    protocol = json.loads(protocol_bytes.decode("utf-8"))
    pool = load_pool()
    require_frozen(protocol, pool)
    try:
        source_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = bool(subprocess.run(
            ["git", "status", "--porcelain"], cwd=ROOT,
            capture_output=True, text=True, check=True
        ).stdout.strip())
    except Exception as error:  # noqa: BLE001
        raise QualificationRefused(f"source provenance unavailable: {error}") from error
    if dirty:
        raise QualificationRefused("commit the frozen M097 apparatus before arming")
    preflight = audit_pool(pool)
    if not preflight["passed"]:
        raise QualificationRefused("M097 frozen pool fails its S0-only audit")
    started = time.time()
    evidence = run_experiment(pool)
    measured, members = mechanism_digest(protocol)
    withdrawn = sorted(path.name for path in EXPERIMENT.glob("WITHDRAWN_RESULT_*.json"))
    result: dict[str, object] = {
        "schema": RESULT_SCHEMA,
        "milestone": "M097",
        "track": "A",
        "attempt": len(withdrawn) + 1,
        "prior_attempts": withdrawn,
        "source_commit": source_commit,
        "working_tree_was_dirty_at_recording": False,
        "model_calls": 0,
        "network_calls": 0,
        "remote_execution": False,
        "protocol_raw_sha256": hashlib.sha256(protocol_bytes).hexdigest(),
        "pool_digest": pool["pool_digest"],
        "mechanism_digest": measured,
        "mechanism_members": members,
        "scientific_evidence": evidence,
        "elapsed_seconds": round(time.time() - started, 3),
    }
    result["result_digest"] = digest(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", action="store_true")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    expected = (EXPERIMENT / "RESULT.json").resolve()
    if not args.arm:
        print("Refusing to acquire M097 without --arm.", file=sys.stderr)
        return 2
    if not args.out or Path(args.out).resolve() != expected:
        print("An armed run must write exactly experiments/M097/RESULT.json.", file=sys.stderr)
        return 2
    try:
        result = materialize(armed=True)
    except QualificationRefused as error:
        print(f"Refused: {error}", file=sys.stderr)
        return 2
    expected.parent.mkdir(parents=True, exist_ok=True)
    expected.write_text(canonical_json(result) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
