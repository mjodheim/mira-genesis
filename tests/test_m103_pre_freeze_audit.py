from __future__ import annotations

import json
from pathlib import Path

from scripts import audit_m103_boundaries as boundary
from scripts import author_m103_predecessor_conservation as conservation_author
from scripts import build_m103_protocol as protocol_builder


ROOT = Path(__file__).resolve().parents[1]
CONSERVATION = ROOT / "experiments" / "M103" / "PREDECESSOR_CONSERVATION.json"


def test_frozen_boundary_audit_binding_and_source_guard_remain_exact() -> None:
    protocol = json.loads(
        (ROOT / "experiments" / "M103" / "PROTOCOL.json").read_text(encoding="ascii")
    )
    assert protocol["adversarial_review"]["boundary_audit_report_digest"] == (
        "a5800607ee71bb7302d1683e5c1c38a557f185b7a1fdfbc70d3dbed34532852a"
    )
    runtime_source = boundary.RUNTIME.read_text(encoding="utf-8")
    runtime_tree = boundary.ast.parse(runtime_source)
    exact_winning_literals = []
    for node in boundary.ast.walk(runtime_tree):
        if not isinstance(node, (boundary.ast.List, boundary.ast.Set, boundary.ast.Tuple)):
            continue
        values = [
            item.value
            for item in node.elts
            if isinstance(item, boundary.ast.Constant) and isinstance(item.value, str)
        ]
        if len(values) == len(node.elts) and set(values) == boundary.VALIDATED_S_PRIME_FEATURES:
            exact_winning_literals.append(sorted(values))
    assert exact_winning_literals == []


def test_predecessor_conservation_fixture_is_exact_and_complete() -> None:
    fixture = json.loads(CONSERVATION.read_text(encoding="ascii"))
    assert fixture == conservation_author.build_fixture()
    assert fixture["fixture_digest"] == (
        "7bfb93b917f78f5f1c2e2c16cee587f8eb50bdd7f9f98d7e922b6ae6506a51ea"
    )
    assert [entry["action"] for entry in fixture["entries"]].count("execute-m100") == 3


def test_protocol_candidate_builder_remains_fail_closed_after_result() -> None:
    builder_source = Path(protocol_builder.__file__).read_text(encoding="utf-8")
    author_source = (
        ROOT / "scripts" / "author_m103_qualification_pool.py"
    ).read_text(encoding="utf-8")
    assert "M103 protocol construction requires a clean worktree" in builder_source
    assert "M103 qualification pool cannot be authored after a result exists" in author_source
