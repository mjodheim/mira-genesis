"""M041 development integration: M040 lineage plus pre-adoption isolated validation."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping

from .m038_certificate import STATUS_AVAILABLE
from .m040_engine import (
    DEVELOPMENT_COMMITMENT as M040_DEVELOPMENT_COMMITMENT,
    DEVELOPMENT_SEED as M040_DEVELOPMENT_SEED,
    M040DevelopmentResult,
    M040EngineError,
    OBSERVATIONS,
    run_m040_development,
)
from .m040_packet_verify import rehydrate_packet
from .m041_isolated_validation import (
    IsolatedAdoptionDecision,
    IsolatedDFAAdoptionGate,
    IsolatedDFAValidation,
    VersionedDFARelease,
    dfa_candidate_digest,
)
from .m012b_dfa import DFA

Word = tuple[int, ...]
DEVELOPMENT_SEED = M040_DEVELOPMENT_SEED
BASE_PROTOCOL_COMMITMENT = M040_DEVELOPMENT_COMMITMENT
M041_PROTOCOL_COMMITMENT = "m041-isolated-completion-development-v1"
_RESULT_DOMAIN = b"m041-completion-audit-result-v1"


class M041EngineError(RuntimeError):
    pass


class _PreAdoptionCapture:
    def __init__(self, gate: IsolatedDFAAdoptionGate | None = None) -> None:
        self.gate = gate or IsolatedDFAAdoptionGate()
        self.decisions: list[IsolatedAdoptionDecision] = []

    def __call__(
        self,
        parent: DFA,
        candidate: DFA,
        target: DFA,
        observations: Mapping[Word, bool],
    ) -> None:
        release = VersionedDFARelease(parent)
        decision = self.gate.evaluate_and_adopt(
            release=release,
            expected_parent_digest=dfa_candidate_digest(parent),
            candidate=candidate,
            target=target,
            observations=observations,
            expected_candidate_digest=dfa_candidate_digest(candidate),
        )
        self.decisions.append(decision)
        if not decision.adopted or not decision.validation.perfect:
            raise M040EngineError("M041 isolated validation rejected the post-migration proposal")
        if release.active != candidate or release.archive != [parent]:
            raise M040EngineError("M041 release adoption did not preserve the parent archive")


@dataclass(frozen=True)
class M041DevelopmentResult:
    master_seed: int
    base_protocol_commitment: str
    m041_protocol_commitment: str
    base_result_digest: str
    base_packet_sha256: str
    base_journal_head: str
    validations: tuple[IsolatedDFAValidation, ...]
    gate_verdicts: Mapping[str, bool]
    gates_one_to_nine_supported: bool
    eligible_for_freeze: bool
    schema: str = "m041-development-result/1"

    def mapping(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "status": "consumed-development-integration-result",
            "master_seed": self.master_seed,
            "base_protocol_commitment": self.base_protocol_commitment,
            "m041_protocol_commitment": self.m041_protocol_commitment,
            "base_result_digest": self.base_result_digest,
            "base_packet_sha256": self.base_packet_sha256,
            "base_journal_head": self.base_journal_head,
            "isolated_validation_count": len(self.validations),
            "isolated_validations": [validation.mapping() for validation in self.validations],
            "isolated_replay_byte_identical": (
                len(self.validations) == 2
                and self.validations[0].mapping() == self.validations[1].mapping()
            ),
            "gate_verdicts": dict(self.gate_verdicts),
            "gates_one_to_nine_supported": self.gates_one_to_nine_supported,
            "eligible_for_freeze": self.eligible_for_freeze,
            "gate_ten_requires_canonical_run": True,
            "development_seed_consumed": True,
            "reuses_consumed_m040_development_input": True,
            "m040_canonical_artefact_unchanged": True,
            "no_sealed_block_opened": True,
            "no_canonical_claim": True,
        }

    def digest(self) -> str:
        return hashlib.sha256(
            _RESULT_DOMAIN
            + json.dumps(
                self.mapping(),
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()


def _gate_verdicts(
    base: M040DevelopmentResult,
    validations: tuple[IsolatedDFAValidation, ...],
) -> dict[str, bool]:
    full = base.arms["complete_migrated_lineage"]
    packet = rehydrate_packet(base.packet_json, expected_sha256=base.packet_sha256)
    parent = packet.source_dfa()
    certificate = base.certificate
    controls_non_exact = all(
        not base.arms[name].exact
        for name in (
            "fresh_on_b",
            "unchanged_parent_migrated",
            "output_only",
            "learned_tool_ablated",
        )
    )
    isolation = (
        len(validations) == 2
        and all(validation.perfect for validation in validations)
        and validations[0].mapping() == validations[1].mapping()
    )
    return {
        "gate_1_autonomous_diagnosis": (
            str(certificate["certificate_status"]) == STATUS_AVAILABLE
            and int(certificate["certified_lower_bound"])
            > int(certificate["body_state_count"])
        ),
        "gate_2_internal_tool_ownership": base.accepted_tool_was_pre_migration_owned,
        "gate_3_self_rewrite": (
            full.exact
            and full.accepted_body is not None
            and dfa_candidate_digest(full.accepted_body) != dfa_candidate_digest(parent)
        ),
        "gate_4_isolated_validation": isolation,
        "gate_5_held_out_improvement": (
            full.exact
            and controls_non_exact
            and int(full.counters["symbolic_search_nodes"])
            < int(base.arms["learning_state_ablated"].counters["symbolic_search_nodes"])
        ),
        "gate_6_adoption_and_rollback": base.rollback_restored_exactly,
        "gate_7_trans_substrate_metamorphosis": base.trans_substrate_continuity_supported,
        "gate_8_post_migration_plasticity": base.post_migration_plasticity_supported,
        "gate_9_repeated_improvement_cycles": (
            len(base.pre_migration_search_audits) == 3
            and base.accepted_tool_was_pre_migration_owned
            and full.exact
        ),
        "gate_10_measurement_integrity": False,
    }


def run_m041_development(
    *,
    master_seed: int = DEVELOPMENT_SEED,
    base_protocol_commitment: str = BASE_PROTOCOL_COMMITMENT,
    m041_protocol_commitment: str = M041_PROTOCOL_COMMITMENT,
) -> M041DevelopmentResult:
    capture = _PreAdoptionCapture()
    base = run_m040_development(
        master_seed=master_seed,
        protocol_commitment=base_protocol_commitment,
        require_replay=True,
        task_family="lineage_anchor",
        pre_adoption_validator=capture,
    )
    validations = tuple(decision.validation for decision in capture.decisions)
    if len(validations) != 2:
        raise M041EngineError("M041 expected one isolated validation per seed-only execution")
    if validations[0].mapping() != validations[1].mapping():
        raise M041EngineError("M041 isolated validation changed during seed-only replay")
    verdicts = _gate_verdicts(base, validations)
    gates_one_to_nine = all(
        verdict
        for name, verdict in verdicts.items()
        if name != "gate_10_measurement_integrity"
    )
    return M041DevelopmentResult(
        master_seed=master_seed,
        base_protocol_commitment=base_protocol_commitment,
        m041_protocol_commitment=m041_protocol_commitment,
        base_result_digest=base.digest(),
        base_packet_sha256=base.packet_sha256,
        base_journal_head=base.journal_head,
        validations=validations,
        gate_verdicts=verdicts,
        gates_one_to_nine_supported=gates_one_to_nine,
        eligible_for_freeze=gates_one_to_nine and not verdicts["gate_10_measurement_integrity"],
    )
