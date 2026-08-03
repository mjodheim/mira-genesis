from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
METAMORPHOSIS = ROOT / "metamorphosis"
CALIBRATION = ROOT / "scripts" / "run_m033_control_calibration.py"
PROTOCOL = ROOT / "experiments" / "M033" / "PROTOCOL_DRAFT.md"


def _imports_m033(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names if ".m033" in alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.startswith("m033") or ".m033" in module:
                found.append(module)
    return found


def _calibration_defaults_are_control_only() -> bool:
    tree = ast.parse(CALIBRATION.read_text(encoding="utf-8"), filename=str(CALIBRATION))
    seed_default_found = False
    lower_bound_guard_found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "add_argument" and node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and first.value == "--seed-start":
                    for keyword in node.keywords:
                        if (
                            keyword.arg == "default"
                            and isinstance(keyword.value, ast.Constant)
                            and keyword.value.value == 1024
                        ):
                            seed_default_found = True
        if isinstance(node, ast.Compare):
            if (
                isinstance(node.left, ast.Name)
                and node.left.id == "seed_start"
                and len(node.ops) == 1
                and isinstance(node.ops[0], ast.Lt)
                and len(node.comparators) == 1
                and isinstance(node.comparators[0], ast.Constant)
                and node.comparators[0].value == 1024
            ):
                lower_bound_guard_found = True
    return seed_default_found and lower_bound_guard_found


def main() -> None:
    failures: list[str] = []

    for path in sorted(METAMORPHOSIS.glob("*.py")):
        if path.name.startswith("m033_"):
            continue
        imports = _imports_m033(path)
        if imports:
            failures.append(
                f"pre-M033 module imports post-migration code: {path.name}: {imports}"
            )
        raw = path.read_text(encoding="utf-8")
        for forbidden in (
            "generate_control_task",
            "ControlTaskFamily",
            "held_out_words",
        ):
            if forbidden in raw:
                failures.append(
                    f"pre-M033 module reaches post-migration task surface: "
                    f"{path.name}: {forbidden}"
                )

    generator = METAMORPHOSIS / "m033_post_migration_plasticity.py"
    generator_raw = generator.read_text(encoding="utf-8")
    if "if seed < 1024" not in generator_raw:
        failures.append("control generator lacks the seed >=1024 fail-closed guard")
    if "M033 control tasks require a seed of at least 1024" not in generator_raw:
        failures.append("control generator lacks an explicit primary-seed rejection")

    if not _calibration_defaults_are_control_only():
        failures.append("calibration runner does not default and fail closed at seed 1024")

    protocol = " ".join(PROTOCOL.read_text(encoding="utf-8").split())
    required_protocol_fragments = (
        "Seeds `0–63` are reserved",
        "Seeds `1024+` are reserved",
        "called only after all lineages have crossed the substrate boundary",
        "does **not** set a numerical advantage threshold",
    )
    for fragment in required_protocol_fragments:
        if fragment not in protocol:
            failures.append(f"protocol separation rule missing: {fragment}")

    if failures:
        for failure in failures:
            print(f"FAIL — {failure}")
        raise SystemExit(1)

    print("OK   — No pre-M033 module imports or reaches the M033 task surface")
    print("OK   — Control generator and calibration reject primary seeds")
    print("OK   — Protocol preserves post-migration reveal and threshold boundaries")


if __name__ == "__main__":
    main()
