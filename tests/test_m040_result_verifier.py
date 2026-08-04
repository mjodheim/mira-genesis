from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from metamorphosis.m040_result_verify import (
    M040ResultVerificationError,
    verify_m040_result,
)

ARTEFACT = Path("results/artifacts/M040_DEVELOPMENT_007.json")
ARTEFACT_SHA256 = "8ecd4e6e08a6c2c9939fa81fc03366d7f92277159fceb9d21fe7cc48f4585197"


@pytest.fixture(scope="module")
def raw_and_payload():
    raw = ARTEFACT.read_bytes()
    return raw, json.loads(raw)


def test_committed_result_007_passes_independent_verification(raw_and_payload) -> None:
    raw, payload = raw_and_payload
    verify_m040_result(payload, raw_bytes=raw, expected_sha256=ARTEFACT_SHA256)


def _set_false(field: str):
    def mutate(payload):
        payload[field] = False
    return mutate


def _migration_not_exact(payload):
    payload["migration"]["exact"] = False


def _wrong_task_family(payload):
    payload["task"]["task_family"] = "prefix_plus_primitive"


def _empty_target(payload):
    payload["task"]["target_states"] = 0


def _invalid_certificate(payload):
    payload["certificate"]["certified_lower_bound"] = payload["certificate"]["body_state_count"]


def _complete_arm_not_exact(payload):
    payload["arms"]["complete_migrated_lineage"]["exact"] = False


def _fresh_arm_exact(payload):
    payload["arms"]["fresh_on_b"]["exact"] = True


def _memory_ablation_exact(payload):
    payload["arms"]["learning_state_ablated"]["exact"] = True


def _tool_ablation_exact(payload):
    payload["arms"]["learned_tool_ablated"]["exact"] = True


def _output_quality_erased(payload):
    payload["arms"]["output_only"]["quality_numerator"] = 0


def _unequal_control_budget(payload):
    payload["arms"]["fresh_on_b"]["counters"]["symbolic_search_nodes"] = 4096


def _accepted_tool_sequence_changed(payload):
    payload["arms"]["complete_migrated_lineage"]["accepted_tool_ids"][0] = "0" * 64


def _task_tool_sequence_changed(payload):
    payload["task"]["generating_tool_ids"][0] = "1" * 64


def _accepted_native_source_changed(payload):
    payload["accepted_native"]["source_digest"] = "2" * 64


def _native_baseline_not_exact(payload):
    payload["control_native_baselines"]["unchanged_parent_migrated"]["exact"] = False


def _audit_counter_changed(payload):
    payload["post_migration_search_audits"]["fresh_on_b"]["symbolic_search_nodes"] += 1


def _audit_digest_erased(payload):
    payload["post_migration_search_audits"]["complete_migrated_lineage"]["transcript_digest"] = ""


def _pre_migration_cycle_reordered(payload):
    payload["pre_migration_search_audits"][0]["cycle"] = 2


def _journal_record_removed(payload):
    payload["journal_records"].pop()
    payload["journal_record_count"] -= 1


def _journal_records_reordered(payload):
    payload["journal_records"][8], payload["journal_records"][9] = (
        payload["journal_records"][9],
        payload["journal_records"][8],
    )


def _journal_head_changed(payload):
    payload["journal_head"] = "3" * 64


def _journal_digest_changed(payload):
    payload["journal_records_sha256"] = "4" * 64


def _migration_budget_exceeded(payload):
    payload["migration"]["probe_calls"] = 121


def _packet_digest_invalid(payload):
    payload["packet_sha256"] = "not-a-sha"


def _control_set_changed(payload):
    payload["arms"].pop("output_only")


MUTATIONS = (
    ("continuity verdict", _set_false("trans_substrate_continuity_supported")),
    ("plasticity verdict", _set_false("post_migration_plasticity_supported")),
    ("replay verdict", _set_false("replay_supported")),
    ("rollback verdict", _set_false("rollback_restored_exactly")),
    ("transported tool attribution", _set_false("accepted_tool_was_pre_migration_owned")),
    ("migration exactness", _migration_not_exact),
    ("task family", _wrong_task_family),
    ("empty target", _empty_target),
    ("incapacity certificate", _invalid_certificate),
    ("complete exact verdict", _complete_arm_not_exact),
    ("fresh control exact", _fresh_arm_exact),
    ("memory ablation exact", _memory_ablation_exact),
    ("tool ablation exact", _tool_ablation_exact),
    ("output-only quality", _output_quality_erased),
    ("unequal control budget", _unequal_control_budget),
    ("accepted tool sequence", _accepted_tool_sequence_changed),
    ("task tool sequence", _task_tool_sequence_changed),
    ("accepted native source", _accepted_native_source_changed),
    ("native baseline exactness", _native_baseline_not_exact),
    ("audit counter", _audit_counter_changed),
    ("audit digest", _audit_digest_erased),
    ("pre-migration cycle", _pre_migration_cycle_reordered),
    ("journal deletion", _journal_record_removed),
    ("journal reordering", _journal_records_reordered),
    ("journal head", _journal_head_changed),
    ("journal digest", _journal_digest_changed),
    ("migration budget", _migration_budget_exceeded),
    ("packet digest format", _packet_digest_invalid),
    ("control set", _control_set_changed),
)


@pytest.mark.parametrize(("name", "mutate"), MUTATIONS, ids=[name for name, _ in MUTATIONS])
def test_each_persisted_result_mutation_is_rejected(raw_and_payload, name, mutate) -> None:
    _, original = raw_and_payload
    payload = deepcopy(original)
    mutate(payload)
    with pytest.raises(M040ResultVerificationError):
        verify_m040_result(payload)
