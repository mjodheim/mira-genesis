"""Langage de transformation structurelle, indépendant de toute expérience.

Une transformation ne nomme jamais un indice d'état. Elle nomme un **rôle** dans le
graphe — état initial, état acceptant le plus profond, état rejetant de plus fort
degré entrant — puis agit sur l'état qui occupe ce rôle. C'est ce qui rend une
transformation transportable d'un automate à un autre.

Ce module a été extrait de `m014c_meta.py`. Il ne contient que la partie qui n'est
propre à aucune expérience : les rôles, les atomes, leur application et les formes
canoniques. Ce qui appartenait à M014c — passeport, session, politique de requêtes —
n'a pas été repris ; voir `experiments/M014c/STATUS.md` pour la raison.

Sémantique de composition : **séquentielle**. Chaque atome résout ses rôles sur
l'automate tel que l'atome précédent l'a laissé. Un programme est une trajectoire,
pas un ensemble d'éditions.

Ce choix n'est pas cosmétique, et il a été fait après mesure. Avec une résolution
unique sur la source, un programme se réduit à des éditions indépendantes sur cinq
états : l'espace atteignable est minuscule et **cinq motifs de trois atomes sur huit
avaient un équivalent exact en deux atomes ou moins**, trois d'entre eux en un seul.
La composition n'apportait donc aucun pouvoir expressif, et une expérience sur le
langage n'aurait mesuré que du bruit — la même impasse que M014c, un cran plus haut.

En séquentiel, un atome déplace les rôles que le suivant va lire. Les raccourcis
deviennent rares, la profondeur porte enfin de l'information, et l'abstraction d'un
motif récurrent a quelque chose à gagner. La concaténation reste associative, seule
propriété dont l'abstraction ait besoin : déplier un macro-symbole rend exactement la
même trajectoire.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import json
from typing import Iterator, Sequence

from .m012b_dfa import DFA, canonicalize, minimize_dfa

Word = tuple[int, ...]

# Quatre rôles, soit 4 + 4×2×4 = 36 atomes. La profondeur 3 fait 46 656 séquences :
# assez pour que la recherche exhaustive coûte cher sans être hors de portée, et
# assez pour que la profondeur 4 — 1,7 million — soit hors budget. C'est là que se
# lit la différence entre un organisme qui étend son langage et un qui ne peut pas.
ROLES: tuple[str, ...] = (
    "initial",
    "deepest_accepting",
    "deepest_rejecting",
    "max_indegree_rejecting",
)


def normalize_dfa(dfa: DFA) -> DFA:
    return canonicalize(minimize_dfa(dfa))


def dfa_key(dfa: DFA) -> str:
    return json.dumps(normalize_dfa(dfa).to_dict(), sort_keys=True, separators=(",", ":"))


def _graph_features(dfa: DFA) -> tuple[list[int], list[int]]:
    n = dfa.n_states
    distances = [10**9] * n
    distances[dfa.initial] = 0
    queue = deque([dfa.initial])
    while queue:
        state = queue.popleft()
        for target in dfa.transitions[state]:
            if distances[target] > distances[state] + 1:
                distances[target] = distances[state] + 1
                queue.append(target)
    indegree = [0] * n
    for row in dfa.transitions:
        for target in row:
            indegree[target] += 1
    return distances, indegree


def role_state(dfa: DFA, role: str) -> int | None:
    """État occupant un rôle, ou None si le rôle est vacant dans cet automate."""
    if role == "initial":
        return dfa.initial
    distances, indegree = _graph_features(dfa)
    if role.endswith("_accepting"):
        want, base_role = True, role[: -len("_accepting")]
    elif role.endswith("_rejecting"):
        want, base_role = False, role[: -len("_rejecting")]
    else:
        raise ValueError(f"unknown structural role: {role}")
    states = [state for state in range(dfa.n_states) if bool(dfa.accepting[state]) is want]
    if not states:
        return None
    if base_role == "deepest":
        return max(states, key=lambda state: (distances[state], indegree[state], -state))
    if base_role == "max_indegree":
        return max(states, key=lambda state: (indegree[state], distances[state], -state))
    raise ValueError(f"unknown structural role: {role}")


@dataclass(frozen=True)
class Atom:
    """Édition structurelle élémentaire, exprimée en rôles."""

    kind: str
    args: tuple[object, ...]

    def to_list(self) -> list[object]:
        return [self.kind, *self.args]

    @staticmethod
    def from_list(data: Sequence[object]) -> "Atom":
        return Atom(str(data[0]), tuple(data[1:]))

    def __str__(self) -> str:
        return f"{self.kind}({','.join(str(argument) for argument in self.args)})"


def flip(role: str) -> Atom:
    return Atom("flip", (role,))


def redirect(source_role: str, symbol: int, target_role: str) -> Atom:
    return Atom("redirect", (source_role, int(symbol), target_role))


def grow(role: str, incoming: int = 0) -> Atom:
    """Duplicate the state holding `role`, routing its `incoming`-th in-edge to the twin."""

    return Atom("grow", (role, int(incoming)))


def growth_atoms(
    roles: Sequence[str] = ROLES, choices: Sequence[int] = (0, 1)
) -> tuple[Atom, ...]:
    """The capacity-increasing vocabulary, kept separate from `all_atoms`.

    Deliberately not folded into `all_atoms`: every recorded experiment draws its
    vocabulary from there, and widening it would change their reachable sets and move
    their digests. An organism opts into growth explicitly.
    """

    return tuple(grow(role, choice) for role in roles for choice in choices)


def all_atoms(roles: Sequence[str] = ROLES, symbols: Sequence[int] = (0, 1)) -> tuple[Atom, ...]:
    """Vocabulaire atomique complet. C'est le plancher expressif, pas le plafond."""
    atoms = [flip(role) for role in roles]
    atoms.extend(
        redirect(source, symbol, target)
        for source in roles
        for symbol in symbols
        for target in roles
    )
    return tuple(atoms)


def apply_atom(current: DFA, atom: Atom) -> DFA | None:
    """Applique **un** atome, rôles résolus sur `current`. None si un rôle est vacant.

    L'automate rendu n'est pas minimisé : c'est la primitive la plus chaude de la
    recherche, appelée des dizaines de milliers de fois par épisode. La recherche
    partage les préfixes, si bien qu'une séquence de longueur d ne coûte qu'un appel
    de plus que son préfixe de longueur d−1.
    """
    if atom.kind == "flip":
        state = role_state(current, str(atom.args[0]))
        if state is None:
            return None
        accepting = list(current.accepting)
        accepting[state] = not accepting[state]
        return DFA(current.alphabet, current.transitions, tuple(accepting), current.initial)

    if atom.kind == "redirect":
        source = role_state(current, str(atom.args[0]))
        target = role_state(current, str(atom.args[2]))
        if source is None or target is None:
            return None
        symbol = int(atom.args[1])  # type: ignore[arg-type]
        transitions = [list(row) for row in current.transitions]
        transitions[source][symbol] = target
        return DFA(
            current.alphabet,
            tuple(tuple(row) for row in transitions),
            tuple(current.accepting),
            current.initial,
        )

    if atom.kind == "grow":
        # The only capacity-increasing atom. Every other edit preserves or reduces the
        # state count — measured across 53,280 applications, 18,540 of which changed it
        # and none increased it — so without this the organism can never express anything
        # its birth size forbids.
        #
        # The twin carries the same outgoing transitions and the same acceptance, so at
        # the instant of duplication the language is unchanged. That neutrality is the
        # mechanism, not a detail: a mutation selection cannot see is free to drift.
        state = role_state(current, str(atom.args[0]))
        if state is None:
            return None
        size = current.n_states
        transitions = [list(row) for row in current.transitions]
        accepting = list(current.accepting)
        transitions.append(list(current.transitions[state]))
        accepting.append(bool(current.accepting[state]))

        incoming = [
            (source, symbol)
            for source in range(size)
            for symbol in (0, 1)
            if transitions[source][symbol] == state
        ]
        if not incoming:
            # An unreachable twin would be stripped by normalisation and would add no
            # capacity. Refusing is honest; pretending to grow is not.
            return None
        source, symbol = incoming[int(atom.args[1]) % len(incoming)]
        transitions[source][symbol] = size
        return DFA(
            current.alphabet,
            tuple(tuple(row) for row in transitions),
            tuple(accepting),
            current.initial,
        )

    raise ValueError(f"unknown atom kind: {atom.kind}")


def apply_atoms(base: DFA, atoms: Sequence[Atom]) -> DFA | None:
    """Déroule une trajectoire complète. None si elle avorte ou n'a aucun effet net."""
    current = base
    for atom in atoms:
        nxt = apply_atom(current, atom)
        if nxt is None:
            return None
        current = nxt
    if current.transitions == base.transitions and current.accepting == base.accepting:
        return None
    return current


def walk(
    base: DFA,
    blocks: Sequence[Sequence[Atom]],
    depth: int,
) -> Iterator[tuple[tuple[int, ...], DFA]]:
    """Parcours en profondeur de toutes les trajectoires de `depth` blocs.

    Un bloc est une suite d'atomes : un atome seul pour le laboratoire, un symbole de
    bibliothèque — donc possiblement un macro — pour l'organisme. Le préfixe est
    partagé, si bien qu'une trajectoire de longueur d ne coûte qu'un pas de plus que
    son préfixe. Sans ce partage, la sémantique séquentielle rendrait la profondeur 3
    impraticable.

    Rend l'indice des blocs choisis et l'automate obtenu, jamais minimisé.
    """

    def descend(
        current: DFA, chosen: tuple[int, ...], remaining: int
    ) -> Iterator[tuple[tuple[int, ...], DFA]]:
        if remaining == 0:
            yield chosen, current
            return
        for index, block in enumerate(blocks):
            nxt: DFA | None = current
            for atom in block:
                nxt = apply_atom(nxt, atom)  # type: ignore[arg-type]
                if nxt is None:
                    break
            if nxt is None:
                continue
            yield from descend(nxt, chosen + (index,), remaining - 1)

    yield from descend(base, (), depth)


def enumerate_words(max_length: int) -> tuple[Word, ...]:
    words: list[Word] = [()]
    frontier: list[Word] = [()]
    for _ in range(max_length):
        frontier = [word + (symbol,) for word in frontier for symbol in (0, 1)]
        words.extend(frontier)
    return tuple(words)


def fingerprint(dfa: DFA, words: Sequence[Word]) -> tuple[bool, ...]:
    """Empreinte comportementale sur un jeu de mots fixe.

    Simulation directe, sans minimisation : c'est la primitive la plus chaude de la
    recherche dans l'espace des programmes.
    """
    transitions = dfa.transitions
    accepting = dfa.accepting
    initial = dfa.initial
    outputs: list[bool] = []
    for word in words:
        state = initial
        for symbol in word:
            state = transitions[state][symbol]
        outputs.append(bool(accepting[state]))
    return tuple(outputs)


def atoms_to_json(atoms: Sequence[Atom]) -> list[list[object]]:
    return [atom.to_list() for atom in atoms]


def atoms_from_json(data: Sequence[Sequence[object]]) -> tuple[Atom, ...]:
    return tuple(Atom.from_list(row) for row in data)


def canonical_atom_key(atoms: Sequence[Atom]) -> str:
    """Clé stable d'une trajectoire. **L'ordre compte** : la sémantique est séquentielle."""
    return json.dumps([atom.to_list() for atom in atoms], separators=(",", ":"))


def describe_atoms(atoms: Sequence[Atom]) -> str:
    return " · ".join(str(atom) for atom in atoms)


__all__ = [
    "ROLES",
    "Atom",
    "Word",
    "all_atoms",
    "apply_atom",
    "apply_atoms",
    "atoms_from_json",
    "atoms_to_json",
    "canonical_atom_key",
    "describe_atoms",
    "dfa_key",
    "enumerate_words",
    "fingerprint",
    "flip",
    "normalize_dfa",
    "redirect",
    "role_state",
    "walk",
]
