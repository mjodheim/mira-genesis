"""Audit that M104 is a fresh population and a mechanism-identical M103 successor."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
M103_POOL = ROOT / "experiments" / "M103" / "QUALIFICATION_POOL.json"
M104_POOL = ROOT / "experiments" / "M104" / "QUALIFICATION_POOL.json"
M103_PROTOCOL = ROOT / "experiments" / "M103" / "PROTOCOL.json"
M104_RESULT = ROOT / "experiments" / "M104" / "RESULT.json"
M104_REPORT = ROOT / "experiments" / "M104" / "CHECK_REPORT.json"
M104_POOL_DIGEST = "a84fa3c5f9c2db51f31f83fa1b910c48f919bdc5c203d548833a7311d7bf1dad"
M104_POOL_RAW_SHA256 = "732e2f46eefef4223e5a715db385639f43ceacf00b27e7c83dff9c15fbf8eb62"


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def _identity_sets(pool: dict[str, Any]) -> dict[str, set[str]]:
    ids: set[str] = set()
    contexts: set[str] = set()
    descriptors: set[str] = set()
    initials: set[str] = set()
    for node in _walk(pool):
        for key in ("demand_id", "case_id", "probe_id", "world_id"):
            if isinstance(node.get(key), str):
                ids.add(node[key])
        if isinstance(node.get("context"), list):
            contexts.update(str(item) for item in node["context"])
        if isinstance(node.get("descriptor"), dict):
            for key in ("section", "option", "value", "old", "new", "path", "content"):
                if key in node["descriptor"]:
                    descriptors.add(json.dumps(node["descriptor"][key], sort_keys=True))
        if "initial" in node:
            initials.add(json.dumps(node["initial"], sort_keys=True))
    return {"ids": ids, "contexts": contexts, "descriptors": descriptors, "initials": initials}


def audit() -> dict[str, Any]:
    m103 = json.loads(M103_POOL.read_text(encoding="ascii"))
    m104 = json.loads(M104_POOL.read_text(encoding="ascii"))
    protocol = json.loads(M103_PROTOCOL.read_text(encoding="ascii"))
    left = _identity_sets(m103)
    right = _identity_sets(m104)
    overlaps = {name: sorted(left[name] & right[name]) for name in left}
    payload = {key: value for key, value in m104.items() if key != "pool_digest"}
    measured = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    ).hexdigest()
    checks = {
        "schema": m104.get("schema") == "m104-qualification-pool-v1",
        "milestone": m104.get("milestone") == "M104",
        "pool_digest": m104.get("pool_digest") == measured == M104_POOL_DIGEST,
        "pool_raw_sha256": hashlib.sha256(M104_POOL.read_bytes()).hexdigest()
        == M104_POOL_RAW_SHA256,
        "complete_population": m104.get("record_count") == 11
        and m104.get("hidden_case_count") == 16
        and len(m104.get("configuration", {}).get("hidden_worlds", [])) == 4
        and len(m104.get("filesystem", {}).get("hidden_worlds", [])) == 4,
        "fresh_identity_categories": all(not overlap for overlap in overlaps.values()),
        "m103_pool_binding": m104.get("m103_pool_raw_sha256")
        == hashlib.sha256(M103_POOL.read_bytes()).hexdigest(),
        "m103_frozen_mechanism_bound": protocol.get("protocol_digest")
        == "cb21a4fa29d9895e477d12f6710eaa4f7c70dfca2e740812fe6846c4ff530de9",
        "canonical_evidence_absent": not M104_RESULT.exists() and not M104_REPORT.exists(),
    }
    report: dict[str, Any] = {
        "schema": "m104-freshness-audit-v1",
        "checks": checks,
        "overlaps": overlaps,
        "confirmed": all(checks.values()),
    }
    report["report_digest"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    ).hexdigest()
    return report


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2, sort_keys=True))
    raise SystemExit(0 if audit()["confirmed"] else 1)

