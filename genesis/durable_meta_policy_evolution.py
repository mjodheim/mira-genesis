"""Crash-consistent reservation wrapper for bounded MetaPolicy evolution.

`meta_policy_evolution.evolve_meta_policy` persists each completed measurement, but its budget
increments originally lived only in the next runtime checkpoint. A process death after an in-memory
`Budget.spend()` and before that checkpoint could therefore resume from the older allowance and redraw
physical work.

This module makes the checkpointed MetaPolicy-evolution path non-redrawable without changing the
trust root. Before any candidate execution begins, the complete round's candidate/evaluation cost is
(1) recorded as a content-addressed reservation, (2) charged to the ordinary admitted Budget, and
(3) checkpointed. The underlying evolution function then runs through a view that consumes those
already-charged slots rather than charging them a second time.

Crash policy is deliberately conservative. If a process dies after the charged checkpoint but before
the complete measurement set is durably present, the round is terminal/ambiguous on restart: Genesis
will not redraw it from the same budget. A crash after the reservation checkpoint but before charge
is safe to resume because no candidate execution is allowed to start before the charged checkpoint.

This is apparatus hardening. It is not a scientific observation and does not make DEVELOPMENT
persistence cryptographically tamper-proof against a hostile host.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from genesis import meta_policy_controller as meta
from genesis import meta_policy_evolution as evolution
from genesis import objective_policy_controller as opc
from genesis import policy_controller
from genesis import retentive_objectives as retentive
from genesis import state as lineage_state
from genesis.trust_root import BudgetExhausted, TrustRootError, artifact_digest_of, digest_of

ROUND_SCHEMA = "genesis-meta-policy-budget-round-v1"
ROUND_KIND = "meta_policy_budget_round"
_RESERVED = "reserved"
_CHARGED = "charged"
_COMPLETED = "completed"
_CRASH_INCOMPLETE = "crash_incomplete"


class DurableMetaPolicyEvolutionError(RuntimeError):
    """Raised when a durable MetaPolicy round cannot be resumed without redrawing work."""


class _ReservedBudgetView:
    """Present already-charged round slots to the lower-level evolution code.

    The underlying Budget has already paid for every physical slot in the round. `spend()` on the
    reserved dimensions therefore consumes only this in-memory allowance. `record()` deliberately
    exposes the real underlying ledger, so checkpoints written during the round keep the full charge.
    """

    def __init__(self, base, allowances: Mapping[str, int]):
        self._base = base
        self._allowances = {str(name): int(value) for name, value in allowances.items()}
        self.limits = base.limits
        self.spent = base.spent

    def remaining(self, dimension: str) -> int:
        if dimension in self._allowances:
            return self._base.remaining(dimension) + self._allowances[dimension]
        return self._base.remaining(dimension)

    def spend(self, dimension: str, amount: int = 1) -> int:
        if amount < 0:
            raise TrustRootError("cannot spend a negative amount")
        if dimension in self._allowances:
            if self._allowances[dimension] < amount:
                raise BudgetExhausted(
                    "reserved budget %r exhausted: %d remaining, %d requested"
                    % (dimension, self._allowances[dimension], amount)
                )
            self._allowances[dimension] -= amount
            return self.remaining(dimension)
        return self._base.spend(dimension, amount)

    def record(self) -> dict[str, Any]:
        return self._base.record()

    def unused(self) -> dict[str, int]:
        return dict(self._allowances)


def _replace_observations(genesis, observations) -> None:
    genesis.state = lineage_state.create_state(
        body_digest=genesis.state["body_digest"],
        components=genesis.state["components"],
        vocabulary=genesis.state["vocabulary"],
        tools=genesis.state["tools"],
        acquisitions=genesis.state["acquisitions"],
        observations=observations,
        generation=genesis.state["generation"],
    )


def _round_payload(
    genesis,
    *,
    objective,
    prior_policy,
    current_meta,
    extensions,
    body_digest: str,
    candidate_units: int,
    evaluation_units: int,
) -> dict[str, Any]:
    return {
        "schema": ROUND_SCHEMA,
        "objective_digest": objective["objective_digest"],
        "prior_policy_digest": prior_policy["policy_digest"],
        "parent_meta_policy_digest": current_meta["meta_policy_digest"],
        "body_artifact_digest": body_digest,
        "evaluation_contract_digest": genesis.evaluation_contract["contract_digest"],
        "extension_digests": sorted(item["mutation_digest"] for item in extensions),
        "reserved": {
            "meta_policy_candidates": int(candidate_units),
            "meta_policy_evaluations": int(evaluation_units),
        },
    }


def _round_digest(payload: Mapping[str, Any]) -> str:
    return digest_of(dict(payload))


def _round_records(genesis, round_digest: str) -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in genesis.state.get("observations", [])
        if isinstance(item, Mapping)
        and item.get("kind") == ROUND_KIND
        and item.get("round_digest") == round_digest
    ]


def _install_round_record(genesis, record: Mapping[str, Any]) -> None:
    target = str(record["round_digest"])
    observations = []
    replaced = False
    for item in genesis.state.get("observations", []):
        if (
            isinstance(item, Mapping)
            and item.get("kind") == ROUND_KIND
            and item.get("round_digest") == target
        ):
            if replaced:
                raise DurableMetaPolicyEvolutionError("duplicate durable MetaPolicy budget round")
            observations.append(dict(record))
            replaced = True
        else:
            observations.append(item)
    if not replaced:
        observations.append(dict(record))
    _replace_observations(genesis, observations)


def _record(
    payload: Mapping[str, Any],
    *,
    status: str,
    budget_before: Mapping[str, int],
    budget_after: Mapping[str, int] | None = None,
    result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    record = {
        "kind": ROUND_KIND,
        **dict(payload),
        "round_digest": _round_digest(payload),
        "status": status,
        "budget_before": dict(budget_before),
        "budget_after": dict(budget_after or {}),
        "result": dict(result or {}),
    }
    record["record_digest"] = digest_of(record)
    return record


def _validate_record(item: Mapping[str, Any], expected_payload: Mapping[str, Any]) -> dict[str, Any]:
    record = dict(item)
    recorded_digest = record.pop("record_digest", "")
    if recorded_digest != digest_of(record):
        raise DurableMetaPolicyEvolutionError("durable MetaPolicy round record digest does not reproduce")
    for key, value in expected_payload.items():
        if item.get(key) != value:
            raise DurableMetaPolicyEvolutionError(
                "durable MetaPolicy round does not reproduce current %s" % key
            )
    if item.get("round_digest") != _round_digest(expected_payload):
        raise DurableMetaPolicyEvolutionError("durable MetaPolicy round identity does not reproduce")
    if item.get("status") not in {_RESERVED, _CHARGED, _COMPLETED, _CRASH_INCOMPLETE}:
        raise DurableMetaPolicyEvolutionError("durable MetaPolicy round has unknown status")
    return dict(item)


def _matching_measurements(genesis, payload: Mapping[str, Any]) -> set[str]:
    found: set[str] = set()
    for item in genesis.state.get("observations", []):
        if not isinstance(item, Mapping) or item.get("kind") != evolution.MEASUREMENT_KIND:
            continue
        if (
            item.get("objective_digest") != payload["objective_digest"]
            or item.get("prior_policy_digest") != payload["prior_policy_digest"]
            or item.get("parent_meta_policy_digest") != payload["parent_meta_policy_digest"]
            or item.get("body_artifact_digest") != payload["body_artifact_digest"]
            or item.get("evaluation_contract_digest") != payload["evaluation_contract_digest"]
        ):
            continue
        digest = item.get("added_mutation_digest")
        if isinstance(digest, str):
            found.add(digest)
    return found


def _charge(genesis, reserved: Mapping[str, int]) -> None:
    try:
        for dimension in ("meta_policy_candidates", "meta_policy_evaluations"):
            amount = int(reserved.get(dimension, 0))
            if amount:
                genesis.budget.spend(dimension, amount)
    except (TrustRootError, BudgetExhausted) as problem:
        raise DurableMetaPolicyEvolutionError(
            "cannot durably charge the complete MetaPolicy round: %s" % problem
        ) from problem


def evolve_meta_policy(
    genesis,
    here,
    *,
    checkpoint_directory: Path,
) -> dict[str, Any]:
    """Run one MetaPolicy descendant round with non-redrawable checkpointed budget.

    A checkpoint directory is mandatory: without a durable commit point, crash-consistent physical
    budget accounting is not a property the function can provide.
    """
    if checkpoint_directory is None:
        raise DurableMetaPolicyEvolutionError("durable MetaPolicy evolution needs a checkpoint directory")
    checkpoint_path = Path(checkpoint_directory)

    retentive.assert_retains_prior_work(genesis, here)
    prior_policy = policy_controller.bound_policy(genesis)
    current_meta = meta.bound_meta_policy(genesis)
    if prior_policy is None or current_meta is None:
        raise DurableMetaPolicyEvolutionError("lineage must hold both search policy and MetaPolicy")
    objective = opc.objective_record(genesis, here)
    if not evolution._current_meta_exhausted(
        genesis,
        here,
        prior_policy=prior_policy,
        current_meta=current_meta,
        objective=objective,
    ):
        raise DurableMetaPolicyEvolutionError(
            "current MetaPolicy is not exhausted on the current policy/objective"
        )

    extensions = evolution.synthesised_extensions(prior_policy, current_meta)
    if not extensions:
        return evolution.evolve_meta_policy(
            genesis, here, checkpoint_directory=checkpoint_path
        )

    body_digest = artifact_digest_of(genesis.body_factory)["artifact_digest"]
    identity_payload = {
        "objective_digest": objective["objective_digest"],
        "prior_policy_digest": prior_policy["policy_digest"],
        "parent_meta_policy_digest": current_meta["meta_policy_digest"],
        "body_artifact_digest": body_digest,
        "evaluation_contract_digest": genesis.evaluation_contract["contract_digest"],
    }
    already_measured = _matching_measurements(genesis, identity_payload)
    pending = [item for item in extensions if item["mutation_digest"] not in already_measured]
    candidate_units = len(pending)
    evaluation_units = sum(evolution._candidate_cost(prior_policy, item) for item in pending)
    payload = _round_payload(
        genesis,
        objective=objective,
        prior_policy=prior_policy,
        current_meta=current_meta,
        extensions=extensions,
        body_digest=body_digest,
        candidate_units=candidate_units,
        evaluation_units=evaluation_units,
    )
    round_digest = _round_digest(payload)
    existing = _round_records(genesis, round_digest)
    if len(existing) > 1:
        raise DurableMetaPolicyEvolutionError("duplicate durable MetaPolicy budget round")

    freshly_charged = False
    if not existing:
        before = {
            "meta_policy_candidates": int(genesis.budget.spent.get("meta_policy_candidates", 0)),
            "meta_policy_evaluations": int(genesis.budget.spent.get("meta_policy_evaluations", 0)),
        }
        reserved_record = _record(payload, status=_RESERVED, budget_before=before)
        _install_round_record(genesis, reserved_record)
        genesis.persist(checkpoint_path)
        existing_record = reserved_record
    else:
        existing_record = _validate_record(existing[0], payload)

    status = existing_record["status"]
    reserved = payload["reserved"]
    if status == _RESERVED:
        _charge(genesis, reserved)
        after = {
            "meta_policy_candidates": int(genesis.budget.spent.get("meta_policy_candidates", 0)),
            "meta_policy_evaluations": int(genesis.budget.spent.get("meta_policy_evaluations", 0)),
        }
        charged_record = _record(
            payload,
            status=_CHARGED,
            budget_before=existing_record["budget_before"],
            budget_after=after,
        )
        _install_round_record(genesis, charged_record)
        genesis.persist(checkpoint_path)
        existing_record = charged_record
        freshly_charged = True
        status = _CHARGED

    if status == _CRASH_INCOMPLETE:
        raise DurableMetaPolicyEvolutionError(
            "prior MetaPolicy round crashed after its physical budget was charged; redraw is refused"
        )
    if status == _COMPLETED:
        return {
            "schema": ROUND_SCHEMA,
            "accepted": bool(existing_record.get("result", {}).get("accepted")),
            "selection_reason": existing_record.get("result", {}).get("selection_reason", ""),
            "already_completed": True,
            "round_digest": round_digest,
            "checkpoint_digest": genesis.checkpoint()["checkpoint_digest"],
        }

    complete = set(payload["extension_digests"]).issubset(
        _matching_measurements(genesis, identity_payload)
    )
    if status == _CHARGED and not freshly_charged and not complete:
        crashed_record = _record(
            payload,
            status=_CRASH_INCOMPLETE,
            budget_before=existing_record["budget_before"],
            budget_after=existing_record["budget_after"],
            result={"reason": "charged round resumed without a complete durable measurement set"},
        )
        _install_round_record(genesis, crashed_record)
        genesis.persist(checkpoint_path)
        raise DurableMetaPolicyEvolutionError(
            "prior MetaPolicy round crashed after its physical budget was charged; redraw is refused"
        )

    # A charged-but-complete round is safe to finalise after a crash: no physical candidate work is
    # redrawn. A freshly charged round receives the full reserved allowance exactly once.
    allowances = dict(reserved) if freshly_charged else {
        "meta_policy_candidates": 0,
        "meta_policy_evaluations": 0,
    }
    base_budget = genesis.budget
    view = _ReservedBudgetView(base_budget, allowances)
    genesis.budget = view
    try:
        run = evolution.evolve_meta_policy(
            genesis,
            here,
            checkpoint_directory=checkpoint_path,
        )
        unused = view.unused()
    finally:
        genesis.budget = base_budget

    if any(int(value) for value in unused.values()):
        raise DurableMetaPolicyEvolutionError(
            "MetaPolicy round consumed fewer physical slots than were durably reserved"
        )

    completed_record = _record(
        payload,
        status=_COMPLETED,
        budget_before=existing_record["budget_before"],
        budget_after=existing_record["budget_after"],
        result={
            "accepted": bool(run.get("accepted")),
            "selection_reason": str(run.get("selection_reason") or ""),
            "run_digest": str(run.get("run_digest") or ""),
        },
    )
    _install_round_record(genesis, completed_record)
    checkpoint = genesis.persist(checkpoint_path)["checkpoint"]
    return {
        **run,
        "durable_budget_round": completed_record,
        "durable_budget_round_digest": round_digest,
        "durable_budget_checkpoint": checkpoint,
    }
