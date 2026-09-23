#!/usr/bin/env python3
"""Internal isolated worker for one already-guarded V23 policy call."""
from __future__ import annotations
import importlib.util,json,sys
from pathlib import Path

def limits()->None:
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        resource.setrlimit(resource.RLIMIT_CPU,(1,1))
        resource.setrlimit(resource.RLIMIT_FSIZE,(1024*1024,1024*1024))
        resource.setrlimit(resource.RLIMIT_NOFILE,(32,32))
        cap=512*1024*1024
        resource.setrlimit(resource.RLIMIT_AS,(cap,cap))
    except (ImportError,ValueError,OSError):
        pass

def main()->None:
    if len(sys.argv)!=2: raise SystemExit("worker requires candidate path")
    limits()
    payload=json.loads(sys.stdin.read())
    path=Path(sys.argv[1]).resolve()
    name="v23_candidate"
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError("cannot load candidate")
    module=importlib.util.module_from_spec(spec); sys.modules[name]=module; spec.loader.exec_module(module)
    metadata=tuple(module.policy_metadata())
    if len(metadata)!=10 or any(type(x) is not int for x in metadata): raise ValueError("invalid policy metadata")
    selected=list(module.select_parent_batch(payload["view"],int(payload["max_parallelism"])))
    sys.stdout.write(json.dumps({"metadata":metadata,"selected_parent_ids":selected},sort_keys=True)+"\n")
if __name__=="__main__": main()
