from __future__ import annotations

import random

from metamorphosis.m012b_dfa import exact_equivalence, random_minimal_dfa
from metamorphosis.m017_lab import BehavioralOracle, generate_episodes, make_environment
from metamorphosis.m017_language import Library
from metamorphosis.m019_engine import Case, Individual, Population
from metamorphosis.m019_selection import (
    FORGET_KINDS,
    Genome,
    Ledger,
    duplicate_and_diverge,
)
from metamorphosis.structural import all_atoms, normalize_dfa


def _case(base, target) -> Case:
    return Case(
        base=base,
        make_oracle=lambda: BehavioralOracle(target),
        verify=lambda solution: bool(exact_equivalence(solution, target)[0]),
    )


def test_energy_is_the_search_budget():
    """Un organisme appauvri cherche moins loin. C'est la spirale de famine.

    Sans elle, l'inefficacité n'a pas de conséquence — et M018 a mesuré que sans
    conséquence, aucun mécanisme d'oubli ne rapporte quoi que ce soit.
    """
    ledger = Ledger(energy=100_000, reward=10_000, ceiling=60_000)
    assert ledger.budget() == 60_000

    ledger.settle(nodes=55_000, solved=False)
    assert ledger.energy == 45_000
    assert ledger.budget() == 45_000, "le budget doit suivre l'énergie une fois sous le plafond"

    ledger.settle(nodes=45_000, solved=False)
    assert not ledger.alive


def test_solving_cheaply_pays_and_solving_dearly_does_not():
    """Résoudre cher ne doit pas valoir mieux que ne pas résoudre."""
    thrifty = Ledger(energy=100_000, reward=25_000, ceiling=60_000)
    spendthrift = Ledger(energy=100_000, reward=25_000, ceiling=60_000)

    thrifty.settle(nodes=43, solved=True)
    spendthrift.settle(nodes=40_000, solved=True)

    assert thrifty.energy > 100_000, "l'organisme économe s'enrichit"
    assert spendthrift.energy < 100_000, "l'organisme dispendieux s'appauvrit"


def test_duplication_diverges_instead_of_copying():
    """L'opérateur que Genesis n'avait pas : copier, puis laisser dériver.

    Une duplication à l'identique n'apporterait rien ; c'est la divergence qui crée
    une structure nouvelle sans détruire l'ancienne.
    """
    library = Library.primitive()
    atoms = all_atoms()
    original = library.add((atoms[0], atoms[1], atoms[2]), episode=0)
    assert original is not None

    born = duplicate_and_diverge(library, random.Random(7))

    assert born is not None
    assert born.atoms != original.atoms
    assert len(born.atoms) == len(original.atoms)
    assert original in library.macros, "l'original survit à sa copie"


def test_a_genome_mutation_changes_exactly_one_trait():
    genome = Genome(
        max_symbols=3, abstraction_threshold=2, forget_kind="none", forget_parameter=6
    )
    rng = random.Random(3)
    for _ in range(30):
        mutant = genome.mutate(rng)
        differences = sum(
            1
            for field in ("max_symbols", "abstraction_threshold", "forget_kind", "forget_parameter")
            if getattr(mutant, field) != getattr(genome, field)
        )
        assert differences <= 1
        assert 2 <= mutant.max_symbols <= 3
        assert mutant.forget_kind in FORGET_KINDS


def test_selection_ranks_on_energy_left_not_on_successes():
    """Le classement porte sur ce qui reste après avoir payé, pas sur le nombre de succès."""
    population = Population.seed(4, seed=5, energy=100_000, reward=20_000, ceiling=60_000)
    rich, poor = population.individuals[0], population.individuals[1]
    rich.ledger.energy = 90_000
    rich.ledger.solved = 1
    poor.ledger.energy = 10_000
    poor.ledger.solved = 8  # beaucoup de succès, tous payés trop cher
    # La moitié la plus riche est conservée : le pauvre doit être hors des deux premiers.
    population.individuals[2].ledger.energy = 60_000
    population.individuals[3].ledger.energy = 50_000

    population.select(random.Random(0), starting_energy=100_000)

    lineages = [individual.lineage for individual in population.individuals]
    assert rich.lineage in lineages
    assert poor.lineage not in lineages


def test_the_dead_are_replaced_and_survivors_restart_level():
    """On sélectionne une stratégie, pas une avance accumulée."""
    population = Population.seed(4, seed=9, energy=100_000, reward=20_000, ceiling=60_000)
    population.individuals[0].ledger.energy = 80_000
    population.individuals[1].ledger.energy = 70_000
    population.individuals[2].ledger.energy = -1
    population.individuals[3].ledger.energy = -5

    population.select(random.Random(1), starting_energy=100_000)

    assert len(population.individuals) == 4
    assert population.deaths == 2
    assert {i.ledger.energy for i in population.individuals} == {100_000}
    assert population.generation == 1


def test_a_population_never_reports_a_false_success():
    """La rareté ne doit pas acheter de l'exactitude — jeter et mourir, oui ; mentir, non."""
    episodes = generate_episodes(make_environment(70_000), 70_100, count=3)
    population = Population.seed(3, seed=2, energy=200_000, reward=25_000, ceiling=60_000)
    population.live_generation([_case(e.base, e.target) for e in episodes])
    assert sum(i.ledger.solved + i.ledger.abstained for i in population.individuals) == 9


def test_a_dead_individual_stops_consuming():
    genome = Genome(
        max_symbols=2, abstraction_threshold=2, forget_kind="none", forget_parameter=4
    )
    individual = Individual.born(genome, "x", energy=-1, reward=10, ceiling=10)
    base = normalize_dfa(random_minimal_dfa(1, 5, 6))
    assert individual.live(_case(base, base)) == 0
