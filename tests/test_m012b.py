from __future__ import annotations

import inspect
from metamorphosis.m012b import (
    AutonomousMorphogenesisEngine,
    NativeBody,
    evaluation_catalogs,
    exact_equivalence,
    insufficient_catalog,
    native_body_to_dfa,
    random_minimal_dfa,
)


def test_all_development_catalogues_construct_exact_bodies() -> None:
    engine = AutonomousMorphogenesisEngine()
    for target_seed in (21001, 21007, 21013):
        target = random_minimal_dfa(target_seed)
        for catalog in evaluation_catalogs():
            certificate = engine.birth(target.accepts, catalog, search_seed=311)
            assert certificate.status == "success", (
                target_seed,
                catalog.catalog_id,
                certificate.reason,
            )
            assert certificate.body is not None
            reconstructed = native_body_to_dfa(certificate.body)
            assert exact_equivalence(target, reconstructed)[0]


def test_native_body_round_trip_preserves_language() -> None:
    target = random_minimal_dfa(21019)
    certificate = AutonomousMorphogenesisEngine().birth(
        target.accepts,
        evaluation_catalogs()[1],
        search_seed=313,
    )
    assert certificate.body is not None
    restored = NativeBody.from_json(certificate.body.to_json())
    assert restored == certificate.body
    assert exact_equivalence(target, native_body_to_dfa(restored))[0]


def test_incomplete_catalogue_causes_abstention() -> None:
    target = random_minimal_dfa(21023)
    certificate = AutonomousMorphogenesisEngine().birth(
        target.accepts,
        insufficient_catalog(),
        search_seed=317,
    )
    assert certificate.status == "abstained"
    assert certificate.body is None
    assert certificate.reason == "insufficient_functional_basis"


def test_non_deterministic_contract_causes_abstention() -> None:
    calls: dict[tuple[int, ...], int] = {}

    def unstable(word: tuple[int, ...]) -> bool:
        calls[word] = calls.get(word, 0) + 1
        base = bool(sum(word) % 2)
        if word == (1,):
            return base if calls[word] % 2 else not base
        return base

    certificate = AutonomousMorphogenesisEngine().birth(
        unstable,
        evaluation_catalogs()[0],
        search_seed=331,
    )
    assert certificate.status == "abstained"
    assert certificate.body is None
    assert "non_deterministic_contract" in certificate.reason


def test_engine_has_no_catalogue_identity_branching() -> None:
    source = inspect.getsource(AutonomousMorphogenesisEngine)
    for catalog_id in ("register_logic", "nand_fabric", "nor_fabric"):
        assert catalog_id not in source



def test_runtime_seed_deriver_is_not_imported_by_tests() -> None:
    forbidden_name = "derive_" + "runtime_" + "seeds"
    assert forbidden_name not in globals()
