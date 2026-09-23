#!/usr/bin/env python3
from __future__ import annotations
import argparse, gzip, hashlib, io, json, shutil, subprocess, tarfile, tempfile, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
HOST_DEFAULT=Path('/mnt/data/v22_host')
PROTOCOL=(ROOT/'V22_TRANSFER_PROPOSER_PROTOCOL.md' if (ROOT/'V22_TRANSFER_PROPOSER_PROTOCOL.md').exists() else ROOT/'protocol'/'V22_TRANSFER_PROPOSER_PROTOCOL.md')
VERIFIER=ROOT/'VERIFY_OUTPUT.py'
PUBLIC_GUARD="./mvnw -q -Dtest='*ServiceTest,*ControllerTest,DomainBehaviorTest,RequestValidationTest,MapperTest,GameClockTest,ApiExceptionHandlerTest' test"
TASKS={
 'brewstead-game-state-estate-max-fields':{
  'source':'src/main/java/be/mjodheim/brewstead/service/GameStateService.java',
  'defect':'defects/game-state-estate-max-fields.patch',
  'evaluator':'evaluator/GameStateEstateReservedTest.java',
  'symptom':'Estate metadata must report the field capacity from the field schedule, not the hive capacity.'},
 'brewstead-progression-merchant-coin-bonus':{
  'source':'src/main/java/be/mjodheim/brewstead/service/ProgressionService.java',
  'defect':'defects/progression-merchant-coin-bonus.patch',
  'evaluator':'evaluator/ProgressionMerchantReservedTest.java',
  'symptom':'The MARCHAND specialization must add its 10% NPC-order coin bonus while other specializations keep the base reward.'},
 'brewstead-catalog-crop-ingredient-name':{
  'source':'src/main/java/be/mjodheim/brewstead/service/CatalogService.java',
  'defect':'defects/catalog-crop-ingredient-name.patch',
  'evaluator':'evaluator/CatalogCropIngredientReservedTest.java',
  'symptom':"Crop catalog entries must expose the linked ingredient's name rather than repeating the crop name."},
}

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
            rel=p.relative_to(root).as_posix()
            ti=tf.gettarinfo(str(p),arcname=rel)
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
            zi.external_attr=(0o100644 & 0xFFFF)<<16
            z.writestr(zi,data)
    return out.getvalue()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--host',type=Path,default=HOST_DEFAULT)
    ap.add_argument('--freeze-commit',required=True)
    ap.add_argument('--out',type=Path,default=Path('/mnt/data/v22_bundles'))
    a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    for task_id,cfg in TASKS.items():
        with tempfile.TemporaryDirectory(prefix='v22-root-') as td:
            parent=Path(td)/'parent'
            shutil.copytree(a.host,parent)
            q=subprocess.run(['git','apply',str(ROOT/cfg['defect'])],cwd=parent,capture_output=True,text=True)
            if q.returncode:
                raise SystemExit(q.stderr)
            parent_tar=deterministic_tar_gz(parent)
            tdig=tree_digest(parent)
            source_sha=sha_file(parent/cfg['source'])
            node=f"v22-{task_id}-root"
            slot=f"v22-{task_id}-r1-shared-s1"
            manifest={
              'allowed_source_path':cfg['source'],
              'arm_id':'shared',
              'campaign_slot_id':slot,
              'evaluator_only_test_included':False,
              'evaluator_commitment_sha256':sha_file(ROOT/cfg['evaluator']),
              'freeze_commit':a.freeze_commit,
              'host_commit':'720b27c8bc80de16c04953e13d5f9e8425beea8c',
              'host_repository':'mjodheim/mjodheim-brewstead',
              'parent_archive_sha256':sha_bytes(parent_tar),
              'parent_node_id':node,
              'parent_quality_milli':0,
              'parent_source_sha256':source_sha,
              'parent_tree_digest':tdig,
              'policy_selected_parent_order':[node],
              'public_guard_command':PUBLIC_GUARD,
              'public_symptom':cfg['symptom'],
              'round':1,
              'schema':'mira-genesis-rsi-v22-transfer-task-manifest-v1',
              'task_id':task_id,
            }
            mbytes=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode()
            prompt=f'''GENESIS RSI V22 — BREWSTEAD RETAINED-EVALUATOR TRANSFER REPAIR

Task: {task_id}
Public symptom: {cfg['symptom']}

Use ONLY this bundle. No web, GitHub, plugins, connectors, saved memory, previous chats, Mira Genesis project context, reserved evaluator source/results, other V22 attempts/slots, G1/G2 selection information, or human candidate-specific hints.

Read V22_TRANSFER_PROPOSER_PROTOCOL.md completely. It is authoritative.

Allowed production source path: {cfg['source']}

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
            entries={
              'PROMPT.txt':prompt,
              'V22_TRANSFER_PROPOSER_PROTOCOL.md':PROTOCOL.read_bytes(),
              'VERIFY_OUTPUT.py':VERIFIER.read_bytes(),
              'parent.tar.gz':parent_tar,
              'task-manifest.json':mbytes,
            }
            zb=zip_bytes(entries)
            dest=a.out/f'genesis-v22-{task_id}-r1-shared-s1.zip'
            dest.write_bytes(zb)
            print(dest.name,sha_bytes(zb),manifest['parent_tree_digest'],manifest['evaluator_commitment_sha256'])

if __name__=='__main__':
    main()
