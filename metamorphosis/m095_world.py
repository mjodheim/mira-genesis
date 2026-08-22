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

        # Local imports keep the authored-world module independent at import time while letting
        # its record use the same measurement as the experiment.  Filenames and public-method
        # counts are descriptions of an intention, not evidence of demand or supply.
        from metamorphosis.m094_diagnosis import (
            CAPABILITY_SHAPES,
            RenderAsMapping,
            _encode_rendering,
            decode_rendering,
            diagnose,
        )
        from metamorphosis.m095_reach import (
            RenderNestedValueObject,
            supplying_method,
        )

        tree = ast.parse((root / COMPONENT).read_text(encoding="utf-8"))
        classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
        # The outer class is the one with a field annotated as another class here; the
        # inner class is what that annotation names. Read rather than defaulted, so a
        # world built differently cannot be recorded as this one.
        names = {node.name for node in classes}
        relationships: list[tuple[str, str, str]] = []
        for node in classes:
            for item in node.body:
                if not (isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)):
                    continue
                annotation = ast.unparse(item.annotation).strip()
                if annotation in names:
                    relationships.append((node.name, annotation, item.target.id))

        outer, inner, nested_field = relationships[0] if relationships else ("", "", "")

        plain = RenderAsMapping()
        nested = RenderNestedValueObject()
        diagnosis = diagnose(root, (COMPONENT,), tuple(CAPABILITY_SHAPES) + (nested,))
        by_name = {node.name: node for node in classes}

        # When more than one nested relation exists, describe the same ranked unmet subject as
        # the chain's control.  Fall back to the first syntactic relation only when no nested
        # demand exists, so a demand-free authored world can still describe its topology.
        ranked_nested = next(
            (item for item in diagnosis.unmet if item.capability == nested.name), None
        )
        if ranked_nested is not None:
            fields = {field for _key, field, _wrapper in decode_rendering(ranked_nested.detail)}
            selected = next(
                (
                    relation for relation in relationships
                    if relation[0] == ranked_nested.target and relation[2] in fields
                ),
                None,
            )
            if selected is not None:
                outer, inner, nested_field = selected

        inner_demand = sum(
            item.demand for item in diagnosis.considered
            if item.target == inner and item.capability == plain.name
        )
        outer_demand = sum(
            item.demand for item in diagnosis.considered
            if item.target == outer and item.capability == nested.name
        )

        # A renderer can exist before any caller asks for it, so diagnosis alone is not enough
        # for this state fact.  Ask whether each class has a callable method returning its own
        # declared fields as a mapping.  This still distinguishes a renderer from an unrelated
        # public method such as ``validate``.
        renders = any(
            supplying_method(
                node,
                _encode_rendering(tuple(
                    (item.target.id, item.target.id, None)
                    for item in node.body
                    if isinstance(item, ast.AnnAssign)
                    and isinstance(item.target, ast.Name)
                    and not item.target.id.startswith("_")
                )),
            ) is not None
            for node in classes
        )
        for item in diagnosis.considered:
            if renders:
                break
            node = by_name.get(item.target)
            if node is None:
                continue
            if item.capability == plain.name:
                renders = supplying_method(node, item.detail) is not None
            elif item.capability == nested.name:
                renders = nested.is_supplied_by(node, item.target, item.detail)
            if renders:
                break
        return cls(
            inner_call_sites=inner_demand,
            outer_call_sites=outer_demand,
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
