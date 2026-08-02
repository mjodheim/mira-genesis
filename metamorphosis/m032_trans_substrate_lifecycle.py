"""M032 — carry a verified rewritten body across an opaque substrate boundary.

This development layer joins M025's transactional self-rewrite with M013e's bounded
unknown-substrate discovery and native-body synthesis.  The complete transaction is
committed only when the adopted source can be compiled into a finite DFA, migrated to
an opaque machine, and packaged together with the organism's portable memory and
exploration state.  Any bridge or migration failure restores both the source body and
the learned-tool registry exactly.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping, Sequence

from .m012b_dfa import DFA
from .m013e_engine import MigrationCertificate, UnknownSubstrateMigrator
from .m013e_lab import OpaqueBooleanMachine
from .m020_self_rewrite import (
    Case,
    ToolRegistry,
    VersionedCodeBody,
    compile_policy,
)
from .m023_workspace import CandidateWorkspace
from .m024_rewrite_passport import import_passport
from .m025_rewrite_lifecycle import (
    PortableRewriteLifecycle,
    execute_portable_rewrite,
)


@dataclass(frozen=True)
class PortableLearningState:
    """Small canonical state surface that must survive the substrate boundary."""

    memory: tuple[tuple[int, ...], ...] = ()
    uncertainty: tuple[int, ...] = ()
    exploration_frontier: tuple[tuple[int, ...], ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "memory": [list(row) for row in self.memory],
            "uncertainty": list(self.uncertainty),
            "exploration_frontier": [list(row) for row in self.exploration_frontier],
        }

    @staticmethod
    def from_dict(data: Mapping[str, object]) -> "PortableLearningState":
        return PortableLearningState(
            memory=tuple(tuple(int(value) for value in row) for row in data["memory"]),
            uncertainty=tuple(int(value) for value in data["uncertainty"]),
            exploration_frontier=tuple(
                tuple(int(value) for value in row)
                for row in data["exploration_frontier"]
            ),
        )


@dataclass(frozen=True)
class TransSubstratePacket:
    """Canonical transport packet for the rewritten body and cognitive state."""

    rewrite_passport_json: str
    rewrite_passport_sha256: str
    source_dfa: Mapping[str, object]
    opaque_body_json: str
    discovered_opcodes: tuple[str, ...]
    learning_state: PortableLearningState

    def to_json(self) -> str:
        return json.dumps(
            {
                "version": "m032-trans-substrate-packet/1",
                "rewrite_passport_json": self.rewrite_passport_json,
                "rewrite_passport_sha256": self.rewrite_passport_sha256,
                "source_dfa": self.source_dfa,
                "opaque_body_json": self.opaque_body_json,
                "discovered_opcodes": list(self.discovered_opcodes),
                "learning_state": self.learning_state.to_dict(),
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    def sha256(self) -> str:
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()

    @staticmethod
    def from_json(raw: str) -> "TransSubstratePacket":
        data = json.loads(raw)
        if data.get("version") != "m032-trans-substrate-packet/1":
            raise ValueError("unsupported M032 packet version")
        passport_json = str(data["rewrite_passport_json"])
        passport_sha256 = str(data["rewrite_passport_sha256"])
        try:
            _, _, passport = import_passport(passport_json)
        except ValueError as error:
            raise ValueError("invalid embedded rewrite passport") from error
        if passport.sha256() != passport_sha256:
            raise ValueError("rewrite passport digest mismatch")
        return TransSubstratePacket(
            rewrite_passport_json=passport_json,
            rewrite_passport_sha256=passport_sha256,
            source_dfa=dict(data["source_dfa"]),
            opaque_body_json=str(data["opaque_body_json"]),
            discovered_opcodes=tuple(str(value) for value in data["discovered_opcodes"]),
            learning_state=PortableLearningState.from_dict(data["learning_state"]),
        )


@dataclass(frozen=True)
class TransSubstrateLifecycle:
    committed: bool
    reason: str
    rewrite: PortableRewriteLifecycle
    source_dfa: DFA | None
    migration: MigrationCertificate | None
    packet_json: str | None
    packet_sha256: str | None


def compile_policy_to_dfa(
    source: str,
    function_name: str,
    *,
    state_count: int,
    accepting_states: Sequence[bool],
    initial_state: int = 0,
) -> DFA:
    """Compile a bounded ``policy(state, symbol) -> next_state`` into a DFA."""

    if state_count < 1:
        raise ValueError("state_count must be positive")
    if len(accepting_states) != state_count:
        raise ValueError("accepting-state vector has the wrong length")
    if not 0 <= initial_state < state_count:
        raise ValueError("initial state is out of range")

    policy = compile_policy(source, function_name)
    transitions: list[tuple[int, int]] = []
    for state in range(state_count):
        row: list[int] = []
        for symbol in (0, 1):
            value = policy(state, symbol)
            if type(value) is not int:
                raise ValueError("compiled policy returned a non-integer state")
            if not 0 <= value < state_count:
                raise ValueError("compiled policy left the finite state space")
            row.append(value)
        transitions.append((row[0], row[1]))

    return DFA(
        (0, 1),
        tuple(transitions),
        tuple(bool(value) for value in accepting_states),
        initial_state,
    )


def _dfa_dict(dfa: DFA) -> dict[str, object]:
    return {
        "alphabet": list(dfa.alphabet),
        "transitions": [list(row) for row in dfa.transitions],
        "accepting": [int(value) for value in dfa.accepting],
        "initial": dfa.initial,
    }


def execute_trans_substrate_lifecycle(
    body: VersionedCodeBody,
    registry: ToolRegistry,
    development_cases: Sequence[Case],
    regression_cases: Sequence[Case],
    *,
    state_count: int,
    accepting_states: Sequence[bool],
    machine: OpaqueBooleanMachine,
    search_seed: int,
    learning_state: PortableLearningState = PortableLearningState(),
    initial_state: int = 0,
    max_edits: int = 2,
    beam_width: int = 32,
    workspace: CandidateWorkspace | None = None,
    migrator: UnknownSubstrateMigrator | None = None,
) -> TransSubstrateLifecycle:
    """Rewrite, validate, compile, discover, migrate and package one transaction."""

    body_snapshot = (
        body.active_source,
        list(body.archive),
        list(body.adopted_digests),
    )
    learned_snapshot = list(registry.learned)

    def restore() -> None:
        body.active_source = body_snapshot[0]
        body.archive[:] = body_snapshot[1]
        body.adopted_digests[:] = body_snapshot[2]
        registry.learned[:] = learned_snapshot

    lifecycle = execute_portable_rewrite(
        body,
        registry,
        development_cases,
        regression_cases,
        max_edits=max_edits,
        beam_width=beam_width,
        workspace=workspace,
    )
    if not lifecycle.adopted:
        return TransSubstrateLifecycle(
            False,
            lifecycle.reason,
            lifecycle,
            None,
            None,
            None,
            None,
        )

    migrated_body = lifecycle.migrated_body
    if migrated_body is None or lifecycle.passport_json is None or lifecycle.passport is None:
        restore()
        return TransSubstrateLifecycle(
            False,
            "incomplete_m025_migration_state",
            lifecycle,
            None,
            None,
            None,
            None,
        )

    try:
        source_dfa = compile_policy_to_dfa(
            migrated_body.active_source,
            migrated_body.function_name,
            state_count=state_count,
            accepting_states=accepting_states,
            initial_state=initial_state,
        )
    except (TypeError, ValueError) as error:
        restore()
        return TransSubstrateLifecycle(
            False,
            f"compiled_body_invalid:{error}",
            lifecycle,
            None,
            None,
            None,
            None,
        )

    migration = (migrator or UnknownSubstrateMigrator()).migrate(
        source_dfa,
        machine,
        search_seed,
        trace={
            "m025_passport_sha256": lifecycle.passport.sha256(),
            "m032_learning_state": learning_state.to_dict(),
        },
    )
    if migration.status != "success" or migration.body is None:
        restore()
        return TransSubstrateLifecycle(
            False,
            f"opaque_migration_{migration.status}:{migration.reason}",
            lifecycle,
            source_dfa,
            migration,
            None,
            None,
        )

    packet = TransSubstratePacket(
        rewrite_passport_json=lifecycle.passport_json,
        rewrite_passport_sha256=lifecycle.passport.sha256(),
        source_dfa=_dfa_dict(source_dfa),
        opaque_body_json=migration.body.to_json(),
        discovered_opcodes=tuple(opcode.opcode for opcode in migration.substrate.opcodes),
        learning_state=learning_state,
    )
    raw_packet = packet.to_json()
    restored_packet = TransSubstratePacket.from_json(raw_packet)
    if restored_packet.to_json() != raw_packet:
        restore()
        raise RuntimeError("M032 packet did not round-trip canonically")

    return TransSubstrateLifecycle(
        True,
        "rewrite_compiled_and_migrated_to_opaque_substrate",
        lifecycle,
        source_dfa,
        migration,
        raw_packet,
        packet.sha256(),
    )
