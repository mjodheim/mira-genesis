"""Pin the M048 cross-process reproducibility defect so a repair cannot land unnoticed.

`experiments/M048/PROTOCOL.md` requires replay to "reproduce the exact final native state
digest", and `experiments/M048/DEVELOPMENT_RESULT.md` claims "exact artifact replay". Both
hold inside one process and neither holds across processes: `_validate` returns a selection
mapping containing the Node worker pid, and `m048_native_lineage.py` digests that mapping into
`validation_digest`, which propagates into the patch registry, the native journal, the causal
memory and the final state digest.

Following D014, the defect is recorded and pinned rather than silently repaired. Correcting it
moves recorded digests, which is a protocol-owner decision.
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


def test_the_validation_selection_carries_the_worker_process_id():
    """The volatile field is real and is part of what gets digested."""
    selection = {
        "action": "adopt",
        "attempts": [],
        "incumbent_task_passes": 0,
        "reason": None,
        "selected_candidate": None,
        "worker_pid": 111,
    }

    assert "worker_pid" in selection
    assert support._digest(VALIDATION_DOMAIN, selection) != support._digest(
        VALIDATION_DOMAIN, {**selection, "worker_pid": 222}
    )


def test_the_native_body_digest_is_the_reproducible_identity():
    """A stable identity does exist, so the defect is in what is published, not in the body."""
    snapshot, memory, _retained, _artifacts = lineage._reconstruct_m047()
    first = lineage._build_migrated_state(snapshot, memory, lineage.M048_PROTOCOL)
    second = lineage._build_migrated_state(snapshot, memory, lineage.M048_PROTOCOL)

    assert support._native_body_digest(first["body"]) == support._native_body_digest(second["body"])


def test_the_manifest_is_not_reproducible_across_processes():
    """Recorded behaviour, not desired behaviour.

    This test asserts the defect. When the repair lands it must fail, which is the point: a
    fix has to update this pin deliberately rather than pass unnoticed.
    """
    script = textwrap.dedent(
        """
        import json
        import metamorphosis.m048_runtime_migration as facade
        manifest = facade.run_m048_native_runtime_migration().to_dict()
        print(json.dumps({
            "final_state_digest": manifest["final_state_digest"],
            "post_migration_checkpoint": manifest["post_migration_checkpoint"],
        }))
        """
    )
    completed = subprocess.run(
        [sys.executable, "-c", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
    )
    other = json.loads(completed.stdout.decode("utf-8").strip().splitlines()[-1])
    here = facade.run_m048_native_runtime_migration().to_dict()

    assert here["final_state_digest"] != other["final_state_digest"]
    assert here["post_migration_checkpoint"] != other["post_migration_checkpoint"]


def test_neutralising_the_worker_pid_restores_reproducibility(monkeypatch):
    """The worker pid is the sole cause, so the repair is bounded and identifiable."""
    original = lineage._validate

    def without_pid(*args, **kwargs):
        return {**dict(original(*args, **kwargs)), "worker_pid": 0}

    monkeypatch.setattr(lineage, "_validate", without_pid)

    first = facade.run_m048_native_runtime_migration().to_dict()
    second = facade.run_m048_native_runtime_migration().to_dict()

    assert first == second
