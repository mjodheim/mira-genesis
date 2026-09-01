"""M118 chronology: every stage must be able to prove its predecessors were committed first.

M117 could not claim its route selection was prospectively clean, because its apparatus changed
five times and some of those changes followed real endpoint observations. M118's answer is not a
promise but a proof obligation: each stage names the artifacts that must already exist **as commits
at HEAD**, byte-identical to the working tree, before that stage may run.

    M117 calibration complete
      -> M118/H63 preregistration
      -> fixed OpenInference route
      -> readiness apparatus frozen
      -> readiness DEVELOPMENT run
      -> readiness result committed
      -> H63 plan / spec / request / nonce frozen
      -> complete tested-system freeze committed
      -> unique H63 qualifying generation
      -> machine-only admission
      -> seal, or terminal abort
      -> reveal authorization
      -> one reveal
      -> frozen scoring
      -> independent replay

A file written seconds before a request is not a freeze. A commit is what makes "before" auditable
by someone who was not in the room, which is why an in-memory record can never satisfy any stage
here: `assert_stage_permitted` reads the committed blob and compares it to disk, and refuses on any
difference. There is no parameter through which a caller may supply a record.

Nothing in this module generates, seals, reveals or scores. It refuses.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Mapping

from metamorphosis.m116_chronology import ChronologyError

MILESTONE = "M118"
HYPOTHESIS = "H63"

M117_DIRECTORY = Path("experiments/M117")
DIRECTORY = Path("experiments/M118")

# Predecessor artifacts, each identified by the stage that produces it.
M117_CALIBRATION = M117_DIRECTORY / "STAGE1_ROUTE_QUALIFICATION.json"
M117_OUTCOME = M117_DIRECTORY / "STAGE1_OUTCOME.md"
PREREGISTRATION = DIRECTORY / "PREREGISTRATION.md"
FIXED_ROUTE_MODULE = Path("metamorphosis/m118_route.py")
READINESS_APPARATUS = Path("scripts/audit_m118_readiness.py")
READINESS_RESULT = DIRECTORY / "READINESS_RESULT.json"
ANALYSIS_PLAN = DIRECTORY / "ANALYSIS_PLAN.json"
GENERATOR_SPEC = DIRECTORY / "GENERATOR_SPEC.json"
TESTED_SYSTEM_FREEZE = DIRECTORY / "TESTED_SYSTEM_FREEZE.json"
DELIVERY_LEDGER = DIRECTORY / "DELIVERY_LEDGER.json"
SEALED_BANK = DIRECTORY / "SEALED_BANK.json.gpg"
REVEAL_AUTHORIZATION = DIRECTORY / "REVEAL_AUTHORIZATION.json"
RESULT = DIRECTORY / "RESULT.json"

# Each stage lists what must already be committed at HEAD before it may run. The lists are
# cumulative by construction: a later stage repeats its predecessors rather than trusting that an
# earlier check ran, because nothing guarantees the earlier check ran in this process.
STAGES: dict[str, tuple[Path, ...]] = {
    "preregistration": (M117_CALIBRATION, M117_OUTCOME),
    "readiness_run": (M117_CALIBRATION, M117_OUTCOME, PREREGISTRATION, FIXED_ROUTE_MODULE,
                      READINESS_APPARATUS),
    "scientific_freeze": (M117_CALIBRATION, M117_OUTCOME, PREREGISTRATION, FIXED_ROUTE_MODULE,
                          READINESS_APPARATUS, READINESS_RESULT),
    "qualifying_generation": (M117_CALIBRATION, M117_OUTCOME, PREREGISTRATION, FIXED_ROUTE_MODULE,
                              READINESS_APPARATUS, READINESS_RESULT, ANALYSIS_PLAN, GENERATOR_SPEC,
                              TESTED_SYSTEM_FREEZE),
    "admission": (READINESS_RESULT, ANALYSIS_PLAN, GENERATOR_SPEC, TESTED_SYSTEM_FREEZE),
    "sealing": (READINESS_RESULT, ANALYSIS_PLAN, GENERATOR_SPEC, TESTED_SYSTEM_FREEZE,
                DELIVERY_LEDGER),
    "reveal": (ANALYSIS_PLAN, GENERATOR_SPEC, TESTED_SYSTEM_FREEZE, DELIVERY_LEDGER, SEALED_BANK,
               REVEAL_AUTHORIZATION),
    "scoring": (ANALYSIS_PLAN, GENERATOR_SPEC, TESTED_SYSTEM_FREEZE, DELIVERY_LEDGER, SEALED_BANK,
                REVEAL_AUTHORIZATION),
    "replay": (ANALYSIS_PLAN, GENERATOR_SPEC, TESTED_SYSTEM_FREEZE, DELIVERY_LEDGER, SEALED_BANK,
               REVEAL_AUTHORIZATION, RESULT),
}

# Artifacts that must NOT exist before the qualifying generation. Their presence means a scientific
# observation already happened, and the stage that is about to run would not be the first.
NO_SCIENTIFIC_ARTIFACT_BEFORE = (DELIVERY_LEDGER, SEALED_BANK, RESULT, REVEAL_AUTHORIZATION,
                                 DIRECTORY / "CARRIER_BANK.json")


def _root(root: Path | None) -> Path:
    return Path(root) if root is not None else Path(__file__).resolve().parents[1]


def _head_blob(root: Path, relative: Path) -> bytes | None:
    """The bytes git has for `relative` at HEAD, or None if it is not committed there."""
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "cat-file", "blob", "HEAD:%s" % relative.as_posix()],
            capture_output=True, check=False,
        )
    except OSError:
        return None
    return completed.stdout if completed.returncode == 0 else None


def assert_committed_at_head(relative: Path, root: Path | None = None) -> str:
    """The artifact exists on disk, is committed at HEAD, and the two agree byte for byte."""
    base = _root(root)
    path = base / relative
    if not path.is_file():
        raise ChronologyError("required predecessor is absent: %s" % relative.as_posix())
    on_disk = path.read_bytes()
    committed = _head_blob(base, relative)
    if committed is None:
        raise ChronologyError(
            "required predecessor exists but is not committed at HEAD: %s" % relative.as_posix())
    if committed != on_disk:
        raise ChronologyError(
            "required predecessor differs from its committed bytes: %s" % relative.as_posix())
    import hashlib
    return hashlib.sha256(on_disk).hexdigest()


def assert_stage_permitted(stage: str, root: Path | None = None) -> dict[str, Any]:
    """May this stage run? Only if every predecessor is already a commit at HEAD.

    There is deliberately no parameter through which a caller may pass a record it just built. An
    earlier milestone allowed that and it was a hole rather than a convenience: a runner could
    construct a freeze moments before generating, satisfy every digest, and bypass the chronology
    the freeze exists to establish.
    """
    if stage not in STAGES:
        raise ChronologyError("unknown M118 stage %r" % stage)
    base = _root(root)
    predecessors = {
        relative.as_posix(): assert_committed_at_head(relative, base)
        for relative in STAGES[stage]
    }
    return {
        "schema": "m118-stage-permission-v1",
        "milestone": MILESTONE, "hypothesis": HYPOTHESIS,
        "stage": stage,
        "permitted": True,
        "committed_predecessors": predecessors,
        "in_memory_freeze_accepted": False,
    }


def assert_no_scientific_observation_yet(root: Path | None = None) -> None:
    """Nothing downstream of the qualifying generation may exist before it runs."""
    base = _root(root)
    present = [p.as_posix() for p in NO_SCIENTIFIC_ARTIFACT_BEFORE if (base / p).exists()]
    if present:
        raise ChronologyError(
            "an H63 scientific artifact already exists, so this would not be the first "
            "qualifying generation: %s" % ", ".join(sorted(present)))


def assert_readiness_passed(root: Path | None = None) -> dict[str, Any]:
    """The scientific freeze may only follow a committed readiness result that says ready.

    A readiness gate whose failure can be stepped over is not a gate. If the fixed route did not
    pass, H63 stops here: the precommitted rule forbids changing provider, changing model,
    weakening the stress, removing a schema requirement, rerunning until it passes, or creating a
    carrier bank.
    """
    import json
    base = _root(root)
    assert_committed_at_head(READINESS_RESULT, base)
    record = json.loads((base / READINESS_RESULT).read_text(encoding="utf-8"))
    if record.get("ready") is not True or record.get("verdict") != "ready":
        raise ChronologyError(
            "the fixed H63 route did not pass the readiness gate (verdict %r); H63 stops before "
            "scientific generation and the route is not substituted"
            % record.get("verdict"))
    return {
        "readiness_verdict": record["verdict"],
        "readiness_result_sha256": record["result_sha256"],
        "readiness_plan_sha256": record["plan_sha256"],
    }


def assert_qualifying_generation_permitted(root: Path | None = None) -> dict[str, Any]:
    """The gate the H63 delivery runner must pass before it may send the qualifying request."""
    base = _root(root)
    permission = assert_stage_permitted("qualifying_generation", base)
    assert_no_scientific_observation_yet(base)
    permission.update(assert_readiness_passed(base))
    permission["no_scientific_observation_existed"] = True
    return permission


def chronology(root: Path | None = None) -> dict[str, Any]:
    """Which stages the committed repository can currently prove. Reports; never advances."""
    base = _root(root)
    reached = {}
    for stage in STAGES:
        try:
            assert_stage_permitted(stage, base)
            reached[stage] = "permitted"
        except ChronologyError as exc:
            reached[stage] = "blocked: %s" % exc
    return {
        "schema": "m118-chronology-v1",
        "milestone": MILESTONE, "hypothesis": HYPOTHESIS,
        "stages": reached,
    }
