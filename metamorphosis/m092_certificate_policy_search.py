"""Target-neutral path-wise certificate-policy search for the frozen M092 criterion run.

M092's independent verifier permits every symbolic back edge to keep or increment each explicit
candidate ghost counter independently.  The first candidate-side generator deliberately provided a
smaller uniform policy as the basic certificate-construction layer.  The criterion search must not
confuse that implementation convenience with the frozen certificate language, so this module
enumerates the missing path-wise policies before any target search is consumed.

The module is still candidate-side.  It imports no independent verifier, qualification material,
result artifact or world generator.  Every policy attempt is represented explicitly, including
failed certificate construction, so the canonical runner can account for actual work rather than
manufacturing counters after the fact.
"""
from __future__ import annotations

from dataclasses import dataclass
import itertools
from typing import Iterator, Mapping, Sequence

import metamorphosis.m092_certificate_generator as base
from metamorphosis.m092_kernel import Program

POLICY_RECORD_SCHEMA = "m092-certificate-policy-record-v1"


@dataclass(frozen=True)
class CertificatePolicyRecord:
    """One deterministic ghost-policy construction attempt for one exact program."""

    ordinal: int
    ghost_count: int
    ghost_names: tuple[str, ...]
    back_edge_path_ids: tuple[str, ...]
    increments: tuple[tuple[str, tuple[int, ...]], ...]
    certificate: Mapping[str, object] | None
    refusal: str | None

    @property
    def constructed(self) -> bool:
        return self.certificate is not None

    def to_dict(self, *, include_certificate: bool = True) -> dict[str, object]:
        value: dict[str, object] = {
            "schema": POLICY_RECORD_SCHEMA,
            "ordinal": self.ordinal,
            "ghost_count": self.ghost_count,
            "ghost_names": list(self.ghost_names),
            "back_edge_path_ids": list(self.back_edge_path_ids),
            "increments": [
                {"path_id": path_id, "values": list(values)}
                for path_id, values in self.increments
            ],
            "constructed": self.constructed,
            "refusal": self.refusal,
        }
        if include_certificate:
            value["certificate"] = self.certificate
        return value


def _paths_for_policy(program: Program, ghosts: Sequence[str]) -> tuple[int, list[base.SymbolicPath]]:
    cfg = base.control_flow_graph(program)
    header = int(cfg["loop_headers"][0])
    paths = base._symbolic_paths(
        program,
        source="entry",
        start=0,
        stop_headers={header},
        initial_state=base._initial_entry_state(ghosts),
    )
    paths.extend(base._symbolic_paths(
        program,
        source=f"header:{header}",
        start=header,
        stop_headers={header},
        initial_state=base._initial_header_state(ghosts),
    ))
    paths.sort(key=lambda item: item.path_id)
    return header, paths


def _back_edge_paths(paths: Sequence[base.SymbolicPath]) -> tuple[str, ...]:
    return tuple(sorted(
        path.path_id
        for path in paths
        if path.outcome == "header" and path.source.startswith("header:")
    ))


def enumerate_policy_vectors(
    back_edge_path_ids: Sequence[str],
    ghost_count: int,
) -> Iterator[tuple[tuple[str, tuple[int, ...]], ...]]:
    """Enumerate all 0/1 ghost updates in a fixed path-major, ghost-minor order.

    The all-zero policy is intentionally included.  Whether it can prove a theorem is a property of
    certificate construction, not something the policy enumerator is allowed to guess in advance.
    """

    if not 0 <= ghost_count <= base.MAX_GHOST_COUNTERS:
        raise base.CertificateGenerationError("ghost count exceeds the frozen certificate bound")
    ordered_paths = tuple(sorted(str(path_id) for path_id in back_edge_path_ids))
    if len(ordered_paths) != len(set(ordered_paths)):
        raise base.CertificateGenerationError("back-edge path identifiers are duplicated")
    bit_count = len(ordered_paths) * ghost_count
    for bits in itertools.product((0, 1), repeat=bit_count):
        offset = 0
        policy: list[tuple[str, tuple[int, ...]]] = []
        for path_id in ordered_paths:
            values = tuple(bits[offset:offset + ghost_count])
            offset += ghost_count
            policy.append((path_id, values))
        yield tuple(policy)


def _updates_for_policy(
    paths: Sequence[base.SymbolicPath],
    ghosts: Sequence[str],
    policy: Mapping[str, tuple[int, ...]],
) -> dict[str, dict[str, base.Affine]]:
    back_edges = set(_back_edge_paths(paths))
    if set(policy) != back_edges:
        raise base.CertificateGenerationError("ghost policy does not cover every symbolic back edge")
    updates: dict[str, dict[str, base.Affine]] = {}
    zeros = (0,) * len(ghosts)
    for path in paths:
        increments = policy[path.path_id] if path.path_id in back_edges else zeros
        if len(increments) != len(ghosts) or any(value not in (0, 1) for value in increments):
            raise base.CertificateGenerationError("ghost policy increment is outside the frozen 0/1 surface")
        updates[path.path_id] = base._ghost_update(path, ghosts, tuple(increments))
    return updates


def _derive_conjunctive_equalities(
    program: Program,
    paths: Sequence[base.SymbolicPath],
    ghosts: Sequence[str],
    updates: Mapping[str, Mapping[str, base.Affine]],
) -> list[base.Constraint]:
    """Derive sparse equalities by deterministic conjunctive induction.

    The base generator originally required every equality to preserve itself by literal symbolic
    identity.  That is sound but unnecessarily incomplete: a normal inductive invariant is a
    conjunction, so preserving one equality may legitimately use equalities already established in
    the same invariant set.  This search keeps the frozen sparse template order and coefficient
    bounds, but accepts a new independent equality when every symbolic back edge proves its next
    form from the candidate plus the already-accepted equalities and that path's guards.

    No verifier result, target observation or qualification value enters this construction.
    """

    entries = base._entry_header_values(paths, updates)
    if not entries:
        return []
    back_paths = [
        path for path in paths
        if path.source.startswith("header:") and path.outcome == "header"
    ]
    variables = base._active_variables(program, ghosts)
    coefficient_values = (-1, 1, -2, 2, -3, 3, -4, 4)
    basis: list[base.Constraint] = []
    rows: list[list[int]] = []
    seen: list[base.Constraint] = []

    for support_size in range(1, min(base.MAX_EQUALITY_SUPPORT, len(variables)) + 1):
        for support in itertools.combinations(variables, support_size):
            for coefficients in itertools.product(coefficient_values, repeat=support_size):
                expression = base.Affine.make(dict(zip(support, coefficients, strict=True)))
                entry_forms = [expression.substitute(values) for values in entries]
                if any(form.terms for form in entry_forms):
                    continue
                constants = {form.constant for form in entry_forms}
                if len(constants) != 1:
                    continue
                constant = -next(iter(constants))
                if abs(constant) > base.MAX_AFFINE_COEFFICIENT:
                    continue
                candidate = base._constraint(
                    "eq", expression + base.Affine.make(constant=constant),
                )
                if candidate in seen:
                    continue
                seen.append(candidate)

                row = [candidate.expression.coefficients().get(name, 0) for name in variables]
                row.append(candidate.expression.constant)
                if base._rank([*rows, row]) <= base._rank(rows):
                    continue

                trial = [*basis, candidate]
                preserves = True
                for path in back_paths:
                    final_state = base._apply_update(path.state, updates[path.path_id])
                    goal = base._constraint(
                        "eq",
                        candidate.expression.substitute(base._source_values(final_state)),
                    )
                    premises = [*trial, *path.guards]
                    if base._proof(premises, goal) is None:
                        preserves = False
                        break
                if not preserves:
                    continue

                basis.append(candidate)
                rows.append(row)
                if len(basis) >= base.MAX_CONSTRAINTS_PER_LOOP - 1:
                    return basis
    return basis


def build_pathwise_candidate_certificate(
    program: Program,
    expected_postcondition: Mapping[str, object],
    *,
    ghost_count: int,
    path_increments: Mapping[str, tuple[int, ...]],
) -> dict[str, object]:
    """Construct one complete certificate using an explicit per-back-edge ghost policy."""

    witnesses, postcondition = base._requirement(expected_postcondition)
    if not len(witnesses) <= ghost_count <= base.MAX_GHOST_COUNTERS:
        raise base.CertificateGenerationError("ghost policy cannot bind the required witnesses")
    ghosts = tuple(f"g{index}" for index in range(ghost_count))
    cfg = base.control_flow_graph(program)
    header, paths = _paths_for_policy(program, ghosts)
    if header != int(cfg["loop_headers"][0]):
        raise base.CertificateGenerationError("candidate CFG changed during policy construction")
    updates = _updates_for_policy(paths, ghosts, path_increments)

    precondition = (base._constraint("ge", base.Affine.variable("x")),)
    equalities = _derive_conjunctive_equalities(program, paths, ghosts, updates)
    inequalities = base._derive_inequalities(
        program, paths, equalities, precondition, updates, ghosts,
    )
    invariants = tuple([*equalities, *inequalities][:base.MAX_CONSTRAINTS_PER_LOOP])
    if not invariants:
        raise base.CertificateGenerationError("no inductive invariant survived the bounded templates")

    statuses = base._path_statuses(paths, precondition, invariants)
    if not any(
        statuses[path.path_id] == "feasible" and path.source == "entry"
        for path in paths
    ):
        raise base.CertificateGenerationError("certificate declares every entry path infeasible")
    if not any(
        statuses[path.path_id] == "feasible"
        and path.source.startswith("header:")
        and path.outcome == "halt"
        for path in paths
    ):
        raise base.CertificateGenerationError("certificate has no feasible loop exit")

    variant_data = base._find_variant(
        program, paths, statuses, precondition, invariants, updates, header, ghosts,
    )
    if variant_data is None:
        raise base.CertificateGenerationError("no bounded affine variant survived")
    variant, decrease, initial_constant, initial_coefficient = variant_data

    witness_bindings = {name: ghosts[index] for index, name in enumerate(witnesses)}
    induction: list[dict[str, object]] = []
    for path in paths:
        premises = base._path_premises(path, precondition, invariants)
        if statuses[path.path_id] == "infeasible":
            record = base._obligation_record(
                "infeasible", path, 0, premises, base._false_constraint(),
            )
            if record is None:
                raise base.CertificateGenerationError("infeasible-path proof search failed")
            induction.append(record)
            continue

        final_state = base._apply_update(path.state, updates[path.path_id])
        final_values = base._source_values(final_state)
        if path.outcome == "header":
            if final_state.stack:
                raise base.CertificateGenerationError("loop path does not preserve the opaque frame")
            for index, invariant in enumerate(invariants):
                goal = base._constraint(
                    invariant.relation, invariant.expression.substitute(final_values),
                )
                kind = "establish" if path.source == "entry" else "preserve"
                record = base._obligation_record(kind, path, index, premises, goal)
                if record is None:
                    raise base.CertificateGenerationError("inductive proof search failed")
                induction.append(record)
        else:
            if len(final_state.stack) != 1:
                raise base.CertificateGenerationError("halt path does not leave exactly one output")
            post_values = {"x": base.Affine.variable("x"), "y": final_state.stack[0]}
            final_ghosts = final_state.ghost_map()
            post_values.update({
                name: final_ghosts[counter] for name, counter in witness_bindings.items()
            })
            for index, condition in enumerate(postcondition):
                goal = base._constraint(
                    condition.relation, condition.expression.substitute(post_values),
                )
                record = base._obligation_record("postcondition", path, index, premises, goal)
                if record is None:
                    raise base.CertificateGenerationError("postcondition proof search failed")
                induction.append(record)

    termination: list[dict[str, object]] = []
    synthetic = base.SymbolicPath(
        f"header-{header}", f"header:{header}", "header", header,
        (), (), (), base._initial_header_state(ghosts),
    )
    record = base._obligation_record(
        "variant_nonnegative", synthetic, 0, invariants, base._constraint("ge", variant),
    )
    if record is None:
        raise base.CertificateGenerationError("variant non-negativity proof failed")
    termination.append(record)

    for path in paths:
        if (
            statuses[path.path_id] != "feasible"
            or path.source != f"header:{header}"
            or path.outcome != "header"
        ):
            continue
        final_state = base._apply_update(path.state, updates[path.path_id])
        next_variant = variant.substitute(base._source_values(final_state))
        goal = base._constraint(
            "ge", variant - next_variant + base.Affine.make(constant=-decrease),
        )
        record = base._obligation_record(
            "variant_decrease", path, 0,
            base._path_premises(path, precondition, invariants), goal,
        )
        if record is None:
            raise base.CertificateGenerationError("variant decrease proof failed")
        termination.append(record)

    for path in paths:
        if (
            statuses[path.path_id] != "feasible"
            or path.source != "entry"
            or path.outcome != "header"
        ):
            continue
        final_state = base._apply_update(path.state, updates[path.path_id])
        initial_variant = variant.substitute(base._source_values(final_state))
        upper = base.Affine.make(
            {"x": initial_coefficient} if initial_coefficient else {}, initial_constant,
        )
        record = base._obligation_record(
            "variant_initial_upper_bound", path, 0,
            base._path_premises(path, precondition, invariants),
            base._constraint("ge", upper - initial_variant),
        )
        if record is None:
            raise base.CertificateGenerationError("variant initial-bound proof failed")
        termination.append(record)

    feasible = [path for path in paths if statuses[path.path_id] == "feasible"]
    max_entry = max((
        len(path.pcs) for path in feasible
        if path.source == "entry" and path.outcome == "header"
    ), default=0)
    direct_bound = max((
        len(path.pcs) for path in feasible
        if path.source == "entry" and path.outcome == "halt"
    ), default=0)
    max_back = max((
        len(path.pcs) for path in feasible
        if path.source.startswith("header:") and path.outcome == "header"
    ), default=0)
    max_exit = max((
        len(path.pcs) for path in feasible
        if path.source.startswith("header:") and path.outcome == "halt"
    ), default=0)
    constant_bound = max(
        direct_bound,
        max_entry + max_back * initial_constant + max_exit,
    )
    coefficient_bound = max_back * initial_coefficient
    if constant_bound > base.FUEL_BASE or coefficient_bound > base.FUEL_SLOPE:
        raise base.CertificateGenerationError("proved step bound exceeds the frozen K1 fuel rule")

    return {
        "schema": base.CERTIFICATE_SCHEMA,
        "program_digest": base.program_digest(program),
        "precondition": {
            "schema": base.PRECONDITION_SCHEMA,
            "input_variable": "x",
            "constraints": [item.to_dict() for item in precondition],
            "register_initial_values": [0] * base.REGISTER_COUNT,
            "ghost_initial_values": {name: 0 for name in ghosts},
            "stack": "opaque_prefix_plus_x",
        },
        "control_flow_graph": cfg,
        "loop_invariants": [{
            "header": header,
            "constraints": [item.to_dict() for item in invariants],
        }],
        "well_founded_variants": [{
            "header": header,
            "expression": variant.to_dict(),
            "minimum_decrease": decrease,
        }],
        "inductive_steps": {
            "schema": base.INDUCTION_SCHEMA,
            "ghost_updates": [
                {
                    "path_id": path.path_id,
                    "assignments": {
                        name: expression.to_dict()
                        for name, expression in updates[path.path_id].items()
                    },
                }
                for path in paths
            ],
            "path_status": [
                {"path_id": path.path_id, "status": statuses[path.path_id]}
                for path in paths
            ],
            "obligations": induction,
        },
        "termination_argument": {
            "schema": base.TERMINATION_SCHEMA,
            "back_edges_break_all_cycles": True,
            "obligations": termination,
        },
        "linear_step_bound": {
            "schema": base.STEP_BOUND_SCHEMA,
            "constant": constant_bound,
            "x_coefficient": coefficient_bound,
            "variant_initial_bounds": [{
                "header": header,
                "constant": initial_constant,
                "x_coefficient": initial_coefficient,
            }],
            "max_entry_steps": max_entry,
            "max_back_edge_steps": max_back,
            "max_exit_steps": max_exit,
        },
        "postcondition": {
            "schema": base.POSTCONDITION_SCHEMA,
            "witness_bindings": witness_bindings,
            "constraints": [dict(item) for item in expected_postcondition["constraints"]],
        },
        "frame_condition": base._frame((header,)),
    }


def enumerate_certificate_policy_records(
    program: Program,
    expected_postcondition: Mapping[str, object],
    *,
    limit: int = 4096,
) -> Iterator[CertificatePolicyRecord]:
    """Yield every attempted policy record up to the frozen per-program bound."""

    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
        raise base.CertificateGenerationError("certificate policy limit must be non-negative")
    witnesses, _ = base._requirement(expected_postcondition)
    ordinal = 0
    for ghost_count in range(len(witnesses), base.MAX_GHOST_COUNTERS + 1):
        ghosts = tuple(f"g{index}" for index in range(ghost_count))
        _, paths = _paths_for_policy(program, ghosts)
        back_edges = _back_edge_paths(paths)
        for vector in enumerate_policy_vectors(back_edges, ghost_count):
            if ordinal >= limit:
                return
            ordinal += 1
            policy = {path_id: values for path_id, values in vector}
            try:
                certificate = build_pathwise_candidate_certificate(
                    program,
                    expected_postcondition,
                    ghost_count=ghost_count,
                    path_increments=policy,
                )
            except base.CertificateGenerationError as error:
                yield CertificatePolicyRecord(
                    ordinal=ordinal,
                    ghost_count=ghost_count,
                    ghost_names=ghosts,
                    back_edge_path_ids=back_edges,
                    increments=vector,
                    certificate=None,
                    refusal=str(error),
                )
                continue
            yield CertificatePolicyRecord(
                ordinal=ordinal,
                ghost_count=ghost_count,
                ghost_names=ghosts,
                back_edge_path_ids=back_edges,
                increments=vector,
                certificate=certificate,
                refusal=None,
            )


__all__ = [
    "CertificatePolicyRecord",
    "POLICY_RECORD_SCHEMA",
    "build_pathwise_candidate_certificate",
    "enumerate_certificate_policy_records",
    "enumerate_policy_vectors",
]
