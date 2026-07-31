from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Iterable, Mapping, Protocol, Sequence

from .m012b_dfa import DFA
from .m013e_engine import MigrationCertificate, UnknownSubstrateMigrator
from .m013e_runtime import DiscoveredSubstrate, OpaqueNativeBody
from .m014c_meta import BehavioralOracle, MetaInference, MetaPlasticityPassport, MetaPlasticitySession


class OpaqueMachine(Protocol):
    def describe(self) -> Sequence[object]: ...
    def probe(self, opcode: str, inputs: Iterable[int]) -> int: ...
    def execute(self, opcode: str, inputs: Iterable[int]) -> int: ...


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MetaAdaptationCertificate:
    status: str
    reason: str
    episode: int
    inherited_passport: DFA
    updated_passport: DFA | None
    old_body: OpaqueNativeBody | None
    new_body: OpaqueNativeBody | None
    old_migration: MigrationCertificate
    new_migration: MigrationCertificate | None
    inference: MetaInference | None
    old_body_sha256_before: str | None
    old_body_sha256_after: str | None
    old_body_bit_exact: bool
    meta_passport_sha256: str
    meta_passport_round_trip_exact: bool
    group_counts_before: tuple[tuple[str, int], ...]
    group_counts_after: tuple[tuple[str, int], ...]
    session_trace_sha256: str | None
    trace: Mapping[str, object]


class DistributionGeneralPlasticityEngine:
    """Persistent learning session on one discovered opaque substrate."""

    def __init__(
        self,
        machine: OpaqueMachine,
        meta_passport_json: str,
        *,
        adaptive: bool = True,
        migrator: UnknownSubstrateMigrator | None = None,
        query_budget: int = 128,
    ) -> None:
        passport = MetaPlasticityPassport.from_json(meta_passport_json)
        restored = passport.to_json()
        self.machine = machine
        self.meta_passport_json = meta_passport_json
        self.meta_passport_sha256 = _sha256_text(meta_passport_json)
        self.meta_passport_round_trip_exact = restored == meta_passport_json
        self.session = MetaPlasticitySession(passport, adaptive=adaptive)
        self.migrator = migrator or UnknownSubstrateMigrator(native_component_budget=360)
        self.query_budget = query_budget
        self._substrate: DiscoveredSubstrate | None = None
        self.episode = 0

    @property
    def discovered_substrate(self) -> DiscoveredSubstrate | None:
        return self._substrate

    def _migrate(
        self,
        passport: DFA,
        seed: int,
        trace: Mapping[str, object],
    ) -> MigrationCertificate:
        attempts = (seed, seed ^ 0x9E37_79B9, seed ^ 0xC2B2_AE35)
        last: MigrationCertificate | None = None
        for attempt_index, attempt_seed in enumerate(attempts):
            attempt_trace = dict(trace)
            attempt_trace["morphogenesis_attempt"] = attempt_index
            certificate = self.migrator.migrate(
                passport,
                self.machine,  # type: ignore[arg-type]
                attempt_seed,
                attempt_trace,
                supplied_substrate=self._substrate,
            )
            last = certificate
            if self._substrate is None and certificate.substrate.stable_opcodes:
                self._substrate = certificate.substrate
            if certificate.status == "success" and certificate.body is not None:
                return certificate
        assert last is not None
        return last

    def adapt_episode(
        self,
        inherited_passport: DFA,
        behavioral_oracle: BehavioralOracle,
        search_seed: int,
        trace: Mapping[str, object] | None = None,
        *,
        policy: str = "adaptive",
    ) -> MetaAdaptationCertificate:
        base_trace = dict(trace or {})
        base_trace["episode"] = self.episode
        counts_before = tuple(sorted(self.session.group_counts.items()))
        old_migration = self._migrate(inherited_passport, search_seed, base_trace)
        old_body = old_migration.body
        if old_migration.status != "success" or old_body is None:
            return MetaAdaptationCertificate(
                "failed", "inherited_body_construction_failed", self.episode,
                inherited_passport, None, old_body, None, old_migration, None, None,
                None, False, self.meta_passport_sha256,
                self.meta_passport_round_trip_exact, counts_before, counts_before,
                None, base_trace,
            )

        archived_json = old_body.to_json()
        archived_hash = _sha256_text(archived_json)
        inference = self.session.identify(
            inherited_passport,
            behavioral_oracle,
            query_budget=self.query_budget,
            policy=policy,
            search_seed=search_seed ^ 0x14C0_14C0,
        )
        after_learning_json = old_body.to_json()
        after_learning_hash = _sha256_text(after_learning_json)
        counts_after = tuple(sorted(self.session.group_counts.items()))
        if inference.status != "success" or inference.updated_passport is None:
            self.episode += 1
            return MetaAdaptationCertificate(
                "abstained", inference.reason, self.episode - 1,
                inherited_passport, None, old_body, None, old_migration, None,
                inference, archived_hash, after_learning_hash,
                archived_json == after_learning_json, self.meta_passport_sha256,
                self.meta_passport_round_trip_exact, counts_before, counts_after,
                inference.trace_digest_sha256 or None, base_trace,
            )

        new_migration = self._migrate(
            inference.updated_passport,
            search_seed ^ 0x5EED_14C0,
            base_trace,
        )
        after_json = old_body.to_json()
        after_hash = _sha256_text(after_json)
        old_exact = archived_json == after_json
        episode_index = self.episode
        self.episode += 1
        if new_migration.status != "success" or new_migration.body is None:
            return MetaAdaptationCertificate(
                "failed", "updated_body_construction_failed", episode_index,
                inherited_passport, inference.updated_passport, old_body, None,
                old_migration, new_migration, inference, archived_hash, after_hash,
                old_exact, self.meta_passport_sha256,
                self.meta_passport_round_trip_exact, counts_before, counts_after,
                inference.trace_digest_sha256, base_trace,
            )
        return MetaAdaptationCertificate(
            "success", "distribution_general_plasticity_episode_completed",
            episode_index, inherited_passport, inference.updated_passport,
            old_body, new_migration.body, old_migration, new_migration, inference,
            archived_hash, after_hash, old_exact, self.meta_passport_sha256,
            self.meta_passport_round_trip_exact, counts_before, counts_after,
            inference.trace_digest_sha256, base_trace,
        )
