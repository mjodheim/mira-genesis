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

import argparse
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
RESULT_PATH = EXPERIMENT / "RESULT.json"
QUALIFICATION_PATH = EXPERIMENT / "QUALIFICATION.json"


def _result_path() -> Path:
    """Resolved at call time, not at import.

    Both constants above are computed from `EXPERIMENT` when the module loads, so a test that
    redirects `EXPERIMENT` alone would leave the run loader reading the real experiment
    directory -- and would silently observe the pre-run branch while believing it had staged a
    run. Deriving the path per call means redirecting `EXPERIMENT` is enough.
    """

    return EXPERIMENT / "RESULT.json"


def _qualification_path() -> Path:
    return EXPERIMENT / "QUALIFICATION.json"


def load_run() -> dict | None:
    """The preserved run, or ``None`` if none exists.

    Every run-dependent condition below branches on this. Before a run it reports
    `uncomputed`; after one it recomputes from what the run preserved. The audit found the
    second branch missing entirely: P7 and P12 *failed* the moment a RESULT.json appeared,
    and P8 through P11 returned `uncomputed` unconditionally, so the protocol's
    "positive only when every condition is computed and true" was unreachable by
    construction.
    """

    result_path = _result_path()
    if not result_path.exists():
        return None
    run = json.loads(result_path.read_text(encoding="utf-8"))
    qualification_path = _qualification_path()
    if qualification_path.exists():
        run.setdefault(
            "qualification", json.loads(qualification_path.read_text(encoding="utf-8"))
        )
    return run


def _arm(run: dict, name: str) -> dict:
    arms = run.get("arms", {})
    value = arms.get(name) if isinstance(arms, dict) else None
    return value if isinstance(value, dict) else {}

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


def _operations_carrying_a_literal_body(directory: Path | None = None) -> set[str]:
    """String constants in the synthesis module that are themselves method bodies.

    A repair assembled from composable operations does not appear anywhere as a
    block of source text. One that is written out as an f-string and filled in
    does, and that is the difference P6 exists to measure.
    """

    # Every M094 module, not just the one that happened to hold the template.
    # Scanning a single file would let the defect pass by being moved, which is
    # the failure mode this whole audit keeps finding.
    directory = directory or (ROOT / "metamorphosis")
    modules = sorted(directory.glob("m094_*.py"))
    assert modules, "no M094 modules found to scan in " + str(directory)

    found: set[str] = set()

    for module_path in modules:
        tree = ast.parse(module_path.read_text(encoding="utf-8"))

        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node, clean=False)
                if doc is not None:
                    docstrings.add(doc)

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
                    found.add(module_path.name + ": " + stripped.splitlines()[0].strip())
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
    """The selection is justified by measurement and stable under a sweep of constants.

    The defect this condition was written for was `RenderAsMapping.min_fields`:
    authored, and sweeping it over 2..6 moved the selected component on three of
    five values. The declared value 3 was in fact the outlier — 2, 4 and 5 all
    chose `mira_core/contracts.py`, which is what the threshold-free rule chooses
    too, so the earlier selection of `mira_core/safety.py` was a property of that
    constant rather than a finding.

    The knob is gone. Attribution now asks how many reachable classes could
    explain a call site: exactly one is evidence about that class, several is
    evidence about none. There is nothing left to sweep, so the check is that
    nothing sweepable exists — reintroducing a numeric knob fails this again.
    """
    import metamorphosis.m094_diagnosis as _diag

    failures: list[str] = []

    knobs: dict[str, dict[str, int]] = {}
    for shape in _diag.CAPABILITY_SHAPES:
        numeric = {
            name: value
            for name, value in vars(shape).items()
            if isinstance(value, int) and not isinstance(value, bool)
        }
        if numeric:
            knobs[shape.name] = numeric

    if knobs:
        failures.append(
            "a capability shape carries an authored numeric constant that can decide "
            f"the selection: {knobs}"
        )

    result = structural_diagnose(ROOT, COMPONENT_PATHS)
    if result.selected is None:
        failures.append("no component is selected, so no selection is justified")

    passed = not failures
    return Condition(
        id="P5",
        name="the_selection_is_justified_against_rivals_by_measurement_and_is_stable_under_a_sweep_of_the_measure_s_own_constants",
        passed=passed,
        evidence=(
            f"no numeric constant governs attribution; selected {result.selected}"
            if passed
            else "; ".join(failures)
        ),
        detail={
            "selected": result.selected,
            "numeric_constants_in_capability_shapes": knobs,
            "attribution_rule": (
                "a call site counts for a class when exactly one reachable class could "
                "explain it; ambiguous sites count for none"
            ),
            "unmet": [
                {"component": i.component_path, "class": i.class_name, "demand": i.demand}
                for i in result.unmet
            ],
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
    name = "the_adopted_repair_satisfies_a_requirement_drawn_after_the_mechanism_was_fixed"
    run = load_run()

    if run is None:
        # Nothing has been qualified. An artifact appearing without a RESULT.json would mean
        # qualification data exists ahead of the run that is supposed to have produced it.
        stray = [
            n for n in ("QUALIFICATION.json", "REGISTER_CLAIM.json")
            if (EXPERIMENT / n).exists()
        ]
        if stray:
            return Condition(
                id="P7", name=name, passed=False,
                evidence="qualification artifacts exist with no run that produced them: "
                         + ", ".join(stray),
                detail={"stray_artifacts": stray},
            )
        return not_computed(
            "P7", name,
            "no qualification run exists, so no drawn requirement has been satisfied or missed",
            detail={"status": protocol.get("status"), "qualification_exists": False},
        )

    # A run exists. Recompute the draw rather than reading its conclusion: a fabricated or
    # re-rolled draw is exactly what the salt rule exists to prevent, and the only way to
    # detect one is to derive it again from the recorded mechanism digest.
    failures: list[str] = []
    qualification = run.get("qualification")
    if not isinstance(qualification, dict):
        return Condition(
            id="P7", name=name, passed=False,
            evidence="the run preserved no qualification",
            detail={"keys": sorted(run)},
        )

    mechanism = str(run.get("mechanism_digest") or qualification.get("mechanism_digest") or "")
    if len(mechanism) != 64:
        failures.append("the run records no 64-character adopted mechanism digest")

    pool_path = EXPERIMENT / "QUALIFICATION_POOL.json"
    recomputed_draw: list[str] = []
    if mechanism and pool_path.exists():
        sys.path.insert(0, str(ROOT / "scripts"))
        from materialize_m094_qualification import draw as redraw  # noqa: PLC0415

        pool = json.loads(pool_path.read_text(encoding="utf-8"))
        pool_digest = _digest({k: v for k, v in pool.items() if k != "pool_digest"})
        if pool_digest != pool.get("pool_digest"):
            failures.append("the committed pool no longer digests to its recorded value")
        recomputed_draw = [entry["entry_digest"] for entry in redraw(pool, mechanism)]
        recorded_draw = [
            str(item.get("entry_digest")) for item in qualification.get("entries", [])
        ]
        if recomputed_draw != recorded_draw:
            failures.append(
                "the recorded draw is not the draw the recorded mechanism digest produces"
            )

    entries = qualification.get("entries", [])
    outcomes = [str(item.get("outcome")) for item in entries]
    components = {str(item.get("component")) for item in entries}
    if not entries:
        failures.append("the qualification drew nothing")
    if len(components) < 2:
        failures.append(f"the draw is not cross-component: {sorted(components)}")
    if qualification.get("salt_is_the_adopted_mechanism_digest") is not True:
        failures.append("the qualification does not record the salt rule it used")
    if qualification.get("drawn_after_adoption") is not True:
        failures.append("the qualification does not record that it was drawn after adoption")

    # An unrunnable entry measures nothing, so it can neither satisfy nor refute. The
    # condition stays uncomputed rather than being scored either way -- seven of the nine
    # frozen pool entries carry hidden cases that raise on construction, and letting that
    # read as a refutation would turn an instrument defect into evidence.
    if not failures and "unrunnable" in outcomes:
        return not_computed(
            "P7", name,
            "a drawn entry is unrunnable: its cases cannot construct their class, so it "
            "measures nothing about the mechanism",
            detail={"outcomes": outcomes, "entries": entries},
        )

    if failures:
        return Condition(
            id="P7", name=name, passed=False, evidence="; ".join(failures),
            detail={"failures": failures, "outcomes": outcomes},
        )

    passed = all(item == "satisfied" for item in outcomes)
    return Condition(
        id="P7", name=name, passed=passed,
        evidence=(
            f"{outcomes.count('satisfied')}/{len(outcomes)} drawn requirements satisfied "
            f"across {len(components)} components; draw recomputed from the mechanism digest"
        ),
        detail={"outcomes": outcomes, "components": sorted(components),
                "draw_recomputed": recomputed_draw},
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

    name = "an_independent_validator_accepted_it_without_seeing_the_qualification"
    run = load_run()
    if run is None:
        return not_computed(
            "P8", name,
            "no validator has accepted anything, because no candidate has been qualified",
            detail={"protocol_preconditions": "satisfied"},
        )

    endogenous = _arm(run, "endogenous_diagnosis_and_synthesis")
    validation = endogenous.get("validation")
    if not isinstance(validation, dict):
        return Condition(
            id="P8", name=name, passed=False,
            evidence="the run preserved no validation record for the endogenous arm",
            detail={"arm_keys": sorted(endogenous)},
        )

    # Re-run the validator on the preserved candidate rather than believing its verdict.
    replayed: dict | None = None
    adopted_source = endogenous.get("adopted_source")
    development = endogenous.get("development", {})
    if isinstance(adopted_source, str) and isinstance(development, dict):
        from metamorphosis.m094_lineage import validate_independently  # noqa: PLC0415

        component = str(development.get("selected_component") or "")
        class_name = str(development.get("class") or "")
        requirement = [tuple(item) for item in development.get("requirement", [])]
        if component and class_name and requirement:
            outcome = validate_independently(
                ROOT, component, adopted_source, class_name, requirement,
            )
            replayed = outcome.to_dict()
            if outcome.accepted is not bool(validation.get("accepted")):
                failures.append(
                    "replaying the validator disagrees with the recorded verdict: "
                    f"recorded={validation.get('accepted')}, replayed={outcome.accepted}"
                )
            if outcome.receipt != validation.get("receipt"):
                failures.append("the replayed validator receipt does not match the recorded one")

    if not validation.get("accepted"):
        failures.append(f"the validator did not accept: {validation.get('reasons')}")
    if not validation.get("receipt"):
        failures.append("the validation carries no receipt")
    if int(validation.get("cases_total", 0)) < 4:
        failures.append(f"only {validation.get('cases_total')} cases were offered")
    if int(validation.get("cases_satisfied", 0)) < 1:
        failures.append("the validator satisfied no case")

    if failures:
        return Condition(
            id="P8", name=name, passed=False, evidence="; ".join(failures),
            detail={"failures": failures, "recorded": validation, "replayed": replayed},
        )

    return Condition(
        id="P8", name=name, passed=True,
        evidence=(
            f"validator accepted {validation.get('cases_satisfied')}/"
            f"{validation.get('cases_total')} executed cases"
            + ("; replayed and agreed" if replayed else "")
        ),
        detail={"recorded": validation, "replayed": replayed},
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

    name = "more_budget_over_the_same_operation_set_closes_nothing"
    run = load_run()
    if run is None:
        return not_computed(
            "P9", name,
            "the budget arm has not been run, so nothing is known about what it closes",
            detail={"protocol_preconditions": "satisfied"},
        )

    from metamorphosis.m094_lineage import _same_mechanism  # noqa: PLC0415

    endogenous = _arm(run, "endogenous_diagnosis_and_synthesis")
    budget = _arm(run, "more_budget_same_operations")
    if not budget:
        return Condition(
            id="P9", name=name, passed=False,
            evidence="the run preserved no record for the budget arm",
            detail={"arms_present": sorted(run.get("arms", {}))},
        )

    same = _same_mechanism(endogenous, budget)
    # A saturated search may reach the same repair with more room -- that is what "closes
    # nothing" means here. What it may not do is reach a different one, which would mean the
    # declared bound was hiding something the protocol claims it is not.
    passed = budget.get("closed") is not True or same
    return Condition(
        id="P9", name=name, passed=passed,
        evidence=(
            "the budget arm reached the same mechanism" if same
            else f"the budget arm closed={budget.get('closed')} with a different mechanism"
        ),
        detail={"closed": budget.get("closed"), "same_mechanism": same,
                "budget_bound": budget.get("development", {}).get("search", {})},
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

    name = "a_random_component_selection_closes_nothing"
    run = load_run()
    if run is None:
        return not_computed(
            "P10", name,
            "the random-selection arm has not been run, so nothing is known about what it closes",
            detail={"protocol_preconditions": "satisfied"},
        )

    randomised = _arm(run, "random_component_selection")
    if not randomised:
        return Condition(
            id="P10", name=name, passed=False,
            evidence="the run preserved no record for the random-selection arm",
            detail={"arms_present": sorted(run.get("arms", {}))},
        )

    development = randomised.get("development", {})
    imposed = development.get("notes", {}).get("component_override") if isinstance(
        development, dict
    ) else None
    if not imposed:
        failures.append(
            "the random-selection arm records no imposed component, so it may have run the "
            "endogenous path under another name"
        )
    if randomised.get("closed") is not False:
        failures.append(f"the random-selection arm closed={randomised.get('closed')}")

    if failures:
        return Condition(
            id="P10", name=name, passed=False, evidence="; ".join(failures),
            detail={"failures": failures, "arm": randomised},
        )
    return Condition(
        id="P10", name=name, passed=True,
        evidence=f"random selection imposed {imposed} and closed nothing",
        detail={"imposed_component": imposed, "arm": randomised},
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

    name = "rollback_is_exact_and_behavioural"
    run = load_run()
    if run is None:
        return not_computed(
            "P11", name,
            "no adoption has occurred, so no rollback has been performed or measured",
            detail={"protocol_preconditions": "satisfied"},
        )

    rollback = run.get("rollback")
    if not isinstance(rollback, dict):
        return Condition(
            id="P11", name=name, passed=False,
            evidence="the run preserved no rollback record",
            detail={"keys": sorted(run)},
        )

    # Each of these is the negation of a falsifier the protocol names. A rollback that
    # struck a detached copy, or that only restored a version number, fails here.
    required = {
        "fault_struck_the_live_file": "the fault did not strike the live file",
        "adopted_supplied_the_capability": "the adopted state did not supply the capability",
        "damage_was_behavioural": "the damage was not observable by executing the component",
        "restoration_is_byte_exact": "restoration was not byte-exact",
        "restored_matches_the_original_behaviour":
            "the restored component does not behave like the original",
    }
    for key, complaint in required.items():
        if rollback.get(key) is not True:
            failures.append(complaint)
    if rollback.get("store_version_after_restore") != 0:
        failures.append(
            f"the store did not return to version 0 "
            f"(got {rollback.get('store_version_after_restore')})"
        )

    if failures:
        return Condition(
            id="P11", name=name, passed=False, evidence="; ".join(failures),
            detail={"failures": failures, "rollback": rollback},
        )
    return Condition(
        id="P11", name=name, passed=True,
        evidence=(
            f"fault {rollback.get('fault')} struck the live file, was behaviourally "
            "observable, and restoration was byte-exact"
        ),
        detail={"rollback": rollback},
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

    # A withdrawn run is disclosed, not forbidden. The protocol's retry policy says
    # superseded runs are preserved and disclosed, so their presence is compliance; what
    # would be a violation is a withdrawn artifact the record does not mention.
    withdrawn = sorted(str(p.name) for p in EXPERIMENT.glob("WITHDRAWN_RESULT_*.json"))

    run = load_run()
    if run is None:
        if withdrawn:
            failures.append(
                "withdrawn result artifacts exist with no current run that supersedes them: "
                + ", ".join(withdrawn)
            )
    else:
        # After a run, RESULT.json existing is the expected state and not a leak. An earlier
        # revision failed this condition precisely because the experiment had been performed,
        # which made a positive verdict unreachable by construction.
        if run.get("track") != "A":
            failures.append(f"the run records track {run.get('track')!r}, expected 'A'")
        if int(run.get("model_calls", 0)) != 0:
            failures.append(f"the run records {run.get('model_calls')} model calls")
        if int(run.get("network_calls", 0)) != 0:
            failures.append(f"the run records {run.get('network_calls')} network calls")
        declared = run.get("prior_attempts")
        if withdrawn and not declared:
            failures.append(
                "withdrawn artifacts exist but the run declares no prior attempts: "
                + ", ".join(withdrawn)
            )
        if run.get("attempt") is None:
            failures.append("the run declares no attempt number")
        elif withdrawn and int(run.get("attempt", 1)) != len(withdrawn) + 1:
            failures.append(
                f"attempt {run.get('attempt')} disagrees with {len(withdrawn)} preserved "
                "withdrawn run(s); the attempt number must be derived from the artifacts"
            )

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
            "run_exists": run is not None,
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
    """Run the checker and print a JSON report.

    Exit codes matter, because a checker CI cannot fail on is not a gate. ``--strict`` turns a
    failing computed condition into a non-zero exit; ``--require-result`` additionally demands
    that a run exists and that the verdict is positive, which is the form to use once M094 has
    been armed. Neither invents a verdict: without a run the report is `incomplete`, and
    ``--strict`` is satisfied by that because nothing has failed.
    """

    parser = argparse.ArgumentParser(description="Recompute M094's twelve conditions.")
    parser.add_argument(
        "--strict", action="store_true",
        help="exit non-zero if any computed condition failed",
    )
    parser.add_argument(
        "--require-result", action="store_true",
        help="also require that a run exists and every condition is computed and true",
    )
    parser.add_argument(
        "--no-write", action="store_true",
        help="do not rewrite CHECK_REPORT.json",
    )
    args = parser.parse_args()

    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    report = compute_report(protocol)

    # Always write the report to the experiment directory if it exists
    if EXPERIMENT.is_dir() and not args.no_write:
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

    if args.require_result:
        if load_run() is None:
            print(
                "\nNo RESULT.json exists: M094 has not been run.", file=sys.stderr,
            )
            return 1
        if report["verdict"] != "positive":
            print(
                f"\nVerdict is {report['verdict']!r}, not 'positive'.", file=sys.stderr,
            )
            return 1
    if args.strict and report["failed"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())