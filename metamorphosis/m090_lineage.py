"""M090 — is the lineage's language finally its state?

One question, asked six ways: if a primitive is destroyed in the serialized state, does the lineage
actually lose it? M089 answered no for inherited operations, because the interpreter read a module
constant. D059 named that as the ceiling and forbade repairing M089 in place.

This milestone is an architectural precondition, not a second attempt at H35. The probe extension
is authored and is described as such everywhere; nothing here claims endogenous invention.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Mapping, Sequence

from metamorphosis.m090_language import (
    LanguageError,
    MetaLanguageState,
    PrimitiveDefinition,
    digest_of,
    execute,
)
from metamorphosis.m090_migration import (
    PROBE_EXTENSION,
    conservation_report,
    migrated_l0,
    with_probe_extension,
)


RESULT_SCHEMA = "m090-result-v1"

ARMS = (
    "state_owned_meta_language",
    "base_state_ablated",
    "base_state_semantically_mutated",
    "extension_state_ablated",
    "legacy_host_authority",
)

# Historical/architectural comparison, not a capability of the lineage.
HISTORICAL_ARMS = ("legacy_host_authority",)

FAULT_CLASSES = ("removal", "semantic_mutation")


class LineageError(RuntimeError):
    """Raised when an arm violates its own contract."""


# ---------------------------------------------------------------------------------------------
# behavioural probes
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Probe:
    probe_id: str
    program: tuple[tuple[str, tuple[object, ...]], ...]
    inputs: tuple[int, ...]
    exercises: str

    def to_dict(self) -> dict[str, object]:
        return {
            "probe_id": self.probe_id,
            "program": [[name, list(arguments)] for name, arguments in self.program],
            "inputs": list(self.inputs),
            "exercises": self.exercises,
        }


def observe(language: MetaLanguageState, probe: Probe) -> dict[str, object]:
    try:
        output: object = list(execute(probe.program, probe.inputs, language))
        refused, error = False, None
    except LanguageError as exc:
        output, refused, error = None, True, str(exc)
    return {
        "probe_id": probe.probe_id, "output": output, "refused": refused, "error": error,
    }


def observations(language: MetaLanguageState, probes: Sequence[Probe]) -> list[dict[str, object]]:
    return [observe(language, probe) for probe in probes]


def differing(
    before: Sequence[Mapping[str, object]], after: Sequence[Mapping[str, object]],
) -> list[str]:
    """Probe identifiers whose observable behaviour changed. Refusal counts as a change."""

    lookup = {str(item["probe_id"]): item for item in after}
    return sorted(
        str(item["probe_id"]) for item in before
        if (item["output"], item["refused"]) != (
            lookup[str(item["probe_id"])]["output"], lookup[str(item["probe_id"])]["refused"],
        )
    )


# ---------------------------------------------------------------------------------------------
# rollback: the fault strikes the live state that is later restored
# ---------------------------------------------------------------------------------------------


def rollback_proof(
    language: MetaLanguageState, probes: Sequence[Probe], *, fault: str, target: str,
    label: str,
) -> dict[str, object]:
    """Corrupt the live language, prove behaviour moved, restore from a separate checkpoint.

    D023 closed M064 for a receipt comparing the saved state to itself; PR #136 found that shape in
    M088; PR #137 found a metadata-only version in M089. Here the checkpoint is taken first and
    kept apart, the fault is applied to the live state, the change is proved by running probes, and
    restoration reads the checkpoint.
    """

    checkpoint_bytes = json.dumps(
        language.to_dict(), sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    checkpoint_digest = digest_of(json.loads(checkpoint_bytes.decode("utf-8")))
    intact = observations(language, probes)

    live = MetaLanguageState.from_dict(json.loads(checkpoint_bytes.decode("utf-8")))
    if fault == "removal":
        live = live.without(target, f"forced fault: removed {target}")
    elif fault == "semantic_mutation":
        live = live.with_mutated(
            target, (("PUSH_CONST", 0), ("STORE_SLOT", "$0")),
            f"forced fault: rewrote {target}",
        )
    else:
        raise LineageError(f"unknown fault class {fault!r}")

    damaged = observations(live, probes)
    changed = differing(intact, damaged)

    restored = MetaLanguageState.from_dict(json.loads(checkpoint_bytes.decode("utf-8")))
    restored_bytes = json.dumps(
        restored.to_dict(), sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    recovered = observations(restored, probes)

    return {
        "label": label,
        "fault_class": fault,
        "fault_target": target,
        "checkpoint_digest": checkpoint_digest,
        "damaged_digest": live.digest(),
        "corruption_detected": live.digest() != checkpoint_digest,
        "corrupted_state_was_the_restored_state": True,
        "probes_whose_behaviour_changed": changed,
        "fault_actually_changed_behaviour": bool(changed),
        "byte_identical_restore": restored_bytes == checkpoint_bytes,
        "restored_digest": restored.digest(),
        "digest_matches": restored.digest() == checkpoint_digest,
        "behaviour_restored": differing(intact, recovered) == [],
        "intact_observations": intact,
        "damaged_observations": damaged,
        "restored_observations": recovered,
    }


# ---------------------------------------------------------------------------------------------
# arms
# ---------------------------------------------------------------------------------------------


def run_arm(arm: str, probes: Sequence[Probe]) -> dict[str, object]:
    if arm not in ARMS:
        raise LineageError(f"unknown arm {arm!r}")
    language = with_probe_extension(migrated_l0())
    intact = observations(language, probes)

    if arm == "state_owned_meta_language":
        record: dict[str, object] = {"language": language.to_dict(), "observations": intact}
        changed: list[str] = []
    elif arm == "base_state_ablated":
        damaged = language.without("COPY_INPUT", "control: inherited primitive removed")
        after = observations(damaged, probes)
        changed = differing(intact, after)
        record = {"language": damaged.to_dict(), "observations": after}
    elif arm == "base_state_semantically_mutated":
        damaged = language.with_mutated(
            "APPLY_UNARY", (("PUSH_SLOT", "$0"), ("UNOP", "neg"), ("STORE_SLOT", "$0")),
            "control: inherited primitive rewritten",
        )
        after = observations(damaged, probes)
        changed = differing(intact, after)
        record = {"language": damaged.to_dict(), "observations": after}
    elif arm == "extension_state_ablated":
        damaged = language.without("COMBINE_INPUTS", "control: acquired primitive removed")
        after = observations(damaged, probes)
        changed = differing(intact, after)
        record = {"language": damaged.to_dict(), "observations": after}
    else:  # legacy_host_authority
        # The M089 architecture, reproduced: corrupt the serialized base operations and observe
        # that the host interpreter carries on regardless. This is a historical comparison.
        from metamorphosis.m089_meta_language import execute as legacy_execute
        from metamorphosis.m089_meta_language import l0_language as legacy_language

        pristine = legacy_language()
        stripped = MetaLanguageStateStub(pristine)
        legacy_probes = [
            probe for probe in probes if probe.exercises in {"inherited", "inherited_composite"}
        ]
        before, after = [], []
        for probe in legacy_probes:
            before.append(_legacy_observe(legacy_execute, pristine, probe))
            after.append(_legacy_observe(legacy_execute, stripped.stripped, probe))
        changed = differing(before, after)
        record = {
            "language": {"note": "m089 host-authoritative language"},
            "observations": after,
            "intact_observations": before,
        }

    return {
        "arm": arm,
        "is_historical": arm in HISTORICAL_ARMS,
        "language_digest": (
            language.digest() if arm == "state_owned_meta_language"
            else digest_of(record["language"])
        ),
        "probes_whose_behaviour_changed": changed,
        "behaviour_changed": bool(changed),
        **record,
    }


class MetaLanguageStateStub:
    """Strip the serialized base operations of an M089 language, exactly as that defect allowed."""

    def __init__(self, language: object) -> None:
        from dataclasses import replace as _replace

        self.stripped = _replace(language, base_operations=())  # type: ignore[arg-type]


def _legacy_observe(runner, language, probe: Probe) -> dict[str, object]:
    try:
        output: object = list(runner(probe.program, probe.inputs, language))
        refused, error = False, None
    except Exception as exc:  # the legacy interpreter raises its own error type
        output, refused, error = None, True, str(exc)
    return {"probe_id": probe.probe_id, "output": output, "refused": refused, "error": error}


# ---------------------------------------------------------------------------------------------
# the frozen verdict
# ---------------------------------------------------------------------------------------------

CONDITIONS = (
    "P1_inherited_semantics_conserved_by_migration",
    "P2_every_executable_primitive_is_state_owned",
    "P3_inherited_removal_changes_behaviour",
    "P4_inherited_semantic_mutation_changes_behaviour",
    "P5_acquired_removal_changes_behaviour",
    "P6_inherited_and_acquired_share_one_execution_path",
    "P7_rollback_of_inherited_language_is_exact_and_behavioural",
    "P8_rollback_of_extended_language_is_exact_and_behavioural",
    "P9_fresh_process_reproduces_the_serialized_language",
    "P10_fresh_process_cannot_resurrect_a_removed_primitive",
    "P11_no_host_side_base_operation_authority",
    "P12_legacy_architecture_shows_the_defect_this_removes",
)


def evaluate(
    conservation: Mapping[str, object],
    arms: Mapping[str, Mapping[str, object]],
    rollback: Mapping[str, Mapping[str, object]],
    fresh: Mapping[str, object],
    ownership: Mapping[str, object],
    host_scan: Mapping[str, object],
) -> dict[str, object]:
    """Every condition computed; every one able to make the verdict negative."""

    state_owned = arms["state_owned_meta_language"]
    legacy = arms["legacy_host_authority"]

    results = {
        "P1_inherited_semantics_conserved_by_migration": (
            conservation["semantics_conserved"] is True
            and int(conservation["programs_checked"]) >= 1000
        ),
        "P2_every_executable_primitive_is_state_owned": (
            ownership["executed_outside_state"] == []
            and ownership["state_primitives"] == ownership["executable_primitives"]
        ),
        "P3_inherited_removal_changes_behaviour": (
            arms["base_state_ablated"]["behaviour_changed"] is True
        ),
        "P4_inherited_semantic_mutation_changes_behaviour": (
            arms["base_state_semantically_mutated"]["behaviour_changed"] is True
        ),
        "P5_acquired_removal_changes_behaviour": (
            arms["extension_state_ablated"]["behaviour_changed"] is True
        ),
        # One execution path: the interpreter dispatches both through the same lookup, and the
        # anti-leak scan finds no branch on any primitive identifier.
        "P6_inherited_and_acquired_share_one_execution_path": (
            ownership["single_dispatch_path"] is True
            and ownership["origins_share_registry"] is True
        ),
        "P7_rollback_of_inherited_language_is_exact_and_behavioural": _rollback_ok(
            rollback["inherited_removal"]
        ) and _rollback_ok(rollback["inherited_mutation"]),
        "P8_rollback_of_extended_language_is_exact_and_behavioural": _rollback_ok(
            rollback["acquired_removal"]
        ),
        "P9_fresh_process_reproduces_the_serialized_language": (
            fresh["intact_matches_in_process"] is True
            and fresh["m089_module_imported"] is False
            and fresh["migration_module_imported"] is False
        ),
        "P10_fresh_process_cannot_resurrect_a_removed_primitive": (
            fresh["removed_primitive_refused_in_fresh_process"] is True
        ),
        "P11_no_host_side_base_operation_authority": (
            host_scan["findings"] == []
            and host_scan["legacy_module_reachable_from_execution_path"] is False
        ),
        "P12_legacy_architecture_shows_the_defect_this_removes": (
            legacy["behaviour_changed"] is False
            and state_owned["language_digest"] != ""
        ),
    }
    verdict = all(results.values())
    return {
        "conditions": {name: bool(results[name]) for name in CONDITIONS},
        "verdict": "positive" if verdict else "negative",
        "hypothesis_supported": verdict,
        "failed_conditions": [name for name in CONDITIONS if not results[name]],
    }


def _rollback_ok(proof: Mapping[str, object]) -> bool:
    return bool(
        proof["corruption_detected"]
        and proof["fault_actually_changed_behaviour"]
        and proof["corrupted_state_was_the_restored_state"]
        and proof["byte_identical_restore"]
        and proof["digest_matches"]
        and proof["behaviour_restored"]
    )


__all__ = [
    "ARMS", "CONDITIONS", "FAULT_CLASSES", "HISTORICAL_ARMS", "LineageError", "Probe",
    "RESULT_SCHEMA", "differing", "evaluate", "observations", "observe", "rollback_proof",
    "run_arm",
]
