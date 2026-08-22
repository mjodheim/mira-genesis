"""Run M096's frozen contract-safe qualification once, locally.

Every frozen population member is evaluated in two byte-independent worlds: the
M096 exact-contract mechanism and the inherited M095 subset-contract mechanism.  The
paired legacy arm measures sensitivity to the contract change under the same world,
operation language, search bound and execution environment.  Its outcome is reported,
but the historical M095 negative result is not silently replaced by this new arm.
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

from metamorphosis import m095_chain as legacy_chain  # noqa: E402
from metamorphosis import m096_contracts as exact_chain  # noqa: E402
from author_m095_qualification_pool import build_world  # noqa: E402
from author_m096_qualification_pool import (  # noqa: E402
    OUTPUT as POOL_PATH,
    audit as audit_pool,
    canonical_json,
    digest,
    load_pool,
)
from run_m095_qualification import _entry_record, file_set_digest  # noqa: E402

EXPERIMENT = ROOT / "experiments" / "M096"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
RESULT_SCHEMA = "m096-result-v1"


class QualificationRefused(RuntimeError):
    """The requested action would cross M096's frozen boundary."""


def mechanism_digest(protocol: dict[str, object]) -> tuple[str, dict[str, str]]:
    try:
        return file_set_digest(protocol, "mechanism")
    except Exception as error:  # normalize the inherited helper's exception type
        raise QualificationRefused(str(error)) from error


def require_frozen(protocol: dict[str, object], pool: dict[str, object]) -> None:
    if protocol.get("status") != "frozen":
        raise QualificationRefused("M096 protocol is not frozen")
    if pool.get("status") != "frozen":
        raise QualificationRefused("M096 qualification pool is not frozen")
    expected = protocol.get("qualification_population", {}).get("pool_digest")
    if expected != pool.get("pool_digest"):
        raise QualificationRefused("the frozen protocol does not bind this pool digest")
    measured, _members = mechanism_digest(protocol)
    if protocol.get("mechanism", {}).get("digest") != measured:
        raise QualificationRefused("the M096 mechanism moved after freeze")
    apparatus, _apparatus_members = file_set_digest(protocol, "qualification_apparatus")
    if protocol.get("qualification_apparatus", {}).get("digest") != apparatus:
        raise QualificationRefused("the M096 qualification apparatus moved after freeze")


def paired_entry_record(
    entry: dict[str, object], exact, legacy
) -> dict[str, object]:
    return {
        "entry": entry["id"],
        "entry_digest": entry["entry_digest"],
        "structure": entry["structure"],
        "arrangement": entry["arrangement"],
        "expected_relation": entry["expected_relation"],
        "expected_descent": entry["expected_descent"],
        "contract_safe": _entry_record(entry, exact),
        "legacy_subset": _entry_record(entry, legacy),
    }


def replay_population(pool: dict[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="m096-qualification-") as temporary:
        base = Path(temporary)
        for entry in pool["entries"]:
            exact_root = base / "exact" / "primary" / str(entry["id"])
            exact_counterfactual = base / "exact" / "counterfactual" / str(entry["id"])
            legacy_root = base / "legacy" / "primary" / str(entry["id"])
            legacy_counterfactual = base / "legacy" / "counterfactual" / str(entry["id"])
            for root in (exact_root, exact_counterfactual, legacy_root, legacy_counterfactual):
                build_world(root, pool, entry)
            exact = exact_chain.run_existing(exact_root, exact_counterfactual)
            legacy = legacy_chain.run_existing(legacy_root, legacy_counterfactual)
            rows.append(paired_entry_record(entry, exact, legacy))
    return rows


def materialize(*, armed: bool = False) -> dict[str, object]:
    if not armed:
        raise QualificationRefused(
            "running the frozen population acquires the M096 result and requires arming"
        )
    if (EXPERIMENT / "RESULT.json").exists():
        raise QualificationRefused("RESULT.json already exists; no overwrite or rerun is allowed")

    protocol_bytes = PROTOCOL_PATH.read_bytes()
    protocol = json.loads(protocol_bytes.decode("utf-8"))
    pool = load_pool()
    require_frozen(protocol, pool)

    try:
        source_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        )
    except Exception as error:  # noqa: BLE001
        raise QualificationRefused(f"source commit could not be resolved: {error}") from error
    if dirty:
        raise QualificationRefused(
            "the working tree is dirty; commit the complete frozen apparatus before arming"
        )

    preflight = audit_pool(pool)
    if not preflight["passed"]:
        raise QualificationRefused("the frozen population no longer passes its S0 audit")

    measured_mechanism, mechanism_members = mechanism_digest(protocol)
    started = time.time()
    rows = replay_population(pool)
    positives = [row for row in rows if row["expected_relation"]]
    negatives = [row for row in rows if not row["expected_relation"]]
    partial = [row for row in positives if row["structure"] != "complete_minimal_contract"]
    complete = [row for row in positives if row["structure"] == "complete_minimal_contract"]
    withdrawn = sorted(path.name for path in EXPERIMENT.glob("WITHDRAWN_RESULT_*.json"))
    result: dict[str, object] = {
        "schema": RESULT_SCHEMA,
        "milestone": "M096",
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
        "remote_execution": False,
        "attempt": len(withdrawn) + 1,
        "prior_attempts": withdrawn,
        "population_is_exhaustive": True,
        "entries_run": len(rows),
        "entries": rows,
        "qualification_summary": {
            "positive_entries": len(positives),
            "contract_safe_positive_demonstrated": sum(
                bool(row["contract_safe"]["enabling_demonstrated"]) for row in positives
            ),
            "negative_entries": len(negatives),
            "contract_safe_negative_remained_negative": sum(
                not bool(row["contract_safe"]["enabling_demonstrated"]) for row in negatives
            ),
            "partial_contract_entries": len(partial),
            "partial_contract_legacy_failed": sum(
                not bool(row["legacy_subset"]["enabling_demonstrated"]) for row in partial
            ),
            "complete_contract_entries": len(complete),
            "complete_contract_legacy_liveness": sum(
                bool(row["legacy_subset"]["enabling_demonstrated"]) for row in complete
            ),
        },
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
        print("Refusing to acquire M096 without --arm.", file=sys.stderr)
        return 2
    if not args.out or Path(args.out).resolve() != expected:
        print("An armed run must write exactly experiments/M096/RESULT.json.", file=sys.stderr)
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
