"""M086-C phase 1: development, meta-search and adoption. No holdout exists while this runs.

Writes the adopted mechanism and a phase record. It imports the bank grammar and never imports the
holdout module, so the holdout it must not see does not exist in this process at all.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m086_evolvable_mechanism import Mechanism  # noqa: E402
from metamorphosis.m086c_bank import (  # noqa: E402
    GENERATOR_VERSION,
    bank_digest,
    body_from_shape,
    development_public,
    draw_shape,
)
from metamorphosis.m086b_lineage import ARMS, canonical, digest_of  # noqa: E402
from metamorphosis.m086c_lineage import run_phase1_arm  # noqa: E402

BASE = ROOT / "experiments/M086C"
PROTOCOL_PATH = BASE / "PROTOCOL.json"
BANK_PATH = BASE / "BANK_COMMITMENT.json"
PRE_ADOPTION_PATH = BASE / "PRE_ADOPTION_MECHANISM.json"
ADOPTED_PATH = BASE / "ADOPTED_MECHANISM.json"
PHASE1_PATH = BASE / "PHASE1.json"


def _write_once(path: Path, payload: dict, digest_key: str) -> dict:
    payload[digest_key] = hashlib.sha256(canonical(
        {key: value for key, value in payload.items() if key != digest_key},
    )).hexdigest()
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get(digest_key) != payload[digest_key]:
            raise SystemExit(f"refusing to overwrite {path.name} with a different {digest_key}")
        print(f"{path.name} already bound: {payload[digest_key]}")
        return existing
    path.write_bytes(json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    print(f"bound {path.name}: {payload[digest_key]}")
    return payload


def main() -> int:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol["bank_generation"]["generator_version"] != GENERATOR_VERSION:
        raise SystemExit("generator version drifted from the frozen protocol")
    salt = bytes.fromhex(protocol["bank_generation"]["salt_hex"])

    shape = draw_shape(salt, "development")
    _write_once(BANK_PATH, {
        "schema": "m086c-bank-commitment-v1",
        "generator_version": GENERATOR_VERSION,
        "protocol_commitment": hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest(),
        "shape": shape.to_dict(),
        "starting_body_digest": body_from_shape(shape).digest(),
        "development_public": [case.to_dict() for case in development_public(salt)],
        "bank_digest": bank_digest(salt),
    }, "bank_commitment")

    # The independent pre-adoption record. Written here, by a caller the adoption transaction cannot
    # reach, so P8's comparison is never against the checkpoint the transaction itself holds.
    independent: dict[str, str] = {}

    def write_independent_record(arm: str, mechanism: Mechanism) -> str:
        independent[arm] = mechanism.digest()
        independent[f"{arm}_bytes_sha256"] = hashlib.sha256(
            canonical(mechanism.to_dict()),
        ).hexdigest()
        return mechanism.digest()

    arms = {arm: run_phase1_arm(arm, salt, write_independent_record) for arm in ARMS}

    _write_once(PRE_ADOPTION_PATH, {
        "schema": "m086c-pre-adoption-mechanism-v1",
        "written_before_any_adoption_transaction": True,
        "records": independent,
    }, "pre_adoption_commitment")

    adopted = arms["evolvable_meta"]["mechanism_carried_to_holdout"]
    adopted_record = _write_once(ADOPTED_PATH, {
        "schema": "m086c-adopted-mechanism-v1",
        "mechanism": adopted,
        "mechanism_digest": arms["evolvable_meta"]["mechanism_carried_digest"],
        "adopted_primitives": arms["evolvable_meta"]["adopted_primitives"],
    }, "adopted_commitment")

    _write_once(PHASE1_PATH, {
        "schema": "m086c-phase1-v1",
        "protocol_commitment": hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest(),
        "bank_commitment": json.loads(BANK_PATH.read_text(encoding="utf-8"))["bank_commitment"],
        "adopted_commitment": adopted_record["adopted_commitment"],
        "python": platform.python_version(),
        "inputs_read": ["PROTOCOL.json", "the bank grammar"],
        "holdout_digest_seen": None,
        "holdout_module_imported": "metamorphosis.m086c_holdout" in sys.modules,
        "arms": arms,
        "arms_digest": digest_of(arms),
    }, "phase1_commitment")

    for arm in ARMS:
        record = arms[arm]
        print(
            f"  {arm:26} adopted={record['meta_transformations_adopted']}"
            f" primitives={record['adopted_primitives']}"
            f" dev_solved={record['development_solved']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
