"""Importable DEVELOPMENT fixtures for endogenous-controller frontier tests.

They stay intentionally small: the tests are about controller continuity, evidence visibility,
step durability and generated-candidate construction, not about the quality of the fixture strategy.
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


def generated_search_policy(context):
    """A tiny bounded search policy over program *data*, conditioned on retained rejections.

    The search order is deliberately simple and authored for DEVELOPMENT. What matters here is that
    none of these candidates exists as an importable body in the world: each is constructed from the
    returned operation sequence and judged before the next evidence-conditioned step.
    """
    from genesis.controller import GenerateTransform, Stop

    if any(str(name).startswith("generated:") for name in context.acquisitions):
        return Stop(reason="a generated descendant was adopted")

    rejected = 0
    for evidence in context.evidence:
        if evidence.get("kind") != "observation":
            continue
        record = evidence.get("record") or {}
        if record.get("kind") == "rejected_candidate" and str(record.get("name", "")).startswith(
            "generated:"
        ):
            rejected += 1

    candidates = (
        ("double",),
        ("increment",),
        ("double", "double"),
        ("double", "increment"),
    )
    if rejected >= len(candidates):
        return Stop(reason="bounded generated search exhausted")
    operations = candidates[rejected]
    return GenerateTransform(
        name="generated:%d" % rejected,
        operations=operations,
        rationale={
            "fixture": "next bounded program after %d retained generated rejections" % rejected
        },
    )
