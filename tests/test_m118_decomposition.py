"""A verdict is not a mechanism: the arms decide what may be claimed."""

from __future__ import annotations

from metamorphosis import m118_decomposition as decomp


def _rates(**kw):
    base = {"T0": 0.10, "fresh_uniform": 0.30, "M2": 0.30, "probe_only": 0.30, "M3": 0.30,
            "probe_only_budget_plus": 0.30}
    base.update(kw)
    return base


def test_a_negative_supports_no_causal_claim():
    out = decomp.decompose(_rates(M3=0.9), positive=False)
    assert "negative" in out["strongest_supported_statement"]
    assert "No causal claim" in out["strongest_supported_statement"]


def test_probe_only_reproducing_the_advantage_denies_the_cascade_claim():
    out = decomp.decompose(_rates(M3=0.9, probe_only=0.9), positive=True)
    assert "NOT the acquired rule cascade" in out["strongest_supported_statement"]
    assert out["descendant_beats_probe_only"] is False


def test_exceeding_both_ablations_supports_the_combined_claim():
    out = decomp.decompose(_rates(M3=0.9, probe_only=0.4, M2=0.4), positive=True)
    assert "additional contribution from the combined acquired machinery" in \
        out["strongest_supported_statement"]


def test_cascade_without_incremental_policy_benefit_is_stated_as_such():
    out = decomp.decompose(_rates(M3=0.75, M2=0.75, probe_only=0.30), positive=True)
    assert "not an incremental benefit from the diagnostic policy" in \
        out["strongest_supported_statement"]


def test_beating_t0_but_not_the_comparator_is_negative():
    out = decomp.decompose(_rates(T0=0.05, fresh_uniform=0.80, M3=0.82), positive=True)
    assert out["descendant_beats_legacy_t0"] is True
    assert out["descendant_beats_designated_fresh_comparator"] is False
    assert "negative against the designated comparator" in out["strongest_supported_statement"]


def test_budget_rescuing_probe_only_is_recorded():
    out = decomp.decompose(_rates(probe_only=0.30, probe_only_budget_plus=0.80), positive=True)
    assert out["extra_budget_rescues_probe_only"] is True


def test_provider_invariance_is_always_unsupported():
    out = decomp.decompose(_rates(M3=0.9, probe_only=0.2, M2=0.2), positive=True)
    assert any("provider invariance" in item for item in out["unsupported_without_further_arms"])


def test_beating_t0_alone_is_never_evidence():
    assert decomp.decompose(_rates(), positive=True)["beating_t0_alone_is_not_evidence"] is True


def test_rates_are_computed_from_outcomes():
    rates = decomp.rates_from_outcomes({"M3": [True, True, False, False]})
    assert rates["M3"] == 0.5
    assert decomp.rates_from_outcomes({"M3": []})["M3"] is None
