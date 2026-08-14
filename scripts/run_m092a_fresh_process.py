"""Execute the migrated substrate in a fresh process, from serialized state and nothing else.

The claim M092-A has to survive is that **state is the execution authority**. A fresh process is the
only honest test of it: if the semantics were still coming from development code, a process that
never imports that code would fail, and a process that imports it would pass for the wrong reason.

This process is allowed exactly three things:

  1. the fixed generic K1 interpreter (`metamorphosis.m092_kernel`);
  2. the serialized substrate state, read from a file;
  3. the generic state loader and dispatcher (`metamorphosis.m092_substrate_state`).

It must not recover inherited micro-operation semantics from `run_body`, from an authored host
dispatch table, from the migration module, from the assembler, or from test fixtures. Two independent
mechanisms enforce that rather than assert it:

* an **import census**, printed by the process itself and checked by the caller, and
* a **tripwire**: `m090_language.run_body` is replaced with a function that raises on contact, so any
  fallback to legacy execution authority aborts this process instead of quietly succeeding.

With `--sabotage-legacy` the legacy host arithmetic is replaced by deliberately wrong code before
anything runs. State-owned execution must be **unaffected**, which is what proves the old
implementation is a reference oracle and not a live authority.
"""
from __future__ import annotations

import argparse
import json
import sys


def _install_tripwire(sabotage: bool) -> None:
    """Make legacy execution authority impossible to use without noticing."""

    from metamorphosis import m090_language

    def _tripwire(*_args: object, **_kwargs: object):  # noqa: ANN202
        raise AssertionError(
            "run_body was called: state-owned execution fell back to legacy host authority"
        )

    m090_language.run_body = _tripwire  # type: ignore[assignment]

    if sabotage:
        # Not merely absent -- actively wrong. If any of this leaks into the result, it shows.
        m090_language._binary = lambda *_a, **_k: 999_999  # type: ignore[assignment]
        m090_language._unary = lambda *_a, **_k: -999_999  # type: ignore[assignment]
        m090_language.MICRO_OPERATIONS = ()  # type: ignore[assignment]
        m090_language.BINARY_OPERATORS = ()  # type: ignore[assignment]
        m090_language.UNARY_OPERATORS = ()  # type: ignore[assignment]


FORBIDDEN_MODULES = (
    "metamorphosis.m092_migration",
    "metamorphosis.m090_migration",
    "metamorphosis.m091_substrate",
    "metamorphosis.m091_lineage",
    "metamorphosis.m091_search",
    "metamorphosis.m091_expressivity",
    "metamorphosis.m091_worlds",
    "scripts.audit_m092_design",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, help="serialized language + substrate state")
    parser.add_argument("--sabotage-legacy", action="store_true")
    parser.add_argument("--json", default="")
    arguments = parser.parse_args()

    _install_tripwire(arguments.sabotage_legacy)

    from metamorphosis.m092_runtime import RuntimeLanguage, SubstrateError
    from metamorphosis.m092_substrate_state import SubstrateState, execute_from_state

    with open(arguments.state, encoding="utf-8") as handle:
        payload = json.load(handle)

    language = RuntimeLanguage.from_dict(payload["language"])
    substrate = SubstrateState.from_dict(payload["substrate"])

    if payload.get("expected_substrate_digest") not in (None, substrate.digest()):
        # Fail closed: a state whose digest does not match what it was published as is not run.
        print(json.dumps({"status": "digest_mismatch", "digest": substrate.digest()}))
        return 2

    outcomes = []
    solved = refused = 0
    for probe in payload["probes"]:
        program = [(name, tuple(args)) for name, args in probe["program"]]
        try:
            slots = execute_from_state(program, probe["inputs"], language, substrate)
            outcomes.append({"id": probe["id"], "status": "value", "slots": list(slots)})
            solved += 1
        except SubstrateError as error:
            outcomes.append({"id": probe["id"], "status": "refused", "code": error.code.value})
            refused += 1

    census = sorted(
        name for name in sys.modules
        if name.startswith(("metamorphosis", "scripts")) and "." in name
    )
    forbidden_present = [name for name in FORBIDDEN_MODULES if name in sys.modules]

    report = {
        "status": "ok",
        "sabotage_legacy": arguments.sabotage_legacy,
        "substrate_digest": substrate.digest(),
        "language_version": language.language_version,
        "registered_operations": len(substrate.operations),
        "probes": len(payload["probes"]),
        "values": solved,
        "refusals": refused,
        "outcomes": outcomes,
        "import_census": census,
        "forbidden_modules_present": forbidden_present,
        "import_census_clean": not forbidden_present,
        "run_body_tripwire_installed": True,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    if arguments.json:
        with open(arguments.json, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
    return 0 if not forbidden_present else 1


if __name__ == "__main__":
    raise SystemExit(main())
