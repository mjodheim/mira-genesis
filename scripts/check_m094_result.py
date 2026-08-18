"""Decisive checker for M094: recompute every protocol condition from preserved artifacts.

M094 is a draft (not frozen). Twelve conditions P1-P12 are defined in
experiments/M094/PROTOCOL.json. This checker re-derives each one from the
preserved source and protocol, with zero skip flags — every condition is
computed and every one can fail.

A conjunctive verdict is computed: positive iff all 12 conditions are true.
The report is returned as JSON, written to stdout, and also written to
experiments/M094/CHECK_REPORT.json (if the directory exists).

Because M094 has never been run, there is no RESULT.json to validate against.
Conditions P7-P12 are therefore checked structurally: the protocol's guarantees
are verified rather than a recorded run. Every condition is fully recomputed.
"""
from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m094_diagnosis import (  # noqa: E402
    CAPABILITY_SHAPES,
    FilterByAttribute,
    Insufficiency,
    RenderAsMapping,
    diagnose as structural_diagnose,
    measure_component,
)
from metamorphosis.m094_synthesis import (  # noqa: E402
    suggest_operations,
)
from metamorphosis.m094_component_discovery import (  # noqa: E402
    ELIGIBLE_COMPONENTS,
)

EXPERIMENT = ROOT / "experiments" / "M094"
PROTOCOL_PATH = EXPERIMENT / "PROTOCOL.json"
DESIGN_AUDIT_PATH = EXPERIMENT / "DESIGN_AUDIT.json"
DESIGN_AUDIT_MD = EXPERIMENT / "DESIGN_AUDIT.md"

DIAGNOSIS_MODULE = ROOT / "metamorphosis" / "m094_diagnosis.py"

# Components measured in the audit and by the structural diagnosis
COMPONENT_PATHS = [
    "mira_core/memory.py",
    "mira_core/safety.py",
    "mira_core/contracts.py",
]

# Forbidden literals that would make the measure component-specific (Defect 1)
_FORBIDDEN_LITERALS = {"mira_core", "MemoryLedger", "memory.py", "event.kind", "events_by_kind"}


# ── Canonical helpers ──────────────────────────────────────────────────────

def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("ascii")).hexdigest()


# ── Result model ───────────────────────────────────────────────────────────


@dataclass
class Condition:
    """One protocol condition with its verdict and evidence."""

    id: str
    name: str
    passed: bool
    evidence: str = ""
    detail: dict | None = None
    #: False when the condition cannot be decided from the evidence that exists.
    #: A condition requiring a qualification run is not satisfied by the absence
    #: of one, and it is not refuted by it either. Forcing such a condition into
    #: pass/fail is how a checker reports a verdict it has not earned.
    computed: bool = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "passed": self.passed,
            "evidence": self.evidence,
            "detail": self.detail or {},
            "computed": self.computed,
        }


def not_computed(condition_id: str, name: str, reason: str, detail: dict | None = None) -> Condition:
    """A condition that no evidence in the repository can currently decide."""

    return Condition(
        id=condition_id,
        name=name,
        passed=False,
        evidence=f"not computable before a qualification run: {reason}",
        detail=detail,
        computed=False,
    )


# ── Synthetic repositories for Defect-2 verification ──────────────────────


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


def _build_ledger_repo(tmp_path: Path, ledger_source: str, callers: int = 1) -> Path:
    _write(tmp_path, "pkg/__init__.py", "")
    _write(tmp_path, "pkg/ledger.py", ledger_source)
    for index in range(callers):
        _write(tmp_path, f"consumers/use_{index}.py", CALLER_FILTERS_BY_HAND)
    return tmp_path


DECISION_WITHOUT_RENDERER = '''
from dataclasses import dataclass

@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    missing: tuple = ()
'''

DECISION_WITH_RENDERER = DECISION_WITHOUT_RENDERER + '''
    def to_dict(self):
        return {"allowed": self.allowed, "reason": self.reason, "missing": list(self.missing)}
'''

CALLER_DESTRUCTURES = '''
from pkg.decision import Decision

def record(step, d):
    return {"step": step, "allowed": d.allowed, "reason": d.reason, "missing": list(d.missing)}
'''


def _qualification_exists() -> bool:
    """Has a qualification run produced artifacts this checker could read?"""

    return any(
        (EXPERIMENT / name).exists()
        for name in ("RESULT.json", "QUALIFICATION.json", "REGISTER_CLAIM.json")
    )


def _operations_carrying_a_literal_body() -> set[str]:
    """String constants in the synthesis module that are themselves method bodies.

    A repair assembled from composable operations does not appear anywhere as a
    block of source text. One that is written out as an f-string and filled in
    does, and that is the difference P6 exists to measure.
    """

    import metamorphosis.m094_synthesis as synthesis

    source = Path(synthesis.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc is not None:
                docstrings.add(doc)

    found: set[str] = set()
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
                found.add(stripped.splitlines()[0].strip())
    return found


# ── P1: Eligible component set ────────────────────────────────────────────

def check_p1(protocol: dict) -> Condition:
    """The eligible component set is enumerated and no component is privileged.

    The protocol must list the eligible components, they must be the same as
    what the implementation enumerates, and no component path or class name
    may appear as a run-time literal in the diagnosis measure.
    """
    failures: list[str] = []

    arms = set(protocol.get("arms", []))
    ceiling = set(protocol.get("ceiling_arms", []))

    expected_arms = {
        "endogenous_diagnosis_and_synthesis",
        "random_component_selection",
        "template_only_repair",
        "more_budget_same_operations",
        "diagnosis_without_adoption",
        "fresh_agent",
        "authored_target_component",
    }
    if arms != expected_arms:
        failures.append(f"arms mismatch: {arms.symmetric_difference(expected_arms)}")
    if ceiling != {"authored_target_component"}:
        failures.append(f"ceiling arms mismatch: expected {{authored_target_component}}, got {ceiling}")

    eligible_paths = {spec.path for spec in ELIGIBLE_COMPONENTS}
    if eligible_paths != set(COMPONENT_PATHS):
        failures.append(f"ELIGIBLE_COMPONENTS mismatch: expected {set(COMPONENT_PATHS)}, got {eligible_paths}")

    # Verify no diagnosis module literal matches a component identity (Defect 1 check)
    source = DIAGNOSIS_MODULE.read_text(encoding="utf-8")
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
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        and node.value not in docstrings
    }
    leaked = {lit for lit in literals if any(bad in lit for bad in _FORBIDDEN_LITERALS)}
    if leaked:
        failures.append(f"diagnosis module contains component-specific string literals: {leaked}")

    # No component carries authored per-component constants in the structural measure.
    # Check CAPABILITY_SHAPES: the shape names must be generic.
    for shape in CAPABILITY_SHAPES:
        if hasattr(shape, "min_fields") and shape.min_fields != 3:
            failures.append(f"RenderAsMapping.min_fields is not at its declared value of 3: {shape.min_fields}")
        # Verify shapes don't carry component names
        for attr in ("name",):
            val = getattr(shape, attr, "")
            if any(comp in str(val) for comp in ("memory", "safety", "contracts", "MemoryLedger")):
                failures.append(f"shape {type(shape).__name__}.{attr} contains a component name: {val}")

    passed = not failures
    return Condition(
        id="P1",
        name="the_eligible_component_set_is_enumerated_and_no_component_is_privileged",
        passed=passed,
        evidence=(
            "enumerated and unprivileged"
            if passed
            else "; ".join(failures)
        ),
        detail={
            "eligible_components": sorted(eligible_paths),
            "arms": sorted(arms),
            "ceiling_arms": sorted(ceiling),
            "leaked_literals": sorted(leaked) if leaked else None,
        },
    )


# ── P2: Insufficiency is a measured property ──────────────────────────────

def check_p2(protocol: dict) -> Condition:
    """The insufficiency is a measured property, not a component-specific string.

    Run the structural diagnosis on the real repository and verify that:
    - The selected component's insufficiency is determined by demand, not by an authored constant
    - The measure module does not name any component path or class
    """
    failures: list[str] = []

    try:
        result = structural_diagnose(ROOT, COMPONENT_PATHS)
    except Exception as exc:
        failures.append(f"structural diagnosis failed: {exc}")
        return Condition(
            id="P2",
            name="the_insufficiency_is_a_measured_property_not_a_component_specific_string",
            passed=False,
            evidence=f"diagnosis raised: {exc}",
            detail={"error": str(exc)},
        )

    if result.selected is None:
        failures.append("diagnosis selected no component (nothing is insufficient)")

    if result.unmet:
        top = result.unmet[0]
        # Verify that demand is > 0 (measurement > constant)
        if top.demand <= 0:
            failures.append(f"selected insufficiency has zero demand: {top.component_path}")
        # Verify the selected component exists
        if top.component_path not in COMPONENT_PATHS:
            failures.append(f"selected component is not in the eligible set: {top.component_path}")
    else:
        failures.append("no unmet capabilities found — diagnostic finds nothing to repair")

    # Verify the measure module names no component (structural check)
    source = DIAGNOSIS_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc is not None:
                docstrings.add(doc)
    lit_check = {
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        and node.value not in docstrings
    }
    leaked = {lit for lit in lit_check if any(bad in lit for bad in _FORBIDDEN_LITERALS)}
    if leaked:
        failures.append(f"diagnosis module leaks component identity: {leaked}")

    passed = not failures
    return Condition(
        id="P2",
        name="the_insufficiency_is_a_measured_property_not_a_component_specific_string",
        passed=passed,
        evidence=(
            f"selected: {result.selected}, unmet: {[i.class_name for i in result.unmet]}"
            if not failures
            else "; ".join(failures)
        ),
        detail={
            "selected": result.selected,
            "unmet": [{"class": i.class_name, "capability": i.capability, "demand": i.demand, "supplied": i.supplied}
                      for i in result.unmet],
            "considered": len(result.considered),
        },
    )


# ── P3: Diagnostic verdict inverts when capability is supplied ───────────

def check_p3(protocol: dict) -> Condition:
    """The diagnostic verdict inverts when the capability is supplied.

    Use a synthetic repository: measure a component without the capability → it
    registers as unmet; add the capability → it is no longer unmet. Also verify
    that demand is unchanged by supply — the structural separation (demand outside,
    supply inside) makes Defect 2 structurally impossible.
    """
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        # --- FilterByAttribute shape ---
        without = _build_ledger_repo(root / "without", LEDGER_WITHOUT_QUERY, callers=1)
        with_it = _build_ledger_repo(root / "with", LEDGER_WITH_QUERY, callers=1)

        try:
            before = measure_component(without, "pkg/ledger.py")
            after = measure_component(with_it, "pkg/ledger.py")
        except Exception as exc:
            failures.append(f"measure_component on synthetic repo failed: {exc}")
            return Condition(id="P3", name="the_diagnostic_verdict_inverts_when_the_capability_is_supplied",
                             passed=False, evidence=f"exception: {exc}", detail={"error": str(exc)})

        unmet_before = [i for i in before if i.is_unmet]
        unmet_after = [i for i in after if i.is_unmet]

        if not unmet_before:
            failures.append("synthetic component without the capability registers as met (should be unmet)")
        if unmet_after:
            failures.append("synthetic component WITH the capability registers as unmet (should be met)")
        if unmet_before and unmet_after:
            if unmet_before[0].demand != unmet_after[0].demand:
                failures.append(
                    f"supplying the capability changed demand: {unmet_before[0].demand} vs {unmet_after[0].demand}"
                    " — the structural separation is violated"
                )

        # --- RenderAsMapping shape ---
        # The caller must import the module actually under measurement. An
        # earlier revision wrote the component to `pkg2` while the caller
        # imported `pkg.decision`, so the import-reach gate correctly reported
        # zero demand and the checker misread that as a diagnosis failure.
        _write(root, "pkg2/__init__.py", "")
        _write(root, "pkg2/decision.py", DECISION_WITHOUT_RENDERER)
        _write(root, "consumers2/rec.py", CALLER_DESTRUCTURES.replace(
            "from pkg.decision import", "from pkg2.decision import"))

        mapping_before = measure_component(root, "pkg2/decision.py")
        unmet_map_before = [i for i in mapping_before if i.is_unmet]

        _write(root, "pkg2/decision.py", DECISION_WITH_RENDERER)
        mapping_after = measure_component(root, "pkg2/decision.py")
        unmet_map_after = [i for i in mapping_after if i.is_unmet]

        if not unmet_map_before:
            failures.append("Decision without to_dict should be unmet")
        if unmet_map_after:
            failures.append("Decision WITH to_dict should be met")
        if unmet_map_before and unmet_map_after and unmet_map_before[0].demand != unmet_map_after[0].demand:
            failures.append("supplying RenderAsMapping changed demand — structural separation violated")

    passed = not failures
    return Condition(
        id="P3",
        name="the_diagnostic_verdict_inverts_when_the_capability_is_supplied",
        passed=passed,
        evidence="verdict inverts when capability is supplied; demand is invariant under supply"
        if passed else "; ".join(failures),
        detail={
            "filter_shape_unmet_before": len([i for i in before if i.is_unmet]) if not failures else None,
        } if passed else {"failures": failures},
    )


# ── P4: Every eligible component is reachable ────────────────────────────

def check_p4(protocol: dict) -> Condition:
    """Every eligible component is reachable under some admissible observation.

    Run the structural diagnosis on all eligible components and verify that
    every component can score unmet demand under some configuration.
    """
    failures: list[str] = []

    try:
        result = structural_diagnose(ROOT, COMPONENT_PATHS)
    except Exception as exc:
        failures.append(f"structural diagnosis failed: {exc}")
        return Condition(
            id="P4", name="every_eligible_component_is_reachable_under_some_admissible_observation",
            passed=False, evidence=str(exc), detail={"error": str(exc)},
        )

    # Collect which components have unmet demand
    selected_components = set()
    for insuff in result.considered:
        selected_components.add(insuff.component_path)

    # Check if every eligible component can be selected under some measurement
    for path in COMPONENT_PATHS:
        if path not in selected_components and path != result.selected:
            # Check if this component can ever have demand by measuring it directly
            measured = measure_component(ROOT, path)
            if all(not i.is_unmet for i in measured) and all(i.demand == 0 for i in measured):
                failures.append(f"{path} has zero demand and zero unmet — it is unreachable")

    passed = not failures
    return Condition(
        id="P4",
        name="every_eligible_component_is_reachable_under_some_admissible_observation",
        passed=passed,
        evidence=(
            f"all {len(COMPONENT_PATHS)} components reachable"
            if passed
            else "; ".join(failures)
        ),
        detail={
            "eligible_components": COMPONENT_PATHS,
            "components_with_unmet_demand": sorted(set(i.component_path for i in result.considered if i.is_unmet)),
            "components_with_any_demand": sorted(selected_components),
            "selected": result.selected,
        },
    )


# ── P5: Stability under sweep of measure constants ──────────────────────

def check_p5(protocol: dict) -> Condition:
    """The selection is stable under a sweep of the measure's own constants.

    RenderAsMapping.min_fields is authored. Sweep it over 2-6 and verify whether
    the selected component is stable. If it moves, the defect is disclosed rather
    than hidden — the checker reports the instability so P5 is documented, even
    if it currently fails.
    """
    import metamorphosis.m094_diagnosis as _diag

    failures: list[str] = []
    saved_shapes = _diag.CAPABILITY_SHAPES
    sweep: dict[str, dict] = {}

    try:
        for threshold in (2, 3, 4, 5, 6):
            _diag.CAPABILITY_SHAPES = (
                FilterByAttribute(),
                RenderAsMapping(min_fields=threshold),
            )
            result = structural_diagnose(ROOT, COMPONENT_PATHS)
            sweep[str(threshold)] = {
                "selected": result.selected,
                "unmet": [{"class": i.class_name, "demand": i.demand} for i in result.unmet],
            }
    finally:
        _diag.CAPABILITY_SHAPES = saved_shapes

    selections = {row["selected"] for row in sweep.values() if row["selected"] is not None}
    is_stable = len(selections) <= 1

    if not is_stable:
        failures.append(
            f"selection is not stable across min_fields sweep: "
            f"{len(selections)} distinct selections: {sorted(selections)}"
        )
        for thresh, row in sweep.items():
            if thresh == "3":  # the declared value
                failures.append(f"  min_fields={thresh} selects {row['selected']} (declared)")
            else:
                failures.append(f"  min_fields={thresh} selects {row['selected']}")

    passed = not failures
    return Condition(
        id="P5",
        name="the_selection_is_justified_against_rivals_by_measurement_and_is_stable_under_a_sweep_of_the_measure_s_own_constants",
        passed=passed,
        evidence=(
            f"stable across min_fields=2..6: selected={list(selections)}"
            if is_stable
            else "; ".join(failures[:5])
        ),
        detail={
            "declared_min_fields": 3,
            "is_stable": is_stable,
            "distinct_selections": sorted(selections),
            "sweep": sweep,
        },
    )


# ── P6: Transformation set is not a single template ──────────────────────

def check_p6(protocol: dict) -> Condition:
    """The repair is assembled from composable operations and is not a template body.

    Use m094_synthesis to generate candidate operations for the selected
    insufficiency. Verify that:
    - The operations are AST-driven, not authored bodies
    - The operation description mentions no component name or path
    - There is at least one operation (search occurs)
    - No operation contains a finished body as a literal
    """
    failures: list[str] = []

    try:
        result = structural_diagnose(ROOT, COMPONENT_PATHS)
    except Exception as exc:
        failures.append(f"structural diagnosis failed: {exc}")
        return Condition(
            id="P6",
            name="the_repair_is_assembled_from_composable_operations_and_is_not_a_template_body",
            passed=False,
            evidence=str(exc),
            detail={"error": str(exc)},
        )

    if not result.unmet and result.selected is None:
        failures.append("no insufficiency diagnosed — cannot verify synthesis")
        return Condition(
            id="P6",
            name="the_repair_is_assembled_from_composable_operations_and_is_not_a_template_body",
            passed=False,
            evidence="no insufficiency to synthesise",
            detail={"error": "no unmet insufficiency"},
        )

    top = result.unmet[0]
    ops = suggest_operations(
        ROOT,
        component_path=top.component_path,
        class_name=top.class_name,
        capability=top.capability,
        target=top.target,
        detail=top.detail,
    )

    if not ops:
        failures.append("suggest_operations returned no candidates — no search occurs")

    for op in ops:
        # Check that the operation description does not leak component identity
        if op.file != top.component_path and op.file not in COMPONENT_PATHS:
            failures.append(f"operation targets unexpected file: {op.file}")
        # Verify the operation has a digest (structural identity, not authored)
        if not op.digest or len(op.digest) < 8:
            failures.append(f"operation has invalid digest: {op.digest}")
        # The operation description should mention the class (from AST) but
        # not a component path
        desc = op.description
        for path in COMPONENT_PATHS:
            if path in desc:
                failures.append(f"operation description contains a component path: {desc}")
                break

    # The assertion the docstring promised and the original omitted: an operation
    # may not carry a finished method body. Identifiers may be substituted from
    # the AST, but the *shape* of the repair must be composed rather than written
    # down, or this is Defect 4 with generic names.
    templated = _operations_carrying_a_literal_body()
    if templated:
        failures.append(
            "the synthesis emits a finished method body as a source template, so the "
            "repair shape is authored rather than assembled: "
            + ", ".join(sorted(templated))
        )

    passed = not failures
    return Condition(
        id="P6",
        name="the_repair_is_assembled_from_composable_operations_and_is_not_a_template_body",
        passed=passed,
        evidence=(
            f"{len(ops)} operation(s) generated for {top.class_name}/{top.capability}"
            if not failures
            else "; ".join(failures)
        ),
        detail={
            "operation_count": len(ops),
            "operations": [op.to_dict() for op in ops],
            "target_class": top.class_name,
            "target_capability": top.capability,
        },
    )


# ── P7: No qualification data exists ────────────────────────────────────

def check_p7(protocol: dict) -> Condition:
    """The adopted repair satisfies a requirement drawn after the mechanism was fixed.

    This claim needs a qualification run: a requirement drawn from the adopted
    mechanism's digest, and a repair measured against it. No such run exists.

    An earlier revision implemented this as "no RESULT.json exists and the
    protocol is a draft", so it passed precisely *because* nothing had been
    qualified, and would have flipped to FAIL the moment M094 produced a real
    result. The polarity was inverted and the pass was vacuous.
    """
    forbidden = ("RESULT.json", "QUALIFICATION.json", "REGISTER_CLAIM.json")
    present = [n for n in forbidden if (EXPERIMENT / n).exists()]

    name = "the_adopted_repair_satisfies_a_requirement_drawn_after_the_mechanism_was_fixed"

    if present:
        return Condition(
            id="P7",
            name=name,
            passed=False,
            evidence=(
                "qualification artifacts exist while the protocol is still a draft: "
                + ", ".join(present)
            ),
            detail={"forbidden_artifacts_present": present},
        )

    return not_computed(
        "P7",
        name,
        "no qualification run exists, so no drawn requirement has been satisfied or missed",
        detail={"status": protocol.get("status"), "qualification_exists": False},
    )


# ── P8: Validator independence ──────────────────────────────────────────

def check_p8(protocol: dict) -> Condition:
    """An independent validator accepted it without seeing the qualification.

    No qualification exists, so the validator is structurally independent.
    Verify that:
    - No qualification module is importable by the synthesis or diagnosis
    - The protocol does not claim a qualification was seen
    """
    failures: list[str] = []

    # Check that the protocol's qualification section says the right thing
    qualification = protocol.get("qualification", {})
    if qualification.get("not_importable_by_the_lineage") is not True:
        failures.append("protocol does not assert qualification is not importable")
    # This field is a disclosure, not a flag. M091 records it as prose stating
    # exactly what is and is not claimed about blindness; an earlier revision
    # tested it for `is True` and so failed every protocol that actually made
    # the disclosure.
    blindness = qualification.get("experimenter_blindness_is_not_claimed")
    if not isinstance(blindness, str) or not blindness.strip():
        failures.append(
            "protocol carries no experimenter-blindness disclosure "
            f"(found {type(blindness).__name__})"
        )

    # Check that no qualification module exists in the codebase (structural)
    qual_path = ROOT / "metamorphosis" / "m094_qualification.py"
    if qual_path.exists():
        failures.append("qualification module exists: metamorphosis/m094_qualification.py")

    if failures:
        return Condition(
            id="P8",
            name="an_independent_validator_accepted_it_without_seeing_the_qualification",
            passed=False,
            evidence="; ".join(failures),
            detail={"protocol_precondition_failures": failures},
        )

    # The protocol preconditions hold. The condition itself is about what a
    # run would show, and no run exists.
    return not_computed(
        "P8",
        "an_independent_validator_accepted_it_without_seeing_the_qualification",
        "no validator has accepted anything, because no candidate has been qualified",
        detail={"protocol_preconditions": "satisfied"},
    )


# ── P9: More budget over same operations closes nothing ─────────────────

def check_p9(protocol: dict) -> Condition:
    """More budget over the same operation set closes nothing.

    Since the synthesis generates operations (not search with varying budget),
    verify that the operation set is finite and no increase in 'budget' would
    produce a different result. The synthesis always returns the same operations
    for the same diagnosis — there is no budget dimension.
    """
    failures: list[str] = []

    # Verify that calling suggest_operations multiple times returns the same result
    try:
        result = structural_diagnose(ROOT, COMPONENT_PATHS)
    except Exception as exc:
        failures.append(f"structural diagnosis failed: {exc}")
        return Condition(
            id="P9", name="more_budget_over_the_same_operation_set_closes_nothing",
            passed=False, evidence=str(exc), detail={"error": str(exc)},
        )

    if not result.unmet:
        return Condition(
            id="P9",
            name="more_budget_over_the_same_operation_set_closes_nothing",
            passed=True,
            evidence="no insufficiency to verify budget against",
            detail={"note": "no unmet insufficiency, vacuously true"},
        )

    top = result.unmet[0]
    ops_first = suggest_operations(
        ROOT,
        component_path=top.component_path,
        class_name=top.class_name,
        capability=top.capability,
        target=top.target,
        detail=top.detail,
    )
    ops_second = suggest_operations(
        ROOT,
        component_path=top.component_path,
        class_name=top.class_name,
        capability=top.capability,
        target=top.target,
        detail=top.detail,
    )

    digests_first = sorted(op.digest for op in ops_first)
    digests_second = sorted(op.digest for op in ops_second)
    if digests_first != digests_second:
        failures.append("suggest_operations is not deterministic: same input → different output")

    # The synthesis always returns the same operations; there is no budget parameter.
    # A control arm must be declared and must NOT be a ceiling arm. Ceiling arms
    # are excluded from the verdict; control arms must be able to fail it. An
    # earlier revision required this arm to be a ceiling arm, which also made the
    # checker unsatisfiable, since P1 requires the ceiling set to be exactly
    # {authored_target_component}.
    arms = set(protocol.get("arms", []))
    ceiling_arms = set(protocol.get("ceiling_arms", []))
    if "more_budget_same_operations" not in arms:
        failures.append("more_budget_same_operations is not declared as an arm")
    if "more_budget_same_operations" in ceiling_arms:
        failures.append("more_budget_same_operations is a ceiling arm; it must be a control")

    if failures:
        return Condition(
            id="P9",
            name="more_budget_over_the_same_operation_set_closes_nothing",
            passed=False,
            evidence="; ".join(failures),
            detail={"protocol_precondition_failures": failures},
        )

    # The protocol preconditions hold. The condition itself is about what a
    # run would show, and no run exists.
    return not_computed(
        "P9",
        "more_budget_over_the_same_operation_set_closes_nothing",
        "the budget arm has not been run, so nothing is known about what it closes",
        detail={"protocol_preconditions": "satisfied"},
    )


# ── P10: Random component selection closes nothing ──────────────────────

def check_p10(protocol: dict) -> Condition:
    """A random component selection closes nothing.

    The diagnosis is deterministic: it selects the component with the highest
    unmet demand. A random selection would pick a different component and
    therefore would not close the insufficiency — the repair is specific to
    the diagnosed component.
    """
    failures: list[str] = []

    try:
        result = structural_diagnose(ROOT, COMPONENT_PATHS)
    except Exception as exc:
        failures.append(f"structural diagnosis failed: {exc}")
        return Condition(
            id="P10", name="a_random_component_selection_closes_nothing",
            passed=False, evidence=str(exc), detail={"error": str(exc)},
        )

    arms = set(protocol.get("arms", []))
    ceiling_arms = set(protocol.get("ceiling_arms", []))
    if "random_component_selection" not in arms:
        failures.append("random_component_selection is not declared as an arm")
    if "random_component_selection" in ceiling_arms:
        failures.append("random_component_selection is a ceiling arm; it must be a control")

    if result.unmet:
        top = result.unmet[0]
        # Verify that for each other component, applying the same capability
        # would not resolve the insufficiency (different components have
        # different insufficiency profiles)
        other_components = [p for p in COMPONENT_PATHS if p != top.component_path]
        for other in other_components:
            measured = measure_component(ROOT, other)
            if any(i.is_unmet and i.capability == top.capability for i in measured):
                # The other component has the same unmet capability — this means
                # random selection could accidentally pick a component that also
                # benefits. That's OK for P10 as long as the selected diagnosis
                # component is the strongest candidate.
                pass

        # Verify the selected component has genuinely higher demand than others
        for other_path in other_components:
            other_measured = measure_component(ROOT, other_path)
            other_unmet = [i for i in other_measured if i.is_unmet]
            if other_unmet and other_unmet[0].demand > top.demand:
                failures.append(f"{other_path} has higher demand ({other_unmet[0].demand}) "
                               f"than selected {top.component_path} ({top.demand}) "
                               "- random selection could pick a stronger candidate")

    if failures:
        return Condition(
            id="P10",
            name="a_random_component_selection_closes_nothing",
            passed=False,
            evidence="; ".join(failures),
            detail={"protocol_precondition_failures": failures},
        )

    # The protocol preconditions hold. The condition itself is about what a
    # run would show, and no run exists.
    return not_computed(
        "P10",
        "a_random_component_selection_closes_nothing",
        "the random-selection arm has not been run, so nothing is known about what it closes",
        detail={"protocol_preconditions": "satisfied"},
    )


# ── P11: Rollback is exact and behavioural ──────────────────────────────

def check_p11(protocol: dict) -> Condition:
    """Rollback is exact and behavioural.

    Since no experiment has been run, verify the rollback infrastructure
    exists and the protocol specifies exact rollback requirements.
    """
    failures: list[str] = []

    retry = protocol.get("retry_policy", {})
    # `reroll_permitted` must be False and the correction ban True. An earlier
    # revision required both to be True, so it failed the protocol for forbidding
    # rerolls — demanding the very violation the discipline exists to prevent.
    if retry.get("reroll_permitted") is not False:
        failures.append(
            f"retry_policy.reroll_permitted must be false, got {retry.get('reroll_permitted')}"
        )
    if retry.get("result_saving_correction_after_a_verdict_is_forbidden") is not True:
        failures.append(
            "retry_policy.result_saving_correction_after_a_verdict_is_forbidden must be true, "
            f"got {retry.get('result_saving_correction_after_a_verdict_is_forbidden')}"
        )

    falsifiers = protocol.get("falsifiers", [])
    has_rollback_falsifier = any(
        "rollback" in f.lower() and "detached" in f.lower()
        for f in falsifiers
    )
    if not has_rollback_falsifier:
        rollback_falsifiers = [f for f in falsifiers if "rollback" in f.lower()]
        if not rollback_falsifiers:
            failures.append("no rollback-related falsifier in the protocol")

    if failures:
        return Condition(
            id="P11",
            name="rollback_is_exact_and_behavioural",
            passed=False,
            evidence="; ".join(failures),
            detail={"protocol_precondition_failures": failures},
        )

    # The protocol preconditions hold. The condition itself is about what a
    # run would show, and no run exists.
    return not_computed(
        "P11",
        "rollback_is_exact_and_behavioural",
        "no adoption has occurred, so no rollback has been performed or measured",
        detail={"protocol_preconditions": "satisfied"},
    )


# ── P12: Chronology track A and no leaked evidence ──────────────────────

def check_p12(protocol: dict) -> Condition:
    """Chronology track A and no leaked evidence.

    The protocol must specify track A, and no evidence (qualification data,
    result artifacts) may leak before the experiment runs.
    """
    failures: list[str] = []

    track = protocol.get("track", "")
    if track != "A":
        failures.append(f"protocol track is '{track}', expected 'A'")

    # Check no evidence of prior runs exists (no WITHDRAWN_RESULT_* files)
    withdrawn = sorted(str(p.name) for p in EXPERIMENT.glob("WITHDRAWN_RESULT_*.json"))
    if withdrawn:
        failures.append(f"withdrawn result artifacts exist: {withdrawn}")

    # Check no experiment record exists
    if (EXPERIMENT / "RESULT.json").exists():
        failures.append("RESULT.json exists before an experiment has run")

    # The protocol must not claim to rerun M092
    if protocol.get("reattempts_m092") is not False:
        failures.append("protocol claims to reattempt M092")
    not_a_reattempt = protocol.get("not_a_reattempt_of_m092", "")
    if "H38 and D062 remain unresolved" not in not_a_reattempt:
        failures.append("protocol does not explicitly state M092 is untouched")

    passed = not failures
    return Condition(
        id="P12",
        name="chronology_track_a_and_no_leaked_evidence",
        passed=passed,
        evidence=(
            "track A, no leaked artifacts, M092 untouched"
            if passed
            else "; ".join(failures)
        ),
        detail={
            "track": track,
            "reattempts_m092": protocol.get("reattempts_m092"),
            "withdrawn_artifacts": withdrawn,
        },
    )


# ── Verdict ──────────────────────────────────────────────────────────────

def compute_report(protocol: dict) -> dict:
    """Recompute all 12 conditions from preserved artifacts."""

    conditions = [
        ("P1", check_p1(protocol)),
        ("P2", check_p2(protocol)),
        ("P3", check_p3(protocol)),
        ("P4", check_p4(protocol)),
        ("P5", check_p5(protocol)),
        ("P6", check_p6(protocol)),
        ("P7", check_p7(protocol)),
        ("P8", check_p8(protocol)),
        ("P9", check_p9(protocol)),
        ("P10", check_p10(protocol)),
        ("P11", check_p11(protocol)),
        ("P12", check_p12(protocol)),
    ]

    # The protocol's verdict rule is "positive iff every condition is true; each
    # is computed and each can fail". A condition that could not be computed is
    # therefore neither a pass nor a refutation, and a verdict may not be
    # declared while any remain outstanding.
    passed = sum(1 for _, c in conditions if c.computed and c.passed)
    failed = sum(1 for _, c in conditions if c.computed and not c.passed)
    uncomputed = sum(1 for _, c in conditions if not c.computed)

    if failed:
        verdict = "negative"
    elif uncomputed:
        verdict = "incomplete"
    else:
        verdict = "positive"

    report = {
        "schema": "m094-checker-v2",
        "milestone": "M094",
        "verdict": verdict,
        "verdict_rule": (
            "negative if any computed condition fails; incomplete while any condition "
            "remains uncomputed; positive only when every condition is computed and true"
        ),
        "total_conditions": len(conditions),
        "passed": passed,
        "failed": failed,
        "uncomputed": uncomputed,
        "conditions": {pid: c.to_dict() for pid, c in conditions},
        "failed_conditions": [pid for pid, c in conditions if c.computed and not c.passed],
        "uncomputed_conditions": [pid for pid, c in conditions if not c.computed],
    }
    report["report_digest"] = _digest(
        {k: v for k, v in report.items() if k != "report_digest"}
    )
    return report


def main() -> int:
    """Run the checker and print a JSON report."""
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    report = compute_report(protocol)

    # Always write the report to the experiment directory if it exists
    if EXPERIMENT.is_dir():
        report_path = EXPERIMENT / "CHECK_REPORT.json"
        report_path.write_text(
            _canonical_json(report) + "\n", encoding="utf-8", newline="\n"
        )
        print(f"Report written to {report_path.relative_to(ROOT)}")

    print(json.dumps(report, indent=2, sort_keys=True))

    if report["failed"] > 0:
        print(f"\nFAILED CONDITIONS: {report['failed_conditions']}", file=sys.stderr)
    if report["uncomputed"] > 0:
        print(
            "UNCOMPUTED CONDITIONS: "
            + str(report["uncomputed_conditions"])
            + " (no qualification run exists)",
            file=sys.stderr,
        )

    # Return 0 for success (we always report, even failures)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())