from metamorphosis.m012b_dfa import DFA
from metamorphosis.m039_engine import (
    Candidate, _compose_adopted_tool, _tool_atoms, primitive_registry,
)
from metamorphosis.m039_lineage import derive_lineage_id


def test_repeated_invocation_keeps_program_but_deduplicates_dependencies():
    commitment = "m040-duplicate-dependency-regression"
    lineage_id = derive_lineage_id(400041, commitment)
    registry = primitive_registry(lineage_id, commitment)
    tool = registry[0]
    atom = _tool_atoms(tool)[0]
    body = DFA((0, 1), ((0, 0),), (False,), 0)
    candidate = Candidate(
        "0" * 64,
        (0, 0),
        (tool.tool_id, tool.tool_id),
        (atom, atom),
        body,
    )
    composed = _compose_adopted_tool(
        lineage_id=lineage_id,
        protocol_commitment=commitment,
        cycle=1,
        candidate=candidate,
        registry=registry,
    )
    assert composed.input_tool_ids == (tool.tool_id,)
    assert len(composed.program) == 2
