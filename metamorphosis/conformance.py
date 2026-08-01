"""Test de conformité exact d'un automate, par oracle d'appartenance seul.

Ce module existe à cause d'un faux succès, et il vaut mieux dire lequel.

M017 confirmait un candidat sur tous les mots jusqu'à la longueur 6, plus 96 mots
tirés au hasard entre 7 et 20. Sa docstring affirmait que ces mots longs couvraient la
borne de distinction. **C'était faux** : 96 tirages ne couvrent pas 2⁷+…+2²⁰. Le banc
de développement a rapporté « zéro faux succès » sur 42 épisodes par chance, pas par
garantie. Un balayage plus large a fini par produire deux automates à 9 états, tous
deux confirmés identiques, que le mot `(1,0,1,0,1,0,1)` distingue.

La méthode W du test de conformité règle exactement ce problème, et elle est plus
ancienne que le projet. Pour une hypothèse H à k états et une cible d'au plus k+s
états, la suite

    T = P · (ε ∪ Σ ∪ … ∪ Σ^s) · W

est **complète** : l'accord sur T implique l'équivalence. `P` est une couverture
d'états — un mot d'accès par état — et `W` un ensemble caractérisant, qui sépare
chaque paire d'états distincts.

Le résultat inattendu est le coût : pour k ≈ 9 et s = 2, la suite compte quelques
centaines de mots, soit **moins** que les 160 mots du jeu probabiliste qu'elle
remplace. L'ancienne confirmation était donc à la fois plus chère et moins sûre.

Hypothèse résiduelle, énoncée plutôt que dissimulée : la complétude ne vaut que si la
cible ne dépasse pas l'hypothèse de plus de `s` états après minimisation.
"""

from __future__ import annotations

from collections import deque
from typing import Sequence

from .m012b_dfa import DFA

Word = tuple[int, ...]


def state_cover(dfa: DFA) -> tuple[Word, ...]:
    """Un mot d'accès par état atteignable, le plus court, en ordre déterministe."""
    access: dict[int, Word] = {dfa.initial: ()}
    queue = deque([dfa.initial])
    while queue:
        state = queue.popleft()
        for symbol_index, symbol in enumerate(dfa.alphabet):
            target = dfa.transitions[state][symbol_index]
            if target not in access:
                access[target] = access[state] + (int(symbol),)
                queue.append(target)
    return tuple(access[state] for state in sorted(access))


def _distinguishing_word(dfa: DFA, left: int, right: int) -> Word | None:
    """Mot le plus court séparant deux états, ou None s'ils sont équivalents."""
    seen = {(left, right)}
    queue: deque[tuple[int, int, Word]] = deque([(left, right, ())])
    while queue:
        first, second, word = queue.popleft()
        if bool(dfa.accepting[first]) != bool(dfa.accepting[second]):
            return word
        for symbol_index, symbol in enumerate(dfa.alphabet):
            pair = (
                dfa.transitions[first][symbol_index],
                dfa.transitions[second][symbol_index],
            )
            if pair not in seen:
                seen.add(pair)
                queue.append((pair[0], pair[1], word + (int(symbol),)))
    return None


def characterizing_set(dfa: DFA) -> tuple[Word, ...]:
    """Ensemble séparant toute paire d'états distincts.

    Construit par ajouts successifs : on ne cherche un séparateur que pour les paires
    que les mots déjà retenus ne séparent pas. Sur un automate minimal, toute paire
    admet un séparateur, donc l'ensemble rendu est complet.
    """
    words: list[Word] = []

    def separated(left: int, right: int) -> bool:
        return any(
            _run_accepts(dfa, left, word) != _run_accepts(dfa, right, word)
            for word in words
        )

    for left in range(dfa.n_states):
        for right in range(left + 1, dfa.n_states):
            if separated(left, right):
                continue
            witness = _distinguishing_word(dfa, left, right)
            if witness is not None and witness not in words:
                words.append(witness)
    if not words:
        words.append(())
    return tuple(words)


def _run_accepts(dfa: DFA, state: int, word: Sequence[int]) -> bool:
    for symbol in word:
        state = dfa.transitions[state][dfa.alphabet.index(symbol)]
    return bool(dfa.accepting[state])


def w_method_suite(dfa: DFA, extra_states: int = 2) -> tuple[Word, ...]:
    """Suite de test complète pour une cible d'au plus `dfa.n_states + extra_states`.

    Rend les mots triés par longueur puis lexicographiquement : les courts d'abord,
    ce qui fait échouer un mauvais candidat au plus tôt.
    """
    cover = state_cover(dfa)
    characterizing = characterizing_set(dfa)

    middles: list[Word] = [()]
    frontier: list[Word] = [()]
    for _ in range(max(0, extra_states)):
        frontier = [
            word + (int(symbol),) for word in frontier for symbol in dfa.alphabet
        ]
        middles.extend(frontier)

    suite = {
        prefix + middle + suffix
        for prefix in cover
        for middle in middles
        for suffix in characterizing
    }
    return tuple(sorted(suite, key=lambda word: (len(word), word)))
