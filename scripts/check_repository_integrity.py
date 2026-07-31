"""Garde-fous structurels du dépôt.

Trois défauts réels ont motivé ce script, tous invisibles pour les workflows
d'évaluation scellée parce que ceux-ci n'exécutaient que des fichiers de test ciblés :

1. `metamorphosis/core.py` importait `torch`, ce qui faisait échouer la collecte de
   `pytest -q` — la commande documentée — sur toute machine sans PyTorch ;
2. environ 2 400 lignes formaient un sous-graphe d'imports entièrement déconnecté,
   sans qu'aucun signal ne le révèle ;
3. `pyproject.toml` déclarait `torch` et `scipy`, jamais importés.

Chaque vérification est indépendante et peut être lancée seule.

    python scripts/check_repository_integrity.py            # tout
    python scripts/check_repository_integrity.py --orphans  # une seule
"""

from __future__ import annotations

import argparse
import ast
from collections import deque
from pathlib import Path
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "metamorphosis"

# Modules de `scripts/` qui sont des points d'entrée légitimes : ils n'ont pas à
# être importés par quoi que ce soit pour être vivants.
ENTRY_POINT_PREFIXES = ("run_", "audit_", "train_", "check_")

# Outils invoqués en ligne de commande, jamais importés depuis le code source.
# Les déclarer sans les importer est légitime.
COMMAND_LINE_TOOLS = {"pytest"}

# Un import de module tiers ne porte pas toujours le nom de sa distribution.
DISTRIBUTION_ALIASES = {
    "yaml": "pyyaml",
    "sklearn": "scikit-learn",
    "cv2": "opencv-python",
    "PIL": "pillow",
}


def source_files() -> list[Path]:
    directories = (ROOT / PACKAGE, ROOT / "scripts", ROOT / "tests")
    return sorted(
        path
        for directory in directories
        if directory.is_dir()
        for path in directory.rglob("*.py")
    )


def module_name(path: Path) -> str:
    relative = path.relative_to(ROOT)
    if relative.parts[0] == PACKAGE:
        return ".".join(relative.with_suffix("").parts)
    return relative.stem


def parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def imported_names(path: Path) -> set[str]:
    """Noms de modules importés par un fichier, résolus pour les imports relatifs."""
    found: set[str] = set()
    package = module_name(path).rsplit(".", 1)[0] if path.parts[-2] == PACKAGE else ""
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
    """Chaque module doit s'importer sans erreur, dépendances déclarées installées."""
    import importlib

    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "scripts"))
    failures: list[str] = []
    for path in source_files():
        if path.parts[-2] == "tests":
            continue  # pytest s'en charge et fournit ses propres fixtures
        name = module_name(path)
        try:
            importlib.import_module(name)
        except Exception as error:  # noqa: BLE001 - on veut le diagnostic complet
            failures.append(f"{path.relative_to(ROOT)} : {type(error).__name__} : {error}")
    return failures


def check_orphans() -> list[str]:
    """Aucun module du paquet ne doit être injoignable depuis un point d'entrée."""
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
            # `metamorphosis.m012b_dfa` ou `m014b_eval_support`, mais aussi
            # `metamorphosis.m012b_dfa.DFA` pour `from x.y import z`.
            for candidate in (target, target.rsplit(".", 1)[0]):
                if candidate in files:
                    queue.append(candidate)

    return [
        f"{files[name].relative_to(ROOT)} n'est importé par aucun point d'entrée"
        for name in sorted(set(files) - reachable)
    ]


def check_dependencies() -> list[str]:
    """Les dépendances déclarées et les imports tiers réels doivent coïncider."""
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

    local = {PACKAGE} | {module_name(path) for path in source_files()}
    used: set[str] = set()
    for path in source_files():
        for name in imported_names(path):
            top = name.split(".")[0]
            if top in local or top in sys.stdlib_module_names or top == "__future__":
                continue
            used.add(DISTRIBUTION_ALIASES.get(top, top).lower())

    problems = [
        f"`{name}` est importé mais absent de pyproject.toml"
        for name in sorted(used - declared)
    ]
    problems += [
        f"`{name}` est déclaré dans pyproject.toml mais jamais importé"
        for name in sorted(declared - used - COMMAND_LINE_TOOLS)
    ]
    return problems


CHECKS = {
    "imports": ("Importabilité de chaque module", check_imports),
    "orphans": ("Absence de module orphelin", check_orphans),
    "dependencies": ("Cohérence des dépendances déclarées", check_dependencies),
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
            print(f"ECHEC — {label}")
            for problem in problems:
                print(f"  - {problem}")
        else:
            print(f"OK    — {label}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
