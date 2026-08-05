"""Reproduce the deterministic M043 Q5 development qualification report."""
from __future__ import annotations

import json

from metamorphosis.m043_migration import run_q5_development_qualification
from metamorphosis import m043_opaque_substrate as _opaque_entry_point


def main() -> int:
    # The explicit import keeps the dynamically used substrate module visible to the
    # repository-integrity graph while the qualification itself uses the public facade.
    assert _opaque_entry_point.OpaqueFieldMachine is not None
    print(
        json.dumps(
            run_q5_development_qualification(),
            sort_keys=True,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
