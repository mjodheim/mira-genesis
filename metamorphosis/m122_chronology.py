"""M122 chronology: every stage proves its predecessors were committed before it ran.

    M119 closed, route fixed
      -> M122/H67 preregistration
      -> DEVELOPMENT bank sizing and instrument rehearsal
      -> DEVELOPMENT route readiness for *this* candidate schema
      -> plan, spec, qualifying input and nonce frozen
      -> complete tested-system freeze committed
      -> unique H67 qualifying generation
      -> machine-only admission
      -> machine-only pre-seal adequacy gate, or terminal abort
      -> seal
      -> reveal authorization
      -> one reveal
      -> frozen scoring
      -> independent replay

Inherited from M119's chronology, which worked, with two additions that its outcome required.

**A readiness result for this schema is a precondition of the freeze.** M119 inherited M118's
readiness evidence, which was correct for M115's schema. M122's candidate schema is a different
schema, and M118's stress schema does not dominate its keyword census -- 22 `enum` occurrences
against 5, eight array-of-object levels against five. Inheriting readiness across that gap would be
asserting a measurement nobody took, so `assert_readiness_passed` requires a committed M122
DEVELOPMENT readiness result and refuses the freeze without one.

**The adequacy record is a predecessor of the seal.** M119's sealing stage required the delivery
ledger. M122's requires the ledger *and* the adequacy gate's record, so a bank the frozen plan
cannot be run on cannot reach the seal, let alone the one reveal.

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

MILESTONE = "M122"
HYPOTHESIS = "H67"

DIRECTORY = Path("experiments/M122")

# Predecessors, outside M122, that fix the route. They are read, never rewritten.
M117_CALIBRATION = Path("experiments/M117/STAGE1_ROUTE_QUALIFICATION.json")
M118_READINESS_RESULT = Path("experiments/M118/READINESS_RESULT.json")
M120_OUTCOME = Path("experiments/M120/OUTCOME.md")
M120_READINESS_RESULT = Path("experiments/M120/READINESS_RESULT.json")
FIXED_ROUTE_MODULE = Path("metamorphosis/m118_route.py")

# M122's own artifacts, each named by the stage that produces it.
ROUTE_DEPTH_DIAGNOSTIC = DIRECTORY / "ROUTE_DEPTH_DIAGNOSTIC.json"
COMPLEXITY_BUDGET = DIRECTORY / "COMPLEXITY_BUDGET.md"
PREREGISTRATION = DIRECTORY / "PREREGISTRATION.md"
GENERATOR_PROMPT = DIRECTORY / "GENERATOR_PROMPT.txt"
BANK_SIZING = DIRECTORY / "BANK_SIZING_DEVELOPMENT.json"
DEVELOPMENT_REHEARSAL = DIRECTORY / "DEVELOPMENT_REHEARSAL.json"
READINESS_RESULT = DIRECTORY / "READINESS_RESULT.json"
ANALYSIS_PLAN = DIRECTORY / "ANALYSIS_PLAN.json"
GENERATOR_SPEC = DIRECTORY / "GENERATOR_SPEC.json"
QUALIFYING_INPUT = DIRECTORY / "QUALIFYING_INPUT.txt"
BANK_NONCE_COMMITMENT = DIRECTORY / "BANK_NONCE_COMMITMENT.json"
TESTED_SYSTEM_FREEZE = DIRECTORY / "TESTED_SYSTEM_FREEZE.json"
DELIVERY_LEDGER = DIRECTORY / "DELIVERY_LEDGER.json"
ADMISSION = DIRECTORY / "ADMISSION.json"
ADEQUACY = DIRECTORY / "ADEQUACY.json"
SEALED_BANK = DIRECTORY / "SEALED_BANK.json.gpg"
PUBLIC_BANK_COMMITMENT = DIRECTORY / "PUBLIC_BANK_COMMITMENT.json"
REVEAL_AUTHORIZATION = DIRECTORY / "REVEAL_AUTHORIZATION.json"
CARRIER_BANK = DIRECTORY / "CARRIER_BANK.json"
REVEAL_RECORD = DIRECTORY / "REVEAL_RECORD.json"
MEASUREMENTS = DIRECTORY / "MEASUREMENTS.json"
RESULT = DIRECTORY / "RESULT.json"

# M122's foundation names M120's closed readiness result as well as its outcome: the depth
# finding that closed M120 is the reason this milestone's contract has the shape it has, and a
# chronology that did not bind it could drift from the record it was built to answer.
_FOUNDATION = (M117_CALIBRATION, M118_READINESS_RESULT, M120_OUTCOME, M120_READINESS_RESULT,
               FIXED_ROUTE_MODULE, COMPLEXITY_BUDGET, ROUTE_DEPTH_DIAGNOSTIC)
_DEVELOPMENT = (BANK_SIZING, DEVELOPMENT_REHEARSAL, READINESS_RESULT)
_FROZEN_COMMITMENTS = (ANALYSIS_PLAN, GENERATOR_SPEC, QUALIFYING_INPUT, BANK_NONCE_COMMITMENT)

# Each stage lists what must already be committed at HEAD before it may run. The lists are
# cumulative by construction: a later stage repeats its predecessors rather than trusting that an
# earlier check ran, because nothing guarantees the earlier check ran in this process.
STAGES: dict[str, tuple[Path, ...]] = {
    "preregistration": _FOUNDATION,
    "development": _FOUNDATION + (PREREGISTRATION, GENERATOR_PROMPT),
    "commitments": _FOUNDATION + (PREREGISTRATION, GENERATOR_PROMPT) + _DEVELOPMENT,
    "scientific_freeze": _FOUNDATION + (PREREGISTRATION, GENERATOR_PROMPT) + _DEVELOPMENT
    + _FROZEN_COMMITMENTS,
    "qualifying_generation": _FOUNDATION + (PREREGISTRATION, GENERATOR_PROMPT) + _DEVELOPMENT
    + _FROZEN_COMMITMENTS + (TESTED_SYSTEM_FREEZE,),
    "admission": _FROZEN_COMMITMENTS + (TESTED_SYSTEM_FREEZE,),
    # The adequacy gate reads the bank the generation produced, so it requires the ledger and the
    # admission record and nothing of its own.
    "adequacy": _FROZEN_COMMITMENTS + (TESTED_SYSTEM_FREEZE, DELIVERY_LEDGER, ADMISSION),
    # Sealing requires adequacy. An admissible-but-inadequate bank cannot reach the seal, which is
    # the whole of what M119 could not say.
    "sealing": _FROZEN_COMMITMENTS + (TESTED_SYSTEM_FREEZE, DELIVERY_LEDGER, ADMISSION, ADEQUACY),
    # The authorizer writes the authorization, so it cannot require it: it requires everything the
    # seal produced and nothing of its own.
    "authorization": _FROZEN_COMMITMENTS + (TESTED_SYSTEM_FREEZE, DELIVERY_LEDGER, ADMISSION,
                                            ADEQUACY, SEALED_BANK, PUBLIC_BANK_COMMITMENT),
    "reveal": _FROZEN_COMMITMENTS + (TESTED_SYSTEM_FREEZE, DELIVERY_LEDGER, ADMISSION, ADEQUACY,
                                     SEALED_BANK, PUBLIC_BANK_COMMITMENT, REVEAL_AUTHORIZATION),
    "scoring": _FROZEN_COMMITMENTS + (TESTED_SYSTEM_FREEZE, DELIVERY_LEDGER, ADMISSION, ADEQUACY,
                                      SEALED_BANK, PUBLIC_BANK_COMMITMENT, REVEAL_AUTHORIZATION,
                                      REVEAL_RECORD, CARRIER_BANK),
    "replay": _FROZEN_COMMITMENTS + (TESTED_SYSTEM_FREEZE, DELIVERY_LEDGER, ADMISSION, ADEQUACY,
                                     SEALED_BANK, PUBLIC_BANK_COMMITMENT, REVEAL_AUTHORIZATION,
                                     REVEAL_RECORD, CARRIER_BANK, MEASUREMENTS),
}

# Artifacts that must NOT exist before the qualifying generation. Their presence means a scientific
# observation already happened, and the stage about to run would not be the first.
NO_SCIENTIFIC_ARTIFACT_BEFORE = (DELIVERY_LEDGER, ADMISSION, ADEQUACY, SEALED_BANK,
                                 PUBLIC_BANK_COMMITMENT, REVEAL_AUTHORIZATION, REVEAL_RECORD,
                                 CARRIER_BANK, MEASUREMENTS, RESULT,
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


# Every artifact this chronology authenticates is text: JSON written by `canonical_bytes`, Markdown,
# a prompt, and Python source. They are compared after normalizing CRLF to LF, and the mode is
# declared here rather than assumed.
#
# The alternative -- raw-byte equality -- is what M119 used, and it makes the gate a property of the
# checkout rather than of the repository: a clone whose git converts line endings fails every
# committed-at-HEAD check for a reason that has nothing to do with the experiment, and this
# repository's own default does exactly that. Declaring the mode is also the only fix available:
# `.gitattributes` is itself a raw-byte-frozen member of M106's apparatus, so an entry added there
# to pin these files would break a closed milestone's freeze. Verified: appending to it does.
#
# What normalization costs is nothing the gate was measuring. It proves the committed blob and the
# working tree carry the same content, which is what "committed before" needs; a line ending is not
# a scientific difference, and every digest the freeze binds is LF-normalized for the same reason.
DIGEST_MODE = "lf_normalized"


def _normalized(payload: bytes) -> bytes:
    return payload.replace(b"\r\n", b"\n")


def assert_committed_at_head(relative: Path, root: Path | None = None) -> str:
    """The artifact exists on disk, is committed at HEAD, and the two agree under `DIGEST_MODE`."""
    base = _root(root)
    path = base / relative
    if not path.is_file():
        raise ChronologyError("required predecessor is absent: %s" % relative.as_posix())
    on_disk = _normalized(path.read_bytes())
    committed = _head_blob(base, relative)
    if committed is None:
        raise ChronologyError(
            "required predecessor exists but is not committed at HEAD: %s" % relative.as_posix())
    if _normalized(committed) != on_disk:
        raise ChronologyError(
            "required predecessor differs from its committed bytes: %s" % relative.as_posix())
    return hashlib.sha256(on_disk).hexdigest()


def assert_stage_permitted(stage: str, root: Path | None = None) -> dict[str, Any]:
    """May this stage run? Only if every predecessor is already a commit at HEAD."""
    if stage not in STAGES:
        raise ChronologyError("unknown M122 stage %r" % stage)
    base = _root(root)
    predecessors = {relative.as_posix(): assert_committed_at_head(relative, base)
                    for relative in STAGES[stage]}
    return {
        "schema": "m122-stage-permission-v1",
        "milestone": MILESTONE, "hypothesis": HYPOTHESIS,
        "stage": stage, "permitted": True,
        "digest_mode": DIGEST_MODE,
        "committed_predecessors": predecessors,
        "in_memory_freeze_accepted": False,
    }


def assert_no_scientific_observation_yet(root: Path | None = None) -> None:
    """Nothing downstream of the qualifying generation may exist before it runs."""
    base = _root(root)
    present = [p.as_posix() for p in NO_SCIENTIFIC_ARTIFACT_BEFORE if (base / p).exists()]
    if present:
        raise ChronologyError(
            "an H67 scientific artifact already exists, so this would not be the first qualifying "
            "generation: %s" % ", ".join(sorted(present)))


def assert_readiness_passed(root: Path | None = None) -> dict[str, Any]:
    """The freeze may only follow a committed M122 readiness result for *this* candidate schema.

    M119 inherited M118's readiness across a schema change and called it evidence. It was evidence
    about M115's schema. This milestone's schema uses the same eleven feature classes but far more
    of them, and M118's stress schema does not dominate its census, so the inherited result cannot
    speak for it. A gate whose failure can be stepped over is not a gate: without a committed M122
    readiness result that says `ready`, the freeze does not happen and the route is not substituted.
    """
    base = _root(root)
    assert_committed_at_head(READINESS_RESULT, base)
    record = json.loads((base / READINESS_RESULT).read_text(encoding="utf-8"))
    if record.get("milestone") != MILESTONE:
        raise ChronologyError("the committed readiness result is not M122's")
    if record.get("ready") is not True or record.get("verdict") != "ready":
        raise ChronologyError(
            "the fixed route did not pass the M122 readiness gate (verdict %r); H67 stops before "
            "scientific generation and the route is not substituted" % record.get("verdict"))
    if record.get("development") is not True:
        raise ChronologyError("the M122 readiness result is not a DEVELOPMENT result")
    if record.get("is_a_qualifying_call") is not False:
        raise ChronologyError(
            "the M122 readiness result claims to be a qualifying call, which would make it "
            "scientific evidence rather than calibration")
    if record.get("candidate_schema_sha256") != _candidate_schema_digest():
        raise ChronologyError(
            "the committed readiness result was measured against a different candidate schema "
            "than the one this freeze would bind")
    return {
        "readiness_verdict": record["verdict"],
        "readiness_result_sha256": record["result_sha256"],
        "readiness_was_measured_against_this_candidate_schema": True,
        "readiness_establishes_that_route_served_conformingly_on_that_date_only": True,
        "the_live_check_is_admission": True,
    }


def _candidate_schema_digest() -> str:
    from metamorphosis import m122_carrier_contract as contract
    return sha256_hex(canonical_bytes(contract.candidate_schema()))


def assert_qualifying_generation_permitted(root: Path | None = None) -> dict[str, Any]:
    """The gate the H67 generation runner must pass before it may send the qualifying request."""
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
    return {"schema": "m122-chronology-v1", "milestone": MILESTONE, "hypothesis": HYPOTHESIS,
            "stages": reached}


# ---------------------------------------------------------------------------------------------
# The tested-system freeze
# ---------------------------------------------------------------------------------------------

FREEZE_SCHEMA = "m122-tested-system-freeze-v1"
INVENTORY_SCHEMA = "m122-tested-system-inventory-v1"

# Roots from which "can this change what the completion means?" is decided. M122 inherits M116's
# roots -- the M113 evaluator, the carrier host and the scientific bank machinery are unchanged --
# adds M119's scientific modules, which it inherits byte-unchanged, and adds its own contract,
# adequacy gate and measurement path. The runner and the checker are roots, not merely libraries.
INTERPRETATION_ROOTS = tuple(dict.fromkeys(
    _m116.INTERPRETATION_ROOTS + (
        "metamorphosis/m118_route.py",
        "metamorphosis/m119_arms.py",
        "metamorphosis/m119_decomposition.py",
        "metamorphosis/m119_endpoint.py",
        "metamorphosis/m122_adequacy.py",
        "metamorphosis/m122_admission.py",
        "metamorphosis/m122_bank.py",
        "metamorphosis/m122_carrier_contract.py",
        "metamorphosis/m122_chronology.py",
        "metamorphosis/m122_devkit.py",
        "metamorphosis/m122_measurement.py",
        "metamorphosis/m122_stress_schema.py",
        "scripts/check_m122_result.py",
        "scripts/run_m122_generation.py",
        "scripts/run_m122_qualification.py",
        "scripts/run_m122_reveal.py",
        "scripts/run_m122_seal.py",
    )
))

TESTED_SYSTEM_PATHS = tuple(dict.fromkeys(
    _m116.TESTED_SYSTEM_PATHS + (
        "metamorphosis/m116_chronology.py",
        "metamorphosis/m118_route.py",
        "metamorphosis/m119_arms.py",
        "metamorphosis/m119_decomposition.py",
        "metamorphosis/m119_endpoint.py",
        "metamorphosis/m122_adequacy.py",
        "metamorphosis/m122_admission.py",
        "metamorphosis/m122_bank.py",
        "metamorphosis/m122_carrier_contract.py",
        "metamorphosis/m122_chronology.py",
        "metamorphosis/m122_devkit.py",
        "metamorphosis/m122_measurement.py",
        "metamorphosis/m122_stress_schema.py",
        "scripts/check_m122_result.py",
        "scripts/run_m122_generation.py",
        "scripts/run_m122_qualification.py",
        "scripts/run_m122_reveal.py",
        "scripts/run_m122_seal.py",
    )
))

# Deliberately unbound, each for a stated reason. The boundary is not "code we did not get to"; it
# is code that cannot reach a scientific interpretation.
UNBOUND_BY_DESIGN = dict(_m116.UNBOUND_BY_DESIGN)
UNBOUND_BY_DESIGN.update({
    "scripts/audit_m122_route_depth.py":
        "DEVELOPMENT route diagnostic; ran before the contract was committed to, sends no qualifying input and produces no carrier",
    "scripts/build_m122_freeze.py":
        "writes commitments before the generation; never reads a completion",
    "scripts/run_m122_authorize.py":
        "records the owner's reveal decision; computes no measure and scores nothing",
    "scripts/run_m122_readiness.py":
        "DEVELOPMENT route calibration; runs before the freeze, sends no qualifying input and "
        "produces no carrier",
    "scripts/build_m122_bank_sizing.py":
        "DEVELOPMENT bank sizing; runs before the freeze over the development emitter and never "
        "reads a completion",
    "scripts/run_m122_rehearsal.py":
        "DEVELOPMENT end-to-end rehearsal; refuses to run once any qualifying artifact exists",
    "scripts/audit_m118_readiness.py":
        "closed DEVELOPMENT gate from a predecessor milestone; ran before M122 began",
    "scripts/build_m119_freeze.py":
        "closed predecessor milestone; wrote M119's commitments before M122 began",
    "scripts/run_m119_authorize.py":
        "closed predecessor milestone; recorded M119's owner reveal decision",
})

# Every measurement entry point M122 owns must be declared by a root. The globs below are what the
# disk is scanned for; a new one that no root declares stops the freeze.
ENTRY_POINT_PATTERNS = ("run_m122_*.py", "check_m122_*.py", "build_m122_*.py")


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
        # `_m116._imports` returns whatever `Path.relative_to` renders, which is backslash-
        # separated on Windows and would never match the POSIX-form paths this module and the
        # freeze both use -- so a closure computed there would report every bound module as
        # unbound. That predecessor is frozen by M116 and M119 and is not edited; the shape is
        # normalized here instead, where it is read.
        queue.extend(sorted(Path(name).as_posix()
                            for name in _m116._imports(path, base)))
    return seen


def undeclared_measurement_entry_points(root: Path | None = None) -> list[str]:
    """M122 entry points on disk that no interpretation root declares.

    `interpretation_closure` walks transitively *downward* from a hardcoded root tuple, so a
    first-party module that nothing imports is never discovered. An entry point is precisely such
    a module: it is invoked from the command line and imported by nothing on the scientific path.

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
    """The plan, spec, qualifying input, nonce and candidate schema the freeze is taken against.

    Source digests alone prove the interpreting code is unchanged and prove nothing about the plan,
    the spec, the exact request bytes, the nonce or the schema the generator is handed. Without
    these a downstream phase could re-check the freeze happily while the analysis plan or the
    request body it was frozen against had been rewritten.
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
        "candidate_schema_sha256": _candidate_schema_digest(),
        "qualifying_input_sha256": sha256_hex(
            (base / QUALIFYING_INPUT).read_bytes().replace(b"\r\n", b"\n")),
        "bank_nonce_sha256": nonce["bank_nonce_sha256"],
        "session_budget": plan["session_budget"],
        "fresh_seed": plan["fresh_seed"],
        "minimum_qualifying_carriers": plan["minimum_qualifying_carriers"],
        "minimum_distinct_qualifying_structures":
            plan["minimum_distinct_qualifying_structures"],
        "alpha": plan["alpha"],
        "minimum_risk_difference": plan["minimum_risk_difference"],
    }


def build_freeze(root: Path | None = None) -> dict[str, Any]:
    """The freeze record. Refuses while any interpreting module is unbound."""
    base = _root(root)
    stock = inventory(base)
    if stock["undeclared_measurement_entry_points"]:
        raise ChronologyError(
            "an H67 measurement entry point is on disk but answered by no interpretation root and "
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
        raise ChronologyError("not an M122 tested-system freeze")
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


DOWNSTREAM_PHASES = ("admission", "adequacy", "sealing", "authorization", "reveal", "scoring",
                     "replay")


def assert_frozen_system_unchanged(root: Path | None = None, *, phase: str) -> dict[str, Any]:
    """Re-prove, at each phase after the generation, that the tested system is still the frozen one
    **and** that everything the earlier phases produced is committed at HEAD.

    The pre-generation gate is necessary and not sufficient: once a completion exists, nothing in
    that earlier check stops someone editing the evaluator, the demand derivation or the scoring
    before the result is computed. That is the same contamination the freeze exists to prevent,
    arriving one step later.

    Checking the freeze alone is also not sufficient. The freeze commitment is derivable from the
    source and the re-derivable plan, spec and nonce, so it is knowable before the generation
    happens and contains no carrier content: proving only that it is unchanged proves nothing about
    *which* sealed bank, reveal or measurement is in hand. The delivery ledger, the admission
    record, the adequacy record, the sealed bank, the reveal and the measurement are one-shot
    experimental data with no re-derivation check, so committed-at-HEAD is the only authentication
    they can have -- which is why every downstream phase runs its stage's predecessor list too.
    """
    if phase not in DOWNSTREAM_PHASES:
        raise ChronologyError("unknown downstream phase %r" % phase)
    base = _root(root)
    permission = assert_stage_permitted(phase, base)
    freeze = json.loads((base / TESTED_SYSTEM_FREEZE).read_text(encoding="utf-8"))
    validate_freeze(freeze, base)
    return {
        "schema": "m122-phase-permission-v1",
        "phase": phase, "permitted": True,
        "committed_predecessors": permission["committed_predecessors"],
        "freeze_commitment_sha256": freeze["freeze_commitment_sha256"],
        "tested_system_unchanged_since_freeze": True,
        "every_artifact_the_earlier_phases_produced_is_committed": True,
    }
