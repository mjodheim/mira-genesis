from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

import pytest

import metamorphosis.m066_canonical_governance as m066
from check_m066_canonical_guard import ARM_MESSAGE, GuardError, inspect_arm
from check_m066_frozen_protocol import FrozenProtocolError, validate_frozen_protocol
from reproduce_m066_canonical import main as reproduce_main


HEAD = "a" * 40
PARENT = "b" * 40


@pytest.fixture(scope="session")
def manifests():
    return [m066.run_m066_development(index) for index in range(len(m066.M066_TASK_BANK))]


@pytest.fixture(scope="session")
def canonical_manifest():
    return m066.run_m066_canonical("1" * 40)


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    committed = tmp_path / "generator.py"
    committed.write_text("VALUE = 1\n", encoding="utf-8")
    frozen = tmp_path / "FROZEN_PROTOCOL.json"
    frozen.write_text(
        json.dumps(
            {
                "schema": "m066-frozen-protocol/1",
                "protocol": m066.M066_PROTOCOL,
                "protocol_sha256": m066.M066_PROTOCOL_SHA256,
                "task_bank_commitment": m066.M066_PROTOCOL["task_bank_commitment"],
                "task_bank_entry_count": 4,
                "canonical_execution": {
                    "marker_history_scope": "first_parent_of_pushed_main_head"
                },
                "file_sha256": {
                    str(committed): hashlib.sha256(
                        committed.read_bytes().replace(b"\r\n", b"\n")
                    ).hexdigest()
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    marker = tmp_path / "CANONICAL_ARMED.json"
    marker.write_text(
        json.dumps(
            {
                "schema": "m066-canonical-arm/1",
                "frozen_parent_sha": PARENT,
                "protocol_sha256": m066.M066_PROTOCOL_SHA256,
                "frozen_protocol_file_sha256": hashlib.sha256(
                    frozen.read_bytes().replace(b"\r\n", b"\n")
                ).hexdigest(),
                "task_bank_commitment": m066.M066_PROTOCOL["task_bank_commitment"],
                "first_run_only": True,
                "reruns_are_reproductions_only": True,
                "independent_reproduction_required": True,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return marker, frozen


def _inspect(marker: Path, frozen: Path, *, history: int = 1):
    return inspect_arm(
        head_sha=HEAD,
        parent_sha=PARENT,
        commit_message=ARM_MESSAGE,
        changed_files=(str(marker),),
        marker_first_parent_history_count=history,
        marker_path=marker,
        frozen_protocol_path=frozen,
    )


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_first_parent_marker_only_commit_arms(tmp_path: Path) -> None:
    marker, frozen = _fixture(tmp_path)
    assert _inspect(marker, frozen)["frozen_parent_sha"] == PARENT


def test_updated_deleted_or_readded_marker_on_main_is_rejected(tmp_path: Path) -> None:
    marker, frozen = _fixture(tmp_path)
    with pytest.raises(GuardError, match="first canonical first-parent"):
        _inspect(marker, frozen, history=2)


def test_first_parent_history_ignores_lateral_pull_request_ref(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "M066 Test")
    _git(repository, "config", "user.email", "m066@example.invalid")
    (repository / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(repository, "add", "seed.txt")
    _git(repository, "commit", "-m", "seed")
    _git(repository, "switch", "-c", "pull-request")
    marker = repository / "experiments" / "M066" / "CANONICAL_ARMED.json"
    marker.parent.mkdir(parents=True)
    marker.write_text("{}\n", encoding="utf-8")
    _git(repository, "add", "experiments/M066/CANONICAL_ARMED.json")
    _git(repository, "commit", "-m", "lateral marker")
    _git(repository, "switch", "main")
    marker.parent.mkdir(parents=True)
    marker.write_text("{}\n", encoding="utf-8")
    _git(repository, "add", "experiments/M066/CANONICAL_ARMED.json")
    _git(repository, "commit", "-m", "canonical marker")
    canonical = _git(
        repository,
        "rev-list",
        "--first-parent",
        "HEAD",
        "--",
        "experiments/M066/CANONICAL_ARMED.json",
    ).splitlines()
    all_refs = _git(
        repository,
        "rev-list",
        "--all",
        "--",
        "experiments/M066/CANONICAL_ARMED.json",
    ).splitlines()
    assert len(canonical) == 1
    assert len(all_refs) == 2


def test_m066_changes_governance_only() -> None:
    protocol = m066.M066_PROTOCOL
    assert protocol["base_protocol_sha256"] == m066.base.M065_PROTOCOL_SHA256
    assert protocol["task_bank_commitment"] == m066.base.M065_PROTOCOL["task_bank_commitment"]
    assert protocol["scientific_changes"] == []
    assert protocol["candidate_budget_per_arm_cycle"] == 8_192
    assert protocol["accepted_post_migration_cycles"] == 3
    assert protocol["arms"] == list(m066.base.M065_PROTOCOL["arms"])


def test_all_four_banks_preserve_the_frozen_m065_outcome(manifests) -> None:
    for manifest in manifests:
        value = manifest.to_dict()
        outcome = value["base_m065_manifest"]["base_manifest"]
        assert outcome["strict_held_out_advantage"] is True
        assert outcome["complete_final_version"] == 12
        assert outcome["complete_final_retained_passed"] == 68
        assert outcome["arm_results"]["complete_continued_lineage"]["held_out_quality"] == {
            "hidden_passes": 18,
            "hidden_total": 18,
            "exact": True,
        }
        for name in m066.M066_PROTOCOL["arms"][1:]:
            assert outcome["arm_results"][name]["held_out_quality"]["hidden_passes"] == 0


def test_m065_negative_attempt_is_preserved_without_bank_selection(manifests) -> None:
    for manifest in manifests:
        value = manifest.to_dict()
        assert value["m065_negative_canonical_run"] == 31287477458
        assert value["m065_negative_guard_job"] == 93178824313
        assert value["m065_bank_selected"] is False
        assert value["m065_first_result_created"] is False
        assert value["m065_reproduction_created"] is False


def test_canonical_wrapper_records_m066_selection_without_reauthorising_m065(
    canonical_manifest,
) -> None:
    value = canonical_manifest.to_dict()
    nested = value["base_m065_manifest"]
    assert value["canonical_workflow_authorised"] is True
    assert value["selection_mode"] == "m066_marker_parent_commitment"
    assert value["marker_parent_sha"] == "1" * 40
    assert nested["selection_mode"] == "m066_marker_parent_commitment"
    assert nested["marker_parent_sha"] == "1" * 40
    assert nested["canonical_workflow_authorised"] is False


def test_repository_frozen_protocol_matches_all_committed_sources() -> None:
    value = validate_frozen_protocol()
    assert value["protocol_sha256"] == m066.M066_PROTOCOL_SHA256


def test_portable_hash_rejects_real_source_drift(tmp_path: Path) -> None:
    _marker, frozen = _fixture(tmp_path)
    data = json.loads(frozen.read_text(encoding="utf-8"))
    source = Path(next(iter(data["file_sha256"])))
    source.write_text("VALUE = 2\n", encoding="utf-8")
    with pytest.raises(FrozenProtocolError, match="source drifted"):
        validate_frozen_protocol(frozen)


def test_workflow_scopes_history_and_never_recreates_first_result() -> None:
    source = Path(".github/workflows/m066-canonical.yml").read_text(encoding="utf-8")
    assert "git rev-list --first-parent HEAD" in source
    assert "git rev-list --all" not in source
    assert "github.run_attempt == 1" in source
    assert "marker-first-parent-history-count" in source
    assert "fetch-depth: 0" in source


def test_reproduction_entrypoint_is_importable() -> None:
    assert callable(reproduce_main)
