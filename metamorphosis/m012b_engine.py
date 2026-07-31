from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable, Mapping

from .m012b_body import NativeBody, synthesize_native_body, unique_component_count
from .m012b_dfa import DFA, Word
from .m012b_discovery import InconsistentContract, LStarExtractor, OpaqueBehavioralContract, QueryBudgetExceeded
from .m012b_primitives import PrimitiveCatalog

@dataclass(frozen=True)
class BirthCertificate:
    status: str
    reason: str
    body: NativeBody | None
    discovered_dfa: DFA | None
    behavioural_queries: int
    candidate_evaluations: int
    native_components: int
    serialized_bytes: int
    elapsed_seconds: float
    discovery_rounds: int
    counterexamples: int
    trace: Mapping[str, object]


class AutonomousMorphogenesisEngine:
    """One task-agnostic and catalogue-agnostic birth path."""

    def __init__(
        self,
        behavioural_query_budget: int = 20_000,
        candidate_budget: int = 50_000,
        max_states: int = 8,
        native_component_budget: int = 256,
        serialized_byte_budget: int = 16_777_216,
        cpu_seconds: float = 120.0,
    ) -> None:
        self.behavioural_query_budget = behavioural_query_budget
        self.candidate_budget = candidate_budget
        self.max_states = max_states
        self.native_component_budget = native_component_budget
        self.serialized_byte_budget = serialized_byte_budget
        self.cpu_seconds = cpu_seconds

    def birth(
        self,
        oracle_fn: Callable[[Word], bool],
        catalog: PrimitiveCatalog,
        search_seed: int,
        trace: Mapping[str, object] | None = None,
    ) -> BirthCertificate:
        started = time.perf_counter()
        contract = OpaqueBehavioralContract(oracle_fn, self.behavioural_query_budget)
        trace_out = dict(trace or {})
        try:
            contract.audit_consistency()
            discovered, extraction = LStarExtractor(contract, search_seed).extract()
            if discovered.n_states > self.max_states:
                return BirthCertificate(
                    "abstained",
                    "discovered_state_limit_exceeded",
                    None,
                    discovered,
                    contract.calls,
                    0,
                    0,
                    0,
                    time.perf_counter() - started,
                    extraction.rounds,
                    extraction.counterexamples,
                    trace_out,
                )
            body, candidates, reason = synthesize_native_body(
                discovered, catalog, search_seed, self.candidate_budget
            )
            if body is None:
                return BirthCertificate(
                    "abstained",
                    reason,
                    None,
                    discovered,
                    contract.calls,
                    candidates,
                    0,
                    0,
                    time.perf_counter() - started,
                    extraction.rounds,
                    extraction.counterexamples,
                    trace_out,
                )
            raw = body.to_json().encode("utf-8")
            components = unique_component_count(body)
            elapsed = time.perf_counter() - started
            if candidates > self.candidate_budget:
                status, reason = "failed", "candidate_budget_exceeded"
            elif components > self.native_component_budget:
                status, reason = "failed", "native_component_budget_exceeded"
            elif len(raw) > self.serialized_byte_budget:
                status, reason = "failed", "serialized_byte_budget_exceeded"
            elif elapsed > self.cpu_seconds:
                status, reason = "failed", "cpu_budget_exceeded"
            else:
                status, reason = "success", "native_body_constructed"
            return BirthCertificate(
                status,
                reason,
                body if status == "success" else None,
                discovered,
                contract.calls,
                candidates,
                components,
                len(raw),
                elapsed,
                extraction.rounds,
                extraction.counterexamples,
                trace_out,
            )
        except (QueryBudgetExceeded, InconsistentContract, RuntimeError) as error:
            return BirthCertificate(
                "abstained",
                str(error),
                None,
                None,
                contract.calls,
                0,
                0,
                0,
                time.perf_counter() - started,
                0,
                0,
                trace_out,
            )
