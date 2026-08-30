"""M115's post-seal lifecycle: freeze the tested system or authorize its single reveal."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from authorize_m115_reveal import main as authorize_reveal
from freeze_m115_system import main as freeze_system


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze-system", action="store_true")
    mode.add_argument("--authorize-reveal", action="store_true")
    arguments = parser.parse_args()
    return freeze_system() if arguments.freeze_system else authorize_reveal()


if __name__ == "__main__":
    raise SystemExit(main())
