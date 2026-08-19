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


def build(root: Path) -> Path:
    """Write S0 into *root* and return it. Nothing here renders anything."""

    (root / "pkg").mkdir(parents=True, exist_ok=True)
    (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / COMPONENT).write_text(VALUES, encoding="utf-8")

    for index in range(READING_CALLERS):
        (root / f"reading_caller_{index}.py").write_text(
            READING_CALLER.format(index=index), encoding="utf-8"
        )
    for index in range(SAMPLE_CALLERS):
        (root / f"sample_caller_{index}.py").write_text(
            SAMPLE_CALLER.format(index=index), encoding="utf-8"
        )
    return root


@dataclass(frozen=True)
class WorldFacts:
    """What the world is, stated so a reader can check it rather than trust it."""

    inner_class: str = "Reading"
    outer_class: str = "Sample"
    nested_field: str = "reading"
    inner_call_sites: int = READING_CALLERS
    outer_call_sites: int = SAMPLE_CALLERS
    nothing_renders_itself_at_s0: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": WORLD_SCHEMA,
            "authored": True,
            "inner_class": self.inner_class,
            "outer_class": self.outer_class,
            "nested_field": self.nested_field,
            "inner_call_sites": self.inner_call_sites,
            "outer_call_sites": self.outer_call_sites,
            "nothing_renders_itself_at_s0": self.nothing_renders_itself_at_s0,
            "selection_is_the_lineage_s": True,
            "why_not_mira_core": (
                "the nested-rendering demand does not exist there: AgentResult holds an "
                "Observation but its call sites reach through it into .state rather than "
                "rendering it, so the demand would have had to be planted"
            ),
        }
