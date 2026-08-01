"""Les décrochages catalogués doivent rester reproductibles.

Un catalogue de modes de défaillance qui cesse de se reproduire n'est plus un
catalogue, c'est une anecdote. Ces tests fixent les mécanismes, pas les valeurs.
"""

from __future__ import annotations

from reproduce_measure_failures import case_R002, case_R004, case_R005, case_R006


def test_an_incapable_baseline_cannot_serve_as_a_criterion():
    finding = case_R002()
    assert finding["diverged"]
    assert finding["closed_solved"].startswith("0/")


def test_the_probabilistic_confirmation_misses_real_differences():
    """Le cœur du catalogue : une garantie annoncée que la procédure ne peut pas donner.

    Les différences sont engendrées avec le jeu d'atomes réel de l'organisme, et la
    vérité terrain est `exact_equivalence` — décidable, donc le décrochage se prouve.
    """
    finding = case_R004()
    assert finding["real_differences"] > 100
    assert finding["missed_by_probabilistic_set"] > 0, "le défaut d'origine a disparu"
    assert finding["missed_by_conformance_suite"] == 0, "la correction a régressé"
    assert finding["diverged"]


def test_a_free_quantity_exerts_no_pressure():
    finding = case_R005()
    assert not finding["budget_ever_binding"]
    assert finding["cost_gap_per_mille"] < 50
    assert finding["diverged"]


def test_an_impatient_horizon_reverses_the_verdict():
    """La mesure est juste ; c'est l'horizon qui retourne son verdict."""
    finding = case_R006()
    assert finding["learner_energy_at_horizon"] < finding["coward_energy_at_horizon"]
    assert finding["learner_energy_at_end"] > finding["coward_energy_at_end"]
    assert finding["diverged"]
