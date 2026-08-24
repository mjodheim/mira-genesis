from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from metamorphosis import m105_runtime as runtime
from tests.test_m105_runtime import feature_demand, json_demand, m104_v3_bytes


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
        "m105_runtime.py": ROOT / "metamorphosis" / "m105_runtime.py",
        "run.py": ROOT / "scripts" / "run_m105_process.py",
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


def test_feature_and_consumer_cross_real_process_death(tmp_path: Path) -> None:
    capsule = build_capsule(tmp_path / "capsule")
    predecessor = tmp_path / "m104-v3.json"
    predecessor.write_bytes(m104_v3_bytes())
    development = tmp_path / "development.json"
    write_json(development, feature_demand())
    later = tmp_path / "json.json"
    write_json(later, json_demand())
    w0 = tmp_path / "w0.json"
    code, created = isolated(
        capsule, "create-state", "--m104", str(predecessor), "--out", str(w0)
    )
    assert code == 0

    w1 = tmp_path / "w1.json"
    code, acquired = isolated(
        capsule,
        "acquire-feature",
        "--state",
        str(w0),
        "--demand",
        str(development),
        "--register",
        "--out",
        str(w1),
    )
    assert code == 0
    assert acquired["confirmed"] is True
    assert acquired["pid"] != created["pid"]
    assert acquired["isolated_mode"] is True
    assert acquired["imported_project_modules"] == []
    assert str(ROOT) not in acquired["search_path"]

    w2 = tmp_path / "w2.json"
    code, consumer = isolated(
        capsule,
        "acquire-consumer",
        "--state",
        str(w1),
        "--demand",
        str(later),
        "--register",
        "--out",
        str(w2),
    )
    assert code == 0
    assert consumer["confirmed"] is True
    assert consumer["pid"] not in {created["pid"], acquired["pid"]}

    code, conservation = isolated(capsule, "conservation", "--state", str(w2))
    assert code == 0
    assert conservation["confirmed"] is True
    assert conservation["pid"] not in {
        created["pid"],
        acquired["pid"],
        consumer["pid"],
    }


def test_corrupt_and_missing_dependency_fail_closed_in_fresh_process(tmp_path: Path) -> None:
    capsule = build_capsule(tmp_path / "capsule")
    predecessor = tmp_path / "m104-v3.json"
    predecessor.write_bytes(m104_v3_bytes())
    development = tmp_path / "development.json"
    write_json(development, feature_demand())
    w0 = tmp_path / "w0.json"
    w1 = tmp_path / "w1.json"
    assert isolated(
        capsule, "create-state", "--m104", str(predecessor), "--out", str(w0)
    )[0] == 0
    assert isolated(
        capsule,
        "acquire-feature",
        "--state",
        str(w0),
        "--demand",
        str(development),
        "--register",
        "--out",
        str(w1),
    )[0] == 0
    corrupt = tmp_path / "corrupt.json"
    assert isolated(
        capsule,
        "state-control",
        "--state",
        str(w1),
        "--control",
        "corrupt",
        "--out",
        str(corrupt),
    )[0] == 0
    code, report = isolated(capsule, "conservation", "--state", str(corrupt))
    assert code == 3
    assert report["failed_closed"] is True
