"""Run M067's class-wide development qualification and emit canonical JSON."""
from __future__ import annotations

import json

from metamorphosis.m067_body_contract import run_m067_development


def main() -> int:
    manifest = run_m067_development()
    print(json.dumps(manifest.to_dict(), indent=2, sort_keys=True))
    print(f"manifest_sha256={manifest.digest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
