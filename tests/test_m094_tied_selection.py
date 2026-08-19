"""Amendment A4: a measure that cannot separate two classes does not pick one by name.

`Diagnosis.unmet` is a total order whose last terms are the capability, the class name and
the encoded detail. When two classes tie on demand, the class that gets repaired — and so the
adopted mechanism's digest, and so the qualification draw — was decided by alphabetical order
on an identifier. In this repository the tie is live: `Goal` and `Observation` both measure
demand 4 from four sites each, and `Goal` won because G sorts before O.

A measured secondary term would not have fixed it. The two are equal on demand *and* on site
count, so any such rule falls back to the name again. The measure is saying it cannot separate
them; the faithful response is to repair both.

The first test is the defect as a fixture: the ordering is still name-decided, and must stay
that way, because the fix is not to change the tie-break but to stop needing one.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from metamorphosis import m094_lineage as lineage  # noqa: E402
from metamorphosis.m094_diagnosis import diagnose  # noqa: E402

COMPONENT = "pkg/values.py"

#: Two classes with identical demand, whose names sort in an obvious order.
TWO_TIED = '''from dataclasses import dataclass


@dataclass(frozen=True)
class Alpha:
    alpha_id: str
    label: str


@dataclass(frozen=True)
class Omega:
    omega_id: str
    label: str
'''

#: Two callers per class, so both measure the same demand from the same number of sites.
CALLERS = '''from pkg.values import Alpha, Omega


def one(a: Alpha) -> dict:
    return {"alpha_id": a.alpha_id, "label": a.label}


def two(a: Alpha) -> dict:
    return {"alpha_id": a.alpha_id, "label": a.label}


def three(o: Omega) -> dict:
    return {"omega_id": o.omega_id, "label": o.label}


def four(o: Omega) -> dict:
    return {"omega_id": o.omega_id, "label": o.label}
'''


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / COMPONENT).write_text(TWO_TIED, encoding="utf-8")
    (tmp_path / "callers.py").write_text(CALLERS, encoding="utf-8")
    return tmp_path


# ── the tie is real, and the ordering is still name-decided ───────────


def test_the_two_classes_tie_on_every_available_measurement(repo: Path) -> None:
    result = diagnose(repo, (COMPONENT,))
    unmet = {item.target: item for item in result.unmet}
    assert {"Alpha", "Omega"} <= set(unmet)
    assert unmet["Alpha"].demand == unmet["Omega"].demand
    assert len(unmet["Alpha"].demand_sites) == len(unmet["Omega"].demand_sites)


def test_the_ordering_is_still_decided_by_the_class_name(repo: Path) -> None:
    """Unchanged on purpose. A4 removes the need for a tie-break, not the ordering.

    If this ever stops holding, the sort key has been altered — which moves the adopted
    mechanism and the qualification draw, and is a different amendment from this one.
    """

    result = diagnose(repo, (COMPONENT,))
    top = [item.target for item in result.unmet if item.demand == result.unmet[0].demand]
    assert top == sorted(top), "the head of the order is the alphabetically first class"


# ── so the selection is the whole tied set ────────────────────────────


def test_the_selection_is_every_class_tied_at_the_top(repo: Path) -> None:
    result = diagnose(repo, (COMPONENT,))
    assert [item.target for item in result.tied_selection()] == ["Alpha", "Omega"]


def test_the_tied_selection_stays_inside_the_selected_component(tmp_path: Path) -> None:
    """The component choice is a measurement and is left alone; only the class choice moved."""

    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / COMPONENT).write_text(TWO_TIED, encoding="utf-8")
    (tmp_path / "pkg" / "other.py").write_text(
        "from dataclasses import dataclass\n\n\n"
        "@dataclass(frozen=True)\nclass Beta:\n    beta_id: str\n    label: str\n",
        encoding="utf-8",
    )
    (tmp_path / "callers.py").write_text(
        CALLERS + "\n\nfrom pkg.other import Beta\n\n\n"
        'def five(b: Beta) -> dict:\n    return {"beta_id": b.beta_id, "label": b.label}\n',
        encoding="utf-8",
    )
    result = diagnose(tmp_path, (COMPONENT, "pkg/other.py"))
    for item in result.tied_selection():
        assert item.component_path == result.selected


def test_a_single_unmet_class_yields_a_selection_of_one(tmp_path: Path) -> None:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / COMPONENT).write_text(
        "from dataclasses import dataclass\n\n\n"
        "@dataclass(frozen=True)\nclass Only:\n    only_id: str\n    label: str\n",
        encoding="utf-8",
    )
    (tmp_path / "callers.py").write_text(
        "from pkg.values import Only\n\n\n"
        'def one(o: Only) -> dict:\n    return {"only_id": o.only_id, "label": o.label}\n\n\n'
        'def two(o: Only) -> dict:\n    return {"only_id": o.only_id, "label": o.label}\n',
        encoding="utf-8",
    )
    result = diagnose(tmp_path, (COMPONENT,))
    assert [item.target for item in result.tied_selection()] == ["Only"]


def test_an_empty_diagnosis_selects_nothing(tmp_path: Path) -> None:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / COMPONENT).write_text("VALUE = 1\n", encoding="utf-8")
    assert diagnose(tmp_path, (COMPONENT,)).tied_selection() == ()


# ── and every one of them is repaired ─────────────────────────────────


def test_both_tied_classes_are_repaired(repo: Path) -> None:
    development = lineage.develop(repo, (COMPONENT,))
    assert [item.target for item in development.targets] == ["Alpha", "Omega"]
    assert len(development.operations) == 2
    assert development.modified_source is not None
    assert development.search["tied_classes_repaired"] == 2


def test_both_repairs_land_in_the_same_source(repo: Path) -> None:
    import ast

    development = lineage.develop(repo, (COMPONENT,))
    tree = ast.parse(development.modified_source)
    for name in ("Alpha", "Omega"):
        node = next(
            n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == name
        )
        added = [n for n in node.body if isinstance(n, ast.FunctionDef)]
        assert added, f"{name} was not repaired"


def test_the_mechanism_digest_covers_every_repair(repo: Path) -> None:
    """A lineage that repaired two things must not be confusable with one that repaired one."""

    development = lineage.develop(repo, (COMPONENT,))
    assert development.mechanism_digest
    single = lineage._digest({
        "repairs": [development.operations[0].digest],
        "classes": ["Alpha"],
    })
    assert development.mechanism_digest != single
    assert development.mechanism_digest != development.operations[0].digest


def test_an_arm_closes_only_when_every_tied_class_closes(repo: Path) -> None:
    record = lineage.run_arm("endogenous_diagnosis_and_synthesis", repo, (COMPONENT,))
    assert record["tied_classes"] == 2
    assert record["tied_classes_closed"] == 2
    assert record["closed"] is True
    assert [item["class"] for item in record["per_target"]] == ["Alpha", "Omega"]


def test_the_unadopted_arm_leaves_every_tied_class_unrepaired(repo: Path) -> None:
    original = (repo / COMPONENT).read_text(encoding="utf-8")
    record = lineage.run_arm("diagnosis_without_adoption", repo, (COMPONENT,))
    assert record["live_still_lacks_the_capability"] is True
    assert (repo / COMPONENT).read_text(encoding="utf-8") == original


# ── the case generator must cope with a class that constrains itself ──


def test_a_cross_field_invariant_does_not_make_a_class_unrepairable(tmp_path: Path) -> None:
    """`Observation` refuses `success` without `terminal`, and independently drawn values
    sometimes violate that. Treating one unlucky draw as "this class cannot be built" made a
    class unrepairable and blocked A4 outright.
    """

    from metamorphosis import m094_execution as execution

    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / COMPONENT).write_text(
        "from dataclasses import dataclass\n\n\n"
        "@dataclass(frozen=True)\n"
        "class Constrained:\n"
        "    token: str\n"
        "    success: bool = False\n"
        "    terminal: bool = False\n\n"
        "    def __post_init__(self):\n"
        "        if self.success and not self.terminal:\n"
        '            raise ValueError("a successful item must be terminal")\n',
        encoding="utf-8",
    )
    # The requirement names the constrained fields, exactly as `Observation`'s does, so the
    # generator has to supply them and the invariant is actually exercised. Fields carrying a
    # default that the requirement does not mention are left alone and never reach it.
    requirement = (
        ("token", "token", None),
        ("success", "success", None),
        ("terminal", "terminal", None),
    )
    cases = execution.constructible_cases(
        tmp_path, COMPONENT, "Constrained", requirement, count=6,
    )
    assert len(cases) == 6, "one unlucky draw must not disqualify the class"
    assert all({"success", "terminal"} <= set(case) for case in cases)
    assert not any(case["success"] and not case["terminal"] for case in cases)
    # And the draws are not all the trivially-safe corner: the generator kept variety.
    assert len({(case["success"], case["terminal"]) for case in cases}) > 1
