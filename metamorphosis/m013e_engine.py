from __future__ import annotations

from dataclasses import dataclass
import random
import time
from typing import Mapping, Sequence

from .m012b_body import synthesize_native_body
from .m012b_dfa import DFA, canonicalize, minimize_dfa
from .m012b_primitives import Primitive, PrimitiveCatalog
from .m013e_lab import OpcodeDescriptor, OpaqueBooleanMachine
from .m013e_runtime import (
    DiscoveredOpcode,
    DiscoveredSubstrate,
    OpaqueNativeBody,
    discover_substrate,
    unique_component_count,
)


@dataclass(frozen=True)
class MigrationCertificate:
    status: str
    reason: str
    body: OpaqueNativeBody | None
    substrate: DiscoveredSubstrate
    probe_calls: int
    candidate_evaluations: int
    native_components: int
    serialized_bytes: int
    elapsed_seconds: float
    used_opcodes: tuple[str, ...]
    trace: Mapping[str, object]


class UnknownSubstrateMigrator:
    """Migrate an inherited finite competence without a task oracle."""

    def __init__(
        self,
        probe_repetitions: int = 3,
        probe_budget: int = 120,
        candidate_budget: int = 75_000,
        cpu_seconds: float = 120.0,
        native_component_budget: int = 320,
        serialized_byte_budget: int = 16_777_216,
    ) -> None:
        self.probe_repetitions = probe_repetitions
        self.probe_budget = probe_budget
        self.candidate_budget = candidate_budget
        self.cpu_seconds = cpu_seconds
        self.native_component_budget = native_component_budget
        self.serialized_byte_budget = serialized_byte_budget

    def migrate(
        self,
        passport: DFA,
        machine: OpaqueBooleanMachine,
        search_seed: int,
        trace: Mapping[str, object] | None = None,
        supplied_substrate: DiscoveredSubstrate | None = None,
    ) -> MigrationCertificate:
        started = time.perf_counter()
        base_trace = dict(trace or {})
        try:
            substrate = supplied_substrate or discover_substrate(
                machine,
                repetitions=self.probe_repetitions,
                probe_budget=self.probe_budget,
            )
        except RuntimeError as exc:
            empty = DiscoveredSubstrate((), self.probe_budget, ())
            return MigrationCertificate(
                "abstained", str(exc), None, empty, self.probe_budget, 0, 0, 0,
                time.perf_counter() - started, (), base_trace,
            )

        if not substrate.stable_opcodes:
            return MigrationCertificate(
                "abstained", "no_stable_native_operations", None, substrate,
                substrate.probe_calls, 0, 0, 0, time.perf_counter() - started, (), base_trace,
            )

        catalog = substrate.catalog()
        abstract_body, evaluations, reason = synthesize_native_body(
            canonicalize(minimize_dfa(passport)),
            catalog,
            search_seed,
            self.candidate_budget,
        )
        if abstract_body is None:
            return MigrationCertificate(
                "abstained", reason, None, substrate, substrate.probe_calls,
                evaluations, 0, 0, time.perf_counter() - started, (), base_trace,
            )

        body = OpaqueNativeBody(
            state_width=abstract_body.state_width,
            next_state=abstract_body.next_state,
            output=abstract_body.output,
            initial_state=abstract_body.initial_state,
            initial_output=abstract_body.initial_output,
        )
        raw = body.to_json().encode("utf-8")
        components = unique_component_count(body)
        elapsed = time.perf_counter() - started
        used = tuple(sorted(body.used_opcodes()))

        if evaluations > self.candidate_budget:
            status, reason, body = "failed", "candidate_budget_exceeded", None
        elif components > self.native_component_budget:
            status, reason, body = "failed", "native_component_budget_exceeded", None
        elif len(raw) > self.serialized_byte_budget:
            status, reason, body = "failed", "serialized_byte_budget_exceeded", None
        elif elapsed > self.cpu_seconds:
            status, reason, body = "failed", "cpu_budget_exceeded", None
        else:
            status, reason = "success", "opaque_native_body_constructed"

        return MigrationCertificate(
            status, reason, body, substrate, substrate.probe_calls, evaluations,
            components, len(raw), elapsed, used, base_trace,
        )


def fixed_role_baseline(descriptors: Sequence[OpcodeDescriptor]) -> DiscoveredSubstrate:
    unary_tables = [(1, 0), (0, 1), (0, 0), (1, 1)]
    binary_tables = [
        (0, 0, 0, 1),
        (0, 1, 1, 1),
        (0, 1, 1, 0),
        (1, 1, 1, 0),
        (1, 0, 0, 0),
        (0, 0, 1, 1),
        (0, 1, 0, 1),
    ]
    unary_index = 0
    binary_index = 0
    operations: list[DiscoveredOpcode] = []
    for descriptor in sorted(descriptors, key=lambda item: item.opcode):
        if descriptor.arity == 1:
            table = unary_tables[unary_index % len(unary_tables)]
            unary_index += 1
        else:
            table = binary_tables[binary_index % len(binary_tables)]
            binary_index += 1
        operations.append(
            DiscoveredOpcode(descriptor.opcode, descriptor.arity, descriptor.cost, table, True)
        )
    return DiscoveredSubstrate(tuple(operations), 0, ())


def random_semantics_baseline(
    descriptors: Sequence[OpcodeDescriptor],
    seed: int,
) -> DiscoveredSubstrate:
    rng = random.Random(seed)
    operations = tuple(
        DiscoveredOpcode(
            descriptor.opcode,
            descriptor.arity,
            descriptor.cost,
            tuple(rng.randrange(2) for _ in range(2 ** descriptor.arity)),
            True,
        )
        for descriptor in sorted(descriptors, key=lambda item: item.opcode)
    )
    return DiscoveredSubstrate(operations, 0, ())
