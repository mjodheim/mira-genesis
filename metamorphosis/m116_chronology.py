"""H61 chronology: the tested system freezes *before* the scientific generation exists.

M115 froze the tested system after sealing and before reveal. That was enough to stop anyone
adapting the system to carrier *content*, because the content stayed sealed. It was not enough to
stop anyone adapting it to what the completion *implies*.

Operational telemetry and the pre-seal admission record are not carrier content, but they are
correlated with it. `completion_tokens`, `content_bytes` and `response_bytes` track bank size;
`records_emitted`, `carriers_accepted`, `carriers_refused` and `distinct_structural_signatures`
track how many carriers the generator produced and how many the host would keep; a violation
location names the schema position the generator failed at. A person who read any of those while
the tested system was still editable could tune the system to the bank it had not seen.

M116 removes the possibility rather than the temptation. The freeze moves ahead of the qualifying
request, so that at the moment the first scientific completion comes into existence, every artifact
that can decide what it means is already committed and digest-bound:

    1. DEVELOPMENT capacity/schema-capability gate passes
    2. analysis plan frozen
    3. generator spec and request-body commitment frozen
    4. bank nonce and envelope commitments frozen
    5. THE ENTIRE TESTED SYSTEM IS FROZEN          <- moved here from step 9
    6. the unique H61 qualifying generation occurs
    7. machine-only telemetry and admission
    8. failed admission -> instrument-aborted, no redraw
    9. successful admission -> that exact completion is sealed
   10. reveal authorization
   11. one reveal
   12. qualification, scoring and P1-P22 against the already-frozen system

The consequence worth stating plainly: because no qualifying completion may exist before step 5,
any artifact that exists before the freeze contains *zero* information derived from a scientific
H61 completion. That is what makes the post-generation telemetry safe to read -- not a claim that
scalars cannot leak, which is false, but a chronology in which there is nothing yet to leak.

Nothing here generates, seals, reveals or scores. It refuses.
"""

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from metamorphosis import m113_carrier_bank as scientific_bank
from metamorphosis.blind_bank_protocol import canonical_bytes, sha256_hex

FREEZE_SCHEMA = "m116-tested-system-freeze-v1"
INVENTORY_SCHEMA = "m116-tested-system-inventory-v1"
MILESTONE = "M116"
HYPOTHESIS = "H61"

EXPERIMENT_DIRECTORY = Path("experiments/M116")
FREEZE_PATH = EXPERIMENT_DIRECTORY / "TESTED_SYSTEM_FREEZE.json"

# Artifacts that may only exist *after* the freeze, because each is derived from a scientific
# completion. The delivery gate refuses if any of them is already present.
POST_FREEZE_ONLY_ARTIFACTS = (
    EXPERIMENT_DIRECTORY / "DELIVERY_LEDGER.json",
    EXPERIMENT_DIRECTORY / "TELEMETRY.json",
    EXPERIMENT_DIRECTORY / "ADMISSION_RECORD.json",
    EXPERIMENT_DIRECTORY / "GENERATION_RESPONSE.json",
    EXPERIMENT_DIRECTORY / "SEALED_BANK.json.gpg",
    EXPERIMENT_DIRECTORY / "PUBLIC_BANK_COMMITMENT.json",
    EXPERIMENT_DIRECTORY / "REVEAL_AUTHORIZATION.json",
    EXPERIMENT_DIRECTORY / "RESULT.json",
)

# The roots from which "can this change what the completion means?" is decided. Everything these
# reach, transitively, inside the first-party packages must be bound by the freeze.
INTERPRETATION_ROOTS = (
    # The runners are roots, not just the libraries: they are the code that turns an admitted
    # payload into carriers, demands and a score, and they are what reaches the M107-M111
    # machinery under test.
    "scripts/run_m113_qualification.py",
    "scripts/run_m115_qualification.py",
    "scripts/check_m113_result.py",
    "scripts/check_m115_result.py",
    "metamorphosis/m116_admission.py",
    "metamorphosis/m116_materialization.py",
    "metamorphosis/m116_terminal.py",
    "metamorphosis/m116_telemetry.py",
    "metamorphosis/m116_schema.py",
    "metamorphosis/m113_carrier_bank.py",
    "metamorphosis/m113_evaluator.py",
    "metamorphosis/carrier_host.py",
)

# The explicit inventory. It is checked against the mechanical import closure below, so it cannot
# quietly fall behind the code it claims to bind.
TESTED_SYSTEM_PATHS = tuple(
    dict.fromkeys(
        scientific_bank.TESTED_SYSTEM_PATHS
        + (
            # Delivery and identity semantics inherited through M115 from M114.
            # Found by the closure check below, not by reading: the devkit supplies the measured
            # qualification rate the frozen plan is validated against, and route selection is
            # reachable from the qualification runner. Neither was bound by M115's inventory.
            "metamorphosis/m113_carrier_devkit.py",
            "metamorphosis/m115_route_selection.py",
            "metamorphosis/m114_carrier_bank.py",
            "metamorphosis/m114_delivery.py",
            "scripts/run_m114_qualification.py",
            "scripts/check_m114_result.py",
            "metamorphosis/m115_carrier_bank.py",
            "metamorphosis/m115_delivery.py",
            "metamorphosis/m115_identity.py",
            "metamorphosis/m115_sealing.py",
            "metamorphosis/m115_execution.py",
            "scripts/run_m115_qualification.py",
            "scripts/check_m115_result.py",
            # M116's own interpretation machinery.
            "metamorphosis/m116_admission.py",
            "metamorphosis/m116_chronology.py",
            "metamorphosis/m116_materialization.py",
            "metamorphosis/m116_schema.py",
            "metamorphosis/m116_telemetry.py",
            "metamorphosis/m116_terminal.py",
            "metamorphosis/blind_bank_protocol.py",
        )
    )
)
DIGEST_MODES = {path: "lf_normalized" for path in TESTED_SYSTEM_PATHS}

# Deliberately *not* bound by the tested-system freeze, each for a stated reason. The boundary is
# not "code we did not get to"; it is code that cannot reach a scientific interpretation.
#
# `audit_m116_capacity` and `m116_stress_schema` run only in DEVELOPMENT, never see a carrier and
# produce no artifact the scientific path reads. `build_carrier_schema_census` derives the gate's
# thresholds from the frozen M115 schema and likewise never touches a completion. Generator
# transport -- the client that performs the physical request -- is bound instead by the generator
# spec's canonical request-body digest, which fixes every byte that reaches the model; transport
# can fail to deliver or misreport identity, and the delivery rule and identity attestation catch
# that, but it cannot change how an admitted completion is scored.
UNBOUND_BY_DESIGN = {
    "scripts/audit_m116_capacity.py": "DEVELOPMENT-only capacity gate; never sees a carrier",
    "metamorphosis/m116_stress_schema.py": "DEVELOPMENT-only synthetic schema; never sees a carrier",
    "scripts/build_carrier_schema_census.py": "derives DEVELOPMENT thresholds from the frozen M115 schema",
}

_SHA256_RE = re.compile(r"\A[0-9a-f]{64}\Z")
PACKAGES = ("metamorphosis", "mira_core")


class ChronologyError(RuntimeError):
    """The H61 chronology cannot be proved. Every path fails closed."""


def _root(root: Path | None) -> Path:
    return Path.cwd().resolve() if root is None else Path(root).resolve()


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and bool(_SHA256_RE.match(value))


# --------------------------------------------------------------------------------------------
# Digests and the mechanical inventory
# --------------------------------------------------------------------------------------------

def tested_system_digests(root: Path | None = None) -> dict[str, str]:
    """Digest every bound member. A missing member is an error, never an empty entry."""
    base = _root(root)
    found: dict[str, str] = {}
    for relative in TESTED_SYSTEM_PATHS:
        path = base / relative
        if not path.is_file():
            raise ChronologyError("tested system member is missing: %s" % relative)
        raw = path.read_bytes()
        if DIGEST_MODES.get(relative) != "lf_normalized":
            raise ChronologyError("tested system member has no declared digest mode: %s" % relative)
        found[relative] = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
    return found


def _module_path(name: str, base: Path) -> str | None:
    """Resolve a dotted import to a first-party source path, or None for stdlib/third party."""
    if name.split(".")[0] not in PACKAGES:
        return None
    candidate = base / (name.replace(".", "/") + ".py")
    if candidate.is_file():
        return str(candidate.relative_to(base))
    # `from metamorphosis.x import y` also yields "metamorphosis.x.y"; fall back to the module.
    parent = name.rsplit(".", 1)[0]
    candidate = base / (parent.replace(".", "/") + ".py")
    return str(candidate.relative_to(base)) if candidate.is_file() else None


def _imports(path: Path, base: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError) as exc:
        raise ChronologyError("cannot parse %s: %s" % (path, exc))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module)
            for alias in node.names:
                found.add("%s.%s" % (node.module, alias.name))
    resolved: set[str] = set()
    for name in found:
        relative = _module_path(name, base)
        if relative:
            resolved.add(relative)
    return resolved


# The closure is a pure function of the source files it walks, so it is cached against a stat
# signature of exactly those files plus the roots. A source edit changes the signature and the
# closure is recomputed; nothing is cached across a change that could alter it.
_CLOSURE_CACHE: dict[Path, tuple[frozenset[tuple[str, int, int]], set[str]]] = {}


def _stat_signature(base: Path, relatives: Iterable[str]) -> frozenset[tuple[str, int, int]]:
    signature = set()
    for relative in relatives:
        path = base / relative
        if path.is_file():
            info = path.stat()
            signature.add((relative, info.st_size, info.st_mtime_ns))
    return frozenset(signature)


def interpretation_closure(root: Path | None = None, *, fresh: bool = False) -> set[str]:
    """Every first-party module reachable from the interpretation roots, transitively.

    `fresh=True` bypasses the cache. The freeze path always asks for a fresh closure: the cache is
    keyed on size and modification time, which a deliberate edit could preserve, and the one thing
    that must never be stale is the answer to "is any interpreting module unbound?".
    """
    base = _root(root)
    cached = None if fresh else _CLOSURE_CACHE.get(base)
    if cached is not None:
        signature, closure = cached
        if signature == _stat_signature(base, set(closure) | set(INTERPRETATION_ROOTS)):
            return set(closure)
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
        queue.extend(sorted(_imports(path, base)))
    _CLOSURE_CACHE[base] = (
        _stat_signature(base, seen | set(INTERPRETATION_ROOTS)), set(seen)
    )
    return seen


def unbound_interpretation_modules(root: Path | None = None, *, fresh: bool = False) -> list[str]:
    """Modules that can change what a completion means and are not bound by the freeze.

    This is the check that keeps the inventory honest. Prose saying "everything relevant is bound"
    ages badly the first time somebody adds an import; a closure computed from the source does not.
    """
    bound = set(TESTED_SYSTEM_PATHS)
    return sorted(interpretation_closure(root, fresh=fresh) - bound - set(UNBOUND_BY_DESIGN))


def inventory(root: Path | None = None, *, fresh: bool = False) -> dict[str, Any]:
    """The committed statement of what the freeze binds, and what it deliberately does not."""
    closure = sorted(interpretation_closure(root, fresh=fresh))
    unbound = unbound_interpretation_modules(root, fresh=fresh)
    record = {
        "schema": INVENTORY_SCHEMA,
        "milestone": MILESTONE,
        "hypothesis": HYPOTHESIS,
        "interpretation_roots": list(INTERPRETATION_ROOTS),
        "interpretation_closure": closure,
        "tested_system_paths": list(TESTED_SYSTEM_PATHS),
        "unbound_by_design": dict(sorted(UNBOUND_BY_DESIGN.items())),
        "unbound_interpretation_modules": unbound,
        "closure_is_fully_bound": not unbound,
        "inventory_sha256": "",
    }
    record["inventory_sha256"] = sha256_hex(
        canonical_bytes({k: v for k, v in record.items() if k != "inventory_sha256"})
    )
    return record


# --------------------------------------------------------------------------------------------
# The freeze record
# --------------------------------------------------------------------------------------------

def freeze_commitment(record: Mapping[str, Any]) -> str:
    return sha256_hex(
        canonical_bytes({k: v for k, v in record.items() if k != "freeze_commitment_sha256"})
    )


def build_freeze(
    *,
    plan_commitment_sha256: str,
    spec_commitment_sha256: str,
    request_body_sha256: str,
    bank_nonce_sha256: str,
    frozen_at: str,
    frozen_at_commit: str,
    root: Path | None = None,
) -> dict[str, Any]:
    """Build the pre-generation freeze. Refuses if any post-freeze artifact already exists."""
    base = _root(root)
    assert_no_scientific_artifacts(base)
    unbound = unbound_interpretation_modules(base, fresh=True)
    if unbound:
        raise ChronologyError(
            "these modules can change how a completion is interpreted and are not bound: %s"
            % ", ".join(unbound)
        )
    record: dict[str, Any] = {
        "schema": FREEZE_SCHEMA,
        "milestone": MILESTONE,
        "hypothesis": HYPOTHESIS,
        "freeze_precedes_scientific_generation": True,
        "plan_commitment_sha256": plan_commitment_sha256,
        "spec_commitment_sha256": spec_commitment_sha256,
        "request_body_sha256": request_body_sha256,
        "bank_nonce_sha256": bank_nonce_sha256,
        "frozen_at": frozen_at,
        "frozen_at_commit": frozen_at_commit,
        "inventory_sha256": inventory(base, fresh=True)["inventory_sha256"],
        "tested_system_digests": tested_system_digests(base),
        "freeze_commitment_sha256": "",
    }
    record["freeze_commitment_sha256"] = freeze_commitment(record)
    return record


def validate_freeze(record: Mapping[str, Any], *, root: Path | None = None) -> None:
    """The freeze must be well-formed, complete, and still true of the working tree."""
    base = _root(root)
    expected = {
        "schema", "milestone", "hypothesis", "freeze_precedes_scientific_generation",
        "plan_commitment_sha256", "spec_commitment_sha256", "request_body_sha256",
        "bank_nonce_sha256", "frozen_at", "frozen_at_commit", "inventory_sha256",
        "tested_system_digests", "freeze_commitment_sha256",
    }
    if not isinstance(record, Mapping) or set(record) != expected:
        raise ChronologyError("M116 tested-system freeze fields differ from the declared schema")
    if record.get("schema") != FREEZE_SCHEMA:
        raise ChronologyError("M116 tested-system freeze schema drifted")
    if record.get("milestone") != MILESTONE or record.get("hypothesis") != HYPOTHESIS:
        raise ChronologyError("M116 tested-system freeze belongs to another experiment")
    if record.get("freeze_precedes_scientific_generation") is not True:
        raise ChronologyError("M116 freeze must assert that it precedes scientific generation")
    for field in ("plan_commitment_sha256", "spec_commitment_sha256", "request_body_sha256",
                  "bank_nonce_sha256", "inventory_sha256", "freeze_commitment_sha256"):
        if not _is_sha256(record.get(field)):
            raise ChronologyError("M116 freeze %s is malformed" % field)
    if record.get("freeze_commitment_sha256") != freeze_commitment(record):
        raise ChronologyError("M116 freeze commitment digest drifted")

    digests = record.get("tested_system_digests")
    if not isinstance(digests, Mapping):
        raise ChronologyError("M116 freeze carries no tested-system digests")
    if set(digests) != set(TESTED_SYSTEM_PATHS):
        missing = sorted(set(TESTED_SYSTEM_PATHS) - set(digests))
        extra = sorted(set(digests) - set(TESTED_SYSTEM_PATHS))
        raise ChronologyError(
            "M116 freeze does not cover the inventory exactly; missing %s, unexpected %s"
            % (missing, extra)
        )
    observed = tested_system_digests(base)
    drifted = sorted(name for name, value in digests.items() if observed.get(name) != value)
    if drifted:
        raise ChronologyError(
            "the tested system changed after it was frozen: %s" % ", ".join(drifted)
        )
    if inventory(base, fresh=True)["inventory_sha256"] != record.get("inventory_sha256"):
        raise ChronologyError("the tested-system inventory changed after the freeze")


def assert_no_scientific_artifacts(root: Path | None = None) -> None:
    """Nothing derived from a scientific completion may exist yet."""
    base = _root(root)
    present = [str(p) for p in POST_FREEZE_ONLY_ARTIFACTS if (base / p).exists()]
    if present:
        raise ChronologyError(
            "these artifacts are derived from a scientific completion and already exist: %s"
            % ", ".join(present)
        )


def _head_blob(root: Path, relative: Path) -> bytes | None:
    """The bytes git has for `relative` at HEAD, or None if it is not committed there."""
    import subprocess
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "cat-file", "blob", "HEAD:%s" % relative.as_posix()],
            capture_output=True, check=False,
        )
    except OSError:
        return None
    return completed.stdout if completed.returncode == 0 else None


# The phases that must each re-prove the freeze still holds. A freeze checked once, before
# generation, would leave every later phase free: the completion exists, and the evaluator, the
# scoring code and the checkers are all still editable. Each of these re-checks it.
DOWNSTREAM_PHASES = ("admission", "sealing", "reveal", "scoring")


def assert_frozen_system_unchanged(
    root: Path | None = None, *, phase: str
) -> dict[str, Any]:
    """Re-prove, at a named downstream phase, that the tested system is still the frozen one.

    The pre-generation gate is necessary and not sufficient. Once a qualifying completion exists,
    nothing in the earlier check stops someone editing the evaluator, the demand derivation or the
    scoring implementation before the result is computed -- which is the same contamination the
    freeze exists to prevent, arriving one step later. Every phase after the generation therefore
    re-validates the committed freeze against the working tree.
    """
    import json

    if phase not in DOWNSTREAM_PHASES:
        raise ChronologyError("unknown downstream phase %r" % phase)
    base = _root(root)
    path = base / FREEZE_PATH
    if not path.is_file():
        raise ChronologyError(
            "phase %r requires the tested-system freeze, which is absent" % phase
        )
    raw = path.read_bytes()
    committed = _head_blob(base, FREEZE_PATH)
    if committed is None:
        raise ChronologyError("phase %r requires a freeze committed at HEAD" % phase)
    if committed != raw:
        raise ChronologyError(
            "phase %r: the tested-system freeze on disk differs from the committed one" % phase
        )
    try:
        freeze = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ChronologyError("cannot read the M116 tested-system freeze: %s" % exc)
    validate_freeze(freeze, root=base)
    return {
        "schema": "m116-phase-permission-v1",
        "phase": phase,
        "permitted": True,
        "freeze_commitment_sha256": freeze["freeze_commitment_sha256"],
        "tested_system_unchanged_since_freeze": True,
    }


def assert_qualifying_delivery_permitted(root: Path | None = None) -> dict[str, Any]:
    """The gate the qualifying delivery runner must pass before it may send the request.

    The freeze is read from the committed file and from nowhere else. An earlier form of this
    function accepted a caller-supplied record, which was a hole rather than a convenience: a
    runner could have called `assert_qualifying_delivery_permitted(freeze=build_freeze(...))` and
    satisfied every check by building the freeze moments before generating. Every digest would
    have matched, and the chronology the freeze exists to establish would have been bypassed
    completely.

    So the record must be on disk, and it must additionally be committed at HEAD with the same
    bytes. A file written seconds before the request is not a freeze; a commit is what makes
    "before" auditable by someone who was not in the room.
    """
    import json

    base = _root(root)
    path = base / FREEZE_PATH
    if not path.is_file():
        raise ChronologyError(
            "the H61 qualifying request may not be sent before the tested system is frozen"
        )
    raw = path.read_bytes()
    committed = _head_blob(base, FREEZE_PATH)
    if committed is None:
        raise ChronologyError(
            "the tested-system freeze is not committed at HEAD; an uncommitted freeze does not "
            "establish that it precedes the generation"
        )
    if committed != raw:
        raise ChronologyError(
            "the tested-system freeze on disk differs from the committed one"
        )
    try:
        freeze = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ChronologyError("cannot read the M116 tested-system freeze: %s" % exc)

    validate_freeze(freeze, root=base)
    assert_no_scientific_artifacts(base)
    return {
        "schema": "m116-delivery-permission-v1",
        "permitted": True,
        "freeze_commitment_sha256": freeze["freeze_commitment_sha256"],
        "freeze_is_committed_at_head": True,
        "tested_system_members": len(TESTED_SYSTEM_PATHS),
        "freeze_precedes_scientific_generation": True,
    }


__all__ = [
    "DIGEST_MODES",
    "FREEZE_PATH",
    "FREEZE_SCHEMA",
    "HYPOTHESIS",
    "INTERPRETATION_ROOTS",
    "INVENTORY_SCHEMA",
    "MILESTONE",
    "POST_FREEZE_ONLY_ARTIFACTS",
    "TESTED_SYSTEM_PATHS",
    "UNBOUND_BY_DESIGN",
    "ChronologyError",
    "assert_no_scientific_artifacts",
    "assert_qualifying_delivery_permitted",
    "build_freeze",
    "freeze_commitment",
    "interpretation_closure",
    "inventory",
    "tested_system_digests",
    "unbound_interpretation_modules",
    "validate_freeze",
]
