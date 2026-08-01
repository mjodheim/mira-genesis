"""Aggregate exact M021 seed shards into one development result."""

from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

from run_m021_measure_comparison import summarize_rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-glob", required=True)
    parser.add_argument("--expected-seeds", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()

    paths = [Path(path) for path in sorted(glob.glob(arguments.input_glob))]
    if not paths:
        parser.error("the input glob matched no shard")

    rows: list[dict[str, object]] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows.extend(payload["runs"])

    summary = summarize_rows(rows)
    if int(summary["seeds"]) != arguments.expected_seeds:
        raise SystemExit(
            f"aggregated {summary['seeds']} paired seeds, expected {arguments.expected_seeds}"
        )

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps({"summary": summary, "runs": rows}, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
