"""Generic component inspection and insufficiency discovery for M094.

A bounded set of real Genesis components is inspected for measurable
limitations. The lineage examines each component, produces diagnostic
hypotheses, selects the most constrained component, and justifies
the choice — all before any transformation is generated.

This is the first step toward removing the authored TARGET_FILE from M093.
"""

from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence


# ── Schemas ──────────────────────────────────────────────────────────

DIAGNOSTIC_SCHEMA = "m094-component-diagnostic-v1"


# ── Canonical JSON ───────────────────────────────────────────────────

def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("ascii")).hexdigest()


# ── Component registry (frozen before experiment) ────────────────────

@dataclass(frozen=True)
class ComponentSpec:
    """A real Genesis component eligible for inspection."""

    path: str                # relative path from repo root, e.g. "mira_core/memory.py"
    module: str              # module name, e.g. "mira_core.memory"
    class_names: tuple[str, ...]  # classes defined in this file
    lines: int               # total lines of code

    def digest(self) -> str:
        return _digest({
            "path": self.path,
            "module": self.module,
            "classes": sorted(self.class_names),
            "lines": self.lines,
        })


# The frozen eligibility scope — hardcoded before experiment, but the
# lineage chooses *which* component to transform, not the human.
ELIGIBLE_COMPONENTS: tuple[ComponentSpec, ...] = (
    ComponentSpec(
        path="mira_core/memory.py",
        module="mira_core.memory",
        class_names=("MemoryEvent", "MemoryLedger"),
        lines=125,
    ),
    ComponentSpec(
        path="mira_core/safety.py",
        module="mira_core.safety",
        class_names=("SafetyViolation", "SafetyPolicy", "SafetyMonitor"),
        lines=73,
    ),
    ComponentSpec(
        path="mira_core/contracts.py",
        module="mira_core.contracts",
        class_names=("Contract", "ParameterContract", "ReturnContract",
                      "StateContract", "InvariantContract", "DigestContract"),
        lines=76,
    ),
)


# ── Measurable insufficiency patterns ────────────────────────────────

@dataclass(frozen=True)
class InsufficiencyPattern:
    """A detectable code pattern that indicates a missing capability."""

    name: str
    description: str
    source_indicator: str  # substring/pattern in source
    severity: int          # higher = more impactful

    def digest(self) -> str:
        return _digest({
            "name": self.name,
            "description": self.description,
            "severity": self.severity,
        })


KNOWN_PATTERNS: tuple[InsufficiencyPattern, ...] = (
    InsufficiencyPattern(
        name="missing_query_method",
        description=(
            "Component exposes a collection but no declarative query method. "
            "Consumers must manually filter, increasing coupling and error risk."
        ),
        source_indicator="event.kind",
        severity=3,
    ),
    InsufficiencyPattern(
        name="missing_validation_method",
        description=(
            "Component accepts state mutations without a dedicated validation method. "
            "Callers must inline validation logic."
        ),
        source_indicator="if not",
        severity=2,
    ),
    InsufficiencyPattern(
        name="missing_factory_or_default",
        description=(
            "Component construction requires explicit parameter passing with no "
            "sensible default or factory method."
        ),
        source_indicator="__init__",
        severity=1,
    ),
)


# ── Diagnostic result ────────────────────────────────────────────────

@dataclass(frozen=True)
class ComponentObservation:
    """Observations about one component's source code."""

    component: ComponentSpec
    source_digest: str
    matched_patterns: tuple[tuple[InsufficiencyPattern, int], ...]  # (pattern, occurrence_count)
    total_severity_score: int

    def digest(self) -> str:
        return _digest({
            "component_digest": self.component.digest(),
            "source_digest": self.source_digest,
            "matched_patterns": [
                {"pattern": p.name, "occurrences": c}
                for p, c in self.matched_patterns
            ],
        })


@dataclass(frozen=True)
class DiagnosticHypothesis:
    """A hypothesis that a specific component is the most constrained.

    Must be falsifiable: another hypothesis must exist that could have
    been chosen instead.
    """

    selected_component: ComponentSpec
    observations: tuple[ComponentObservation, ...]
    justification: str
    rejected_alternatives: tuple[tuple[ComponentSpec, str], ...]  # (component, reason)

    def digest(self) -> str:
        return _digest({
            "selected": self.selected_component.path,
            "observations": [o.digest() for o in self.observations],
            "rejected": [(c.path, r) for c, r in self.rejected_alternatives],
        })


# ── Discovery engine ─────────────────────────────────────────────────

def inspect_all(repo_root: Path) -> tuple[ComponentObservation, ...]:
    """Inspect every eligible component and return observations."""

    observations: list[ComponentObservation] = []

    for spec in ELIGIBLE_COMPONENTS:
        source_path = repo_root / spec.path
        source = source_path.read_text(encoding="utf-8")
        source_digest = hashlib.sha256(source.encode("utf-8")).hexdigest()

        matched: list[tuple[InsufficiencyPattern, int]] = []
        for pattern in KNOWN_PATTERNS:
            count = source.count(pattern.source_indicator)
            if count > 0:
                matched.append((pattern, count))

        total_severity = sum(p.severity * c for p, c in matched)

        observations.append(ComponentObservation(
            component=spec,
            source_digest=source_digest,
            matched_patterns=tuple(matched),
            total_severity_score=total_severity,
        ))

    return tuple(observations)


def diagnose(observations: tuple[ComponentObservation, ...]) -> DiagnosticHypothesis:
    """Select the most constrained component from observations.

    The selection rule is frozen and falsifiable: pick the component with
    the highest total_severity_score. Ties are broken by most patterns matched.
    """

    if not observations:
        raise ValueError("no observations to diagnose")

    sorted_obs = sorted(
        observations,
        key=lambda o: (-o.total_severity_score, -len(o.matched_patterns)),
    )

    selected = sorted_obs[0]
    rejected: list[tuple[ComponentSpec, str]] = []

    for obs in sorted_obs[1:]:
        if obs.total_severity_score < selected.total_severity_score:
            reason = (
                f"lower total severity ({obs.total_severity_score} vs "
                f"{selected.total_severity_score})"
            )
        elif len(obs.matched_patterns) < len(selected.matched_patterns):
            reason = (
                f"fewer insufficiency patterns ({len(obs.matched_patterns)} vs "
                f"{len(selected.matched_patterns)})"
            )
        else:
            reason = f"tie-break: ordered after {selected.component.path}"
        rejected.append((obs.component, reason))

    # Build human-readable justification
    parts: list[str] = []
    parts.append(
        f"Selected {selected.component.path}: "
        f"severity score {selected.total_severity_score}, "
        f"{len(selected.matched_patterns)} pattern(s) matched"
    )
    for pattern, count in selected.matched_patterns:
        parts.append(f"  - '{pattern.name}': {count} occurrence(s)")
    parts.append(f"Rejected {len(rejected)} alternative(s):")
    for comp, reason in rejected:
        parts.append(f"  - {comp.path}: {reason}")

    return DiagnosticHypothesis(
        selected_component=selected.component,
        observations=observations,
        justification="\n".join(parts),
        rejected_alternatives=tuple(rejected),
    )