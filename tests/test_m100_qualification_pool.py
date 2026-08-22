from __future__ import annotations

from scripts.author_m100_qualification_pool import audit, build_pool, digest, load_pool


def test_committed_pool_is_exact_authored_frozen_population() -> None:
    pool = load_pool()
    assert pool == build_pool(status="frozen")
    assert len(pool["entries"]) == 9
    assert pool["cycle_counts"] == {"A": 3, "B": 3, "C": 3}
    assert pool["m097_through_m099_worlds_excluded"] is True
    for entry in pool["entries"]:
        payload = {key: value for key, value in entry.items() if key != "entry_digest"}
        assert entry["entry_digest"] == digest(payload)


def test_pool_preflight_never_crosses_cumulative_boundary() -> None:
    report = audit(load_pool())
    assert report["passed"] is True
    assert report["migration_was_run"] is False
    assert report["acquisition_was_run"] is False
    assert report["fresh_runtime_was_run"] is False
    assert report["fault_was_injected"] is False
