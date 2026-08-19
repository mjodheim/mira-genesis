"""Draw and evaluate M094's qualification — a separate process, by design.

`experiments/M094/PROTOCOL.json` commits to this shape:

    "drawn_by": "a separate process, with a salt derived from the adopted mechanism's own
                 digest, which does not exist until adoption"
    "draw_rule": "Order entries by sha256(entry_digest + adopted mechanism digest) and take
                  the first two whose components differ."

So this is a script and not a lineage module, and the separation is structural rather than
promised: `metamorphosis/m094_lineage.py` never imports this file, never reads
`experiments/`, and `tests/test_m094_qualification_pool.py` fails if any module the lineage
runs can reach the pool. The salt is supplied on the command line by whoever has already
adopted; nothing here can invent it, because the mechanism digest does not exist until a
candidate has been adopted.

What this does **not** claim: experimenter blindness. The pool was authored by someone who
had seen the development result, and the protocol says so. What is claimed is reachability
— that the lineage cannot read the pool before adoption — and that is what the boundary test
enforces.

Usage:
    python -m scripts.materialize_m094_qualification --mechanism-digest <hex> \
        [--out experiments/M094/QUALIFICATION.json]

Without ``--out`` it prints the materialized qualification and writes nothing. Writing into
`experiments/M094/` is a scientific act and requires ``--arm``.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m094_lineage import (  # noqa: E402
    behavioural_cases,
    sandbox_component,
    validate_independently,
)

POOL_PATH = ROOT / "experiments" / "M094" / "QUALIFICATION_POOL.json"
QUALIFICATION_SCHEMA = "m094-qualification-v1"

#: The protocol fixes both numbers at the freeze.
ENTRIES_PER_QUALIFICATION = 2
HIDDEN_CASES_PER_REQUIREMENT = 5


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("ascii")).hexdigest()


def draw(pool: dict, mechanism_digest: str) -> list[dict]:
    """Apply the frozen draw rule, exactly as the protocol words it.

    Order by ``sha256(entry_digest + mechanism_digest)``, then take the first entries whose
    components differ. The cross-component requirement is the point: a repair mechanism
    specialised to the component it grew on fails here.
    """

    if not mechanism_digest or len(mechanism_digest) != 64:
        raise SystemExit("a 64-character adopted mechanism digest is required")

    ordered = sorted(
        pool["entries"],
        key=lambda entry: hashlib.sha256(
            (entry["entry_digest"] + mechanism_digest).encode("ascii")
        ).hexdigest(),
    )
    drawn: list[dict] = []
    seen: set[str] = set()
    for entry in ordered:
        if entry["component"] in seen:
            continue
        drawn.append(entry)
        seen.add(entry["component"])
        if len(drawn) == ENTRIES_PER_QUALIFICATION:
            break
    if len(drawn) < ENTRIES_PER_QUALIFICATION:
        raise SystemExit("the pool cannot supply two entries on distinct components")
    return drawn


def _requirement_triples(entry: dict) -> list[tuple[str, str, str | None]]:
    return [(item["key"], item["field"], item["wrapper"]) for item in entry["requirement"]]


def apply_mechanism(root: Path, entry: dict, max_length: int | None = None) -> str | None:
    """Run the adopted mechanism against a drawn entry's component.

    Imported here rather than in the lineage, so the mechanism is exercised on the drawn
    component without the lineage ever having learned that the component exists. No new
    operation may be added during qualification, and none is: this calls the same
    `suggest_operations` the development run called.
    """

    from metamorphosis.m094_diagnosis import _encode_rendering  # noqa: PLC0415
    from metamorphosis.m094_synthesis import suggest_operations  # noqa: PLC0415

    detail = _encode_rendering([
        (item["key"], item["field"], item["wrapper"]) for item in entry["requirement"]
    ])
    operations = suggest_operations(
        root, entry["component"], entry["class"], entry["capability"],
        entry["class"], detail, max_length=max_length,
    )
    if not operations:
        return None
    source = (root / entry["component"]).read_text(encoding="utf-8")
    try:
        return operations[0].apply(source)
    except Exception:
        return None


def evaluate_entry(root: Path, entry: dict) -> dict:
    """Does the adopted mechanism close this drawn requirement, when executed?

    The hidden cases committed in the pool are used as well as freshly derived ones, so a
    mechanism that happened to satisfy the pool's five recorded cases and nothing else is
    still caught.
    """

    modified = apply_mechanism(root, entry)
    requirement = _requirement_triples(entry)
    record: dict[str, object] = {
        "component": entry["component"],
        "class": entry["class"],
        "capability": entry["capability"],
        "entry_digest": entry["entry_digest"],
        "requirement": [list(item) for item in requirement],
        "mechanism_produced_a_candidate": modified is not None,
    }
    if modified is None:
        record["outcome"] = "refuted"
        record["satisfied"] = False
        record["reason"] = "the mechanism produced no candidate for this component"
        return record

    hidden = tuple(case["fields"] for case in entry["hidden_cases"])
    derived = behavioural_cases(
        root, entry["component"], entry["class"],
        count=HIDDEN_CASES_PER_REQUIREMENT, seed="m094-qualification-cases-v1",
    )
    before = sandbox_component(
        root, entry["component"], (root / entry["component"]).read_text(encoding="utf-8"),
        entry["class"], requirement, hidden + derived, variant="qualification_original",
    )
    after = sandbox_component(
        root, entry["component"], modified, entry["class"], requirement,
        hidden + derived, variant="qualification_candidate",
    )
    validation = validate_independently(
        root, entry["component"], modified, entry["class"], requirement,
        seed="m094-qualification-validator-v1",
    )

    record["hidden_cases"] = len(hidden)
    record["derived_cases"] = len(derived)
    record["original"] = before.to_dict()
    record["candidate"] = after.to_dict()
    record["validation"] = validation.to_dict()

    # An entry whose cases cannot construct their class is `unrunnable`, and unrunnable is
    # not the same as unsatisfied. The audit found seven of the nine frozen entries carrying
    # hidden cases that raise on construction -- the requirements were measured, the case
    # values were synthesised and never executed. Scoring those as refutations would let the
    # instrument's own defect masquerade as evidence against H39, so the outcome is reported
    # as a third state and the verdict may not read it as a failure.
    if not before.runnable:
        record["outcome"] = "unrunnable"
        record["satisfied"] = None
        record["reason"] = (
            f"no case constructs {entry['class']}: "
            f"{before.cases_constructible}/{before.cases_total} constructible. "
            "The entry measures nothing about the mechanism."
        )
        return record

    record["satisfied"] = bool(
        not before.supplies_the_capability
        and after.supplies_the_capability
        and validation.accepted
    )
    record["outcome"] = "satisfied" if record["satisfied"] else "refuted"
    if not record["satisfied"]:
        record["reason"] = (
            f"original_supplied={before.supplies_the_capability}, "
            f"candidate_supplied={after.supplies_the_capability}, "
            f"validator_accepted={validation.accepted}, "
            f"constructible={before.cases_constructible}/{before.cases_total}"
        )
    return record


def materialize(root: Path, mechanism_digest: str) -> dict:
    """Draw, then measure. Nothing here can be re-rolled: the salt fixes the draw."""

    pool = json.loads(POOL_PATH.read_text(encoding="utf-8"))
    recomputed = _digest({k: v for k, v in pool.items() if k != "pool_digest"})
    drawn = draw(pool, mechanism_digest)
    entries = [evaluate_entry(root, entry) for entry in drawn]
    result = {
        "schema": QUALIFICATION_SCHEMA,
        "milestone": "M094",
        "salt_is_the_adopted_mechanism_digest": True,
        "drawn_after_adoption": True,
        "mechanism_digest": mechanism_digest,
        "pool_path": POOL_PATH.relative_to(ROOT).as_posix(),
        "pool_digest_recomputed": recomputed,
        "pool_digest_matches_committed": recomputed == pool.get("pool_digest"),
        "entries_drawn": len(entries),
        "components_drawn": sorted({item["component"] for item in entries}),
        "cross_component": len({item["component"] for item in entries}) >= 2,
        "entries": entries,
        "satisfied_count": sum(1 for item in entries if item.get("outcome") == "satisfied"),
        "refuted_count": sum(1 for item in entries if item.get("outcome") == "refuted"),
        "unrunnable_count": sum(1 for item in entries if item.get("outcome") == "unrunnable"),
    }
    # A qualification containing an unrunnable entry is incomplete, not negative. The
    # distinction is the whole reason the third outcome exists.
    result["complete"] = result["unrunnable_count"] == 0
    result["verdict"] = (
        "incomplete" if result["unrunnable_count"]
        else ("positive" if result["refuted_count"] == 0 else "negative")
    )
    result["qualification_digest"] = _digest(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mechanism-digest", required=True,
                        help="the adopted mechanism's digest; the draw's salt")
    parser.add_argument("--root", default=str(ROOT),
                        help="repository root to qualify against (a worktree copy, normally)")
    parser.add_argument("--out", default=None, help="where to write the qualification")
    parser.add_argument(
        "--arm", action="store_true",
        help="required to write into experiments/M094/, which is a scientific act",
    )
    args = parser.parse_args()

    result = materialize(Path(args.root).resolve(), args.mechanism_digest)

    if args.out:
        out = Path(args.out)
        canonical = out.resolve()
        inside_experiment = canonical.parent == (ROOT / "experiments" / "M094")
        if inside_experiment and not args.arm:
            print(
                "Refusing to write into experiments/M094/ without --arm. Materializing a\n"
                "qualification there is a scientific act and the protocol forbids repairing\n"
                "a result after a verdict; pass --arm deliberately or write elsewhere.",
                file=sys.stderr,
            )
            return 2
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(_canonical_json(result) + "\n", encoding="utf-8", newline="\n")
        print(f"Qualification written to {out}")

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
