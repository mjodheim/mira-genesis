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
BANK_NONCE_COMMITMENT = DIRECTORY / "BANK_NONCE_COMMITMENT.json"
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
                              BANK_NONCE_COMMITMENT, TESTED_SYSTEM_FREEZE),
    "admission": (READINESS_RESULT, ANALYSIS_PLAN, GENERATOR_SPEC, BANK_NONCE_COMMITMENT,
                  TESTED_SYSTEM_FREEZE),
    "sealing": (READINESS_RESULT, ANALYSIS_PLAN, GENERATOR_SPEC, BANK_NONCE_COMMITMENT,
                  TESTED_SYSTEM_FREEZE,
                DELIVERY_LEDGER),
    "reveal": (ANALYSIS_PLAN, GENERATOR_SPEC, BANK_NONCE_COMMITMENT, TESTED_SYSTEM_FREEZE, DELIVERY_LEDGER, SEALED_BANK,
               REVEAL_AUTHORIZATION),
    "scoring": (ANALYSIS_PLAN, GENERATOR_SPEC, BANK_NONCE_COMMITMENT, TESTED_SYSTEM_FREEZE, DELIVERY_LEDGER, SEALED_BANK,
                REVEAL_AUTHORIZATION),
    "replay": (ANALYSIS_PLAN, GENERATOR_SPEC, BANK_NONCE_COMMITMENT, TESTED_SYSTEM_FREEZE, DELIVERY_LEDGER, SEALED_BANK,
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


# ---------------------------------------------------------------------------------------------
# The tested-system freeze
# ---------------------------------------------------------------------------------------------
#
# The interpreting closure is computed from the source, not asserted in prose. Prose saying
# "everything relevant is bound" ages badly the first time somebody adds an import; a closure
# computed mechanically does not, and M116 found two genuinely unbound modules that way.

from metamorphosis import m116_chronology as _m116  # noqa: E402
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex  # noqa: E402

FREEZE_SCHEMA = "m118-tested-system-freeze-v1"
INVENTORY_SCHEMA = "m118-tested-system-inventory-v1"
FREEZE_PATH = DIRECTORY / "TESTED_SYSTEM_FREEZE.json"

# Roots from which "can this change what the completion means?" is decided. M118 inherits M115's
# scientific interpretation path unchanged, so it inherits M116's roots and adds its own.
INTERPRETATION_ROOTS = tuple(dict.fromkeys(
    _m116.INTERPRETATION_ROOTS + (
        "metamorphosis/m118_route.py",
        "metamorphosis/m118_chronology.py",
    )
))

TESTED_SYSTEM_PATHS = tuple(dict.fromkeys(
    _m116.TESTED_SYSTEM_PATHS + (
        "metamorphosis/m116_chronology.py",
        "metamorphosis/m118_route.py",
        "metamorphosis/m118_chronology.py",
    )
))

# Deliberately unbound, each for a stated reason. The boundary is not "code we did not get to"; it
# is code that cannot reach a scientific interpretation.
#
# The readiness gate and the freeze builder run before any carrier exists and produce no artifact
# the scientific path reads. Generator transport is bound instead by the generator spec's canonical
# request-body digest, which fixes every byte reaching the model: transport can fail to deliver or
# misreport identity, and the delivery rule and identity attestation catch that, but it cannot
# change how an admitted completion is scored.
UNBOUND_BY_DESIGN = dict(_m116.UNBOUND_BY_DESIGN)
UNBOUND_BY_DESIGN.update({
    "scripts/audit_m118_readiness.py":
        "DEVELOPMENT-only readiness gate; runs before any carrier exists and scores nothing",
    "scripts/build_m118_freeze.py":
        "writes commitments before the generation; never reads a completion",
})


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


def unbound_interpretation_modules(root: Path | None = None) -> list[str]:
    """Modules that can change what a completion means and are not bound by the freeze."""
    return sorted(
        interpretation_closure(root) - set(TESTED_SYSTEM_PATHS) - set(UNBOUND_BY_DESIGN))


def inventory(root: Path | None = None) -> dict[str, Any]:
    """What the freeze binds, and what it deliberately does not."""
    closure = sorted(interpretation_closure(root))
    unbound = unbound_interpretation_modules(root)
    record = {
        "schema": INVENTORY_SCHEMA,
        "milestone": MILESTONE, "hypothesis": HYPOTHESIS,
        "interpretation_roots": list(INTERPRETATION_ROOTS),
        "interpretation_closure": closure,
        "tested_system_paths": list(TESTED_SYSTEM_PATHS),
        "unbound_by_design": dict(sorted(UNBOUND_BY_DESIGN.items())),
        "unbound_interpretation_modules": unbound,
        "closure_is_fully_bound": not unbound,
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
    """The plan, spec, request body and nonce the freeze is taken against."""
    import json as _json
    missing = [a.as_posix() for a in (ANALYSIS_PLAN, GENERATOR_SPEC, BANK_NONCE_COMMITMENT)
               if not (base / a).is_file()]
    if missing:
        raise ChronologyError(
            "the freeze is taken against the plan, spec and nonce, which are absent: %s"
            % ", ".join(missing))
    plan = _json.loads((base / ANALYSIS_PLAN).read_text(encoding="utf-8"))
    spec = _json.loads((base / GENERATOR_SPEC).read_text(encoding="utf-8"))
    nonce = _json.loads((base / BANK_NONCE_COMMITMENT).read_text(encoding="utf-8"))
    return {
        "analysis_plan_commitment_sha256": plan["plan_commitment_sha256"],
        "spec_commitment_sha256": spec["spec_commitment_sha256"],
        "canonical_request_body_sha256": spec["canonical_request_body_sha256"],
        "bank_nonce_sha256": nonce["bank_nonce_sha256"],
        "envelope_version": nonce["envelope_version"],
    }


def build_freeze(root: Path | None = None) -> dict[str, Any]:
    """The freeze record. Refuses while any interpreting module is unbound."""
    base = _root(root)
    stock = inventory(base)
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
        # Source digests alone prove the interpreting code is unchanged and prove nothing about
        # the plan, the spec, the exact request bytes or the nonce. Without these a downstream
        # phase could re-check the freeze happily while the analysis plan or the request body it
        # was frozen against had been rewritten.
        "bound_commitments": _bound_commitments(base),
        "tested_system_digests": tested_system_digests(base),
        "freeze_commitment_sha256": "",
    }
    record["freeze_commitment_sha256"] = sha256_hex(
        canonical_bytes({k: v for k, v in record.items()
                         if k != "freeze_commitment_sha256"}))
    return record


def validate_freeze(record: Mapping[str, Any], root: Path | None = None) -> None:
    """Does the working tree still match the frozen record, exactly?"""
    base = _root(root)
    if record.get("schema") != FREEZE_SCHEMA:
        raise ChronologyError("not an M118 tested-system freeze")
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
        raise ChronologyError(
            "the tested system changed after the freeze: %s" % ", ".join(drifted))
    unbound = unbound_interpretation_modules(base)
    if unbound:
        raise ChronologyError(
            "interpreting modules became unbound after the freeze: %s" % ", ".join(unbound))
    bound = record.get("bound_commitments")
    if not isinstance(bound, Mapping) or not bound:
        raise ChronologyError("the freeze binds no plan, spec, request body or nonce")
    current = _bound_commitments(base)
    moved = sorted(k for k in set(bound) | set(current) if bound.get(k) != current.get(k))
    if moved:
        raise ChronologyError(
            "a commitment the freeze was taken against changed: %s" % ", ".join(moved))


DOWNSTREAM_PHASES = ("admission", "sealing", "reveal", "scoring")


def assert_frozen_system_unchanged(root: Path | None = None, *, phase: str) -> dict[str, Any]:
    """Re-prove, at each phase after the generation, that the tested system is still the frozen one.

    The pre-generation gate is necessary and not sufficient: once a completion exists, nothing in
    that earlier check stops someone editing the evaluator, the demand derivation or the scoring
    before the result is computed. That is the same contamination the freeze exists to prevent,
    arriving one step later.
    """
    import json as _json
    if phase not in DOWNSTREAM_PHASES:
        raise ChronologyError("unknown downstream phase %r" % phase)
    base = _root(root)
    assert_committed_at_head(FREEZE_PATH, base)
    freeze = _json.loads((base / FREEZE_PATH).read_text(encoding="utf-8"))
    validate_freeze(freeze, base)
    return {
        "schema": "m118-phase-permission-v1",
        "phase": phase, "permitted": True,
        "freeze_commitment_sha256": freeze["freeze_commitment_sha256"],
        "tested_system_unchanged_since_freeze": True,
    }
