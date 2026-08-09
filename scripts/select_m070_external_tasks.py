"""Apply the frozen M070 identifier-only selection rule to a pinned Git task tree."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "experiments" / "M070" / "SELECTION_PROTOCOL.json"


def select(repo: Path, protocol_path: Path = PROTOCOL) -> Mapping[str, object]:
    protocol = json.loads(Path(protocol_path).read_text(encoding="utf-8"))
    commit = protocol["benchmark_revision"]
    completed = subprocess.run(
        ["git", "-C", str(Path(repo)), "ls-tree", "-r", "--name-only", commit],
        capture_output=True, text=True, check=False,
    )
    if completed.returncode != 0:
        raise ValueError((completed.stderr or completed.stdout).strip())
    paths = sorted(
        line.strip() for line in completed.stdout.splitlines()
        if line.strip().endswith("/task.toml")
    )
    if not paths:
        raise ValueError("pinned benchmark tree contains no task.toml files")
    salt = bytes.fromhex(protocol["selection_salt_utf8_hex"])
    inventory: list[list[str]] = []
    seen: set[str] = set()
    for path in paths:
        identifier = path.rsplit("/", 2)[-2]
        if identifier in seen:
            raise ValueError(f"duplicate task identifier: {identifier}")
        seen.add(identifier)
        digest = hashlib.sha256(salt + identifier.encode("utf-8")).hexdigest()
        inventory.append([digest, identifier])
    inventory.sort()
    count = protocol["selection_count"]
    selected = inventory[:count]
    return {
        "schema": "m070-external-task-selection-v1",
        "benchmark_repository": protocol["benchmark_repository"],
        "benchmark_revision": commit,
        "selection_protocol_commit": subprocess.check_output(
            ["git", "-C", str(ROOT), "log", "-1", "--format=%H", "--",
             "experiments/M070/SELECTION_PROTOCOL.json"], text=True,
        ).strip(),
        "selection_count": count,
        "replacement_permitted": protocol["replacement_permitted"],
        "inventory_count": len(inventory),
        "inventory_pair_schema": ["selection_sha256", "task_identifier"],
        "inventory": inventory,
        "inventory_sha256": hashlib.sha256(json.dumps(
            inventory, separators=(",", ":"), ensure_ascii=False,
        ).encode("utf-8")).hexdigest(),
        "selected": selected,
        "task_content_inspected_before_selection": False,
        "task_executed": False,
        "scientific_result_exists": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(select(args.repo), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
