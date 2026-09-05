from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import time
from typing import Any, cast

import pytest

from mira_core import MemoryLedger
from mira_core.process import run_utf8_process


def test_memory_accessors_do_not_expose_nested_ledger_state() -> None:
    source_payload: dict[str, Any] = {"nested": [{"value": 1}]}
    ledger = MemoryLedger()
    appended = ledger.append("nested", source_payload)
    checkpoint = ledger.checkpoint()
    digest = ledger.digest

    # The caller-owned input and the event returned by append are both detached.
    source_payload["nested"][0]["value"] = 2
    cast(dict[str, Any], appended.payload)["nested"][0]["value"] = 3
    assert ledger.checkpoint() == checkpoint
    assert ledger.digest == digest
    ledger.verify()

    # Public event access and history snapshots must be recursively detached as well.
    exposed_event = ledger.events[0]
    cast(dict[str, Any], exposed_event.payload)["nested"][0]["value"] = 4
    exposed_history = ledger.history()
    cast(dict[str, Any], exposed_history[0])["payload"]["nested"][0]["value"] = 5
    filtered_event = ledger.events_by_kind("nested")[0]
    cast(dict[str, Any], filtered_event.payload)["nested"][0]["value"] = 6

    assert ledger.checkpoint() == checkpoint
    assert ledger.digest == digest
    ledger.verify()
    assert MemoryLedger.restore(checkpoint).checkpoint() == checkpoint


def test_timeout_kills_descendant_even_when_parent_has_already_exited(tmp_path: Path) -> None:
    marker = tmp_path / "late-descendant-acted.txt"
    ready = tmp_path / "parent-exited-after-spawn.txt"
    child = (
        "from pathlib import Path; import sys,time; time.sleep(1.0); "
        "Path(sys.argv[1]).write_text('orphan acted',encoding='utf-8')"
    )
    parent = (
        "from pathlib import Path; import subprocess,sys; "
        "subprocess.Popen([sys.executable,'-I','-c',sys.argv[1],sys.argv[2]]); "
        "Path(sys.argv[3]).write_text('spawned',encoding='utf-8')"
    )

    started = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        run_utf8_process(
            (sys.executable, "-I", "-c", parent, child, str(marker), str(ready)),
            timeout_seconds=0.3,
        )
    elapsed = time.monotonic() - started

    assert ready.exists()
    # Cleanup is bounded; the old Windows implementation could wait for the child to exit itself.
    assert elapsed < 1.5
    time.sleep(1.1)
    assert not marker.exists()
