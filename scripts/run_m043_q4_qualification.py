"""Reproduce the deterministic M043 Q4 development qualification report."""
from __future__ import annotations

import json

import metamorphosis.m043_validation_worker as validation_worker
from metamorphosis.m043_adoption import run_q4_development_qualification


def main() -> int:
    if validation_worker.__name__ != "metamorphosis.m043_validation_worker":
        raise RuntimeError("unexpected Q4 validation-worker identity")
    print(
        json.dumps(
            run_q4_development_qualification(),
            sort_keys=True,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
