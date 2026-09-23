from __future__ import annotations
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"experiment"/"rsi_v23"/"policy_guard.py"
spec=importlib.util.spec_from_file_location("v23_policy_guard_test",P)
assert spec is not None and spec.loader is not None
guard=importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)

GOOD='''"""candidate"""
def policy_metadata():
    return (10,6,3,5,5,4,8,1,8,3)

def select_parent_batch(view,max_parallelism):
    rows=list(view["revealed_nodes"])
    best=max(int(row["outcome"]["quality_milli"]) for row in rows)
    if best >= 780:
        return []
    return [view["root_node_id"]] if view["root_node_id"] in view["eligible_parent_ids"] else []
'''

def test_known_g2_shape_is_accepted():
    assert guard.guard_source(GOOD)==[]

def test_import_and_io_are_rejected():
    src=GOOD+"\nimport os\nopen('x','w')\n"
    p=guard.guard_source(src)
    assert any("imports are forbidden" in x for x in p)
    assert any("forbidden" in x and "open" in x for x in p)

def test_reflective_escape_is_rejected():
    src=GOOD.replace("return []","return [getattr(view, '__class__')]")
    p=guard.guard_source(src)
    assert any("getattr" in x for x in p)
    assert any("__class__" in x for x in p)

def test_development_task_literal_is_rejected():
    src=GOOD.replace("best >= 780","view['root_node_id'] == 'brewstead-secret-task'")
    p=guard.guard_source(src,["brewstead-secret-task"])
    assert any("forbidden development token" in x for x in p)

def test_literal_top_level_constants_are_allowed():
    src="THRESHOLD=780\n"+GOOD
    assert guard.guard_source(src)==[]

def test_computed_top_level_state_is_rejected():
    src="THRESHOLD=max(1,2)\n"+GOOD
    assert any("top-level assignments" in x for x in guard.guard_source(src))
