"""M119 chronology: every stage proves its predecessors were committed before it ran.

    M118 closed, route fixed, readiness passed
      -> M119/H64 preregistration
      -> plan, spec, qualifying input and nonce frozen
      -> complete tested-system freeze committed
      -> unique H64 qualifying generation
      -> machine-only admission
      -> seal, or terminal abort
      -> reveal authorization
      -> one reveal
      -> frozen scoring
      -> independent replay

A file written seconds before a request is not a freeze. A commit is what makes "before" auditable
by someone who was not in the room, so `assert_stage_permitted` reads the committed blob and
compares it to disk, and refuses on any difference. There is deliberately no parameter through
which a caller may supply a record it has just built: an earlier milestone allowed that, and it was
a hole rather than a convenience.

The interpreting closure is computed from the source rather than asserted in prose, and a second
guard scans the disk for measurement entry points no root declares -- because a closure walks
*downward* from its roots, so a module nothing imports is invisible to it, and a runner is exactly
such a module.

Nothing here generates, seals, reveals or scores. It refuses.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping

from metamorphosis import m116_chronology as _m116
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex
from metamorphosis.m116_chronology import ChronologyError

MILESTONE = "M119"
HYPOTHESIS = "H64"

DIRECTORY = Path("experiments/M119")

# Predecessors, outside M119, that fix the route and its readiness. They are read, never rewritten.
M117_CALIBRATION = Path("experiments/M117/STAGE1_ROUTE_QUALIFICATION.json")
M118_OUTCOME = Path("experiments/M118/OUTCOME.md")
M118_READINESS_RESULT = Path("experiments/M118/READINESS_RESULT.json")
FIXED_ROUTE_MODULE = Path("metamorphosis/m118_route.py")

# M119's own artifacts, each named by the stage that produces it.
COMPLEXITY_BUDGET = DIRECTORY / "COMPLEXITY_BUDGET.md"
PREREGISTRATION = DIRECTORY / "PREREGISTRATION.md"
ANALYSIS_PLAN = DIRECTORY / "ANALYSIS_PLAN.json"
GENERATOR_SPEC = DIRECTORY / "GENERATOR_SPEC.json"
QUALIFYING_INPUT = DIRECTORY / "QUALIFYING_INPUT.txt"
BANK_NONCE_COMMITMENT = DIRECTORY / "BANK_NONCE_COMMITMENT.json"
TESTED_SYSTEM_FREEZE = DIRECTORY / "TESTED_SYSTEM_FREEZE.json"
DELIVERY_LEDGER = DIRECTORY / "DELIVERY_LEDGER.json"
SEALED_BANK = DIRECTORY / "SEALED_BANK.json.gpg"
PUBLIC_BANK_COMMITMENT = DIRECTORY / "PUBLIC_BANK_COMMITMENT.json"
REVEAL_AUTHORIZATION = DIRECTORY / "REVEAL_AUTHORIZATION.json"
CARRIER_BANK = DIRECTORY / "CARRIER_BANK.json"
REVEAL_RECORD = DIRECTORY / "REVEAL_RECORD.json"
MEASUREMENTS = DIRECTORY / "MEASUREMENTS.json"
RESULT = DIRECTORY / "RESULT.json"

_FOUNDATION = (M117_CALIBRATION, M118_OUTCOME, M118_READINESS_RESULT, FIXED_ROUTE_MODULE,
               COMPLEXITY_BUDGET)
_FROZEN_COMMITMENTS = (ANALYSIS_PLAN, GENERATOR_SPEC, QUALIFYING_INPUT, BANK_NONCE_COMMITMENT)

# Each stage lists what must already be committed at HEAD before it may run. The lists are
# cumulative by construction: a later stage repeats its predecessors rather than trusting that an
# earlier check ran, because nothing guarantees the earlier check ran in this process.
STAGES: dict[str, tuple[Path, ...]] = {
    "preregistration": _FOUNDATION,
    "commitments": _FOUNDATION + (PREREGISTRATION,),
    "scientific_freeze": _FOUNDATION + (PREREGISTRATION,) + _FROZEN_COMMITMENTS,
    "qualifying_generation": _FOUNDATION + (PREREGISTRATION,) + _FROZEN_COMMITMENTS
    + (TESTED_SYSTEM_FREEZE,),
    "admission": _FROZEN_COMMITMENTS + (TESTED_SYSTEM_FREEZE,),
    "sealing": _FROZEN_COMMITMENTS + (TESTED_SYSTEM_FREEZE, DELIVERY_LEDGER),
    "reveal": _FROZEN_COMMITMENTS + (TESTED_SYSTEM_FREEZE, DELIVERY_LEDGER, SEALED_BANK,
                                     PUBLIC_BANK_COMMITMENT, REVEAL_AUTHORIZATION),
    "scoring": _FROZEN_COMMITMENTS + (TESTED_SYSTEM_FREEZE, DELIVERY_LEDGER, SEALED_BANK,
                                      PUBLIC_BANK_COMMITMENT, REVEAL_AUTHORIZATION,
                                      REVEAL_RECORD, CARRIER_BANK),
    "replay": _FROZEN_COMMITMENTS + (TESTED_SYSTEM_FREEZE, DELIVERY_LEDGER, SEALED_BANK,
                                     PUBLIC_BANK_COMMITMENT, REVEAL_AUTHORIZATION,
                                     REVEAL_RECORD, CARRIER_BANK, MEASUREMENTS),
}

# Artifacts that must NOT exist before the qualifying generation. Their presence means a scientific
# observation already happened, and the stage about to run would not be the first.
NO_SCIENTIFIC_ARTIFACT_BEFORE = (DELIVERY_LEDGER, SEALED_BANK, PUBLIC_BANK_COMMITMENT,
                                 REVEAL_AUTHORIZATION, REVEAL_RECORD, CARRIER_BANK,
                                 MEASUREMENTS, RESULT,
                                 DIRECTORY / "GENERATION_RESPONSE.json")


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
    return hashlib.sha256(on_disk).hexdigest()


def assert_stage_permitted(stage: str, root: Path | None = None) -> dict[str, Any]:
    """May this stage run? Only if every predecessor is already a commit at HEAD."""
    if stage not in STAGES:
        raise ChronologyError("unknown M119 stage %r" % stage)
    base = _root(root)
    predecessors = {relative.as_posix(): assert_committed_at_head(relative, base)
                    for relative in STAGES[stage]}
    return {
        "schema": "m119-stage-permission-v1",
        "milestone": MILESTONE, "hypothesis": HYPOTHESIS,
        "stage": stage, "permitted": True,
        "committed_predecessors": predecessors,
        "in_memory_freeze_accepted": False,
    }


def assert_no_scientific_observation_yet(root: Path | None = None) -> None:
    """Nothing downstream of the qualifying generation may exist before it runs."""
    base = _root(root)
    present = [p.as_posix() for p in NO_SCIENTIFIC_ARTIFACT_BEFORE if (base / p).exists()]
    if present:
        raise ChronologyError(
            "an H64 scientific artifact already exists, so this would not be the first qualifying "
            "generation: %s" % ", ".join(sorted(present)))


def assert_readiness_passed(root: Path | None = None) -> dict[str, Any]:
    """The freeze may only follow a committed readiness result that says the route is ready.

    A gate whose failure can be stepped over is not a gate. M119 inherits M118's committed
    DEVELOPMENT readiness result rather than re-measuring it: the route is the same fixed route,
    and that result was produced before any H64 carrier existed. What it establishes is that this
    route served the frozen request shape conformingly on that date -- not that it still does. The
    live check is admission, where a response that fails identity, schema or truncation is a
    terminal instrument failure and is never redrawn.
    """
    base = _root(root)
    assert_committed_at_head(M118_READINESS_RESULT, base)
    record = json.loads((base / M118_READINESS_RESULT).read_text(encoding="utf-8"))
    if record.get("ready") is not True or record.get("verdict") != "ready":
        raise ChronologyError(
            "the fixed route did not pass the readiness gate (verdict %r); H64 stops before "
            "scientific generation and the route is not substituted" % record.get("verdict"))
    if record.get("development") is not True:
        raise ChronologyError("the inherited readiness result is not a DEVELOPMENT result")
    if record.get("is_a_qualifying_call") is not False:
        raise ChronologyError(
            "the inherited readiness result claims to be a qualifying call, which would make it "
            "scientific evidence rather than calibration")
    return {
        "readiness_verdict": record["verdict"],
        "readiness_result_sha256": record["result_sha256"],
        "readiness_is_inherited_from_m118_not_re_measured": True,
        "readiness_establishes_that_route_served_conformingly_on_that_date_only": True,
        "the_live_check_is_admission": True,
    }


def assert_qualifying_generation_permitted(root: Path | None = None) -> dict[str, Any]:
    """The gate the H64 generation runner must pass before it may send the qualifying request."""
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
    return {"schema": "m119-chronology-v1", "milestone": MILESTONE, "hypothesis": HYPOTHESIS,
            "stages": reached}


# ---------------------------------------------------------------------------------------------
# The tested-system freeze
# ---------------------------------------------------------------------------------------------

FREEZE_SCHEMA = "m119-tested-system-freeze-v1"
INVENTORY_SCHEMA = "m119-tested-system-inventory-v1"

# Roots from which "can this change what the completion means?" is decided. M119 inherits M116's
# roots -- the M113 evaluator, the carrier host and the scientific bank machinery are unchanged --
# and adds its own measurement path. The runner and the checker are roots, not merely libraries:
# they turn an admitted payload into carriers, demands and a verdict.
INTERPRETATION_ROOTS = tuple(dict.fromkeys(
    _m116.INTERPRETATION_ROOTS + (
        "metamorphosis/m118_route.py",
        "metamorphosis/m119_arms.py",
        "metamorphosis/m119_bank.py",
        "metamorphosis/m119_chronology.py",
        "metamorphosis/m119_decomposition.py",
        "metamorphosis/m119_endpoint.py",
        "scripts/reveal_m119_bank.py",
        "scripts/run_m119_generation.py",
        "scripts/run_m119_qualification.py",
        "scripts/check_m119_result.py",
        "scripts/seal_m119_bank.py",
    )
))

TESTED_SYSTEM_PATHS = tuple(dict.fromkeys(
    _m116.TESTED_SYSTEM_PATHS + (
        "metamorphosis/m116_chronology.py",
        "metamorphosis/m118_route.py",
        "metamorphosis/m119_arms.py",
        "metamorphosis/m119_bank.py",
        "metamorphosis/m119_chronology.py",
        "metamorphosis/m119_decomposition.py",
        "metamorphosis/m119_endpoint.py",
        "scripts/reveal_m119_bank.py",
        "scripts/run_m119_generation.py",
        "scripts/run_m119_qualification.py",
        "scripts/check_m119_result.py",
        "scripts/seal_m119_bank.py",
    )
))

# Deliberately unbound, each for a stated reason. The boundary is not "code we did not get to"; it
# is code that cannot reach a scientific interpretation.
#
# The freeze builder writes commitments before any completion exists and never reads one. The
# reveal authorizer records an owner decision and computes no measure. M118's readiness gate is
# already closed and ran before M119 began.
UNBOUND_BY_DESIGN = dict(_m116.UNBOUND_BY_DESIGN)
UNBOUND_BY_DESIGN.update({
    "scripts/build_m119_freeze.py":
        "writes commitments before the generation; never reads a completion",
    "scripts/authorize_m119_reveal.py":
        "records the owner's reveal decision; computes no measure and scores nothing",
    "scripts/audit_m118_readiness.py":
        "closed DEVELOPMENT gate from the predecessor milestone; ran before M119 began",
})

# Every measurement entry point M119 owns must be declared by a root. The globs below are what the
# disk is scanned for; a new one that no root declares stops the freeze.
ENTRY_POINT_PATTERNS = ("run_m119_*.py", "check_m119_*.py", "seal_m119_*.py",
                        "reveal_m119_*.py", "authorize_m119_*.py", "build_m119_*.py")


def interpretation_closure(root: Path | None = None) -> set[str]:
    """Every first-party module reachable from the interpretation roots, transitively.

    Always computed fresh. The one thing that must never be stale is the answer to "is any
    interpreting module unbound?", and a cache keyed on size and modification time is exactly what
    a deliberate edit could preserve.
    """
    base = _root(root)
    seen: set[str] = set()
    queue = list(INTERPRETATION_ROOTS)
    while queue:
        relative = queue.pop()
        if relative in seen:
            continue
        path = base / relative
        if not path.is_file():
            raise ChronologyError("interpretation root is missing: %s" % relative)
        seen.add(relative)
        queue.extend(sorted(_m116._imports(path, base)))
    return seen


def undeclared_measurement_entry_points(root: Path | None = None) -> list[str]:
    """M119 entry points on disk that no interpretation root declares.

    `interpretation_closure` walks transitively *downward* from a hardcoded root tuple, so a
    first-party module that nothing imports is never discovered and `unbound_interpretation_modules`
    cannot name it. An entry point is precisely such a module: it is invoked from the command line
    and imported by nothing on the scientific path. Without this guard the freeze could report
    "fully bound" while the code that turns a sealed completion into a verdict sat outside it.

    An entry point may be answered either by a root or by an explicit `UNBOUND_BY_DESIGN` reason.
    Silence is what this refuses, not exemption.
    """
    base = _root(root)
    answered = set(INTERPRETATION_ROOTS) | set(UNBOUND_BY_DESIGN)
    found = []
    for pattern in ENTRY_POINT_PATTERNS:
        for path in sorted((base / "scripts").glob(pattern)):
            relative = "scripts/%s" % path.name
            if relative not in answered:
                found.append(relative)
    return sorted(found)


def unbound_interpretation_modules(root: Path | None = None) -> list[str]:
    """Modules that can change what a completion means and are not bound by the freeze."""
    return sorted(interpretation_closure(root) - set(TESTED_SYSTEM_PATHS) - set(UNBOUND_BY_DESIGN))


def inventory(root: Path | None = None) -> dict[str, Any]:
    """What the freeze binds, and what it deliberately does not."""
    closure = sorted(interpretation_closure(root))
    unbound = unbound_interpretation_modules(root)
    undeclared = undeclared_measurement_entry_points(root)
    record = {
        "schema": INVENTORY_SCHEMA,
        "milestone": MILESTONE, "hypothesis": HYPOTHESIS,
        "interpretation_roots": list(INTERPRETATION_ROOTS),
        "interpretation_closure": closure,
        "tested_system_paths": list(TESTED_SYSTEM_PATHS),
        "unbound_by_design": dict(sorted(UNBOUND_BY_DESIGN.items())),
        "unbound_interpretation_modules": unbound,
        "undeclared_measurement_entry_points": undeclared,
        "closure_is_fully_bound": not unbound and not undeclared,
        "inventory_sha256": "",
    }
    record["inventory_sha256"] = sha256_hex(
        canonical_bytes({k: v for k, v in record.items() if k != "inventory_sha256"}))
    return record


def tested_system_digests(root: Path | None = None) -> dict[str, str]:
    base = _root(root)
    digests: dict[str, str] = {}
    for relative in TESTED_SYSTEM_PATHS:
        path = base / relative
        if not path.is_file():
            raise ChronologyError("tested-system path is missing: %s" % relative)
        digests[relative] = sha256_hex(path.read_bytes().replace(b"\r\n", b"\n"))
    return digests


def _bound_commitments(base: Path) -> dict[str, Any]:
    """The plan, spec, qualifying input and nonce the freeze is taken against.

    Source digests alone prove the interpreting code is unchanged and prove nothing about the plan,
    the spec, the exact request bytes or the nonce. Without these a downstream phase could re-check
    the freeze happily while the analysis plan or the request body it was frozen against had been
    rewritten.
    """
    missing = [a.as_posix() for a in _FROZEN_COMMITMENTS if not (base / a).is_file()]
    if missing:
        raise ChronologyError(
            "the freeze is taken against the plan, spec, qualifying input and nonce, which are "
            "absent: %s" % ", ".join(missing))
    plan = json.loads((base / ANALYSIS_PLAN).read_text(encoding="utf-8"))
    spec = json.loads((base / GENERATOR_SPEC).read_text(encoding="utf-8"))
    nonce = json.loads((base / BANK_NONCE_COMMITMENT).read_text(encoding="utf-8"))
    return {
        "analysis_plan_commitment_sha256": plan["plan_commitment_sha256"],
        "spec_commitment_sha256": spec["spec_commitment_sha256"],
        "canonical_request_body_sha256": spec["canonical_request_body_sha256"],
        "qualifying_input_sha256": sha256_hex(
            (base / QUALIFYING_INPUT).read_bytes().replace(b"\r\n", b"\n")),
        "bank_nonce_sha256": nonce["bank_nonce_sha256"],
        "session_budget": plan["session_budget"],
        "fresh_seed": plan["fresh_seed"],
    }


def build_freeze(root: Path | None = None) -> dict[str, Any]:
    """The freeze record. Refuses while any interpreting module is unbound."""
    base = _root(root)
    stock = inventory(base)
    if stock["undeclared_measurement_entry_points"]:
        raise ChronologyError(
            "an H64 measurement entry point is on disk but answered by no interpretation root and "
            "no stated exemption, so the closure cannot see it: %s"
            % ", ".join(stock["undeclared_measurement_entry_points"]))
    if not stock["closure_is_fully_bound"]:
        raise ChronologyError(
            "the tested-system freeze would leave interpreting modules unbound: %s"
            % ", ".join(stock["unbound_interpretation_modules"]))
    assert_no_scientific_observation_yet(base)
    record = {
        "schema": FREEZE_SCHEMA,
        "milestone": MILESTONE, "hypothesis": HYPOTHESIS,
        "frozen_before_generation": True,
        "no_scientific_completion_existed_at_freeze": True,
        "digest_mode": "lf_normalized",
        "inventory": stock,
        "bound_commitments": _bound_commitments(base),
        "tested_system_digests": tested_system_digests(base),
        "freeze_commitment_sha256": "",
    }
    record["freeze_commitment_sha256"] = sha256_hex(
        canonical_bytes({k: v for k, v in record.items() if k != "freeze_commitment_sha256"}))
    return record


def validate_freeze(record: Mapping[str, Any], root: Path | None = None) -> None:
    """Does the working tree still match the frozen record, exactly?"""
    base = _root(root)
    if record.get("schema") != FREEZE_SCHEMA:
        raise ChronologyError("not an M119 tested-system freeze")
    expected = sha256_hex(canonical_bytes(
        {k: v for k, v in record.items() if k != "freeze_commitment_sha256"}))
    if record.get("freeze_commitment_sha256") != expected:
        raise ChronologyError("the freeze commitment does not match its contents")
    frozen = record.get("tested_system_digests")
    if not isinstance(frozen, Mapping) or not frozen:
        raise ChronologyError("the freeze binds no tested-system path")
    current = tested_system_digests(base)
    drifted = sorted(p for p in set(frozen) | set(current) if frozen.get(p) != current.get(p))
    if drifted:
        raise ChronologyError("the tested system changed after the freeze: %s" % ", ".join(drifted))
    unbound = unbound_interpretation_modules(base)
    if unbound:
        raise ChronologyError(
            "interpreting modules became unbound after the freeze: %s" % ", ".join(unbound))
    undeclared = undeclared_measurement_entry_points(base)
    if undeclared:
        raise ChronologyError(
            "a measurement entry point appeared after the freeze: %s" % ", ".join(undeclared))
    bound = record.get("bound_commitments")
    if not isinstance(bound, Mapping) or not bound:
        raise ChronologyError("the freeze binds no plan, spec, request body or nonce")
    live = _bound_commitments(base)
    moved = sorted(k for k in set(bound) | set(live) if bound.get(k) != live.get(k))
    if moved:
        raise ChronologyError("a commitment the freeze was taken against changed: %s"
                              % ", ".join(moved))


DOWNSTREAM_PHASES = ("admission", "sealing", "reveal", "scoring", "replay")


def assert_frozen_system_unchanged(root: Path | None = None, *, phase: str) -> dict[str, Any]:
    """Re-prove, at each phase after the generation, that the tested system is still the frozen one.

    The pre-generation gate is necessary and not sufficient: once a completion exists, nothing in
    that earlier check stops someone editing the evaluator, the demand derivation or the scoring
    before the result is computed. That is the same contamination the freeze exists to prevent,
    arriving one step later.
    """
    if phase not in DOWNSTREAM_PHASES:
        raise ChronologyError("unknown downstream phase %r" % phase)
    base = _root(root)
    assert_committed_at_head(TESTED_SYSTEM_FREEZE, base)
    freeze = json.loads((base / TESTED_SYSTEM_FREEZE).read_text(encoding="utf-8"))
    validate_freeze(freeze, base)
    return {
        "schema": "m119-phase-permission-v1",
        "phase": phase, "permitted": True,
        "freeze_commitment_sha256": freeze["freeze_commitment_sha256"],
        "tested_system_unchanged_since_freeze": True,
    }
