"""Amendment A2: a candidate is judged by running it.

The frozen acceptance rule read a candidate's syntax tree and asked whether it bound the
keys the requirement named. Every other key it carried was unconstrained, wrapper included,
so a method binding the required keys and wrapping an unrelated integer in ``list()`` passed
and raised when executed. `ContainerLimits` — eight fields, a two-key requirement, thousands
of accepted candidates and a content-address tie-break — is where the qualification found it.

The first test below is that defect, written as a fixture. It must stay failing under the
structural predicate and passing under execution, because the day both agree is the day the
amendment stopped doing anything.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from metamorphosis import m094_execution as execution  # noqa: E402
from metamorphosis.m094_diagnosis import RenderAsMapping, _encode_rendering  # noqa: E402
from metamorphosis.m094_execution import (  # noqa: E402,F401
    MAX_CONFIRMATIONS,
    STRING_SHAPES,
    agrees,
    constructible_cases,
    probe_variants,
)

COMPONENT = "pkg/values.py"

#: Eight fields, like `ContainerLimits`, so a two-key requirement leaves six unconstrained.
WIDE_SOURCE = '''from dataclasses import dataclass


@dataclass(frozen=True)
class Wide:
    memory_bytes: int = 1024
    pids_limit: int = 256
    max_steps: int = 64
    cpus: float = 1.0
    label: str = "x"
    timeout_seconds: float = 120.0
    tmpfs_bytes: int = 512
    max_output_bytes: int = 65536
'''


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / COMPONENT).write_text(WIDE_SOURCE, encoding="utf-8")
    return tmp_path


REQUIREMENT = (("memory_bytes", "memory_bytes", None), ("pids_limit", "pids_limit", None))


def _with_method(body: str) -> str:
    return WIDE_SOURCE + "\n" + "\n".join("    " + line for line in body.splitlines()) + "\n"


#: Binds both required keys correctly, and wraps an unrelated int in list().
RAISING_CANDIDATE = _with_method(
    "def as_mapping(self):\n"
    "    return {'memory_bytes': self.memory_bytes, 'pids_limit': self.pids_limit,"
    " 'max_steps': list(self.max_steps)}"
)

#: Binds both required keys correctly and nothing that raises.
WORKING_CANDIDATE = _with_method(
    "def as_mapping(self):\n"
    "    return {'memory_bytes': self.memory_bytes, 'pids_limit': self.pids_limit}"
)


# ── the defect A2 exists to catch ─────────────────────────────────────


def test_the_structural_predicate_accepts_a_method_that_raises() -> None:
    """The frozen acceptance rule, shown failing. If this ever fails, A2 is unnecessary."""

    node = next(
        n for n in ast.walk(ast.parse(RAISING_CANDIDATE))
        if isinstance(n, ast.ClassDef) and n.name == "Wide"
    )
    assert RenderAsMapping().is_supplied_by(node, "Wide", _encode_rendering(REQUIREMENT))


def test_executing_that_same_method_raises(repo: Path) -> None:
    cases = execution.constructible_cases(repo, COMPONENT, "Wide", REQUIREMENT)
    assert cases, "the fixture must be constructible or this proves nothing"
    records = execution.probe_variants(
        repo, COMPONENT, [("raising", RAISING_CANDIDATE)], "Wide", REQUIREMENT, cases,
    )
    assert not execution.agrees(records[0])
    assert records[0]["satisfying_methods"] == []


def test_execution_accepts_the_candidate_that_works(repo: Path) -> None:
    cases = execution.constructible_cases(repo, COMPONENT, "Wide", REQUIREMENT)
    records = execution.probe_variants(
        repo, COMPONENT, [("working", WORKING_CANDIDATE)], "Wide", REQUIREMENT, cases,
    )
    assert execution.agrees(records[0])
    assert "as_mapping" in records[0]["satisfying_methods"]


def test_both_variants_are_told_apart_in_one_process(repo: Path) -> None:
    """Many variants share a subprocess, and must not contaminate each other."""

    cases = execution.constructible_cases(repo, COMPONENT, "Wide", REQUIREMENT)
    records = execution.probe_variants(
        repo, COMPONENT,
        [("raising", RAISING_CANDIDATE), ("working", WORKING_CANDIDATE),
         ("raising_again", RAISING_CANDIDATE)],
        "Wide", REQUIREMENT, cases,
    )
    by_id = {record["id"]: record for record in records}
    assert not execution.agrees(by_id["raising"])
    assert execution.agrees(by_id["working"])
    assert not execution.agrees(by_id["raising_again"]), "state leaked between variants"


# ── the method name is never a way in ─────────────────────────────────


def test_a_method_with_the_expected_name_and_wrong_values_is_refused(repo: Path) -> None:
    cases = execution.constructible_cases(repo, COMPONENT, "Wide", REQUIREMENT)
    liar = _with_method(
        "def as_mapping(self):\n"
        "    return {'memory_bytes': 0, 'pids_limit': 0}"
    )
    records = execution.probe_variants(
        repo, COMPONENT, [("liar", liar)], "Wide", REQUIREMENT, cases,
    )
    assert not execution.agrees(records[0])


def test_a_method_with_an_unexpected_name_and_right_values_is_accepted(repo: Path) -> None:
    """Nothing consults the name, so an oddly-named method that works must pass."""

    cases = execution.constructible_cases(repo, COMPONENT, "Wide", REQUIREMENT)
    odd = _with_method(
        "def zzz_render(self):\n"
        "    return {'memory_bytes': self.memory_bytes, 'pids_limit': self.pids_limit}"
    )
    records = execution.probe_variants(
        repo, COMPONENT, [("odd", odd)], "Wide", REQUIREMENT, cases,
    )
    assert execution.agrees(records[0])
    assert records[0]["satisfying_methods"] == ["zzz_render"]


# ── cases the class actually accepts ──────────────────────────────────


def test_cases_are_verified_by_construction(repo: Path) -> None:
    import importlib

    cases = execution.constructible_cases(repo, COMPONENT, "Wide", REQUIREMENT, count=4)
    assert len(cases) == 4
    # Imported dynamically: a literal `from pkg...` would make the fixture package look like
    # an undeclared third-party dependency to check_repository_integrity.
    sys.path.insert(0, str(repo))
    try:
        module = importlib.import_module("pkg.values")
        for case in cases:
            module.Wide(**case)
    finally:
        sys.path.remove(str(repo))
        for name in ("pkg.values", "pkg"):
            sys.modules.pop(name, None)


def test_a_class_that_rejects_every_shape_yields_no_case(tmp_path: Path) -> None:
    """No case is better than a case that measures nothing.

    The pool's superseded hidden cases raised on construction and were scored as failures.
    Returning nothing forces the caller to say "this measures nothing" instead.
    """

    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / COMPONENT).write_text(
        "from dataclasses import dataclass\n\n\n"
        "@dataclass(frozen=True)\n"
        "class Impossible:\n"
        "    token: str\n\n"
        "    def __post_init__(self):\n"
        '        raise ValueError("nothing is acceptable")\n',
        encoding="utf-8",
    )
    cases = execution.constructible_cases(
        tmp_path, COMPONENT, "Impossible", (("token", "token", None),),
    )
    assert cases == ()


def test_a_constraint_is_met_by_walking_the_shape_ladder(tmp_path: Path) -> None:
    """A class demanding an absolute path is satisfied without anything naming that class."""

    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / COMPONENT).write_text(
        "from dataclasses import dataclass\n\n\n"
        "@dataclass(frozen=True)\n"
        "class Pathy:\n"
        "    location: str\n\n"
        "    def __post_init__(self):\n"
        "        if not self.location.startswith('/'):\n"
        '            raise ValueError("location must be absolute")\n',
        encoding="utf-8",
    )
    cases = execution.constructible_cases(
        tmp_path, COMPONENT, "Pathy", (("location", "location", None),), count=3,
    )
    assert len(cases) == 3
    assert all(case["location"].startswith("/") for case in cases)


# ── a broken variant is refused, not fatal ────────────────────────────


def test_unparsable_source_is_refused_without_raising(repo: Path) -> None:
    cases = execution.constructible_cases(repo, COMPONENT, "Wide", REQUIREMENT)
    records = execution.probe_variants(
        repo, COMPONENT, [("broken", "class Wide:\n    def oops(")], "Wide",
        REQUIREMENT, cases,
    )
    assert not execution.agrees(records[0])
    assert records[0]["imported"] is False
