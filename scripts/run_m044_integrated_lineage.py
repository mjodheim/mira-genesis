#!/usr/bin/env python3
"""Run the accelerated M044 integrated Mealy lineage and emit its exact manifest."""
from __future__ import annotations

import json

from metamorphosis.m044_integrated_lineage import run_m044_integrated_lineage


def main() -> None:
    manifest = run_m044_integrated_lineage()
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
