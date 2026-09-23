#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,subprocess,sys,tarfile,tempfile
from pathlib import Path

SCHEMA="mira-genesis-rsi-v22-transfer-proposal-v1"
TOP={
 "schema","task_id","campaign_slot_id","parent_node_id","parent_tree_digest",
 "host_commit","task_manifest_sha256","proposer_protocol_sha256",
 "proposal_patch_sha256","intent","rationale","files_changed","public_checks",
 "uncertainties","information_boundary",
}
INFO={
 "used_only_supplied_bundle":True,
 "used_web_or_github":False,
 "used_saved_memory_or_previous_chats":False,
 "used_reserved_evaluator_source_or_result":False,
 "used_other_v22_attempt_or_slot_output":False,
 "used_g1_g2_selection_information":False,
 "used_human_candidate_specific_guidance":False,
}

def sha(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def patch_paths(path:Path)->list[str]:
    out=[]
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("diff --git a/"):
            q=line.split(" ",3)
            if len(q)!=4 or not q[2].startswith("a/") or not q[3].startswith("b/"):
                raise SystemExit("malformed diff header")
            left,right=q[2][2:],q[3][2:]
            if left!=right:
                raise SystemExit("renames are forbidden")
            out.append(left)
    if not out:
        raise SystemExit("empty patch or missing diff --git header")
    if len(out)!=len(set(out)):
        raise SystemExit("duplicate patch path")
    return sorted(out)

if len(sys.argv)!=3:
    raise SystemExit("usage: VERIFY_OUTPUT.py proposal.patch transcript.json")
proposal=Path(sys.argv[1]).resolve()
transcript=Path(sys.argv[2]).resolve()
manifest_path=Path("task-manifest.json")
protocol_path=Path("V22_TRANSFER_PROPOSER_PROTOCOL.md")
parent_archive=Path("parent.tar.gz")

m=json.loads(manifest_path.read_text())
t=json.loads(transcript.read_text())

if set(t)!=TOP or t.get("schema")!=SCHEMA:
    raise SystemExit("transcript schema/field mismatch")
for k in ("task_id","campaign_slot_id","parent_node_id","parent_tree_digest","host_commit"):
    if t.get(k)!=m.get(k):
        raise SystemExit("manifest identity mismatch: "+k)
if sha(parent_archive)!=m.get("parent_archive_sha256"):
    raise SystemExit("parent archive digest mismatch")
expected={
 "task_manifest_sha256":sha(manifest_path),
 "proposer_protocol_sha256":sha(protocol_path),
 "proposal_patch_sha256":sha(proposal),
}
for k,v in expected.items():
    if t.get(k)!=v:
        raise SystemExit("digest mismatch: "+k)
if t.get("information_boundary")!=INFO:
    raise SystemExit("information boundary mismatch")
for k in ("intent","rationale"):
    if not isinstance(t.get(k),str) or not t[k].strip():
        raise SystemExit("missing "+k)
for k in ("files_changed","public_checks","uncertainties"):
    v=t.get(k)
    if not isinstance(v,list) or not v or any(not isinstance(x,str) or not x.strip() for x in v):
        raise SystemExit("bad list field: "+k)
    if v!=sorted(v) or len(v)!=len(set(v)):
        raise SystemExit("list must be sorted and unique: "+k)
paths=patch_paths(proposal)
if paths!=[m["allowed_source_path"]]:
    raise SystemExit("patch path outside frozen task scope")
if t["files_changed"]!=paths:
    raise SystemExit("files_changed mismatch")
with tempfile.TemporaryDirectory(prefix="v22-proposer-check-") as td:
    root=Path(td)/"host"; root.mkdir()
    with tarfile.open(parent_archive,"r:gz") as tf:
        tf.extractall(root,filter="data")
    q=subprocess.run(["git","apply","--check",str(proposal)],cwd=root,capture_output=True,text=True)
    if q.returncode:
        raise SystemExit("patch does not apply: "+(q.stderr or q.stdout)[-2000:])
print("GENESIS_RSI_V22_TRANSFER_OUTPUT=PASS")
