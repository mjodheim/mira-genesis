from __future__ import annotations

import json

from metamorphosis.m050_primitive_composition import run_m050_bounded_primitive_composition


def main() -> None:
    print(json.dumps(run_m050_bounded_primitive_composition(), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
