#!/usr/bin/env python3
"""M125/H70 DEVELOPMENT readiness instrument; network remains separately owner-gated."""
from __future__ import annotations
import argparse,http.client,importlib,json,os,ssl,sys,time,urllib.parse
from datetime import datetime,timezone
from pathlib import Path
from typing import Any,Callable,Mapping
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from metamorphosis import m125_protocol_gate as gate  # noqa:E402
DIRECTORY=ROOT/"experiments"/"M125";RESULT_PATH=DIRECTORY/"READINESS_RESULT.json";LEDGER_PATH=DIRECTORY/"READINESS_LEDGER.json";JOURNAL_PATH=DIRECTORY/"STEP_JOURNAL.json"
SECRET_VARIABLE="OPENROUTER_API_KEY";RETRYABLE_STATUSES=(429,500,502,503,504);MAX_RETRIES=2;RETRY_BASE_SECONDS=2.;RETRY_MAX_SECONDS=60.;PROBE_MAX_TOKENS=4096;STRESS_MAX_TOKENS=65536;REASONING_EFFORT="none";MAX_REASONING_TOKENS=0;REQUEST_TIMEOUT_SECONDS=900
DELIVERY_VERDICT=gate.DELIVERY_VERDICT;RESULT_SCHEMA="m125-readiness-result-v1";JOURNAL_SCHEMA="m125-step-journal-v1"
Transport=Callable[...,dict[str,Any]]
class ReadinessError(RuntimeError):pass

def _now():return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
def _secret():
    s=os.environ.get(SECRET_VARIABLE)
    if not s:raise ReadinessError("%s is not set; no network request was made"%SECRET_VARIABLE)
    return s

def _instrument_modules():
    return {"probes":importlib.import_module("metamorphosis.m125_capability_probes"),"stress":importlib.import_module("metamorphosis.m125_stress_schema"),"schema_tools":importlib.import_module("metamorphosis.m116_schema"),"contract":importlib.import_module("metamorphosis.m122_carrier_contract"),"fixed":importlib.import_module("metamorphosis.m118_route"),"blind":importlib.import_module("metamorphosis.blind_bank_protocol")}

def _http(secret,url,*,method="POST",body=None,timeout=REQUEST_TIMEOUT_SECONDS):
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!="https" or not parsed.hostname:raise ReadinessError("M125 endpoint must use https")
    headers={"Accept":"application/json","Authorization":"Bearer %s"%secret}
    if body is not None:headers.update({"Content-Type":"application/json","X-OpenRouter-Metadata":"enabled","X-OpenRouter-Cache":"false"})
    started=_now();context=ssl.create_default_context();connection=None;began=False
    try:
        proxy=os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        if proxy:
            via=urllib.parse.urlsplit(proxy if "://" in proxy else "http://"+proxy);connection=http.client.HTTPSConnection(via.hostname,via.port or 80,timeout=timeout,context=context);connection.set_tunnel(parsed.hostname,parsed.port or 443)
        else:connection=http.client.HTTPSConnection(parsed.hostname,parsed.port or 443,timeout=timeout,context=context)
        path=parsed.path or "/";path+=("?"+parsed.query) if parsed.query else "";began=True;connection.request(method,path,body=body,headers=headers);response=connection.getresponse();raw=response.read();status=response.status;rh={k.lower():v for k,v in response.getheaders() if k.lower() in ("date","retry-after","x-generation-id")}
    except Exception as exc:return {"status":None,"body":None,"response_bytes":None,"response_headers":{},"started_at":started,"finished_at":_now(),"transport_failure_class":type(exc).__name__,"model_execution_cannot_be_excluded":bool(began and body is not None)}
    finally:
        if connection is not None:connection.close()
    try:decoded=json.loads(raw.decode())
    except (UnicodeDecodeError,ValueError):decoded=None
    return {"status":status,"body":decoded if isinstance(decoded,Mapping) else None,"response_bytes":len(raw),"response_headers":rh,"started_at":started,"finished_at":_now(),"transport_failure_class":None,"model_execution_cannot_be_excluded":False}

def _parts(observed):
    body=observed.get("body") if isinstance(observed.get("body"),Mapping) else {};choices=body.get("choices") if isinstance(body.get("choices"),list) else [];first=choices[0] if choices and isinstance(choices[0],Mapping) else {};message=first.get("message") if isinstance(first.get("message"),Mapping) else {};usage=body.get("usage") if isinstance(body.get("usage"),Mapping) else {};return dict(body),dict(first),dict(message),dict(usage)
def answered(observed):
    _,first,message,_=_parts(observed);c=message.get("content");f=first.get("finish_reason");return bool(isinstance(c,str) and c.strip() and isinstance(f,str) and f in ("stop","length"))
def deterministic_request_rejection(observed):
    s=observed.get("status");return bool(isinstance(s,int) and 400<=s<500 and s!=429 and not answered(observed))
def retryable_delivery(observed):
    if answered(observed) or deterministic_request_rejection(observed):return False
    s=observed.get("status");return bool(s==200 or s in RETRYABLE_STATUSES or observed.get("transport_failure_class") is not None)
def _wait_before_retrying(observed,attempt,sleeper=time.sleep):
    h=observed.get("response_headers") if isinstance(observed.get("response_headers"),Mapping) else {};adv=None
    for k,v in h.items():
        if str(k).lower()=="retry-after":
            try:adv=float(str(v).strip())
            except (TypeError,ValueError):adv=None
            break
    d=adv if adv is not None else RETRY_BASE_SECONDS*(2**attempt);d=max(0.,min(float(d),RETRY_MAX_SECONDS))
    if d:sleeper(d)
    return d
def _send(transport,endpoint,body,budget,*,sleeper=time.sleep):
    last={}
    for attempt in range(MAX_RETRIES+1):
        if budget["spent"]>=budget["limit"]:raise ReadinessError("the frozen physical-request budget is exhausted")
        budget["spent"]+=1;last=transport(endpoint,method="POST",body=body,timeout=REQUEST_TIMEOUT_SECONDS)
        if retryable_delivery(last) and attempt<MAX_RETRIES:_wait_before_retrying(last,attempt,sleeper);continue
        return last
    return last

def _reasoning_tokens(body):
    u=body.get("usage") if isinstance(body.get("usage"),Mapping) else {};d=u.get("completion_tokens_details")
    if isinstance(d,Mapping) and isinstance(d.get("reasoning_tokens"),int):return d["reasoning_tokens"]
    return u.get("reasoning_tokens") if isinstance(u.get("reasoning_tokens"),int) else None

def _request_body(modules,prompt,schema,name,max_tokens):
    fixed=modules["fixed"];fixed.assert_is_the_fixed_route(fixed.REQUESTED_MODEL,fixed.PROVIDER)
    return {"model":fixed.REQUESTED_MODEL,"messages":[{"role":"user","content":prompt}],"provider":fixed.provider_block(),"response_format":{"type":"json_schema","json_schema":{"name":name,"strict":True,"schema":schema}},"max_tokens":max_tokens,"seed":0,"stream":False,"temperature":1.0,"reasoning":{"effort":REASONING_EFFORT}}

def validate_protocol_semantics(protocol,modules):
    p=modules["probes"];s=modules["stress"];st=modules["schema_tools"];c=modules["contract"];f=modules["fixed"];b=modules["blind"];candidate=c.candidate_schema();census=st.census(candidate);matrix=p.build_matrix(census);names=[r["name"] for r in matrix];required=p.required_feature_classes(census)
    checks=((names,protocol.get("probe_names"),"probe sequence"),(required,protocol.get("required_feature_classes"),"feature set"),(PROBE_MAX_TOKENS,protocol.get("probe_max_tokens"),"probe cap"),(STRESS_MAX_TOKENS,protocol.get("stress_max_tokens"),"stress cap"),(list(s.CALIBRATION_QUEUE),protocol.get("calibration_queue"),"calibration queue"),(s.MIN_COMPLETION_TOKENS,protocol.get("minimum_completion_tokens"),"lower threshold"),(s.MAX_COMPLETION_TOKENS,protocol.get("maximum_completion_tokens"),"upper threshold"),(list(RETRYABLE_STATUSES),protocol.get("retryable_statuses"),"retry statuses"),(MAX_RETRIES,protocol.get("max_retries_per_logical_step"),"retry count"),(c.GENERATOR_ENDPOINT,protocol.get("endpoint"),"endpoint"),(f.REQUESTED_MODEL,protocol.get("requested_model"),"model"),(f.PROVIDER,protocol.get("provider"),"provider"))
    for actual,frozen,label in checks:
        if actual!=frozen:raise ReadinessError("%s differs from frozen protocol"%label)
    p.assert_complete_coverage(census,matrix)
    for r in matrix:
        if r["max_compact_json_bytes"]>=PROBE_MAX_TOKENS:raise ReadinessError("probe %s is not bounded"%r["name"])
    dg=b.sha256_hex(b.canonical_bytes(candidate))
    if protocol.get("candidate_schema_sha256")!=dg:raise ReadinessError("candidate schema digest differs")
    proof=s.assert_certifies(candidate,s.CALIBRATION_QUEUE[0],c.CERTIFIED_ARRAY_OF_OBJECT_LEVELS)
    if proof["pinning_census_bit_identical"] is not True:raise ReadinessError("pinning changed census")
    return {"candidate_schema_sha256":dg,"required_feature_classes":required,"probe_names":names,"probe_bounds":{r["name"]:r["max_compact_json_bytes"] for r in matrix},"pinning_census_bit_identical":True,"historical_token_observations_used_for_m125_calibration":False}

def offline_preflight(root=ROOT):
    g=gate.offline_preflight(root);m=_instrument_modules();sem=validate_protocol_semantics(gate.load_frozen_protocol(root),m);return {"schema":"m125-offline-preflight-v1","protocol_sha256":g["protocol_sha256"],"source_manifest_verified":True,"network_authorization_present":g["network_authorization_present"],"credential_access_permitted":False,"delivery_accounting":g["delivery_accounting"],"semantics":sem}

def _probe_observation(modules,probe,observed):
    st=modules["schema_tools"];fixed=modules["fixed"];body,first,message,usage=_parts(observed);finish=first.get("finish_reason") if isinstance(first.get("finish_reason"),str) else None;content=message.get("content");r={"answered":answered(observed),"http_status":observed.get("status"),"finish_reason":finish,"content_present":bool(isinstance(content,str) and content.strip()),"completion_tokens":usage.get("completion_tokens") if isinstance(usage.get("completion_tokens"),int) else None,"reasoning_tokens":_reasoning_tokens(body),"schema_conforms":False,"raw_completion_persisted":False}
    if deterministic_request_rejection(observed):return "not_ready_request",r
    if not r["answered"]:return DELIVERY_VERDICT,r
    identity=fixed.identity_holds(body);r["identity_holds"]=bool(identity["holds"])
    if not identity["holds"]:return "not_ready_identity",r
    if isinstance(r["reasoning_tokens"],int) and r["reasoning_tokens"]>MAX_REASONING_TOKENS:return "not_ready_reasoning",r
    if finish=="length":return "not_ready_probe_envelope",r
    try:instance=json.loads(content)
    except (TypeError,ValueError):return "not_ready_features",r
    ok,loc,key=st.instance_is_valid(instance,probe["schema"]);r.update({"schema_conforms":bool(ok),"failing_schema_location":loc,"first_failing_keyword":key})
    return (None if ok else "not_ready_features"),r

def _stress_observation(modules,stations,observed):
    st=modules["schema_tools"];fixed=modules["fixed"];stress=modules["stress"];body,first,message,usage=_parts(observed);finish=first.get("finish_reason") if isinstance(first.get("finish_reason"),str) else None;content=message.get("content");tokens=usage.get("completion_tokens") if isinstance(usage.get("completion_tokens"),int) else None;r={"stations":stations,"answered":answered(observed),"http_status":observed.get("status"),"finish_reason":finish,"completion_tokens":tokens,"reasoning_tokens":_reasoning_tokens(body),"schema_conforms":False,"raw_completion_persisted":False}
    if deterministic_request_rejection(observed):return "not_ready_request",r
    if not r["answered"]:return DELIVERY_VERDICT,r
    identity=fixed.identity_holds(body);r["identity_holds"]=bool(identity["holds"])
    if not identity["holds"]:return "not_ready_identity",r
    if isinstance(r["reasoning_tokens"],int) and r["reasoning_tokens"]>MAX_REASONING_TOKENS:return "not_ready_reasoning",r
    if finish=="length":return "not_ready_calibration_envelope",r
    try:instance=json.loads(content)
    except (TypeError,ValueError):return "not_ready_calibration",r
    ok=st.instance_is_valid(instance,stress.build_stress_schema(stations))[0];r["schema_conforms"]=bool(ok)
    if not ok or not isinstance(tokens,int) or tokens<=0:return "not_ready_calibration",r
    return None,r

def _write_json(path,value,canonical):path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(canonical(value)+b"\n")
def _new_journal(protocol_sha):return {"schema":JOURNAL_SCHEMA,"milestone":"M125","hypothesis":"H70","development":True,"protocol_sha256":protocol_sha,"steps":{},"raw_completion_persisted":False}
def _completed_steps(journal):return {str(n) for n,r in (journal.get("steps") or {}).items() if isinstance(r,Mapping) and r.get("answered") is True}
def _persist_result(directory,result,canonical):
    result["result_sha256"]="";result["result_sha256"]=gate.sha256(canonical({k:v for k,v in result.items() if k!="result_sha256"}));_write_json(directory/"READINESS_LEDGER.json",result,canonical);_write_json(directory/"READINESS_RESULT.json",result,canonical);idx=len(list(directory.glob("READINESS_ATTEMPT_*.json")))+1;_write_json(directory/("READINESS_ATTEMPT_%02d_%s.json"%(idx,result["verdict"])),result,canonical);return result

def run_with_transport(protocol,modules,transport,directory,*,initial_journal=None,delivery_accounting=None,sleeper=time.sleep):
    validate_protocol_semantics(protocol,modules);p=modules["probes"];s=modules["stress"];st=modules["schema_tools"];c=modules["contract"];blind=modules["blind"];canonical=blind.canonical_bytes;endpoint=c.GENERATOR_ENDPOINT;journal=dict(initial_journal) if initial_journal is not None else _new_journal(protocol["protocol_sha256"]);journal["steps"]={str(n):dict(r) for n,r in (journal.get("steps") or {}).items()};completed=_completed_steps(journal);budget={"spent":0,"limit":int(protocol["physical_request_budget"])}
    def close(verdict,note,extra=None):
        result={"schema":RESULT_SCHEMA,"milestone":"M125","hypothesis":"H70","development":True,"is_a_qualifying_call":False,"qualifying_input_was_sent":False,"advances_a_generality_gate":False,"carries_no_qualification_statistic":True,"protocol_sha256":protocol["protocol_sha256"],"candidate_schema_sha256":protocol["candidate_schema_sha256"],"verdict":verdict,"ready":verdict=="ready","note":note,"requests_spent":budget["spent"],"completed_logical_steps":sorted(_completed_steps(journal)),"raw_completion_persisted":False,"delivery_accounting_before_attempt":dict(delivery_accounting or {}),"result_sha256":""};result.update(dict(extra or {}));_write_json(directory/"STEP_JOURNAL.json",journal,canonical);return _persist_result(directory,result,canonical)
    matrix=p.build_matrix(st.census(c.candidate_schema()))
    for probe in matrix:
        step="probe:%s"%probe["name"]
        if step in completed:continue
        body=_request_body(modules,probe["prompt"],probe["schema"],"m125_readiness_%s"%probe["name"],PROBE_MAX_TOKENS);obs=_send(transport,endpoint,canonical(body),budget,sleeper=sleeper);verdict,record=_probe_observation(modules,probe,obs)
        if verdict:return close(verdict,"logical step %s did not complete cleanly"%step,{"failed_step":step,"failed_observation":record})
        record.update({"answered":True,"step":step,"feature_class":probe["feature_class"],"probe":probe["name"]});journal["steps"][step]=record;_write_json(directory/"STEP_JOURNAL.json",journal,canonical);completed.add(step)
    points=[]
    for stations in s.CALIBRATION_QUEUE:
        step=s.calibration_step_name(stations)
        if step in completed:
            r=journal["steps"][step];points.append({"stations":stations,"completion_tokens":r["completion_tokens"],"answered":True,"finish_reason":r["finish_reason"],"schema_conforms":r["schema_conforms"]});continue
        schema=s.build_stress_schema(stations);body=_request_body(modules,s.stress_prompt(stations),schema,"m125_calibration_%d"%stations,STRESS_MAX_TOKENS);obs=_send(transport,endpoint,canonical(body),budget,sleeper=sleeper);verdict,r=_stress_observation(modules,stations,obs)
        if verdict:return close(verdict,"fresh calibration step %s failed"%step,{"failed_step":step,"failed_observation":r})
        r.update({"answered":True,"step":step,"kind":"fresh_calibration"});journal["steps"][step]=r;_write_json(directory/"STEP_JOURNAL.json",journal,canonical);completed.add(step);points.append({"stations":stations,"completion_tokens":r["completion_tokens"],"answered":True,"finish_reason":r["finish_reason"],"schema_conforms":r["schema_conforms"]})
    try:sizing=s.derive_final_size(points)
    except s.StressError as exc:return close("not_ready_calibration",str(exc),{"calibration_points":points})
    fs=int(sizing["final_stations"]);step="final:%d"%fs
    if step in completed:final=dict(journal["steps"][step])
    else:
        schema=s.build_stress_schema(fs);body=_request_body(modules,s.stress_prompt(fs),schema,"m125_final_%d"%fs,STRESS_MAX_TOKENS);obs=_send(transport,endpoint,canonical(body),budget,sleeper=sleeper);verdict,final=_stress_observation(modules,fs,obs)
        if verdict:
            if verdict=="not_ready_calibration_envelope":verdict="not_ready_stress"
            return close(verdict,"final out-of-sample stress failed",{"failed_step":step,"failed_observation":final,"fresh_sizing":sizing})
        final.update({"answered":True,"step":step,"kind":"final_out_of_sample"});journal["steps"][step]=final;_write_json(directory/"STEP_JOURNAL.json",journal,canonical)
    if not s.final_observation_holds(final,sizing):return close("not_ready_stress","final observation missed frozen band; no refit permitted",{"fresh_sizing":sizing,"final_observation":final})
    return close("ready","bounded probes, fresh calibration and out-of-sample stress passed",{"fresh_sizing":sizing,"final_observation":final,"historical_token_observations_used_for_calibration":False})

def execute(root=ROOT):
    context=gate.precredential_context(root);modules=_instrument_modules();protocol=context["protocol"];validate_protocol_semantics(protocol,modules);secret=_secret()
    def transport(url,*,method="POST",body=None,timeout=REQUEST_TIMEOUT_SECONDS):return _http(secret,url,method=method,body=body,timeout=timeout)
    return run_with_transport(protocol,modules,transport,Path(root)/"experiments"/"M125",initial_journal=context["resume_journal"],delivery_accounting=context["delivery_accounting"])
def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument("--preflight",action="store_true");g.add_argument("--execute",action="store_true");a=p.parse_args()
    try:r=offline_preflight(ROOT) if a.preflight else execute(ROOT)
    except (ReadinessError,gate.GateError) as exc:print("REFUSED: %s"%exc);return 1
    print(json.dumps(r if a.preflight else {k:r[k] for k in ("verdict","ready","requests_spent","protocol_sha256","result_sha256")},indent=2,sort_keys=True));return 0 if a.preflight or r["ready"] else 1
if __name__=="__main__":raise SystemExit(main())
