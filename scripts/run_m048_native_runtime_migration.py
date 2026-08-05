#!/usr/bin/env python3
"""Run M048 and emit its bounded native migration development manifest."""
from __future__ import annotations

import json

from metamorphosis.m048_runtime_migration import (
    run_m048_native_runtime_migration,
)


def main() -> None:
    manifest = run_m048_native_runtime_migration()
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
