"""Importable DEVELOPMENT fixtures for endogenous-controller frontier tests.

They stay intentionally small: the tests are about controller continuity, evidence visibility and
step durability, not about the quality of the fixture strategy.
"""
from __future__ import annotations


def stop_as_alpha(_context):
    from genesis.controller import Stop

    return Stop(reason="alpha mechanism")


def stop_as_beta(_context):
    from genesis.controller import Stop

    return Stop(reason="beta mechanism")


def always_regress(_context):
    from genesis.controller import Transform

    return Transform(
        name="regressed",
        body="regressed",
        rationale={"fixture": "produce one durable rejection"},
    )


def react_to_rejection(context):
    """Try one bad candidate, then stop because the retained evidence says why it failed."""
    from genesis.controller import Stop, Transform

    for evidence in context.evidence:
        if evidence.get("kind") != "observation":
            continue
        record = evidence.get("record") or {}
        if record.get("kind") == "rejected_candidate":
            reasons = list(record.get("reasons") or [])
            return Stop(reason="saw retained rejection: %s" % (reasons[0] if reasons else "rejected"))
    return Transform(
        name="regressed",
        body="regressed",
        rationale={"fixture": "create evidence for the next decision"},
    )
