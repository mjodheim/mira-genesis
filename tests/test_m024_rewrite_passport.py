from __future__ import annotations

import hashlib
import json

import pytest

from metamorphosis.m020_self_rewrite import (
    Case,
    SelfRewriteEngine,
    ToolRegistry,
    VersionedCodeBody,
    apply_patch,
    evaluate_source,
)
from metamorphosis.m024_rewrite_passport import (
    InvalidPassport,
    create_passport,
    export_passport,
    import_passport,
)


BROKEN = """\
def policy(x):
    if x >= 0:
        return x + 0
    return -x + 0
"""

DEVELOPMENT = (
    Case((-3,), 4),
    Case((-1,), 2),
    Case((1,), 2),
    Case((3,), 4),
)

HELD_OUT = (
    Case((-21,), 22),
    Case((0,), 1),
    Case((34,), 35),
)


def _learned_state():
    registry = ToolRegistry()
    engine = SelfRewriteEngine(registry, max_edits=2, beam_width=32)
    body = VersionedCodeBody("policy", BROKEN)
    result = engine.improve(body.active_source, body.function_name, DEVELOPMENT)
    assert result.adopted
    assert body.adopt(result)
    return body, registry, result


def _repack(envelope: dict[str, object]) -> str:
    payload = envelope["payload"]
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    envelope["payload_sha256"] = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()
    return json.dumps(envelope, sort_keys=True, separators=(",", ":"))


def test_complete_rewrite_state_round_trips_exactly():
    body, registry, result = _learned_state()

    raw = export_passport(body, registry)
    migrated_body, migrated_registry, passport = import_passport(raw)

    assert migrated_body.function_name == body.function_name
    assert migrated_body.active_source == body.active_source
    assert migrated_body.archive == body.archive
    assert migrated_body.adopted_digests == body.adopted_digests
    assert migrated_body.run(-9) == 10
    assert evaluate_source(migrated_body.active_source, "policy", HELD_OUT).perfect

    assert [tool.name for tool in migrated_registry.learned] == [
        tool.name for tool in registry.learned
    ]
    assert migrated_registry.learned[0].operations == result.selected.trace
    assert passport.sha256() == create_passport(body, registry).sha256()


def test_learned_tool_remains_reusable_after_migration():
    body, registry, result = _learned_state()
    del body, registry
    _, migrated_registry, _ = import_passport(
        export_passport(*_learned_state()[:2])
    )
    structurally_similar = """\
def policy(value):
    if value >= 0:
        return value + 0
    return -value + 0
"""

    proposals = tuple(migrated_registry.learned[0].propose(structurally_similar))

    assert proposals == (result.selected.trace,)
    rewritten = apply_patch(structurally_similar, proposals[0])
    assert evaluate_source(rewritten, "policy", HELD_OUT).perfect


def test_rollback_survives_passport_migration():
    body, registry, _ = _learned_state()
    migrated_body, _, _ = import_passport(export_passport(body, registry))

    assert migrated_body.rollback()
    assert migrated_body.active_source == BROKEN
    assert migrated_body.run(-9) == 9


def test_export_is_canonical_and_deterministic():
    body, registry, _ = _learned_state()

    first = export_passport(body, registry)
    second = export_passport(body, registry)

    assert first == second
    assert json.loads(first)["payload_sha256"]


def test_envelope_tampering_is_rejected_before_rehydration():
    body, registry, _ = _learned_state()
    envelope = json.loads(export_passport(body, registry))
    envelope["payload"]["active_source"] = BROKEN

    with pytest.raises(InvalidPassport, match="digest mismatch"):
        import_passport(json.dumps(envelope))


def test_semantically_forged_active_source_is_rejected_even_with_new_envelope_hash():
    body, registry, _ = _learned_state()
    envelope = json.loads(export_passport(body, registry))
    envelope["payload"]["active_source"] = BROKEN

    with pytest.raises(InvalidPassport, match="latest adopted digest"):
        import_passport(_repack(envelope))


def test_forged_learned_tool_name_is_rejected():
    body, registry, _ = _learned_state()
    envelope = json.loads(export_passport(body, registry))
    envelope["payload"]["learned_tools"][0]["name"] = "learned_patch_forged"

    with pytest.raises(InvalidPassport, match="name does not match"):
        import_passport(_repack(envelope))


def test_invalid_primitive_configuration_is_rejected():
    body, registry, _ = _learned_state()
    envelope = json.loads(export_passport(body, registry))
    envelope["payload"]["primitive_tools"][0]["values"] = []

    with pytest.raises(InvalidPassport, match="non-empty"):
        import_passport(_repack(envelope))
