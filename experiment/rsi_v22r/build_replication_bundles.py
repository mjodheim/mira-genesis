#!/usr/bin/env python3
"""Deterministically rebind exact V22 R1 capsules into fresh V22R proposer slots.

No parent source, evaluator commitment, public guard, allowed path, protocol or
verifier is changed. The source capsule hash must match one of the three exact
pre-evaluator V22 R1 capsules.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import zipfile
from pathlib import Path

EXPECTED = {
    "brewstead-game-state-estate-max-fields": {
        "file": "genesis-v22-brewstead-game-state-estate-max-fields-r1-shared-s1.zip",
        "sha256": "8a4c473d31d088240a81faca9b13e52f5d3fac308173c9211816ae0bff9d0f73",
    },
    "brewstead-progression-merchant-coin-bonus": {
        "file": "genesis-v22-brewstead-progression-merchant-coin-bonus-r1-shared-s1.zip",
        "sha256": "75255ab5c377a53797b50f37d2bf0ed6d1562e655ee089f8e61e445ba2610295",
    },
    "brewstead-catalog-crop-ingredient-name": {
        "file": "genesis-v22-brewstead-catalog-crop-ingredient-name-r1-shared-s1.zip",
        "sha256": "ef1f4da85734af6df8108fdaece0011a1b64f4eaeac391a49a3b87fd91edc533",
    },
}
MEMBERS = {
    "PROMPT.txt",
    "V22_TRANSFER_PROPOSER_PROTOCOL.md",
    "VERIFY_OUTPUT.py",
    "parent.tar.gz",
    "task-manifest.json",
}

def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def zip_bytes(entries: dict[str, bytes]) -> bytes:
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in entries.items():
            zi=zipfile.ZipInfo(name,date_time=(2026,9,24,0,0,0))
            zi.compress_type=zipfile.ZIP_DEFLATED
            zi.external_attr=(0o100644 & 0xFFFF)<<16
            z.writestr(zi,data)
    return out.getvalue()

def rewrite_prompt(raw: bytes, task_id: str) -> bytes:
    text=raw.decode("utf-8")
    text=text.replace(
        "GENESIS RSI V22 — BREWSTEAD RETAINED-EVALUATOR TRANSFER REPAIR",
        "GENESIS RSI V22R — BREWSTEAD RETAINED-EVALUATOR TRANSFER REPAIR",
        1,
    )
    needle=f"Task: {task_id}\n"
    replacement=(
        f"Task: {task_id}\n"
        "Replication attempt: V22R. Prior V22 proposer outputs are forbidden information.\n"
    )
    if needle not in text:
        raise ValueError("source prompt task line missing")
    return text.replace(needle,replacement,1).encode("utf-8")

def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--input-dir",type=Path,required=True)
    ap.add_argument("--apparatus-commit",required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)

    records=[]
    for task_id,cfg in EXPECTED.items():
        src=args.input_dir/cfg["file"]
        raw=src.read_bytes()
        if sha_bytes(raw)!=cfg["sha256"]:
            raise SystemExit(f"source capsule hash mismatch: {src}")
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            if set(z.namelist())!=MEMBERS:
                raise SystemExit(f"source capsule member mismatch: {src}")
            entries={name:z.read(name) for name in z.namelist()}

        manifest=json.loads(entries["task-manifest.json"])
        if manifest["task_id"]!=task_id:
            raise SystemExit("task id mismatch")
        if manifest["round"]!=1 or manifest["arm_id"]!="shared":
            raise SystemExit("source is not shared R1")
        manifest["campaign_slot_id"]=f"v22r-{task_id}-r1-shared-s1"
        manifest["freeze_commit"]=args.apparatus_commit
        mbytes=(json.dumps(manifest,indent=2,sort_keys=True)+"\n").encode("utf-8")

        entries["task-manifest.json"]=mbytes
        entries["PROMPT.txt"]=rewrite_prompt(entries["PROMPT.txt"],task_id)
        out_bytes=zip_bytes(entries)
        dest=args.out/f"genesis-v22r-{task_id}-r1-shared-s1.zip"
        dest.write_bytes(out_bytes)
        records.append({
            "task_id":task_id,
            "file":dest.name,
            "sha256":sha_bytes(out_bytes),
            "task_manifest_sha256":sha_bytes(mbytes),
            "parent_archive_sha256":manifest["parent_archive_sha256"],
            "parent_tree_digest":manifest["parent_tree_digest"],
            "evaluator_commitment_sha256":manifest["evaluator_commitment_sha256"],
            "campaign_slot_id":manifest["campaign_slot_id"],
        })

    print(json.dumps({"schema":"mira-genesis-rsi-v22r-bundle-build-v1","bundles":records},indent=2,sort_keys=True))

if __name__=="__main__":
    main()
