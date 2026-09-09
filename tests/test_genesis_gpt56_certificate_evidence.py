"""Counterexamples at the experimental-diagnosis -> certificate boundary.

A certificate is useful only to the extent that the evidence which licensed it survives the
conversion. These tests are intentionally red until component acquisition stops collapsing measured
reachability into an uncheckable boolean and incomplete searches stop qualifying as exhaustion.
"""
from __future__ import annotations

import pytest

from genesis import probe
from genesis import state as st


def test_component_certificate_requires_each_prior_probe_to_be_exhausted():
    """`resolved=False` may mean budget/instrument failure; it is not by itself exhaustion."""
    with pytest.raises(st.StateError, match="exhaust"):
        st.component_extension_certificate(
            prior_registry=["operator_table"],
            new_component="joint_registry",
            demand_digest="demand",
            probe_records=[
                {
                    "component": "operator_table",
                    "resolved": False,
                    "search_exhausted": False,
                    "budget_exhausted": True,
                    "instrument_failure": False,
                }
            ],
            resolves_with_new_component=True,
        )


def test_experimental_certificate_retains_the_resolving_composition_it_was_licensed_by():
    diagnosis = {
        "licenses_naming_a_new_component": True,
        "registry": ["operator_table"],
        "demand_digest": "demand",
        "probes": [
            {
                "component": "operator_table",
                "resolved": False,
                "attempts": 3,
                "search_exhausted": True,
                "budget_exhausted": False,
            }
        ],
        "resolving_composition": {
            "schema": probe.COMPOSITION_SCHEMA,
            "operations": ["double", "increment"],
            "composition_digest": "measured-composition-digest",
        },
    }

    certificate = probe.certificate_from_experiment(
        diagnosis,
        new_component="joint_registry",
    )
    assert certificate["resolving_composition"] == diagnosis["resolving_composition"]


def test_component_certificate_does_not_reduce_new_reachability_to_a_caller_boolean():
    """A raw `True` from the caller must not be enough to certify that a new component resolves."""
    with pytest.raises(st.StateError, match="resolving composition|evidence"):
        st.component_extension_certificate(
            prior_registry=["operator_table"],
            new_component="joint_registry",
            demand_digest="demand",
            probe_records=[
                {
                    "component": "operator_table",
                    "resolved": False,
                    "search_exhausted": True,
                    "budget_exhausted": False,
                    "instrument_failure": False,
                }
            ],
            resolves_with_new_component=True,
        )
