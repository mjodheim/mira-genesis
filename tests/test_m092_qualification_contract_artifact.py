from __future__ import annotations

import json
from pathlib import Path

from metamorphosis.m092_qualification_contract import execution_contract, validate_contract


CONTRACT = Path("experiments/M092/QUALIFICATION_CONTRACT.json")


def test_persisted_contract_is_exactly_the_pre_result_implementation_contract() -> None:
    stored = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert stored == execution_contract()
    assert validate_contract(stored) == stored["contract_digest"]


def _all_mapping_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            assert isinstance(key, str)
            keys.add(key)
            keys.update(_all_mapping_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(_all_mapping_keys(child))
    return keys


def test_persisted_contract_contains_no_dynamic_result_identity() -> None:
    stored = json.loads(CONTRACT.read_text(encoding="utf-8"))
    forbidden_keys = {
        "selected_candidate",
        "candidate_program",
        "canonical_result_digest",
        "reproduction_result_digest",
        "extended_substrate_digest",
        "extended_language_digest",
        "hidden_values",
    }
    assert not (forbidden_keys & _all_mapping_keys(stored))
    assert stored["result_or_hidden_values_embedded"] is False
