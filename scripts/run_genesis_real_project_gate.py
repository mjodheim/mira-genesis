#!/usr/bin/env python3
"""Run the bounded Genesis real-project gate from a host-owned JSON manifest."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from genesis import real_project


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host-root", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    try:
        report = real_project.run_gate(
            args.host_root,
            manifest,
            output_directory=args.output_dir,
        )
    except real_project.RealProjectError as problem:
        print(json.dumps({"passed": False, "error": str(problem)}, ensure_ascii=False))
        return 2

    print(
        json.dumps(
            {
                "classification": report["classification"],
                "passed": report["passed"],
                "selected_candidate_id": report["selected_candidate_id"],
                "report_digest": report["report_digest"],
            },
            sort_keys=True,
        )
    )
    return 0 if report["passed"] else 3


if __name__ == "__main__":
    sys.exit(main())
