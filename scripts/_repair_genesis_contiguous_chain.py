"""One-shot DEVELOPMENT repair for contiguous causal-chain reporting.

Deleted together with its branch-only workflow after focused validation passes.
"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"{label} anchor changed")
    return text.replace(old, new, 1)


def repair_loop() -> None:
    path = ROOT / "genesis" / "loop.py"
    text = path.read_text(encoding="utf-8")
    old = '''        acquisitions = list(self.state["acquisitions"])
        length = 0
        for acquisition in reversed(acquisitions):
            if not (acquisition.get("causal_dependency") or {}).get("established"):
                break
            length += 1
        return {
'''
    new = '''        acquisitions = list(self.state["acquisitions"])
        length = 0
        # A chain link is local: generation n must have been shown to need generation n-1.
        # An established dependency on some older held acquisition is real evidence about that
        # older acquisition, but it does not make the acquisition sequence contiguous.
        for index in range(len(acquisitions) - 1, 0, -1):
            acquisition = acquisitions[index]
            causal = acquisition.get("causal_dependency") or {}
            predecessor = acquisitions[index - 1]
            if not causal.get("established"):
                break
            if causal.get("depends_on") != predecessor.get("name"):
                break
            length += 1
        return {
'''
    text = replace_once(text, old, new, "causal_chain body")
    old_doc = '''        A run of acceptances is not a chain. This counts the consecutive acquisitions, ending at the
        most recent, whose dependency on the one before was established by ablation — so a claim
        about recursive improvement has to read a number that can be small.
'''
    new_doc = '''        A run of acceptances is not a chain. This counts the consecutive acquisitions, ending at the
        most recent, whose dependency on the *immediately preceding acquisition* was established by
        ablation. A dependency that skips a generation is evidence, but not a contiguous link — so
        a claim about recursive improvement has to read a number that can be small.
'''
    text = replace_once(text, old_doc, new_doc, "causal_chain docstring")
    path.write_text(text, encoding="utf-8")


def repair_tests() -> None:
    path = ROOT / "tests" / "test_genesis_loop.py"
    tests = path.read_text(encoding="utf-8")
    anchor = '''def test_the_chain_report_counts_links_without_grading_them():
    genesis = _genesis()
    _cycle_with(genesis, bodies.migrated_parent_body, name=bodies.ACQUIRED_COMPONENT)
    _cycle_with(
        genesis,
        bodies.migrated_improved_body,
        depends_on=bodies.ACQUIRED_COMPONENT,
        name=bodies.SECOND_ACQUISITION,
    )
    _cycle_with(
        genesis,
        bodies.migrated_further_body,
        depends_on=bodies.SECOND_ACQUISITION,
        name="third",
    )
    chain = genesis.causal_chain()
    assert chain["acquisitions"] == 3
    assert chain["established_links"] == 2
    assert "is_a_chain_rather_than_a_sequence" not in chain
'''
    regression = anchor + '''

def test_the_chain_report_refuses_an_established_link_that_skips_a_generation():
    """An n -> n-2 dependency is evidence, but it is not the n -> n-1 link a chain needs."""
    genesis = _genesis()
    _cycle_with(genesis, bodies.migrated_parent_body, name=bodies.ACQUIRED_COMPONENT)
    _cycle_with(
        genesis,
        bodies.migrated_improved_body,
        depends_on=bodies.ACQUIRED_COMPONENT,
        name=bodies.SECOND_ACQUISITION,
    )
    _cycle_with(
        genesis,
        bodies.migrated_further_body,
        depends_on=bodies.SECOND_ACQUISITION,
        name="third",
    )

    acquisitions = [dict(item) for item in genesis.state["acquisitions"]]
    last = dict(acquisitions[-1])
    causal = dict(last["causal_dependency"])
    assert causal["established"] is True
    causal["depends_on"] = acquisitions[0]["name"]
    last["causal_dependency"] = causal
    acquisitions[-1] = last
    genesis.state = st.create_state(
        body_digest=genesis.state["body_digest"],
        components=genesis.state["components"],
        vocabulary=genesis.state["vocabulary"],
        tools=genesis.state["tools"],
        acquisitions=acquisitions,
        observations=genesis.state["observations"],
        generation=genesis.state["generation"],
    )

    chain = genesis.causal_chain()
    assert chain["acquisitions"] == 3
    assert chain["established_links"] == 0
    assert chain["makes_no_recursion_claim"] is True
'''
    tests = replace_once(tests, anchor, regression, "chain positive test")
    path.write_text(tests, encoding="utf-8")


def write_audit() -> None:
    path = ROOT / "docs" / "audits" / "GENESIS_CONTIGUOUS_CAUSAL_CHAIN_2026-09-09.md"
    path.write_text(
        '''# Genesis contiguous causal-chain repair — DEVELOPMENT apparatus

**Prepared:** 9 September 2026  
**Status:** runtime metrology repair; no scientific observation; no gate movement.

## Defect

`Genesis.causal_chain()` counted consecutive records whose causal flag was `established`, but did not
verify that each record depended on the immediately preceding acquisition. A generation could name an
older held acquisition, skip its predecessor, and still be counted as part of one continuous chain.

## Repair

The report now walks backward through adjacent acquisition pairs. A link counts only when the current
acquisition both has `established: true` and names the immediately previous acquisition in `depends_on`.
The first mismatch ends the current suffix chain. A skipped-generation dependency remains preserved in
the acquisition record as evidence; it simply does not get relabelled as a contiguous link.

## Regression

A three-acquisition fixture first produces two genuine adjacent links. The last record is then changed
to point to acquisition 1 instead of acquisition 2 while retaining `established: true`. The chain
report must return zero current contiguous links rather than two.

## Boundary

No frozen experiment, result, protocol, sealed bank or scientific decision is changed. This only
narrows the DEVELOPMENT summary emitted by `Genesis.causal_chain()`.
''',
        encoding="utf-8",
    )


if __name__ == "__main__":
    repair_loop()
    repair_tests()
    write_audit()
