from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from metamorphosis import m103_runtime as runtime

from tests.test_m103_runtime import development_demand, m102_u2_bytes


ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, value: object) -> None:
    path.write_bytes(runtime.canonical_json(value).encode("ascii"))


def build_capsule(path: Path) -> Path:
    path.mkdir()
    sources = {
        "m100_runtime.py": ROOT / "metamorphosis" / "m100_runtime.py",
        "m101_runtime.py": ROOT / "metamorphosis" / "m101_runtime.py",
        "m102_runtime.py": ROOT / "metamorphosis" / "m102_runtime.py",
        "m103_runtime.py": ROOT / "metamorphosis" / "m103_runtime.py",
        "run.py": ROOT / "scripts" / "run_m103_process.py",
    }
    for name, source in sources.items():
        shutil.copyfile(source, path / name)
    assert sorted(item.name for item in path.iterdir()) == sorted(sources)
    return path


def isolated(capsule: Path, *arguments: str) -> tuple[int, dict[str, object]]:
    completed = subprocess.run(
        [sys.executable, "-I", str(capsule / "run.py"), *arguments],
        cwd=capsule,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode, json.loads(completed.stdout)


def test_constructor_state_crosses_real_process_death(tmp_path: Path) -> None:
    capsule = build_capsule(tmp_path / "capsule")
    predecessor = tmp_path / "m102-u2.json"
    predecessor.write_bytes(m102_u2_bytes())
    demand = tmp_path / "development.json"
    write_json(demand, development_demand())
    v0 = tmp_path / "v0.json"
    code, created = isolated(
        capsule, "create-state", "--m102", str(predecessor), "--out", str(v0)
    )
    assert code == 0
    assert created["confirmed"] is True
    producer_pid = created["pid"]

    v1 = tmp_path / "v1.json"
    code, acquired = isolated(
        capsule,
        "acquire-constructor",
        "--state",
        str(v0),
        "--demand",
        str(demand),
        "--register",
        "--out",
        str(v1),
    )
    assert code == 0
    assert acquired["confirmed"] is True
    assert acquired["pid"] != producer_pid
    assert acquired["isolated_mode"] is True
    assert acquired["imported_project_modules"] == []
    assert str(ROOT) not in acquired["search_path"]

    code, conservation = isolated(capsule, "conservation", "--state", str(v1))
    assert code == 0
    assert conservation["confirmed"] is True
    assert conservation["pid"] not in {producer_pid, acquired["pid"]}


def test_corrupt_state_fails_closed_in_isolated_process(tmp_path: Path) -> None:
    capsule = build_capsule(tmp_path / "capsule")
    predecessor = tmp_path / "m102-u2.json"
    predecessor.write_bytes(m102_u2_bytes())
    v0 = tmp_path / "v0.json"
    assert isolated(
        capsule, "create-state", "--m102", str(predecessor), "--out", str(v0)
    )[0] == 0
    corrupt = tmp_path / "corrupt.json"
    assert isolated(
        capsule,
        "state-control",
        "--state",
        str(v0),
        "--control",
        "corrupt",
        "--out",
        str(corrupt),
    )[0] == 0
    code, result = isolated(capsule, "conservation", "--state", str(corrupt))
    assert code == 3
    assert result["confirmed"] is False
    assert result["failed_closed"] is True
