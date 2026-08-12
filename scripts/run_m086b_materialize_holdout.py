"""M086-B step 2: materialize the holdout, after the adopted mechanism has been committed.

Run in its own process, after phase 1's artifacts exist. It imports the holdout generator and the
bank grammar, and imports no lineage module, so it cannot execute or influence anything the lineage
already did. The record it writes binds the adopted mechanism digest it was generated after.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m086b_holdout import holdout_record  # noqa: E402

BASE = ROOT / "experiments/M086B"
PROTOCOL_PATH = BASE / "PROTOCOL.json"
ADOPTED_PATH = BASE / "ADOPTED_MECHANISM.json"
HOLDOUT_PATH = BASE / "HOLDOUT.json"


def main() -> int:
    if not ADOPTED_PATH.exists():
        raise SystemExit(
            "the adopted mechanism does not exist yet; the holdout may not be materialized "
            "before phase 1 has run and committed it"
        )
    if HOLDOUT_PATH.exists():
        print(f"{HOLDOUT_PATH.name} already materialized; refusing to redraw it")
        return 0

    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    salt = bytes.fromhex(protocol["bank_generation"]["salt_hex"])
    adopted = json.loads(ADOPTED_PATH.read_text(encoding="utf-8"))

    record = holdout_record(salt, adopted["mechanism_digest"])
    record["adopted_artifact_commitment"] = adopted["adopted_commitment"]
    record["lineage_module_imported"] = any(
        name.startswith("metamorphosis.m086b_lineage") for name in sys.modules
    )
    HOLDOUT_PATH.write_bytes(
        json.dumps(record, indent=2, sort_keys=True).encode("utf-8") + b"\n",
    )
    print(f"materialized {HOLDOUT_PATH.name}: {record['holdout_digest']}")
    print(f"  generated after adopted mechanism {adopted['mechanism_digest'][:16]}")
    print(f"  lineage module imported: {record['lineage_module_imported']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
