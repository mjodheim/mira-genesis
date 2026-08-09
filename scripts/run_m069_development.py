"""Run the M069 governed real-terminal development experiment."""
from __future__ import annotations

import json

from metamorphosis.m069_governed_terminal_repair import run_m069_development


def main() -> int:
    manifest = run_m069_development()
    print(json.dumps({**manifest.to_dict(), "manifest_digest": manifest.digest()}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
