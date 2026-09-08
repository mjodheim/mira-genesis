#!/usr/bin/env python3
"""Delete each Genesis runtime guard in turn and ask whether the complete Genesis suite notices.

A mutation score is only meaningful when two preconditions hold:

* the unmutated baseline suite is green; otherwise every mutant appears "killed" by a failure that
  was already present;
* every current Genesis test participates; otherwise new hostile tests can exist while the checker
  silently measures an older subset.

The checker therefore discovers every ``tests/test_genesis_*.py`` file, verifies the baseline first,
then replaces one ``raise <Error>(...)`` at a time with ``pass``. It also prints enough platform
context to interpret redundant enforcement. In particular, ``RLIMIT_NPROC`` may independently block
process creation for an unprivileged process but be ineffective for uid 0, so deletion of the Python
audit-hook subprocess guard can survive on one platform and be killed on another without any source
change.

    python scripts/check_genesis_guards_are_tested.py
    python scripts/check_genesis_guards_are_tested.py --module state
"""
from __future__ import annotations

import argparse
import ast
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "genesis"
SUITES = sorted(
    str(path.relative_to(ROOT)) for path in (ROOT / "tests").glob("test_genesis_*.py")
)

#: Modules holding the runtime's refusals. `development_bodies` is fixtures, not runtime.
MODULES = (
    "trust_root",
    "state",
    "journal",
    "sandbox",
    "loop",
    "migration",
    "probe",
    "artifacts",
    "capabilities",
)


def guards(path: Path) -> list[tuple[int, int, str]]:
    """Every `raise SomeError(...)` in the file, as (first line, last line, message fragment)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise) or node.exc is None:
            continue
        call = node.exc if isinstance(node.exc, ast.Call) else None
        name = getattr(call.func, "id", "") if call else getattr(node.exc, "id", "")
        if not name.endswith("Error"):
            continue
        label = ""
        if call and call.args and isinstance(call.args[0], ast.Constant):
            label = str(call.args[0].value)
        elif call and call.args and isinstance(call.args[0], ast.BinOp):
            left = call.args[0].left
            label = str(left.value) if isinstance(left, ast.Constant) else ""
        found.append((node.lineno, node.end_lineno or node.lineno, label))
    return sorted(found)


def without_guard(source: str, first: int, last: int) -> str:
    """Replace one raise statement with `pass`, keeping the file's line numbering intact."""
    lines = source.splitlines(keepends=True)
    original = lines[first - 1]
    indent = original[: len(original) - len(original.lstrip())]
    lines[first - 1] = indent + "pass\n"
    for index in range(first, last):
        lines[index] = indent + "pass\n"
    return "".join(lines)


def run_suite() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            *SUITES,
            "-q",
            "-x",
            "--no-header",
            "-p",
            "no:cacheprovider",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def suite_passes() -> bool:
    return run_suite().returncode == 0


def dirty_sources() -> list[str]:
    completed = subprocess.run(
        ["git", "status", "--porcelain", "--", "genesis"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return [line for line in completed.stdout.splitlines() if line.strip()]


def rlimit_nproc_control() -> str:
    """Measure whether RLIMIT_NPROC alone blocks one subprocess in a disposable interpreter."""
    code = r'''
try:
    import resource, subprocess
except ImportError:
    print("unsupported")
    raise SystemExit(0)
try:
    resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))
except Exception as error:
    print("setrlimit-failed:%s" % type(error).__name__)
    raise SystemExit(0)
try:
    subprocess.run(["/bin/true"], check=True)
except Exception as error:
    print("blocked:%s" % type(error).__name__)
else:
    print("allowed")
'''
    completed = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True
    )
    return (completed.stdout or completed.stderr or "unknown").strip().replace("\n", " | ")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", action="append", help="restrict to these genesis modules")
    arguments = parser.parse_args()

    dirty = dirty_sources()
    if dirty:
        print("refusing to run: genesis/ has uncommitted changes, which this script would restore")
        for line in dirty:
            print("  %s" % line)
        return 2

    print("mutation context:")
    print("  python: %s" % sys.version.split()[0])
    print("  platform: %s" % sys.platform)
    print("  uid: %s" % (os.geteuid() if hasattr(os, "geteuid") else "unavailable"))
    print("  RLIMIT_NPROC control: %s" % rlimit_nproc_control())
    print("  suites: %d" % len(SUITES))
    for suite in SUITES:
        print("    %s" % suite)

    baseline = run_suite()
    if baseline.returncode != 0:
        print("\nrefusing to score mutants: the unmutated Genesis baseline is already red")
        tail = (baseline.stdout + "\n" + baseline.stderr).strip().splitlines()[-30:]
        for line in tail:
            print("  %s" % line)
        return 2

    names = arguments.module or list(MODULES)
    survivors: list[tuple[str, int, str]] = []
    killed = 0

    for name in names:
        path = PACKAGE / ("%s.py" % name)
        source = path.read_text(encoding="utf-8")
        try:
            for first, last, label in guards(path):
                path.write_text(without_guard(source, first, last), encoding="utf-8")
                if suite_passes():
                    survivors.append((name, first, label))
                    print("SURVIVED  %s:%d  %s" % (name, first, label[:70]))
                else:
                    killed += 1
                    print("killed    %s:%d  %s" % (name, first, label[:70]))
        finally:
            path.write_text(source, encoding="utf-8")

    total = killed + len(survivors)
    print(
        "\n%d guards removed one at a time: %d killed by a test, %d survived"
        % (total, killed, len(survivors))
    )
    if survivors:
        print("\nGuards no current Genesis test distinguishes under this environment:")
        for name, line, label in survivors:
            print("  genesis/%s.py:%d  %s" % (name, line, label))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
