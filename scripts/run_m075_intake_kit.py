"""Command line entry point for the independent M075 task-bank maintainer intake kit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m075_intake_kit import (  # noqa: E402
    instructions,
    template,
    validate,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--template", action="store_true", help="print a skeleton envelope")
    group.add_argument("--instructions", action="store_true", help="print the signing commands")
    group.add_argument("--validate", type=Path, help="check a candidate envelope before sending")
    parser.add_argument(
        "--signature-verified", action="store_true",
        help="assert that ssh-keygen -Y verify already succeeded for this envelope",
    )
    arguments = parser.parse_args()

    if arguments.template:
        print(json.dumps(template(), indent=2, sort_keys=True))
        return 0
    if arguments.instructions:
        print(instructions())
        return 0
    return validate(arguments.validate, signature_verified=arguments.signature_verified)


if __name__ == "__main__":
    raise SystemExit(main())
