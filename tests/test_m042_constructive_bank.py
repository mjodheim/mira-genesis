from __future__ import annotations

import inspect

from metamorphosis import m042_engine


def test_m042_uses_the_immutable_positive_m040_base_not_the_m041_seed():
    assert m042_engine.BASE_MASTER_SEED == 18_441_616_668_168_956_400
    assert m042_engine.BASE_MASTER_SEED != 4_616_374_729_204_286_922
    assert m042_engine.BASE_PROTOCOL_COMMITMENT == (
        "sha256:4816bc3c32e4fc04df5de4fad784a8935f0b8757c544dbc3862a1d2cb7b59d30"
    )


def test_bank_range_and_minimum_are_fixed_before_selection():
    assert m042_engine.BANK_SEED_START == 420_000
    assert m042_engine.BANK_SEED_ATTEMPTS == 128
    assert m042_engine.MINIMUM_BANK_SIZE == 4
    assert m042_engine.DEVELOPMENT_SELECTION_INDEX == 0


def test_every_bank_entry_runs_full_controls_validation_native_and_rollback():
    source = inspect.getsource(m042_engine._entry_for_seed)

    for required in (
        "generate_lineage_anchor_task",
        "_certificate",
        'arm="complete_continued_lineage"',
        'arm="learning_state_ablated"',
        'arm="fresh_on_b"',
        'arm="learned_tool_ablated"',
        'arm="unchanged_parent_migrated"',
        'arm="output_only"',
        "IsolatedDFAWorkspace().evaluate",
        "_synthesise_native",
        "VersionedNativePair",
        "versioned.rollback()",
    ):
        assert required in source


def test_selection_occurs_only_after_the_whole_bank_is_built_and_replayed():
    source = inspect.getsource(m042_engine.run_m042_development)

    first_bank = source.index("first_bank = _build_bank(base)")
    replay_bank = source.index("replay_bank = _build_bank(base)")
    selection = source.index("selected = first_bank[selected_index]")

    assert first_bank < replay_bank < selection


def test_gate_ten_stays_false_in_development():
    source = inspect.getsource(m042_engine.run_m042_development)

    assert '"gate_10_measurement_integrity": False' in source
    assert "no_sealed_block_opened" in inspect.getsource(
        m042_engine.M042DevelopmentResult.mapping
    )
