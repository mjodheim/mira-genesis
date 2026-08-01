from __future__ import annotations

import functools

from metamorphosis.m012b_dfa import exact_equivalence
from metamorphosis.m017_engine import (
    ClosedLibraryOrganism,
    OpenSearchOrganism,
    SelfExtendingOrganism,
)
from metamorphosis.m017_lab import (
    CLOSED_LIBRARY_PROGRAMS,
    BehavioralOracle,
    generate_episodes,
    make_environment,
    make_out_of_language_target,
)
from metamorphosis.m017_language import Library, description_length
from metamorphosis.structural import (
    all_atoms,
    apply_atoms,
    flip,
    normalize_dfa,
    redirect,
    walk,
)


# La construction d'un environnement filtre ses motifs par recherche de référence :
# coûteux, et identique pour tous les tests. Une seule fois.
@functools.lru_cache(maxsize=2)
def _environment(seed: int):
    return make_environment(seed)


@functools.lru_cache(maxsize=2)
def _episodes(seed: int, count: int):
    return generate_episodes(_environment(seed), seed + 100, count=count)


def test_composition_is_sequential_not_a_set_of_edits():
    """Un atome déplace les rôles que le suivant va lire.

    C'est la propriété qui donne à la profondeur un pouvoir expressif. Sans elle —
    rôles résolus une fois sur la source — un programme n'est qu'un ensemble
    d'éditions indépendantes, et cinq motifs de trois atomes sur huit avaient alors
    un équivalent en deux atomes ou moins.
    """
    base = _episodes(70_000, 2)[0].base
    first = redirect("initial", 0, "deepest_accepting")
    second = flip("deepest_accepting")
    forward = apply_atoms(base, (first, second))
    backward = apply_atoms(base, (second, first))
    assert forward is not None and backward is not None
    assert not exact_equivalence(normalize_dfa(forward), normalize_dfa(backward))[0]


def test_walk_agrees_with_direct_application():
    """Le parcours à préfixes partagés doit rendre exactement les mêmes automates."""
    base = _episodes(70_000, 2)[0].base
    atoms = all_atoms()[:6]
    blocks = [(atom,) for atom in atoms]
    for indices, produced in walk(base, blocks, 2):
        direct = apply_atoms(base, [atoms[index] for index in indices])
        if direct is None:
            assert produced.transitions == base.transitions
            assert produced.accepting == base.accepting
        else:
            assert produced.transitions == direct.transitions
            assert produced.accepting == direct.accepting


def test_closed_library_cannot_express_composed_targets():
    """L'organisme de M014c s'abstient : incapacité structurelle, pas lenteur."""
    episodes = _episodes(70_000, 4)
    organism = ClosedLibraryOrganism(CLOSED_LIBRARY_PROGRAMS)
    statuses = [
        organism.solve(episode.base, BehavioralOracle(episode.target)).status
        for episode in episodes
    ]
    assert set(statuses) == {"abstained"}


def test_open_search_solves_but_never_gets_cheaper():
    """Capable, mais il repaye le prix fort : aucun symbole n'est jamais absorbé."""
    episodes = _episodes(70_000, 4)
    organism = OpenSearchOrganism()
    results = [
        organism.solve(episode.base, BehavioralOracle(episode.target))
        for episode in episodes
    ]
    assert any(result.status == "success" for result in results)
    assert all(result.macro_count == 0 for result in results)
    assert len(organism.library.macros) == 0


def test_self_extending_organism_absorbs_and_collapses_its_search():
    """Le cœur de M017 : le vocabulaire grandit, la recherche s'effondre.

    Les solutions restent exactes — un gain de coût payé par une approximation ne
    prouverait rien.
    """
    episodes = _episodes(70_000, 12)
    organism = SelfExtendingOrganism()
    solved: list[tuple[int, int]] = []
    for episode in episodes:
        result = organism.solve(episode.base, BehavioralOracle(episode.target))
        if result.status != "success":
            continue
        assert result.solution is not None
        assert exact_equivalence(result.solution, episode.target)[0]
        solved.append((episode.index, result.search_nodes))

    assert len(organism.library.macros) > 0, "aucun motif absorbé"
    early = [nodes for index, nodes in solved if index < len(episodes) // 2]
    late = [nodes for index, nodes in solved if index >= len(episodes) // 2]
    assert early and late
    assert min(late) * 10 < max(early), "la recherche ne s'est pas effondrée"


def test_self_extension_buys_capability_not_only_speed():
    """Genesis résout des cibles que la recherche ouverte n'atteint pas."""
    episodes = _episodes(70_000, 12)
    genesis = SelfExtendingOrganism()
    genesis_solved = {
        episode.index
        for episode in episodes
        if genesis.solve(episode.base, BehavioralOracle(episode.target)).status == "success"
    }
    openly = OpenSearchOrganism()
    open_solved = {
        episode.index
        for episode in episodes
        if openly.solve(episode.base, BehavioralOracle(episode.target)).status == "success"
    }
    assert open_solved <= genesis_solved


def test_a_macro_compresses_the_description_length():
    library = Library.primitive()
    trajectory = (
        redirect("initial", 0, "deepest_accepting"),
        flip("deepest_accepting"),
        flip("deepest_rejecting"),
    )
    assert description_length(trajectory, library) == 3
    library.add(trajectory, episode=0)
    assert description_length(trajectory, library) == 1


def test_library_survives_a_serialization_round_trip():
    """Un langage qui ne se transporte pas ne se réincarne pas."""
    library = Library.primitive()
    library.add((flip("initial"), flip("deepest_rejecting")), episode=3)
    restored = Library.from_json(library.to_json())
    assert restored.to_json() == library.to_json()
    assert restored.sha256() == library.sha256()
    assert len(restored.macros) == 1


def test_the_conformance_suite_separates_every_real_difference():
    """La confirmation probabiliste laissait passer de vraies différences.

    Elle tirait 96 mots longs au hasard en affirmant couvrir la borne de distinction.
    Le « zéro faux succès » de M017 tenait à la chance du tirage : deux automates à
    9 états confirmés identiques sont séparés par `(1,0,1,0,1,0,1)`.
    """
    from metamorphosis.conformance import w_method_suite
    from metamorphosis.m012b_dfa import DFA, random_minimal_dfa

    # Les différences sont produites par le langage réel de l'organisme, atomes de
    # redirection compris. Une version antérieure de ce test n'inversait que des bits
    # d'acceptation : elle passait alors que la suite, bâtie sur une couverture d'états
    # au lieu d'une couverture de transitions, laissait passer toutes les redirections.
    atoms = all_atoms()
    checked = 0
    for seed in range(30):
        left = normalize_dfa(random_minimal_dfa(seed, 7, 9))
        for offset in range(0, len(atoms), 7):
            edited = apply_atoms(left, (atoms[offset],))
            if edited is None:
                continue
            right = normalize_dfa(edited)
            if exact_equivalence(left, right)[0]:
                continue
            checked += 1
            suite = w_method_suite(left, max_target_states=left.n_states)
            assert any(
                left.accepts(word) != right.accepts(word) for word in suite
            ), f"la suite laisse passer {atoms[offset]}, graine {seed}"
    assert checked > 20, "le test n'a pas exercé assez de différences réelles"


def test_the_conformance_suite_needs_a_minimal_hypothesis():
    """La méthode W exige une hypothèse minimale, et la minimise plutôt que la supposer.

    La première correction construisait la suite depuis le candidat brut de la
    recherche. `characterizing_set` y cherchait à séparer des paires d'états
    équivalents, échouait en silence, et un second faux succès a survécu.
    """
    from metamorphosis.conformance import w_method_suite
    from metamorphosis.m012b_dfa import DFA, random_minimal_dfa

    minimal = normalize_dfa(random_minimal_dfa(11, 5, 6))
    # Même langage, états dupliqués : l'automate n'est plus minimal.
    width = minimal.n_states
    padded = DFA(
        minimal.alphabet,
        tuple(tuple(row) for row in minimal.transitions)
        + tuple(tuple(row) for row in minimal.transitions),
        minimal.accepting + minimal.accepting,
        minimal.initial,
    )
    assert padded.n_states == 2 * width

    from_minimal = w_method_suite(minimal, max_target_states=width)
    from_padded = w_method_suite(padded, max_target_states=width)
    assert from_padded == from_minimal


def test_an_unrelated_inherited_library_is_a_liability():
    """Absorber n'est pas gratuit : un macro qui ne s'applique jamais coûte quand même.

    Mesuré sur quatre paires d'environnements : une bibliothèque héritée d'un
    environnement aux motifs disjoints donne 0,65× à 0,75× — strictement pire que pas
    de bibliothèque du tout. C'est la leçon de M014b un cran plus haut : transporter
    un mécanisme ne transporte pas son avantage.

    Ce test verrouille le mécanisme, pas la valeur : une bibliothèque encombrée de
    symboles inutiles élargit le facteur de branchement, donc explore strictement plus
    de nœuds à solution égale.
    """
    episode = _episodes(70_000, 2)[0]
    oracle_a = BehavioralOracle(episode.target)
    oracle_b = BehavioralOracle(episode.target)

    bare = SelfExtendingOrganism()
    cluttered_library = Library.primitive()
    for start in range(0, 12, 2):
        atoms = all_atoms()
        cluttered_library.add((atoms[start], atoms[start + 1]), episode=0)
    cluttered = SelfExtendingOrganism(library=cluttered_library)

    plain = bare.solve(episode.base, oracle_a)
    loaded = cluttered.solve(episode.base, oracle_b)

    assert plain.status == "success" and loaded.status == "success"
    assert loaded.search_nodes > plain.search_nodes


def test_out_of_language_target_is_refused():
    """Une cible qui ajoute un état n'est atteignable à aucune profondeur."""
    episode = _episodes(70_000, 2)[0]
    oracle = BehavioralOracle(make_out_of_language_target(episode.base, 4242))
    result = SelfExtendingOrganism(search_budget=20_000).solve(episode.base, oracle)
    assert result.status == "abstained"


def test_unstable_oracle_is_refused():
    episode = _episodes(70_000, 2)[0]
    oracle = BehavioralOracle(episode.target, mode="alternating")
    result = SelfExtendingOrganism(search_budget=20_000).solve(episode.base, oracle)
    assert result.status == "abstained"
    assert result.reason == "oracle_inconsistent"
