"""Run M099's frozen stable hard-persistence qualification locally."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from author_m099_qualification_pool import (  # noqa: E402
    OUTPUT as POOL_PATH,
    audit as audit_pool,
    canonical_json,
    digest,
    load_pool,
)
from run_m095_qualification import file_set_digest  # noqa: E402
from run_m098_qualification import (  # noqa: E402
    M097_RESULT_PATH,
    QualificationRefused,
    run_experiment as run_process_experiment,
)

EXPERIMENT = ROOT / "experiments" / "M099"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
M098_RESULT_PATH = ROOT / "experiments" / "M098" / "RESULT.json"
M098_CHECK_PATH = ROOT / "experiments" / "M098" / "CHECK_REPORT.json"
RESULT_SCHEMA = "m099-result-v1"
EPHEMERAL_KEYS = frozenset({"pid", "producer_pid", "consumer_pids", "search_path"})


def stable_projection(value: object) -> object:
    """Remove all frozen process/location ephemera, including aggregate PID lists."""
    if isinstance(value, dict):
        return {
            key: stable_projection(item)
            for key, item in value.items()
            if key not in EPHEMERAL_KEYS
        }
    if isinstance(value, list):
        return [stable_projection(item) for item in value]
    return value


def mechanism_digest(protocol: dict[str, object]) -> tuple[str, dict[str, str]]:
    return file_set_digest(protocol, "mechanism")


def require_frozen(protocol: dict[str, object], pool: dict[str, object]) -> None:
    if protocol.get("status") != "frozen" or pool.get("status") != "frozen":
        raise QualificationRefused("M099 protocol or pool is not frozen")
    if protocol.get("qualification_population", {}).get("pool_digest") != pool.get("pool_digest"):
        raise QualificationRefused("M099 protocol does not bind this pool")
    m097 = json.loads(M097_RESULT_PATH.read_text(encoding="utf-8"))
    m098 = json.loads(M098_RESULT_PATH.read_text(encoding="utf-8"))
    m098_check = json.loads(M098_CHECK_PATH.read_text(encoding="utf-8"))
    inputs = protocol.get("preserved_inputs", {})
    if inputs.get("m097_result_digest") != m097.get("result_digest"):
        raise QualificationRefused("M097 result differs from the frozen M099 input")
    state = m097.get("scientific_evidence", {}).get("extended_language_state", {})
    if inputs.get("m097_state_digest") != state.get("state_digest"):
        raise QualificationRefused("M097 state differs from the frozen M099 input")
    if inputs.get("m098_result_digest") != m098.get("result_digest"):
        raise QualificationRefused("M098 result differs from the frozen M099 input")
    if inputs.get("m098_checker_digest") != m098_check.get("report_digest"):
        raise QualificationRefused("M098 checker differs from the frozen M099 input")
    measured, _members = mechanism_digest(protocol)
    apparatus, _apparatus_members = file_set_digest(protocol, "qualification_apparatus")
    if protocol.get("mechanism", {}).get("digest") != measured:
        raise QualificationRefused("M099 persistence mechanism moved after freeze")
    if protocol.get("qualification_apparatus", {}).get("digest") != apparatus:
        raise QualificationRefused("M099 apparatus moved after freeze")


def run_experiment(pool: dict[str, object]) -> dict[str, object]:
    return run_process_experiment(pool)


def materialize(*, armed: bool = False) -> dict[str, object]:
    if not armed:
        raise QualificationRefused("M099 result acquisition requires --arm")
    result_path = EXPERIMENT / "RESULT.json"
    if result_path.exists():
        raise QualificationRefused("M099 RESULT.json exists; overwrite and rerun are forbidden")
    protocol_bytes = PROTOCOL_PATH.read_bytes()
    protocol = json.loads(protocol_bytes.decode("utf-8"))
    pool = load_pool()
    require_frozen(protocol, pool)
    source_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    dirty = bool(subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT,
        capture_output=True, text=True, check=True
    ).stdout.strip())
    if dirty:
        raise QualificationRefused("commit the frozen M099 apparatus before arming")
    if not audit_pool(pool)["passed"]:
        raise QualificationRefused("M099 frozen pool fails preflight")
    started = time.time()
    evidence = run_experiment(pool)
    measured, members = mechanism_digest(protocol)
    apparatus, apparatus_members = file_set_digest(protocol, "qualification_apparatus")
    m097 = json.loads(M097_RESULT_PATH.read_text(encoding="utf-8"))
    m098 = json.loads(M098_RESULT_PATH.read_text(encoding="utf-8"))
    m098_check = json.loads(M098_CHECK_PATH.read_text(encoding="utf-8"))
    withdrawn = sorted(path.name for path in EXPERIMENT.glob("WITHDRAWN_RESULT_*.json"))
    result = {
        "schema": RESULT_SCHEMA,
        "milestone": "M099",
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
        "m097_result_digest": m097["result_digest"],
        "m097_state_digest": m097["scientific_evidence"]["extended_language_state"]["state_digest"],
        "m098_result_digest": m098["result_digest"],
        "m098_checker_digest": m098_check["report_digest"],
        "mechanism_digest": measured,
        "mechanism_members": members,
        "qualification_apparatus_digest": apparatus,
        "qualification_apparatus_members": apparatus_members,
        "scientific_evidence": evidence,
        "stable_evidence_digest": digest(stable_projection(evidence)),
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
        print("Refusing to acquire M099 without --arm.", file=sys.stderr)
        return 2
    if not args.out or Path(args.out).resolve() != expected:
        print("An armed run must write exactly experiments/M099/RESULT.json.", file=sys.stderr)
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
