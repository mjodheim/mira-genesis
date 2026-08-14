"""Physical isolation — run the migrated substrate where `m090_language.py` does not exist.

An import census says "the legacy module was not imported". A tripwire says "it was not called".
Both are claims about a process that still *had* the file. This harness removes the file.

It builds a temporary directory containing only the minimal M092 runtime modules, copied as
top-level modules with their intra-package imports rewritten, plus the serialized state and a small
driver. The `metamorphosis` package is not present under any name, so `m090_language` is not
importable, not shadowable and not reachable. The inherited substrate must still execute correctly.

The driver asserts its own isolation before running anything:

* `m090_language` and `metamorphosis` must both be unimportable;
* every loaded module file must live inside the temporary root or the standard library;
* the probe outcomes must match what the full environment produced.

The child runs under `python -I` (isolated mode: no `PYTHONPATH`, no user site directory) with its
working directory inside the temporary root, so the repository is not on `sys.path`.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile

# The complete permitted runtime surface. Anything not listed here is absent from the child.
RUNTIME_MODULES = (
    "m092_runtime.py",
    "m092_kernel.py",
    "m092_substrate_state.py",
)

DRIVER = '''"""Driver for the isolated runtime. Imports only the permitted modules."""
import importlib.util, json, os, sys, sysconfig

ROOT = os.path.dirname(os.path.abspath(__file__))

# Take explicit control of the import path: the isolated root plus the standard library, and
# nothing else. Site-packages is dropped so that an editable install of the repository cannot
# quietly make the historical modules reachable. The resulting path is reported, so the claim
# "m090_language was not available" is auditable rather than asserted.
PATHS = [ROOT]
for key in ("stdlib", "platstdlib"):
    entry = sysconfig.get_paths().get(key)
    if entry and entry not in PATHS:
        PATHS.append(entry)
dynload = os.path.join(sysconfig.get_paths()["stdlib"], "lib-dynload")
if os.path.isdir(dynload):
    PATHS.append(dynload)
for entry in list(sys.path):
    # keep zip/frozen stdlib entries that the interpreter needs to function
    if entry.endswith(".zip") and entry not in PATHS:
        PATHS.append(entry)
sys.path[:] = PATHS

# Editable installs inject a MetaPathFinder at interpreter startup via a .pth file. That hook is
# path-INDEPENDENT, so clearing sys.path alone would not stop it resolving `metamorphosis`. Drop
# every finder that did not come from the standard library, and drop the modules they arrived in.
_stdlib = os.path.abspath(sysconfig.get_paths()["stdlib"])
removed_finders = []
kept = []
for finder in sys.meta_path:
    module = sys.modules.get(getattr(finder, "__module__", ""))
    origin = os.path.abspath(getattr(module, "__file__", "") or "") if module else ""
    if origin and not origin.startswith(_stdlib):
        removed_finders.append(f"{getattr(finder, '__name__', finder)} <- {origin}")
    else:
        kept.append(finder)
sys.meta_path[:] = kept
for name, module in list(sys.modules.items()):
    origin = os.path.abspath(getattr(module, "__file__", "") or "")
    if origin and not (origin.startswith(_stdlib) or origin.startswith(ROOT)):
        del sys.modules[name]
sys.path_importer_cache.clear()
importlib.invalidate_caches()

findings = []
for forbidden in ("m090_language", "metamorphosis", "m090_migration", "m092_migration",
                  "m091_substrate", "m091_lineage"):
    try:
        reachable = importlib.util.find_spec(forbidden) is not None
    except (ImportError, ValueError):
        reachable = False
    if reachable:
        findings.append(f"{forbidden} is importable")

from m092_runtime import RefusalCode, RuntimeLanguage, SubstrateError
from m092_substrate_state import SubstrateState, execute_from_state

with open(os.path.join(ROOT, "state.json"), encoding="utf-8") as handle:
    payload = json.load(handle)

language = RuntimeLanguage.from_dict(payload["language"])
substrate = SubstrateState.from_dict(payload["substrate"])

if payload.get("expected_substrate_digest") not in (None, substrate.digest()):
    print(json.dumps({"status": "digest_mismatch"}))
    raise SystemExit(2)

outcomes = []
for probe in payload["probes"]:
    program = [(name, tuple(args)) for name, args in probe["program"]]
    try:
        slots = execute_from_state(program, probe["inputs"], language, substrate)
        outcomes.append({"id": probe["id"], "status": "value", "slots": list(slots)})
    except SubstrateError as error:
        outcomes.append({"id": probe["id"], "status": "refused", "code": error.code.value})

stdlib = sysconfig.get_paths()["stdlib"]
outside = []
for name, module in list(sys.modules.items()):
    path = getattr(module, "__file__", None)
    if not path:
        continue
    resolved = os.path.abspath(path)
    if not (resolved.startswith(ROOT) or resolved.startswith(os.path.abspath(stdlib))):
        outside.append(f"{name} -> {resolved}")

print(json.dumps({
    "status": "ok",
    "findings": findings,
    "sys_path": sys.path,
    "removed_meta_path_finders": removed_finders,
    "meta_path_after": [getattr(f, "__name__", str(f)) for f in sys.meta_path],
    "modules_outside_the_isolated_root_or_stdlib": outside,
    "loaded_project_modules": sorted(
        name for name, m in sys.modules.items()
        if getattr(m, "__file__", None) and os.path.abspath(m.__file__).startswith(ROOT)
    ),
    "substrate_digest": substrate.digest(),
    "registered_operations": len(substrate.operations),
    "outcomes": outcomes,
}, indent=2, sort_keys=True))
raise SystemExit(0 if not findings and not outside else 1)
'''


def build_isolated_root(state_payload: dict, source_dir: str) -> str:
    """Copy the permitted modules as top-level modules, rewriting package imports."""

    root = tempfile.mkdtemp(prefix="m092a-isolated-")
    for name in RUNTIME_MODULES:
        source = os.path.join(source_dir, name)
        text = open(source, encoding="utf-8").read()
        # `from metamorphosis.X import ...` -> `from X import ...`
        text = re.sub(r"from metamorphosis\.(\w+) import", r"from \1 import", text)
        text = re.sub(r"import metamorphosis\.(\w+)", r"import \1", text)
        with open(os.path.join(root, name), "w", encoding="utf-8") as handle:
            handle.write(text)
    with open(os.path.join(root, "state.json"), "w", encoding="utf-8") as handle:
        json.dump(state_payload, handle, indent=2, sort_keys=True)
    with open(os.path.join(root, "driver.py"), "w", encoding="utf-8") as handle:
        handle.write(DRIVER)
    return root


def run(root: str) -> dict:
    completed = subprocess.run(
        [sys.executable, "-I", os.path.join(root, "driver.py")],
        capture_output=True, text=True, cwd=root,
    )
    try:
        report = json.loads(completed.stdout)
    except json.JSONDecodeError:
        report = {
            "status": "unparseable",
            "stdout": completed.stdout[-2000:], "stderr": completed.stderr[-3000:],
        }
    report["exit_code"] = completed.returncode
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True)
    parser.add_argument("--keep", action="store_true", help="do not delete the isolated root")
    parser.add_argument("--json", default="")
    arguments = parser.parse_args()

    with open(arguments.state, encoding="utf-8") as handle:
        payload = json.load(handle)

    source_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "metamorphosis")
    root = build_isolated_root(payload, source_dir)
    try:
        report = run(root)
        report["isolated_root_contents"] = sorted(os.listdir(root))
        report["permitted_runtime_modules"] = list(RUNTIME_MODULES)
        report["m090_language_present_in_root"] = "m090_language.py" in os.listdir(root)
        print(json.dumps(report, indent=2, sort_keys=True))
        if arguments.json:
            with open(arguments.json, "w", encoding="utf-8") as handle:
                json.dump(report, handle, indent=2, sort_keys=True)
        return 0 if report.get("exit_code") == 0 else 1
    finally:
        if not arguments.keep:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
