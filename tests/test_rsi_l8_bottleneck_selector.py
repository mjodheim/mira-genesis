from __future__ import annotations
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"experiment"/"rsi_l6_l8"/"bottleneck_selector.py"
spec=importlib.util.spec_from_file_location("rsi_l8_selector_test",P)
assert spec is not None and spec.loader is not None
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

PROGRAM={
    "schema":m.PROGRAM_SCHEMA,
    "expression":{"op":{"name":"sub","args":[
        {"metric":"failure_milli"},
        {"metric":"cost_milli"},
    ]}},
}
SNAPSHOT={
    "schema":m.SNAPSHOT_SCHEMA,
    "components":[
        {"id":"exploration","metrics":{"failure_milli":800,"cost_milli":300}},
        {"id":"memory","metrics":{"failure_milli":700,"cost_milli":100}},
        {"id":"verification","metrics":{"failure_milli":600,"cost_milli":200}},
    ],
}

def test_selector_is_metric_driven_and_deterministic():
    r=m.choose(PROGRAM,SNAPSHOT)
    assert r["selected_component"]=="memory"
    assert r["scores"]=={"exploration":500,"memory":600,"verification":400}

def test_program_cannot_access_component_identity():
    bad={"schema":m.PROGRAM_SCHEMA,"expression":{"component_id":"memory"}}
    try:
        m.validate_program(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("component identity access was accepted")

def test_missing_metric_fails_closed():
    s={"schema":m.SNAPSHOT_SCHEMA,"components":[
        {"id":"a","metrics":{"failure_milli":1}},
        {"id":"b","metrics":{"failure_milli":2}},
    ]}
    try:
        m.choose(PROGRAM,s)
    except ValueError as e:
        assert "missing metric" in str(e)
    else:
        raise AssertionError("missing selector metric was accepted")

def test_tie_break_is_apparatus_owned_and_stable():
    p={"schema":m.PROGRAM_SCHEMA,"expression":{"const":1}}
    s={"schema":m.SNAPSHOT_SCHEMA,"components":[
        {"id":"z","metrics":{}},{"id":"a","metrics":{}}
    ]}
    r=m.choose(p,s)
    assert r["selected_component"]=="a"
    assert r["tie_count"]==2

def test_non_integer_snapshot_metric_is_rejected():
    s={"schema":m.SNAPSHOT_SCHEMA,"components":[
        {"id":"a","metrics":{"x":1.5}},{"id":"b","metrics":{"x":2}}
    ]}
    p={"schema":m.PROGRAM_SCHEMA,"expression":{"metric":"x"}}
    try:
        m.choose(p,s)
    except ValueError as e:
        assert "integer" in str(e)
    else:
        raise AssertionError("floating metric was accepted")
