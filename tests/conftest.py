"""Pytest collection policy for platform-specific historical apparatus.

The M116-M118 audit scripts listed below import :mod:`fcntl` at module import time
because their historical development-only locking/route apparatus was POSIX-only.
Those scripts are frozen scientific history and must not be rewritten merely to make
Windows import them.  Linux continues to collect and execute every one of these tests.

On Windows we therefore exclude only the test modules whose import graph reaches that
POSIX-only apparatus.  Current portable readiness code is deliberately *not* covered by
this exception.
"""

from __future__ import annotations

import sys


if sys.platform == "win32":
    collect_ignore = [
        "test_audit_m116_capacity.py",
        "test_m116_schema_census.py",
        "test_m116_capacity_lifecycle.py",
        "test_m116_capability_matrix.py",
        "test_m117_route_qualification.py",
        "test_m117_stress_rejection.py",
        "test_m117_apparatus_revision.py",
        "test_m118_route_and_readiness.py",
    ]
else:
    collect_ignore: list[str] = []
