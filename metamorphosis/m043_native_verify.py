"""Independent recomputation of M043 Q5 native synthesis certificates."""
from __future__ import annotations

from typing import Mapping, Sequence

from metamorphosis.m043_mealy import (
    MealyMachine,
    exact_mealy_equivalence,
    mealy_digest,
)
from metamorphosis.m043_native_program import (
    FORBIDDEN_TABLE_KEYS,
    NativeMealyProgram,
    NativeProgramError,
    NativeSynthesisCertificate,
    audit_program_against_discovery,
    native_program_to_mealy,
)
from metamorphosis.m043_opaque_substrate import (
    DiscoveredFieldSubstrate,
    OpaqueFieldMachine,
)
from metamorphosis.m043_rewrite import exact_body_bytes, exact_body_digest


def _contains_forbidden_table_key(value: object) -> bool:
    if isinstance(value, Mapping):
        if any(key in FORBIDDEN_TABLE_KEYS for key in value):
            return True
        return any(_contains_forbidden_table_key(item) for item in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_forbidden_table_key(item) for item in value)
    return False


def recompute_native_synthesis_certificate(
    source: MealyMachine,
    program: NativeMealyProgram,
    discovery: DiscoveredFieldSubstrate,
    machine: OpaqueFieldMachine,
) -> NativeSynthesisCertificate:
    audit_program_against_discovery(program, discovery)
    reconstructed = native_program_to_mealy(program, machine)
    equivalent, witness = exact_mealy_equivalence(source, reconstructed)
    maximum_arity = max(
        (len(node.args) for node in program.nodes if node.kind == "call"),
        default=0,
    )
    return NativeSynthesisCertificate(
        source_body_digest=exact_body_digest(source),
        source_behaviour_digest=mealy_digest(source, minimise=True),
        native_program_digest=program.digest(),
        discovery_digest=discovery.digest(),
        exact_pair_count=source.n_states * len(source.input_alphabet),
        pairwise_exact=(source == reconstructed),
        behavioural_equivalence=equivalent,
        distinguishing_word=witness,
        forbidden_table_keys_absent=not _contains_forbidden_table_key(
            program.to_dict()
        ),
        source_body_bytes_embedded=exact_body_bytes(source) in program.to_bytes(),
        all_nodes_reachable=(
            program.reachable_node_indices() == frozenset(range(len(program.nodes)))
        ),
        maximum_call_arity=maximum_arity,
    )


def verify_native_synthesis_certificate(
    source: MealyMachine,
    program: NativeMealyProgram,
    discovery: DiscoveredFieldSubstrate,
    machine: OpaqueFieldMachine,
    certificate: NativeSynthesisCertificate,
) -> None:
    recomputed = recompute_native_synthesis_certificate(
        source, program, discovery, machine
    )
    if recomputed != certificate:
        raise NativeProgramError("native synthesis certificate mismatch")
    if not recomputed.exact:
        raise NativeProgramError("native synthesis certificate is not exact")


__all__ = [
    "recompute_native_synthesis_certificate",
    "verify_native_synthesis_certificate",
]
