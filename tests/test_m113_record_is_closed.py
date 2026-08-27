"""M113 is closed. Its record may not be edited, reinterpreted or completed.

M113 froze a generator identity, made one physical request, received HTTP 429, materialized no
bank and left H58 untested. That is an instrument failure and not a result, and the owner closed
the milestone permanently rather than re-freezing it.

A closed record that is only closed by convention is closed until someone edits it. These digests
make it closed by construction. They are not a claim that the milestone succeeded -- they pin a
failure exactly as it happened, which is the harder thing to keep.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from metamorphosis import m113_carrier_bank as bank
from metamorphosis.blind_bank_protocol import sha256_hex

EXPERIMENT = bank.EXPERIMENT_DIRECTORY

# Byte digests of the artifacts that constitute the closed record.
CLOSED_RECORD = {
    "ANALYSIS_PLAN.json": "48948e6782c111e00a58aac996f22c7fa610c79138168f80a099268656bc0527",
    "GENERATOR_SPEC.json": "a8be0181d448b49200555de3ff1031265283109d8c68bcc3299703e0105751a4",
    "GENERATION_LEDGER.json": "ac3ab6033a52f7dc4b15a85475fc954ca9686ca3704ad301e3a3e5024fa8285a",
    "GENERATOR_PROMPT.txt": "f79fb18cde53e0efd4b1defef43460589376c0d3e93ff0eb2443836de526269e",
    "QUALIFYING_INPUT.txt": "c73721aec1de46b792551c9b16291b69806f21b4181a212b356bcc73e3f592e0",
    "OUTPUT_SCHEMA.json": "1020a1db9625f2734be1f548edd4c5af0139cb17732d13fb25913144f9106075",
}


@pytest.mark.parametrize("name,digest", sorted(CLOSED_RECORD.items()))
def test_the_m113_record_still_reproduces_byte_for_byte(name: str, digest: str) -> None:
    path = EXPERIMENT / name
    assert path.is_file(), "%s is part of M113's closed record and may not be removed" % name
    assert sha256_hex(path.read_bytes()) == digest, (
        "%s has changed. M113 is closed: its record may not be edited, reinterpreted or "
        "completed, and a corrective replication belongs in a successor milestone." % name
    )


def test_m113_materialized_no_bank_and_is_not_repeated() -> None:
    """The facts the record exists to hold, asserted rather than described."""
    ledger = json.loads((EXPERIMENT / "GENERATION_LEDGER.json").read_text(encoding="utf-8"))
    spec = json.loads((EXPERIMENT / "GENERATOR_SPEC.json").read_text(encoding="utf-8"))

    entries = ledger["entries"]
    assert len(entries) == 1, "M113 made exactly one physical request and is not repeated"
    only = entries[0]
    assert only["outcome"] == "aborted"
    assert only["payload_sha256"] is None
    assert only["spec_commitment_sha256"] == spec["spec_commitment_sha256"]
    assert not any(item["outcome"] == "materialized" for item in entries)


def test_no_m113_bank_reveal_or_result_may_ever_appear() -> None:
    """Nothing downstream of a bank exists, and the phase machine agrees."""
    for name in (
        "SEALED_BANK.json.gpg",
        "PUBLIC_BANK_COMMITMENT.json",
        "REVEAL_AUTHORIZATION.json",
        "SYSTEM_PROTOCOL.json",
        "RESULT.json",
        "CHECK_REPORT.json",
        "GENERATION_RESPONSE.json",
    ):
        assert not (EXPERIMENT / name).is_file(), (
            "%s exists. M113 materialized no bank; anything downstream of one would be a "
            "completion of a closed record." % name
        )

    report = bank.assess_carrier_bank_readiness(Path(bank.EXPERIMENT_DIRECTORY).parents[1])
    assert report["revealed"] is False
    assert report["phase"] == "spec_frozen"
    assert any("materialized 0 banks" in blocker for blocker in report["blockers"])
