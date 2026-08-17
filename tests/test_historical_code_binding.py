"""Adversarial tests for historical-code-binding verification.

Each test verifies that the historical code-binding logic in
metamorphosis.m074_scientific_runner fails closed (raises error)
for every attack mode, and accepts only the exact correct case.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from metamorphosis.m074_scientific_runner import (
    REQUIRED_CODE_PATHS,
    ROOT,
    ScientificRunnerError,
    _SYNTHETIC_COMMIT_MARKER,
    _resolve_validation_mode,
    _verify_code_files,
    portable_file_sha256,
)

# The real M074 protocol commit and its code-sha256 bindings.
REAL_COMMIT = "55a34a90bdc0033c7f1eb811a315516dea14acff"
_PROTOCOL_PATH = ROOT / "experiments" / "M074" / "SCIENTIFIC_PROTOCOL.json"

with open(_PROTOCOL_PATH) as _f:
    _PROTOCOL_DATA = json.load(_f)

REAL_CODE_SHA256: dict[str, str] = dict(_PROTOCOL_DATA["code_sha256"])

# ── helpers ──────────────────────────────────────────────────────────────


def _build_protocol(
    apparatus_commit: str | None,
    code_sha256: dict[str, str] | None = None,
) -> dict:
    return {
        "apparatus_commit": apparatus_commit,
        "code_sha256": code_sha256 or REAL_CODE_SHA256.copy(),
    }


# ── tests ────────────────────────────────────────────────────────────────


class TestAdversarialValidationMode:
    """Tests focused on _resolve_validation_mode directly."""

    def test_unknown_historical_commit_rejected(self) -> None:
        """40-hex-char commit that does not exist in the repo."""
        with pytest.raises(ValueError, match="does not exist"):
            _resolve_validation_mode(
                "0000000000000000000000000000000000000001", ROOT,
            )

    def test_malformed_historical_commit_rejected(self) -> None:
        """Non-hex apparatus_commit string."""
        with pytest.raises(ValueError, match="40-character hex SHA"):
            _resolve_validation_mode("not-a-commit", ROOT)

    def test_short_historical_commit_rejected(self) -> None:
        """Too-short apparatus_commit (< 40 chars)."""
        with pytest.raises(ValueError, match="40-character hex SHA"):
            _resolve_validation_mode("abc123", ROOT)

    def test_absent_historical_commit_rejected(self) -> None:
        """None apparatus_commit."""
        with pytest.raises(ValueError, match="mandatory"):
            _resolve_validation_mode(None, ROOT)

    def test_git_inaccessible_rejected(self, tmp_path: Path) -> None:
        """Valid-looking commit but root is a non-git directory."""
        with pytest.raises(ValueError, match="inaccessible"):
            _resolve_validation_mode(
                "1111111111111111111111111111111111111111", tmp_path,
            )

    def test_synthetic_commit_returns_live(self) -> None:
        """_SYNTHETIC_COMMIT_MARKER returns 'live', not 'historical'."""
        mode = _resolve_validation_mode(_SYNTHETIC_COMMIT_MARKER, ROOT)
        assert mode == "live"

    def test_exact_historical_commit_returns_historical(self) -> None:
        """A real commit that exists in the repo returns 'historical'."""
        mode = _resolve_validation_mode(REAL_COMMIT, ROOT)
        assert mode == "historical"


class TestVerifyCodeFilesIntegration:
    """Integration tests exercising _verify_code_files end-to-end."""

    def test_exact_historical_commit_and_digest_accepted(self) -> None:
        """Real commit + correct code-sha256 → no error."""
        # Should not raise.
        _verify_code_files(
            _build_protocol(REAL_COMMIT), ROOT, REQUIRED_CODE_PATHS,
        )

    def test_historical_commit_wrong_digest_rejected(self) -> None:
        """Real commit with one corrupted sha256 hex char."""
        bad = REAL_CODE_SHA256.copy()
        key = next(iter(bad))
        chars = list(bad[key])
        chars[0] = "0" if chars[0] != "0" else "1"
        bad[key] = "".join(chars)
        with pytest.raises(ScientificRunnerError, match="drifted"):
            _verify_code_files(
                _build_protocol(REAL_COMMIT, bad), ROOT, REQUIRED_CODE_PATHS,
            )

    def test_synthetic_commit_marker_accepted(self, tmp_path: Path) -> None:
        """_SYNTHETIC_COMMIT_MARKER routes to live validation with matching files."""
        code_sha256: dict[str, str] = {}
        for rel_path in REQUIRED_CODE_PATHS:
            full = tmp_path / rel_path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(f"mock content for {rel_path}")
            code_sha256[rel_path] = portable_file_sha256(full)

        _verify_code_files(
            _build_protocol(_SYNTHETIC_COMMIT_MARKER, code_sha256),
            tmp_path,
            REQUIRED_CODE_PATHS,
        )

    def test_historical_commit_tracked_file_missing_rejected(self) -> None:
        """Real commit but one code path does not exist at that commit."""
        code_sha256 = REAL_CODE_SHA256.copy()
        # Replace a real path with one that never existed.
        del code_sha256["metamorphosis/m074_ablation_arms.py"]
        code_sha256["nonexistent/module.py"] = "0" * 64
        # The set check passes (same size), but _validate_historical will
        # fail when trying to read "nonexistent/module.py" from history.
        with pytest.raises(ScientificRunnerError, match="cannot read"):
            _verify_code_files(
                _build_protocol(REAL_COMMIT, code_sha256),
                ROOT,
                # Need to match the set exactly, so we must adjust REQUIRED_CODE_PATHS too.
                tuple(
                    p if p != "metamorphosis/m074_ablation_arms.py"
                    else "nonexistent/module.py"
                    for p in REQUIRED_CODE_PATHS
                ),
            )