from __future__ import annotations

from dataclasses import replace

import pytest

from metamorphosis.m039_lineage import (
    CycleManifest,
    LineageManifest,
    M039IntegrityError,
    ReplayInputs,
    ToolUse,
    compose_lineage_tool,
    derive_cycle_seed,
    derive_lineage_id,
    gate2_eligible,
    protocol_primitive_tool,
    verify_replayed_manifest,
)


def h(symbol: str) -> str:
    assert len(symbol) == 1
    return symbol * 64


def program(name: str):
    return ({"operation": name, "argument": 0},)


def primitive(lineage_id: str, commitment: str, ordinal: int = 0):
    return protocol_primitive_tool(
        lineage_id=lineage_id,
        protocol_commitment=commitment,
        primitive_name=f"p{ordinal}",
        program=program(f"primitive-{ordinal}"),
        ordinal=ordinal,
    )


def cycle(
    index: int,
    *,
    start: str,
    end: str,
    used=(),
    constructed=(),
) -> CycleManifest:
    symbol = str(index)
    return CycleManifest(
        cycle=index,
        cycle_seed=index,
        starting_body_digest=start,
        target_digest=h(chr(ord("a") + index)),
        ending_body_digest=end,
        evidence_digest=h(chr(ord("d") + index)),
        certificate_digest=h(chr(ord("g") + index)),
        compact_trace_head=h(chr(ord("j") + index)),
        checkpoint_digest=h(chr(ord("m") + index)),
        journal_head=h(chr(ord("p") + index)),
        decision_transcript_digest=h(chr(ord("s") + index)),
        accepted_candidate_id=h(chr(ord("v") + index)),
        accepted_program_digest=h(chr(ord("y") + index)),
        used_tool_ids=tuple(used),
        constructed_tool_ids=tuple(constructed),
        rollback_restored_exactly=True,
        functional_counters={"operations": index},
        audit_counters={"operations": index + 10},
    )


def manifest() -> LineageManifest:
    commitment = "m039-development"
    lineage_id = derive_lineage_id(39, commitment)
    p0 = primitive(lineage_id, commitment)
    construction_event = h("1")
    macro = compose_lineage_tool(
        lineage_id=lineage_id,
        protocol_commitment=commitment,
        introduced_cycle=1,
        introduced_by_event=construction_event,
        input_tools=(p0,),
        program=({"operation": "primitive-0", "argument": 0},),
    )
    use = ToolUse(
        tool_id=macro.tool_id,
        cycle=2,
        candidate_id=h("2"),
        adopted=True,
        proposing_block_index=0,
    )
    c1 = cycle(1, start=h("a"), end=h("b"), constructed=(macro.tool_id,))
    c2 = cycle(2, start=h("b"), end=h("c"), used=(macro.tool_id,))
    c3 = cycle(3, start=h("c"), end=h("d"), used=(macro.tool_id,))
    return LineageManifest(
        master_seed=39,
        protocol_commitment=commitment,
        lineage_id=lineage_id,
        initial_body_digest=h("a"),
        cycles=(c1, c2, c3),
        tool_registry=(p0, macro),
        tool_uses=(use,),
        ablation_required_tool_ids=(macro.tool_id,),
        final_body_digest=h("d"),
    )


def test_cycle_seed_derivation_is_stable_and_cycle_separated():
    first = derive_cycle_seed(39, 1, "commitment")
    assert first == derive_cycle_seed(39, 1, "commitment")
    assert len({derive_cycle_seed(39, cycle, "commitment") for cycle in (1, 2, 3)}) == 3


def test_a_protocol_primitive_never_becomes_gate2_eligible():
    commitment = "m039-development"
    lineage_id = derive_lineage_id(39, commitment)
    tool = primitive(lineage_id, commitment)
    use = ToolUse(tool.tool_id, 2, h("2"), True, 0)

    assert not gate2_eligible(
        tool,
        valid_construction_event_hashes=(h("1"),),
        registry_before_construction=(),
        uses=(use,),
        ablation_required_tool_ids=(tool.tool_id,),
    )


def test_a_lineage_composition_requires_inputs_that_predate_construction():
    commitment = "m039-development"
    lineage_id = derive_lineage_id(39, commitment)
    birth = primitive(lineage_id, commitment)
    first = compose_lineage_tool(
        lineage_id=lineage_id,
        protocol_commitment=commitment,
        introduced_cycle=1,
        introduced_by_event=h("1"),
        input_tools=(birth,),
        program=program("macro-1"),
    )

    with pytest.raises(M039IntegrityError, match="predate"):
        compose_lineage_tool(
            lineage_id=lineage_id,
            protocol_commitment=commitment,
            introduced_cycle=1,
            introduced_by_event=h("2"),
            input_tools=(first,),
            program=program("illegal-same-cycle-extension"),
        )


def test_gate2_eligibility_is_computed_from_event_inputs_later_use_and_ablation():
    commitment = "m039-development"
    lineage_id = derive_lineage_id(39, commitment)
    birth = primitive(lineage_id, commitment)
    event_hash = h("1")
    tool = compose_lineage_tool(
        lineage_id=lineage_id,
        protocol_commitment=commitment,
        introduced_cycle=1,
        introduced_by_event=event_hash,
        input_tools=(birth,),
        program=program("macro"),
    )
    later_use = ToolUse(tool.tool_id, 2, h("2"), True, 0)

    assert gate2_eligible(
        tool,
        valid_construction_event_hashes=(event_hash,),
        registry_before_construction=(birth.tool_id,),
        uses=(later_use,),
        ablation_required_tool_ids=(tool.tool_id,),
    )
    assert not gate2_eligible(
        tool,
        valid_construction_event_hashes=(),
        registry_before_construction=(birth.tool_id,),
        uses=(later_use,),
        ablation_required_tool_ids=(tool.tool_id,),
    )
    assert not gate2_eligible(
        tool,
        valid_construction_event_hashes=(event_hash,),
        registry_before_construction=(),
        uses=(later_use,),
        ablation_required_tool_ids=(tool.tool_id,),
    )
    assert not gate2_eligible(
        tool,
        valid_construction_event_hashes=(event_hash,),
        registry_before_construction=(birth.tool_id,),
        uses=(),
        ablation_required_tool_ids=(tool.tool_id,),
    )
    assert not gate2_eligible(
        tool,
        valid_construction_event_hashes=(event_hash,),
        registry_before_construction=(birth.tool_id,),
        uses=(later_use,),
        ablation_required_tool_ids=(),
    )


def test_same_cycle_membership_is_not_later_causal_reuse():
    commitment = "m039-development"
    lineage_id = derive_lineage_id(39, commitment)
    birth = primitive(lineage_id, commitment)
    event_hash = h("1")
    tool = compose_lineage_tool(
        lineage_id=lineage_id,
        protocol_commitment=commitment,
        introduced_cycle=1,
        introduced_by_event=event_hash,
        input_tools=(birth,),
        program=program("macro"),
    )
    same_cycle = ToolUse(tool.tool_id, 1, h("2"), True, 0)

    assert not gate2_eligible(
        tool,
        valid_construction_event_hashes=(event_hash,),
        registry_before_construction=(birth.tool_id,),
        uses=(same_cycle,),
        ablation_required_tool_ids=(tool.tool_id,),
    )


def test_manifest_requires_one_contiguous_three_cycle_lineage():
    good = manifest()
    assert good.digest() == good.digest()

    broken_second = replace(good.cycles[1], starting_body_digest=h("f"))
    with pytest.raises(M039IntegrityError, match="contiguous"):
        replace(good, cycles=(good.cycles[0], broken_second, good.cycles[2]))

    with pytest.raises(M039IntegrityError, match="cycles 1, 2 and 3"):
        replace(good, cycles=good.cycles[:2])


def test_manifest_digest_changes_when_a_decision_anchor_changes():
    good = manifest()
    altered_cycle = replace(good.cycles[2], journal_head=h("e"))
    altered = replace(good, cycles=(good.cycles[0], good.cycles[1], altered_cycle))
    assert altered.digest() != good.digest()


def test_replay_inputs_contain_anchors_but_no_generated_outputs():
    good = manifest()
    replay = ReplayInputs(
        master_seed=good.master_seed,
        protocol_commitment=good.protocol_commitment,
        primitive_registry_digest=h("f"),
        expected_manifest_digest=good.digest(),
        expected_final_body_digest=good.final_body_digest,
        expected_cycle_journal_heads=tuple(c.journal_head for c in good.cycles),
    )
    fields = set(replay.mapping())

    assert "founder" not in fields
    assert "targets" not in fields
    assert "observations" not in fields
    assert "accepted_programs" not in fields
    assert "tool_registry" not in fields
    assert "final_body" not in fields
    verify_replayed_manifest(good, replay)


def test_replay_verification_rejects_a_different_head_or_final_body():
    good = manifest()
    replay = ReplayInputs(
        master_seed=good.master_seed,
        protocol_commitment=good.protocol_commitment,
        primitive_registry_digest=h("f"),
        expected_manifest_digest=good.digest(),
        expected_final_body_digest=good.final_body_digest,
        expected_cycle_journal_heads=tuple(c.journal_head for c in good.cycles),
    )

    with pytest.raises(M039IntegrityError, match="journal heads"):
        verify_replayed_manifest(
            good,
            replace(
                replay,
                expected_cycle_journal_heads=(h("0"),) + replay.expected_cycle_journal_heads[1:],
            ),
        )

    with pytest.raises(M039IntegrityError, match="final body"):
        verify_replayed_manifest(good, replace(replay, expected_final_body_digest=h("0")))
