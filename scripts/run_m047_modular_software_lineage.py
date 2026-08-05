#!/usr/bin/env python3
"""Run M047 and emit its exact bounded modular-software development manifest."""
from __future__ import annotations

import json

from metamorphosis.m047_modular_lineage import (
    run_m047_modular_software_lineage,
)


def main() -> None:
    manifest = run_m047_modular_software_lineage()
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
