#!/usr/bin/env python3
"""Build the next V22 proposer capsules exactly from frozen campaign plans."""
from __future__ import annotations
import argparse, gzip, hashlib, io, json, shutil, subprocess, tarfile, tempfile, zipfile
from pathlib import Path
import campaign

HERE=Path(__file__).resolve().parent
PROTOCOL=HERE/'V22_TRANSFER_PROPOSER_PROTOCOL.md'
if not PROTOCOL.exists(): PROTOCOL=HERE/'protocol'/'V22_TRANSFER_PROPOSER_PROTOCOL.md'
VERIFIER=HERE/'VERIFY_OUTPUT.py'

def sha_bytes(b:bytes)->str: return hashlib.sha256(b).hexdigest()
def sha_file(p:Path)->str: return sha_bytes(p.read_bytes())

def tree_digest(root:Path)->str:
    h=hashlib.sha256()
    for p in sorted(x for x in root.rglob('*') if x.is_file() and '.git' not in x.parts):
        rel=p.relative_to(root).as_posix().encode()
        h.update(rel+b'\0'+hashlib.sha256(p.read_bytes()).hexdigest().encode()+b'\n')
    return h.hexdigest()

def deterministic_tar_gz(root:Path)->bytes:
    raw=io.BytesIO()
    with tarfile.open(fileobj=raw,mode='w') as tf:
        for p in sorted(root.rglob('*'), key=lambda x:x.relative_to(root).as_posix()):
            if '.git' in p.parts: continue
            rel=p.relative_to(root).as_posix(); ti=tf.gettarinfo(str(p),arcname=rel)
            ti.uid=ti.gid=0; ti.uname=ti.gname=''; ti.mtime=0
            if p.is_file():
                with p.open('rb') as f: tf.addfile(ti,f)
            else: tf.addfile(ti)
    out=io.BytesIO()
    with gzip.GzipFile(fileobj=out,mode='wb',mtime=0,filename='') as gz: gz.write(raw.getvalue())
    return out.getvalue()

def zip_bytes(entries:dict[str,bytes])->bytes:
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in entries.items():
            zi=zipfile.ZipInfo(name,date_time=(2026,9,23,0,0,0)); zi.compress_type=zipfile.ZIP_DEFLATED
            zi.external_attr=(0o100644 & 0xFFFF)<<16; z.writestr(zi,data)
    return out.getvalue()

def extract_root_parent(root_bundle:Path,dest:Path)->dict:
    with zipfile.ZipFile(root_bundle) as z:
        names=set(z.namelist())
        required={'PROMPT.txt','V22_TRANSFER_PROPOSER_PROTOCOL.md','VERIFY_OUTPUT.py','parent.tar.gz','task-manifest.json'}
        if names!=required: raise ValueError(f'root bundle members differ: {sorted(names)}')
        manifest=json.loads(z.read('task-manifest.json')); tar_bytes=z.read('parent.tar.gz')
    with tarfile.open(fileobj=io.BytesIO(tar_bytes),mode='r:gz') as tf: tf.extractall(dest,filter='data')
    return manifest

def find_patch(results_dir:Path,sha:str)->Path:
    matches=[p for p in results_dir.rglob('proposal.patch') if sha_file(p)==sha]
    if len(matches)!=1: raise ValueError(f'expected one proposal.patch with {sha}, found {len(matches)}')
    return matches[0]

def lineage(state:dict,parent_id:str)->list[dict]:
    rows=[]; cur=state['nodes'][parent_id]
    while cur['parent_node_id'] is not None:
        rows.append(cur); cur=state['nodes'][cur['parent_node_id']]
    return list(reversed(rows))

def materialize(state:dict,parent_id:str,root_bundle:Path,results_dir:Path,dest:Path)->dict:
    manifest=extract_root_parent(root_bundle,dest)
    if manifest['task_id']!=state['task_id']: raise ValueError('root bundle task mismatch')
    for node in lineage(state,parent_id):
        patch=find_patch(results_dir,node['proposal_patch_sha256'])
        q=subprocess.run(['git','apply',str(patch.resolve())],cwd=dest,capture_output=True,text=True)
        if q.returncode: raise ValueError(f'failed to reconstruct {node["node_id"]}: {q.stderr}')
    node=state['nodes'][parent_id]
    if tree_digest(dest)!=node['tree_digest']: raise ValueError('materialized parent tree digest mismatch')
    if sha_file(dest/state['allowed_source_path'])!=node['source_sha256']: raise ValueError('materialized parent source digest mismatch')
    return manifest

def prompt(task_id:str,symptom:str,source:str)->bytes:
    return f'''GENESIS RSI V22 — BREWSTEAD RETAINED-EVALUATOR TRANSFER REPAIR

Task: {task_id}
Public symptom: {symptom}

Use ONLY this bundle. No web, GitHub, plugins, connectors, saved memory, previous chats, Mira Genesis project context, reserved evaluator source/results, other V22 attempts/slots, G1/G2 selection information, or human candidate-specific hints.

Read V22_TRANSFER_PROPOSER_PROTOCOL.md completely. It is authoritative.

Allowed production source path: {source}

Extract parent.tar.gz as the exact supplied parent.
Inspect the supplied public source and public tests.
Produce the smallest causal repair for the public symptom while preserving existing correct behavior.

Before returning, run:
python3 VERIFY_OUTPUT.py proposal.patch transcript.json

Do not return until it prints exactly:
GENESIS_RSI_V22_TRANSFER_OUTPUT=PASS

Return exactly proposal.patch and transcript.json.
No prose outside the two files.
'''.encode()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--state',type=Path,required=True); ap.add_argument('--arm',choices=['g1','g2'],required=True)
    ap.add_argument('--root-bundle',type=Path,required=True); ap.add_argument('--results-dir',type=Path,required=True)
    ap.add_argument('--freeze-commit',required=True); ap.add_argument('--out',type=Path,required=True); a=ap.parse_args()
    state=json.loads(a.state.read_text()); plan=campaign.plan_next(state,a.arm); a.out.mkdir(parents=True,exist_ok=True)
    if not plan['selected_parent_ids']:
        print(json.dumps(plan,sort_keys=True)); return
    records=[]
    for i,parent_id in enumerate(plan['selected_parent_ids'],1):
        with tempfile.TemporaryDirectory(prefix='v22-parent-') as td:
            parent=Path(td); root_manifest=materialize(state,parent_id,a.root_bundle,a.results_dir,parent)
            tar=deterministic_tar_gz(parent); node=state['nodes'][parent_id]
            slot=f"v22-{state['task_id']}-r{plan['round']}-{a.arm}-s{i}"
            manifest={'allowed_source_path':state['allowed_source_path'],'arm_id':a.arm,'campaign_slot_id':slot,
              'evaluator_only_test_included':False,'evaluator_commitment_sha256':root_manifest['evaluator_commitment_sha256'],
              'freeze_commit':a.freeze_commit,'host_commit':root_manifest['host_commit'],'host_repository':root_manifest['host_repository'],
              'parent_archive_sha256':sha_bytes(tar),'parent_node_id':parent_id,'parent_quality_milli':node['outcome']['quality_milli'],
              'parent_source_sha256':node['source_sha256'],'parent_tree_digest':node['tree_digest'],
              'policy_selected_parent_order':plan['selected_parent_ids'],'public_guard_command':root_manifest['public_guard_command'],
              'public_symptom':root_manifest['public_symptom'],'round':plan['round'],
              'schema':'mira-genesis-rsi-v22-transfer-task-manifest-v1','task_id':state['task_id']}
            mbytes=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode()
            entries={'PROMPT.txt':prompt(state['task_id'],manifest['public_symptom'],state['allowed_source_path']),
                     'V22_TRANSFER_PROPOSER_PROTOCOL.md':PROTOCOL.read_bytes(),'VERIFY_OUTPUT.py':VERIFIER.read_bytes(),
                     'parent.tar.gz':tar,'task-manifest.json':mbytes}
            zb=zip_bytes(entries); dest=a.out/f"genesis-v22-{state['task_id']}-r{plan['round']}-{a.arm}-s{i}.zip"; dest.write_bytes(zb)
            records.append({'file':dest.name,'sha256':sha_bytes(zb),'slot':slot,'parent_node_id':parent_id,'parent_tree_digest':node['tree_digest']})
    print(json.dumps({'plan':plan,'bundles':records},indent=2,sort_keys=True))
if __name__=='__main__': main()
