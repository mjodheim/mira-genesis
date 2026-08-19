"""The M094 lineage: the pipeline `experiments/M094/PROTOCOL.json` commits to.

`docs/REPOSITORY_AUDIT_2026_08_18.md` recorded two blockers. This module is the second
one. The protocol declares adoption (P7), independent validation (P8), a budget arm (P9),
a random-selection arm (P10), exact behavioural rollback (P11) and seven arms, and what
existed was diagnosis, synthesis, and an in-memory string.

The shape is M091's, deliberately, because M091 is the milestone in this repository whose
checker replays its science instead of reading booleans out of a file:

    observe · develop · sandbox · compare · validate · adopt · persist · restart
    · rollback_proof · run_arm · evaluate

Three things it does **not** do, and must not:

* it does not read `experiments/M094/QUALIFICATION_POOL.json`, or anything under
  `experiments/`. The draw is a separate process
  (`scripts/materialize_m094_qualification.py`) keyed on a mechanism digest that does not
  exist until adoption. `tests/test_m094_qualification_pool.py` enforces the boundary
  rather than trusting this docstring;
* it does not call a model or the network;
* it does not decide anything about `mira_core/`'s contents. The component, the class and
  the capability come from `m094_diagnosis`, which measures them.

What remains authored is what the protocol already discloses as the next ceiling: the
eligible set, the admissible observations, the operation set and the composition bound.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from metamorphosis.m094_composition import MAX_COMPOSITION_LENGTH
from metamorphosis.m094_diagnosis import (
    CAPABILITY_SHAPES,
    Diagnosis,
    Insufficiency,
    decode_rendering,
    diagnose,
)
from metamorphosis.m094_synthesis import suggest_operations

LINEAGE_SCHEMA = "m094-lineage-v1"
STATE_SCHEMA = "m094-transformation-state-v1"

#: Declared in `experiments/M094/PROTOCOL.json`. Mirrored, and checked against it by
#: `scripts/check_m094_result.py`, so the two cannot drift apart silently.
ARMS = (
    "endogenous_diagnosis_and_synthesis",
    "random_component_selection",
    "template_only_repair",
    "more_budget_same_operations",
    "diagnosis_without_adoption",
    "fresh_agent",
    "authored_target_component",
)

CEILING_ARMS = ("authored_target_component",)

CONDITIONS = (
    "P1_the_eligible_component_set_is_enumerated_and_no_component_is_privileged_by_the_protocol",
    "P2_the_insufficiency_is_a_measured_property_not_a_component_specific_string",
    "P3_the_diagnostic_verdict_inverts_when_the_capability_is_supplied",
    "P4_every_eligible_component_is_reachable_under_some_admissible_observation",
    "P5_the_selection_is_justified_against_rivals_by_measurement_and_is_stable_under_a_sweep_of_the_measure_s_own_constants",
    "P6_the_repair_is_assembled_from_composable_operations_and_is_not_a_template_body",
    "P7_the_adopted_repair_satisfies_a_requirement_drawn_after_the_mechanism_was_fixed",
    "P8_an_independent_validator_accepted_it_without_seeing_the_qualification",
    "P9_more_budget_over_the_same_operation_set_closes_nothing",
    "P10_a_random_component_selection_closes_nothing",
    "P11_rollback_is_exact_and_behavioural",
    "P12_chronology_track_a_and_no_leaked_evidence",
)

#: The budget arm's bound. Larger than the composition bound, and disclosed: the audit
#: measured the search saturating at length 5, so this arm is expected to close nothing
#: and the protocol requires it to be able to fail.
BUDGET_COMPOSITION_LENGTH = 20

#: Behavioural cases per component during development. The qualification draws its own.
DEVELOPMENT_CASES = 8

#: Seed for the development cases. Disclosed, so anyone can regenerate them. It does not
#: reach the qualification, whose salt is the adopted mechanism's digest.
DEVELOPMENT_SEED = "m094-development-cases-v1"


class LineageError(RuntimeError):
    """A lineage step was asked for something it cannot do."""


# ── canonical form ───────────────────────────────────────────────────


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("ascii")).hexdigest()


def _source_digest(source: str) -> str:
    return hashlib.sha256(b"m094-source-v1\0" + source.encode("utf-8")).hexdigest()


# ── observe ──────────────────────────────────────────────────────────


def observe(root: Path, components: Sequence[str]) -> Diagnosis:
    """Measure the eligible set. A thin pass-through, kept so the step has a name.

    The pipeline's first step is a measurement and not a choice, and naming it here means
    the arm runners cannot quietly substitute something else for it.
    """

    if not components:
        raise LineageError("the eligible component set is empty")
    return diagnose(root, components)


# ── behavioural cases ────────────────────────────────────────────────


def _value_for(annotation: str, name: str, rng: random.Random) -> Any:
    """Invent a value for one field from its annotation.

    Deliberately dumb and deliberately generic: it reads the annotation as text because
    the annotation is all the lineage is allowed to know about a field it did not write.
    A wrong guess costs a refused case, not a wrong verdict.
    """

    text = annotation.lower()
    token = f"{name}-{rng.randrange(16 ** 8):08x}"
    if "bool" in text:
        return rng.choice([True, False])
    if "int" in text or "float" in text:
        return rng.randrange(1000)
    if "mapping" in text or "dict" in text:
        return {f"{name}-key": token}
    if "tuple" in text or "sequence" in text or "iterable" in text:
        return (token, f"{name}-{rng.randrange(16 ** 8):08x}")
    if "list" in text or "set" in text:
        return [token]
    return token


def behavioural_cases(
    root: Path,
    component_path: str,
    class_name: str,
    *,
    count: int = DEVELOPMENT_CASES,
    seed: str = DEVELOPMENT_SEED,
) -> tuple[dict[str, Any], ...]:
    """Concrete constructor arguments for *class_name*, one per case.

    The cases are values, not expectations. What a correct method must return on them is
    derived from the requirement at comparison time, so nothing here contains an answer.
    """

    source = (root / component_path).read_text(encoding="utf-8")
    tree = ast.parse(source)
    node = next(
        (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == class_name),
        None,
    )
    if node is None:
        raise LineageError(f"class {class_name} not found in {component_path}")

    declared: list[tuple[str, str]] = []
    for item in node.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            declared.append((item.target.id, ast.unparse(item.annotation)))

    rng = random.Random(_digest({"seed": seed, "component": component_path, "class": class_name}))
    cases = []
    for _ in range(count):
        cases.append({name: _value_for(annotation, name, rng) for name, annotation in declared})
    return tuple(cases)


# ── the sandbox ──────────────────────────────────────────────────────


def _repo_dependencies(root: Path, component_path: str, source: str) -> tuple[str, ...]:
    """Which repository modules the variant imports, transitively.

    A sandbox that copies the whole package pulls in `mira_core/__init__.py`, which imports
    every module and therefore numpy. Copying only what the variant reaches keeps the
    sandbox a test of the component.

    The component's own imports are read from *source* rather than from disk, because the
    variant being sandboxed is frequently not what is on disk -- and in `rollback_proof` the
    live file is deliberately damaged, so reading it would crash the very step that proves
    the damage. An unparsable source contributes no edges, which is the right answer: a
    broken variant has no discoverable imports and the sandbox should report that it does
    not import rather than fail to be built.
    """

    seen: set[str] = {component_path}
    queue: list[str] = []

    def edges(text: str) -> list[str]:
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return []
        found: list[str] = []
        for item in ast.walk(tree):
            modules: list[str] = []
            if isinstance(item, ast.Import):
                modules = [alias.name for alias in item.names]
            elif isinstance(item, ast.ImportFrom) and item.module:
                modules = [item.module]
            for module in modules:
                candidate = module.replace(".", "/") + ".py"
                if (root / candidate).exists():
                    found.append(candidate)
        return found

    queue.extend(edges(source))
    while queue:
        current = queue.pop()
        if current in seen:
            continue
        seen.add(current)
        queue.extend(edges((root / current).read_text(encoding="utf-8")))
    return tuple(sorted(seen - {component_path}))


@dataclass(frozen=True)
class SandboxOutcome:
    """What one variant of a component did when it was actually executed.

    `cases_constructible` is reported apart from `cases_total` on purpose. A case that
    cannot build the object it is meant to exercise says nothing about the candidate, and
    an instrument that scores it as a failure turns its own defect into a refutation. The
    pool audit in `docs/REPOSITORY_AUDIT_2026_08_18.md` found seven of nine frozen
    qualification entries in exactly that state, so this distinction is load-bearing rather
    than fastidious.
    """

    variant: str
    imported: bool
    cases_total: int
    cases_satisfied: int
    satisfying_methods: tuple[str, ...]
    error: str | None
    cases_constructible: int = 0

    @property
    def runnable(self) -> bool:
        """Did anything actually get exercised?"""

        return self.imported and self.cases_constructible > 0

    @property
    def supplies_the_capability(self) -> bool:
        return self.runnable and self.cases_satisfied == self.cases_constructible

    def to_dict(self) -> dict[str, object]:
        return {
            "variant": self.variant,
            "imported": self.imported,
            "cases_total": self.cases_total,
            "cases_constructible": self.cases_constructible,
            "cases_satisfied": self.cases_satisfied,
            "satisfying_methods": list(self.satisfying_methods),
            "runnable": self.runnable,
            "supplies_the_capability": self.supplies_the_capability,
            "error": self.error,
        }


#: Executed inside the disposable subprocess. It receives the class name, the requirement
#: and the cases on stdin, and it is told nothing about which method should satisfy them:
#: it tries every public zero-argument method and reports which ones agree.
_PROBE_SCRIPT = r'''
import ast, importlib, json, sys, traceback

payload = json.loads(sys.stdin.read())
sys.path.insert(0, ".")

def wrap(value, wrapper):
    if wrapper == "list":
        return list(value)
    if wrapper == "tuple":
        return tuple(value)
    return value

result = {"imported": False, "cases_total": 0, "cases_constructible": 0,
          "cases_satisfied": 0, "satisfying_methods": [], "error": None}
try:
    module = importlib.import_module(payload["module"])
    cls = getattr(module, payload["class"])
    result["imported"] = True

    requirement = [tuple(item) for item in payload["requirement"]]
    cases = payload["cases"]
    result["cases_total"] = len(cases)

    # Every public zero-argument method is a candidate. The probe does not know the name
    # of the method it is looking for, so it cannot be satisfied by the right name alone.
    names = sorted(
        name for name in dir(cls)
        if not name.startswith("_") and callable(getattr(cls, name, None))
    )

    # Constructibility is measured before agreement and reported separately. A case that
    # cannot build the object measures nothing about the candidate, and counting it as a
    # failure would let a broken case read as a refuted requirement.
    constructible = 0
    for case in cases:
        try:
            cls(**case)
            constructible += 1
        except Exception:
            pass
    result["cases_constructible"] = constructible

    agreeing = []
    for name in names:
        satisfied = 0
        for case in cases:
            try:
                instance = cls(**case)
            except Exception:
                continue
            try:
                produced = getattr(instance, name)()
            except Exception:
                break
            if not isinstance(produced, dict):
                break
            ok = True
            for key, attribute, wrapper in requirement:
                try:
                    expected = wrap(getattr(instance, attribute), wrapper)
                except Exception:
                    ok = False
                    break
                if key not in produced or produced[key] != expected:
                    ok = False
                    break
            if not ok:
                break
            satisfied += 1
        # Agreement is judged over the cases that could be constructed, not over all of them.
        if constructible and satisfied == constructible:
            agreeing.append(name)

    result["satisfying_methods"] = agreeing
    if agreeing:
        result["cases_satisfied"] = constructible
except Exception:
    result["error"] = traceback.format_exc(limit=4)

print("M094_PROBE:" + json.dumps(result, sort_keys=True))
'''


def sandbox_component(
    root: Path,
    component_path: str,
    source: str,
    class_name: str,
    requirement: Sequence[tuple[str, str, str | None]],
    cases: Sequence[Mapping[str, Any]],
    *,
    variant: str,
    timeout_seconds: int = 60,
) -> SandboxOutcome:
    """Execute one source variant in a disposable directory, in a fresh interpreter.

    The variant never touches the live tree. Its repository dependencies are copied
    unmodified so an import failure means the variant is broken rather than lonely.
    """

    module = component_path.replace("/", ".").removesuffix(".py")
    with tempfile.TemporaryDirectory(prefix="m094-sandbox-") as tmp:
        sandbox = Path(tmp)
        target = sandbox / component_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
        # An empty package marker, not the real __init__, which imports the whole platform.
        for parent in Path(component_path).parents:
            if str(parent) not in {".", ""}:
                (sandbox / parent / "__init__.py").write_text("", encoding="utf-8")
        for dependency in _repo_dependencies(root, component_path, source):
            destination = sandbox / dependency
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / dependency, destination)
            for parent in Path(dependency).parents:
                if str(parent) not in {".", ""}:
                    marker = sandbox / parent / "__init__.py"
                    if not marker.exists():
                        marker.write_text("", encoding="utf-8")

        script = sandbox / "_m094_probe.py"
        script.write_text(_PROBE_SCRIPT, encoding="utf-8")
        payload = _canonical_json({
            "module": module,
            "class": class_name,
            "requirement": [list(item) for item in requirement],
            "cases": [dict(case) for case in cases],
        })

        try:
            completed = subprocess.run(
                [sys.executable, str(script)],
                cwd=sandbox,
                input=payload,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
        except subprocess.TimeoutExpired:
            return SandboxOutcome(variant, False, len(cases), 0, (), "TIMEOUT", 0)

        line = next(
            (l for l in completed.stdout.splitlines() if l.startswith("M094_PROBE:")), None
        )
        if line is None:
            return SandboxOutcome(
                variant, False, len(cases), 0, (),
                (completed.stderr or "no probe output")[-800:], 0,
            )
        parsed = json.loads(line[len("M094_PROBE:"):])
        return SandboxOutcome(
            variant=variant,
            imported=bool(parsed["imported"]),
            cases_total=int(parsed["cases_total"]),
            cases_satisfied=int(parsed["cases_satisfied"]),
            satisfying_methods=tuple(parsed["satisfying_methods"]),
            error=parsed["error"],
            cases_constructible=int(parsed.get("cases_constructible", 0)),
        )


# ── compare ──────────────────────────────────────────────────────────


def compare(before: SandboxOutcome, after: SandboxOutcome) -> dict[str, object]:
    """The A/B on a criterion fixed before either side was run.

    H0: the candidate makes no measurable difference to whether the component supplies the
    capability. H0 is rejected only when the original imported and did **not** supply it and
    the candidate imported and did. A candidate that breaks the import fails, and so does one
    that changes nothing.
    """

    null_rejected = bool(
        before.runnable
        and not before.supplies_the_capability
        and after.runnable
        and after.supplies_the_capability
    )
    if not before.imported:
        reason = "original does not import; the candidate cannot be credited"
    elif not before.runnable:
        reason = (
            f"no case could construct the object ({before.cases_constructible}/"
            f"{before.cases_total}); the comparison measures nothing"
        )
    elif before.supplies_the_capability:
        reason = "original already supplies the capability; there is nothing to close"
    elif not after.imported:
        reason = "candidate does not import"
    elif not after.supplies_the_capability:
        reason = (
            f"candidate satisfies {after.cases_satisfied}/{after.cases_total} cases; "
            "the requirement is not met"
        )
    else:
        reason = (
            f"candidate satisfies {after.cases_satisfied}/{after.cases_total} cases "
            f"through {', '.join(after.satisfying_methods)}; the original satisfied none"
        )

    return {
        "criterion": "the_candidate_supplies_a_capability_the_original_did_not_when_executed",
        "null_rejected": null_rejected,
        "reason": reason,
        "before": before.to_dict(),
        "after": after.to_dict(),
    }


# ── independent validation ───────────────────────────────────────────


@dataclass(frozen=True)
class Validation:
    """A separate process's verdict on a candidate it was handed without context."""

    validator_id: str
    accepted: bool
    reasons: tuple[str, ...]
    cases_total: int
    cases_satisfied: int
    methods_tried: int
    receipt: str

    def to_dict(self) -> dict[str, object]:
        return {
            "validator_id": self.validator_id,
            "accepted": self.accepted,
            "reasons": list(self.reasons),
            "cases_total": self.cases_total,
            "cases_satisfied": self.cases_satisfied,
            "methods_tried": self.methods_tried,
            "receipt": self.receipt,
        }


def validate_independently(
    root: Path,
    component_path: str,
    modified_source: str,
    class_name: str,
    requirement: Sequence[tuple[str, str, str | None]],
    *,
    validator_id: str = "m094-behavioural-validator",
    seed: str = "m094-validator-cases-v1",
    count: int = DEVELOPMENT_CASES,
) -> Validation:
    """Judge the candidate by running it, on cases the generator never saw.

    Three separations from the generator, because P8 is about independence and the audit
    found the acceptance predicate inside the search sharing its author:

    * it **executes** the candidate; the search only parses it;
    * it draws its own cases from its own seed, so a candidate tuned to the development
      cases has nothing to tune to;
    * it runs in a fresh interpreter that is handed the class name and the requirement and
      not the method name, so it cannot be satisfied by recognising the expected repair.

    It also cannot reach the qualification: the subprocess is given a directory holding the
    candidate and its dependencies, and `experiments/` is not in it.
    """

    reasons: list[str] = []
    try:
        ast.parse(modified_source)
    except SyntaxError as exc:
        return Validation(validator_id, False, (f"does_not_parse: {exc}",), 0, 0, 0, "")

    cases = behavioural_cases(root, component_path, class_name, count=count, seed=seed)
    outcome = sandbox_component(
        root, component_path, modified_source, class_name, requirement, cases,
        variant="validator",
    )

    if not outcome.imported:
        reasons.append("candidate_does_not_import")
    if outcome.cases_total == 0:
        reasons.append("no_case_was_offered")
    elif outcome.cases_constructible == 0:
        # Not a refusal of the candidate. The validator could not build the object at all,
        # so it has no opinion, and saying "accepted" or "rejected" would both be lies.
        reasons.append("no_case_could_construct_the_object")
    if outcome.imported and not outcome.satisfying_methods:
        reasons.append("no_public_method_reproduces_the_requirement_when_executed")
    if outcome.error:
        reasons.append("probe_error")

    accepted = not reasons and outcome.supplies_the_capability
    receipt = _digest({
        "validator_id": validator_id,
        "component": component_path,
        "class": class_name,
        "requirement": [list(item) for item in requirement],
        "seed": seed,
        "accepted": accepted,
        "cases": outcome.cases_total,
        "satisfied": outcome.cases_satisfied,
    })
    return Validation(
        validator_id=validator_id,
        accepted=accepted,
        reasons=tuple(reasons),
        cases_total=outcome.cases_total,
        cases_satisfied=outcome.cases_satisfied,
        methods_tried=len(outcome.satisfying_methods),
        receipt=receipt,
    )


# ── development ──────────────────────────────────────────────────────


@dataclass
class Development:
    """One arm's attempt: what it measured, what it built, and what refused it."""

    arm: str
    diagnosis: Diagnosis | None = None
    insufficiency: Insufficiency | None = None
    operations: tuple[object, ...] = ()
    modified_source: str | None = None
    mechanism_digest: str | None = None
    search: dict[str, object] = field(default_factory=dict)
    notes: dict[str, object] = field(default_factory=dict)

    @property
    def requirement(self) -> tuple[tuple[str, str, str | None], ...]:
        if self.insufficiency is None:
            return ()
        return decode_rendering(self.insufficiency.detail)

    def to_dict(self) -> dict[str, object]:
        return {
            "arm": self.arm,
            "selected_component": self.diagnosis.selected if self.diagnosis else None,
            "class": self.insufficiency.target if self.insufficiency else None,
            "capability": self.insufficiency.capability if self.insufficiency else None,
            "demand": self.insufficiency.demand if self.insufficiency else None,
            "requirement": [list(item) for item in self.requirement],
            "operation_count": len(self.operations),
            "mechanism_digest": self.mechanism_digest,
            "produced_a_candidate": self.modified_source is not None,
            "search": dict(self.search),
            "notes": dict(self.notes),
        }


def develop(
    root: Path,
    components: Sequence[str],
    *,
    arm: str = "endogenous_diagnosis_and_synthesis",
    max_length: int | None = None,
    component_override: str | None = None,
    template_only: bool = False,
) -> Development:
    """Diagnose, then build a candidate for what the diagnosis selected.

    `component_override` is how the random-selection and ceiling arms are expressed: the
    measurement still runs, and its requirement is still what the candidate must satisfy,
    but the component the repair is attempted on is imposed. That is exactly the human
    dependency M094 exists to remove, so the arms that keep it must be able to fail.
    """

    development = Development(arm=arm)
    development.diagnosis = observe(root, components)
    if not development.diagnosis.unmet:
        development.notes["stopped"] = "no unmet insufficiency"
        return development

    target = development.diagnosis.unmet[0]
    development.insufficiency = target

    if component_override is not None and component_override != target.component_path:
        # The requirement stays the diagnosed one. Repairing a different component cannot
        # satisfy it, and the arm exists to show that rather than to be spared it.
        development.notes["component_override"] = component_override
        development.notes["requirement_belongs_to"] = target.component_path
        return development

    source = (root / target.component_path).read_text(encoding="utf-8")

    if template_only:
        from metamorphosis import m094_transform as template

        operations = template.suggest_query_method(
            source, target.target, target.detail.split(",")[-1].split("=")[0],
        )
        development.operations = tuple(operations)
        development.notes["template"] = "m094_transform.suggest_query_method"
        try:
            modified = operations[0].apply(source) if operations else None
        except Exception as exc:  # the authored template may not even apply
            development.notes["template_error"] = str(exc)[:200]
            return development
        if modified is None:
            return development
        development.modified_source = modified
        development.mechanism_digest = _digest({"template": True, "source": modified})
        return development

    operations = suggest_operations(
        root, target.component_path, target.target,
        target.capability, target.target, target.detail,
        max_length=max_length,
    )
    development.operations = tuple(operations)
    if not operations:
        development.notes["stopped"] = "synthesis produced no operation"
        return development

    development.modified_source = operations[0].apply(source)
    development.mechanism_digest = operations[0].digest
    development.search = {
        "description": operations[0].description,
        "max_length": max_length or MAX_COMPOSITION_LENGTH,
    }
    return development


# ── adoption, persistence, restart ───────────────────────────────────


@dataclass(frozen=True)
class JournalEntry:
    """One immutable entry in the adoption journal."""

    version: int
    event: str
    component: str
    mechanism_digest: str
    original_source_digest: str
    modified_source_digest: str
    validation_receipt: str
    comparison: str
    previous_entry_digest: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "event": self.event,
            "component": self.component,
            "mechanism_digest": self.mechanism_digest,
            "original_source_digest": self.original_source_digest,
            "modified_source_digest": self.modified_source_digest,
            "validation_receipt": self.validation_receipt,
            "comparison": self.comparison,
            "previous_entry_digest": self.previous_entry_digest,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True)
class StoreState:
    """The store's serialisable state. This is what survives a process death."""

    version: int
    current_source_digest: str
    journal: tuple[JournalEntry, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": STATE_SCHEMA,
            "version": self.version,
            "current_source_digest": self.current_source_digest,
            "journal": [entry.to_dict() for entry in self.journal],
        }

    def to_bytes(self) -> bytes:
        return _canonical_json(self.to_dict()).encode("ascii")

    def digest(self) -> str:
        return _digest(self.to_dict())

    @classmethod
    def initial(cls, source_digest: str) -> StoreState:
        return cls(version=0, current_source_digest=source_digest, journal=())

    @classmethod
    def restore(cls, data: bytes) -> StoreState:
        raw = json.loads(data.decode("ascii"))
        if raw.get("schema") != STATE_SCHEMA:
            raise LineageError("state schema mismatch")
        return cls(
            version=int(raw["version"]),
            current_source_digest=str(raw["current_source_digest"]),
            journal=tuple(JournalEntry(**entry) for entry in raw["journal"]),
        )


class TransformationStore:
    """Transactional adoption of a real component, with exact rollback.

    Files, not objects. The component under transformation is the one on disk that the
    rest of the repository imports, which is what makes the rollback claim in P11 worth
    making and what makes the fault in `rollback_proof` strike something live.
    """

    STATE_NAME = ".m094-state.json"

    def __init__(self, root: Path, state: StoreState, work_dir: Path) -> None:
        self._root = root
        self._state = state
        self._work_dir = work_dir

    @property
    def state(self) -> StoreState:
        return self._state

    @property
    def version(self) -> int:
        return self._state.version

    @classmethod
    def state_path(cls, work_dir: Path) -> Path:
        return work_dir / cls.STATE_NAME

    def _backup_path(self, component: str) -> Path:
        return self._work_dir / f".m094-backup-{Path(component).name}"

    def _persist(self) -> None:
        self.state_path(self._work_dir).write_bytes(self._state.to_bytes())

    @classmethod
    def init_or_load(cls, root: Path, work_dir: Path, source_digest: str) -> TransformationStore:
        """Load persisted state if there is any, otherwise start a lineage.

        This is the restart boundary: a fresh process calls exactly this and gets the state
        the previous one left, with no context handed over in memory.
        """

        work_dir.mkdir(parents=True, exist_ok=True)
        path = cls.state_path(work_dir)
        if path.exists():
            return cls(root, StoreState.restore(path.read_bytes()), work_dir)
        store = cls(root, StoreState.initial(source_digest), work_dir)
        store._persist()
        return store

    def adopt(
        self,
        component: str,
        original_source: str,
        modified_source: str,
        mechanism_digest: str,
        validation: Validation,
        comparison: Mapping[str, object],
    ) -> bool:
        """Write the candidate to the live component, or refuse and change nothing.

        Refusal is not an error. An unvalidated or unimproving candidate must leave the
        tree exactly as it was, and the journal must record no adoption.
        """

        if not validation.accepted:
            return False
        if not comparison.get("null_rejected"):
            return False

        target = self._root / component
        backup = self._backup_path(component)
        # The original is preserved before the live file is touched, so a crash between
        # these two writes is recoverable rather than silent.
        backup.write_text(original_source, encoding="utf-8", newline="")
        target.write_text(modified_source, encoding="utf-8", newline="")

        previous = self._state.journal[-1].digest() if self._state.journal else None
        entry = JournalEntry(
            version=self._state.version + 1,
            event="adopt",
            component=component,
            mechanism_digest=mechanism_digest,
            original_source_digest=_source_digest(original_source),
            modified_source_digest=_source_digest(modified_source),
            validation_receipt=validation.receipt,
            comparison=str(comparison.get("reason", "")),
            previous_entry_digest=previous,
        )
        self._state = StoreState(
            version=entry.version,
            current_source_digest=entry.modified_source_digest,
            journal=self._state.journal + (entry,),
        )
        self._persist()
        return True

    def restore_exactly(self, component: str) -> str:
        """Put the preserved original back, byte for byte, and verify that it is back."""

        if self._state.version == 0:
            raise LineageError("nothing has been adopted, so nothing can be restored")
        entry = self._state.journal[-1]
        backup = self._backup_path(component)
        if not backup.exists():
            raise LineageError(f"the preserved original is missing: {backup}")
        original = backup.read_text(encoding="utf-8")
        if _source_digest(original) != entry.original_source_digest:
            raise LineageError("the preserved original does not match its recorded digest")

        target = self._root / component
        target.write_text(original, encoding="utf-8", newline="")
        written = target.read_text(encoding="utf-8")
        if _source_digest(written) != entry.original_source_digest:
            raise LineageError("restoration is not byte-exact")

        previous_journal = self._state.journal[:-1]
        self._state = StoreState(
            version=self._state.version - 1,
            current_source_digest=entry.original_source_digest,
            journal=previous_journal,
        )
        self._persist()
        return written


# ── rollback ─────────────────────────────────────────────────────────


def rollback_proof(
    root: Path,
    store: TransformationStore,
    component: str,
    class_name: str,
    requirement: Sequence[tuple[str, str, str | None]],
    cases: Sequence[Mapping[str, Any]],
    *,
    fault: str = "truncate_the_adopted_method",
) -> dict[str, object]:
    """Damage the **live** component, then restore it, and prove both by execution.

    The falsifier this exists to fail is "the rollback fault strikes a detached copy rather
    than the live file". So the fault is written to the file the repository imports, the
    damage is shown by running the component rather than by comparing a version number, and
    the restoration is verified both by digest and by re-running the same cases.
    """

    target = root / component
    adopted_source = target.read_text(encoding="utf-8")
    adopted_digest = _source_digest(adopted_source)
    after_adoption = sandbox_component(
        root, component, adopted_source, class_name, requirement, cases, variant="adopted",
    )

    if fault == "truncate_the_adopted_method":
        damaged_source = adopted_source[: int(len(adopted_source) * 0.8)]
    elif fault == "revert_to_the_original":
        damaged_source = store._backup_path(component).read_text(encoding="utf-8")
    else:
        raise LineageError(f"unknown fault class {fault!r}")

    # The live file, not a copy.
    target.write_text(damaged_source, encoding="utf-8", newline="")
    live_after_fault = target.read_text(encoding="utf-8")
    damaged_outcome = sandbox_component(
        root, component, live_after_fault, class_name, requirement, cases, variant="damaged",
    )

    restored = store.restore_exactly(component)
    restored_outcome = sandbox_component(
        root, component, restored, class_name, requirement, cases, variant="restored",
    )
    original_digest = _source_digest(restored)

    return {
        "fault": fault,
        "fault_struck_the_live_file": _source_digest(live_after_fault) != adopted_digest,
        "adopted_digest": adopted_digest,
        "damaged_digest": _source_digest(damaged_source),
        "restored_digest": original_digest,
        "restoration_is_byte_exact": (
            original_digest == store.state.current_source_digest
        ),
        "adopted_supplied_the_capability": after_adoption.supplies_the_capability,
        "damage_was_behavioural": not damaged_outcome.supplies_the_capability,
        "restored_matches_the_original_behaviour": (
            not restored_outcome.supplies_the_capability
        ),
        "store_version_after_restore": store.version,
        "observations": {
            "adopted": after_adoption.to_dict(),
            "damaged": damaged_outcome.to_dict(),
            "restored": restored_outcome.to_dict(),
        },
    }


# ── restart in a genuinely fresh process ─────────────────────────────


#: Run by `fresh_process_check` in a new interpreter. It is given the work directory and
#: nothing else: no diagnosis, no mechanism digest, no requirement. Everything it reports
#: it read back out of the persisted state.
_RESUME_SCRIPT = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
from pathlib import Path
from metamorphosis.m094_lineage import TransformationStore, StoreState, _source_digest

root = Path(sys.argv[1])
work = Path(sys.argv[2])
path = TransformationStore.state_path(work)
out = {"state_file_existed": path.exists()}
if path.exists():
    state = StoreState.restore(path.read_bytes())
    out["version"] = state.version
    out["journal_length"] = len(state.journal)
    out["state_digest"] = state.digest()
    entry = state.journal[-1] if state.journal else None
    out["mechanism_digest"] = entry.mechanism_digest if entry else None
    out["component"] = entry.component if entry else None
    if entry is not None:
        live = (root / entry.component).read_text(encoding="utf-8")
        out["live_matches_recorded_digest"] = (
            _source_digest(live) == state.current_source_digest
        )
print("M094_RESUME:" + json.dumps(out, sort_keys=True))
"""


def fresh_process_check(
    root: Path, work_dir: Path, *, timeout_seconds: int = 120,
) -> dict[str, object]:
    """Kill the process and continue from what was written down.

    The point is not that a subprocess can read a file. It is that the state on disk is
    sufficient: the new interpreter is handed a directory, reconstructs which component was
    transformed and which mechanism did it, and confirms the live file still matches the
    digest the previous generation recorded -- without being told any of it.
    """

    completed = subprocess.run(
        [sys.executable, "-c", _RESUME_SCRIPT, str(root), str(work_dir)],
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    line = next(
        (l for l in completed.stdout.splitlines() if l.startswith("M094_RESUME:")), None
    )
    if line is None:
        return {
            "resumed_from_state": False,
            "error": (completed.stderr or "no resume output")[-800:],
        }
    parsed = json.loads(line[len("M094_RESUME:"):])
    parsed["resumed_from_state"] = bool(
        parsed.get("state_file_existed")
        and parsed.get("mechanism_digest")
        and parsed.get("live_matches_recorded_digest") is True
    )
    parsed["process_was_fresh"] = True
    return parsed


# ── arms ─────────────────────────────────────────────────────────────


def _random_component(components: Sequence[str], selected: str, *, salt: str) -> str:
    """Pick a component without looking at the measurement.

    Seeded from the eligible set alone so the arm is reproducible, and excluding the
    diagnosed component so the arm is actually a rival rather than the same run again.
    """

    rivals = [item for item in components if item != selected]
    if not rivals:
        raise LineageError("the eligible set has no rival component")
    rng = random.Random(_digest({"salt": salt, "components": list(components)}))
    return rng.choice(sorted(rivals))


def run_arm(
    arm: str,
    root: Path,
    components: Sequence[str],
    *,
    work_dir: Path | None = None,
) -> dict[str, object]:
    """Run one declared arm and report what it closed.

    Every arm produces the same record shape, so `evaluate` compares like with like and a
    control cannot be excused for having reported something different.
    """

    if arm not in ARMS:
        raise LineageError(f"unknown arm {arm!r}")

    if arm == "fresh_agent":
        if work_dir is None:
            raise LineageError(
                "the fresh_agent arm needs the work directory holding the persisted state"
            )
        resumed = fresh_process_check(root, work_dir)
        return {
            "arm": arm,
            "is_ceiling": False,
            # This arm does not search, so "closed" means the lineage continued from its
            # own state rather than that a repair was found again.
            "closed": bool(resumed.get("resumed_from_state")),
            "persistence": resumed,
        }

    baseline = observe(root, components)
    if not baseline.unmet:
        return {"arm": arm, "is_ceiling": arm in CEILING_ARMS, "closed": False,
                "notes": {"stopped": "no unmet insufficiency"}}

    target = baseline.unmet[0]
    override: str | None = None
    template_only = False
    max_length: int | None = None

    if arm == "random_component_selection":
        override = _random_component(components, target.component_path, salt=arm)
    elif arm == "template_only_repair":
        template_only = True
    elif arm == "more_budget_same_operations":
        max_length = BUDGET_COMPOSITION_LENGTH
    elif arm == "authored_target_component":
        # The ceiling. The target is handed over instead of measured, which is the
        # dependency the milestone is about; excluded from the verdict by the protocol.
        override = target.component_path

    development = develop(
        root, components, arm=arm, max_length=max_length,
        component_override=override, template_only=template_only,
    )

    record: dict[str, object] = {
        "arm": arm,
        "is_ceiling": arm in CEILING_ARMS,
        "development": development.to_dict(),
    }

    if development.modified_source is None:
        record["closed"] = False
        record["reason"] = str(development.notes.get(
            "stopped", development.notes.get("template_error", "no candidate was produced"),
        ))
        return record

    cases = behavioural_cases(root, target.component_path, target.target)
    requirement = development.requirement
    original = (root / target.component_path).read_text(encoding="utf-8")
    before = sandbox_component(
        root, target.component_path, original, target.target, requirement, cases,
        variant="original",
    )
    after = sandbox_component(
        root, target.component_path, development.modified_source, target.target,
        requirement, cases, variant=arm,
    )
    comparison = compare(before, after)
    validation = validate_independently(
        root, target.component_path, development.modified_source, target.target, requirement,
    )

    record["comparison"] = comparison
    record["validation"] = validation.to_dict()
    record["closed"] = bool(comparison["null_rejected"] and validation.accepted)

    if arm == "diagnosis_without_adoption":
        # It closed in the sandbox and is deliberately never written. The live component
        # must still lack the capability afterwards, and that is what the arm reports.
        live = sandbox_component(
            root, target.component_path,
            (root / target.component_path).read_text(encoding="utf-8"),
            target.target, requirement, cases, variant="live_after_arm",
        )
        record["live_still_lacks_the_capability"] = not live.supplies_the_capability
        record["adopted"] = False

    return record


# ── the verdict ──────────────────────────────────────────────────────


def evaluate(
    development: Mapping[str, object],
    arms: Mapping[str, Mapping[str, object]],
    rollback: Mapping[str, object],
    persistence: Mapping[str, object],
    integrity: Mapping[str, object],
    qualification: Mapping[str, object] | None,
) -> dict[str, object]:
    """Compute every condition, and make every one able to turn the verdict negative.

    P1 to P6 are properties of the mechanism and are computed by the checker from the
    protocol and the source. P7 to P11 are properties of a run, and are computed here from
    what the run preserved. P12 is chronology. A condition whose inputs are absent is
    reported `uncomputed`, never as a pass.
    """

    endogenous = arms.get("endogenous_diagnosis_and_synthesis", {})
    budget = arms.get("more_budget_same_operations", {})
    randomised = arms.get("random_component_selection", {})
    template = arms.get("template_only_repair", {})
    unadopted = arms.get("diagnosis_without_adoption", {})
    fresh = arms.get("fresh_agent", {})

    def computed(value: object) -> bool:
        return value is not None

    results: dict[str, dict[str, object]] = {}

    def record(name: str, passed: bool | None, evidence: str, detail: object = None) -> None:
        results[name] = {
            "computed": passed is not None,
            "passed": bool(passed) if passed is not None else False,
            "evidence": evidence,
            "detail": detail,
        }

    # P7 — the drawn requirement
    if qualification is None:
        record(
            CONDITIONS[6], None,
            "no qualification has been materialized, so no drawn requirement has been met or missed",
        )
    else:
        entries = list(qualification.get("entries", []))
        satisfied = [item for item in entries if item.get("satisfied") is True]
        cross = {item.get("component") for item in entries}
        record(
            CONDITIONS[6],
            bool(entries) and len(satisfied) == len(entries) and len(cross) >= 2
            and qualification.get("salt_is_the_adopted_mechanism_digest") is True
            and qualification.get("drawn_after_adoption") is True,
            f"{len(satisfied)}/{len(entries)} drawn requirements satisfied across "
            f"{len(cross)} component(s)",
            {"entries": entries},
        )

    # P8 — independent validation
    validation = endogenous.get("validation") if endogenous else None
    if validation is None:
        record(CONDITIONS[7], None, "no validator has run, because no candidate was produced")
    else:
        record(
            CONDITIONS[7],
            bool(validation.get("accepted")) and bool(validation.get("receipt"))
            and int(validation.get("cases_total", 0)) >= 4
            and integrity.get("validator_cannot_reach_the_qualification") is True
            and integrity.get("validator_executes_rather_than_parses") is True,
            f"validator accepted={validation.get('accepted')} on "
            f"{validation.get('cases_satisfied')}/{validation.get('cases_total')} executed cases",
            validation,
        )

    # P9 — more budget over the same operation set
    if not budget:
        record(CONDITIONS[8], None, "the budget arm has not been run")
    else:
        record(
            CONDITIONS[8],
            budget.get("closed") is not True or _same_mechanism(endogenous, budget),
            "budget arm closed nothing beyond the same mechanism"
            if budget.get("closed") is not True or _same_mechanism(endogenous, budget)
            else "the budget arm reached something the declared bound did not",
            {"closed": budget.get("closed"),
             "same_mechanism_as_endogenous": _same_mechanism(endogenous, budget)},
        )

    # P10 — random component selection
    if not randomised:
        record(CONDITIONS[9], None, "the random-selection arm has not been run")
    else:
        record(
            CONDITIONS[9],
            randomised.get("closed") is False,
            f"random-selection arm closed={randomised.get('closed')}",
            randomised.get("development"),
        )

    # P11 — rollback
    if not rollback:
        record(CONDITIONS[10], None, "no adoption has occurred, so no rollback was performed")
    else:
        record(
            CONDITIONS[10],
            rollback.get("fault_struck_the_live_file") is True
            and rollback.get("damage_was_behavioural") is True
            and rollback.get("restoration_is_byte_exact") is True
            and rollback.get("restored_matches_the_original_behaviour") is True,
            f"fault={rollback.get('fault')}, live={rollback.get('fault_struck_the_live_file')}, "
            f"byte_exact={rollback.get('restoration_is_byte_exact')}",
            rollback,
        )

    supporting = {
        "template_arm_closed": template.get("closed") if template else None,
        "unadopted_arm_left_the_component_unchanged": (
            unadopted.get("live_still_lacks_the_capability") if unadopted else None
        ),
        "fresh_process_resumed_from_state": persistence.get("resumed_from_state"),
        "fresh_agent_arm": fresh.get("closed") if fresh else None,
    }

    return {
        "schema": LINEAGE_SCHEMA,
        "conditions": results,
        "supporting": supporting,
        "development": dict(development),
        "arms_run": sorted(arms),
        "ceiling_arms": list(CEILING_ARMS),
    }


def _same_mechanism(left: Mapping[str, object], right: Mapping[str, object]) -> bool:
    """Did two arms arrive at the identical adopted mechanism?

    The budget arm is allowed to reach the same repair -- that is the expected result, and
    it is what "closes nothing" means for a saturated search. What it may not do is reach a
    different one, which would mean the declared bound was hiding something.
    """

    def digest(record: Mapping[str, object]) -> object:
        development = record.get("development")
        if isinstance(development, Mapping):
            return development.get("mechanism_digest")
        return None

    return digest(left) is not None and digest(left) == digest(right)
