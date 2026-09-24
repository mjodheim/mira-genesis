#!/usr/bin/env python3
"""Build deterministic fresh-slot V22R root capsules from the frozen host commit.

The builder reconstructs each parent from the exact host checkout plus the
already-frozen defect patch. Archive metadata is normalized so ZIP identity is
not affected by checkout filesystem modes or mtimes.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
V22=ROOT.parent/"rsi_v22"
HOST_COMMIT="720b27c8bc80de16c04953e13d5f9e8425beea8c"
PROTOCOL=V22/"V22_TRANSFER_PROPOSER_PROTOCOL.md"
VERIFIER=V22/"VERIFY_OUTPUT.py"
PUBLIC_GUARD="./mvnw -q -Dtest='*ServiceTest,*ControllerTest,DomainBehaviorTest,RequestValidationTest,MapperTest,GameClockTest,ApiExceptionHandlerTest' test"

TASKS={
    "brewstead-game-state-estate-max-fields":{
        "source":"src/main/java/be/mjodheim/brewstead/service/GameStateService.java",
        "defect":"defects/game-state-estate-max-fields.patch",
        "evaluator":"evaluator/GameStateEstateReservedTest.java",
        "symptom":"Estate metadata must report the field capacity from the field schedule, not the hive capacity.",
        "expected_parent_tree_digest":"59725b22907797fb0c5c2b58f0b74787b50af35cbc1f7cec318dbc4b1b8b204a",
    },
    "brewstead-progression-merchant-coin-bonus":{
        "source":"src/main/java/be/mjodheim/brewstead/service/ProgressionService.java",
        "defect":"defects/progression-merchant-coin-bonus.patch",
        "evaluator":"evaluator/ProgressionMerchantReservedTest.java",
        "symptom":"The MARCHAND specialization must add its 10% NPC-order coin bonus while other specializations keep the base reward.",
        "expected_parent_tree_digest":"651e4f46d14b2567e056aeea0946fcfda488a83587f146edeb6e2c26d529e5f0",
    },
    "brewstead-catalog-crop-ingredient-name":{
        "source":"src/main/java/be/mjodheim/brewstead/service/CatalogService.java",
        "defect":"defects/catalog-crop-ingredient-name.patch",
        "evaluator":"evaluator/CatalogCropIngredientReservedTest.java",
        "symptom":"Crop catalog entries must expose the linked ingredient's name rather than repeating the crop name.",
        "expected_parent_tree_digest":"c61e697543dd463d893c71fc1a26bde788af35313cfb3117f129c303fc34dde4",
    },
}

def sha_bytes(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def sha_file(path:Path)->str:
    return sha_bytes(path.read_bytes())

def tree_digest(root:Path)->str:
    h=hashlib.sha256()
    for p in sorted(x for x in root.rglob("*") if x.is_file() and ".git" not in x.parts):
        rel=p.relative_to(root).as_posix().encode()
        h.update(rel+b"\0"+hashlib.sha256(p.read_bytes()).hexdigest().encode()+b"\n")
    return h.hexdigest()

def normalized_tar_gz(root:Path)->bytes:
    raw=io.BytesIO()
    with tarfile.open(fileobj=raw,mode="w",format=tarfile.PAX_FORMAT) as tf:
        for p in sorted(root.rglob("*"),key=lambda x:x.relative_to(root).as_posix()):
            if ".git" in p.parts:
                continue
            rel=p.relative_to(root).as_posix()
            ti=tarfile.TarInfo(rel)
            ti.uid=0
            ti.gid=0
            ti.uname=""
            ti.gname=""
            ti.mtime=0
            if p.is_symlink():
                ti.type=tarfile.SYMTYPE
                ti.linkname=os.readlink(p)
                ti.mode=0o777
                ti.size=0
                tf.addfile(ti)
            elif p.is_dir():
                ti.type=tarfile.DIRTYPE
                ti.mode=0o755
                ti.size=0
                tf.addfile(ti)
            elif p.is_file():
                data=p.read_bytes()
                ti.type=tarfile.REGTYPE
                ti.mode=0o755 if rel=="mvnw" else 0o644
                ti.size=len(data)
                tf.addfile(ti,io.BytesIO(data))
            else:
                raise ValueError(f"unsupported host path type: {rel}")
    out=io.BytesIO()
    with gzip.GzipFile(fileobj=out,mode="wb",mtime=0,filename="") as gz:
        gz.write(raw.getvalue())
    return out.getvalue()

def zip_bytes(entries:dict[str,bytes])->bytes:
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in ("PROMPT.txt","V22_TRANSFER_PROPOSER_PROTOCOL.md","VERIFY_OUTPUT.py","parent.tar.gz","task-manifest.json"):
            data=entries[name]
            zi=zipfile.ZipInfo(name,date_time=(2026,9,24,0,0,0))
            zi.compress_type=zipfile.ZIP_DEFLATED
            zi.external_attr=(0o100644 & 0xFFFF)<<16
            z.writestr(zi,data)
    return out.getvalue()

def prompt(task_id:str,symptom:str,source:str)->bytes:
    return f"""GENESIS RSI V22R — BREWSTEAD RETAINED-EVALUATOR TRANSFER REPAIR

Task: {task_id}
Replication attempt: V22R. Prior V22 proposer outputs are forbidden information.
Public symptom: {symptom}

Use ONLY this bundle. No web, GitHub, plugins, connectors, saved memory, previous chats, Mira Genesis project context, reserved evaluator source/results, previous V22/V22R attempts or slots, G1/G2 selection information, or human candidate-specific hints.

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
""".encode()

def assert_host_identity(host:Path)->None:
    q=subprocess.run(["git","rev-parse","HEAD"],cwd=host,text=True,capture_output=True)
    if q.returncode or q.stdout.strip()!=HOST_COMMIT:
        raise SystemExit(f"host commit mismatch: {q.stdout.strip()} {q.stderr.strip()}")

def main()->None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--host",type=Path,required=True)
    ap.add_argument("--apparatus-commit",required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    assert_host_identity(args.host)
    args.out.mkdir(parents=True,exist_ok=True)

    records=[]
    for task_id,cfg in TASKS.items():
        with tempfile.TemporaryDirectory(prefix="v22r-root-") as td:
            parent=Path(td)/"parent"
            shutil.copytree(args.host,parent,ignore=shutil.ignore_patterns(".git"))
            q=subprocess.run(["git","apply",str((V22/cfg["defect"]).resolve())],cwd=parent,text=True,capture_output=True)
            if q.returncode:
                raise SystemExit(q.stderr or q.stdout)

            tdig=tree_digest(parent)
            if tdig!=cfg["expected_parent_tree_digest"]:
                raise SystemExit(f"{task_id}: parent tree digest mismatch {tdig}")

            parent_tar=normalized_tar_gz(parent)
            node=f"v22r-{task_id}-root"
            slot=f"v22r-{task_id}-r1-shared-s1"
            manifest={
                "allowed_source_path":cfg["source"],
                "arm_id":"shared",
                "campaign_slot_id":slot,
                "evaluator_only_test_included":False,
                "evaluator_commitment_sha256":sha_file(V22/cfg["evaluator"]),
                "freeze_commit":args.apparatus_commit,
                "host_commit":HOST_COMMIT,
                "host_repository":"mjodheim/mjodheim-brewstead",
                "parent_archive_sha256":sha_bytes(parent_tar),
                "parent_node_id":node,
                "parent_quality_milli":0,
                "parent_source_sha256":sha_file(parent/cfg["source"]),
                "parent_tree_digest":tdig,
                "policy_selected_parent_order":[node],
                "public_guard_command":PUBLIC_GUARD,
                "public_symptom":cfg["symptom"],
                "round":1,
                "schema":"mira-genesis-rsi-v22-transfer-task-manifest-v1",
                "task_id":task_id,
            }
            mbytes=(json.dumps(manifest,indent=2,sort_keys=True)+"\n").encode()
            entries={
                "PROMPT.txt":prompt(task_id,cfg["symptom"],cfg["source"]),
                "V22_TRANSFER_PROPOSER_PROTOCOL.md":PROTOCOL.read_bytes(),
                "VERIFY_OUTPUT.py":VERIFIER.read_bytes(),
                "parent.tar.gz":parent_tar,
                "task-manifest.json":mbytes,
            }
            bundle=zip_bytes(entries)
            dest=args.out/f"genesis-v22r-{task_id}-r1-shared-s1.zip"
            dest.write_bytes(bundle)
            records.append({
                "task_id":task_id,
                "file":dest.name,
                "sha256":sha_bytes(bundle),
                "task_manifest_sha256":sha_bytes(mbytes),
                "parent_archive_sha256":manifest["parent_archive_sha256"],
                "parent_tree_digest":tdig,
                "parent_source_sha256":manifest["parent_source_sha256"],
                "evaluator_commitment_sha256":manifest["evaluator_commitment_sha256"],
                "campaign_slot_id":slot,
            })

    print(json.dumps({"schema":"mira-genesis-rsi-v22r-root-build-v1","bundles":records},indent=2,sort_keys=True))

if __name__=="__main__":
    main()
