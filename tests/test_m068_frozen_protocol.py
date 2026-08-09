from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from check_m068_frozen_protocol import M068FreezeError, validate_frozen_protocol


def test_frozen_protocol_matches_runtime_and_live_bank() -> None:
    frozen = validate_frozen_protocol()
    protocol = frozen["protocol"]
    attestation = frozen["body_bank_attestation"]
    assert protocol["complete_word_count"] == sum(8 ** length for length in range(1, 6)) == 37_448
    assert protocol["descriptor_grammar_disclosed"] is False
    assert protocol["external_target_authorship_claimed"] is False
    assert protocol["target_bank_frozen_before_discovery_engine"] is True
    assert attestation["command_words_disclosed"] is False
    assert attestation["semantic_assignments_disclosed"] is False
    assert attestation["descriptor_grammar_disclosed"] is False


def test_runtime_has_no_external_authority() -> None:
    source = Path("metamorphosis/m068_external_body_bank.mjs").read_text(encoding="utf-8")
    assert 'from "node:crypto"' in source
    assert 'from "node:fs"' not in source
    assert 'from "node:http"' not in source
    assert "fetch(" not in source
    assert 'mode === "public" || mode === "hidden"' in source


def test_runtime_drift_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import check_m068_frozen_protocol as freeze

    altered = tmp_path / "body.mjs"
    altered.write_bytes(freeze.RUNTIME_PATH.read_bytes() + b"\n// drift\n")
    monkeypatch.setattr(freeze, "RUNTIME_PATH", altered)
    with pytest.raises(M068FreezeError, match="runtime drifted"):
        validate_frozen_protocol()


def test_protocol_digest_covers_scientific_rule(tmp_path: Path) -> None:
    source = json.loads(Path("experiments/M068/FROZEN_PROTOCOL.json").read_text(encoding="utf-8"))
    source["protocol"]["max_word_length"] = 6
    altered = tmp_path / "FROZEN_PROTOCOL.json"
    altered.write_text(json.dumps(source), encoding="utf-8")
    with pytest.raises(M068FreezeError, match="protocol digest mismatch"):
        validate_frozen_protocol(altered)


def test_lf_hash_is_checkout_portable() -> None:
    runtime = Path("metamorphosis/m068_external_body_bank.mjs").read_bytes()
    lf = runtime.replace(b"\r\n", b"\n")
    crlf = lf.replace(b"\n", b"\r\n")
    expected = hashlib.sha256(lf).hexdigest()
    assert hashlib.sha256(crlf.replace(b"\r\n", b"\n")).hexdigest() == expected
