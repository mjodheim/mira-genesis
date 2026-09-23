#!/usr/bin/env python3
"""Evaluate one returned V22 proposal against the retained lab boundary."""
from __future__ import annotations
import argparse, hashlib, json, shutil, subprocess, tarfile, tempfile, zipfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
CALIBRATION = HERE / "calibration-manifest.json"
EVALUATOR_DIR = HERE / "evaluator"
SCHEMA = "mira-genesis-rsi-v22-evaluation-v1"

def sha256_bytes(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def sha256_file(path: Path) -> str: return sha256_bytes(path.read_bytes())

def tree_digest(root: Path) -> str:
    h=hashlib.sha256()
    for p in sorted(x for x in root.rglob("*") if x.is_file() and ".git" not in x.parts):
        rel=p.relative_to(root).as_posix().encode()
        h.update(rel+b"\0"+hashlib.sha256(p.read_bytes()).hexdigest().encode()+b"\n")
    return h.hexdigest()

def run(cmd: list[str] | str, *, cwd: Path, shell: bool=False) -> dict[str, Any]:
    p=subprocess.run(cmd,cwd=cwd,shell=shell,text=True,capture_output=True)
    return {"returncode":p.returncode,"stdout_tail":p.stdout[-4000:],"stderr_tail":p.stderr[-4000:]}

def load_task(task_id: str) -> dict[str, Any]:
    manifest=json.loads(CALIBRATION.read_text(encoding="utf-8"))
    matches=[x for x in manifest["tasks"] if x["task_id"]==task_id]
    if len(matches)!=1: raise ValueError(f"unknown or duplicate task_id: {task_id}")
    return matches[0]

def safe_extract_zip(path: Path,dest: Path)->None:
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        if any(Path(n).is_absolute() or ".." in Path(n).parts for n in names): raise ValueError("unsafe zip member")
        z.extractall(dest)

def safe_extract_tar(path: Path,dest: Path)->None:
    with tarfile.open(path,"r:gz") as tf: tf.extractall(dest,filter="data")

def evaluate(bundle: Path,proposal: Path,transcript: Path)->dict[str,Any]:
    result={"schema":SCHEMA,"bundle_sha256":sha256_file(bundle),"proposal_patch_sha256":sha256_file(proposal),
            "transcript_sha256":sha256_file(transcript),"represented_observation":False,"mechanical_valid":False,
            "public_guard_pass":False,"reserved_objective_pass":False,"quality_milli":None,
            "infrastructure_preflight_pass":False}
    with tempfile.TemporaryDirectory(prefix="v22-eval-") as td:
        td=Path(td); capsule=td/"capsule"; capsule.mkdir(); safe_extract_zip(bundle,capsule)
        required={"PROMPT.txt","V22_TRANSFER_PROPOSER_PROTOCOL.md","VERIFY_OUTPUT.py","parent.tar.gz","task-manifest.json"}
        found={p.name for p in capsule.iterdir() if p.is_file()}
        if found!=required:
            result["mechanical_error"]=f"bundle members mismatch: {sorted(found)}"; return result
        tm=json.loads((capsule/"task-manifest.json").read_text(encoding="utf-8"))
        result.update(task_id=tm["task_id"],campaign_slot_id=tm["campaign_slot_id"],
                      parent_node_id=tm["parent_node_id"],parent_tree_digest=tm["parent_tree_digest"])
        task=load_task(tm["task_id"])
        if task["allowed_source_path"]!=tm["allowed_source_path"]:
            result["mechanical_error"]="allowed source mismatch with frozen calibration manifest"; return result
        verifier=run(["python3",str(capsule/"VERIFY_OUTPUT.py"),str(proposal.resolve()),str(transcript.resolve())],cwd=capsule)
        result["output_verifier"]=verifier
        if verifier["returncode"]!=0 or "GENESIS_RSI_V22_TRANSFER_OUTPUT=PASS" not in verifier["stdout_tail"]:
            result["mechanical_error"]="output verifier failed"; return result
        result["mechanical_valid"]=True
        parent=td/"parent"; parent.mkdir(); safe_extract_tar(capsule/"parent.tar.gz",parent)
        if tree_digest(parent)!=tm["parent_tree_digest"]:
            result["mechanical_valid"]=False; result["mechanical_error"]="extracted parent tree digest mismatch"; return result

        # Compile an untouched copy so Maven-generated target/ files never enter
        # the content-addressed candidate tree.
        preflight_parent=td/"preflight-parent"; shutil.copytree(parent,preflight_parent)
        preflight=run(["./mvnw","-q","-DskipTests","compile"],cwd=preflight_parent)
        result["infrastructure_preflight"]=preflight
        if preflight["returncode"]!=0:
            result["infrastructure_error"]="exact parent failed Maven compile preflight"; return result
        result["infrastructure_preflight_pass"]=True

        applied=run(["git","apply",str(proposal.resolve())],cwd=parent); result["patch_apply"]=applied
        if applied["returncode"]!=0:
            result["mechanical_valid"]=False; result["mechanical_error"]="patch failed after verifier acceptance"; return result

        # Bind the candidate identity before adding any lab-only evaluator source
        # or running Maven tests.
        candidate_tree_digest=tree_digest(parent)
        candidate_source_sha256=sha256_file(parent/tm["allowed_source_path"])

        evaluator_source=EVALUATOR_DIR/next(p.name for p in EVALUATOR_DIR.glob("*.java") if p.stem==task["reserved_test"])
        commitment=sha256_file(evaluator_source); result["evaluator_commitment_sha256"]=commitment
        if commitment!=tm["evaluator_commitment_sha256"]:
            result["infrastructure_error"]="reserved evaluator commitment mismatch"; return result
        test_dir=parent/"src/test/java/be/mjodheim/brewstead/service"; shutil.copy2(evaluator_source,test_dir/evaluator_source.name)
        public=run(tm["public_guard_command"],cwd=parent,shell=True); result["public_guard"]=public
        result["public_guard_pass"]=public["returncode"]==0
        reserved=run(["./mvnw","-q",f"-Dtest={task['reserved_test']}","test"],cwd=parent); result["reserved_objective"]=reserved
        result["reserved_objective_pass"]=reserved["returncode"]==0
        result["represented_observation"]=True
        result["quality_milli"]=1000 if result["public_guard_pass"] and result["reserved_objective_pass"] else 0
        result["tree_digest"]=candidate_tree_digest
        result["source_sha256"]=candidate_source_sha256
        return result

def main()->None:
    ap=argparse.ArgumentParser(); ap.add_argument("bundle",type=Path); ap.add_argument("proposal",type=Path)
    ap.add_argument("transcript",type=Path); ap.add_argument("--out",type=Path); args=ap.parse_args()
    result=evaluate(args.bundle,args.proposal,args.transcript); text=json.dumps(result,indent=2,sort_keys=True)+"\n"
    if args.out: args.out.write_text(text,encoding="utf-8")
    print(text,end="")
    if not result.get("mechanical_valid"): raise SystemExit(20)
    if not result.get("infrastructure_preflight_pass") or "infrastructure_error" in result: raise SystemExit(30)

if __name__=="__main__": main()
