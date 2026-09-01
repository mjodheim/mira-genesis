#!/usr/bin/env python3
"""Independently replay and check an M117 Stage 1 route-qualification record.

The checker recomputes, from committed artifacts alone: the frozen plan digest, the candidate
universe and its order, each candidate's qualification, and the selection. It agrees with the
recorded result or it fails. It never contacts a network, never reads a completion, and never
recomputes an *observation* -- observations are what was seen and are not re-derivable.

It also refuses a record whose chronology cannot be proven: the plan must be the one the universe
was derived under, the universe must be the one the probes were run against, and the selection must
follow from the frozen order and the recorded qualifications alone.

    python scripts/check_m117_stage1.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metamorphosis import m117_route_qualification as rule  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex  # noqa: E402
from scripts import audit_m117_route_qualification as stage1  # noqa: E402


class Stage1CheckError(RuntimeError):
    """The Stage 1 record does not replay. Every path fails closed."""


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise Stage1CheckError("missing artifact: %s" % path.relative_to(ROOT))
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Stage1CheckError("cannot read %s: %s" % (path.relative_to(ROOT), exc))


def _digest_of(record: dict[str, Any], field: str) -> str:
    return sha256_hex(canonical_bytes({k: v for k, v in record.items() if k != field}))


def check() -> dict[str, Any]:
    findings: list[str] = []
    universe = _load(stage1.UNIVERSE_PATH)
    report = _load(stage1.REPORT_PATH)
    catalogue = _load(stage1.CATALOGUE_PATH)
    frozen = stage1.plan()

    # 1. Self-consistency of every committed digest.
    if universe.get("universe_sha256") != _digest_of(universe, "universe_sha256"):
        findings.append("the candidate universe digest does not match its contents")
    if report.get("report_sha256") != _digest_of(report, "report_sha256"):
        findings.append("the Stage 1 report digest does not match its contents")
    if catalogue.get("snapshot_sha256") != _digest_of(catalogue, "snapshot_sha256"):
        findings.append("the catalogue snapshot digest does not match its contents")

    # 2. Chronology: one plan, one universe, one catalogue, all the way through.
    if universe.get("plan_sha256") != frozen["plan_sha256"]:
        findings.append("the universe was derived under a different frozen plan")
    if report.get("plan_sha256") != frozen["plan_sha256"]:
        findings.append("the report was produced under a different frozen plan")
    if report.get("universe_sha256") != universe.get("universe_sha256"):
        findings.append("the report was produced against a different candidate universe")
    if universe.get("catalogue_snapshot_sha256") != catalogue.get("snapshot_sha256"):
        findings.append("the universe was derived from a different catalogue snapshot")

    # 3. The universe replays from the catalogue snapshot alone.
    replayed = rule.derive_universe(catalogue.get("endpoint_entries") or [])
    if [(c["model"], c["provider"], c["order"]) for c in replayed["ordered_candidates"]] != \
       [(c["model"], c["provider"], c["order"]) for c in universe.get("ordered_candidates") or []]:
        findings.append("the candidate universe does not replay from the catalogue snapshot")
    if replayed["eligible_count"] != universe.get("eligible_count"):
        findings.append("the eligible candidate count does not replay")

    # 4. Every recorded qualification replays from its own profile.
    for profile in report.get("profiles") or []:
        if profile.get("incomplete"):
            if profile.get("qualification", {}).get("qualifies") is not False:
                findings.append("an incomplete candidate is not recorded as unqualified")
            continue
        recomputed = rule.qualifies(profile)
        if recomputed["qualifies"] != profile.get("qualification", {}).get("qualifies"):
            findings.append("qualification does not replay for %s/%s"
                            % (profile.get("model"), profile.get("provider")))

    # 5. The selection replays from the frozen order and the recorded qualifications alone.
    selection = rule.select(universe, report.get("profiles") or [])
    if selection.get("selected") != report.get("selection", {}).get("selected"):
        findings.append("the selection does not replay from the frozen rule")
    if report.get("selection", {}).get("carrier_quality_was_an_input") is not False:
        findings.append("the record does not assert that carrier quality was not an input")

    # 6. Budget and boundary.
    if int(report.get("requests_spent") or 0) > rule.GLOBAL_REQUEST_CEILING:
        findings.append("the recorded budget exceeds the frozen ceiling")
    if report.get("qualifying_calls") != 0:
        findings.append("the record claims a qualifying scientific invocation")
    if report.get("qualifying_input_was_sent") is not False:
        findings.append("the record does not assert the qualifying input was withheld")
    if report.get("raw_completion_persisted") is not False:
        findings.append("the record does not assert that no raw completion was persisted")

    # 7. No candidate may have been probed that the committed universe does not contain.
    known = {(c["model"], c["provider"]) for c in universe.get("ordered_candidates") or []}
    for profile in report.get("profiles") or []:
        if (profile.get("model"), profile.get("provider")) not in known:
            findings.append("a probed candidate is absent from the committed universe: %s/%s"
                            % (profile.get("model"), profile.get("provider")))

    return {
        "schema": "m117-stage1-check-v1",
        "plan_sha256": frozen["plan_sha256"],
        "universe_sha256": universe.get("universe_sha256"),
        "report_sha256": report.get("report_sha256"),
        "candidates_probed": len(report.get("profiles") or []),
        "requests_spent": report.get("requests_spent"),
        "route_selected": report.get("selection", {}).get("route_selected"),
        "selection_replays": not any("selection does not replay" in f for f in findings),
        "findings": findings,
        "passed": not findings,
    }


def main() -> int:
    try:
        result = check()
    except Stage1CheckError as exc:
        print("Stage 1 check FAILED: %s" % exc)
        return 1
    for finding in result["findings"]:
        print("  - %s" % finding)
    print("Stage 1 check: %s" % ("PASSED" if result["passed"] else "FAILED"))
    print("  route selected: %s" % result["route_selected"])
    print("  candidates probed: %s | requests spent: %s"
          % (result["candidates_probed"], result["requests_spent"]))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
