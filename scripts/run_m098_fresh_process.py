"""Entry point copied beside the isolated M098 runtime; imports nothing from the repository."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from m098_runtime import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
