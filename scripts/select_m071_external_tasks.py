"""Apply the frozen M071 identifier-only rule to a pinned Git task tree."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Mapping

from mira_core.process import run_utf8_process


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "experiments" / "M071" / "SELECTION_PROTOCOL.json"


def _protocol_commit(protocol_path: Path) -> str | None:
    if Path(protocol_path).resolve() != PROTOCOL.resolve():
        return None
    completed = run_utf8_process(
        ("git", "log", "-1", "--format=%H", "--", str(PROTOCOL.relative_to(ROOT))),
        cwd=ROOT, timeout_seconds=30,
    )
    return completed.stdout.strip() or None


def select(repo: Path, protocol_path: Path = PROTOCOL) -> Mapping[str, object]:
    protocol = json.loads(Path(protocol_path).read_text(encoding="utf-8"))
    if protocol.get("schema") != "m071-external-selection-protocol-v1":
        raise ValueError("unexpected M071 selection protocol schema")
    commit = protocol["benchmark_revision"]
    completed = run_utf8_process(
        ("git", "-C", str(Path(repo)), "ls-tree", "-r", "--name-only", commit),
        timeout_seconds=60,
    )
    if completed.returncode != 0:
        raise ValueError((completed.stderr or completed.stdout).strip())
    paths = sorted(
        line.strip() for line in completed.stdout.splitlines()
        if line.strip().endswith("/task.toml")
    )
    if not paths:
        raise ValueError("pinned benchmark tree contains no task.toml files")
    excluded = set(protocol["excluded_identifiers"])
    salt = bytes.fromhex(protocol["selection_salt_hex"])
    inventory: list[list[str]] = []
    seen: set[str] = set()
    excluded_observed: list[str] = []
    for path in paths:
        identifier = path.rsplit("/", 2)[-2]
        if identifier in seen:
            raise ValueError(f"duplicate task identifier: {identifier}")
        seen.add(identifier)
        if identifier in excluded:
            excluded_observed.append(identifier)
            continue
        digest = hashlib.sha256(salt + identifier.encode("utf-8")).hexdigest()
        inventory.append([digest, identifier])
    missing_exclusions = excluded - set(excluded_observed)
    if missing_exclusions:
        raise ValueError(f"pinned tree lacks required exclusions: {sorted(missing_exclusions)}")
    inventory.sort()
    count = protocol["selection_count"]
    if not isinstance(count, int) or count < 1 or len(inventory) < count:
        raise ValueError("eligible inventory is smaller than the frozen selection count")
    selected = inventory[:count]
    return {
        "schema": "m071-external-task-selection-v1",
        "benchmark_repository": protocol["benchmark_repository"],
        "benchmark_revision": commit,
        "selection_protocol_commit": _protocol_commit(Path(protocol_path)),
        "selection_count": count,
        "replacement_permitted": protocol["replacement_permitted"],
        "all_identifier_count": len(seen),
        "excluded_identifiers": sorted(excluded_observed),
        "eligible_inventory_count": len(inventory),
        "inventory_pair_schema": ["selection_sha256", "task_identifier"],
        "inventory": inventory,
        "inventory_sha256": hashlib.sha256(json.dumps(
            inventory, separators=(",", ":"), ensure_ascii=False,
        ).encode("utf-8")).hexdigest(),
        "selected": selected,
        "fresh_task_content_inspected_before_selection": False,
        "fresh_task_executed": False,
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
