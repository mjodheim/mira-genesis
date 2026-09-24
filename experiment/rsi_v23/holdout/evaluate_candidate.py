#!/usr/bin/env python3
"""External retained evaluator for V23/L5 holdout candidate source bytes."""
from __future__ import annotations
import argparse, hashlib, json, shutil, subprocess, tempfile, xml.etree.ElementTree as ET
from pathlib import Path

TASKS = {
 "brewtrack-brewmath-precision": {
   "source":"Domain/BrewMath.cs","kind":"dotnet",
   "patch":"experiment/rsi_v23/holdout/defects/brewtrack-brewmath-precision.patch",
   "reserved":"experiment/rsi_v23/holdout/evaluator/L5BrewMathReservedTests.cs",
   "reserved_name":"L5BrewMathReservedTests",
 },
 "brewtrack-recipemath-units-water": {
   "source":"Domain/RecipeMath.cs","kind":"dotnet",
   "patch":"experiment/rsi_v23/holdout/defects/brewtrack-recipemath-units-water.patch",
   "reserved":"experiment/rsi_v23/holdout/evaluator/L5RecipeMathReservedTests.cs",
   "reserved_name":"L5RecipeMathReservedTests",
 },
 "brewstead-effect-rounding": {
   "source":"src/main/java/be/mjodheim/brewstead/service/EffectService.java","kind":"java",
   "patch":"experiment/rsi_v23/holdout/defects/brewstead-effect-rounding.patch",
   "reserved":"experiment/rsi_v23/holdout/evaluator/L5EffectServiceReservedTest.java",
   "reserved_name":"L5EffectServiceReservedTest",
 },
 "brewstead-brew-lifecycle-thresholds": {
   "source":"src/main/java/be/mjodheim/brewstead/service/BrewService.java","kind":"java",
   "patch":"experiment/rsi_v23/holdout/defects/brewstead-brew-lifecycle-thresholds.patch",
   "reserved":"experiment/rsi_v23/holdout/evaluator/L5BrewServiceReservedTest.java",
   "reserved_name":"L5BrewServiceReservedTest",
 },
}

def _run(cmd,cwd,timeout=240):
 p=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True,timeout=timeout)
 return p.returncode,p.stdout,p.stderr

def defect_root_source(task_id:str,host_root:Path,apparatus_root:Path)->str:
 t=TASKS[task_id]
 source=(host_root/t["source"]).read_text(encoding="utf-8-sig")
 with tempfile.TemporaryDirectory(prefix="v23-l5-root-") as td:
  root=Path(td); target=root/t["source"]; target.parent.mkdir(parents=True,exist_ok=True)
  target.write_text(source,encoding="utf-8")
  _run(["git","init","-q"],root)
  rc,out,err=_run(["git","apply",str((apparatus_root/t["patch"]).resolve())],root)
  if rc: raise RuntimeError("defect patch failed: "+err[-2000:])
  return target.read_text(encoding="utf-8")

def _trx_counts(path:Path)->dict[str,int]:
 root=ET.parse(path).getroot()
 for elem in root.iter():
  if elem.tag.endswith("Counters"):
   return {k:int(v) for k,v in elem.attrib.items() if v.isdigit()}
 raise RuntimeError("no TRX counters")

def _surefire_counts(path:Path)->dict[str,int]:
 root=ET.parse(path).getroot()
 return {k:int(root.attrib.get(k,0)) for k in ("tests","failures","errors","skipped")}

def evaluate(task_id:str,source_text:str,host_root:Path,apparatus_root:Path)->dict:
 t=TASKS[task_id]
 digest=hashlib.sha256(source_text.encode()).hexdigest()
 with tempfile.TemporaryDirectory(prefix="v23-l5-eval-") as td:
  work=Path(td)/"host"; shutil.copytree(host_root,work,symlinks=True)
  (work/t["source"]).write_text(source_text,encoding="utf-8")
  if t["kind"]=="dotnet":
   proj=work/"Tests/L5Snapshot.Tests.csproj"
   rc,so,se=_run(["dotnet","build",str(proj),"-c","Release"],work)
   if rc: return {"quality_milli":0,"public_guard_pass":False,"reserved_passed":0,"source_sha256":digest,"phase":"public_build"}
   rc,so,se=_run(["dotnet","test",str(proj),"-c","Release","--no-build","--filter","FullyQualifiedName~BrewMathTests|FullyQualifiedName~RecipeMathTests"],work)
   if rc: return {"quality_milli":0,"public_guard_pass":False,"reserved_passed":0,"source_sha256":digest,"phase":"public_test"}
   reserved_target=work/"Tests"/Path(t["reserved"]).name
   shutil.copy2(apparatus_root/t["reserved"],reserved_target)
   log="reserved.trx"
   rc,so,se=_run(["dotnet","test",str(proj),"-c","Release","--filter",f"FullyQualifiedName~{t['reserved_name']}","--logger",f"trx;LogFileName={log}"],work)
   trx=next((work/"Tests/TestResults").rglob(log))
   c=_trx_counts(trx); passed=int(c.get("passed",0)); total=int(c.get("total",0))
  else:
   mvnw=work/"mvnw"; mvnw.chmod(mvnw.stat().st_mode|0o111)
   public="*ServiceTest,*ControllerTest,DomainBehaviorTest,RequestValidationTest,MapperTest,GameClockTest,ApiExceptionHandlerTest"
   rc,so,se=_run(["./mvnw","-q",f"-Dtest={public}","test"],work)
   if rc: return {"quality_milli":0,"public_guard_pass":False,"reserved_passed":0,"source_sha256":digest,"phase":"public_test"}
   reserved_target=work/"src/test/java/be/mjodheim/brewstead/service"/Path(t["reserved"]).name
   shutil.copy2(apparatus_root/t["reserved"],reserved_target)
   rc,so,se=_run(["./mvnw","-q",f"-Dtest={t['reserved_name']}","test"],work)
   xml=work/f"target/surefire-reports/TEST-be.mjodheim.brewstead.service.{t['reserved_name']}.xml"
   c=_surefire_counts(xml); total=c["tests"]; passed=total-c["failures"]-c["errors"]-c["skipped"]
  if total!=4: raise RuntimeError(f"reserved evaluator produced {total} assertions, expected 4")
  return {"quality_milli":250*passed,"public_guard_pass":True,"reserved_passed":passed,"source_sha256":digest,"phase":"complete"}

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("task_id"); ap.add_argument("source",type=Path)
 ap.add_argument("--host-root",type=Path,required=True); ap.add_argument("--apparatus-root",type=Path,default=Path("."))
 a=ap.parse_args()
 result=evaluate(a.task_id,a.source.read_text(encoding="utf-8"),a.host_root,a.apparatus_root.resolve())
 print(json.dumps(result,indent=2,sort_keys=True))
if __name__=="__main__": main()
