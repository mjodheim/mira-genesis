"""Offline adversarial tests for the prospective M125/H70 readiness instrument.

No test sends a network request. The frozen protocol and interpreting-source manifest are verified
against the exact committed bytes before any M125 DEVELOPMENT network authorization may exist.
"""
from __future__ import annotations
import json,re,subprocess
from pathlib import Path
import pytest
from metamorphosis import m116_schema as schema_tools
from metamorphosis import m122_carrier_contract as contract
from metamorphosis import m125_capability_probes as probes
from metamorphosis import m125_protocol_gate as gate
from metamorphosis import m125_stress_schema as stress
from metamorphosis.blind_bank_protocol import canonical_bytes,sha256_hex
from scripts import run_m125_readiness as readiness
ROOT=Path(__file__).resolve().parents[1]
IDENTITY={"model":"deepseek/deepseek-v4-flash-0731","provider":"OpenInference","openrouter_metadata":{"requested":"deepseek/deepseek-v4-flash-0731","strategy":"direct","attempt":1,"endpoints":{"available":[{"provider":"OpenInference","model":"deepseek/deepseek-v4-flash-20260731","selected":True}]}}}
_PATTERN_VALUES={r"^zq[0-9]{4}$":"zq0000",r"^[a-z][a-z0-9_]{1,11}$":"alpha_one",r"^[a-z][a-z0-9]{1,7}$":"alpha1"}

def conforming(schema):
    if "enum" in schema:return schema["enum"][0]
    kind=schema.get("type")
    if kind=="object":return {n:conforming(c) for n,c in (schema.get("properties") or {}).items()}
    if kind=="array":
        count=max(1,int(schema.get("minItems",1)));count=min(count,int(schema.get("maxItems",count)))
        return [conforming(schema.get("items") or {"type":"boolean"}) for _ in range(count)]
    if kind=="integer":return int(schema.get("minimum",0))
    if kind=="boolean":return True
    if kind=="null":return None
    if kind=="string":
        pattern=schema.get("pattern")
        if pattern:
            value=_PATTERN_VALUES.get(pattern);assert value is not None and re.fullmatch(pattern,value);return value
        return "ok"
    raise AssertionError("unsupported test schema %r"%kind)

def modules():return readiness._instrument_modules()
def protocol_record():
    m=modules();census=schema_tools.census(contract.candidate_schema());matrix=probes.build_matrix(census)
    r={"schema":"m125-readiness-protocol-v1","milestone":"M125","hypothesis":"H70","development":True,"scientific_observation":False,"probe_names":[x["name"] for x in matrix],"required_feature_classes":probes.required_feature_classes(census),"probe_max_tokens":readiness.PROBE_MAX_TOKENS,"stress_max_tokens":readiness.STRESS_MAX_TOKENS,"calibration_queue":list(stress.CALIBRATION_QUEUE),"minimum_completion_tokens":stress.MIN_COMPLETION_TOKENS,"maximum_completion_tokens":stress.MAX_COMPLETION_TOKENS,"retryable_statuses":list(readiness.RETRYABLE_STATUSES),"max_retries_per_logical_step":readiness.MAX_RETRIES,"endpoint":contract.GENERATOR_ENDPOINT,"requested_model":m["fixed"].REQUESTED_MODEL,"provider":m["fixed"].PROVIDER,"candidate_schema_sha256":sha256_hex(canonical_bytes(contract.candidate_schema())),"physical_request_budget":42,"inherited_delivery_spent":4,"interpreting_source_manifest":{},"historical_token_observations_used_for_calibration":False,"refit_after_final_observation_permitted":False,"protocol_sha256":""}
    r["protocol_sha256"]=gate.protocol_payload_sha256(r);return r

class FakeRoute:
    def __init__(self,*,first_empty=False,always_empty=False):self.first_empty=first_empty;self.always_empty=always_empty;self.calls=[]
    def __call__(self,_url,*,method="POST",body=b"",timeout=900):
        req=json.loads(body.decode());decl=req["response_format"]["json_schema"];name,schema=decl["name"],decl["schema"];self.calls.append(name)
        if self.always_empty or (self.first_empty and len(self.calls)==1):return {"status":200,"body":{},"response_headers":{}}
        instance=conforming(schema)
        if name.startswith("m125_calibration_") or name.startswith("m125_final_"):tokens=int(name.rsplit("_",1)[1])*1000
        else:tokens=200
        out=dict(IDENTITY);out["choices"]=[{"index":0,"finish_reason":"stop","message":{"role":"assistant","content":json.dumps(instance)}}];out["usage"]={"completion_tokens":tokens,"completion_tokens_details":{"reasoning_tokens":0}}
        return {"status":200,"body":out,"response_headers":{}}

# Bounded probe matrix and explicit coverage.
def test_every_required_feature_has_named_coverage_including_isolated_items():
    census=schema_tools.census(contract.candidate_schema());matrix=probes.build_matrix(census);mapping=probes.coverage_map(census,matrix);required=probes.required_feature_classes(census)
    assert "items" in required and mapping["items"]==["items"] and all(mapping.get(f) for f in required)
def test_probe_dependency_order_is_prospective_and_fixed():
    names=[x["name"] for x in probes.build_matrix(schema_tools.census(contract.candidate_schema()))]
    assert names.index("max_items")<names.index("items")<names.index("min_items")
def test_every_probe_has_finite_static_bound_below_cap():
    for row in probes.build_matrix(schema_tools.census(contract.candidate_schema())):
        assert 0<row["max_compact_json_bytes"]<probes.PROBE_OUTPUT_SAFETY_CAP_TOKENS
        assert probes.max_compact_json_bytes(row["schema"])==row["max_compact_json_bytes"]
def test_probe_matrix_is_non_carrier():probes.assert_non_carrier(probes.build_matrix(schema_tools.census(contract.candidate_schema())))
def test_unbounded_new_string_constraint_is_refused():
    with pytest.raises(probes.ProbeError,match="not finitely bounded"):probes.max_compact_json_bytes({"type":"string"})
def test_probes_do_not_introduce_max_length_keyword():
    blob=json.dumps(probes.build_matrix(schema_tools.census(contract.candidate_schema())))
    assert "maxLength" not in blob

# Pinned stress and fresh-only sizing.
def _ranges(node,path=()):
    found=[]
    if isinstance(node,dict):
        if node.get("type")=="array":found.append((path,node.get("minItems"),node.get("maxItems")))
        for k,v in node.items():found.extend(_ranges(v,path+(str(k),)))
    elif isinstance(node,list):
        for i,v in enumerate(node):found.extend(_ranges(v,path+(str(i),)))
    return found
def test_pinning_leaves_structural_census_bit_identical_and_all_arrays_fixed():
    proof=stress.pinning_proof(8);assert proof["census_bit_identical"] is True and proof["census_before"]==proof["census_after"]
    assert all(lo==hi for _,lo,hi in _ranges(stress.build_stress_schema(8)))
def test_upper_midpoint_rule_is_fixed():
    assert [stress.upper_midpoint(*x) for x in [(1,3),(3,4),(0,1),(1,4),(2,3)]]==[2,4,1,3,3]
def _point(s,t):return {"stations":s,"completion_tokens":t,"answered":True,"finish_reason":"stop","schema_conforms":True}
def test_fresh_8_16_32_derives_one_new_out_of_sample_size():
    d=stress.derive_final_size([_point(8,8000),_point(16,16000),_point(32,32000)]);assert d["final_stations"]==42 and d["final_is_out_of_sample"] is True and d["historical_token_observations_used"] is False and d["refit_after_final_observation_permitted"] is False
def test_no_admissible_window_closes_instead_of_refitting():
    with pytest.raises(stress.StressError,match="no admissible"):stress.derive_final_size([_point(8,4000),_point(16,8000),_point(32,200000)])
def test_old_or_missing_point_cannot_enter_m125_fit():
    with pytest.raises(stress.StressError,match="exactly one fresh"):stress.derive_final_size([_point(8,8000),_point(16,16000),_point(24,24000)])

# One answered predicate and retry semantics.
def _answer(finish="stop",content="{}"):return {"status":200,"body":{"choices":[{"finish_reason":finish,"message":{"content":content}}]},"response_headers":{}}
def test_empty_200_and_missing_finish_are_unanswered_and_retryable():
    empty={"status":200,"body":{}};assert not readiness.answered(empty) and readiness.retryable_delivery(empty)
    missing=_answer();missing["body"]["choices"][0].pop("finish_reason");assert not readiness.answered(missing) and readiness.retryable_delivery(missing)
def test_length_is_answered_and_not_retried():
    o=_answer("length","partial");assert readiness.answered(o) and not readiness.retryable_delivery(o)
def test_non_429_4xx_is_terminal_request_rejection_and_one_physical_attempt():
    o={"status":400,"body":{"error":{}},"response_headers":{}};calls=[]
    def tx(*a,**k):calls.append(1);return o
    r=readiness._send(tx,"https://example.invalid",b"{}",{"spent":0,"limit":9},sleeper=lambda x:None)
    assert readiness.deterministic_request_rejection(o) and not readiness.retryable_delivery(o) and r["status"]==400 and len(calls)==1
def test_retry_after_reads_actual_response_headers():
    slept=[];d=readiness._wait_before_retrying({"response_headers":{"Retry-After":"7"},"headers":{"retry-after":"99"}},0,sleeper=slept.append);assert d==7 and slept==[7]
def test_empty_200_is_retried_at_request_level():
    seq=[{"status":200,"body":{},"response_headers":{}},_answer()];calls=[]
    def tx(*a,**k):calls.append(1);return seq.pop(0)
    r=readiness._send(tx,"https://example.invalid",b"{}",{"spent":0,"limit":9},sleeper=lambda x:None);assert readiness.answered(r) and len(calls)==2

# Git fixtures for authoritative HEAD + working-tree gates.
def _git(root,*args):return subprocess.run(["git","-C",str(root),*args],check=True,capture_output=True,text=True)
def _init_repo(root):
    _git(root,"init");_git(root,"config","user.email","m125-test@example.invalid");_git(root,"config","user.name","M125 Test");_git(root,"commit","--allow-empty","-m","initial")
def _commit(root,message="fixture"):_git(root,"add","-A");_git(root,"commit","-m",message)
def _write(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
def _delivery(protocol_sha="p",digest="d"):return {"schema":readiness.RESULT_SCHEMA,"milestone":"M125","hypothesis":"H70","development":True,"verdict":gate.DELIVERY_VERDICT,"protocol_sha256":protocol_sha,"result_sha256":digest}
def _terminal(verdict="not_ready_features"):return {"schema":readiness.RESULT_SCHEMA,"milestone":"M125","hypothesis":"H70","development":True,"verdict":verdict,"result_sha256":"terminal"}
def test_terminal_working_tree_result_refuses(tmp_path):
    _init_repo(tmp_path);_write(tmp_path/gate.RESULT_REL,_terminal())
    with pytest.raises(gate.GateError,match="terminal"):gate.inspect_anti_rearm(tmp_path)
def test_terminal_head_result_deleted_locally_still_refuses(tmp_path):
    _init_repo(tmp_path);p=tmp_path/gate.RESULT_REL;_write(p,_terminal());_commit(tmp_path);p.unlink()
    with pytest.raises(gate.GateError,match="HEAD result"):gate.inspect_anti_rearm(tmp_path)
def test_terminal_head_result_replaced_by_delivery_still_refuses(tmp_path):
    _init_repo(tmp_path);p=tmp_path/gate.RESULT_REL;_write(p,_terminal());_commit(tmp_path);_write(p,_delivery())
    with pytest.raises(gate.GateError,match="HEAD result"):gate.inspect_anti_rearm(tmp_path)
def test_terminal_head_archive_deleted_locally_still_refuses(tmp_path):
    _init_repo(tmp_path);p=tmp_path/"experiments/M125/READINESS_ATTEMPT_01_not_ready_features.json";_write(p,_terminal());_commit(tmp_path);p.unlink()
    with pytest.raises(gate.GateError,match="HEAD experiments/M125/READINESS_ATTEMPT"):gate.inspect_anti_rearm(tmp_path)
def test_terminal_head_archive_replaced_by_delivery_still_refuses(tmp_path):
    _init_repo(tmp_path);p=tmp_path/"experiments/M125/READINESS_ATTEMPT_01_not_ready_features.json";_write(p,_terminal());_commit(tmp_path);_write(p,_delivery())
    with pytest.raises(gate.GateError,match="terminal"):gate.inspect_anti_rearm(tmp_path)
def test_missing_verdict_fails_closed(tmp_path):
    _init_repo(tmp_path);_write(tmp_path/gate.RESULT_REL,{"milestone":"M125"})
    with pytest.raises(gate.GateError,match="missing/unrecognized verdict"):gate.inspect_anti_rearm(tmp_path)

def _manifest_fixture(root):
    _init_repo(root);manifest={}
    for rel in gate.MINIMUM_MANIFEST_PATHS:
        p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text("# %s\n"%rel,encoding="utf-8");manifest[rel]=gate.sha256(gate.normalized(p.read_bytes()))
    r={"schema":"m125-readiness-protocol-v1","milestone":"M125","hypothesis":"H70","development":True,"scientific_observation":False,"interpreting_source_manifest":manifest,"inherited_delivery_spent":4,"protocol_sha256":""};r["protocol_sha256"]=gate.protocol_payload_sha256(r);_write(root/gate.PROTOCOL_REL,r);_commit(root);return r
def test_dirty_manifest_source_refuses(tmp_path):
    p=_manifest_fixture(tmp_path);t=tmp_path/gate.MINIMUM_MANIFEST_PATHS[0];t.write_text(t.read_text()+"# dirty\n")
    with pytest.raises(gate.GateError,match="differs from HEAD"):gate.verify_source_manifest(tmp_path,p)
def test_missing_manifest_source_refuses(tmp_path):
    p=_manifest_fixture(tmp_path);(tmp_path/gate.MINIMUM_MANIFEST_PATHS[0]).unlink()
    with pytest.raises(gate.GateError,match="working-tree source is missing"):gate.verify_source_manifest(tmp_path,p)
def test_committed_source_change_after_freeze_refuses(tmp_path):
    p=_manifest_fixture(tmp_path);t=tmp_path/gate.MINIMUM_MANIFEST_PATHS[0];t.write_text(t.read_text()+"# drift\n");_commit(tmp_path,"drift")
    with pytest.raises(gate.GateError,match="committed interpreting-source digest changed"):gate.verify_source_manifest(tmp_path,p)
def test_missing_network_authorization_blocks_before_credential_accessor(tmp_path,monkeypatch):
    _manifest_fixture(tmp_path);touched=[]
    def secret():touched.append(True);raise AssertionError("credential accessor reached")
    monkeypatch.setattr(readiness,"_secret",secret)
    with pytest.raises(gate.GateError,match="no committed M125 DEVELOPMENT network authorization"):readiness.execute(tmp_path)
    assert touched==[]
def test_future_authorization_must_bind_exact_protocol(tmp_path):
    p=_manifest_fixture(tmp_path);a={"schema":"m125-network-authorization-v1","scope":"development_network_only","protocol_sha256":"wrong","authorizes_h70_scientific_generation":False};_write(tmp_path/gate.AUTHORIZATION_REL,a);_commit(tmp_path,"auth")
    with pytest.raises(gate.GateError,match="exact frozen protocol"):gate.load_network_authorization(tmp_path,p["protocol_sha256"])

# Complete fake-route rehearsal, persistent no-redraw and delivery closure.
def test_full_offline_rehearsal_reaches_ready_without_science(tmp_path):
    p=protocol_record();route=FakeRoute();r=readiness.run_with_transport(p,modules(),route,tmp_path,delivery_accounting={"spent":4,"total":6,"remaining":2},sleeper=lambda x:None)
    assert r["verdict"]=="ready" and r["ready"] is True and r["fresh_sizing"]["final_stations"]==42
    assert r["historical_token_observations_used_for_calibration"] is False and r["qualifying_input_was_sent"] is False and r["is_a_qualifying_call"] is False and r["advances_a_generality_gate"] is False and r["raw_completion_persisted"] is False
    assert "m125_readiness_items" in route.calls and "m125_final_42" in route.calls
def test_completed_probe_is_never_redrawn_on_resume(tmp_path):
    p=protocol_record();route=FakeRoute();j=readiness._new_journal(p["protocol_sha256"]);j["steps"]["probe:enum"]={"answered":True,"step":"probe:enum","feature_class":"enum","probe":"enum","finish_reason":"stop","schema_conforms":True,"completion_tokens":1}
    r=readiness.run_with_transport(p,modules(),route,tmp_path,initial_journal=j,delivery_accounting={"spent":4,"total":6,"remaining":2},sleeper=lambda x:None);assert r["ready"] is True and "m125_readiness_enum" not in route.calls
def test_delivery_failure_does_not_mark_unanswered_step_complete(tmp_path):
    p=protocol_record();r=readiness.run_with_transport(p,modules(),FakeRoute(always_empty=True),tmp_path,delivery_accounting={"spent":4,"total":6,"remaining":2},sleeper=lambda x:None);assert r["verdict"]==gate.DELIVERY_VERDICT and r["completed_logical_steps"]==[];assert json.loads((tmp_path/"STEP_JOURNAL.json").read_text())["steps"]=={}

# Frozen protocol/source binding. This replaces the one-run manifest emitter.
def test_frozen_protocol_binds_exact_committed_m125_sources_and_stays_network_inert():
    p=gate.load_frozen_protocol(ROOT)
    assert p["protocol_sha256"]=="49e86626ffe3a5e835fa574f943072768e53fad40ca91b505d6294c09bff0257"
    expected={}
    for rel in gate.MINIMUM_MANIFEST_PATHS:
        committed=gate.head_blob(ROOT,rel);assert committed is not None,rel;expected[rel]=gate.sha256(gate.normalized(committed))
    assert p["interpreting_source_manifest"]==expected
    assert gate.verify_source_manifest(ROOT,p)==expected
    pre=readiness.offline_preflight(ROOT)
    assert pre["protocol_sha256"]==p["protocol_sha256"] and pre["source_manifest_verified"] is True
    assert pre["network_authorization_present"] is False and pre["credential_access_permitted"] is False
