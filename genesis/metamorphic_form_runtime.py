"""Metamorphic policy runtime that keeps generated descendants in the lineage's current form.

``metamorphic_policy_loop`` owns the body/policy/MetaPolicy sequencing. This surface adds one runtime
invariant around that unchanged loop: every generated candidate constructed while an objective is
being worked on uses the interpreter target embodied by the current generated body.

That scope includes ordinary body proposals, lower-level policy-mutation evaluation, MetaPolicy
extension evaluation and retained-measurement semantic revalidation because they all construct bodies
through ``genesis.programs.artifact``. The binding is context-local and is discarded after the call.
After process death it is therefore derived again from the reconstructed body rather than remembered
in ambient process state.

This is DEVELOPMENT apparatus for testing continuation after a form/substrate change. It does not
make the alternate form self-generated and does not alter the trust-root measure.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from genesis import metamorphic_policy_loop as base
from genesis import programs


def _latest_acquisition_name(genesis) -> str:
    acquisitions = list(genesis.state.get("acquisitions") or [])
    if not acquisitions:
        return ""
    latest = acquisitions[-1]
    if not isinstance(latest, Mapping):
        return ""
    return str(latest.get("name") or "")


def run_objective(
    genesis,
    here,
    *,
    seed_policy: Mapping[str, Any] | None = None,
    seed_meta_policy: Mapping[str, Any] | None = None,
    max_rounds: int = 64,
    checkpoint_directory: Path | None = None,
) -> dict[str, Any]:
    """Run one integrated objective without reverting form or severing strict ancestry."""
    with programs.inherit_interpreter_form(
        genesis.body_factory,
        dependency=_latest_acquisition_name(genesis),
    ):
        result = base.run_objective(
            genesis,
            here,
            seed_policy=seed_policy,
            seed_meta_policy=seed_meta_policy,
            max_rounds=max_rounds,
            checkpoint_directory=checkpoint_directory,
        )
    result["generated_form_target"] = programs.interpreter_target_of(genesis.body_factory)
    return result
