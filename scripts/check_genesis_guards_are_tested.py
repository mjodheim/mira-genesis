#!/usr/bin/env python3
"""Delete each of the Genesis runtime's guards in turn and check that a test notices.

A test suite written by the same agent that wrote the code proves less than it appears to. The
cheapest honest question to ask of it is not "does it pass" but "would it still pass if the thing it
covers were gone". This script asks that mechanically.

For every `raise <Error>(...)` in the `genesis/` package — each one a refusal the runtime claims to
make — it removes that single statement, runs the Genesis test suites, and records whether anything
failed. A guard whose removal keeps the suite green is a **surviving mutant**: the runtime refuses
something no test ever asks it to refuse, so the refusal rests on the author's word.

Surviving mutants are not automatically defects. Some guards are genuinely unreachable defensive
checks, and a few are covered only by a stricter guard upstream. The script does not judge; it
produces the list the reviewer would otherwise have to assemble by hand, and it makes the claim in
`docs/audits/GENESIS_RUNTIME_HOSTILE_REVIEW_BRIEF.md` checkable rather than asserted.

The source files are restored in a `finally` block, and the script refuses to start if the working
tree already has uncommitted changes to `genesis/`, so an interrupted run cannot leave a mutation
behind unnoticed.

    python scripts/check_genesis_guards_are_tested.py            # every guard
    python scripts/check_genesis_guards_are_tested.py --module state
"""
from __future__ import annotations

import argparse
import ast
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "genesis"
SUITES = [
    "tests/test_genesis_trust_root.py",
    "tests/test_genesis_loop.py",
    "tests/test_genesis_migration.py",
    "tests/test_genesis_demonstration.py",
]
#: Modules holding the runtime's refusals. `development_bodies` is fixtures, not runtime.
MODULES = ("trust_root", "state", "journal", "sandbox", "loop", "migration", "diagnosis")


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


def suite_passes() -> bool:
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", *SUITES, "-q", "-x", "--no-header", "-p", "no:cacheprovider"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def dirty_sources() -> list[str]:
    completed = subprocess.run(
        ["git", "status", "--porcelain", "--", "genesis"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return [line for line in completed.stdout.splitlines() if line.strip()]


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
    print("\n%d guards removed one at a time: %d killed by a test, %d survived" % (total, killed, len(survivors)))
    if survivors:
        print("\nGuards no test exercises — each is a refusal resting on the author's word:")
        for name, line, label in survivors:
            print("  genesis/%s.py:%d  %s" % (name, line, label))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
