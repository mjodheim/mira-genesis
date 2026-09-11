"""Runtime-owned Genesis v2 objective loop for bounded Open Metamorphosis.

The environment supplies an objective.  The launcher may supply the initial bounded search policy and
seed transformation language once, but it does not choose whether the lineage should search bodies,
construct its first language extension, or enter a recursive language generation.

The runtime owns that hand-off:

1. run the currently held body-search policy normally;
2. only after objective-scoped exhaustion may transformation machinery change;
3. if the lineage has no prior endogenous transformation-language extension, derive the admitted
   primitive lower kernel from the held seed language and search the first extension;
4. otherwise derive recursive primitives from lineage history and search the next extension;
5. if an extension is acquired, apply it through the separate causal language->policy->body path.

The immutable trust root, evaluation contract, isolation and physical budgets remain external.  This
is bounded DEVELOPMENT apparatus and does not imply open-ended self-programming.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from genesis import objective_policy_controller as opc
from genesis import policy_controller
from genesis import recursive_transformation_language as recursive
from genesis import retentive_objectives as retentive
from genesis import transformation_language as language
from genesis import transformation_language_application as application
from genesis import transformation_language_controller as language_controller
from genesis.trust_root import digest_of

OBJECTIVE_RUN_SCHEMA = "genesis-open-metamorphosis-objective-v1"


class OpenMetamorphosisRuntimeError(RuntimeError):
    """Raised when the runtime cannot justify the next v2 machinery transition."""


def _extension_certificates(genesis) -> tuple[dict[str, Any], ...]:
    values = []
    for item in genesis.state.get("observations", []):
        if not isinstance(item, Mapping) or item.get("kind") != "transformation_language_extension":
            continue
        certificate = item.get("certificate")
        if isinstance(certificate, Mapping):
            values.append(dict(certificate))
    return tuple(values)


def _seed_lower_steps(held_language: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """Derive the first-generation lower kernel from the already admitted seed language.

    Seed operators may expose the same primitive step under different names; content identity removes
    duplicates. Invocation is excluded: recursive invocation authority comes only from evidence-backed
    acquired operators through ``recursive_transformation_language``.
    """
    held = language.validate_language(held_language)
    values: dict[str, dict[str, Any]] = {}
    for operator in held["operators"]:
        for raw in operator["steps"]:
            step = language.validate_step(raw)
            if step["kind"] == "invoke_held_operator":
                continue
            values[step["step_digest"]] = step
    if not values:
        raise OpenMetamorphosisRuntimeError(
            "seed transformation language exposes no non-recursive lower primitive"
        )
    return tuple(sorted(values.values(), key=language.step_sort_key))


def run_objective(
    genesis,
    here,
    *,
    seed_policy: Mapping[str, Any] | None = None,
    seed_language: Mapping[str, Any] | None = None,
    max_policy_steps: int = 64,
    checkpoint_directory: Path | None = None,
) -> dict[str, Any]:
    """Run one objective and autonomously choose the required bounded v2 machinery level."""
    retentive.assert_retains_prior_work(genesis, here)
    checkpoint = Path(checkpoint_directory) if checkpoint_directory is not None else None

    held_language_before = language_controller.bound_language(genesis)
    if held_language_before is None and seed_language is not None:
        language_controller.admit_seed_language(genesis, seed_language)
        held_language_before = language_controller.bound_language(genesis)
        if checkpoint is not None:
            genesis.persist(checkpoint)
    elif seed_language is not None:
        validated_seed = language.validate_language(seed_language)
        if held_language_before != validated_seed:
            raise OpenMetamorphosisRuntimeError(
                "launcher attempted to replace the lineage's held transformation language"
            )

    body_run = retentive.run_policy(
        genesis,
        here,
        seed_policy=seed_policy if policy_controller.bound_policy(genesis) is None else None,
        max_steps=max_policy_steps,
        checkpoint_directory=checkpoint,
    )
    accepted = [step for step in body_run["steps"] if step.get("accepted")]
    if accepted:
        record = {
            "schema": OBJECTIVE_RUN_SCHEMA,
            "objective": opc.objective_record(genesis, here),
            "body_search": body_run,
            "body_adopted": True,
            "machinery_transition": None,
            "machinery_generation_selected_by_runtime": None,
            "language_application": None,
            "extension_count_before": len(_extension_certificates(genesis)),
            "extension_count_after": len(_extension_certificates(genesis)),
            "final_state_digest": genesis.state["state_digest"],
        }
        record["run_digest"] = digest_of(record)
        return record

    current_policy = policy_controller.bound_policy(genesis)
    if current_policy is None or not opc.exhausted(genesis, here, current_policy):
        raise OpenMetamorphosisRuntimeError(
            "body search stopped without adoption or a mechanically established exhaustion state"
        )

    held_language = language_controller.bound_language(genesis)
    if held_language is None:
        raise OpenMetamorphosisRuntimeError(
            "body machinery exhausted but the lineage holds no transformation language"
        )

    prior_extensions = _extension_certificates(genesis)
    generation = len(prior_extensions) + 1
    if not prior_extensions:
        transition = language_controller.run_extension_search(
            genesis,
            here,
            admitted_steps=_seed_lower_steps(held_language),
            checkpoint_directory=checkpoint,
        )
        mode = "first_endogenous_language_extension"
        language_changed = bool(transition.get("language_changed"))
    else:
        transition = recursive.run_recursive_extension_search(
            genesis,
            here,
            checkpoint_directory=checkpoint,
        )
        mode = "recursive_language_extension"
        language_changed = bool(transition.get("recursive_extension"))

    if not language_changed:
        record = {
            "schema": OBJECTIVE_RUN_SCHEMA,
            "objective": opc.objective_record(genesis, here),
            "body_search": body_run,
            "body_adopted": False,
            "machinery_transition": transition,
            "machinery_generation_selected_by_runtime": generation,
            "machinery_mode": mode,
            "language_application": None,
            "extension_count_before": len(prior_extensions),
            "extension_count_after": len(_extension_certificates(genesis)),
            "final_state_digest": genesis.state["state_digest"],
        }
        record["run_digest"] = digest_of(record)
        return record

    applied = application.apply_acquired_extension(
        genesis,
        here,
        max_policy_steps=max_policy_steps,
        checkpoint_directory=checkpoint,
    )
    if not applied.get("body_adopted"):
        raise OpenMetamorphosisRuntimeError(
            "runtime acquired a wider transformation language but it failed to produce an ordinary accepted body"
        )
    after_extensions = _extension_certificates(genesis)
    if len(after_extensions) != len(prior_extensions) + 1:
        raise OpenMetamorphosisRuntimeError(
            "one objective produced an unexpected number of transformation-language descendants"
        )

    record = {
        "schema": OBJECTIVE_RUN_SCHEMA,
        "objective": opc.objective_record(genesis, here),
        "body_search": body_run,
        "body_adopted": True,
        "machinery_transition": transition,
        "machinery_generation_selected_by_runtime": generation,
        "machinery_mode": mode,
        "language_application": applied,
        "extension_count_before": len(prior_extensions),
        "extension_count_after": len(after_extensions),
        "final_state_digest": genesis.state["state_digest"],
    }
    record["run_digest"] = digest_of(record)
    return record
