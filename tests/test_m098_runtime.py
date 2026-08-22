from __future__ import annotations

import ast
import json
from pathlib import Path

from scripts import run_m098_qualification as runner
from scripts.author_m098_qualification_pool import build_world, write_cases


DEVELOPMENT = {
    "id": "development_delta_not_in_qualification",
    "class": "DevelopmentDelta",
    "key": "delta",
    "left_field": "finish",
    "right_field": "start",
    "fields": [
        {"name": "label", "annotation": "str"},
        {"name": "start", "annotation": "int"},
        {"name": "finish", "annotation": "int"},
    ],
    "cases": [
        {"label": "a", "start": 2, "finish": 9},
        {"label": "b", "start": 8, "finish": 1},
    ],
    "caller_count": 2,
    "operator": "sub",
}


def _m097_state() -> dict[str, object]:
    result = json.loads(runner.M097_RESULT_PATH.read_text(encoding="utf-8"))
    return json.loads(result["scientific_evidence"]["serialized_state"])


def test_isolated_development_consumer_requires_the_persisted_extension(tmp_path: Path) -> None:
    capsule, _digests = runner._capsule(tmp_path)
    world = build_world(tmp_path / "development", DEVELOPMENT)
    cases = write_cases(world / "cases.json", DEVELOPMENT)

    state = _m097_state()
    state_path = tmp_path / "state.json"
    state_path.write_bytes(runner._state_bytes(state))
    extended = runner._fresh(capsule, state_path, world, cases)
    assert extended["returncode"] == 0
    assert extended["runtime"]["confirmed"] is True
    assert extended["runtime"]["isolated_mode"] is True
    assert extended["runtime"]["imported_project_modules"] == []
    assert not any(
        str(runner.ROOT).casefold() in str(item).casefold()
        for item in extended["runtime"]["search_path"]
    )

    inherited = dict(state)
    inherited["extensions"] = []
    inherited_path = tmp_path / "inherited.json"
    inherited_path.write_bytes(runner._state_bytes(inherited))
    absent = runner._fresh(capsule, inherited_path, world, cases)
    assert absent["returncode"] == 1
    assert absent["runtime"]["confirmed"] is False
    assert absent["runtime"]["extensions_loaded"] == 0


def test_isolated_development_consumer_rejects_mutation_and_corruption(tmp_path: Path) -> None:
    capsule, _digests = runner._capsule(tmp_path)
    world = build_world(tmp_path / "development", DEVELOPMENT)
    cases = write_cases(world / "cases.json", DEVELOPMENT)
    state = _m097_state()

    mutated = json.loads(json.dumps(state))
    mutated["extensions"][0]["body"][-1] = "ADD"
    mutated_path = tmp_path / "mutated.json"
    mutated_path.write_bytes(runner._state_bytes(mutated))
    semantic = runner._fresh(capsule, mutated_path, world, cases)
    assert semantic["returncode"] == 1
    assert semantic["runtime"]["confirmed"] is False

    corrupt = bytearray(runner._state_bytes(state))
    corrupt[len(corrupt) // 2] ^= 1
    corrupt_path = tmp_path / "corrupt.json"
    corrupt_path.write_bytes(corrupt)
    rejected = runner._fresh(capsule, corrupt_path, world, cases)
    assert rejected["returncode"] == 3
    assert rejected["runtime"]["confirmed"] is False
    assert rejected["runtime"]["failed_closed"] is True


def test_runtime_capsule_has_only_standard_library_imports() -> None:
    path = runner.ROOT / "metamorphosis" / "m098_runtime.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        str(node.module).split(".")[0]
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
    }
    assert imported <= {
        "__future__", "argparse", "ast", "hashlib", "json", "os", "sys", "types", "pathlib"
    }
