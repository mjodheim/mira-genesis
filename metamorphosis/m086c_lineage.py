"""M086-C phase 1, over the corrected bank grammar.

Every generic part of the lineage — the cycle, the meta-search, the faulted adoption transaction, the
holdout arm and the ten-condition verdict — is imported unchanged from M086-B. Only the bank the
development phase draws from is different, so nothing M086-B recorded can shift.
"""
from __future__ import annotations

from typing import Callable

from metamorphosis.m086_evolvable_mechanism import Mechanism, m0_mechanism
from metamorphosis.m086b_lineage import (
    ARMS,
    ARMS_THAT_MAY_ADOPT,
    CYCLES_PER_PHASE,
    MetaTrial,
    RollbackEvidence,
    adopt_with_forced_fault,
    digest_of,
    meta_search,
    pursue,
    solves,
)
from metamorphosis.m086c_bank import body_from_shape, draw_shape, public_cases_from_shape


def run_phase1_arm(
    arm: str, salt: bytes, write_independent_record: Callable[[str, Mechanism], str],
) -> dict[str, object]:
    """Identical in shape to M086-B's phase 1, drawing from the corrected grammar."""

    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm!r}")

    shape = draw_shape(salt, "development")
    body = body_from_shape(shape)
    public = public_cases_from_shape(shape, "development")

    mechanism = m0_mechanism()
    start_digest = mechanism.digest()
    journal: list[dict[str, object]] = [{
        "step": "phase1_entered", "arm": arm, "mechanism": start_digest,
        "body": body.digest(), "public": [case.case_id for case in public],
    }]

    developed, outcomes = pursue(mechanism, body, public, CYCLES_PER_PHASE)
    solved = solves(developed, public)
    journal.append({
        "step": "attempt_with_starting_mechanism",
        "cycles": [outcome.to_dict() for outcome in outcomes],
        "solved": solved,
    })

    trials: list[MetaTrial] = []
    rollback: RollbackEvidence | None = None
    adopted_primitives: tuple[str, ...] = ()

    if arm in ARMS_THAT_MAY_ADOPT and not solved:
        candidate, trials = meta_search(mechanism, body, public)
        journal.append({
            "step": "meta_search",
            "limitation": "the starting mechanism produced no hypothesis for two-stage evidence",
            "trials": [trial.to_dict() for trial in trials],
        })
        if candidate is not None:
            independent = write_independent_record(arm, mechanism)
            mechanism, rollback = adopt_with_forced_fault(mechanism, candidate, independent)
            adopted_primitives = mechanism.provenance
            journal.append({
                "step": "meta_adoption_under_forced_fault",
                "primitives": list(adopted_primitives),
                "rollback": rollback.to_dict(),
                "mechanism_after": mechanism.digest(),
            })
            developed, _ = pursue(mechanism, body, public, CYCLES_PER_PHASE)
            solved = solves(developed, public)

    after_development = mechanism.digest()
    if arm == "meta_acquisition_ablated":
        mechanism = m0_mechanism()
        journal.append({
            "step": "meta_acquisition_stripped", "mechanism_restored_to": mechanism.digest(),
        })

    record = {
        "arm": arm,
        "mechanism_start_digest": start_digest,
        "mechanism_after_development_digest": after_development,
        "mechanism_carried_to_holdout": mechanism.to_dict(),
        "mechanism_carried_digest": mechanism.digest(),
        "meta_transformations_adopted": 1 if adopted_primitives else 0,
        "adopted_primitives": list(adopted_primitives),
        "rejected_primitives": [list(t.primitives) for t in trials if not t.solved],
        "meta_trials": [trial.to_dict() for trial in trials],
        "development_solved": solved,
        "rollback": rollback.to_dict() if rollback else None,
        "journal": journal,
    }
    record["record_digest"] = digest_of(record)
    return record
