"""Guard the M048 cross-process reproducibility repair.

`experiments/M048/PROTOCOL.md` requires replay to "reproduce the exact final native state
digest". That held inside one process and not across processes: `_validate` returns a selection
mapping containing the Node worker pid, and `m048_native_lineage.py` digested that whole mapping
into `validation_digest`, which propagated into the patch registry, the native journal, the
causal memory and the final state digest.

`_decided` now excludes the environmental fields before digesting. These tests assert the
repaired behaviour and keep the mechanism of the original defect visible, so a regression that
reintroduced the dependency would fail here rather than pass unnoticed.
"""
from __future__ import annotations

import json
import subprocess
import sys
import textwrap

import metamorphosis.m048_runtime_migration as facade
import metamorphosis.m048_native_lineage as lineage
import metamorphosis.m048_native_support as support


VALIDATION_DOMAIN = b"m048-native-validation-v1\x00"
_SELECTION = {
    "action": "adopt",
    "attempts": [],
    "incumbent_task_passes": 0,
    "reason": None,
    "selected_candidate": None,
    "worker_pid": 111,
}


def test_the_decided_view_drops_the_environmental_fields_and_keeps_the_rest():
    decided = lineage._decided(_SELECTION)

    assert "worker_pid" not in decided
    assert decided == {key: value for key, value in _SELECTION.items() if key != "worker_pid"}
    assert lineage._VOLATILE_VALIDATION_FIELDS == ("worker_pid",)


def test_the_validation_digest_no_longer_depends_on_the_worker_process_id():
    other = {**_SELECTION, "worker_pid": 222}

    assert support._digest(VALIDATION_DOMAIN, lineage._decided(_SELECTION)) == support._digest(
        VALIDATION_DOMAIN, lineage._decided(other)
    )
    # The mechanism of the original defect, kept visible: digesting the raw mapping still drifts.
    assert support._digest(VALIDATION_DOMAIN, _SELECTION) != support._digest(VALIDATION_DOMAIN, other)


def test_the_native_body_digest_is_stable():
    snapshot, memory, _retained, _artifacts = lineage._reconstruct_m047()
    first = lineage._build_migrated_state(snapshot, memory, lineage.M048_PROTOCOL)
    second = lineage._build_migrated_state(snapshot, memory, lineage.M048_PROTOCOL)

    assert support._native_body_digest(first["body"]) == support._native_body_digest(second["body"])


def test_the_manifest_is_reproducible_across_processes():
    """The claim the protocol makes, now measured across processes rather than within one."""
    script = textwrap.dedent(
        """
        import json
        import metamorphosis.m048_runtime_migration as facade
        print(json.dumps(facade.run_m048_native_runtime_migration().to_dict()))
        """
    )
    completed = subprocess.run(
        [sys.executable, "-c", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
    )
    other = json.loads(completed.stdout.decode("utf-8").strip().splitlines()[-1])
    here = facade.run_m048_native_runtime_migration().to_dict()

    assert here == other
    assert here["final_state_digest"] == other["final_state_digest"]
    assert here["post_migration_checkpoint"] == other["post_migration_checkpoint"]


def test_the_repair_moves_identities_and_no_finding(monkeypatch):
    """D015: a repair that moves recorded digests must be shown to change no result."""
    repaired = facade.run_m048_native_runtime_migration().to_dict()
    monkeypatch.setattr(lineage, "_decided", lambda selection: dict(selection))
    previous = facade.run_m048_native_runtime_migration().to_dict()

    moved = {key for key in repaired if repaired[key] != previous[key]}

    assert moved == {"final_state_digest", "post_migration_checkpoint"}
    for key in (
        "native_migration_all_retained_passed",
        "post_migration_all_retained_passed",
        "pre_migration_mean_tool_reused_after_migration",
        "post_migration_version",
        "post_migration_selected_template",
        "forced_fault_exact_restoration",
        "forced_fault_restored_version",
        "terminal_action",
        "terminal_body_unchanged",
        "replay_identical",
        "semantic_delegation_to_python",
        "source_retained_case_count",
    ):
        assert repaired[key] == previous[key], key
