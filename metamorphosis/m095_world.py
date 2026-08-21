"""The authored world M095 runs in.

The world is **authored and disclosed**, as M091's worlds were and as M094's eligible component
set is. What is authored: two value objects, one nested inside the other, and call sites that
destructure both by hand. What is *not* authored: which of them the diagnosis selects first,
what either repair contains, or whether the second repair is reachable — all three are measured,
and the third is the milestone.

Why a world rather than `mira_core`. M094 ran on the real repository and that is not
re-litigated. The nested-rendering demand M095 needs does not exist there: `AgentResult` holds
an `Observation`, but its call sites reach *through* it into `.state` rather than rendering it,
so the demand would have had to be planted. Planting the demand the diagnosis then discovers is
the defect the M094 design audit spent twelve findings removing, and a disclosed authored world
is the honest alternative.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

WORLD_SCHEMA = "m095-world-v1"
COMPONENT = "pkg/values.py"

#: Two value objects. `Reading` is nested inside `Sample`, and neither renders itself.
VALUES = '''"""Two value objects, neither of which renders itself."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Reading:
    reading_id: str
    unit: str


@dataclass(frozen=True)
class Sample:
    sample_id: str
    reading: Reading
'''

#: One caller per file. Demand is counted per reaching source, so three files destructuring
#: `Reading` outrank two rendering `Sample`, and the diagnosis selects `Reading` first without
#: being told to. That ordering is the only thing the world arranges, and it arranges it by
#: giving `Reading` more callers rather than by ranking anything.
READING_CALLER = '''from pkg.values import Reading


def emit_{index}(reading: Reading) -> dict:
    return {{"reading_id": reading.reading_id, "unit": reading.unit}}
'''

#: Each of these writes the whole nested `Reading` out by hand. That is the demand only a
#: renderer *on `Reading`* can meet — and at S0 there is none.
SAMPLE_CALLER = '''from pkg.values import Sample


def report_{index}(sample: Sample) -> dict:
    return {{
        "sample_id": sample.sample_id,
        "reading": {{
            "reading_id": sample.reading.reading_id,
            "unit": sample.reading.unit,
        }},
    }}
'''

READING_CALLERS = 3
SAMPLE_CALLERS = 2


def build(
    root: Path,
    *,
    reading_callers: int | None = None,
    sample_callers: int | None = None,
) -> Path:
    """Write S0 into *root* and return it. Nothing here renders anything.

    The caller counts are parameters rather than constants read from the module because the
    relation between them is the one thing the world arranges, and an arrangement that cannot
    be varied cannot be shown to matter. Varying it is how the domain of the milestone's claim
    was measured; see `experiments/M095/DESIGN_AUDIT.md`, defect 5.

    They default to `None` and resolve to the module constants in the body rather than in
    the signature, because a default evaluated at definition time would freeze the constants
    at import and make the module-level values unpatchable — which is exactly the silent
    inertness this parameter exists to remove.
    """

    reading_callers = READING_CALLERS if reading_callers is None else reading_callers
    sample_callers = SAMPLE_CALLERS if sample_callers is None else sample_callers

    (root / "pkg").mkdir(parents=True, exist_ok=True)
    (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / COMPONENT).write_text(VALUES, encoding="utf-8")

    for index in range(reading_callers):
        (root / f"reading_caller_{index}.py").write_text(
            READING_CALLER.format(index=index), encoding="utf-8"
        )
    for index in range(sample_callers):
        (root / f"sample_caller_{index}.py").write_text(
            SAMPLE_CALLER.format(index=index), encoding="utf-8"
        )
    return root


@dataclass(frozen=True)
class WorldFacts:
    """What the world is, stated so a reader can check it rather than trust it.

    The call-site counts carry no defaults on purpose. They used to default to the module
    constants, so `WorldFacts()` reported three inner and two outer call sites whatever had
    actually been written to disk — a record that described the author's intention rather than
    the experiment's world. Build these with `of(root)`, which counts.
    """

    inner_call_sites: int
    outer_call_sites: int
    inner_class: str = ""
    outer_class: str = ""
    nested_field: str = ""
    nothing_renders_itself_at_s0: bool = True

    @classmethod
    def of(cls, root: Path) -> WorldFacts:
        """Read what is on disk, so the record cannot disagree with the world."""

        tree = ast.parse((root / COMPONENT).read_text(encoding="utf-8"))
        classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
        # The outer class is the one with a field annotated as another class here; the
        # inner class is what that annotation names. Read rather than defaulted, so a
        # world built differently cannot be recorded as this one.
        names = {node.name for node in classes}
        outer, inner, nested_field = "", "", ""
        for node in classes:
            for item in node.body:
                if not (isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)):
                    continue
                annotation = ast.unparse(item.annotation).strip()
                if annotation in names:
                    outer, inner, nested_field = node.name, annotation, item.target.id
                    break
            if outer:
                break

        # A substring search for "def " would find one in a docstring or a comment. Ask
        # the tree whether any class defines a public method.
        renders = any(
            isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            and not item.name.startswith("_")
            for node in classes for item in node.body
        )
        return cls(
            inner_call_sites=len(list(root.glob("reading_caller_*.py"))),
            outer_call_sites=len(list(root.glob("sample_caller_*.py"))),
            inner_class=inner,
            outer_class=outer,
            nested_field=nested_field,
            nothing_renders_itself_at_s0=not renders,
        )

    @property
    def ordering_regime(self) -> str:
        """Which way the demand falls, named so the claim's domain can be stated."""

        if self.inner_call_sites > self.outer_call_sites:
            return "inner>outer"
        return "inner==outer" if self.inner_call_sites == self.outer_call_sites else "inner<outer"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": WORLD_SCHEMA,
            "authored": True,
            "inner_class": self.inner_class,
            "outer_class": self.outer_class,
            "nested_field": self.nested_field,
            "inner_call_sites": self.inner_call_sites,
            "outer_call_sites": self.outer_call_sites,
            "ordering_regime": self.ordering_regime,
            "nothing_renders_itself_at_s0": self.nothing_renders_itself_at_s0,
            "why_not_mira_core": (
                "the nested-rendering demand does not exist there: AgentResult holds an "
                "Observation but its call sites reach through it into .state rather than "
                "rendering it, so the demand would have had to be planted"
            ),
        }
