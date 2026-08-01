from __future__ import annotations

import functools

from metamorphosis.m012b_dfa import exact_equivalence
from metamorphosis.m017_lab import BehavioralOracle, generate_episodes, make_environment
from metamorphosis.m017_language import AbstractionRule, Library
from metamorphosis.m018_engine import ForgettingOrganism
from metamorphosis.m018_forgetting import (
    BudgetForgetting,
    DissolutionForgetting,
    NoForgetting,
    SymbolLedger,
    UtilityForgetting,
)
from metamorphosis.structural import all_atoms, flip


@functools.lru_cache(maxsize=2)
def _episodes(seed: int, count: int):
    return generate_episodes(make_environment(seed), seed + 100, count=count)


def _library_with(macro_count: int) -> tuple[Library, SymbolLedger]:
    library = Library.primitive()
    ledger = SymbolLedger()
    atoms = all_atoms()
    for index in range(macro_count):
        symbol = library.add((atoms[index], atoms[index + 1]), episode=0)
        assert symbol is not None
        ledger.register(symbol, 0)
    return library, ledger


def test_utility_forgetting_discards_only_what_never_served():
    library, ledger = _library_with(3)
    macros = list(library.macros)
    ledger.credit([macros[0].name])
    policy = UtilityForgetting(grace_period=2)

    assert policy.after_episode(library, AbstractionRule(), ledger, episode=1) == ()
    dropped = policy.after_episode(library, AbstractionRule(), ledger, episode=5)

    assert set(dropped) == {macros[1].name, macros[2].name}
    assert [symbol.name for symbol in library.macros] == [macros[0].name]


def test_budget_forgetting_evicts_the_least_used():
    library, ledger = _library_with(5)
    macros = list(library.macros)
    ledger.credit([macros[4].name, macros[4].name, macros[3].name])
    policy = BudgetForgetting(max_macros=2)

    dropped = policy.after_episode(library, AbstractionRule(), ledger, episode=9)

    assert len(dropped) == 3
    survivors = {symbol.name for symbol in library.macros}
    assert survivors == {macros[3].name, macros[4].name}


def test_dissolution_keeps_the_plan_and_destroys_the_body():
    """La chrysalide : tous les macros partent, les compteurs survivent affaiblis."""
    library, ledger = _library_with(4)
    rule = AbstractionRule()
    rule.counts = {"motif-a": 5, "motif-b": 1}
    policy = DissolutionForgetting(period=3)

    assert policy.after_episode(library, rule, ledger, episode=0) == ()
    dropped = policy.after_episode(library, rule, ledger, episode=2)

    assert len(dropped) == 4
    assert library.macros == ()
    assert [symbol.origin for symbol in library.symbols] == ["primitive"] * len(library)
    # Le plan survit, divisé par deux ; ce qui ne récurrait quasiment plus disparaît.
    assert rule.counts == {"motif-a": 2}


def test_no_forgetting_reproduces_the_m017_organism():
    library, ledger = _library_with(3)
    dropped = NoForgetting().after_episode(library, AbstractionRule(), ledger, episode=99)
    assert dropped == ()
    assert len(library.macros) == 3


def test_the_ledger_never_inspects_what_a_symbol_does():
    """L'organisme juge sur l'usage, jamais sur la sémantique.

    C'est la contrainte exacte d'un organisme qui manipule du code que personne ne
    comprend : le registre ne retient qu'un compte d'usages et un âge.
    """
    ledger = SymbolLedger()
    symbol = Library.primitive().symbols[0]
    ledger.register(symbol, episode=3)
    ledger.credit([symbol.name])

    assert ledger.uses[symbol.name] == 1
    assert ledger.age(symbol.name, episode=10) == 7
    assert set(vars(ledger)) == {"uses", "present_since"}


def test_a_forgetting_organism_still_never_reports_a_false_success():
    """Jeter ne doit jamais dégrader l'exactitude, seulement le coût."""
    episodes = _episodes(70_000, 6)
    organism = ForgettingOrganism(policy=DissolutionForgetting(period=3))
    for episode in episodes:
        result = organism.solve(episode.base, BehavioralOracle(episode.target))
        if result.status != "success":
            continue
        assert result.solution is not None
        assert exact_equivalence(result.solution, episode.target)[0]


def test_an_inherited_library_enters_the_ledger_unproven():
    """Une bibliothèque héritée n'a encore rien prouvé ici — c'est le passif de M017."""
    library = Library.primitive()
    library.add((flip("initial"), flip("deepest_rejecting")), episode=0)
    organism = ForgettingOrganism(policy=UtilityForgetting(), library=library)

    inherited = organism.library.macros[0].name
    assert organism.ledger.uses[inherited] == 0
    assert organism.ledger.present_since[inherited] == 0
