"""Run M095's frozen structural qualification locally and preserve what happened.

There is no remote execution path here.  All worlds are materialised in a local temporary
directory and every member of the committed finite population is run exactly once.  A run
is refused until both protocol and pool say ``frozen``.  Writing under ``experiments/M095``
also requires ``--arm`` so importing or rehearsing the instrument cannot acquire a result.

Usage after the freeze commit::

    python -m scripts.run_m095_qualification --arm \
        --out experiments/M095/RESULT.json
"""

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

from metamorphosis import m095_arms as arms  # noqa: E402
from metamorphosis import m095_chain as chain  # noqa: E402
from author_m095_qualification_pool import (  # noqa: E402
    OUTPUT as POOL_PATH,
    audit as audit_pool,
    build_world,
    canonical_json,
    digest,
    load_pool,
)

EXPERIMENT = ROOT / "experiments" / "M095"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
RESULT_SCHEMA = "m095-result-v1"


class QualificationRefused(RuntimeError):
    """The requested action would cross a frozen-protocol boundary."""


def _raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_set_digest(
    protocol: dict[str, object], section: str,
) -> tuple[str, dict[str, str]]:
    files = protocol.get(section, {}).get("files", [])
    if not isinstance(files, list) or not files:
        raise QualificationRefused(f"the protocol fixes no {section} files")
    members = {
        str(relative): _raw_sha256(ROOT / str(relative))
        for relative in files
    }
    return digest(members), members


def mechanism_digest(protocol: dict[str, object]) -> tuple[str, dict[str, str]]:
    return file_set_digest(protocol, "mechanism")


def require_frozen(protocol: dict[str, object], pool: dict[str, object]) -> None:
    if protocol.get("status") != "frozen":
        raise QualificationRefused("M095 protocol is not frozen")
    if pool.get("status") != "frozen":
        raise QualificationRefused("M095 qualification pool is not frozen")
    expected = protocol.get("qualification_population", {}).get("pool_digest")
    if expected != pool.get("pool_digest"):
        raise QualificationRefused("the frozen protocol does not bind this pool digest")
    measured, _members = mechanism_digest(protocol)
    declared = protocol.get("mechanism", {}).get("digest")
    if declared != measured:
        raise QualificationRefused(
            f"the mechanism moved after freeze: protocol {declared}, current {measured}"
        )
    apparatus, _apparatus_members = file_set_digest(protocol, "qualification_apparatus")
    declared_apparatus = protocol.get("qualification_apparatus", {}).get("digest")
    if declared_apparatus != apparatus:
        raise QualificationRefused(
            "the qualification apparatus moved after freeze: "
            f"protocol {declared_apparatus}, current {apparatus}"
        )


def _entry_record(entry: dict[str, object], built: chain.Chain) -> dict[str, object]:
    control = built.control
    step_a = built.step_a
    step_b = built.step_b
    counterfactual = built.counterfactual
    return {
        "entry": entry["id"],
        "entry_digest": entry["entry_digest"],
        "structure": entry["structure"],
        "arrangement": entry["arrangement"],
        "expected_relation": entry["expected_relation"],
        "expected_descent": entry["expected_descent"],
        "world": dict(built.facts),
        "enabling_demonstrated": built.enabling_demonstrated,
        "descent_used": bool(built.descended_to),
        "control_b_from_s0_reached": control.reached if control else None,
        "a_reached": step_a.reached if step_a else None,
        "a_identified_by": built.step_a_identified_by,
        "b_reached": step_b.reached if step_b else None,
        "b_confirmed_by_execution": step_b.confirmed if step_b else 0,
        "counterfactual_b_without_a_reached": (
            counterfactual.reached if counterfactual else None
        ),
        "same_bound_control_to_b": control.bound if control else None,
        "same_bound_step_b": step_b.bound if step_b else None,
        "same_operations_offered_control": control.operations_offered if control else None,
        "same_operations_offered_step_b": step_b.operations_offered if step_b else None,
        "chain": built.to_dict(),
    }


def materialize(*, armed: bool = False) -> dict[str, object]:
    if not armed:
        raise QualificationRefused(
            "running the frozen population acquires the scientific result and requires arming"
        )
    if (EXPERIMENT / "RESULT.json").exists():
        raise QualificationRefused(
            "RESULT.json already exists; the frozen population may not be rerun or overwritten"
        )
    protocol_bytes = PROTOCOL_PATH.read_bytes()
    protocol = json.loads(protocol_bytes.decode("utf-8"))
    pool = load_pool()
    require_frozen(protocol, pool)

    try:
        source_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        dirty = bool(subprocess.run(
            ["git", "status", "--porcelain"], cwd=ROOT,
            capture_output=True, text=True, check=True,
        ).stdout.strip())
    except Exception as error:  # noqa: BLE001 - a canonical run requires resolvable provenance
        raise QualificationRefused(f"source commit could not be resolved: {error}") from error
    if dirty:
        raise QualificationRefused(
            "the working tree is dirty; commit the frozen protocol and apparatus before arming"
        )

    pool_audit = audit_pool(pool)
    if not pool_audit["passed"]:
        raise QualificationRefused("the frozen pool no longer passes its S0 construction audit")

    measured_mechanism, mechanism_members = mechanism_digest(protocol)
    started = time.time()
    rows = []
    with tempfile.TemporaryDirectory(prefix="m095-qualification-") as temporary:
        base = Path(temporary)
        for entry in pool["entries"]:
            entry_root = base / "population" / str(entry["id"])
            counterfactual_root = base / "counterfactual" / str(entry["id"])
            build_world(entry_root, pool, entry)
            build_world(counterfactual_root, pool, entry)
            rows.append(_entry_record(entry, chain.run_existing(entry_root, counterfactual_root)))

        def make_root(name: str) -> Path:
            return base / "development-arms" / name

        arrangement = arms.run(make_root).to_dict()
        random_target = arms.random_target(make_root).to_dict()
        more_budget = arms.more_budget(make_root).to_dict()

    withdrawn = sorted(path.name for path in EXPERIMENT.glob("WITHDRAWN_RESULT_*.json"))
    positives = [row for row in rows if row["expected_relation"]]
    negatives = [row for row in rows if not row["expected_relation"]]
    result: dict[str, object] = {
        "schema": RESULT_SCHEMA,
        "milestone": "M095",
        "track": "A",
        "protocol_raw_sha256": hashlib.sha256(protocol_bytes).hexdigest(),
        "protocol_status": protocol["status"],
        "pool_digest": pool["pool_digest"],
        "mechanism_digest": measured_mechanism,
        "mechanism_members": mechanism_members,
        "source_commit": source_commit,
        "working_tree_was_dirty_at_recording": False,
        "model_calls": 0,
        "network_calls": 0,
        "attempt": len(withdrawn) + 1,
        "prior_attempts": withdrawn,
        "population_is_exhaustive": True,
        "entries_run": len(rows),
        "entries": rows,
        "qualification_summary": {
            "positive_entries": len(positives),
            "positive_demonstrated": sum(
                1 for row in positives if row["enabling_demonstrated"]
            ),
            "negative_entries": len(negatives),
            "negative_remained_negative": sum(
                1 for row in negatives if not row["enabling_demonstrated"]
            ),
            "ranking_unaided_demonstrated": sum(
                1 for row in positives
                if row["enabling_demonstrated"] and not row["descent_used"]
            ),
            "descent_demonstrated": sum(
                1 for row in positives
                if row["enabling_demonstrated"] and row["descent_used"]
            ),
        },
        "development_arms": {
            "arrangement": arrangement,
            "random_target_ceiling": random_target,
            "more_budget_same_operations": more_budget,
        },
        "random_target_is_non_decisive": True,
        "random_target_reason": (
            "no eligible rival can touch the inner class; this is a disclosed sensitivity "
            "ceiling, not a condition capable of supporting the verdict"
        ),
        "elapsed_seconds": round(time.time() - started, 3),
    }
    result["result_digest"] = digest(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=None, help="optional result path")
    parser.add_argument(
        "--arm", action="store_true",
        help="required to write a scientific result under experiments/M095",
    )
    args = parser.parse_args()
    if not args.arm:
        print(
            "Refusing to run the frozen qualification without --arm; execution itself "
            "acquires the scientific result.",
            file=sys.stderr,
        )
        return 2
    if not args.out or Path(args.out).resolve() != (EXPERIMENT / "RESULT.json").resolve():
        print(
            "An armed run must preserve its evidence exactly at experiments/M095/RESULT.json.",
            file=sys.stderr,
        )
        return 2
    try:
        result = materialize(armed=True)
    except QualificationRefused as error:
        print(f"Refused: {error}", file=sys.stderr)
        return 2

    if args.out:
        out = Path(args.out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(canonical_json(result) + "\n", encoding="utf-8", newline="\n")
        print(f"Result written to {out}")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
