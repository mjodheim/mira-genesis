"""The synthesis must derive the repair from the component, not carry it.

`experiments/M094/DESIGN_AUDIT.md` Defect 4 records the inherited transformation
set: one template holding the finished method body plus a branch on a component
name. The module under test removes the branch and derives every identifier from
the AST, which is real progress and is checked here.

It does **not** remove the template body itself, and that is checked here too —
as a failure, not an omission. P6 asks for a repair assembled from composable
operations, and an f-string of a method is not one. These tests pin the honest
position rather than the flattering one.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from metamorphosis.m094_diagnosis import diagnose, measure_component
from metamorphosis.m094_synthesis import SynthesisOperation, suggest_operations

MODULE = Path("metamorphosis/m094_synthesis.py").resolve()


def _write(root: Path, relative: str, source: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8", newline="\n")
    return path


DECISION = '''
from dataclasses import dataclass

@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    missing: tuple = ()
'''

CALLER = '''
from pkg.decision import Decision

def record(step, d):
    return {"step": step, "allowed": d.allowed, "reason": d.reason, "missing": list(d.missing)}
'''


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    _write(tmp_path, "pkg/__init__.py", "")
    _write(tmp_path, "pkg/decision.py", DECISION)
    _write(tmp_path, "consumers/rec.py", CALLER)
    return tmp_path


def _only_unmet(repo: Path):
    unmet = [i for i in measure_component(repo, "pkg/decision.py") if i.is_unmet]
    assert len(unmet) == 1
    return unmet[0]


# ── What the synthesis does correctly ────────────────────────────────


def test_it_generates_an_operation_for_a_diagnosed_insufficiency(repo: Path) -> None:
    top = _only_unmet(repo)
    ops = suggest_operations(
        repo,
        component_path=top.component_path,
        class_name=top.class_name,
        capability=top.capability,
        target=top.target,
        detail=top.detail,
    )
    assert len(ops) == 1
    assert isinstance(ops[0], SynthesisOperation)
    assert ops[0].class_name == "Decision"


def test_the_generated_repair_is_valid_python_and_applies(repo: Path) -> None:
    top = _only_unmet(repo)
    op = suggest_operations(
        repo,
        component_path=top.component_path,
        class_name=top.class_name,
        capability=top.capability,
        target=top.target,
        detail=top.detail,
    )[0]

    before = (repo / "pkg/decision.py").read_text(encoding="utf-8")
    after = op.apply(before)

    ast.parse(after)
    assert len(after) > len(before)

    methods = {
        node.name
        for parent in ast.walk(ast.parse(after))
        if isinstance(parent, ast.ClassDef) and parent.name == "Decision"
        for node in parent.body
        if isinstance(node, ast.FunctionDef)
    }
    assert "to_dict" in methods


def test_applying_the_repair_satisfies_the_diagnosis(repo: Path) -> None:
    """The loop must close: the repair must make the insufficiency met."""

    top = _only_unmet(repo)
    op = suggest_operations(
        repo,
        component_path=top.component_path,
        class_name=top.class_name,
        capability=top.capability,
        target=top.target,
        detail=top.detail,
    )[0]

    path = repo / "pkg/decision.py"
    path.write_text(op.apply(path.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")

    assert [i.is_unmet for i in measure_component(repo, "pkg/decision.py")] == [False]


def test_field_names_come_from_the_ast_not_from_the_module(tmp_path: Path) -> None:
    """A different class yields a different repair, with no shared identifiers."""

    _write(tmp_path, "pkg/__init__.py", "")
    _write(tmp_path, "pkg/other.py", '''
from dataclasses import dataclass

@dataclass(frozen=True)
class Telemetry:
    latency_ms: int
    region: str
    dropped: int = 0
''')
    _write(tmp_path, "consumers/use.py", '''
from pkg.other import Telemetry

def emit(t):
    return {"latency_ms": t.latency_ms, "region": t.region, "dropped": t.dropped}
''')
    top = [i for i in measure_component(tmp_path, "pkg/other.py") if i.is_unmet][0]
    op = suggest_operations(
        tmp_path,
        component_path=top.component_path,
        class_name=top.class_name,
        capability=top.capability,
        target=top.target,
        detail=top.detail,
    )[0]

    produced = op.apply((tmp_path / "pkg/other.py").read_text(encoding="utf-8"))
    assert "latency_ms" in produced and "region" in produced
    assert "allowed" not in produced and "reason" not in produced


def test_the_module_names_no_component_identity() -> None:
    """Defect 4's `if class_name == "MemoryLedger"` branch must stay gone."""

    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc is not None:
                docstrings.add(doc)

    literals = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value not in docstrings
    }
    forbidden = {"mira_core", "MemoryLedger", "SafetyDecision", "memory.py", "safety.py"}
    leaked = {lit for lit in literals if any(bad in lit for bad in forbidden)}
    assert leaked == set(), f"synthesis names a component: {leaked}"


# ── What it does not do, recorded as a failure rather than omitted ───


def test_the_repair_shape_is_still_an_authored_template() -> None:
    """P6 is not satisfied, and this test exists so that stays visible.

    Identifiers are derived from the AST, but the method itself is written out
    as an f-string and filled in. That is Defect 4 with generic names: a repair
    assembled from composable operations does not appear anywhere as a block of
    source text.

    When synthesis becomes genuinely compositional this test must be inverted,
    deliberately, rather than quietly deleted.
    """

    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc is not None:
                docstrings.add(doc)

    bodies: set[str] = set()
    for node in ast.walk(tree):
        pieces: list[str] = []
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            pieces = [node.value]
        elif isinstance(node, ast.JoinedStr):
            pieces = [
                v.value for v in node.values
                if isinstance(v, ast.Constant) and isinstance(v.value, str)
            ]
        for piece in pieces:
            if piece in docstrings:
                continue
            stripped = piece.strip()
            if stripped.startswith("def ") and "(" in stripped:
                bodies.add(stripped.splitlines()[0].strip())

    assert bodies, (
        "the synthesis no longer emits a literal method body — if that is "
        "intentional, invert this test and re-examine P6"
    )
