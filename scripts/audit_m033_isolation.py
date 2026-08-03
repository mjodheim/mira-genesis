from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
METAMORPHOSIS = ROOT / "metamorphosis"
CONTROL_CALIBRATION = ROOT / "scripts" / "run_m033_control_calibration.py"
STRUCTURAL_CALIBRATION = ROOT / "scripts" / "run_m033_structural_calibration.py"
COMBINED_CALIBRATION = ROOT / "scripts" / "run_m033_combined_calibration.py"
PROTOCOL = ROOT / "experiments" / "M033" / "PROTOCOL_DRAFT.md"
STRUCTURAL_MODULE = "metamorphosis.m033_structural_tasks"


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _imports_m033(path: Path) -> list[str]:
    tree = _parse(path)
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names if ".m033" in alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.startswith("m033") or ".m033" in module:
                found.append(module)
    return found


def _module_int_constant_equals(path: Path, name: str, expected: int) -> bool:
    tree = _parse(path)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if (
                any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
                and isinstance(node.value, ast.Constant)
                and node.value.value == expected
            ):
                return True
        elif isinstance(node, ast.AnnAssign):
            if (
                isinstance(node.target, ast.Name)
                and node.target.id == name
                and isinstance(node.value, ast.Constant)
                and node.value.value == expected
            ):
                return True
    return False


def _imports_name(path: Path, module: str, name: str) -> bool:
    for node in _parse(path).body:
        if isinstance(node, ast.ImportFrom) and node.module == module:
            if any(alias.name == name for alias in node.names):
                return True
    return False


def _matches_value(
    node: ast.expr,
    *,
    expected_literal: int,
    expected_name: str | None,
    named_value_imported: bool,
) -> bool:
    if isinstance(node, ast.Constant) and node.value == expected_literal:
        return True
    return (
        named_value_imported
        and expected_name is not None
        and isinstance(node, ast.Name)
        and node.id == expected_name
    )


def _runner_defaults_are_control_only(
    path: Path,
    *,
    expected_default: int,
    expected_guard: int,
    expected_name: str | None = None,
    expected_module: str | None = None,
) -> bool:
    tree = _parse(path)
    named_value_imported = (
        expected_name is None
        or (
            expected_module is not None
            and _imports_name(path, expected_module, expected_name)
        )
    )
    seed_default_found = False
    lower_bound_guard_found = False

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "add_argument" and node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and first.value == "--seed-start":
                    for keyword in node.keywords:
                        if keyword.arg == "default" and _matches_value(
                            keyword.value,
                            expected_literal=expected_default,
                            expected_name=expected_name,
                            named_value_imported=named_value_imported,
                        ):
                            seed_default_found = True
        if isinstance(node, ast.Compare):
            if (
                isinstance(node.left, ast.Name)
                and node.left.id == "seed_start"
                and len(node.ops) == 1
                and isinstance(node.ops[0], ast.Lt)
                and len(node.comparators) == 1
                and _matches_value(
                    node.comparators[0],
                    expected_literal=expected_guard,
                    expected_name=expected_name,
                    named_value_imported=named_value_imported,
                )
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
            "generate_structural_control_task",
            "generate_combined_control_task",
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

    structural_generator = METAMORPHOSIS / "m033_structural_tasks.py"
    structural_raw = structural_generator.read_text(encoding="utf-8")
    for name, expected in (
        ("STRUCTURAL_CONTROL_SEED_START", 2048),
        ("COMBINED_CONTROL_SEED_START", 3072),
    ):
        if not _module_int_constant_equals(structural_generator, name, expected):
            failures.append(f"{name} is not fixed at {expected}")

    structural_guard = (
        "if seed < STRUCTURAL_CONTROL_SEED_START or "
        "seed >= COMBINED_CONTROL_SEED_START"
    )
    if structural_guard not in structural_raw:
        failures.append("structural generator does not fail closed outside 2048–3071")
    if "M033 structural controls require a seed from 2048 through 3071" not in structural_raw:
        failures.append("structural generator lacks an explicit closed-block rejection")
    if "if seed < COMBINED_CONTROL_SEED_START" not in structural_raw:
        failures.append("combined generator lacks the seed >=3072 fail-closed guard")
    if "M033 combined controls require a seed of at least 3072" not in structural_raw:
        failures.append("combined generator lacks an explicit earlier-block rejection")

    if not _runner_defaults_are_control_only(
        CONTROL_CALIBRATION,
        expected_default=1024,
        expected_guard=1024,
    ):
        failures.append("control calibration does not default and fail closed at 1024")
    if not _runner_defaults_are_control_only(
        STRUCTURAL_CALIBRATION,
        expected_default=2048,
        expected_guard=2048,
        expected_name="STRUCTURAL_CONTROL_SEED_START",
        expected_module=STRUCTURAL_MODULE,
    ):
        failures.append("structural calibration does not default and fail closed at 2048")
    if not _runner_defaults_are_control_only(
        COMBINED_CALIBRATION,
        expected_default=3072,
        expected_guard=3072,
        expected_name="COMBINED_CONTROL_SEED_START",
        expected_module=STRUCTURAL_MODULE,
    ):
        failures.append("combined calibration does not default and fail closed at 3072")

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
    print("OK   — Fixed, structural and combined control blocks are disjoint")
    print("OK   — All control generators and runners reject primary seeds")
    print("OK   — Protocol preserves post-migration reveal and threshold boundaries")


if __name__ == "__main__":
    main()
