from __future__ import annotations

import hashlib
import json

import select_m070_external_tasks as selection


def test_m070_committed_inventory_reproduces_frozen_selection_rule() -> None:
    protocol = json.loads(selection.PROTOCOL.read_text(encoding="utf-8"))
    artifact_path = selection.ROOT / "experiments" / "M070" / "TASK_SELECTION.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    salt = bytes.fromhex(protocol["selection_salt_utf8_hex"])
    inventory = artifact["inventory"]
    assert len(inventory) == artifact["inventory_count"] == 89
    assert len({identifier for _, identifier in inventory}) == 89
    assert inventory == sorted(inventory)
    for digest, identifier in inventory:
        assert digest == hashlib.sha256(salt + identifier.encode("utf-8")).hexdigest()
    assert artifact["inventory_sha256"] == hashlib.sha256(json.dumps(
        inventory, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()
    assert artifact["selected"] == inventory[:protocol["selection_count"]] == [
        [
            "021fd05341f6812e2a884b419b932f69af728ebf415425f6b931f32c9122bcbc",
            "rstan-to-pystan",
        ],
        [
            "03b8fb3cbff0c024e7665f5c0de01ca07dc89eb87ed3fda5ac7208fd3582ddc7",
            "llm-inference-batching-scheduler",
        ],
    ]
    assert artifact["replacement_permitted"] is False
    assert artifact["task_content_inspected_before_selection"] is False
    assert artifact["task_executed"] is False
