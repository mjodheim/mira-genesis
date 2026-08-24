from __future__ import annotations

import json
from pathlib import Path

from metamorphosis import m103_runtime as runtime
from scripts import check_m103_closure as checker
from tests.test_m103_runtime import m102_u2_bytes


ROOT = Path(__file__).resolve().parents[1]


def test_independent_checker_closes_all_three_s0_demands() -> None:
    v0 = runtime.create_state(m102_u2_bytes())
    development = json.loads(
        (ROOT / "experiments" / "M103" / "DEVELOPMENT_FIXTURE.json").read_text(
            encoding="ascii"
        )
    )
    pool = json.loads(
        (ROOT / "experiments" / "M103" / "QUALIFICATION_POOL.json").read_text(
            encoding="ascii"
        )
    )
    for demand in (
        development["producer"],
        pool["configuration"]["acquisition"],
        pool["filesystem"]["acquisition"],
    ):
        report = checker.close(v0, demand)
        assert report["confirmed"] is True
        assert report["accepted"] == 0
        assert report["enumerated"] == report["finite_image_size"] == 2
        assert report["same_input_distinct_context_output_witnesses"]
        assert report["independent_of_m103_runtime_and_search"] is True


def test_independent_checker_source_has_no_m103_runtime_import() -> None:
    source = (ROOT / "scripts" / "check_m103_closure.py").read_text(encoding="utf-8")
    assert "import m103_runtime" not in source
    assert "from metamorphosis import m103_runtime" not in source
