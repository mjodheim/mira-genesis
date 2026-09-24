from __future__ import annotations
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"experiment"/"rsi_v23"/"make_forbidden_tokens.py"
spec=importlib.util.spec_from_file_location("v23_tokens_test",P)
assert spec is not None and spec.loader is not None
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def test_development_identity_tokens_are_extracted():
    s={"task_id":"task-A","root_node_id":"root-A","allowed_source_path":"src/A.java",
       "nodes":{"root-A":{"action":{"target_axes":["task-A"],"changed_regions":["src/A.java"]}},
                "child-A":{"action":{"target_axes":["task-A"],"changed_regions":["src/A.java"]}}}}
    assert m.tokens_from_state(s)=={"task-A","root-A","child-A","src/A.java"}
