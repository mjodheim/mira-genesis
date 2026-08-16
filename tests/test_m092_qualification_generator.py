from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from metamorphosis.m092_qualification_generator import (
    DOMAIN_MAX,
    DOMAIN_MIN,
    FAMILIES,
    INSTANCES_PER_FAMILY,
    INSTANCES_PER_PARITY,
    QualificationGenerationError,
    materialize_hidden_qualification,
)
from metamorphosis.m092_runtime import canonical_bytes


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "experiments" / "M092" / "PROTOCOL.json"
SUBSTRATE_DIGEST = "1" * 64
LANGUAGE_DIGEST = "2" * 64


def _materialize(protocol_blob: bytes | None = None) -> dict[str, object]:
    return materialize_hidden_qualification(
        PROTOCOL.read_bytes() if protocol_blob is None else protocol_blob,
        extended_substrate_digest=SUBSTRATE_DIGEST,
        extended_language_digest=LANGUAGE_DIGEST,
        adoption_committed=True,
        fresh_process_loaded=True,
    )


@pytest.mark.parametrize(
    ("adoption_committed", "fresh_process_loaded"),
    [(False, False), (False, True), (True, False)],
)
def test_hidden_qualification_refuses_pre_adoption_or_pre_reload(
    adoption_committed: bool,
    fresh_process_loaded: bool,
) -> None:
    with pytest.raises(QualificationGenerationError, match="committed adoption and fresh reload"):
        materialize_hidden_qualification(
            PROTOCOL.read_bytes(),
            extended_substrate_digest=SUBSTRATE_DIGEST,
            extended_language_digest=LANGUAGE_DIGEST,
            adoption_committed=adoption_committed,
            fresh_process_loaded=fresh_process_loaded,
        )


def test_hidden_qualification_is_deterministic_stratified_and_digest_bound() -> None:
    first = _materialize()
    second = _materialize()

    assert first == second
    assert first["protocol_sha256"] == hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    assert first["extended_substrate_digest"] == SUBSTRATE_DIGEST
    assert first["extended_language_digest"] == LANGUAGE_DIGEST
    assert first["instances_per_family"] == INSTANCES_PER_FAMILY
    assert first["instances_per_parity"] == INSTANCES_PER_PARITY
    assert first["materialized_after_adoption"] is True
    assert first["fresh_process_loaded_before_materialization"] is True

    families = first["families"]
    assert isinstance(families, list)
    assert [entry["family"] for entry in families] == list(FAMILIES)

    for entry in families:
        draws = entry["draws"]
        assert isinstance(draws, list)
        assert len(draws) == INSTANCES_PER_FAMILY
        values = [int(draw["value"]) for draw in draws]
        assert len(values) == len(set(values))
        assert all(DOMAIN_MIN <= value <= DOMAIN_MAX for value in values)
        assert sum(value % 2 == 0 for value in values) == INSTANCES_PER_PARITY
        assert sum(value % 2 == 1 for value in values) == INSTANCES_PER_PARITY
        assert entry["stratum_order"] in (["even", "odd"], ["odd", "even"])
        assert all(draw["stratum"] in {"even", "odd"} for draw in draws)
        assert all(len(str(draw["draw_digest"])) == 64 for draw in draws)

    payload = dict(first)
    claimed_digest = payload.pop("materialization_digest")
    assert claimed_digest == hashlib.sha256(canonical_bytes(payload)).hexdigest()


def test_raw_protocol_bytes_are_part_of_the_hidden_world_salt() -> None:
    original = PROTOCOL.read_bytes()
    # JSON trailing whitespace is semantically inert, so this proves the frozen raw blob—not merely
    # its decoded object—is part of the qualification salt.
    variant = original + b" "

    first = _materialize(original)
    second = _materialize(variant)

    assert first["protocol_sha256"] != second["protocol_sha256"]
    assert first["salt_digest"] != second["salt_digest"]
    assert first["materialization_digest"] != second["materialization_digest"]


@pytest.mark.parametrize("mutation", ["count", "domain", "families", "algorithm"])
def test_hidden_qualification_refuses_protocol_contract_drift(mutation: str) -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    qualification = protocol["qualification"]

    if mutation == "count":
        qualification["hidden_instances_per_family"] = 5
    elif mutation == "domain":
        qualification["hidden_value_domain"]["inclusive_maximum"] = DOMAIN_MAX + 1
    elif mutation == "families":
        qualification["family_schemas"].pop(FAMILIES[0])
    elif mutation == "algorithm":
        qualification["draw_algorithm"] = "unfrozen sampler"
    else:  # pragma: no cover - parametrization is closed above
        raise AssertionError(mutation)

    drifted = json.dumps(protocol, sort_keys=True, separators=(",", ":")).encode("utf-8")
    with pytest.raises(QualificationGenerationError):
        _materialize(drifted)


@pytest.mark.parametrize(
    ("substrate_digest", "language_digest"),
    [("x" * 64, LANGUAGE_DIGEST), (SUBSTRATE_DIGEST, "ABC"), ("1" * 63, LANGUAGE_DIGEST)],
)
def test_hidden_qualification_refuses_malformed_state_digests(
    substrate_digest: str,
    language_digest: str,
) -> None:
    with pytest.raises(QualificationGenerationError, match="lowercase SHA-256"):
        materialize_hidden_qualification(
            PROTOCOL.read_bytes(),
            extended_substrate_digest=substrate_digest,
            extended_language_digest=language_digest,
            adoption_committed=True,
            fresh_process_loaded=True,
        )
