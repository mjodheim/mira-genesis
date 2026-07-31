from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis.m014b_lab import make_development_demonstrations
from metamorphosis.m014b_policy import train_plasticity_passport


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    passport = train_plasticity_passport(make_development_demonstrations())
    raw = passport.to_json()
    restored = type(passport).from_json(raw)
    if restored.to_json() != raw:
        raise RuntimeError("plasticity passport serialization is not canonical")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(raw, encoding="utf-8")
    print(
        json.dumps(
            {
                "sha256": passport.sha256(),
                "bytes": len(raw.encode("utf-8")),
                "hypothesis_language": list(passport.hypothesis_language),
                "learned_prior": dict(passport.learned_prior),
                "development_provenance_sha256": passport.development_provenance_sha256,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
