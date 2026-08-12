"""M086-C step 3: run every arm against the materialized holdout and preserve the first result.

Reads the holdout from an artifact that did not exist when phase 1 ran, carries each arm's mechanism
forward from `PHASE1.json`, evaluates P1 through P10, and writes `RESULT.json` once.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m047_runtime_sandbox import run_body_in_sandbox  # noqa: E402
from metamorphosis.m047_search_diagnosis import diagnose_limiting_module  # noqa: E402
from metamorphosis.m047_search_templates import _candidate_sources  # noqa: E402
from metamorphosis.m047_software_body import SoftwareCase  # noqa: E402
from metamorphosis.m047_software_tools import founder_software_body  # noqa: E402
from metamorphosis.m086_evolvable_mechanism import (  # noqa: E402
    Mechanism,
    Rule,
    diagnose,
    generate,
    m0_mechanism,
)
from metamorphosis.m086c_bank import body_from_shape, draw_shape  # noqa: E402
from metamorphosis.m086c_holdout import cases_from_record  # noqa: E402
from metamorphosis.m086b_lineage import (  # noqa: E402
    ARMS,
    canonical,
    digest_of,
    enumerate_starting_image,
    evaluate,
    run_holdout_arm,
)

BASE = ROOT / "experiments/M086C"
PROTOCOL_PATH = BASE / "PROTOCOL.json"
PHASE1_PATH = BASE / "PHASE1.json"
ADOPTED_PATH = BASE / "ADOPTED_MECHANISM.json"
HOLDOUT_PATH = BASE / "HOLDOUT.json"
RESULT_PATH = BASE / "RESULT.json"

DIFFERENTIAL_PROBES = (
    ("unknown token", ("plus 4 5", 9)),
    ("missing route", ("mean 1 2 3", 2.0)),
    ("already passing", ("add 2 3", 5)),
)


def mechanism_from_dict(payload: dict) -> Mechanism:
    return Mechanism(
        schema=str(payload["schema"]),
        rules=tuple(
            Rule(
                rule_id=str(rule["rule_id"]), module=str(rule["module"]),
                requires=str(rule["requires"]), options=tuple(rule["options"]),
                parameterized=bool(rule["parameterized"]), relaxed=bool(rule["relaxed"]),
            )
            for rule in payload["rules"]
        ),
        composes=bool(payload["composes"]),
        provenance=tuple(payload["provenance"]),
    )


def differential_equivalence(salt: bytes) -> dict:
    """P10, computed here so it can enter the verdict rather than living only in a checker."""

    mechanism = m0_mechanism()
    probes = 0
    equivalent = True
    for body_label, body in (
        ("bank", body_from_shape(draw_shape(salt, "development"))),
        ("founder", founder_software_body()),
    ):
        for label, (request, expected) in DIFFERENTIAL_PROBES:
            executed = run_body_in_sandbox(
                body, (SoftwareCase("p", request, expected, "probe"),), timeout_seconds=60.0,
            )
            old = diagnose_limiting_module(executed.cases)
            new = diagnose(mechanism, executed.cases)
            same_diagnosis = ((old.module,) if old.module else ()) == new.modules
            old_sets = sorted(
                tuple(sorted(item.items()))
                for _, item in (_candidate_sources(body, old) if old.sufficient else ())
            )
            new_sets = sorted(
                tuple(sorted(item.items())) for _, item in generate(mechanism, body, new)
            )
            if not (same_diagnosis and old_sets == new_sets):
                equivalent = False
            probes += 1
    return {"equivalent": equivalent, "probes": probes}


def chronology(phase1: dict, holdout: dict, adopted: dict) -> dict:
    """P9, proved from recorded digests rather than from the absence of a reference."""

    checks = {
        "phase1_saw_no_holdout": phase1.get("holdout_digest_seen") is None,
        "phase1_did_not_import_the_holdout_module": phase1.get("holdout_module_imported") is False,
        "holdout_records_the_adopted_mechanism": (
            holdout.get("generated_after_adopted_mechanism_digest") == adopted["mechanism_digest"]
        ),
        "holdout_records_the_adopted_artifact": (
            holdout.get("adopted_artifact_commitment") == adopted["adopted_commitment"]
        ),
        "holdout_generator_did_not_import_the_lineage": (
            holdout.get("lineage_module_imported") is False
        ),
        "phase1_binds_the_same_adopted_artifact": (
            phase1.get("adopted_commitment") == adopted["adopted_commitment"]
        ),
    }
    return {
        "ordered": all(checks.values()),
        "checks": checks,
        "detail": ", ".join(f"{name}={value}" for name, value in checks.items()),
    }


def main() -> int:
    for path in (PHASE1_PATH, ADOPTED_PATH, HOLDOUT_PATH):
        if not path.exists():
            raise SystemExit(f"{path.name} is missing; the phases must run in order")

    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    salt = bytes.fromhex(protocol["bank_generation"]["salt_hex"])
    phase1 = json.loads(PHASE1_PATH.read_text(encoding="utf-8"))
    adopted = json.loads(ADOPTED_PATH.read_text(encoding="utf-8"))
    holdout = json.loads(HOLDOUT_PATH.read_text(encoding="utf-8"))

    holdout_body = body_from_shape(draw_shape(salt, "holdout"))
    public = cases_from_record(holdout["public"])
    hidden = cases_from_record(holdout["hidden"])

    image = enumerate_starting_image(holdout_body, public)
    print(f"starting mechanism image for the holdout: {image['candidate_count']} candidates")

    holdout_arms = {}
    for arm in ARMS:
        carried = mechanism_from_dict(phase1["arms"][arm]["mechanism_carried_to_holdout"])
        print(f"running {arm} on the holdout ...", flush=True)
        holdout_arms[arm] = run_holdout_arm(arm, carried, holdout_body, public, hidden)

    verdict = evaluate(
        phase1["arms"], holdout_arms, image,
        chronology(phase1, holdout, adopted),
        differential_equivalence(salt),
    )

    payload = {
        "schema": "m086c-result-v1",
        "protocol_commitment": hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest(),
        "bank_commitment": phase1["bank_commitment"],
        "phase1_commitment": phase1["phase1_commitment"],
        "holdout_digest": holdout["holdout_digest"],
        "adopted_commitment": adopted["adopted_commitment"],
        "attempt": 1,
        "retried": False,
        "external_model_called": False,
        "network_opened": False,
        "python": platform.python_version(),
        "starting_mechanism_image_on_holdout": image,
        "chronology": chronology(phase1, holdout, adopted),
        "differential_equivalence": differential_equivalence(salt),
        "phase1_arms": phase1["arms"],
        "holdout_arms": holdout_arms,
        "complete_record_digest": digest_of(
            {"phase1": phase1["arms"], "holdout": holdout_arms, "image": image},
        ),
        "verdict_table": verdict.to_dict(),
        "verdict": "positive" if verdict.positive else "negative",
        "claim_boundary": protocol["claim_boundary"],
    }
    payload["result_sha256"] = hashlib.sha256(canonical(
        {key: value for key, value in payload.items() if key != "result_sha256"},
    )).hexdigest()

    if RESULT_PATH.exists():
        existing = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
        if existing.get("result_sha256") != payload["result_sha256"]:
            raise SystemExit("refusing to overwrite a preserved result with a different digest")
        print("result already preserved and identical")
    else:
        RESULT_PATH.write_bytes(
            json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n",
        )
        print(f"preserved RESULT.json: {payload['result_sha256']}")

    print(f"\nverdict: {payload['verdict']}")
    for name in ("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10"):
        mark = "PASS" if verdict.conditions[name] else "FAIL"
        print(f"  {name:4} {mark:5} {verdict.reasons[name]}")
    return 0 if verdict.positive else 1


if __name__ == "__main__":
    raise SystemExit(main())
