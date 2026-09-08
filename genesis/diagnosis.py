"""Diagnosis machinery: how a lineage finds out what is wrong with it.

`state.py` supplies registries that grow against certificates. Nothing produced those certificates —
the mechanism existed and nothing drove it. This module is the driver, and it is where the first two
authored ceilings actually open.

Two generalisations of things M107–M111 did once each:

* **Speculative extension with proven rollback.** M111's `probe()` extends one component, asks
  whether that resolves the demand, rolls back, and proves the rollback by comparing serialized
  state byte-for-byte. Here that shape is generic and the component list is not fixed by a module
  constant, so a lineage can probe a component class it named itself.
* **Insufficiency by exhaustion.** M107's certificate proves a target unreachable by exhausting the
  constructive image rather than by a failed search. Here, exhausting the *registry* — probing every
  component the lineage has and finding none of them resolves the demand — is what licenses naming a
  new one. "I could not fix it" is not evidence; "none of the things I can change is the thing that
  is wrong" is.

The vocabulary side has its own trigger, and it is empirical rather than invented. M113's pre-freeze
survey found the inherited three-feature vocabulary ambiguous on four of six occupied rows, one of
which M111 had recorded as determined. Two demands the current features cannot tell apart, whose
limiting components differ, are exactly the pair a vocabulary extension needs.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

from genesis import state as lineage_state
from genesis.trust_root import canonical_bytes, digest_of

DIAGNOSIS_SCHEMA = "genesis-diagnosis-v1"
PROBE_SCHEMA = "genesis-probe-v1"


class DiagnosisError(RuntimeError):
    """Raised when a probe cannot be trusted — most importantly when its rollback is not exact."""


def probe_component(
    state: Mapping[str, Any],
    component: str,
    demand: Mapping[str, Any],
    *,
    speculate: Callable[[Mapping[str, Any], str, Mapping[str, Any]], bool],
) -> dict[str, Any]:
    """Speculatively extend one component, ask whether the demand resolves, and prove the rollback.

    The rollback is not a promise. The state is serialized before and after and the two byte strings
    are compared, so a speculation that quietly kept something is caught rather than trusted.
    """
    if component not in lineage_state.component_names(state):
        raise DiagnosisError("cannot probe %r: it is not in the lineage's registry" % component)
    # Serialize the object as it is rather than through the validating encoder. A speculation that
    # mutated the state would otherwise surface as a digest error, which is true but says the wrong
    # thing: the fault is that the rollback was not exact, and the message should say so.
    before = canonical_bytes(dict(state))
    resolved = bool(speculate(state, component, demand))
    after = canonical_bytes(dict(state))
    if before != after:
        raise DiagnosisError(
            "probing %r mutated the lineage state; a speculation must roll back exactly" % component
        )
    return {
        "schema": PROBE_SCHEMA,
        "component": component,
        "resolved": resolved,
        "rolled_back_exactly": True,
        "demand_digest": digest_of(dict(demand)),
    }


def diagnose(
    state: Mapping[str, Any],
    demand: Mapping[str, Any],
    *,
    speculate: Callable[[Mapping[str, Any], str, Mapping[str, Any]], bool],
    budget,
    probe_dimension: str = "probes",
) -> dict[str, Any]:
    """Probe every component the lineage has, and report what that exhausts.

    A demand resolved by an existing component is an ordinary diagnosis. A demand no existing
    component resolves is the finding that licenses naming a new component class — but only that:
    the name and the demonstration that the new class resolves the demand are still the lineage's to
    supply.
    """
    registry = lineage_state.component_names(state)
    probes = []
    resolved_by = None
    for component in registry:
        budget.spend(probe_dimension)
        record = probe_component(state, component, demand, speculate=speculate)
        probes.append(record)
        if record["resolved"]:
            resolved_by = component
            break
    exhausted = resolved_by is None and len(probes) == len(registry)
    return {
        "schema": DIAGNOSIS_SCHEMA,
        "demand_digest": digest_of(dict(demand)),
        "registry": registry,
        "probes": probes,
        "resolved_by": resolved_by,
        "registry_exhausted": exhausted,
        "licenses_naming_a_new_component": exhausted,
    }


def certificate_from_diagnosis(
    diagnosis: Mapping[str, Any],
    *,
    new_component: str,
    resolves_with_new_component: bool,
) -> dict[str, Any]:
    """Turn an exhausting diagnosis into the certificate `state.extend_components` demands."""
    if not diagnosis.get("registry_exhausted"):
        raise DiagnosisError(
            "the registry was not exhausted, so an existing component could still be the answer"
        )
    return lineage_state.component_extension_certificate(
        prior_registry=list(diagnosis["registry"]),
        new_component=new_component,
        demand_digest=diagnosis["demand_digest"],
        probe_records=[
            {"component": record["component"], "resolved": False} for record in diagnosis["probes"]
        ],
        resolves_with_new_component=resolves_with_new_component,
    )


def find_indistinguishable_pair(
    state: Mapping[str, Any],
    demands: Sequence[Mapping[str, Any]],
    *,
    feature_row: Callable[[Mapping[str, Any], Mapping[str, Any]], Sequence[bool]],
    limiting_component: Callable[[Mapping[str, Any]], str],
) -> dict[str, Any] | None:
    """Find two demands the current vocabulary cannot separate although their causes differ.

    This is the empirical trigger for extending the vocabulary, not an invented one: without such a
    pair, a new feature is decoration, and `state.vocabulary_extension_certificate` refuses it.
    """
    seen: dict[tuple[bool, ...], list[Mapping[str, Any]]] = {}
    for demand in demands:
        row = tuple(bool(value) for value in feature_row(state, demand))
        seen.setdefault(row, []).append(demand)
    for row, group in sorted(seen.items()):
        for index, first in enumerate(group):
            for second in group[index + 1 :]:
                if limiting_component(first) != limiting_component(second):
                    return {
                        "shared_prior_row": list(row),
                        "demands": [dict(first), dict(second)],
                        "demand_digests": [digest_of(dict(first)), digest_of(dict(second))],
                        "limiting_components": [
                            limiting_component(first),
                            limiting_component(second),
                        ],
                    }
    return None


def certificate_from_pair(
    state: Mapping[str, Any],
    pair: Mapping[str, Any],
    *,
    new_feature: str,
    separates: Callable[[Mapping[str, Any]], bool],
) -> dict[str, Any]:
    """Turn a confusable pair into the certificate `state.extend_vocabulary` demands."""
    prior = lineage_state.vocabulary_names(state)
    row = list(pair["shared_prior_row"])
    values = [bool(separates(demand)) for demand in pair["demands"]]
    if values[0] == values[1]:
        raise DiagnosisError("the proposed feature gives both demands the same value")
    return lineage_state.vocabulary_extension_certificate(
        prior_vocabulary=prior,
        new_feature=new_feature,
        demand_digests=list(pair["demand_digests"]),
        shared_prior_row=row,
        limiting_components=list(pair["limiting_components"]),
        separated_rows=[row + [values[0]], row + [values[1]]],
    )
