from __future__ import annotations

from dataclasses import dataclass
import random
import time
from typing import Mapping, Sequence

from .core import DFA, canonicalize, minimize_dfa
from .morphogenesis import GenericCubeSynthesizer, REGISTER_CATALOG, one_hot_constraints
from .opaque_machine_lab import OpcodeDescriptor, OpaqueBooleanMachine
from .opaque_runtime import (
    DiscoveredOpcode,
    DiscoveredSubstrate,
    OpaqueExpr,
    OpaqueNativeBody,
    discover_substrate,
    opaque_body_to_dfa,
    unique_component_count,
)
from .opaque_synthesis import OpaqueBasisSynthesizer, translate_abstract_expr


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
    def __init__(
        self,
        candidate_budget: int = 75_000,
        cpu_seconds: float = 120.0,
        native_component_budget: int = 320,
        serialized_byte_budget: int = 16_777_216,
    ) -> None:
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
        try:
            substrate = supplied_substrate or discover_substrate(machine)
        except RuntimeError as exc:
            empty = DiscoveredSubstrate((), 120, ())
            return MigrationCertificate(
                "abstained",
                str(exc),
                None,
                empty,
                120,
                0,
                0,
                0,
                time.perf_counter() - started,
                (),
                dict(trace or {}),
            )

        basis_search = OpaqueBasisSynthesizer(substrate, self.candidate_budget, search_seed)
        basis = basis_search.synthesize()
        if basis is None:
            return MigrationCertificate(
                "abstained",
                "insufficient_or_unstable_functional_basis",
                None,
                substrate,
                substrate.probe_calls,
                basis_search.evaluations,
                0,
                0,
                time.perf_counter() - started,
                (),
                dict(trace or {}),
            )

        constraints, initial, initial_output = one_hot_constraints(canonicalize(minimize_dfa(passport)))
        cube = GenericCubeSynthesizer(
            REGISTER_CATALOG,
            heritage=None,
            candidate_budget=max(1, self.candidate_budget - basis_search.evaluations),
            seed=search_seed,
        )
        abstract_body, stats, reason = cube.synthesize(constraints, initial, initial_output)
        total_evaluations = basis_search.evaluations + stats.candidate_evaluations
        if abstract_body is None:
            return MigrationCertificate(
                "abstained",
                reason,
                None,
                substrate,
                substrate.probe_calls,
                total_evaluations,
                0,
                0,
                time.perf_counter() - started,
                (),
                dict(trace or {}),
            )

        body = OpaqueNativeBody(
            state_width=abstract_body.state_width,
            next_state_exprs=tuple(
                translate_abstract_expr(expr, basis) for expr in abstract_body.next_state_exprs
            ),
            output_expr=translate_abstract_expr(abstract_body.output_expr, basis),
            initial_state=abstract_body.initial_state,
            initial_output=abstract_body.initial_output,
        )
        raw = body.to_json().encode("utf-8")
        components = unique_component_count(body)
        elapsed = time.perf_counter() - started
        used = tuple(sorted(body.used_opcodes()))

        if total_evaluations > self.candidate_budget:
            return MigrationCertificate("failed", "candidate_budget_exceeded", None, substrate, substrate.probe_calls, total_evaluations, components, len(raw), elapsed, used, dict(trace or {}))
        if components > self.native_component_budget:
            return MigrationCertificate("failed", "native_component_budget_exceeded", None, substrate, substrate.probe_calls, total_evaluations, components, len(raw), elapsed, used, dict(trace or {}))
        if len(raw) > self.serialized_byte_budget:
            return MigrationCertificate("failed", "serialized_byte_budget_exceeded", None, substrate, substrate.probe_calls, total_evaluations, components, len(raw), elapsed, used, dict(trace or {}))
        if elapsed > self.cpu_seconds:
            return MigrationCertificate("failed", "cpu_budget_exceeded", None, substrate, substrate.probe_calls, total_evaluations, components, len(raw), elapsed, used, dict(trace or {}))
        return MigrationCertificate(
            "success",
            "native_body_constructed",
            body,
            substrate,
            substrate.probe_calls,
            total_evaluations,
            components,
            len(raw),
            elapsed,
            used,
            dict(trace or {}),
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


__all__ = [
    "DiscoveredOpcode",
    "DiscoveredSubstrate",
    "OpaqueExpr",
    "OpaqueNativeBody",
    "MigrationCertificate",
    "UnknownSubstrateMigrator",
    "discover_substrate",
    "fixed_role_baseline",
    "random_semantics_baseline",
    "opaque_body_to_dfa",
]
