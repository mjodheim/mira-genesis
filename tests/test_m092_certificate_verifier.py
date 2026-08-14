"""The M092 verifier gets one neutral rehearsal and adversarial certificate checks.

Nothing in this file constructs or executes the qualifying remainder program.  The positive fixture
is the protocol's declared countdown-to-zero rehearsal.
"""
from __future__ import annotations

import ast
import copy
import itertools
from pathlib import Path

import pytest

import metamorphosis.m092_certificate_verifier as verifier
from metamorphosis.m092_certificate_verifier import (
    CERTIFICATE_SCHEMA,
    COUNTDOWN_POSTCONDITION,
    FRAME_SCHEMA,
    INDUCTION_SCHEMA,
    POSTCONDITION_SCHEMA,
    PRECONDITION_SCHEMA,
    STEP_BOUND_SCHEMA,
    TERMINATION_SCHEMA,
    Affine,
    CertificateError,
    affine_constraint,
    control_flow_graph,
    verify_global_certificate,
)
from metamorphosis.m092_kernel import Machine, Program, execute_program, program_digest


COUNTDOWN_PROGRAM: Program = (
    ("SPOP", 0),
    ("LOADI", 1, 1),
    ("JZ", 0, 5),
    ("SUB", 0, 0, 1),
    ("JMP", 2),
    ("SPUSH", 0),
    ("HALT",),
)


def _proof_for(obligation: verifier.Obligation) -> dict[str, object]:
    ranges = []
    for premise in obligation.premises:
        if obligation.goal.relation == "eq" and premise.relation == "ge":
            ranges.append((0,))
        elif premise.relation == "ge":
            ranges.append(range(5))
        else:
            ranges.append(range(-4, 5))
    slack_range = (0,) if obligation.goal.relation == "eq" else range(5)
    for multipliers in itertools.product(*ranges):
        for slack in slack_range:
            combination = Affine.make(constant=slack)
            for premise, multiplier in zip(obligation.premises, multipliers, strict=True):
                combination = combination + premise.expression.scale(multiplier)
            if combination == obligation.goal.expression:
                return {"multipliers": list(multipliers), "slack": slack}
    raise AssertionError(f"neutral rehearsal has no small exact proof for {obligation.obligation_id}")


def _frame() -> dict[str, object]:
    return {
        "schema": FRAME_SCHEMA,
        "entry_stack": "opaque_prefix_plus_x",
        "loop_header_relative_depths": [{"header": 2, "relative_depth": -1}],
        "halt_stack": "opaque_prefix_plus_y",
        "slots": "unchanged",
        "inputs": "unchanged",
        "argument": "unread",
        "forbidden_opcodes": list(verifier.FORBIDDEN_OPCODES),
    }


def _countdown_skeleton() -> dict[str, object]:
    cfg = control_flow_graph(COUNTDOWN_PROGRAM)
    certificate: dict[str, object] = {
        "schema": CERTIFICATE_SCHEMA,
        "program_digest": program_digest(COUNTDOWN_PROGRAM),
        "precondition": {
            "schema": PRECONDITION_SCHEMA,
            "input_variable": "x",
            "constraints": [affine_constraint("ge", {"x": 1})],
            "register_initial_values": [0] * 8,
            "ghost_initial_values": {"g0": 0},
            "stack": "opaque_prefix_plus_x",
        },
        "control_flow_graph": cfg,
        "loop_invariants": [{
            "header": 2,
            "constraints": [
                affine_constraint("ge", {"r0": 1}),
                affine_constraint("eq", {"x": 1, "r0": -1, "g0": -1}),
                affine_constraint("ge", {"g0": 1}),
                affine_constraint("eq", {"r1": 1}, -1),
            ],
        }],
        "well_founded_variants": [{
            "header": 2,
            "expression": {"coefficients": {"r0": 1}, "constant": 0},
            "minimum_decrease": 1,
        }],
        "inductive_steps": {
            "schema": INDUCTION_SCHEMA,
            "ghost_updates": [],
            "path_status": [],
            "obligations": [],
        },
        "termination_argument": {
            "schema": TERMINATION_SCHEMA,
            "back_edges_break_all_cycles": True,
            "obligations": [],
        },
        "linear_step_bound": {
            "schema": STEP_BOUND_SCHEMA,
            "constant": 5,
            "x_coefficient": 3,
            "variant_initial_bounds": [{"header": 2, "constant": 0, "x_coefficient": 1}],
            "max_entry_steps": 2,
            "max_back_edge_steps": 3,
            "max_exit_steps": 3,
        },
        "postcondition": {
            "schema": POSTCONDITION_SCHEMA,
            "witness_bindings": {},
            "constraints": copy.deepcopy(COUNTDOWN_POSTCONDITION["constraints"]),
        },
        "frame_condition": _frame(),
    }

    ghosts, _ = verifier._parse_precondition(certificate["precondition"])
    headers = tuple(cfg["loop_headers"])
    paths = verifier._symbolic_paths(
        COUNTDOWN_PROGRAM,
        source="entry",
        start=0,
        stop_headers=set(headers),
        initial_state=verifier._initial_entry_state(ghosts),
    )
    for header in headers:
        paths.extend(verifier._symbolic_paths(
            COUNTDOWN_PROGRAM,
            source=f"header:{header}",
            start=header,
            stop_headers=set(headers),
            initial_state=verifier._initial_header_state(ghosts),
        ))
    paths.sort(key=lambda item: item.path_id)
    for path in paths:
        status = "infeasible" if (2, "negative") in path.decisions else "feasible"
        certificate["inductive_steps"]["path_status"].append({
            "path_id": path.path_id,
            "status": status,
        })
        increment = path.source == "header:2" and path.outcome == "header" and status == "feasible"
        certificate["inductive_steps"]["ghost_updates"].append({
            "path_id": path.path_id,
            "assignments": {
                "g0": {"coefficients": {"g0": 1}, "constant": 1 if increment else 0},
            },
        })
    return certificate


def _complete_countdown_certificate() -> dict[str, object]:
    certificate = _countdown_skeleton()
    analysis = verifier._derive_analysis(
        COUNTDOWN_PROGRAM, certificate, COUNTDOWN_POSTCONDITION,
    )
    certificate["inductive_steps"]["obligations"] = [
        obligation.to_candidate_dict(_proof_for(obligation))
        for obligation in analysis.inductive_obligations
    ]
    certificate["termination_argument"]["obligations"] = [
        obligation.to_candidate_dict(_proof_for(obligation))
        for obligation in analysis.termination_obligations
    ]
    return certificate


@pytest.fixture(scope="module")
def countdown_certificate() -> dict[str, object]:
    return _complete_countdown_certificate()


def test_neutral_countdown_has_a_global_exact_certificate(
    countdown_certificate: dict[str, object],
) -> None:
    report = verify_global_certificate(
        COUNTDOWN_PROGRAM,
        countdown_certificate,
        expected_postcondition=COUNTDOWN_POSTCONDITION,
    )
    assert report["status"] == "accepted"
    assert report["global_domain"] == "every integer x >= 0"
    assert report["finite_execution_used"] is False
    assert report["loop_headers"] == 1
    assert report["linear_step_bound"] == {
        "schema": STEP_BOUND_SCHEMA,
        "constant": 5,
        "x_coefficient": 3,
        "variant_initial_bounds": [{"header": 2, "constant": 0, "x_coefficient": 1}],
        "max_entry_steps": 2,
        "max_back_edge_steps": 3,
        "max_exit_steps": 3,
    }


def test_neutral_execution_is_only_a_small_rehearsal() -> None:
    for value in (0, 1, 9):
        machine = Machine(stack=[41, value], slots=[7], inputs=[11])
        execute_program(COUNTDOWN_PROGRAM, machine)
        assert machine.stack == [41, 0]
        assert machine.slots == [7]
        assert machine.inputs == [11]


def test_wrong_program_digest_is_a_decisive_refusal(
    countdown_certificate: dict[str, object],
) -> None:
    altered = copy.deepcopy(countdown_certificate)
    altered["program_digest"] = "0" * 64
    with pytest.raises(CertificateError, match="exact candidate program"):
        verify_global_certificate(
            COUNTDOWN_PROGRAM, altered, expected_postcondition=COUNTDOWN_POSTCONDITION,
        )


def test_false_inductive_witness_is_refused(
    countdown_certificate: dict[str, object],
) -> None:
    altered = copy.deepcopy(countdown_certificate)
    proof = altered["inductive_steps"]["obligations"][0]["proof"]
    proof["slack"] += 1
    with pytest.raises(CertificateError, match="does not derive its exact goal"):
        verify_global_certificate(
            COUNTDOWN_PROGRAM, altered, expected_postcondition=COUNTDOWN_POSTCONDITION,
        )


def test_non_decreasing_variant_is_refused(
    countdown_certificate: dict[str, object],
) -> None:
    altered = copy.deepcopy(countdown_certificate)
    altered["well_founded_variants"][0]["expression"] = {
        "coefficients": {"r1": 1}, "constant": 0,
    }
    with pytest.raises(CertificateError, match="termination obligations"):
        verify_global_certificate(
            COUNTDOWN_PROGRAM, altered, expected_postcondition=COUNTDOWN_POSTCONDITION,
        )


def test_wrong_postcondition_is_refused(
    countdown_certificate: dict[str, object],
) -> None:
    altered = copy.deepcopy(countdown_certificate)
    altered["postcondition"]["constraints"] = [affine_constraint("eq", {"y": 1}, -1)]
    with pytest.raises(CertificateError, match="required theorem"):
        verify_global_certificate(
            COUNTDOWN_PROGRAM, altered, expected_postcondition=COUNTDOWN_POSTCONDITION,
        )


def test_frame_claim_cannot_hide_stack_or_slot_access(
    countdown_certificate: dict[str, object],
) -> None:
    altered = copy.deepcopy(countdown_certificate)
    altered["frame_condition"]["slots"] = "candidate_claims_unchanged"
    with pytest.raises(CertificateError, match="frame condition"):
        verify_global_certificate(
            COUNTDOWN_PROGRAM, altered, expected_postcondition=COUNTDOWN_POSTCONDITION,
        )


def test_certificate_schema_rejects_finite_test_vectors(
    countdown_certificate: dict[str, object],
) -> None:
    altered = copy.deepcopy(countdown_certificate)
    altered["sampled_outputs"] = [[0, 0], [1, 0]]
    with pytest.raises(CertificateError, match="closed schema"):
        verify_global_certificate(
            COUNTDOWN_PROGRAM, altered, expected_postcondition=COUNTDOWN_POSTCONDITION,
        )


def test_verifier_import_boundary_excludes_builders_and_qualification() -> None:
    source_path = Path(verifier.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    project_imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            project_imports.update(alias.name for alias in node.names if alias.name.startswith("metamorphosis"))
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("metamorphosis"):
            project_imports.add(node.module)
    assert project_imports == {
        "metamorphosis.m092_kernel",
        "metamorphosis.m092_runtime",
    }
