"""Temporary unmerged probe: emit the exact pre-arm manifest from frozen main bytes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import check_m092_canonical_guard as guard

ROOT = Path(__file__).resolve().parents[1]
marker: dict[str, object] = {
    "schema": guard.ARM_SCHEMA,
    "frozen_parent_sha": "05518190dd2ca915ede647f02b45679c85d938a6",
    "program_limit": guard.PROGRAM_LIMIT,
    "first_run_only": True,
    "reruns_are_reproductions_only": True,
    "qualification_forbidden": True,
}
for field, relative in guard.BOUND_FILES.items():
    marker[field] = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()

raise RuntimeError("M092_ARM_MANIFEST_JSON=" + json.dumps(marker, sort_keys=True, separators=(",", ":")))
