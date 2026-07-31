from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from m012b_eval_support import source_isolation_audit


def main() -> None:
    audit = source_isolation_audit()
    print(json.dumps(audit, indent=2))
    if not audit["passed"] or audit["runtime_nonce_calls_in_runner"] != 1:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
