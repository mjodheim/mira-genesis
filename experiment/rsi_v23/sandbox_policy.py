#!/usr/bin/env python3
"""Guard and execute a V23 policy in a bounded child process."""
from __future__ import annotations
import argparse,importlib.util,json,os,subprocess,sys,tempfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
WORKER=HERE/"policy_worker.py"

def load_guard():
    p=HERE/"policy_guard.py"; spec=importlib.util.spec_from_file_location("v23_guard_runtime",p)
    if spec is None or spec.loader is None: raise RuntimeError("cannot load policy guard")
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def _run_worker(policy:Path,payload:dict,timeout_seconds:float)->dict:
    with tempfile.TemporaryDirectory(prefix="v23-policy-sandbox-") as td:
        env={"PYTHONHASHSEED":"0","LC_ALL":"C","LANG":"C"}
        try:
            p=subprocess.run([sys.executable,"-S",str(WORKER),str(policy.resolve())],
                input=json.dumps(payload,sort_keys=True),text=True,capture_output=True,cwd=td,env=env,timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            return {"accepted":False,"phase":"runtime","error":"timeout"}
    if p.returncode:
        return {"accepted":False,"phase":"runtime","error":"worker_failed","stderr_tail":p.stderr[-2000:]}
    try:
        out=json.loads(p.stdout)
    except json.JSONDecodeError:
        return {"accepted":False,"phase":"runtime","error":"non_json_output","stdout_tail":p.stdout[-2000:]}
    return {"accepted":True,"phase":"worker_complete","output":out}

def metadata(policy:Path,forbidden_tokens:list[str],timeout_seconds:float=3.0)->dict:
    guard=load_guard(); problems=guard.guard_source(policy.read_text(encoding="utf-8"),forbidden_tokens)
    if problems:
        return {"accepted":False,"phase":"static_guard","problems":problems}
    raw=_run_worker(policy,{"mode":"metadata"},timeout_seconds)
    if not raw["accepted"]: return raw
    values=raw["output"].get("metadata")
    if not isinstance(values,list) or len(values)!=10 or any(type(x) is not int for x in values):
        return {"accepted":False,"phase":"runtime","error":"invalid_metadata"}
    return {"accepted":True,"phase":"complete","metadata":values}

def execute(policy:Path,view:dict,max_parallelism:int,forbidden_tokens:list[str],timeout_seconds:float=3.0)->dict:
    guard=load_guard(); problems=guard.guard_source(policy.read_text(encoding="utf-8"),forbidden_tokens)
    if problems:
        return {"accepted":False,"phase":"static_guard","problems":problems}
    raw=_run_worker(policy,{"mode":"select","view":view,"max_parallelism":int(max_parallelism)},timeout_seconds)
    if not raw["accepted"]: return raw
    out=raw["output"]
    selected=out.get("selected_parent_ids")
    if not isinstance(selected,list) or any(not isinstance(x,str) for x in selected):
        return {"accepted":False,"phase":"runtime","error":"invalid_selected_parent_ids"}
    if len(selected)!=len(set(selected)):
        return {"accepted":False,"phase":"runtime","error":"duplicate_selected_parent_ids"}
    if len(selected)>int(max_parallelism):
        return {"accepted":False,"phase":"runtime","error":"parallelism_exceeded"}
    return {"accepted":True,"phase":"complete","metadata":out["metadata"],"selected_parent_ids":selected}

def main()->None:
    ap=argparse.ArgumentParser(); ap.add_argument("policy",type=Path); ap.add_argument("view",type=Path)
    ap.add_argument("--max-parallelism",type=int,required=True); ap.add_argument("--forbidden-token-file",type=Path)
    ap.add_argument("--timeout-seconds",type=float,default=3.0); a=ap.parse_args()
    tokens=[] if a.forbidden_token_file is None else [x.strip() for x in a.forbidden_token_file.read_text().splitlines() if x.strip()]
    result=execute(a.policy,json.loads(a.view.read_text()),a.max_parallelism,tokens,a.timeout_seconds)
    print(json.dumps(result,indent=2,sort_keys=True))
    raise SystemExit(0 if result["accepted"] else 2)
if __name__=="__main__": main()
