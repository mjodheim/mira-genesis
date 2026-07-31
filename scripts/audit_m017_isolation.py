"""M017 — audit d'isolation et de trace entière. Porte de gel n°6.

Deux propriétés doivent tenir avant tout gel de protocole, et aucune n'est garantie
par les tests :

1. **Isolation.** Le code de l'organisme ne doit rien connaître du laboratoire.
   M012, M013 et M013b ont toutes trois été classées `INCONCLUSIVE — CONTAMINATED`
   pour des variantes de ce défaut. Un import suffit : `m017_engine` importait
   `BehavioralOracle` depuis `m017_lab`, ce qui rendait atteignables depuis
   l'organisme le générateur d'épisodes, les motifs de l'environnement et
   `_audit_target`.

2. **Trace entière.** Aucune grandeur qui entre dans une décision ne doit être un
   flottant. Le `consolidation_record_sha256` de M014b différait d'un environnement à
   l'autre parce qu'il incorporait des scores flottants : le résultat scientifique
   était reproductible, sa preuve ne l'était pas.

Exécution :

    python scripts/audit_m017_isolation.py
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

# Source de l'organisme : ce qu'il a le droit de savoir.
ORGANISM_MODULES = (
    ROOT / "metamorphosis" / "m017_engine.py",
    ROOT / "metamorphosis" / "m017_language.py",
    ROOT / "metamorphosis" / "structural.py",
)

# Le laboratoire : ce qu'il ne doit jamais atteindre.
LABORATORY_MODULE = "m017_lab"

FORBIDDEN_NAMES = (
    "_audit_target",
    "_audit_truth_table",
    "_audit_snapshot",
    "make_environment",
    "generate_episodes",
    "make_out_of_language_target",
    "is_irreducible_motif",
    "_recovers_motif",
    "motifs",
    "Episode",
)


def check_isolation() -> list[str]:
    problems: list[str] = []
    for path in ORGANISM_MODULES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        name = path.relative_to(ROOT)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if LABORATORY_MODULE in node.module:
                    problems.append(f"{name} importe le laboratoire : {node.module}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if LABORATORY_MODULE in alias.name:
                        problems.append(f"{name} importe le laboratoire : {alias.name}")
            elif isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_NAMES:
                problems.append(f"{name} atteint un nom réservé au laboratoire : {node.attr}")
            elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
                problems.append(f"{name} atteint un nom réservé au laboratoire : {node.id}")
    return problems


def check_integer_only_decisions() -> list[str]:
    """Aucune division flottante, aucune conversion en flottant, aucune moyenne.

    La division entière `//` est autorisée ; c'est `/` qui produit un flottant en
    Python 3, et c'est exactement le défaut de traçabilité de M014b.
    """
    problems: list[str] = []
    for path in ORGANISM_MODULES:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        name = path.relative_to(ROOT)
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                problems.append(f"{name}:{node.lineno} division flottante `/`")
            elif isinstance(node, ast.Constant) and isinstance(node.value, float):
                problems.append(f"{name}:{node.lineno} littéral flottant {node.value}")
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == "float":
                    problems.append(f"{name}:{node.lineno} conversion `float(`")
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in {"mean", "fmean", "stdev", "variance"}:
                    problems.append(f"{name}:{node.lineno} statistique flottante `{node.func.attr}`")
    return problems


def check_no_canonical_claim() -> list[str]:
    """Aucun script de développement ne doit pouvoir se faire passer pour canonique."""
    problems: list[str] = []
    for path in sorted((ROOT / "scripts").glob("run_m017_*.py")):
        source = path.read_text(encoding="utf-8")
        name = path.relative_to(ROOT)
        if '"development_only": True' not in source:
            problems.append(f"{name} n'affirme pas son marqueur `development_only`")
        if "--canonical" in source:
            problems.append(f"{name} expose un drapeau canonique")
    return problems


CHECKS = (
    ("Isolation de l'organisme vis-à-vis du laboratoire", check_isolation),
    ("Décisions entièrement entières", check_integer_only_decisions),
    ("Aucune revendication canonique en développement", check_no_canonical_claim),
)


def main() -> int:
    failed = False
    for label, check in CHECKS:
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
    sys.exit(main())
