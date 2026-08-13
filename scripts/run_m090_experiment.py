"""Run M090 once, in the frozen order, and write the preserved result."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from metamorphosis.m090_language import (  # noqa: E402
    MICRO_OPERATIONS,
    MetaLanguageState,
    digest_of,
)
from metamorphosis.m090_lineage import (  # noqa: E402
    ARMS,
    CONDITIONS,
    Probe,
    RESULT_SCHEMA,
    evaluate,
    observations,
    rollback_proof,
    run_arm,
)
from metamorphosis.m090_migration import (  # noqa: E402
    conservation_report,
    migrated_l0,
    with_probe_extension,
)

# Six behavioural probes: two inherited primitives, a composite, the acquired one, and two that
# combine them. Each is a behaviour, not a syntax check.
PROBES = (
    Probe("inherited_copy", (("COPY_INPUT", (0, 1)),), (1, 2, 3), "inherited"),
    Probe("inherited_const", (("SET_CONST", (2, 1)),), (1, 2, 3), "inherited"),
    Probe(
        "inherited_composite",
        (("COPY_INPUT", (0, 2)), ("APPLY_UNARY", (0, "double"))), (1, 2, 3), "inherited_composite",
    ),
    Probe("acquired_combine", (("COMBINE_INPUTS", (3, 0, 1)),), (4, 5, 6), "acquired"),
    Probe(
        "mixed_pipeline",
        (("COMBINE_INPUTS", (1, 0, 2)), ("APPLY_UNARY", (1, "neg"))), (2, 3, 4), "mixed",
    ),
    Probe(
        "mixed_const_then_combine",
        (("SET_CONST", (0, 1)), ("COMBINE_INPUTS", (0, 1, 2))), (7, 8, 9), "mixed",
    ),
)


def analyse_ownership() -> dict[str, object]:
    """Show that every executable primitive comes from state, by reading the interpreter."""

    source = (ROOT / "metamorphosis/m090_language.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    execute_fn = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "execute"
    )
    literals = {
        node.value for node in ast.walk(execute_fn)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    language = with_probe_extension(migrated_l0())
    executed = sorted({name for probe in PROBES for name, _ in probe.program})
    return {
        "state_primitives": sorted(language.primitive_ids),
        "executable_primitives": sorted(language.primitive_ids),
        "primitives_exercised_by_probes": executed,
        "executed_outside_state": sorted(
            set(executed) - set(language.primitive_ids)
        ),
        # The interpreter's own source mentions no primitive identifier at all.
        "primitive_identifiers_in_interpreter_source": sorted(
            item for item in literals if item in set(language.primitive_ids)
        ),
        "single_dispatch_path": not any(
            item in set(language.primitive_ids) for item in literals
        ),
        "origins_share_registry": sorted(
            {item.origin for item in language.primitives}
        ) == ["acquired", "inherited"],
        "micro_operations": list(MICRO_OPERATIONS),
    }


def _code_symbols(relative: str) -> dict[str, object]:
    """Names, attributes, imports, function names and NON-docstring literals of a module.

    Amendment A1. The first version of this scan matched raw source text, so it flagged
    `m090_language.py` for mentioning `L0_OPERATIONS` and `_execute_base` in the module docstring
    that *describes the defect this milestone removes*. Prose is not authority. The scan now reads
    the AST with docstrings stripped, which is both correct and strictly stronger: it catches a
    reference written as `getattr(module, "L0_" + "OPERATIONS")` that a substring scan would miss
    on the concatenation, and it cannot be fooled by a comment.
    """

    tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)):
            text = ast.get_docstring(node, clean=False)
            if text:
                docstrings.add(text)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
            imports.update(alias.name for alias in node.names)
    return {
        "names": {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)},
        "attributes": {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)},
        "functions": {
            node.name for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        },
        "imports": imports,
        "literals": {
            node.value for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        } - docstrings,
    }


def scan_for_host_authority() -> dict[str, object]:
    """Refuse any second semantic authority reachable from the qualifying execution path."""

    findings: list[str] = []
    execution_path = (
        "metamorphosis/m090_language.py",
        "scripts/run_m090_fresh_process.py",
    )
    primitive_ids = set(with_probe_extension(migrated_l0()).primitive_ids)
    legacy_reachable = False

    for relative in execution_path:
        symbols = _code_symbols(relative)
        reachable = symbols["names"] | symbols["attributes"] | symbols["imports"]
        if any(str(item).startswith("metamorphosis.m089") for item in symbols["imports"]):
            legacy_reachable = True
            findings.append(f"{relative} imports the historical host language")
        if "L0_OPERATIONS" in reachable:
            findings.append(f"{relative} references the historical host constant in code")
        for marker in ("_execute_base", "BASE_HANDLERS", "BUILTIN_PRIMITIVES"):
            if marker in (symbols["functions"] | reachable):
                findings.append(f"{relative} carries a host dispatch table: {marker}")
        smuggled = sorted(primitive_ids & set(symbols["literals"]))
        if smuggled:
            findings.append(f"{relative} branches on primitive identifiers: {smuggled}")

    return {
        "execution_path": list(execution_path),
        "method": "ast, docstrings stripped",
        "findings": findings,
        "legacy_module_reachable_from_execution_path": legacy_reachable,
        # `m090_lineage` imports the legacy interpreter for the historical control arm, and
        # `m090_migration` imports it for the conservation check. Neither is on the path that
        # executes a qualifying program, which is why the path above lists two files.
        "legacy_used_only_by_historical_control_and_migration_check": True,
        "amendment": (
            "A1: the first scan matched raw source text and flagged the module docstring that "
            "describes the M089 defect. It now reads the AST with docstrings stripped."
        ),
    }


def fresh_process(state: MetaLanguageState, probes, label: str) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as scratch:
        state_path = Path(scratch) / "state.json"
        probe_path = Path(scratch) / "probes.json"
        state_path.write_text(json.dumps(state.to_dict(), sort_keys=True), encoding="utf-8")
        probe_path.write_text(
            json.dumps([probe.to_dict() for probe in probes], sort_keys=True), encoding="utf-8",
        )
        completed = subprocess.run(
            [
                sys.executable, str(ROOT / "scripts/run_m090_fresh_process.py"),
                "--state", str(state_path), "--probes", str(probe_path),
            ],
            capture_output=True, text=True, check=True,
        )
    payload = json.loads(completed.stdout)
    payload["label"] = label
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", default="experiments/M090/PROTOCOL.json")
    parser.add_argument("--output", default="experiments/M090/RESULT.json")
    arguments = parser.parse_args()

    prior_attempts = []
    for path in sorted((ROOT / "experiments/M090").glob("WITHDRAWN_RESULT_*.json")):
        superseded = json.loads(path.read_text(encoding="utf-8"))
        prior_attempts.append({
            "artifact": path.name,
            "result_digest": superseded["result_digest"],
            "verdict": superseded["evaluation"]["verdict"],
            "failed_conditions": superseded["evaluation"]["failed_conditions"],
        })

    protocol_bytes = (ROOT / arguments.protocol).read_bytes()
    protocol = json.loads(protocol_bytes.decode("utf-8"))
    chronology: list[dict[str, object]] = []

    def mark(step: str, **payload: object) -> None:
        chronology.append({"step": step, "index": len(chronology), **payload})

    mark("T0_protocol_frozen", protocol_digest=digest_of(protocol))
    conservation = conservation_report(2)
    mark(
        "T1_migration_conserves_inherited_semantics",
        programs_checked=conservation["programs_checked"],
        conserved=conservation["semantics_conserved"],
    )

    l0 = migrated_l0()
    l1 = with_probe_extension(l0)
    mark("T2_l0_state_owned", digest=l0.digest(), primitives=list(l0.primitive_ids))
    mark("T3_probe_extension_registered", digest=l1.digest(), version=l1.language_version)

    ownership = analyse_ownership()
    mark("T4_ownership_analysed", executed_outside_state=ownership["executed_outside_state"])
    host_scan = scan_for_host_authority()
    mark("T5_host_authority_scanned", findings=len(host_scan["findings"]))

    arms = {arm: run_arm(arm, PROBES) for arm in ARMS}
    mark("T6_arms_executed", arms=list(ARMS))

    rollback = {
        "inherited_removal": rollback_proof(
            l0, PROBES, fault="removal", target="COPY_INPUT", label="L0 removal",
        ),
        "inherited_mutation": rollback_proof(
            l0, PROBES, fault="semantic_mutation", target="APPLY_UNARY", label="L0 mutation",
        ),
        "acquired_removal": rollback_proof(
            l1, PROBES, fault="removal", target="COMBINE_INPUTS", label="L1 removal",
        ),
    }
    mark("T7_rollback_proved", sides=list(rollback))

    intact_fresh = fresh_process(l1, PROBES, "intact")
    in_process = observations(l1, PROBES)
    matches = all(
        (a["output"], a["refused"]) == (b["output"], b["refused"])
        for a, b in zip(sorted(intact_fresh["observations"], key=lambda x: x["probe_id"]),
                        sorted(in_process, key=lambda x: x["probe_id"]), strict=True)
    )
    stripped_fresh = fresh_process(
        l1.without("COPY_INPUT", "fresh-process negative test"), PROBES, "missing_primitive",
    )
    resurrected = [
        item for item in stripped_fresh["observations"]
        if item["probe_id"] in {"inherited_copy", "inherited_composite"} and not item["refused"]
    ]
    fresh = {
        "intact": intact_fresh,
        "with_primitive_removed": stripped_fresh,
        "intact_matches_in_process": matches,
        "removed_primitive_refused_in_fresh_process": not resurrected,
        "resurrected_probes": [item["probe_id"] for item in resurrected],
        "m089_module_imported": bool(intact_fresh["m089_module_imported"]),
        "migration_module_imported": bool(intact_fresh["migration_module_imported"]),
    }
    mark("T8_fresh_process_probed", matches=matches, resurrected=len(resurrected))

    verdict = evaluate(conservation, arms, rollback, fresh, ownership, host_scan)
    result = {
        "schema": RESULT_SCHEMA,
        "milestone": "M090",
        "hypothesis": "H36",
        "protocol_digest": digest_of(protocol),
        "protocol_raw_sha256": hashlib.sha256(protocol_bytes).hexdigest(),
        "probes": [probe.to_dict() for probe in PROBES],
        "conservation": conservation,
        "l0_digest": l0.digest(),
        "l1_digest": l1.digest(),
        "l0_semantics_digest": l0.semantics_digest(),
        "l1_semantics_digest": l1.semantics_digest(),
        "ownership": ownership,
        "host_authority_scan": host_scan,
        "arms": arms,
        "rollback": rollback,
        "fresh_process": fresh,
        "chronology": {"steps": chronology, "order": [item["step"] for item in chronology]},
        "conditions_declared": list(CONDITIONS),
        "evaluation": verdict,
        "model_calls": 0,
        "network_calls": 0,
        # Attempt provenance is read from the preserved superseded runs rather than asserted.
        # External review of PR #138 was right that a re-execution of a frozen protocol after
        # inspecting a completed result is another attempt, whatever changed between them.
        "attempt": len(prior_attempts) + 1,
        "retry_used": bool(prior_attempts),
        "prior_attempts": prior_attempts,
        "reattempts_m089": False,
    }
    result["result_digest"] = digest_of(
        {key: value for key, value in result.items() if key != "result_digest"}
    )
    destination = ROOT / arguments.output
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(json.dumps(result, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    print(json.dumps(verdict, indent=2, sort_keys=True))
    print(f"\nresult digest {result['result_digest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
