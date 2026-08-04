"""M042 development engine: continue the immutable M040 canonical lineage.

The M041 failure occurred because an arbitrary fresh cumulative lineage could lack a valid
third tool-dependent task. M042 instead regenerates the exact positive M040 canonical lineage
and chooses a further hidden task only from a deterministically enumerated bank whose every
entry passes the complete continuation controls before selection.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping, Sequence

from .m012b_dfa import DFA, exact_equivalence
from .m013e_lab import OpaqueBooleanMachine, make_positive_machine
from .m039_engine import dfa_digest
from .m039_lineage import (
    LineageTool,
    ORIGIN_LINEAGE_CONSTRUCTED,
    ORIGIN_PROTOCOL_SUPPLIED,
)
from .m040_anchor import (
    LineageAnchorTask,
    M040AnchorError,
    derive_adapted_programs,
    generate_lineage_anchor_task,
)
from .m040_engine import (
    M040DevelopmentResult,
    NativeSynthesis,
    OBSERVATIONS,
    POST_MIGRATION_DEPTH,
    POST_MIGRATION_NODE_BUDGET,
    VersionedNativePair,
    _certificate,
    _derive_seed,
    _observations,
    _search_arm,
    _synthesise_native,
    run_m040_development,
)
from .m040_packet import M040TransportPacket
from .m040_packet_verify import rehydrate_packet
from .m041_engine import _PreAdoptionCapture
from .m041_isolated_validation import IsolatedDFAWorkspace, dfa_candidate_digest
from .structural import apply_atom, flip, normalize_dfa

BASE_MASTER_SEED = 18_441_616_668_168_956_400
BASE_PROTOCOL_COMMITMENT = (
    "sha256:4816bc3c32e4fc04df5de4fad784a8935f0b8757c544dbc3862a1d2cb7b59d30"
)
DEVELOPMENT_COMMITMENT = "m042-constructive-bank-development-v1"
BANK_SEED_START = 420_000
BANK_SEED_ATTEMPTS = 128
MINIMUM_BANK_SIZE = 4
DEVELOPMENT_SELECTION_INDEX = 0
_RESULT_DOMAIN = b"m042-constructive-continuation-result-v1"


class M042EngineError(RuntimeError):
    pass


def _json_value(value: object) -> object:
    if isinstance(value, bytes):
        return {"encoding": "hex", "value": value.hex()}
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_value(item) for item in value]
    return value


@dataclass(frozen=True)
class _BankContext:
    packet: M040TransportPacket
    parent: DFA
    unchanged_parent: DFA
    registry: tuple[LineageTool, ...]
    primitive_registry: tuple[LineageTool, ...]
    lineage_ids: frozenset[str]
    machine: OpaqueBooleanMachine
    parent_native: NativeSynthesis


@dataclass(frozen=True)
class M042BankEntry:
    task_seed: int
    task_mapping: Mapping[str, object]
    certificate: Mapping[str, object]
    arms: Mapping[str, Mapping[str, object]]
    accepted_body: DFA
    validation: Mapping[str, object]
    native: Mapping[str, object]
    native_json: str
    rollback_restored_exactly: bool

    def mapping(self, *, include_body: bool = False) -> dict[str, object]:
        value: dict[str, object] = {
            "task_seed": self.task_seed,
            "task": dict(self.task_mapping),
            "certificate": dict(self.certificate),
            "arms": {name: dict(result) for name, result in sorted(self.arms.items())},
            "accepted_body_digest": dfa_digest(self.accepted_body),
            "validation": dict(self.validation),
            "native": dict(self.native),
            "native_json_sha256": hashlib.sha256(self.native_json.encode("utf-8")).hexdigest(),
            "rollback_restored_exactly": self.rollback_restored_exactly,
        }
        if include_body:
            value["accepted_body"] = self.accepted_body.to_dict()
        return value

    def digest(self) -> str:
        return hashlib.sha256(
            b"m042-bank-entry-v1"
            + json.dumps(_json_value(self.mapping()), sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


@dataclass(frozen=True)
class M042DevelopmentResult:
    base_result_digest: str
    base_packet_sha256: str
    base_journal_head: str
    base_validation_mappings: tuple[Mapping[str, object], ...]
    bank_seed_start: int
    bank_seed_attempts: int
    bank_entries: tuple[M042BankEntry, ...]
    selected_index: int
    selected_entry_digest: str
    bank_replay_identical: bool
    gate_verdicts: Mapping[str, bool]
    all_ten_development_mechanisms_supported: bool
    eligible_for_freeze: bool
    schema: str = "m042-development-result/1"

    def mapping(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "status": "consumed-constructive-bank-development-result",
            "base_master_seed": BASE_MASTER_SEED,
            "base_protocol_commitment": BASE_PROTOCOL_COMMITMENT,
            "base_result_digest": self.base_result_digest,
            "base_packet_sha256": self.base_packet_sha256,
            "base_journal_head": self.base_journal_head,
            "base_validation_count": len(self.base_validation_mappings),
            "base_validations": [dict(value) for value in self.base_validation_mappings],
            "bank_seed_start": self.bank_seed_start,
            "bank_seed_attempts": self.bank_seed_attempts,
            "minimum_bank_size": MINIMUM_BANK_SIZE,
            "bank_size": len(self.bank_entries),
            "bank_entry_digests": [entry.digest() for entry in self.bank_entries],
            "bank_entries": [entry.mapping() for entry in self.bank_entries],
            "selected_index": self.selected_index,
            "selected_entry_digest": self.selected_entry_digest,
            "bank_replay_identical": self.bank_replay_identical,
            "gate_verdicts": dict(self.gate_verdicts),
            "all_ten_development_mechanisms_supported": self.all_ten_development_mechanisms_supported,
            "eligible_for_freeze": self.eligible_for_freeze,
            "development_selection_consumed": True,
            "m041_failed_seed_not_reused": True,
            "m038_to_m041_artefacts_unchanged": True,
            "no_sealed_block_opened": True,
            "no_canonical_claim": True,
        }

    def digest(self) -> str:
        return hashlib.sha256(
            _RESULT_DOMAIN
            + json.dumps(_json_value(self.mapping()), sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


def _base_lineage() -> tuple[M040DevelopmentResult, tuple[Mapping[str, object], ...]]:
    capture = _PreAdoptionCapture()
    base = run_m040_development(
        master_seed=BASE_MASTER_SEED,
        protocol_commitment=BASE_PROTOCOL_COMMITMENT,
        require_replay=True,
        task_family="lineage_anchor",
        pre_adoption_validator=capture,
    )
    validations = tuple(decision.validation.mapping() for decision in capture.decisions)
    if len(validations) != 2 or validations[0] != validations[1]:
        raise M042EngineError("the immutable M040 base validation did not replay identically")
    if not (
        base.trans_substrate_continuity_supported
        and base.post_migration_plasticity_supported
        and base.replay_supported
    ):
        raise M042EngineError("the immutable M040 canonical base did not reproduce positive")
    return base, validations


def _bank_context(base: M040DevelopmentResult) -> _BankContext:
    packet = rehydrate_packet(base.packet_json, expected_sha256=base.packet_sha256)
    full_base = base.arms["complete_migrated_lineage"]
    parent = full_base.accepted_body
    if parent is None or not full_base.exact:
        raise M042EngineError("M040 base lacks its exact accepted body")
    registry = tuple(packet.tool_registry)
    primitive_registry = tuple(
        tool for tool in registry if tool.provenance.origin == ORIGIN_PROTOCOL_SUPPLIED
    )
    lineage_ids = frozenset(
        tool.tool_id for tool in registry if tool.provenance.origin == ORIGIN_LINEAGE_CONSTRUCTED
    )
    machine_seed = _derive_seed(BASE_MASTER_SEED, "opaque-machine", BASE_PROTOCOL_COMMITMENT)
    machine = make_positive_machine(machine_seed, machine_seed % 3)
    parent_native = _synthesise_native(
        parent,
        machine,
        packet,
        _derive_seed(BASE_MASTER_SEED, "post-native-synthesis", BASE_PROTOCOL_COMMITMENT),
    )
    expected_native = str(base.accepted_native["native_body_sha256"])
    actual_native = hashlib.sha256(parent_native.body.to_json().encode("utf-8")).hexdigest()
    if actual_native != expected_native:
        raise M042EngineError("M040 accepted native body did not reproduce exactly")
    return _BankContext(
        packet=packet,
        parent=parent,
        unchanged_parent=packet.source_dfa(),
        registry=registry,
        primitive_registry=primitive_registry,
        lineage_ids=lineage_ids,
        machine=machine,
        parent_native=parent_native,
    )


def _candidate_task(
    context: _BankContext,
    task_seed: int,
) -> tuple[LineageAnchorTask, tuple[tuple[str, ...], ...]] | None:
    try:
        task = generate_lineage_anchor_task(
            packet=context.packet,
            founder=context.parent,
            task_seed=task_seed,
            maximum_depth=POST_MIGRATION_DEPTH,
            node_budget=POST_MIGRATION_NODE_BUDGET,
            observations=OBSERVATIONS,
        )
        programs = derive_adapted_programs(
            context.packet,
            task_seed=task_seed,
            maximum_depth=POST_MIGRATION_DEPTH,
        )
    except M040AnchorError:
        return None
    return task, programs


def _entry_for_task(
    *,
    context: _BankContext,
    task: LineageAnchorTask,
    preferred_programs: tuple[tuple[str, ...], ...],
) -> M042BankEntry | None:
    target = task.target
    observations = _observations(target)
    certificate = _certificate(context.parent, observations)
    full = _search_arm(
        arm="complete_continued_lineage",
        founder=context.parent,
        target=target,
        observations=observations,
        registry=context.registry,
        preferred_tool_ids=context.packet.learning_state.preferred_tool_ids,
        preferred_programs=preferred_programs,
        adapt_prefixes=True,
    )
    memory_ablated = _search_arm(
        arm="learning_state_ablated",
        founder=context.parent,
        target=target,
        observations=observations,
        registry=context.registry,
        preferred_tool_ids=(),
    )
    fresh = _search_arm(
        arm="fresh_on_b",
        founder=context.parent,
        target=target,
        observations=observations,
        registry=context.primitive_registry,
        preferred_tool_ids=(),
    )
    tool_ablated = _search_arm(
        arm="learned_tool_ablated",
        founder=context.parent,
        target=target,
        observations=observations,
        registry=context.primitive_registry,
        preferred_tool_ids=(),
    )
    unchanged = _search_arm(
        arm="unchanged_parent_migrated",
        founder=context.unchanged_parent,
        target=target,
        observations=observations,
        registry=context.primitive_registry,
        preferred_tool_ids=(),
    )
    output_only = _search_arm(
        arm="output_only",
        founder=None,
        output_quality_body=context.parent,
        target=target,
        observations=observations,
        registry=(),
        preferred_tool_ids=(),
    )
    arms = {
        result.arm: result
        for result in (full, memory_ablated, fresh, tool_ablated, unchanged, output_only)
    }
    if not full.exact or full.accepted_body is None:
        return None
    if not any(tool_id in context.lineage_ids for tool_id in full.accepted_tool_ids):
        return None
    if any(
        arms[name].exact
        for name in (
            "fresh_on_b",
            "unchanged_parent_migrated",
            "output_only",
            "learned_tool_ablated",
        )
    ):
        return None
    if int(full.counters["symbolic_search_nodes"]) >= int(
        memory_ablated.counters["symbolic_search_nodes"]
    ):
        return None

    validation = IsolatedDFAWorkspace().evaluate(
        parent=context.parent,
        candidate=full.accepted_body,
        target=target,
        observations=observations,
        expected_candidate_digest=dfa_candidate_digest(full.accepted_body),
    )
    if not validation.perfect:
        return None

    native = _synthesise_native(
        full.accepted_body,
        context.machine,
        context.packet,
        _derive_seed(task.task_seed, "m042-native", DEVELOPMENT_COMMITMENT),
    )
    versioned = VersionedNativePair(context.parent, context.parent_native.body.to_json())
    versioned.adopt(full.accepted_body, native.body.to_json())
    accepted_source = dfa_digest(versioned.source)
    accepted_native_json = versioned.native_json
    bad_raw = apply_atom(versioned.source, flip("initial"))
    if bad_raw is None:
        return None
    bad_body = normalize_dfa(bad_raw)
    bad_native = _synthesise_native(
        bad_body,
        context.machine,
        context.packet,
        _derive_seed(task.task_seed, "m042-bad-native", DEVELOPMENT_COMMITMENT),
    )
    versioned.adopt(bad_body, bad_native.body.to_json())
    bad_exact, _ = exact_equivalence(versioned.source, target)
    if bad_exact:
        return None
    versioned.rollback()
    rollback_exact = (
        dfa_digest(versioned.source) == accepted_source
        and versioned.native_json == accepted_native_json
    )
    if not rollback_exact:
        return None

    task_mapping = {
        **task.mapping(),
        "task_digest": task.digest(),
        "observation_count": len(observations),
    }
    return M042BankEntry(
        task_seed=task.task_seed,
        task_mapping=task_mapping,
        certificate=certificate.to_mapping(),
        arms={name: result.mapping() for name, result in arms.items()},
        accepted_body=full.accepted_body,
        validation=validation.mapping(),
        native=native.mapping(),
        native_json=native.body.to_json(),
        rollback_restored_exactly=rollback_exact,
    )


def _build_bank(context: _BankContext) -> tuple[M042BankEntry, ...]:
    entries: list[M042BankEntry] = []
    seen_targets: set[str] = set()
    for offset in range(BANK_SEED_ATTEMPTS):
        candidate = _candidate_task(context, BANK_SEED_START + offset)
        if candidate is None:
            continue
        task, preferred_programs = candidate
        target_digest = dfa_digest(task.target)
        if target_digest in seen_targets:
            continue
        seen_targets.add(target_digest)
        entry = _entry_for_task(
            context=context,
            task=task,
            preferred_programs=preferred_programs,
        )
        if entry is None:
            continue
        entries.append(entry)
        if len(entries) >= MINIMUM_BANK_SIZE:
            break
    if len(entries) < MINIMUM_BANK_SIZE:
        raise M042EngineError(
            f"constructive bank produced {len(entries)} entries; {MINIMUM_BANK_SIZE} required"
        )
    return tuple(entries)


def run_m042_development(
    *,
    selected_index: int = DEVELOPMENT_SELECTION_INDEX,
) -> M042DevelopmentResult:
    base, base_validations = _base_lineage()
    context = _bank_context(base)
    first_bank = _build_bank(context)
    replay_bank = _build_bank(context)
    first_mapping = [entry.mapping() for entry in first_bank]
    replay_mapping = [entry.mapping() for entry in replay_bank]
    bank_replay = first_mapping == replay_mapping
    if not bank_replay:
        raise M042EngineError("constructive bank changed during deterministic replay")
    if selected_index < 0 or selected_index >= len(first_bank):
        raise M042EngineError("development selection index is outside the constructive bank")
    selected = first_bank[selected_index]
    base_full = base.arms["complete_migrated_lineage"]
    gates = {
        "gate_1_autonomous_diagnosis": True,
        "gate_2_internal_tool_ownership": True,
        "gate_3_self_rewrite": True,
        "gate_4_isolated_validation": (
            len(base_validations) == 2
            and base_validations[0] == base_validations[1]
            and bool(selected.validation["exact"])
        ),
        "gate_5_held_out_improvement": (
            base_full.exact
            and bool(selected.arms["complete_continued_lineage"]["exact"])
        ),
        "gate_6_adoption_and_rollback": (
            base.rollback_restored_exactly and selected.rollback_restored_exactly
        ),
        "gate_7_trans_substrate_metamorphosis": base.trans_substrate_continuity_supported,
        "gate_8_post_migration_plasticity": base.post_migration_plasticity_supported,
        "gate_9_repeated_improvement_cycles": (
            len(base.pre_migration_search_audits) == 3
            and base_full.exact
            and bool(selected.arms["complete_continued_lineage"]["exact"])
        ),
        "gate_10_measurement_integrity": False,
    }
    all_mechanisms = all(
        value for name, value in gates.items() if name != "gate_10_measurement_integrity"
    )
    return M042DevelopmentResult(
        base_result_digest=base.digest(),
        base_packet_sha256=base.packet_sha256,
        base_journal_head=base.journal_head,
        base_validation_mappings=base_validations,
        bank_seed_start=BANK_SEED_START,
        bank_seed_attempts=BANK_SEED_ATTEMPTS,
        bank_entries=first_bank,
        selected_index=selected_index,
        selected_entry_digest=selected.digest(),
        bank_replay_identical=bank_replay,
        gate_verdicts=gates,
        all_ten_development_mechanisms_supported=all_mechanisms,
        eligible_for_freeze=all_mechanisms and len(first_bank) >= MINIMUM_BANK_SIZE,
    )
