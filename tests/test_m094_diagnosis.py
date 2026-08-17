"""The structural diagnosis must measure the component, not name it.

`experiments/M094/DESIGN_AUDIT.md` records four defects in the substring
diagnostic this module replaces. The checks below are written against those
defects directly: each one fails if the corresponding defect returns.

Fixtures are synthetic repositories built in `tmp_path`, so the properties hold
independently of what `mira_core` happens to contain on any given day.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from metamorphosis.m094_diagnosis import (
    CAPABILITY_SHAPES,
    diagnose,
    measure_component,
)

MODULE_SOURCE = Path(
    "metamorphosis/m094_diagnosis.py"
).resolve()


# ── Fixtures ─────────────────────────────────────────────────────────


def _write(root: Path, relative: str, source: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8", newline="\n")
    return path


LEDGER_WITHOUT_QUERY = '''
class Ledger:
    def __init__(self):
        self._events = []

    @property
    def events(self):
        return tuple(self._events)
'''

LEDGER_WITH_QUERY = '''
class Ledger:
    def __init__(self):
        self._events = []

    @property
    def events(self):
        return tuple(self._events)

    def events_by_kind(self, kind):
        return tuple(e for e in self._events if e.kind == kind)
'''

CALLER_FILTERS_BY_HAND = '''
from pkg.ledger import Ledger

def summarise(ledger):
    return [e for e in ledger.events if e.kind == "start"]
'''


def _build_repo(tmp_path: Path, ledger_source: str, callers: int = 1) -> Path:
    _write(tmp_path, "pkg/__init__.py", "")
    _write(tmp_path, "pkg/ledger.py", ledger_source)
    for index in range(callers):
        _write(tmp_path, f"consumers/use_{index}.py", CALLER_FILTERS_BY_HAND)
    return tmp_path


# ── Defect 2 — the detector must invert when the capability is supplied ──


def test_supplying_the_capability_flips_the_verdict(tmp_path: Path) -> None:
    """This is the property the substring detector violated."""

    without = _build_repo(tmp_path / "without", LEDGER_WITHOUT_QUERY)
    with_it = _build_repo(tmp_path / "with", LEDGER_WITH_QUERY)

    unmet_before = measure_component(without, "pkg/ledger.py")
    unmet_after = measure_component(with_it, "pkg/ledger.py")

    assert [i.is_unmet for i in unmet_before] == [True]
    assert [i.is_unmet for i in unmet_after] == [False]

    # Demand is identical; only supply changed.
    assert unmet_before[0].demand == unmet_after[0].demand
    assert unmet_before[0].supplied is False
    assert unmet_after[0].supplied is True


def test_implementing_the_capability_never_raises_demand(tmp_path: Path) -> None:
    """The old indicator scored 2 with the method present and 1 without it."""

    without = _build_repo(tmp_path / "without", LEDGER_WITHOUT_QUERY)
    with_it = _build_repo(tmp_path / "with", LEDGER_WITH_QUERY)

    before = measure_component(without, "pkg/ledger.py")[0].demand
    after = measure_component(with_it, "pkg/ledger.py")[0].demand
    assert after <= before


def test_the_component_s_own_source_contributes_no_demand(tmp_path: Path) -> None:
    """Demand is counted outside the component; supply inside it."""

    repo = _build_repo(tmp_path, LEDGER_WITH_QUERY, callers=0)
    measurements = measure_component(repo, "pkg/ledger.py")
    # The query method itself contains the filter, but it is not a demand site.
    assert all(m.demand == 0 for m in measurements)


# ── Defect 1 and 3 — measurement, and reachability ───────────────────


def test_any_component_can_be_selected_given_demand(tmp_path: Path) -> None:
    """No component is privileged; the winner follows the evidence."""

    _write(tmp_path, "pkg/__init__.py", "")
    _write(tmp_path, "pkg/alpha.py", LEDGER_WITHOUT_QUERY.replace("Ledger", "Alpha"))
    _write(tmp_path, "pkg/beta.py", LEDGER_WITHOUT_QUERY.replace("Ledger", "Beta"))

    # One caller for alpha.
    _write(tmp_path, "consumers/a.py", '''
from pkg.alpha import Alpha

def f(x):
    return [e for e in x.events if e.kind == "k"]
''')
    first = diagnose(tmp_path, ["pkg/alpha.py", "pkg/beta.py"])
    assert first.selected == "pkg/alpha.py"

    # Two callers for beta now outweigh alpha's one.
    for index in range(2):
        _write(tmp_path, f"consumers/b{index}.py", f'''
from pkg.beta import Beta

def f{index}(x):
    return [e for e in x.events if e.kind == "k"]
''')
    second = diagnose(tmp_path, ["pkg/alpha.py", "pkg/beta.py"])
    assert second.selected == "pkg/beta.py"


def test_a_component_with_no_demand_is_never_selected(tmp_path: Path) -> None:
    repo = _build_repo(tmp_path, LEDGER_WITHOUT_QUERY, callers=0)
    result = diagnose(repo, ["pkg/ledger.py"])
    assert result.selected is None
    assert result.unmet == ()


def test_demand_requires_reaching_the_component(tmp_path: Path) -> None:
    """A file that filters an identically-named collection on an unrelated class
    contributes nothing, because it cannot reach this component."""

    repo = _build_repo(tmp_path, LEDGER_WITHOUT_QUERY, callers=0)
    _write(tmp_path, "unrelated/other.py", '''
from unrelated.journal import Journal

def f(journal):
    return [e for e in journal.events if e.kind == "k"]
''')
    _write(tmp_path, "unrelated/journal.py", "class Journal:\n    pass\n")

    measurements = measure_component(repo, "pkg/ledger.py")
    assert all(m.demand == 0 for m in measurements)


def test_a_package_reexport_still_reaches_the_component(tmp_path: Path) -> None:
    """`from pkg import Ledger` reaches `pkg/ledger.py`."""

    _write(tmp_path, "pkg/__init__.py", "from pkg.ledger import Ledger\n")
    _write(tmp_path, "pkg/ledger.py", LEDGER_WITHOUT_QUERY)
    _write(tmp_path, "consumers/via_package.py", '''
from pkg import Ledger

def f(x):
    return [e for e in x.events if e.kind == "k"]
''')
    measurements = measure_component(tmp_path, "pkg/ledger.py")
    assert [m.demand for m in measurements] == [1]
    assert measurements[0].is_unmet is True


# ── Defect 1 — no component-specific constants in the measure ────────


def test_the_measure_names_no_component_path_or_class() -> None:
    """The module must not key on any identity from the repository under study.

    Docstrings are excluded. M090's amendment A1 settled this exact point: a
    scanner over raw source text flagged prose *describing* a defect and produced
    a false negative verdict, and the correction was to read the AST rather than
    the text. Prose that names `MemoryLedger` while explaining why the measure
    must not depend on it is not a dependency on it; a string constant consulted
    at run time would be.
    """

    source = MODULE_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)

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
    forbidden = {"mira_core", "MemoryLedger", "memory.py", "event.kind", "events_by_kind"}
    leaked = {lit for lit in literals if any(bad in lit for bad in forbidden)}
    assert leaked == set(), f"the measure names the component it should measure: {leaked}"


def test_capability_shapes_carry_no_collection_or_attribute_names() -> None:
    """The shape is generic; the names come from the source being measured."""

    for shape in CAPABILITY_SHAPES:
        assert "kind" not in shape.name
        assert "event" not in shape.name
