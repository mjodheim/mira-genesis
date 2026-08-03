from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
METAMORPHOSIS = ROOT / "metamorphosis"
CONTROL_CALIBRATION = ROOT / "scripts" / "run_m033_control_calibration.py"
STRUCTURAL_CALIBRATION = ROOT / "scripts" / "run_m033_structural_calibration.py"
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


def _module_int_constant_equals(path: Path, name: str, expected: int) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
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


def _runner_defaults_are_control_only(
    path: Path,
    *,
    expected_default: int,
    expected_guard: int,
    expected_guard_name: str | None = None,
    expected_guard_module: str | None = None,
) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    seed_default_found = False
    lower_bound_guard_found = False
    named_guard_imported = expected_guard_name is None

    if expected_guard_name is not None and expected_guard_module is not None:
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module == expected_guard_module:
                if any(alias.name == expected_guard_name for alias in node.names):
                    named_guard_imported = True
                    break

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "add_argument" and node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and first.value == "--seed-start":
                    for keyword in node.keywords:
                        if (
                            keyword.arg == "default"
                            and isinstance(keyword.value, ast.Constant)
                            and keyword.value.value == expected_default
                        ):
                            seed_default_found = True
        if isinstance(node, ast.Compare):
            if (
                isinstance(node.left, ast.Name)
                and node.left.id == "seed_start"
                and len(node.ops) == 1
                and isinstance(node.ops[0], ast.Lt)
                and len(node.comparators) == 1
            ):
                comparator = node.comparators[0]
                literal_guard = (
                    isinstance(comparator, ast.Constant)
                    and comparator.value == expected_guard
                )
                named_guard = (
                    named_guard_imported
                    and expected_guard_name is not None
                    and isinstance(comparator, ast.Name)
                    and comparator.id == expected_guard_name
                )
                if literal_guard or named_guard:
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
    if not _module_int_constant_equals(
        structural_generator,
        "STRUCTURAL_CONTROL_SEED_START",
        2048,
    ):
        failures.append("structural control seed boundary is not fixed at 2048")
    if "if seed < STRUCTURAL_CONTROL_SEED_START" not in structural_raw:
        failures.append("structural generator lacks the seed >=2048 fail-closed guard")
    if "M033 structural controls require a seed of at least 2048" not in structural_raw:
        failures.append("structural generator lacks an explicit primary-seed rejection")

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
        expected_guard_name="STRUCTURAL_CONTROL_SEED_START",
        expected_guard_module="metamorphosis.m033_structural_tasks",
    ):
        failures.append("structural calibration does not default and fail closed at 2048")

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
    print("OK   — Both control generators and runners reject primary seeds")
    print("OK   — Protocol preserves post-migration reveal and threshold boundaries")


if __name__ == "__main__":
    main()
