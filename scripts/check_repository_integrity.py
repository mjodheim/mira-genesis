"""Structural repository guardrails.

Three real defects motivated this script. All were invisible to sealed evaluation
workflows because those workflows executed only selected test files:

1. `metamorphosis/core.py` imported `torch`, which made the documented `pytest -q`
   command fail on every machine without PyTorch;
2. roughly 2,400 lines formed a completely disconnected import subgraph without any
   signal exposing it;
3. `pyproject.toml` declared `torch` and `scipy`, although neither was imported.

Each check is independent and may be run on its own.

    python scripts/check_repository_integrity.py            # all checks
    python scripts/check_repository_integrity.py --orphans  # one check
"""

from __future__ import annotations

import argparse
import ast
from collections import deque
from pathlib import Path
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ("metamorphosis", "mira_core")

# Modules under `scripts/` that are legitimate entry points. They do not need to be
# imported by another module to be considered live.
ENTRY_POINT_PREFIXES = ("run_", "audit_", "train_", "check_")

# Tools invoked from the command line and never imported by source code. Declaring them
# without importing them is legitimate.
COMMAND_LINE_TOOLS = {"pytest"}

# A third-party import name does not always match its distribution name.
DISTRIBUTION_ALIASES = {
    "yaml": "pyyaml",
    "sklearn": "scikit-learn",
    "cv2": "opencv-python",
    "PIL": "pillow",
}


def source_files() -> list[Path]:
    directories = tuple(ROOT / package for package in PACKAGES) + (ROOT / "scripts", ROOT / "tests")
    return sorted(
        path
        for directory in directories
        if directory.is_dir()
        for path in directory.rglob("*.py")
    )


def module_name(path: Path) -> str:
    relative = path.relative_to(ROOT)
    if relative.parts[0] in PACKAGES:
        parts = relative.with_suffix("").parts
        if parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts)
    return relative.stem


def parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def imported_names(path: Path) -> set[str]:
    """Return imported module names, resolving relative imports."""
    found: set[str] = set()
    relative = path.relative_to(ROOT)
    package = module_name(path).rsplit(".", 1)[0] if relative.parts[0] in PACKAGES else ""
    for node in ast.walk(parse(path)):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level and package:
                found.add(f"{package}.{node.module}" if node.module else package)
            elif node.module:
                found.add(node.module)
    return found


def check_imports() -> list[str]:
    """Every module must import cleanly with declared dependencies installed."""
    import importlib

    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "scripts"))
    failures: list[str] = []
    for path in source_files():
        if path.parts[-2] == "tests":
            continue  # pytest owns collection and fixture setup for tests
        name = module_name(path)
        try:
            importlib.import_module(name)
        except Exception as error:  # noqa: BLE001 - preserve the complete diagnostic
            failures.append(f"{path.relative_to(ROOT)}: {type(error).__name__}: {error}")
    return failures


def check_orphans() -> list[str]:
    """No package module may be unreachable from a legitimate entry point."""
    files = {module_name(path): path for path in source_files()}
    roots = [
        name
        for name, path in files.items()
        if path.parts[-2] == "tests" or name.startswith(ENTRY_POINT_PREFIXES)
    ]

    reachable: set[str] = set()
    queue = deque(roots)
    while queue:
        name = queue.popleft()
        if name in reachable or name not in files:
            continue
        reachable.add(name)
        for target in imported_names(files[name]):
            # Handles `metamorphosis.m012b_dfa` and `m014b_eval_support`, as well as
            # `metamorphosis.m012b_dfa.DFA` produced by `from x.y import z`.
            for candidate in (target, target.rsplit(".", 1)[0]):
                if candidate in files:
                    queue.append(candidate)

    return [
        f"{files[name].relative_to(ROOT)} is not imported by any entry point"
        for name in sorted(set(files) - reachable)
    ]


def check_dependencies() -> list[str]:
    """Declared dependencies and real third-party imports must match."""
    manifest = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = manifest.get("project", {})

    def distributions(requirements: list[str]) -> set[str]:
        cleaned = set()
        for requirement in requirements:
            name = requirement.split(";")[0]
            for separator in ("[", ">", "<", "=", "!", "~", " "):
                name = name.split(separator)[0]
            if name:
                cleaned.add(name.strip().lower())
        return cleaned

    declared = distributions(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        declared |= distributions(extra)

    # ``scripts`` is an intentional repository-local namespace even though it is not an
    # installable distribution package.  Tests and cross-checkers may use an explicit
    # ``scripts.foo`` import when they need the package-qualified identity; pyproject's pytest
    # path also supports the historical bare ``foo`` entry-point imports.  Neither spelling is a
    # third-party dependency.
    local = set(PACKAGES) | {"scripts"} | {module_name(path) for path in source_files()}
    used: set[str] = set()
    for path in source_files():
        for name in imported_names(path):
            top = name.split(".")[0]
            if top in local or top in sys.stdlib_module_names or top == "__future__":
                continue
            used.add(DISTRIBUTION_ALIASES.get(top, top).lower())

    problems = [
        f"`{name}` is imported but absent from pyproject.toml"
        for name in sorted(used - declared)
    ]
    problems += [
        f"`{name}` is declared in pyproject.toml but never imported"
        for name in sorted(declared - used - COMMAND_LINE_TOOLS)
    ]
    return problems


CHECKS = {
    "imports": ("Every module imports cleanly", check_imports),
    "orphans": ("No orphan module", check_orphans),
    "dependencies": ("Declared dependencies match imports", check_dependencies),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for flag, (help_text, _) in CHECKS.items():
        parser.add_argument(f"--{flag}", action="store_true", help=help_text)
    arguments = parser.parse_args()

    selected = [flag for flag in CHECKS if getattr(arguments, flag)] or list(CHECKS)

    failed = False
    for flag in selected:
        label, check = CHECKS[flag]
        problems = check()
        if problems:
            failed = True
            print(f"FAIL — {label}")
            for problem in problems:
                print(f"  - {problem}")
        else:
            print(f"OK   — {label}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
