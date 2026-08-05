#!/usr/bin/env python3
"""Run M046 and emit the deterministic scalable-lineage manifest."""
from __future__ import annotations

import json

from metamorphosis.m046_scalable_lineage import run_m046_scalable_lineage


def main() -> None:
    manifest = run_m046_scalable_lineage()
    print(
        json.dumps(
            {
                "manifest": manifest.to_dict(),
                "manifest_sha256": manifest.digest(),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()
