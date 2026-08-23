from __future__ import annotations

import ast
import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from metamorphosis import m100_runtime
from metamorphosis import m101_executor as executor
from metamorphosis import m101_runtime as runtime
from scripts import check_m101_definitions as validator
from scripts import run_m101_development as development

ROOT = Path(__file__).resolve().parents[1]


def _case(case_id: str, value: object, expected: object) -> dict[str, object]:
    return {"case_id": case_id, "input": value, "expected": expected}


def _m100_s3_bytes() -> tuple[bytes, str]:
    result = json.loads((ROOT / "experiments/M100/RESULT.json").read_text(encoding="utf-8"))
    record = result["scientific_evidence"]["states"]["S3"]
    raw = m100_runtime.canonical_json(record["state"]).encode("ascii")
    assert hashlib.sha256(raw).hexdigest() == record["raw_sha256"]
    return raw, record["raw_sha256"]


def _text_world() -> dict[str, object]:
    return {
        "id": "development_text_trigger",
        "role": "producer_trigger",
        "carrier": "text",
        "catalog": [
            {"kind": "strip"},
            {"kind": "upper"},
            {"kind": "suffix", "value": "!"},
        ],
        "public_cases": [
            _case("text-public-1", "  mica  ", "MICA"),
            _case("text-public-2", " ash ", "ASH"),
            _case("text-public-3", "\tquartz\n", "QUARTZ"),
            _case("text-public-4", " iron", "IRON"),
        ],
        "hidden_cases": [
            _case("text-hidden-1", "  cobalt", "COBALT"),
            _case("text-hidden-2", "tin  ", "TIN"),
            _case("text-hidden-3", "\nlead\t", "LEAD"),
            _case("text-hidden-4", " zinc ", "ZINC"),
        ],
    }


def _record_world() -> dict[str, object]:
    public_values = [
        ([3, 1, 2], "a"),
        ([5, -1], "b"),
        ([2, 2, 1], "c"),
        ([], "d"),
    ]
    hidden_values = [
        ([9, 4], "e"),
        ([0, -3, 2], "f"),
        ([7], "g"),
        ([4, 1, 4], "h"),
    ]

    def cases(prefix: str, values: list[tuple[list[int], str]]) -> list[dict[str, object]]:
        return [
            _case(
                f"record-{prefix}-{index}",
                {"raw": items, "label": label},
                {"values": sorted(items), "label": label},
            )
            for index, (items, label) in enumerate(values, start=1)
        ]

    return {
        "id": "development_record_transfer",
        "role": "record_transfer",
        "carrier": "record",
        "catalog": [
            {"kind": "rename_key", "old": "raw", "new": "values"},
            {"kind": "sort_list", "key": "values"},
            {"kind": "drop_key", "key": "label"},
        ],
        "public_cases": cases("public", public_values),
        "hidden_cases": cases("hidden", hidden_values),
    }


def _syntax_transfer_world() -> dict[str, object]:
    sources = [
        "def rough(x):\n    return x - 3\n",
        "def rough(value):\n    return value * 2\n",
        "def rough(item):\n    return item + 7\n",
        "def rough(number):\n    return -number\n",
        "def rough(x):\n    return x // 2\n",
        "def rough(value):\n    return value - 9\n",
        "def rough(item):\n    return item * item\n",
        "def rough(number):\n    return number + 1\n",
    ]

    def expected(source: str) -> str:
        renamed = source.replace("def rough", "def refined")
        return renamed.replace("return ", "return abs(").rstrip() + ")"

    return {
        "id": "development_syntax_transfer",
        "role": "syntax_transfer",
        "carrier": "syntax",
        "catalog": [
            {"kind": "rename_function", "old": "rough", "new": "refined"},
            {"kind": "wrap_return", "call": "abs"},
            {"kind": "add_docstring", "text": "development"},
        ],
        "public_cases": [
            _case(f"syntax-public-{index}", source, expected(source))
            for index, source in enumerate(sources[:4], start=1)
        ],
        "hidden_cases": [
            _case(f"syntax-hidden-{index}", source, expected(source))
            for index, source in enumerate(sources[4:], start=1)
        ],
    }


def _syntax_b_world() -> dict[str, object]:
    expressions = [
        "x - 3", "x * 2", "-x", "x + 5", "x // 2", "x - 8", "x * x", "x + 1"
    ]
    sources = [f"def draft(x):\n    return {expression}\n" for expression in expressions]

    def expected(expression: str) -> str:
        return f"def published(payload):\n    return {expression.replace('x', 'payload')}"

    return {
        "id": "development_syntax_b",
        "role": "b_reuse",
        "carrier": "syntax",
        "catalog": [
            {"kind": "rename_function", "old": "draft", "new": "final"},
            {
                "kind": "rename_argument",
                "function": "final",
                "old": "x",
                "new": "payload",
            },
            {"kind": "rename_function", "old": "final", "new": "published"},
            {"kind": "add_docstring", "text": "wrong"},
        ],
        "public_cases": [
            _case(f"b-public-{index}", source, expected(expression))
            for index, (source, expression) in enumerate(
                zip(sources[:4], expressions[:4]), start=1
            )
        ],
        "hidden_cases": [
            _case(f"b-hidden-{index}", source, expected(expression))
            for index, (source, expression) in enumerate(
                zip(sources[4:], expressions[4:]), start=1
            )
        ],
    }


def _t1() -> tuple[dict[str, object], dict[str, object]]:
    t0 = runtime.create_state(_m100_s3_bytes()[0])
    acquisition = runtime.acquire_a(
        t0, runtime.public_demand(_text_world()), register_result=True
    )
    assert acquisition["confirmed"] is True
    return t0, acquisition["next_state"]


def _t2() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    t0, t1 = _t1()
    acquisition = runtime.acquire_b(
        t1, runtime.public_demand(_syntax_b_world()), register_result=True
    )
    assert acquisition["confirmed"] is True
    return t0, t1, acquisition["next_state"]


def test_m100_s3_bytes_are_conserved_exactly_through_t2() -> None:
    raw, raw_sha256 = _m100_s3_bytes()
    t0, t1 = _t1()
    acquired_b = runtime.acquire_b(
        t1, runtime.public_demand(_syntax_b_world()), register_result=True
    )
    assert acquired_b["confirmed"] is True
    t2 = acquired_b["next_state"]
    for state in (t0, t1, t2):
        checked = runtime.decode_state(state)
        assert checked["m100_ascii"].encode("ascii") == raw
        assert checked["m100_sha256"] == raw_sha256
    assert t2["definitions"][:1] == t1["definitions"]


def test_acquisition_accepts_only_a_closed_public_projection() -> None:
    world = _text_world()
    demand = runtime.public_demand(world)
    assert set(demand) == {
        "schema", "world_id", "role", "carrier", "catalog", "public_cases"
    }
    assert [case["case_id"] for case in demand["public_cases"]] == [
        f"text-public-{index}" for index in range(1, 5)
    ]
    assert "hidden_cases" not in runtime.canonical_json(demand)
    t0 = runtime.create_state(_m100_s3_bytes()[0])
    with pytest.raises(ValueError, match="closed record"):
        runtime.acquire_a(t0, world, register_result=True)
    with pytest.raises(ValueError, match="closed record"):
        runtime.acquire_b(t0, _syntax_b_world(), register_result=True)


def test_development_a_is_demand_derived_registered_and_carrier_neutral() -> None:
    t0 = runtime.create_state(_m100_s3_bytes()[0])
    world = _text_world()
    demand = runtime.public_demand(world)
    baseline = executor.execute_a(t0, executor._world(deepcopy(world)))
    assert baseline["reachable"] is False
    assert baseline["structural_max_atomic_effects"] == 1
    built = runtime.acquire_a(t0, demand, register_result=False)
    assert built["confirmed"] is True
    assert built["registered"] is False
    assert built["next_state"] is None
    assert runtime.encode_state(t0) == runtime.encode_state(runtime.decode_state(t0))
    acquired = runtime.acquire_a(t0, demand, register_result=True)
    assert acquired["public_case_ids"] == [
        f"text-public-{index}" for index in range(1, 5)
    ]
    assert acquired["shortest_accepted_length"] == 4
    assert sorted(runtime._a_call_order(acquired["adopted"]["body"])) == [0, 1]
    assert acquired["adopted"]["dependencies"] == []
    assert not any(
        term in runtime.canonical_json(acquired["adopted"]).lower()
        for term in runtime.FORBIDDEN_A_SUBSTRINGS
    )
    assert executor.execute_a(
        acquired["next_state"], executor._world(deepcopy(world))
    )["hidden_passed"] == 4


@pytest.mark.parametrize("world_factory", [_record_world, _syntax_transfer_world])
def test_registered_a_transfers_while_the_fresh_baseline_remains_closed(world_factory) -> None:
    _t0_state, t1 = _t1()
    world = world_factory()
    baseline = executor.execute_a(_t0_state, executor._world(deepcopy(world)))
    assert baseline["reachable"] is False
    execution = executor.execute_a(t1, executor._world(deepcopy(world)))
    assert execution["confirmed"] is True
    assert execution["hidden_passed"] == 4
    assert baseline["candidate_budget"] == execution["binding_search"]["assembled"]


def test_later_syntax_b_requires_registered_a_and_retains_a_live() -> None:
    t0, t1 = _t1()
    world = _syntax_b_world()
    demand = runtime.public_demand(world)
    assert runtime.acquire_b(t0, demand, register_result=True)["confirmed"] is False
    acquired = runtime.acquire_b(t1, demand, register_result=True)
    assert acquired["confirmed"] is True
    assert acquired["registered"] is True
    t2 = acquired["next_state"]
    a, b = t2["definitions"]
    assert b["dependencies"] == [a["definition_id"]]
    assert any(token.startswith(f"CALL:{a['definition_id']}:") for token in b["body"])
    assert executor.execute_b(t2, executor._world(deepcopy(world)))["hidden_passed"] == 4

    fault = runtime.rewrite_a_order_for_fault(t2)
    assert executor.execute_b(fault, executor._world(deepcopy(world)))["confirmed"] is False
    with pytest.raises(
        ValueError, match="missing or forward dependency|first M101 definition"
    ):
        runtime.decode_state(runtime.ablate_a_raw(t2))
    with pytest.raises(ValueError, match="digest mismatch"):
        runtime.decode_state(runtime.corrupt_state_digest(t2))
    assert len(runtime.ablate_b(t2)["definitions"]) == 1


def test_definition_and_state_tampering_fail_closed() -> None:
    _t0_state, t1 = _t1()
    tampered = deepcopy(t1)
    tampered["definitions"][0]["body"] = ["LOAD_INPUT", "RETURN"]
    payload = {key: value for key, value in tampered.items() if key != "state_digest"}
    tampered["state_digest"] = runtime.digest(payload)
    with pytest.raises(ValueError, match="content-addressed definition id mismatch"):
        runtime.decode_state(tampered)

    changed_predecessor = deepcopy(t1)
    changed_predecessor["m100_ascii"] += " "
    payload = {key: value for key, value in changed_predecessor.items() if key != "state_digest"}
    changed_predecessor["state_digest"] = runtime.digest(payload)
    with pytest.raises(ValueError, match="predecessor bytes changed"):
        runtime.decode_state(changed_predecessor)


def test_t0_has_no_host_pipeline_shortcut_and_same_executor_compares_t0_to_t1() -> None:
    runtime_source = (ROOT / "metamorphosis/m101_runtime.py").read_text(encoding="utf-8")
    executor_source = (ROOT / "metamorphosis/m101_executor.py").read_text(encoding="utf-8")
    for forbidden in ("apply_pipeline", "infer_slots", "resolve_slots"):
        assert forbidden not in runtime_source
        assert forbidden not in executor_source

    t0, t1 = _t1()
    world = executor._world(deepcopy(_record_world()))
    baseline = executor.execute_a(t0, deepcopy(world))
    retained = executor.execute_a(t1, deepcopy(world))
    assert baseline["reachable"] is False
    assert retained["confirmed"] is True
    assert baseline["candidate_budget"] == retained["binding_search"]["assembled"]


def test_independent_definition_validator_recomputes_a_and_b_semantics() -> None:
    _t0_state, _t1_state, t2 = _t2()
    raw_m100, expected_m100_sha256 = _m100_s3_bytes()
    report = validator.validate(
        runtime.encode_state(t2), expected_m100_sha256=expected_m100_sha256
    )
    assert report["confirmed"] is True
    assert report["scientific_verdict"] is False
    assert report["definition_count"] == 2
    assert report["m100_sha256"] == hashlib.sha256(raw_m100).hexdigest()
    assert sorted(report["definitions"][0]["symbolic_trace"]) == [0, 1]
    assert sorted(report["definitions"][1]["symbolic_trace"]) == [0, 1, 2]
    assert report["definitions"][1]["live_a_calls"] == 1

    fault = runtime.rewrite_a_order_for_fault(t2)
    with pytest.raises(ValueError, match="A symbolic semantics"):
        validator.validate(runtime.encode_state(fault))
    with pytest.raises(ValueError, match="independently expected digest"):
        validator.validate(runtime.encode_state(t2), expected_m100_sha256="0" * 64)


def test_execution_capsule_is_minimal_isolated_and_reuses_registered_state(tmp_path: Path) -> None:
    _t0_state, t1, t2 = _t2()
    state_t1 = tmp_path / "T1.json"
    state_t2 = tmp_path / "T2.json"
    fault_state = tmp_path / "T2-fault.json"
    corrupt_state = tmp_path / "T2-corrupt.json"
    a_world = tmp_path / "record-world.json"
    b_world = tmp_path / "syntax-b-world.json"
    state_t1.write_bytes(runtime.encode_state(t1))
    state_t2.write_bytes(runtime.encode_state(t2))
    fault_state.write_bytes(runtime.encode_state(runtime.rewrite_a_order_for_fault(t2)))
    corrupt_state.write_bytes(runtime.corrupt_state_digest(t2))
    a_world.write_text(runtime.canonical_json(_record_world()), encoding="ascii")
    b_world.write_text(runtime.canonical_json(_syntax_b_world()), encoding="ascii")

    capsule, member_digests = development.build_capsule(tmp_path)
    assert sorted(path.name for path in capsule.iterdir()) == ["m101_executor.py", "run.py"]
    assert set(member_digests) == {"m101_executor.py", "run.py"}

    a_result = development.fresh_execute(capsule, "execute-a", state_t1, a_world)
    b_result = development.fresh_execute(capsule, "execute-b", state_t2, b_world)
    assert a_result["returncode"] == 0
    assert b_result["returncode"] == 0
    for result in (a_result, b_result):
        payload = result["runtime"]
        assert payload["confirmed"] is True
        assert payload["isolated_mode"] is True
        assert payload["imported_project_modules"] == []
        assert str(ROOT) not in payload["search_path"]
        assert payload["execution"]["hidden_passed"] == 4

    absent_b = development.fresh_execute(capsule, "execute-b", state_t1, b_world)
    semantic_fault = development.fresh_execute(capsule, "execute-b", fault_state, b_world)
    corrupt = development.fresh_execute(capsule, "execute-b", corrupt_state, b_world)
    assert absent_b["returncode"] == 3
    assert absent_b["runtime"]["failed_closed"] is True
    assert "B is not registered" in absent_b["runtime"]["error"]
    assert semantic_fault["returncode"] == 1
    assert semantic_fault["runtime"]["confirmed"] is False
    assert semantic_fault["runtime"]["execution"]["hidden_passed"] == 0
    assert corrupt["returncode"] == 3
    assert corrupt["runtime"]["failed_closed"] is True
    assert "state digest mismatch" in corrupt["runtime"]["error"]
    assert len(
        {
            result["runtime"]["pid"]
            for result in (a_result, b_result, absent_b, semantic_fault, corrupt)
        }
    ) == 5


def test_executor_and_validator_sources_preserve_the_separation_boundary() -> None:
    executor_path = ROOT / "metamorphosis/m101_executor.py"
    validator_path = ROOT / "scripts/check_m101_definitions.py"
    executor_source = executor_path.read_text(encoding="utf-8")
    validator_source = validator_path.read_text(encoding="utf-8")
    executor_tree = ast.parse(executor_source)
    validator_tree = ast.parse(validator_source)

    allowed_executor_imports = {
        "__future__", "argparse", "ast", "copy", "dataclasses", "hashlib", "itertools",
        "json", "os", "pathlib", "sys", "typing",
    }
    executor_imports = {
        node.module.split(".")[0]
        for node in ast.walk(executor_tree)
        if isinstance(node, ast.ImportFrom) and node.module
    } | {
        alias.name.split(".")[0]
        for node in ast.walk(executor_tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert executor_imports <= allowed_executor_imports
    executor_functions = {
        node.name for node in ast.walk(executor_tree) if isinstance(node, ast.FunctionDef)
    }
    assert not any(name.startswith("acquire") for name in executor_functions)
    assert "register" not in executor_functions
    assert all(term not in executor_source for term in ("A_TOKENS", "B_MAX_BODY", "RESULT.json"))

    validator_imports = {
        node.module.split(".")[0]
        for node in ast.walk(validator_tree)
        if isinstance(node, ast.ImportFrom) and node.module
    } | {
        alias.name.split(".")[0]
        for node in ast.walk(validator_tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not validator_imports & {"metamorphosis", "m101_runtime", "m101_executor"}
    assert "scientific_verdict" in validator_source
