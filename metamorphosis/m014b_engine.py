from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Iterable, Mapping, Protocol, Sequence

from .m012b_dfa import DFA
from .m013e_engine import MigrationCertificate, UnknownSubstrateMigrator
from .m013e_runtime import OpaqueNativeBody
from .m014b_confirmation import ConformanceConfirmation, confirm_candidate
from .m014b_policy import (
    BehavioralOracle,
    EditHypothesis,
    PlasticityPassport,
    UpdateInference,
    identify_update,
)


class OpaqueMachine(Protocol):
    def describe(self) -> Sequence[object]: ...

    def probe(self, opcode: str, inputs: Iterable[int]) -> int: ...

    def execute(self, opcode: str, inputs: Iterable[int]) -> int: ...


@dataclass(frozen=True)
class PortablePlasticityCertificate:
    status: str
    reason: str
    inherited_passport: DFA
    updated_passport: DFA | None
    old_body: OpaqueNativeBody | None
    new_body: OpaqueNativeBody | None
    old_migration: MigrationCertificate
    new_migration: MigrationCertificate | None
    inference: UpdateInference | None
    confirmation: ConformanceConfirmation | None
    total_update_oracle_calls: int
    plasticity_passport_sha256: str
    plasticity_round_trip_exact: bool
    old_body_sha256_before: str | None
    old_body_sha256_after: str | None
    old_body_bit_exact: bool
    consolidation_record_sha256: str | None
    trace: Mapping[str, object]


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _consolidation_digest(
    hypothesis: EditHypothesis,
    inference: UpdateInference,
    confirmation: ConformanceConfirmation,
) -> str:
    payload = {
        "selected_hypothesis": hypothesis.to_dict(),
        "raw_oracle_calls": inference.raw_oracle_calls,
        "unique_queries": inference.unique_queries,
        "initial_candidates": inference.initial_candidates,
        "remaining_candidates": inference.remaining_candidates,
        "query_trace": list(inference.query_trace),
        "confirmation_reason": confirmation.reason,
        "confirmation_raw_calls": confirmation.raw_oracle_calls,
        "confirmation_words": [list(word) for word in confirmation.checked_words],
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


class PortablePlasticityEngine:
    """Continue learning after unknown-substrate migration without a target DFA."""

    def __init__(
        self,
        *,
        query_budget: int = 192,
        migrator: UnknownSubstrateMigrator | None = None,
    ) -> None:
        self.query_budget = query_budget
        self.migrator = migrator or UnknownSubstrateMigrator(
            native_component_budget=360,
        )

    def adapt(
        self,
        inherited_passport: DFA,
        machine: OpaqueMachine,
        plasticity_passport_json: str,
        behavioral_oracle: BehavioralOracle,
        search_seed: int,
        trace: Mapping[str, object] | None = None,
        *,
        policy_override: str | None = None,
    ) -> PortablePlasticityCertificate:
        base_trace = dict(trace or {})
        plasticity = PlasticityPassport.from_json(plasticity_passport_json)
        restored_json = plasticity.to_json()
        plasticity_hash = _sha256_text(plasticity_passport_json)
        plasticity_round_trip = restored_json == plasticity_passport_json

        old_migration = self.migrator.migrate(
            inherited_passport,
            machine,
            search_seed,
            base_trace,
        )
        old_body = old_migration.body
        if old_migration.status != "success" or old_body is None:
            return PortablePlasticityCertificate(
                "failed",
                "inherited_competence_could_not_migrate",
                inherited_passport,
                None,
                old_body,
                None,
                old_migration,
                None,
                None,
                None,
                0,
                plasticity_hash,
                plasticity_round_trip,
                None,
                None,
                False,
                None,
                base_trace,
            )

        archived_old_json = old_body.to_json()
        archived_old_hash = _sha256_text(archived_old_json)
        inference = identify_update(
            inherited_passport,
            behavioral_oracle,
            plasticity,
            query_budget=self.query_budget,
            policy=policy_override,
            search_seed=search_seed ^ 0x14B0_14B0,
        )
        old_after_json = old_body.to_json()
        old_after_hash = _sha256_text(old_after_json)
        old_bit_exact = archived_old_json == old_after_json

        if inference.status != "success" or inference.updated_passport is None:
            return PortablePlasticityCertificate(
                "abstained",
                inference.reason,
                inherited_passport,
                None,
                old_body,
                None,
                old_migration,
                None,
                inference,
                None,
                inference.raw_oracle_calls,
                plasticity_hash,
                plasticity_round_trip,
                archived_old_hash,
                old_after_hash,
                old_bit_exact,
                None,
                base_trace,
            )

        asked = {
            tuple(int(value) for value in row["word"])
            for row in inference.query_trace
            if isinstance(row.get("word"), list)
        }
        confirmation = confirm_candidate(
            inference.updated_passport,
            behavioral_oracle,
            already_asked=asked,
            raw_budget=max(0, self.query_budget - inference.raw_oracle_calls),
            repetitions=plasticity.repeat_queries,
            max_length=5,
        )
        total_update_calls = inference.raw_oracle_calls + confirmation.raw_oracle_calls
        old_after_json = old_body.to_json()
        old_after_hash = _sha256_text(old_after_json)
        old_bit_exact = archived_old_json == old_after_json
        if confirmation.status != "confirmed":
            return PortablePlasticityCertificate(
                "abstained",
                confirmation.reason,
                inherited_passport,
                None,
                old_body,
                None,
                old_migration,
                None,
                inference,
                confirmation,
                total_update_calls,
                plasticity_hash,
                plasticity_round_trip,
                archived_old_hash,
                old_after_hash,
                old_bit_exact,
                None,
                base_trace,
            )

        new_migration = self.migrator.migrate(
            inference.updated_passport,
            machine,
            search_seed ^ 0x5EED_14B0,
            base_trace,
            supplied_substrate=old_migration.substrate,
        )
        old_after_json = old_body.to_json()
        old_after_hash = _sha256_text(old_after_json)
        old_bit_exact = archived_old_json == old_after_json
        if new_migration.status != "success" or new_migration.body is None:
            return PortablePlasticityCertificate(
                "failed",
                "updated_native_body_construction_failed",
                inherited_passport,
                inference.updated_passport,
                old_body,
                None,
                old_migration,
                new_migration,
                inference,
                confirmation,
                total_update_calls,
                plasticity_hash,
                plasticity_round_trip,
                archived_old_hash,
                old_after_hash,
                old_bit_exact,
                None,
                base_trace,
            )

        assert inference.selected_hypothesis is not None
        consolidation_digest = _consolidation_digest(
            inference.selected_hypothesis,
            inference,
            confirmation,
        )
        return PortablePlasticityCertificate(
            "success",
            "portable_plasticity_chain_completed",
            inherited_passport,
            inference.updated_passport,
            old_body,
            new_migration.body,
            old_migration,
            new_migration,
            inference,
            confirmation,
            total_update_calls,
            plasticity_hash,
            plasticity_round_trip,
            archived_old_hash,
            old_after_hash,
            old_bit_exact,
            consolidation_digest,
            base_trace,
        )
