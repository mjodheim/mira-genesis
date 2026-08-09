"""Run the M068 open command-language induction development experiment."""
from __future__ import annotations

import json

from metamorphosis.m068_open_command_induction import run_m068_development


def main() -> int:
    manifest = run_m068_development()
    print(json.dumps({**manifest.to_dict(), "manifest_digest": manifest.digest()}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
