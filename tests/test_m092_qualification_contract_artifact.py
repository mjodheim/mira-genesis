from __future__ import annotations

import json
from pathlib import Path

from metamorphosis.m092_qualification_contract import execution_contract, validate_contract


CONTRACT = Path("experiments/M092/QUALIFICATION_CONTRACT.json")


def test_persisted_contract_is_exactly_the_pre_result_implementation_contract() -> None:
    stored = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert stored == execution_contract()
    assert validate_contract(stored) == stored["contract_digest"]


def test_persisted_contract_contains_no_dynamic_result_identity() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    for forbidden in (
        "selected_candidate",
        "candidate_program",
        "canonical_result_digest",
        "reproduction_result_digest",
        "extended_substrate_digest",
        "extended_language_digest",
        "hidden_values",
    ):
        assert forbidden not in text
