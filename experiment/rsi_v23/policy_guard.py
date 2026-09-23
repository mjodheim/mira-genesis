#!/usr/bin/env python3
"""Static development guard for executable RSI V23 search policies.

This is a containment/overfit guard, not a proof of semantic purity. Fresh online
holdout evaluation remains authoritative.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Iterable

SCHEMA="mira-genesis-rsi-v23-policy-guard-v1"
REQUIRED_FUNCTIONS={"policy_metadata","select_parent_batch"}
BANNED_CALLS={
    "__import__","breakpoint","compile","delattr","dir","eval","exec","getattr",
    "globals","help","input","locals","memoryview","open","setattr","vars",
}
BANNED_NAMES={
    "__builtins__","os","sys","subprocess","socket","pathlib","requests","urllib",
    "http","shutil","tempfile","pickle","marshal","ctypes","importlib","inspect",
}
BANNED_ATTRIBUTE_ROOTS=BANNED_NAMES
ALLOWED_TOPLEVEL=(ast.Expr,ast.FunctionDef,ast.Assign,ast.AnnAssign)
ALLOWED_LITERAL=(ast.Constant,ast.Tuple,ast.List,ast.Set,ast.Dict,ast.UnaryOp)

def sha256_file(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _root_name(node:ast.AST)->str|None:
    cur=node
    while isinstance(cur,ast.Attribute):
        cur=cur.value
    return cur.id if isinstance(cur,ast.Name) else None

def _literal_assignment(node:ast.AST)->bool:
    if isinstance(node,ast.Constant):
        return True
    if isinstance(node,(ast.Tuple,ast.List,ast.Set)):
        return all(_literal_assignment(x) for x in node.elts)
    if isinstance(node,ast.Dict):
        return all((k is None or _literal_assignment(k)) and _literal_assignment(v) for k,v in zip(node.keys,node.values))
    if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
        return _literal_assignment(node.operand)
    return False

def guard_source(source:str,forbidden_tokens:Iterable[str]=())->list[str]:
    problems=[]
    try:
        tree=ast.parse(source)
    except SyntaxError as e:
        return [f"syntax error: {e.msg} at line {e.lineno}"]

    funcs={node.name for node in tree.body if isinstance(node,ast.FunctionDef)}
    missing=sorted(REQUIRED_FUNCTIONS-funcs)
    if missing:
        problems.append("missing required function(s): "+", ".join(missing))

    for node in tree.body:
        if not isinstance(node,ALLOWED_TOPLEVEL):
            problems.append(f"forbidden top-level node: {type(node).__name__}")
        if isinstance(node,ast.Expr):
            if not (isinstance(node.value,ast.Constant) and isinstance(node.value.value,str)):
                problems.append("only a module docstring is allowed as a top-level expression")
        if isinstance(node,ast.Assign) and not _literal_assignment(node.value):
            problems.append("top-level assignments must contain literals only")
        if isinstance(node,ast.AnnAssign) and node.value is not None and not _literal_assignment(node.value):
            problems.append("top-level annotated assignments must contain literals only")

    for node in ast.walk(tree):
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            problems.append(f"imports are forbidden at line {node.lineno}")
        elif isinstance(node,(ast.ClassDef,ast.AsyncFunctionDef,ast.Await,ast.Yield,ast.YieldFrom,ast.With,ast.AsyncWith,ast.Global,ast.Nonlocal)):
            problems.append(f"{type(node).__name__} is forbidden at line {getattr(node,'lineno','?')}")
        elif isinstance(node,ast.Name):
            if node.id in BANNED_NAMES|BANNED_CALLS:
                problems.append(f"forbidden name {node.id!r} at line {node.lineno}")
            if node.id.startswith("__") and node.id.endswith("__") and len(node.id) >= 4:
                problems.append(f"dunder name {node.id!r} is forbidden at line {node.lineno}")
        elif isinstance(node,ast.Attribute):
            if node.attr.startswith("__"):
                problems.append(f"dunder attribute {node.attr!r} is forbidden at line {node.lineno}")
            root=_root_name(node)
            if root in BANNED_ATTRIBUTE_ROOTS:
                problems.append(f"forbidden attribute root {root!r} at line {node.lineno}")
        elif isinstance(node,ast.Call):
            if isinstance(node.func,ast.Name) and node.func.id in BANNED_CALLS:
                problems.append(f"forbidden call {node.func.id!r} at line {node.lineno}")
        elif isinstance(node,ast.Constant) and isinstance(node.value,(str,bytes)):
            raw=node.value.decode("utf-8","ignore") if isinstance(node.value,bytes) else node.value
            if "__" in raw:
                problems.append(f"dunder-like literal {raw!r} is forbidden at line {node.lineno}")
            for token in forbidden_tokens:
                if token and token in raw:
                    problems.append(f"forbidden development token appears in a literal at line {node.lineno}: {token!r}")

    return sorted(set(problems))

def main()->None:
    ap=argparse.ArgumentParser()
    ap.add_argument("policy",type=Path)
    ap.add_argument("--forbidden-token",action="append",default=[])
    ap.add_argument("--forbidden-token-file",type=Path)
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    tokens=list(args.forbidden_token)
    if args.forbidden_token_file:
        tokens.extend(x.strip() for x in args.forbidden_token_file.read_text().splitlines() if x.strip())
    problems=guard_source(args.policy.read_text(encoding="utf-8"),tokens)
    result={"schema":SCHEMA,"policy_sha256":sha256_file(args.policy),"accepted":not problems,"problems":problems}
    text=json.dumps(result,indent=2,sort_keys=True)+"\n"
    if args.out: args.out.write_text(text,encoding="utf-8")
    print(text,end="")
    raise SystemExit(0 if not problems else 2)

if __name__=="__main__": main()
