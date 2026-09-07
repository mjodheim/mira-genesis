"""Fail-closed pre-credential gate for the prospective M125 DEVELOPMENT instrument.

This module intentionally imports only the Python standard library. Network-capable M125 execution
must run this gate before importing any interpreting M125 helper, reading a credential, constructing
a transport, or sending a request.
"""
from __future__ import annotations
import hashlib, json, subprocess
from pathlib import Path
from typing import Any, Mapping

PROTOCOL_REL=Path("experiments/M125/PROTOCOL.json")
AUTHORIZATION_REL=Path("experiments/M125/NETWORK_AUTHORIZATION.json")
RESULT_REL=Path("experiments/M125/READINESS_RESULT.json")
JOURNAL_REL=Path("experiments/M125/STEP_JOURNAL.json")
M125_ARCHIVE_PREFIX="experiments/M125/READINESS_ATTEMPT_"
M125_ARCHIVE_SUFFIX=".json"
DELIVERY_VERDICT="not_ready_delivery"
TOTAL_DELIVERY_CEILING=6
M125_DELIVERY_LIMIT=2
MINIMUM_MANIFEST_PATHS=(
"scripts/run_m125_readiness.py","metamorphosis/m125_protocol_gate.py",
"metamorphosis/m125_capability_probes.py","metamorphosis/m125_stress_schema.py",
"metamorphosis/m116_capability_probes.py","metamorphosis/m116_schema.py",
"metamorphosis/m122_stress_schema.py","metamorphosis/m122_carrier_contract.py",
"metamorphosis/m118_route.py","metamorphosis/blind_bank_protocol.py")

class GateError(RuntimeError): pass

def normalized(payload:bytes)->bytes:return payload.replace(b"\r\n",b"\n")
def sha256(payload:bytes)->str:return hashlib.sha256(payload).hexdigest()
def canonical_bytes(value:Any)->bytes:return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def protocol_payload_sha256(record:Mapping[str,Any])->str:return sha256(canonical_bytes({k:v for k,v in record.items() if k!="protocol_sha256"}))

def _git(root:Path,*args:str):
    try:return subprocess.run(["git","-C",str(root),*args],capture_output=True,check=False)
    except OSError as exc:raise GateError("git unavailable before credential access") from exc

def head_blob(root:Path,relative:Path|str)->bytes|None:
    c=_git(root,"cat-file","blob","HEAD:%s"%Path(relative).as_posix());return c.stdout if c.returncode==0 else None

def head_paths(root:Path,prefix:str)->list[str]:
    c=_git(root,"ls-tree","-r","--name-only","HEAD","--","experiments/M125")
    if c.returncode:raise GateError("cannot enumerate committed M125 archive paths")
    return sorted(n for n in c.stdout.decode().splitlines() if n.startswith(prefix) and n.endswith(M125_ARCHIVE_SUFFIX))

def _parse(payload:bytes,source:str)->dict[str,Any]:
    try:r=json.loads(normalized(payload).decode())
    except Exception as exc:raise GateError("%s is not valid JSON"%source) from exc
    if not isinstance(r,dict):raise GateError("%s is not an object"%source)
    return r

def _working(root:Path,relative:Path|str)->bytes|None:
    try:return (root/Path(relative)).read_bytes()
    except FileNotFoundError:return None

def _m125_surfaces(root:Path):
    rows=[]
    wt=_working(root,RESULT_REL);hd=head_blob(root,RESULT_REL)
    if wt is not None:rows.append(("working-tree result",_parse(wt,"working-tree result")))
    if hd is not None:rows.append(("HEAD result",_parse(hd,"HEAD result")))
    wtpaths=set()
    d=root/"experiments"/"M125"
    if d.is_dir():wtpaths={p.relative_to(root).as_posix() for p in d.glob("READINESS_ATTEMPT_*.json") if p.is_file()}
    hpaths=set(head_paths(root,M125_ARCHIVE_PREFIX))
    for p in sorted(wtpaths|hpaths):
        w=_working(root,p);h=head_blob(root,p)
        if w is not None:rows.append(("working-tree %s"%p,_parse(w,p)))
        if h is not None:rows.append(("HEAD %s"%p,_parse(h,p)))
    return rows

def inspect_anti_rearm(root:Path)->dict[str,Any]:
    rows=_m125_surfaces(root);unique={}
    for source,r in rows:
        v=r.get("verdict")
        if not isinstance(v,str) or not v:raise GateError("%s has a missing/unrecognized verdict"%source)
        if v!=DELIVERY_VERDICT:raise GateError("%s records terminal M125 verdict %r; delete/replace/rename cannot re-arm M125"%(source,v))
        dg=r.get("result_sha256") or sha256(canonical_bytes(r));unique.setdefault(dg,r)
    if len(unique)>=M125_DELIVERY_LIMIT:raise GateError("M125 delivery-only continuation limit exhausted")
    return {"checked_surfaces":[s for s,_ in rows],"delivery_records":list(unique.values()),"m125_delivery_closures":len(unique)}

def load_frozen_protocol(root:Path)->dict[str,Any]:
    w=_working(root,PROTOCOL_REL);h=head_blob(root,PROTOCOL_REL)
    if w is None or h is None:raise GateError("M125 PROTOCOL.json must exist in working tree and committed HEAD")
    if normalized(w)!=normalized(h):raise GateError("M125 PROTOCOL.json differs from HEAD")
    r=_parse(h,"M125 PROTOCOL.json")
    if r.get("protocol_sha256")!=protocol_payload_sha256(r):raise GateError("M125 protocol_sha256 mismatch")
    if r.get("milestone")!="M125" or r.get("hypothesis")!="H70" or r.get("development") is not True or r.get("scientific_observation") is not False:raise GateError("M125 protocol identity/boundary invalid")
    return r

def verify_source_manifest(root:Path,protocol:Mapping[str,Any])->dict[str,str]:
    m=protocol.get("interpreting_source_manifest")
    if not isinstance(m,Mapping):raise GateError("no interpreting_source_manifest")
    m={str(k):str(v) for k,v in m.items()};missing=sorted(set(MINIMUM_MANIFEST_PATHS)-set(m))
    if missing:raise GateError("source manifest omits: %s"%", ".join(missing))
    for p,expected in sorted(m.items()):
        h=head_blob(root,p)
        if h is None:raise GateError("manifest source absent from HEAD: %s"%p)
        hn=normalized(h)
        if sha256(hn)!=expected:raise GateError("committed interpreting-source digest changed: %s"%p)
        w=_working(root,p)
        if w is None:raise GateError("manifest-listed working-tree source is missing: %s"%p)
        if normalized(w)!=hn:raise GateError("manifest-listed working-tree source differs from HEAD: %s"%p)
    return m

def verify_delivery_records_match_protocol(anti,protocol_sha):
    for r in anti.get("delivery_records") or ():
        if r.get("protocol_sha256")!=protocol_sha:raise GateError("prior M125 delivery belongs to a different protocol")

def load_network_authorization(root:Path,protocol_sha:str)->dict[str,Any]:
    w=_working(root,AUTHORIZATION_REL);h=head_blob(root,AUTHORIZATION_REL)
    if w is None or h is None:raise GateError("no committed M125 DEVELOPMENT network authorization exists; credential access is blocked")
    if normalized(w)!=normalized(h):raise GateError("M125 network authorization differs from HEAD")
    r=_parse(h,"network authorization")
    if r.get("schema")!="m125-network-authorization-v1" or r.get("scope")!="development_network_only":raise GateError("M125 network authorization scope/schema invalid")
    if r.get("protocol_sha256")!=protocol_sha:raise GateError("M125 network authorization does not bind the exact frozen protocol")
    if r.get("authorizes_h70_scientific_generation") is not False:raise GateError("authorization must leave H70 blocked")
    return r

def _all_attempt_paths(root:Path):
    c=_git(root,"ls-tree","-r","--name-only","HEAD","--","experiments")
    if c.returncode:raise GateError("cannot enumerate delivery archive")
    hs={n for n in c.stdout.decode().splitlines() if "/READINESS_ATTEMPT_" in n and n.endswith(".json")}
    ws={p.relative_to(root).as_posix() for p in (root/"experiments").glob("M*/READINESS_ATTEMPT_*.json") if p.is_file()} if (root/"experiments").is_dir() else set()
    return sorted(hs|ws)

def delivery_accounting(root:Path,protocol:Mapping[str,Any])->dict[str,Any]:
    unique={}
    for p in _all_attempt_paths(root):
        for src,payload in (("wt",_working(root,p)),("head",head_blob(root,p))):
            if payload is None:continue
            try:r=json.loads(normalized(payload).decode())
            except Exception:continue
            if not isinstance(r,dict) or r.get("verdict")!=DELIVERY_VERDICT:continue
            dg=r.get("result_sha256") or sha256(canonical_bytes(r));unique.setdefault(dg,p)
    spent=len(unique);floor=protocol.get("inherited_delivery_spent")
    if floor!=4:raise GateError("protocol does not preserve inherited 4/6 count")
    if spent<floor:raise GateError("delivery reconstruction found %d below inherited %d"%(spent,floor))
    if spent>=TOTAL_DELIVERY_CEILING:raise GateError("global delivery ceiling exhausted")
    return {"spent":spent,"total":TOTAL_DELIVERY_CEILING,"remaining":TOTAL_DELIVERY_CEILING-spent,"unique_delivery_result_digests":sorted(unique)}

def load_resume_state(root:Path,protocol_sha:str)->dict[str,Any]:
    w=_working(root,JOURNAL_REL);h=head_blob(root,JOURNAL_REL)
    if w is None and h is None:return {"schema":"m125-step-journal-v1","protocol_sha256":protocol_sha,"steps":{}}
    if w is None or h is None:raise GateError("resume journal exists on only one authoritative surface")
    if normalized(w)!=normalized(h):raise GateError("resume journal differs from HEAD")
    r=_parse(h,"resume journal")
    if r.get("schema")!="m125-step-journal-v1" or r.get("protocol_sha256")!=protocol_sha or not isinstance(r.get("steps"),dict):raise GateError("resume journal invalid")
    for n,s in r["steps"].items():
        if not isinstance(s,dict) or s.get("answered") is not True:raise GateError("persisted step %s is not answered"%n)
    return r

def precredential_context(root:Path)->dict[str,Any]:
    root=Path(root);anti=inspect_anti_rearm(root);p=load_frozen_protocol(root);m=verify_source_manifest(root,p);verify_delivery_records_match_protocol(anti,p["protocol_sha256"]);a=load_network_authorization(root,p["protocol_sha256"]);d=delivery_accounting(root,p);j=load_resume_state(root,p["protocol_sha256"])
    return {"protocol":p,"manifest":m,"authorization":a,"delivery_accounting":d,"resume_journal":j,"anti_rearm":anti,"credential_access_permitted":True}

def offline_preflight(root:Path)->dict[str,Any]:
    root=Path(root);anti=inspect_anti_rearm(root);p=load_frozen_protocol(root);m=verify_source_manifest(root,p);verify_delivery_records_match_protocol(anti,p["protocol_sha256"]);d=delivery_accounting(root,p)
    return {"protocol_sha256":p["protocol_sha256"],"manifest_paths":sorted(m),"delivery_accounting":d,"anti_rearm":anti,"network_authorization_present":head_blob(root,AUTHORIZATION_REL) is not None,"credential_access_permitted":False}
