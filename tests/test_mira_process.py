from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import time

import pytest

from mira_core.process import run_utf8_process


def test_utf8_transport_is_independent_of_the_ambient_code_page() -> None:
    value = "Mira adapts — sans ambiguïté ‑ 🧭"
    completed = run_utf8_process(
        (sys.executable, "-I", "-c", (
            "import sys; data=sys.stdin.buffer.read(); "
            "sys.stdout.buffer.write(data); sys.stderr.buffer.write('été'.encode())"
        )),
        input_text=value,
        timeout_seconds=5,
    )
    assert completed.returncode == 0
    assert completed.stdout == value
    assert completed.stderr == "été"


def test_non_utf8_process_output_fails_closed() -> None:
    with pytest.raises(UnicodeDecodeError):
        run_utf8_process(
            (sys.executable, "-I", "-c", "import sys;sys.stdout.buffer.write(b'\\xff')"),
            timeout_seconds=5,
        )


def test_timeout_terminates_delayed_descendants_before_they_can_act(tmp_path: Path) -> None:
    marker = tmp_path / "descendant-acted.txt"
    ready = tmp_path / "descendant-started.txt"
    child = (
        "from pathlib import Path; import sys,time; time.sleep(1.0); "
        "Path(sys.argv[1]).write_text('orphan acted',encoding='utf-8')"
    )
    parent = (
        "from pathlib import Path; import subprocess,sys,time; "
        "subprocess.Popen([sys.executable,'-I','-c',sys.argv[1],sys.argv[2]]); "
        "Path(sys.argv[3]).write_text('ready',encoding='utf-8'); time.sleep(30)"
    )
    with pytest.raises(subprocess.TimeoutExpired):
        run_utf8_process(
            (sys.executable, "-I", "-c", parent, child, str(marker), str(ready)),
            timeout_seconds=0.5,
        )
    assert ready.exists()
    time.sleep(1.2)
    assert not marker.exists()
