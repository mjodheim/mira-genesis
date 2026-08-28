"""Legitimate entry point for the pure DEVELOPMENT M115/H60 candidate derivation.

This wrapper exists so repository-integrity reachability remains explicit. It performs no network
calls, sends no qualifying input, creates no bank, and consumes no freeze or gate.
"""

from scripts.derive_m115_h60_candidate import main


if __name__ == "__main__":
    raise SystemExit(main())
