"""Run M091 once, in the frozen causal order, and write the preserved result.

The order is the science. The limitation is diagnosed before anything is built; the primitive is
built and validated before anything is registered; the language is frozen and serialized before the
qualifying worlds exist at all; and the worlds are drawn by a separate process using a salt derived
from the extended language's own digest, a value that does not exist until adoption has happened.
Every step is recorded with its index, and the checker re-derives the order rather than reading a
promise.

Attempt provenance is derived from the preserved artifacts, never declared. External review of
PR #138 established that re-executing a frozen protocol after inspecting a completed result is
another attempt whatever changed in between.
"""
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
    PrimitiveDefinition,
    digest_of,
)
from metamorphosis.m090_migration import migrated_l0  # noqa: E402
from metamorphosis.m091_lineage import (  # noqa: E402
    ARMS,
    CONDITIONS,
    PRIMITIVE_ID,
    RESULT_SCHEMA,
    acquire_primitive,
    conservation_report,
    evaluate,
    rollback_proof,
    run_arm,
    state_authority_report,
    validate_candidate,
)
from metamorphosis.m091_substrate import (  # noqa: E402
    build_definition,
    implementation_digest,
    semantics_digest,
    substrate_manifest,
)
from metamorphosis.m091_worlds import development_world  # noqa: E402

EXPERIMENT = ROOT / "experiments/M091"

# Modules that participate in diagnosing, assembling, validating or selecting a primitive. None of
# them may contain the answer, the qualification, or a conditional that installs one given the
# other. The ceiling arm's authored primitive is deliberately NOT here: it is built below, in the
# instrument, where the assembler cannot see it.
ACQUISITION_PATH = (
    "metamorphosis/m091_lineage.py",
    "metamorphosis/m091_substrate.py",
    "metamorphosis/m091_expressivity.py",
    "metamorphosis/m091_search.py",
    "metamorphosis/m091_worlds.py",
)


# ---------------------------------------------------------------------------------------------
# the ceiling arm's primitive, authored here rather than on the acquisition path
# ---------------------------------------------------------------------------------------------


def ceiling_primitive() -> PrimitiveDefinition:
    """The answer, written by a person, handed to the ceiling arm. Never evidence about the lineage.

    If this arm succeeds it shows the rest of the pipeline can exploit a new primitive, which is
    worth knowing and is not a finding about whether the lineage can make one. It is excluded from
    the verdict by name in `CEILING_ARMS`.
    """

    return build_definition(
        "authored_clamp",
        (("PUSH_SLOT", "$0"), ("PUSH_CONST", 0), ("BINOP", "max"), ("STORE_SLOT", "$0")),
        ("slot",),
        ("handed to the ceiling arm by a person, not assembled by the lineage",),
    )


# ---------------------------------------------------------------------------------------------
# the anti-lookup scan
# ---------------------------------------------------------------------------------------------


def _literal(node: ast.AST) -> object | None:
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError, TypeError):
        return None


def _pair_sequences(tree: ast.AST) -> list[tuple[tuple[object, object], ...]]:
    """Every literal sequence of two-element literal sequences found in a module.

    A primitive body and a program are both sequences of pairs, so this is the shape a lookup of
    either would have to take. It is precise: `binary_shape` comparing against the string `"max"`
    is not a body, and is not flagged.
    """

    found: list[tuple[tuple[object, object], ...]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.List, ast.Tuple)):
            continue
        value = _literal(node)
        if not isinstance(value, (list, tuple)) or len(value) < 2:
            continue
        if not all(isinstance(item, (list, tuple)) and len(item) == 2 for item in value):
            continue
        found.append(tuple((item[0], item[1]) for item in value))
    return found


def _string_constants(tree: ast.AST) -> set[str]:
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            text = ast.get_docstring(node, clean=False)
            if text:
                docstrings.add(text)
    return {
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    } - docstrings


def _imports(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module)
            names.update(alias.name for alias in node.names)
    return names


def scan_for_lookup(
    adopted: PrimitiveDefinition, programs, qualification, digests,
) -> dict[str, object]:
    """Refuse a disguised lookup anywhere on the acquisition path.

    Looked for: the adopted body as a literal; any constructed program as a literal; either of the
    primitive's digests as a literal; a qualifying world's identifier or family; a conditional that
    hands `build_definition` a literal body; and any import of the qualification materializer.
    """

    findings: list[str] = []
    body = tuple((name, argument) for name, argument in adopted.body)
    program_shapes = {
        tuple((name, tuple(arguments)) for name, arguments in program) for program in programs
    }
    world_labels = {str(world["world_id"]) for world in qualification["worlds"]}
    world_labels |= {str(world["family"]) for world in qualification["worlds"]}
    forbidden_digests = set(digests)

    for relative in ACQUISITION_PATH:
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        for sequence in _pair_sequences(tree):
            if sequence == body:
                findings.append(f"{relative} contains the adopted body as a literal")
            normalised = tuple(
                (item[0], tuple(item[1]) if isinstance(item[1], (list, tuple)) else item[1])
                for item in sequence
            )
            if normalised in program_shapes:
                findings.append(f"{relative} contains a constructed program as a literal")
        constants = _string_constants(tree)
        leaked = sorted(constants & (world_labels | forbidden_digests))
        if leaked:
            findings.append(f"{relative} names qualification material: {leaked}")
        imports = _imports(tree)
        if any("materialize_m091" in str(item) for item in imports):
            findings.append(f"{relative} imports the qualification materializer")
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            callee = node.func
            name = getattr(callee, "id", None) or getattr(callee, "attr", None)
            if name not in {"build_definition", "PrimitiveDefinition"}:
                continue
            for argument in list(node.args) + [item.value for item in node.keywords]:
                value = _literal(argument)
                if isinstance(value, (list, tuple)) and value and all(
                    isinstance(item, (list, tuple)) and len(item) == 2 for item in value
                ):
                    findings.append(
                        f"{relative} builds a primitive from a literal body"
                    )
    return {
        "acquisition_path": list(ACQUISITION_PATH),
        "method": "ast, docstrings stripped",
        "findings": findings,
        "no_lookup_of_the_answer": not findings,
    }


def import_graph_report() -> dict[str, object]:
    """No module the lineage imports may reach the qualification, at any depth."""

    reachable: set[str] = set()
    frontier = ["metamorphosis.m091_lineage"]
    seen: set[str] = set()
    while frontier:
        module = frontier.pop()
        if module in seen:
            continue
        seen.add(module)
        relative = ROOT / (module.replace(".", "/") + ".py")
        if not relative.is_file():
            continue
        for name in _imports(ast.parse(relative.read_text(encoding="utf-8"))):
            reachable.add(str(name))
            if str(name).startswith("metamorphosis."):
                frontier.append(str(name))
    offending = sorted(
        item for item in reachable
        if "materialize_m091" in item or "qualification" in item.lower()
    )
    return {
        "root": "metamorphosis.m091_lineage",
        "modules_visited": sorted(seen),
        "offending_imports": offending,
        "qualification_not_reachable_from_the_lineage": not offending,
    }


# ---------------------------------------------------------------------------------------------
# subprocess helpers
# ---------------------------------------------------------------------------------------------


def fresh_process(state: MetaLanguageState, worlds, label: str) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as scratch:
        state_path = Path(scratch) / "state.json"
        worlds_path = Path(scratch) / "worlds.json"
        state_path.write_text(json.dumps(state.to_dict(), sort_keys=True), encoding="utf-8")
        worlds_path.write_text(json.dumps(list(worlds), sort_keys=True), encoding="utf-8")
        completed = subprocess.run(
            [
                sys.executable, str(ROOT / "scripts/run_m091_fresh_process.py"),
                "--state", str(state_path), "--worlds", str(worlds_path),
            ],
            capture_output=True, text=True, check=True,
        )
    payload = json.loads(completed.stdout)
    payload["label"] = label
    return payload


def materialize_qualification(salt: str, language_digest: str) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as scratch:
        destination = Path(scratch) / "qualification.json"
        subprocess.run(
            [
                sys.executable, str(ROOT / "scripts/materialize_m091_qualification.py"),
                "--salt", salt, "--language-digest", language_digest,
                "--output", str(destination),
            ],
            capture_output=True, text=True, check=True,
        )
        return json.loads(destination.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------------------------
# the run
# ---------------------------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", default="experiments/M091/PROTOCOL.json")
    parser.add_argument("--output", default="experiments/M091/RESULT.json")
    parser.add_argument(
        "--qualification", default="experiments/M091/QUALIFICATION.json",
        help="where the separately materialized worlds are written",
    )
    arguments = parser.parse_args()

    prior_attempts = []
    for path in sorted(EXPERIMENT.glob("WITHDRAWN_RESULT_*.json")):
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

    l0 = migrated_l0()
    mark("T1_inherited_language_frozen", digest=l0.digest(), primitives=list(l0.primitive_ids))

    manifest = substrate_manifest()
    mark("T2_extension_substrate_frozen", digest=digest_of(manifest))

    world = development_world()
    mark("T3_development_limitation_materialized", world_id=world["world_id"])

    acquisition = acquire_primitive(world)
    mark(
        "T4_limitation_diagnosed",
        outside=acquisition.diagnosis["outside_constructive_image"],
        fan_in=acquisition.diagnosis["requirement_fan_in"],
    )
    mark(
        "T5_candidates_assembled_and_validated",
        assembled=acquisition.candidates_assembled,
        rejected=len(acquisition.rejected),
        classes=sorted(acquisition.rejection_counts),
    )
    if acquisition.adopted is None or acquisition.extended is None:
        raise SystemExit("no primitive was adopted; the run cannot continue")
    adopted = acquisition.adopted
    mark(
        "T6_primitive_adopted",
        implementation_digest=implementation_digest(adopted.body),
        semantics_digest=adopted.semantics_digest(),
    )

    # The provisional language, and the proof that it can be taken away again.
    provisional = acquisition.extended
    probes = _probes(adopted.primitive_id)
    rollback = {
        "before_adoption": rollback_proof(
            l0, provisional, probes, fault="semantic_mutation", target="APPLY_UNARY",
            label="provisional extension reverted to the inherited language",
        ),
    }
    mark("T7_provisional_extension_rolled_back", digest=l0.digest())

    l1 = MetaLanguageState.from_dict(json.loads(json.dumps(provisional.to_dict())))
    mark("T8_extension_adopted_and_serialized", digest=l1.digest(), version=l1.language_version)

    rollback["after_adoption"] = rollback_proof(
        l1, l1, probes, fault="removal", target=adopted.primitive_id,
        label="the adopted extension corrupted and restored",
    )
    mark("T9_adopted_language_rolled_back", digest=l1.digest())

    conservation = conservation_report(l0, l1)
    mark(
        "T10_inherited_semantics_conserved",
        calls=conservation["calls_checked"], conserved=conservation["semantics_conserved"],
    )

    # The salt cannot exist before adoption: it is derived from the extended language's digest.
    salt = hashlib.sha256(
        f"m091|{l1.digest()}|{adopted.semantics_digest()}".encode("utf-8")
    ).hexdigest()
    qualification = materialize_qualification(salt, l1.digest())
    (ROOT / arguments.qualification).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / arguments.qualification).write_bytes(
        json.dumps(qualification, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    )
    worlds = list(qualification["worlds"])
    mark(
        "T11_qualification_materialized_separately",
        artifact_digest=qualification["artifact_digest"],
        worlds=[world["world_id"] for world in worlds],
        bound_to_language=qualification["extended_language_digest"] == l1.digest(),
    )

    arms = {}
    for arm in ARMS:
        arms[arm] = run_arm(arm, acquisition, worlds, ceiling_primitive())
    mark("T12_arms_executed", arms=list(ARMS))

    constructed = [
        tuple((name, tuple(args)) for name, args in item["search"]["program"])
        for item in arms["evolvable_meta_language"]["encounters"]
        if item["search"]["found"]
    ]
    authority = state_authority_report(l1, constructed, adopted.primitive_id)
    mark("T13_state_authority_probed", removed=authority[
        "removing_the_primitive_from_state_removes_the_transformation"
    ])

    intact = fresh_process(l1, worlds, "intact")
    stripped = fresh_process(
        l1.without(adopted.primitive_id, "fresh-process negative test"), worlds, "primitive_removed",
    )
    fresh_agent = fresh_process(l0, worlds, "fresh_agent_inherited_language_only")
    persistence = {
        "intact": intact,
        "with_primitive_removed": stripped,
        "fresh_agent_process": fresh_agent,
        "fresh_process_solves_every_world": intact["correct_worlds"] == len(worlds),
        "fresh_process_reused_the_same_primitive_semantics": (
            intact["acquired_semantics_digests"] == [adopted.semantics_digest()]
        ),
        "fresh_process_registered_nothing_new": bool(
            intact["language_unchanged_by_this_process"] and intact["language_version"] == 1
        ),
        "fresh_process_imported_no_development_module": (
            intact["development_modules_imported"] is False
        ),
        "removed_primitive_refused_in_fresh_process": stripped["correct_worlds"] == 0,
        "fresh_agent_solved_nothing": fresh_agent["correct_worlds"] == 0,
        # Nested rather than spread: the authority report has an `intact` of its own, and spreading
        # it silently replaced the fresh-process record with a list of outcome strings.
        "state_authority": authority,
        "all_ran_intact": authority["all_ran_intact"],
        "removing_the_primitive_from_state_removes_the_transformation": authority[
            "removing_the_primitive_from_state_removes_the_transformation"
        ],
        "removing_an_inherited_primitive_removes_it_too": authority[
            "removing_an_inherited_primitive_removes_it_too"
        ],
    }
    mark(
        "T14_extension_persisted_and_reused_in_a_fresh_process",
        solved=intact["correct_worlds"], families=intact["families_solved"],
    )

    lookup = scan_for_lookup(
        adopted, constructed + [acquisition.program or ()], qualification,
        [implementation_digest(adopted.body), adopted.semantics_digest()],
    )
    graph = import_graph_report()
    validator_control = _validator_control(l0)
    mark("T15_integrity_scanned", findings=len(lookup["findings"]))

    integrity = {
        "model_calls": 0,
        "network_calls": 0,
        "declared_conditions_match_evaluated_conditions": (
            sorted(protocol["conditions"]) == sorted(CONDITIONS)
        ),
        "chronology_in_causal_order": _chronology_ok(chronology),
        "qualification_materialized_after_the_language_was_frozen": bool(
            qualification["extended_language_digest"] == l1.digest()
            and _index(chronology, "T11_qualification_materialized_separately")
            > _index(chronology, "T8_extension_adopted_and_serialized")
        ),
        "adopted_body_is_not_a_literal_in_the_lineage": not any(
            "adopted body" in item for item in lookup["findings"]
        ),
        "adopted_fingerprint_absent_from_the_inherited_closure": _outside_closure(adopted, l0),
        "validator_cannot_reach_the_qualification": graph[
            "qualification_not_reachable_from_the_lineage"
        ],
        "validator_control": validator_control,
        "lookup_scan": lookup,
        "import_graph": graph,
        "no_lookup_of_the_answer": lookup["no_lookup_of_the_answer"],
        "qualification_not_reachable_from_the_lineage": graph[
            "qualification_not_reachable_from_the_lineage"
        ],
    }

    verdict = evaluate(
        acquisition.to_dict(), arms, rollback, conservation, persistence, integrity,
    )
    result = {
        "schema": RESULT_SCHEMA,
        "milestone": "M091",
        "hypothesis": "H37",
        "protocol_digest": digest_of(protocol),
        "protocol_raw_sha256": hashlib.sha256(protocol_bytes).hexdigest(),
        "substrate_manifest": manifest,
        "development_world": world,
        "qualification": qualification,
        "acquisition": acquisition.to_dict(),
        "l0_digest": l0.digest(),
        "l1_digest": l1.digest(),
        "l0_semantics_digest": l0.semantics_digest(),
        "l1_semantics_digest": l1.semantics_digest(),
        "conservation": conservation,
        "arms": arms,
        "rollback": rollback,
        "persistence": persistence,
        "integrity": integrity,
        "probes": probes,
        "chronology": {"steps": chronology, "order": [item["step"] for item in chronology]},
        "conditions_declared": list(CONDITIONS),
        "evaluation": verdict,
        "model_calls": 0,
        "network_calls": 0,
        "attempt": len(prior_attempts) + 1,
        "retry_used": bool(prior_attempts),
        "prior_attempts": prior_attempts,
        "reattempts_m089": False,
        "h35_supported": False,
        "micro_operations": list(MICRO_OPERATIONS),
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


def _probes(acquired_id: str) -> list[dict[str, object]]:
    """Behavioural probes for the rollback proofs: inherited, acquired and mixed."""

    return [
        {"probe_id": "inherited_copy", "program": [["COPY_INPUT", [0, 1]]], "inputs": [1, 2, 3]},
        {"probe_id": "inherited_const", "program": [["SET_CONST", [2, 1]]], "inputs": [1, 2, 3]},
        {
            "probe_id": "inherited_composite",
            "program": [["COPY_INPUT", [0, 2]], ["APPLY_UNARY", [0, "double"]]],
            "inputs": [1, 2, 3],
        },
        {
            "probe_id": "acquired_clamp",
            "program": [["COPY_INPUT", [0, 0]], [acquired_id, [0]]],
            "inputs": [-4, 3, 7],
        },
        {
            "probe_id": "mixed_conjugate",
            "program": [
                ["COPY_INPUT", [3, 2]], ["APPLY_UNARY", [3, "neg"]], [acquired_id, [3]],
                ["APPLY_UNARY", [3, "neg"]],
            ],
            "inputs": [2, 5, -7],
        },
    ]


def _index(chronology, step: str) -> int:
    return next(item["index"] for item in chronology if item["step"] == step)


def _chronology_ok(chronology) -> bool:
    order = [item["step"] for item in chronology]
    required = [
        "T0_protocol_frozen", "T1_inherited_language_frozen", "T2_extension_substrate_frozen",
        "T3_development_limitation_materialized", "T4_limitation_diagnosed",
        "T5_candidates_assembled_and_validated", "T6_primitive_adopted",
        "T7_provisional_extension_rolled_back", "T8_extension_adopted_and_serialized",
        "T9_adopted_language_rolled_back", "T10_inherited_semantics_conserved",
        "T11_qualification_materialized_separately", "T12_arms_executed",
        "T13_state_authority_probed", "T14_extension_persisted_and_reused_in_a_fresh_process",
        "T15_integrity_scanned",
    ]
    return order == required


def _outside_closure(adopted: PrimitiveDefinition, inherited: MetaLanguageState) -> bool:
    from metamorphosis.m091_lineage import inherited_macro_semantics

    return semantics_digest(
        adopted.body, adopted.parameter_kinds
    ) not in inherited_macro_semantics(adopted.parameter_kinds, inherited)


def _validator_control(inherited: MetaLanguageState) -> dict[str, object]:
    """Positive controls on the validator itself, so that acceptance means something.

    M090's authored probe extension is the M089-shaped primitive — it routes two input positions
    into one slot. It must be refused here as **overbroad**: widening the source fan-in is a
    different extension from the one this milestone diagnosed, and nobody proved it was needed.
    """

    from metamorphosis.m090_migration import PROBE_EXTENSION
    from metamorphosis.m091_lineage import RETAINED_WORLDS

    m089_shaped = validate_candidate(
        PROBE_EXTENSION, inherited, RETAINED_WORLDS, require_bend=True,
    )
    unsafe = validate_candidate(
        PrimitiveDefinition(
            primitive_id="unsafe_candidate",
            parameter_kinds=("slot",),
            body=(("PUSH_CONST", 1), ("STORE_SLOT", "$0")),
            origin="acquired",
            provenance=("validator control",),
            capabilities=("pure_slot_write",),
        ),
        inherited, RETAINED_WORLDS, require_bend=True,
    )
    return {
        "m089_shaped_primitive_rejected": m089_shaped.accepted is False,
        "m089_shaped_rejection_reasons": m089_shaped.reasons,
        "m089_shaped_rejected_as_overbroad": (
            "overbroad_widens_the_source_fan_in" in m089_shaped.reasons
        ),
        "inherited_composition_rejected": unsafe.accepted is False,
        "inherited_composition_rejection_reasons": unsafe.reasons,
        "the_validator_refuses_something": bool(
            m089_shaped.accepted is False and unsafe.accepted is False
        ),
    }


if __name__ == "__main__":
    raise SystemExit(main())
